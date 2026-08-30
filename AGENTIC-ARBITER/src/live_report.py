# -*- coding: utf-8 -*-
"""LIVE_REPORT -- the downloadable report for ONE live run, built at request time.  ZERO API CALLS.

    from live_report import build_live
    pdf_bytes, meta = build_live(job)          # job is one entry of serve_live.JOBS

--------------------------------------------------------------------------------------------
WHY THIS IS A SEPARATE FILE FROM report.py
--------------------------------------------------------------------------------------------
`report.py` builds the per-site report AT BUILD TIME from the committed artefacts, for one named
configuration, and says so on page 1. It cannot describe a live run: a live run happens after the
build, decides the NEXT hours from a forecast bought seconds ago, and its schedule exists only in the
job that produced it.

So this reads a finished job out of `serve_live.JOBS` and writes a report about that run and nothing
else. The user's instruction was explicit that it "will definitely not be a copy of the replay mode
report", and the two share only the PDF writer.

--------------------------------------------------------------------------------------------
HELVETICA FOR PROSE, COURIER FOR THE TABLE, AND WHY THAT IS SAFE
--------------------------------------------------------------------------------------------
`report.py`'s writer wraps text by arithmetic: every Courier glyph is exactly 600/1000 em, so
`cols_at(size)` is exact. Helvetica is proportional and its metrics are not in this repository.

The resolution is that wrapping HELVETICA text with COURIER's metric is CONSERVATIVE, not wrong.
Helvetica's average advance is around 0.5 em against Courier's 0.6, so a line measured as fitting in
Courier is comfortably narrower once set in Helvetica. Lines come out shorter than the available
width; they can never run past the margin, which is the only failure that matters. `verify()` in
report.py already bounds-checks every placed string, and this file's own verify does the same.

The numeric table stays Courier, and that is not a compromise either: a column of figures wants a
fixed advance so the digits line up, which is exactly what a proportional face will not do.

⚠ TRUE INTER WOULD MEAN EMBEDDING A TRUETYPE FONT BY HAND: a font descriptor, an embedded font file
stream, a /Widths array and the real advance table parsed out of the woff2. That is a rewrite of the
writer's core assumption with a real chance of emitting a subtly corrupt file. Recorded in
CONTEXT/01-STATE.md as a deliberate deferral rather than an oversight.
"""
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import report as R                                                   # noqa: E402


# ============================================================================
# HELVETICA PROSE, wrapped on Helvetica's own metric
# ============================================================================
# 🔴 ONE FORMAT FOR THE HEADER AND THE ROWS, and the wind column is 18 wide rather than 14.
# The header and the rows already shared a format here, spelled out twice; a constant means they
# cannot come apart the way `report.py`'s pair did. The width is the real fix. WIND carried
# "%s deg @ %s m/s", which is up to 18 characters ("250 deg @ 12.3 m/s") in a 14-character field, so
# any row with a bearing OVERFLOWED and shoved RISE, BOUND, DEW PT and MODE two or three columns
# right of their own headings, while a row reading "--" stayed put. MEASURED in the selftest report:
# "10 deg @ 3.1 m/s" is 16 characters and pushed that row 2 columns out of line with the row below
# it. 18 = 3 for the bearing, 7 for " deg @ ", 4 for the speed and 4 for " m/s", so the widest
# possible value now fits its column instead of moving the table.
LIVE_ROW = "%-7s %6s %9s %18s %8s %8s %7s  %s"


def hpara(pdf, text, size=R.BODY_PT, bold=False, x=R.MARGIN, indent=""):
    """A wrapped paragraph in Helvetica, measured in Helvetica.

    🔴 IT USED TO COUNT CHARACTERS AT COURIER'S ADVANCE, and that was wrong in both directions.
    Ordinary prose came out about a quarter short -- MEASURED, lines ending at x=412.93 against
    rules running to 549.60 -- so every paragraph on this page had a column and a half of blank
    paper down its right side that nothing had asked for. And it was not even safe in the other
    direction: "AVAST" is 30.82 pt in Helvetica against 28.20 pt in Courier, so a line of capitals
    was already free to run past the margin unnoticed. `wrap_measured` asks the face itself.
    """
    avail = R.PAGE_W - R.MARGIN - x
    for ln in R.wrap_measured(text, avail, size, "H", bold, indent):
        pdf.line(ln, size, bold, x, face="H")


def num(v, nd=2, dash="--"):
    """A number, or a dash. NEVER a bare None, "nan" or "null" on the page: report.py's verify()
    fails the file if any of those strings reach it, and it is right to."""
    if v is None:
        return dash
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    if f != f:                      # NaN
        return dash
    return ("%%.%df" % nd) % f


def flat(d, prefix=""):
    """Every scalar in a nested dict, as (label, value) pairs.

    🔴 GENERIC ON PURPOSE. The alternative was naming the fields of `result["config"]`,
    `result["spend"]` and `result["summary"]` in this file, and every one of those names would be a
    second place the shape of live.py's output is written down. When live.py adds a field this prints
    it; when it renames one this prints the new name instead of silently dropping the row.
    """
    out = []
    for k, v in (d or {}).items():
        label = ("%s%s" % (prefix, k)).replace("_", " ")
        if isinstance(v, dict):
            out.extend(flat(v, prefix + k + " "))
        elif isinstance(v, (list, tuple)):
            if v and all(isinstance(x, (int, float, str, bool)) for x in v):
                out.append((label, ", ".join(str(x) for x in v[:8])
                            + (" ..." if len(v) > 8 else "")))
            else:
                out.append((label, "%d entr%s" % (len(v), "y" if len(v) == 1 else "ies")))
        elif isinstance(v, bool):
            out.append((label, "yes" if v else "no"))
        elif v is None:
            out.append((label, "--"))
        else:
            out.append((label, str(v)))
    return out


# ============================================================================
# THE REASONING FOR ONE HOUR, derived from that hour's own fields
# ============================================================================
def reason_for(h, limit_c, dp_limit):
    """Why this hour got the mode it got, in words, from the row itself.

    🔴 NOTHING HERE IS A TEMPLATE WITH A GUESS IN IT. Every clause is gated on a field live.py
    actually emitted for this hour, and every number quoted is that hour's own. An hour with no
    forecast says so and claims nothing else: live.py's own comment records that counting a missing
    hour as "blocked by temperature" is a lie about why the agent refused, because `bound` is NaN and
    `NaN <= limit` is False, which silently inflated the temperature bucket.
    """
    if h.get("no_data_reason"):
        return ("No forecast for this hour: %s. The chiller stays on, which is the safe default, and "
                "this hour is NOT counted as blocked by temperature or humidity, because nothing was "
                "measured about either." % h["no_data_reason"])

    bits = []
    if h.get("free_cooling"):
        bits.append("FREE COOLING. Outside air carries the load this hour.")
    else:
        bits.append("MECHANICAL. The chiller runs this hour.")

    b, d = h.get("bound_c"), h.get("dewpoint_c")
    if h.get("gate_dry_ok") is False and b is not None and limit_c is not None:
        bits.append("Temperature gate FAILED: the bound is %s C against a %s C plant limit, over by "
                    "%s C. The bound, not the raw forecast: it is the forecast plus this hour's own "
                    "measured margin of %s C."
                    % (num(b), num(limit_c, 1), num(float(b) - float(limit_c)), num(h.get("margin_c"))))
    elif h.get("gate_dry_ok") and b is not None and limit_c is not None:
        bits.append("Temperature gate passed: bound %s C, under the %s C limit."
                    % (num(b), num(limit_c, 1)))

    if h.get("gate_dewpoint_ok") is False and d is not None and dp_limit is not None:
        bits.append("Dew-point gate FAILED: %s C against a published %s C maximum. That maximum is "
                    "cited, not an invented margin." % (num(d, 1), num(dp_limit, 1)))
    elif h.get("gate_dewpoint_ok") and d is not None and dp_limit is not None:
        bits.append("Dew-point gate passed: %s C, under the %s C maximum." % (num(d, 1), num(dp_limit, 1)))

    if h.get("bearing_refused"):
        bits.append("The plume solver REFUSED this bearing rather than return a rise it cannot stand "
                    "behind, so no free-cooling claim is made for this hour on geometry grounds.")
    elif h.get("rise_c") is not None:
        bits.append("Plume rise at the intake: %s C on this hour's wind (%s deg at %s m/s)."
                    % (num(h.get("rise_c"), 4), num(h.get("bearing_deg"), 0), num(h.get("speed_ms"), 1)))
    return " ".join(bits)


# ============================================================================
# THE REPORT
# ============================================================================
def build_live(job, site_label=None):
    """One finished live job in, (pdf_bytes, meta) out. Raises if the job is not usable."""
    if not isinstance(job, dict) or job.get("state") != "done":
        raise ValueError("live report needs a finished job; this one is state=%r"
                         % (job or {}).get("state"))
    res = job.get("result") or {}
    hours = res.get("hours") or []
    if not hours:
        raise ValueError("the job carries no hours, so there is no schedule to report")

    cfg = res.get("config") or {}
    limit_c = cfg.get("limit_c")
    dp_limit = cfg.get("dewpoint_limit_c", cfg.get("dp_limit_c"))
    site = job.get("site") or res.get("metro") or "this site"
    label = site_label or res.get("metro_label") or site
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p = R.Pdf()

    # ---- page 1: what this is -------------------------------------------------------------------
    p.line("AGENTIC-ARBITER", 19.0, True, face="H")
    p.line("LIVE RUN REPORT", 12.0, True, face="H", rgb=R.RGB_RULE if hasattr(R, "RGB_RULE") else None)
    p.space()
    p.rule("=")
    p.space()
    hpara(p, "This report describes ONE live run and nothing else. The next hours were decided from a "
             "FortyGuard forecast bought at the moment the run started, bounded by the agent's own "
             "measured track record, and scheduled under the plant configuration listed below.")
    p.space()
    hpara(p, "It is NOT the per-site report. That one is generated at build time from saved responses "
             "for one named configuration; this one exists only because this run happened.", bold=True)
    p.space()
    p.field("Site", str(label))
    p.field("Generated", now)
    p.field("Job", str(job.get("id") or job.get("job_id") or "--"))
    p.field("Status", str(res.get("status") or "--"))
    p.field("Hours decided", str(len(hours)))
    if res.get("device"):
        p.field("Solver device", str(res["device"]))
    p.space()

    for section, payload in (("The configuration this run used", cfg),
                             ("What it spent", res.get("spend")),
                             ("Summary", res.get("summary")),
                             ("Margin provenance", res.get("margin_provenance"))):
        rows = flat(payload)
        if not rows:
            continue
        p.heading(section)
        for k, v in rows[:26]:
            p.field(k[:1].upper() + k[1:], v)
        p.space()

    if res.get("operator_message"):
        p.heading("What the agent says to the operator")
        hpara(p, str(res["operator_message"]))
        p.space()

    # ---- the schedule, as a fixed-width table ---------------------------------------------------
    p.heading("The schedule, hour by hour")
    hpara(p, "Courier below, because a column of figures wants a fixed advance so the digits line up.")
    p.space()
    head = (LIVE_ROW
            % ("HOUR", "LEAD", "AMBIENT", "WIND", "RISE", "BOUND", "DEW PT", "MODE"))
    p.line(head, R.BODY_PT, True)
    p.rule("-")
    for h in hours:
        mode = ("free" if h.get("free_cooling") else
                ("no data" if h.get("no_data_reason") else "mechanical"))
        wind = ("%s deg @ %s m/s" % (num(h.get("bearing_deg"), 0), num(h.get("speed_ms"), 1))
                if h.get("bearing_deg") is not None else "--")
        p.line(LIVE_ROW
               % (str(h.get("hour_site_local") or "--")[:7],
                  ("+%s h" % num(h.get("lead_h"), 1)) if h.get("lead_h") is not None else "--",
                  num(h.get("ambient_c")), wind, num(h.get("rise_c"), 4),
                  num(h.get("bound_c")), num(h.get("dewpoint_c"), 1), mode))
    p.space()
    n_free = sum(1 for h in hours if h.get("free_cooling"))
    n_nodata = sum(1 for h in hours if h.get("no_data_reason"))
    p.line("%d of %d hour(s) free cooling, %d with no forecast."
           % (n_free, len(hours), n_nodata), R.BODY_PT, True)
    p.space()

    # ---- THE REASONING, HOUR BY HOUR, which is what was asked for --------------------------------
    p.heading("The reasoning, hour by hour")
    hpara(p, "One paragraph per hour, derived from that hour's own measured fields. No hour is "
             "described by a template that outran its data: an hour with no forecast says so and "
             "claims nothing else.")
    p.space()
    for h in hours:
        p.line("%s   (lead %s h, hour %s of %d)"
               % (str(h.get("hour_site_local") or "--"),
                  num(h.get("lead_h"), 1), str(h.get("hour_index") or "?"), len(hours)),
               R.BODY_PT, True, face="H")
        hpara(p, reason_for(h, limit_c, dp_limit), x=R.MARGIN + 2 * R.char_width(R.BODY_PT))
        p.space()

    # ---- the seven stages, as they streamed -----------------------------------------------------
    prog = job.get("progress") or []
    if prog:
        p.heading("The seven stages, as they ran")
        for ev in prog[:70]:
            name = str(ev.get("stage_name") or ev.get("stage") or "").upper()
            txt = str(ev.get("text") or ev.get("msg") or "").strip()
            if not txt:
                continue
            at = ev.get("at_s")
            p.line("%-12s %s" % (name[:12], ("+%.1fs" % at) if isinstance(at, (int, float)) else ""),
                   R.BODY_PT, True)
            hpara(p, txt, x=R.MARGIN + 2 * R.char_width(R.BODY_PT))
        p.space()

    # ---- what this report is not -----------------------------------------------------------------
    p.heading("Limits of this report")
    for s in (
        "It describes the hours listed above and no others. A live run decides the NEXT hours; it "
        "does not restate the five-year backtest, which is in the per-site report.",
        "The margin applied here was calibrated on day-pairs measured at their own leads. Where this "
        "run's leads fall outside that domain the report says so in the margin provenance above, and "
        "coverage measured in one lead cell is not a guarantee in another.",
        "An hour with no forecast is scheduled mechanical, which is the safe default, and is excluded "
        "from the blocked counts rather than attributed to a gate that never saw data.",
    ):
        hpara(p, s, indent="  ")
        p.space(0.4)

    # Measured while the placements are still in hand, and carried out through `meta` so the one
    # named verifier reports it alongside everything else.
    overflow = p.overflows()
    data = p.bytes()
    meta = {
        "site": str(site), "label": str(label), "hours": len(hours),
        "free": n_free, "no_data": n_nodata, "status": res.get("status"),
        "generated": now, "overflow": overflow,
    }
    return data, meta


def verify_live(data, meta):
    """Read the PDF back and assert the run is really in it. Returns a list of problems."""
    bad = []
    try:
        import pypdf
    except ImportError:
        return ["pypdf not available, so the file was not read back"]
    try:
        r = pypdf.PdfReader(io.BytesIO(data))
        txt = "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception as e:                                            # noqa: BLE001
        return ["the file this wrote could not be reopened: %s" % e]

    bad.extend(meta.get("overflow") or [])
    if "LIVE RUN REPORT" not in txt:
        bad.append("the title is missing")
    if str(meta["label"]).split(",")[0] not in txt:
        bad.append("the site name is missing")
    # 🔴 CASE-INSENSITIVE, because Pdf.heading() UPPERCASES its argument. The first version of this
    # check looked for "The reasoning, hour by hour" and failed against the "THE REASONING, HOUR BY
    # HOUR" that is actually on the page. The section was there the whole time.
    if "the reasoning, hour by hour" not in txt.lower():
        bad.append("the reasoning section is missing")

    # 🔴 WORD BOUNDARIES, NOT SUBSTRINGS, and this one was a genuine false positive.
    # `"nan" in txt` fired on the word "provenance": p-r-o-v-e-NAN-c-e. The check exists to catch a
    # field that reached the page unformatted, which means a STANDALONE token, so that is what it
    # now tests. A substring test on a three-letter word against English prose was always going to
    # do this; it only surfaced because this report prints a section called "margin provenance".
    import re as _re
    for token in ("nan", "None", "null", "undefined", "NaN"):
        if _re.search(r"(?<![A-Za-z0-9_])" + _re.escape(token) + r"(?![A-Za-z0-9_])", txt):
            bad.append("the page contains the bare token %r, so a field reached it unformatted"
                       % token)
    return bad


def selftest():
    """Build a report from a synthetic job and read it back. No artefacts, no network."""
    job = {
        "state": "done", "id": "selftest", "site": "ashburn",
        "progress": [{"stage_name": "perceive", "text": "read the field", "at_s": 0.4},
                     {"stage_name": "bound", "text": "bounded from residuals", "at_s": 1.2}],
        "result": {
            "status": "ok_partial", "device": "cpu", "metro_label": "Ashburn, Virginia",
            "config": {"limit_c": 18.0, "dewpoint_limit_c": 15.0, "notice_h": 3},
            "spend": {"credits": 2900, "calls": 1},
            "summary": {"free_hours": 0, "of_hours": 3},
            "hours": [
                {"hour_site_local": "18:00", "lead_h": 0.5, "hour_index": 1, "ambient_c": 31.55,
                 "bearing_deg": 10.0, "speed_ms": 3.1, "rise_c": 0.0, "margin_c": 0.15,
                 "bound_c": 31.70, "dewpoint_c": 22.4, "bearing_refused": False,
                 "gate_dry_ok": False, "gate_dewpoint_ok": False, "free_cooling": False,
                 "no_data_reason": None},
                {"hour_site_local": "19:00", "lead_h": 1.5, "hour_index": 2, "ambient_c": None,
                 "bearing_deg": None, "speed_ms": None, "rise_c": 0.001, "margin_c": 0.15,
                 "bound_c": None, "dewpoint_c": None, "bearing_refused": False,
                 "gate_dry_ok": False, "gate_dewpoint_ok": False, "free_cooling": False,
                 "no_data_reason": "vendor returned no field (submit_rejected)"},
                {"hour_site_local": "20:00", "lead_h": 2.5, "hour_index": 3, "ambient_c": 14.2,
                 "bearing_deg": 250.0, "speed_ms": 2.1, "rise_c": 0.02, "margin_c": 0.2,
                 "bound_c": 14.9, "dewpoint_c": 9.4, "bearing_refused": False,
                 "gate_dry_ok": True, "gate_dewpoint_ok": True, "free_cooling": True,
                 "no_data_reason": None},
            ],
        },
    }
    data, meta = build_live(job)
    problems = verify_live(data, meta)
    print("   built %d bytes, %d hours, %d free, %d with no forecast"
          % (len(data), meta["hours"], meta["free"], meta["no_data"]))
    for b in problems:
        print("   [FAIL] %s" % b)
    if not problems:
        print("   [ok]   read back clean: title, site, reasoning present, no unformatted fields")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    print(__doc__.strip().split("\n")[0])
    print("   python live_report.py selftest")
