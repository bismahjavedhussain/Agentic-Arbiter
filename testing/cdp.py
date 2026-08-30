"""A very small Chrome DevTools Protocol client, so a check can HOVER and can press TAB.

🔴 WHY THIS EXISTS, AND WHY NOTHING ELSE IN `testing/` NEEDED IT UNTIL NOW.
Every other browser check here runs Chrome with `--dump-dom` or `--screenshot`, evaluates a probe
script, and reads what the page published. That is enough for anything the page can do to itself, and
it is enough for the ~500 assertions already written against it. It cannot do the two things a
POINTER and a KEYBOARD do, and those are exactly what a hover-and-focus brief is about:

  * `:hover` is set by the browser from real pointer position. There is no DOM API that sets it. A
    probe can read the RULE out of the CSSOM, which proves the rule was written; it cannot prove the
    browser applies it, and it cannot photograph it.
  * `:focus-visible` is a HEURISTIC, not a synonym for `:focus`. Chrome grants it when focus arrived
    from the keyboard and withholds it from a plain `element.focus()` on a <button>. So a check that
    calls `.focus()` and finds no ring has proved nothing at all: that is the specified behaviour.
    Only a real Tab keypress answers "does tabbing show a ring".

CDP supplies both: `Input.dispatchMouseEvent` moves a real pointer, `Input.dispatchKeyEvent` presses a
real key, and `Page.captureScreenshot` photographs the result. `websockets` is already installed;
nothing new is added to the environment.

⚠ THIS IS A TEST HARNESS AND NOTHING SHIPS IT. It talks to a Chrome this process started, on a
loopback port this process chose, and it tears that Chrome down in a `finally`. It never reads the
repository's `.env`, never sends a request anywhere but 127.0.0.1, and cannot spend a credit.

Usage:
    from cdp import Chrome
    with Chrome(url, width=1600, height=1000) as c:
        c.eval("document.title")
        c.hover(x, y)
        c.key("Tab")
        png_bytes = c.shot()
"""
import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect as ws_connect

CHROME = None
for _c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")):
    if os.path.isfile(_c):
        CHROME = _c
        break


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Chrome(object):
    def __init__(self, url, width=1600, height=1000, extra=()):
        self.url = url
        self.width = width
        self.height = height
        self.extra = list(extra)
        self.proc = None
        self.ws = None
        self.prof = None
        self._id = 0
        # Buffered CDP events, and the set of method names worth buffering. Empty by default, so a
        # caller that never subscribes pays nothing and behaves exactly as before.
        self._events = []
        self._want = set()
        self.polls = []

    # ---------------------------------------------------------------- lifecycle
    def __enter__(self):
        if not CHROME:
            raise RuntimeError("no chrome found")
        self.port = free_port()
        self.prof = tempfile.mkdtemp(prefix="cdp_")
        args = [CHROME, "--headless=new", "--no-first-run", "--no-default-browser-check",
                "--remote-debugging-port=%d" % self.port,
                "--user-data-dir=" + self.prof,
                "--window-size=%d,%d" % (self.width, self.height),
                "--hide-scrollbars",
                # MapLibre needs a rasteriser; every other check here passes the same pair.
                "--enable-unsafe-swiftshader", "--use-gl=angle",
                "--autoplay-policy=no-user-gesture-required",
                # ⚠ NO --virtual-time-budget. Virtual time and a live CDP session fight: the clock
                # runs ahead of the socket and the page can finish before the first command lands.
                # This harness waits on the real clock, which is what a hover check has to do anyway.
                "--disable-features=Translate,BackForwardCache",
                ] + self.extra + ["about:blank"]
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        target = None
        for _ in range(120):
            try:
                raw = urllib.request.urlopen(
                    "http://127.0.0.1:%d/json/list" % self.port, timeout=1).read()
                for t in json.loads(raw.decode("utf-8")):
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        target = t
                        break
                if target:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        if not target:
            self.__exit__(None, None, None)
            raise RuntimeError("chrome never opened a debuggable page")

        self.ws = ws_connect(target["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024,
                             open_timeout=20)
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("DOM.enable")
        return self

    def __exit__(self, *a):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if self.prof:
            shutil.rmtree(self.prof, ignore_errors=True)
        return False

    # ---------------------------------------------------------------- protocol
    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        deadline = time.time() + 60
        while time.time() < deadline:
            raw = self.ws.recv(timeout=max(1, deadline - time.time()))
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
            # 🔴 EVENTS ARRIVE ON THE SAME SOCKET AS REPLIES, AND DROPPING THEM LOSES DATA.
            # A command's reply can be preceded by any number of events, and this loop used to
            # discard every one of them. That is fine while nothing subscribes; it is fatal the
            # moment something does, because the frames arrive between commands and there is no
            # second chance to read them. Buffered instead, for `frames()` below.
            m = msg.get("method")
            if m and m in self._want:
                self._events.append((time.time(), m, msg.get("params", {})))
        raise RuntimeError("%s: timed out" % method)

    def subscribe(self, *methods):
        """Start keeping the named CDP events. Anything not named here is still discarded."""
        self._want.update(methods)

    def pump(self, seconds, poll=None):
        """Read the socket for `seconds`, keeping subscribed events.

        🔴 THE ONLY WAY TO SEE THE FIRST SECOND OF A PAGE. `Page.captureScreenshot` is a COMMAND: it
        has to be scheduled on a main thread that, during a cold start, is busy parsing 2 MB of
        JavaScript and initialising WebGL. MEASURED on this repository: a capture requested at 300 ms
        was delivered at 2,053 ms. Anything that samples by asking is therefore blind over exactly the
        window a startup fault lives in.
        A screencast is the other way round: the browser PUSHES a frame whenever it composites one, so
        the timestamps are the compositor's rather than the harness's. Subscribe to
        'Page.screencastFrame', call `Page.startScreencast`, then pump.
        `poll` is an optional callable run between reads, for interleaving a DOM sample with the
        frames; it is called with the elapsed seconds and its return value is appended to `.polls`.
        """
        end = time.time() + seconds
        while time.time() < end:
            try:
                raw = self.ws.recv(timeout=0.08)
            except TimeoutError:
                raw = None
            except Exception:
                raw = None
            if raw:
                msg = json.loads(raw)
                m = msg.get("method")
                if m and m in self._want:
                    self._events.append((time.time(), m, msg.get("params", {})))
                    # A screencast stalls unless every frame is acknowledged.
                    if m == "Page.screencastFrame":
                        try:
                            self.send("Page.screencastFrameAck",
                                      sessionId=msg["params"]["sessionId"])
                        except Exception:
                            pass
            if poll:
                try:
                    self.polls.append((time.time(), poll(time.time() - (end - seconds))))
                except Exception:
                    pass

    def frames(self, out_dir, t0=None):
        """Write every buffered screencast frame to `out_dir` and return [(ms, path), ...]."""
        import base64 as _b64
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        base = t0 if t0 is not None else (self._events[0][0] if self._events else time.time())
        got = []
        for i, (ts, method, params) in enumerate(self._events):
            if method != "Page.screencastFrame":
                continue
            ms = int(round((ts - base) * 1000))
            path = os.path.join(out_dir, "f%03d_%05dms.png" % (i, ms))
            with open(path, "wb") as f:
                f.write(_b64.b64decode(params["data"]))
            got.append((ms, path))
        return got

    # ---------------------------------------------------------------- page
    def goto(self, url=None, settle=2.5):
        self.send("Page.navigate", url=url or self.url)
        # The load event is not what this harness waits for: several checks here serve a subresource
        # slowly on purpose. Poll readyState and then let the frame settle on the real clock.
        for _ in range(160):
            try:
                # ⚠ `user_gesture=False`: this is a READ, and granting an activation here would leave
                # the page holding a user gesture it never received. testing/verify_audio_unlock.py
                # asserts there is none before its click, and this poll was the thing supplying one.
                if self.eval("document.readyState", user_gesture=False) == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.25)
        time.sleep(settle)

    def eval(self, expr, wait=False, user_gesture=True):
        """Evaluate in the page.

        ⚠ `user_gesture` DEFAULTS TO TRUE AND THAT IS A HAZARD FOR ONE KIND OF CHECK. CDP grants the
        page a user activation for the duration of an evaluate with this set, which is convenient for
        driving a UI and fatal for testing anything gated on activation: a probe that merely READS
        `navigator.userActivation`, or that calls `play()`, would be handed the very permission the
        check exists to prove is absent. Pass `user_gesture=False` for those.
        """
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=bool(wait), userGesture=bool(user_gesture))
        if r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:600])
        return r.get("result", {}).get("value")

    def poll(self, expr, timeout=25.0, step=0.25):
        """Wait until `expr` is truthy. Returns its value, or None on timeout."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                # A read, so no gesture. See the note in `goto`.
                v = self.eval(expr, user_gesture=False)
                if v:
                    return v
            except Exception:
                pass
            time.sleep(step)
        return None

    # ---------------------------------------------------------------- input
    def hover(self, x, y, settle=0.35):
        """A REAL pointer move, which is the only thing that sets `:hover`."""
        self.send("Input.dispatchMouseEvent", type="mouseMoved", x=float(x), y=float(y),
                  button="none", buttons=0, clickCount=0)
        time.sleep(settle)

    def click(self, x, y, settle=0.35):
        for t, b in (("mousePressed", 1), ("mouseReleased", 1)):
            self.send("Input.dispatchMouseEvent", type=t, x=float(x), y=float(y),
                      button="left", buttons=b, clickCount=1)
        time.sleep(settle)

    def key(self, key, settle=0.2):
        """A REAL keypress, which is what makes Chrome grant `:focus-visible`."""
        codes = {"Tab": (9, "Tab", "Tab"), "Escape": (27, "Escape", "Escape"),
                 "Enter": (13, "Enter", "Enter")}
        vk, code, k = codes.get(key, (0, key, key))
        for t in ("rawKeyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", type=t, windowsVirtualKeyCode=vk,
                      nativeVirtualKeyCode=vk, code=code, key=k)
        time.sleep(settle)

    # ---------------------------------------------------------------- output
    def shot(self, path, full=False, clip=None, pad=0):
        """`clip` is a DOMRect-shaped dict {x,y,width,height} -- pass an element's own rect, read from
        the page, and the screenshot is of that element rather than of the whole viewport. `pad`
        widens it, which is how a focus ring drawn OUTSIDE the element's box stays in frame."""
        kw = {"format": "png", "captureBeyondViewport": bool(full)}
        if clip:
            kw["clip"] = {"x": max(0.0, float(clip["x"]) - pad),
                          "y": max(0.0, float(clip["y"]) - pad),
                          "width": float(clip["width"]) + pad * 2,
                          "height": float(clip["height"]) + pad * 2,
                          "scale": 1}
        r = self.send("Page.captureScreenshot", **kw)
        data = base64.b64decode(r["data"])
        with open(path, "wb") as f:
            f.write(data)
        return len(data)
