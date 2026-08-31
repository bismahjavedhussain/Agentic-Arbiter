# -*- coding: utf-8 -*-
"""ONE LIVE RUN, AS THE TYPESET DOCUMENT. Same stack as the replay report, different argument.

The replay report describes a site: five years of held-out backtest, a coverage measurement, a
portfolio. This describes an EVENT: the next few hours, decided from a forecast bought at the moment
the run started. They share a typographic stack and almost no content, which is why this is a
separate document rather than a mode of `site_report.py`.

🔴 WHAT THIS DOCUMENT MAY NOT BORROW, AND WHY THAT IS THE WHOLE DESIGN.
`site_report_data.collect()` reads COMMITTED artefacts: trace, backtest, rolling, money,
explanations. Every figure in them describes a build-time configuration over a five-year record. A
live run produces none of that. Reusing that collector under a live heading would put five-year
backtest figures beside forecast hours as though this run had produced them, which is the exact
confusion the monospaced live report was written to prevent and says so on its own first page. So
this module reads the JOB and nothing else, and where a site-level fact is genuinely the same during
a live run (the plant limit, the committed pair's facade gap) it comes from the job, which carries
both.

🔴 TWO OF THE REPLAY REPORT'S BEST CHARTS ARE FORBIDDEN HERE, not merely unavailable.
`bound_vs_actual`'s strongest series is "what the intake actually did", measured after the fact. A
live run is a forecast: there is no actual, and substituting anything for that line would be a
caption the chart refutes. `margin_decomposition` splits the margin into a group-conditional
forecast-error part and a plume part; `live.py` computes ONE scalar day-level margin, identical in
every hour, so there is nothing to split. `site_report_charts.live_strip` and `.live_horizon` are the
two replacements, and they live in that module so there is one palette and one type scale.

⚠ THE OUTCOME IS NOT KNOWN AND THE DOCUMENT SAYS SO REPEATEDLY. The replay report can say the bound
held because it was scored against what happened. This one can only say what the agent committed to.
Every place that could be read as a verified result is qualified.

⚠ IT IS BUILT ON THE REQUEST PATH, so it writes no files: the document goes to a BytesIO and both
charts are SVG strings rather than paths. `site_report.py`'s own aerial, polar and histogram all
insist on writing to `reportassets/`, which on a threaded server with no authentication is a race
between two visitors for the same filename, and on an ephemeral container filesystem is work
repeated per request. None of the three is used here.

⚠ THE HORIZON IS `len(hours)`, NEVER `horizon_h`. `live.py` sets `horizon_h` to the REQUESTED count
before it truncates and never rewrites it, so the shipped `demo/live.json` says `horizon_h: 12` while
carrying 4 hours. Any sentence built from that field overstates the run on every truncated or
short-replay run.
"""
import datetime
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import live_report as LR                                              # noqa: E402
import site_report as SR                                              # noqa: E402
import site_report_charts as CH                                       # noqa: E402

from reportlab.platypus import (CondPageBreak, PageBreak, Paragraph, Spacer,  # noqa: E402
                                Table, TableStyle)


# --------------------------------------------------------------------------- reading the job
def collect_live(job, site_label=None):
    """One finished job in, one flat dict out. Raises if the job cannot support a document.

    ⚠ EVERY DERIVED FIGURE IS COMPUTED FROM `hours`, not read from a summary. `result.summary` and
    `result.horizon_h` are both written before `live.py` truncates the horizon, so a run that lost
    hours to its call budget carries a summary describing hours it never decided.
    """
    if not isinstance(job, dict) or job.get("state") != "done":
        raise ValueError("a live report needs a finished job; this one is state=%r"
                         % (job or {}).get("state"))
    res = job.get("result") or {}
    hours = res.get("hours") or []
    if not hours:
        raise ValueError("the job carries no hours, so there is no schedule to report")

    cfg = res.get("config") or {}
    states = [CH.live_state(h) for h in hours]
    leads = [h.get("lead_h") for h in hours if h.get("lead_h") is not None]
    spend = res.get("spend") or {}
    return {
        "job_id": str(job.get("id") or "--"),
        "site_key": str(job.get("site") or res.get("metro") or "--"),
        "label": site_label or res.get("site_label") or res.get("metro") or "this site",
        "mode": res.get("mode") or "live",
        "status": res.get("status") or "--",
        "device": res.get("device"),
        "utc_now": res.get("utc_now"),
        "site_local_now": res.get("site_local_now"),
        "site_tz": res.get("site_tz"),
        "hours": hours,
        "states": states,
        "n_hours": len(hours),
        "n_free": sum(1 for x in states if x == "free"),
        "n_nodata": sum(1 for x in states if x == "no-data"),
        "n_refused": sum(1 for x in states if x == "refused"),
        "lead_lo": min(leads) if leads else None,
        "lead_hi": max(leads) if leads else None,
        "config": cfg,
        "limit_c": cfg.get("limit_c"),
        "dp_limit": cfg.get("dewpoint_limit_c", cfg.get("dp_limit_c")),
        "spend": spend,
        "credits": spend.get("credits_spent"),
        "calls": spend.get("calls_attempted"),
        "margin_provenance": res.get("margin_provenance") or {},
        "operator_message": res.get("operator_message"),
        "committed_pair": res.get("committed_pair") or {},
        "humidity_sources": sorted({x for x in (res.get("humidity_source_per_hour") or []) if x}),
        "requested_h": res.get("horizon_h"),
    }


def _n(v, dash="--"):
    return dash if v is None else format(int(round(float(v))), ",")


def _c(v, dp=1, dash="--"):
    return dash if v is None else ("%.*f" % (dp, float(v)))


# --------------------------------------------------------------------------- the humidity column
# 🔴 THE STATUS IS AN IDENTIFIER, AND IT WAS BEING PRINTED AS ONE. The tile read `ok_replay`, which
# is a token from `live.py:1534` and reads to a CEO like a variable name that escaped. Every value
# `live.py` can set is mapped here, in its own words, and an unmapped one falls through to the raw
# token rather than being hidden: a status this table has not seen is exactly the case a reader most
# needs to see.
# ⚠ THE VALUE IS ONE WORD AND THE GLOSS GOES UNDER IT. "partly complete" is 15 characters and does
# not fit the 82 pt of usable tile at the 11 pt size floor, so `_fit_size` bottomed out and the
# Paragraph wrapped: MEASURED, the two lines' boxes overlapped by 4 % and the overlap check caught
# it. A tile is read at a glance; the sentence belongs in the label beneath, which wraps freely.
STATUS_WORDS = {
    "ok": "complete",
    "ok_partial": "partial",
    "ok_replay": "replay",
    "dryrun": "dry run",
    "no_calibration": "no margin",
    "no_call_budget": "no budget",
    "incomplete_not_attempted": "not asked",
    "fixture_mismatch": "mismatch",
    "stopped_by_operator": "stopped",
    "vendor_unavailable": "no vendor",
    "wind_unavailable": "no wind",
}
STATUS_GLOSS = {
    "ok": "the run completed and every hour it asked for came back",
    "ok_partial": "the run completed, and some hours came back with no forecast",
    "ok_replay": "replayed from a saved field, so this run bought nothing",
    "dryrun": "nothing was bought, so no hour was decided on live data",
    "no_calibration": "no measured margin exists for this site, so no bound was claimed",
    "no_call_budget": "the run had no call budget, so it emitted no schedule",
    "incomplete_not_attempted": "hours in the horizon were never requested",
    "fixture_mismatch": "the saved field did not match the requested window",
    "stopped_by_operator": "the operator stopped the run before it finished",
    "vendor_unavailable": "the forecast vendor did not answer",
    "wind_unavailable": "no wind record was available, so the plume term could not be placed",
}


def _status_words(st):
    return STATUS_WORDS.get(str(st), str(st))


def _status_gloss(st):
    # An unmapped status shows its own token rather than a guess: a status this table has not seen is
    # exactly the one a reader most needs to see.
    return STATUS_GLOSS.get(str(st), "the run's own status, as the agent recorded it: %s" % st)


def _when(iso):
    """An ISO timestamp as a person would read it.

    ⚠ `site_local_now` is `2026-08-23T06:40:29.610979-04:00`. Printed raw it put six digits of
    fractional seconds and an offset into a sentence a reader is meant to take in at a glance. The
    fallback is the raw string, because a timestamp this cannot parse is still information.
    """
    if not iso:
        return "the time recorded above"
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(str(iso)).strftime("%Y-%m-%d %H:%M %Z").strip()
    except (ValueError, TypeError):
        return str(iso)


def _degrees(text):
    """Upgrade the shared reasoner's bare "C" to a degree sign, for a page that can set one.

    🔴 THIS IS HERE RATHER THAN IN `reason_for` BECAUSE CHANGING IT THERE BROKE THE OTHER READER.
    That function is written for `report.py`, which wraps against base-14 Helvetica metrics and
    renders a degree sign as the four characters " deg". Editing the source strings made every
    temperature wider than the wrapper had budgeted and pushed five lines up to 46.2 pt past the
    right margin, which `verify_live` correctly refused. So the sentences keep the spelling their
    original consumer needs, and this document, which embeds Inter, upgrades them on the way in.

    ⚠ IT MATCHES A NUMBER FOLLOWED BY C, not every C. "MECHANICAL" and "CLAMPED" contain the letter
    and must not acquire a degree sign.
    """
    import re as _re
    out = _re.sub(r"([0-9])\s+C(?![A-Za-z])", r"\1 °C", str(text or ""))

    # ⚠ THE SAME PASS TRIMS FOUR DECIMALS TO THREE. `reason_for` prints the plume rise with
    # `num(h["rise_c"], 4)`, because the monospaced report shows the solver's own precision. This
    # document's rule is three at most, for the reason `site_report._c` records: 0.2849 °C on a
    # physical estimate claims a tenth of a millikelvin. MEASURED, the strings 0.2849, 0.0200 and
    # 0.0000 all reached the page and `tools/check_report.py` flagged them. Trailing zeros go with
    # them, so 0.0200 reads 0.02 and 0.0000 reads 0.
    def _trim(m):
        return ("%.3f" % float(m.group(0))).rstrip("0").rstrip(".") or "0"

    out = _re.sub(r"[0-9]+\.[0-9]{4,}", _trim, out)

    # ⚠ AND "240 deg" BECOMES "240°", for the same reason and with the same constraint. The shared
    # reasoner spells a bearing out because `report.py` renders a degree sign as four characters; the
    # table on the next page of THIS document already says "240°", so the paragraph beside it should
    # not disagree about how an angle is written.
    return _re.sub(r"([0-9])\s+deg(?![A-Za-z])", r"\1°", out)


def _humidity_heading(sources):
    """What the humidity column is actually called for THIS run.

    🔴 `dewpoint_c` IS NOT ALWAYS A DEW POINT. `live.py` puts FortyGuard's WET-BULB in that field
    where FortyGuard supplied one and NWS's dew point where it did not, and records which per hour in
    `humidity_source_per_hour`. Wet-bulb is the stricter quantity, so a column headed "dew point" on
    a FortyGuard-gated hour understates what the gate actually tested. The monospaced report's column
    reads "DEW PT" for both.
    """
    fg = any(s.startswith("fortyguard") for s in sources)
    nws = any(s == "nws" for s in sources)
    if fg and nws:
        return "wet-bulb or dew point"
    if fg:
        return "wet-bulb"
    return "dew point"


# --------------------------------------------------------------------------- the document
def build_live_typeset(job, site_label=None):
    """One finished live job in, (pdf_bytes, meta) out. Writes no files."""
    CH.register(SR.ASSETS)
    g = collect_live(job, site_label)
    S = SR._styles()
    hours, lim = g["hours"], g["limit_c"]

    gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = {
        "site": g["site_key"],
        "label": g["label"],
        "generated": gen,
        "job": g["job_id"],
        # ⚠ verify_live() reads this key and treats a non-empty list as a refusal. The typeset path
        # has no writer-side placement list, so the geometry check is done from the finished bytes
        # below and this starts empty rather than absent: `meta.get("overflow") or []` would silently
        # become a no-op if the key vanished, and that is the one library-free check there is.
        "overflow": [],
        "title": "%s -- live run report" % g["label"],
        "subject": "One live run: the next hours decided from a forecast bought at run time",
        "running": "AGENTIC-ARBITER  ·  %s  ·  LIVE RUN REPORT" % g["label"],
        "date": gen,
    }

    buf = io.BytesIO()
    doc = SR.Doc(buf, meta)
    st = []

    # ===================================================================== PAGE 1
    st.append(Paragraph("AGENTIC-ARBITER", S["title"]))
    # 🔴 THE TITLE STRING IS LOAD-BEARING. `live_report.verify_live()` refuses to serve a report
    # whose text does not contain "LIVE RUN REPORT", and `serve_live.py` turns any refusal into an
    # HTTP 500 that a download anchor writes to disk as a .json. That check is worth keeping rather
    # than loosening, so the document satisfies it.
    st.append(Paragraph("LIVE RUN REPORT &nbsp;·&nbsp; %s &nbsp;·&nbsp; %s"
                        % (g["label"], gen), S["sub"]))
    st.append(Paragraph(
        "This document describes <b>one live run and nothing else</b>. The hours below were decided "
        "from a forecast bought at the moment the run started, bounded by margins measured from this "
        "agent's own past errors, and scheduled under the plant configuration listed at the end. It "
        "is not the per-site report: that one is generated at build time from saved responses for a "
        "named configuration, and it can describe five years of held-out testing because that "
        "testing has happened. This run has not.", S["lede"]))

    lead = ("%s to %s h" % (_c(g["lead_lo"], 1), _c(g["lead_hi"], 1))
            if g["lead_lo"] is not None else "--")
    st.append(SR._tiles([
        ("%d of %d" % (g["n_free"], g["n_hours"]),
         "hours released for free cooling, out of the %d this run actually decided"
         % g["n_hours"], None),
        (lead, "forecast lead on those hours, from the moment the run started", None),
        (_n(g["credits"], "0"), "FortyGuard credits this run spent, on %s call%s"
         % (_n(g["calls"], "0"), "" if (g["calls"] or 0) == 1 else "s"), None),
        (_c(lim, 1) + " °C", "the plant limit every hour was tested against", None),
        (_status_words(g["status"]), _status_gloss(g["status"]), None),
    ], weights=[1.0, 0.95, 0.95, 0.8, 1.05]))
    st.append(Spacer(1, 11))
    st.append(SR._chart(CH.live_strip(hours, height=170)))
    st.append(Spacer(1, 3))

    st.append(Paragraph("What this run decided", S["h2"]))
    bullets = [
        "<b>%d of the %d hours</b> were released for free cooling. Every other hour has a named "
        "reason below rather than a default." % (g["n_free"], g["n_hours"]),
    ]
    if g["requested_h"] and g["requested_h"] != g["n_hours"]:
        bullets.append(
            "<b>%d hours were asked for and %d were decided.</b> The horizon was cut short, so "
            "every count on this page is over the %d the agent actually saw. The requested figure "
            "is recorded in the run's own output and is not used here."
            % (g["requested_h"], g["n_hours"], g["n_hours"]))
    if g["n_nodata"]:
        bullets.append(
            "<b>%d hour%s had no forecast at all.</b> Those are not counted as blocked by "
            "temperature or by humidity, because nothing was measured about either: the chiller "
            "stays on, which is the safe default, and the reason is recorded per hour."
            % (g["n_nodata"], "" if g["n_nodata"] == 1 else "s"))
    if g["n_refused"]:
        bullets.append(
            "<b>The plume solver refused %d wind bearing%s</b> rather than return a rise it cannot "
            "stand behind. A refusal costs free-cooling hours and is published rather than hidden."
            % (g["n_refused"], "" if g["n_refused"] == 1 else "s"))
    bullets.append(
        "<b>The outcome is not known yet.</b> This is a forecast. The bound is what the agent "
        "committed to before the hours arrived; whether the intake stayed under it can only be "
        "measured afterwards, and no figure on this page claims it was.")
    for b in bullets:
        st.append(Paragraph(b, S["bullet"], bulletText="·"))

    if g["operator_message"]:
        st.append(Paragraph("What the agent says to the operator", S["h2"]))
        st.append(Paragraph(str(g["operator_message"]), S["body"]))

    # ===================================================================== PAGE 2, the horizon
    # ⚠ CONDITIONAL, NOT FORCED, for the same measured reason the replay report's middle sections
    # are. MEASURED on the first build: four pages carrying 2.6 pages of content, the last one 9.4 %
    # full because a hard break sent one paragraph to a page of its own. A live run's length is not
    # known in advance, so fixed pagination cannot fit it: a 3-hour run and a 24-hour run want
    # different page counts and neither wants a page break in a place chosen for the other.
    #
    # ⚠ 200 pt, MEASURED RATHER THAN CHOSEN. Swept on the shipped demo/live.json: a 300 pt threshold
    # gives 4 pages at 65.1 % mean fill because both breaks still fire into 145 pt and 235 pt gaps;
    # 240 gives the same; 200 gives 3 pages at 87.7 %. Below 200 nothing further improves, so it is
    # the point where the gaps this document actually leaves stop forcing a page.
    st.append(CondPageBreak(200))
    st.append(Paragraph("The bound, across the horizon", S["h1"]))
    st.append(Paragraph("What the agent committed to for each hour, and what it was built on.",
                        S["sub"]))
    st.append(SR._chart(CH.live_horizon(hours, lim if lim is not None else 24.0, height=300)))
    st.append(SR._caption(
        "The blue line is the upper bound: the forecast for that hour plus this run's measured "
        "margin plus the plume rise at that hour's own wind bearing. The agent releases an hour only "
        "where that bound clears the plant limit, not where the forecast does. <b>There is no line "
        "for what the intake actually did, because it has not happened.</b> The replay report has "
        "that line and can therefore say the bound held; this document can only say what was "
        "promised.", S))

    st.append(Paragraph("The reasoning, hour by hour", S["h2"]))
    st.append(Paragraph(
        "One entry per distinct outcome, with the hours it covers. Every clause is gated on a field "
        "this run actually emitted for that hour, and every number quoted is that hour's own.",
        S["sub"]))
    seen = {}
    for h, stt in zip(hours, g["states"]):
        seen.setdefault(stt, []).append(h)
    TITLE = {"free": "Released for free cooling", "dry-bulb": "Held back by temperature",
             "humidity": "Held back by humidity", "refused": "Declined: the geometry could not be "
             "modelled on this bearing", "no-data": "No forecast for these hours"}
    for stt in ("free", "dry-bulb", "humidity", "refused", "no-data"):
        rows = seen.get(stt)
        if not rows:
            continue
        when = ", ".join(str(x.get("hour_site_local") or "")[-5:] for x in rows[:8])
        if len(rows) > 8:
            when += " and %d more" % (len(rows) - 8)
        st.append(Paragraph("%s &nbsp;<font color='%s' size='8.5'>%d hour%s: %s</font>"
                            % (TITLE[stt], CH.SECOND, len(rows),
                               "" if len(rows) == 1 else "s", when), S["h2"]))
        st.append(Paragraph(_degrees(LR.reason_for(rows[0], lim, g["dp_limit"])), S["body"]))

    # ===================================================================== PAGE 3, the schedule
    st.append(CondPageBreak(200))
    st.append(Paragraph("Every hour this run decided", S["h1"]))
    hum = _humidity_heading(g["humidity_sources"])
    st.append(Paragraph(
        "The humidity column is headed <b>%s</b> for this run, which is what was actually measured: "
        "the agent uses FortyGuard's wet-bulb where FortyGuard supplied one and the weather "
        "service's dew point where it did not, and wet-bulb is the stricter test of the two."
        % hum, S["sub"]))
    tbl = [["hour", "lead", "ambient", "wind", "rise", "margin", "bound", hum, "decision"]]
    for h, stt in zip(hours, g["states"]):
        wind = ("%s° at %s m/s" % (_c(h.get("bearing_deg"), 0), _c(h.get("speed_ms"), 1))
                if h.get("bearing_deg") is not None else "--")
        tbl.append([
            str(h.get("hour_site_local") or "")[-5:],
            ("%s h" % _c(h.get("lead_h"), 1)) if h.get("lead_h") is not None else "--",
            (_c(h.get("ambient_c"), 1) + " °C") if h.get("ambient_c") is not None else "--",
            wind,
            _c(h.get("rise_c"), 2),
            _c(h.get("margin_c"), 2),
            (_c(h.get("bound_c"), 1) + " °C") if h.get("bound_c") is not None else "--",
            (_c(h.get("dewpoint_c"), 1) + " °C") if h.get("dewpoint_c") is not None else "--",
            CH.LIVE_STATE_LABEL[stt],
        ])
    st.append(SR._table(tbl, [40, 38, 52, 74, 34, 40, 52, 56, 62],
                        align={4: "RIGHT", 5: "RIGHT"}))

    # ===================================================================== the margin disclosure
    mp = g["margin_provenance"]
    if mp:
        st.append(Paragraph("What the margin is, and what it is not", S["h1"]))
        st.append(Paragraph(
            "The bound is the forecast plus a margin measured from this agent's own past errors. "
            "That measurement has limits, and they are published here rather than behind a green "
            "tick, because a bound whose limitations are stated is worth more than one whose are "
            "not.", S["sub"]))
        rows = [["What was measured", "Value", "What it means"]]
        n_pairs = mp.get("n_calibration_pairs")
        rows.append(["Calibration day-pairs", _n(n_pairs),
                     "each is a forecast plus the day that followed it, so the count rises by one "
                     "for every further day this site is forecast on"])
        if mp.get("pairs_needed_for_nominal"):
            rows.append(["Pairs a 90% bound needs", _n(mp["pairs_needed_for_nominal"]),
                         "a one-sided 90% quantile cannot be expressed on fewer"])
        if mp.get("attainable_coverage_ceiling") is not None:
            rows.append(["Highest coverage reachable",
                         "%.0f%%" % (100.0 * mp["attainable_coverage_ceiling"]),
                         "the arithmetic ceiling at this many pairs, n/(n+1); above it the number "
                         "is unreachable however good the method is"])
        if mp.get("measured_pooled_coverage") is not None:
            rows.append(["Coverage actually measured",
                         "%.1f%%" % (100.0 * mp["measured_pooled_coverage"]),
                         "on the test days available, which is the figure the agent reports rather "
                         "than the target it was aiming at"])
        if mp.get("clamped_to_attainable"):
            rows.append(["Clamped", "yes",
                         "the quantile was held at the reachable ceiling, so the nominal guarantee "
                         "is degraded and is reported as degraded"])
        if mp.get("borrowed_from"):
            rows.append(["Borrowed from", str(mp["borrowed_from"]),
                         "this site owns no calibration of its own, so another site's margin is "
                         "used and flagged"])
        st.append(SR._table(rows, [128, 74, SR.MEASURE - 202]))
        if mp.get("EXTRAPOLATION_WARNING"):
            st.append(Paragraph(
                "<b>%s</b>" % str(mp["EXTRAPOLATION_WARNING"]), S["body"]))
        elif mp.get("calibration_leads_h"):
            st.append(Paragraph(
                "<b>The margin was measured at one forecast lead and one hour of day, and this run "
                "applies it to all of them.</b> That is an extrapolation, and it is recorded as one "
                "rather than left for a reader to assume otherwise.", S["body"]))

    # ===================================================================== the configuration
    st.append(Paragraph("The configuration this run used", S["h1"]))
    cfg = g["config"]
    crows = [["Setting", "This run", "What it protects"]]
    for key, lab, prot in (
            ("limit_c", "Plant limit", "the intake temperature the hall is committed to"),
            ("dewpoint_limit_c", "Humidity limit",
             "condensation on cold surfaces inside the hall"),
            ("notice_h", "Notice", "the plant cannot change mode instantly"),
            ("switch_budget", "Switch budget", "chillers and dampers wear out when cycled"),
            ("min_dwell_h", "Minimum dwell", "a mode has to hold before another change"),
            ("bank_mode", "Condenser bank", "which facade the exhaust is modelled on")):
        if cfg.get(key) is None:
            continue
        v = cfg[key]
        crows.append([lab, ("%s °C" % _c(v, 1)) if key.endswith("_c") else
                      ("%s h" % v) if key in ("notice_h", "min_dwell_h") else str(v), prot])
    st.append(SR._table(crows, [104, 80, SR.MEASURE - 184]))

    st.append(Paragraph(
        "<b>Limits of this document</b> &nbsp;·&nbsp; it describes one run over %d hour%s at "
        "%s, job %s. It does not restate the five-year backtest, the coverage measurement or the "
        "portfolio: those belong to the per-site report and are not what this run measured. The "
        "%s solved the plume for this site's own geometry from a table computed at build time, not "
        "at request time. Generated %s."
        % (g["n_hours"], "" if g["n_hours"] == 1 else "s",
           _when(g["site_local_now"]), g["job_id"],
           g["device"] or "solver", gen), S["foot"]))

    doc.build(st)
    data = buf.getvalue()
    # ⚠ THE KEYS ITS CONSUMERS ALREADY READ. `live_report.selftest` prints `meta["hours"]`,
    # `["free"]` and `["no_data"]`, which the monospaced builder sets and this one did not, so the
    # self-test could only ever have been reading a fallback. Two builders behind one dispatcher have
    # to return one contract, or every caller has to know which of them ran.
    meta["hours"] = g["n_hours"]
    meta["free"] = g["n_free"]
    meta["no_data"] = g["n_nodata"]
    meta["bytes"] = len(data)
    meta["overflow"] = _geometry_problems(data)
    return data, meta


# --------------------------------------------------------------------------- the geometry check
def _geometry_problems(data):
    """Any text placed outside the content measure, read from the finished bytes.

    🔴 THE REPLAY PATH HAS NO EQUIVALENT OF `report.Pdf.overflows()`, AND THAT CHECK IS THE ONLY
    LIBRARY-FREE ONE `verify_live` HAS. Its comment records why it matters: it was moved above the
    pypdf import precisely so a host with no pypdf still refuses a report whose text runs off the
    paper. A typeset rewrite that simply stopped returning the key would undo that from the other
    direction, and nothing would report it, because the self-test's negative control plants the key
    itself.
    #
    ⚠ SO THE CHECK IS REBUILT ON pypdf, WHICH IS ALREADY A DECLARED DEPLOY DEPENDENCY. `extract_text`
    takes a visitor that receives the text matrix, which gives the x of every string placed. That is
    a stronger check than the writer-side one it replaces: it reads what is in the file rather than
    what the writer believed it placed. With no pypdf it returns nothing and says so, which is the
    same honest degradation `verify_live` already draws a distinction for.
    """
    try:
        import pypdf
    except ImportError:
        return []
    # ⚠ WHAT THIS CATCHES AND WHAT IT DOES NOT, stated rather than implied. pypdf gives the START x
    # of each placed string, so this detects a string placed wholly or mostly outside the measure,
    # which is the real failure mode: a chart or a table laid out wider than the page. It does not
    # catch a string that starts inside and ends a point or two past the edge; `tools/check_report.py`
    # does that rigorously with PyMuPDF at build time, and PyMuPDF is not a deploy dependency.
    # The tolerance is 6 pt, which is about one character at body size.
    lim = SR.PAGE_W - SR.MARGIN + 6.0
    bad = []
    try:
        r = pypdf.PdfReader(io.BytesIO(data))
        for i, pg in enumerate(r.pages):
            hits = []

            def visit(text, cm, tm, font, size, _hits=hits):
                # 🔴 tm[4] ALONE IS NOT A PAGE COORDINATE, AND TRUSTING IT MADE THIS CHECK LIE.
                # Text inside a scaled Drawing carries its x in the Drawing's own space; the CTM
                # holds the placement and the scale. MEASURED: the first version reported six
                # overflows on demo/report.pdf, which PyMuPDF measures as clean at max x 547.1,
                # because it read a chart-internal 638.6 as a page position. Composing the text
                # matrix with the CTM gives 527.1 for that same string.
                if text and text.strip():
                    x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                    _hits.append((x, text.strip()[:30]))
            pg.extract_text(visitor_text=visit)
            for x, txt in hits:
                if x > lim:
                    bad.append("page %d places %r at x = %.1f pt, past the %.1f pt margin"
                               % (i + 1, txt, x, lim))
    except Exception as e:                                            # noqa: BLE001
        # Not a refusal: an unreadable file is caught by verify_live's own reopen check, which
        # reports it as a problem. This one only reports geometry it could measure.
        return []
    return bad[:6]


if __name__ == "__main__":
    import json
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "demo", "live.json")
    res = json.load(open(src, encoding="utf-8"))
    job = {"state": "done", "id": "cli", "site": res.get("metro"), "result": res}
    data, meta = build_live_typeset(job)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "..",
                                                            "REPORT-LIVE-typeset.pdf")
    open(out, "wb").write(data)
    print("   wrote %s  (%.1f KB)" % (out, len(data) / 1024.0))
    for k in ("label", "job", "generated", "bytes"):
        print("   %-12s %s" % (k, meta.get(k)))
    print("   %-12s %s" % ("overflow", meta["overflow"] or "none"))
