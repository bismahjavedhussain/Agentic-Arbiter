# -*- coding: utf-8 -*-
"""FETCH AND SAVE A FORTYGUARD `env_params` DAY, so a replay is date-consistent.  PAID, 2,900/call.

WHY THIS EXISTS
    A replay is supposed to be one site, one date, one set of saved FortyGuard responses. It was
    not: every heatmap in the live cache is 2026-08-20, and every environmental response on disk was
    2026-07-22..08-11 or 2026-08-22. So a replay paired a temperature field from one day with
    humidity and air quality from another, and `live.py` had to warn that the gates were real
    FortyGuard values but not that date's air.

    There is no clever fix for that -- the data simply was not bought. This buys it.

WHAT ONE CALL COVERS
    `filter_type: 2` over 00:00-23:00 returns **24 hourly values per field**, so ONE call covers
    every cached heatmap window for that date and every hour a replay could ask for. At 2,900 it is
    cheaper than a single 4,220 heatmap window, which is the whole reason the environmental gates
    are the cheap part of the perception rather than the expensive one.

    ⚠ `env_params` is a POINT call -- latitude and longitude, not a polygon -- so it is per SITE.
    Fetching for Ashburn does nothing for Chicago.

USAGE
    python fetch_env_for_replay.py dryrun --date 2026-08-20 [--metro ashburn]
    python fetch_env_for_replay.py run --date 2026-08-20 --allow-paid
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_key, credits_remaining, submit_poll, banner, verdict, RESULTS, FIXTURES,
                    utc_now, classify_vendor, vendor_rec, vendor_sentence, is_billed)

IA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "INTAKE-ARBITER")
sys.path.insert(0, os.path.join(IA, "src"))
import metros as M                                                        # noqa: E402

ENV_PARAMS_CREDITS = 2_900


def cached_heatmap_dates(metro):
    """Which dates this metro already has a saved heatmap for -- the dates worth matching."""
    d = os.path.join(IA, "data", "live_cache", metro)
    out = set()
    for nm in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if nm.endswith(".json") and len(nm) > 10:
            out.add(nm[:10])
    return sorted(out)


def payload(metro, date):
    clat, clon = M.site_centre(metro)
    return {"latitude": round(clat, 5), "longitude": round(clon, 5),
            # required by the schema, echoed back, never consumed (findings 1.1 / 1.7)
            "temperature": 25.0,
            "date_time": {"start_date": date, "start_time": "00:00",
                          "end_time": "23:00", "filter_type": 2}}


def main(argv):
    mode = (argv[0].lower() if argv and not argv[0].startswith("-") else "dryrun")
    date = next((argv[i + 1] for i, a in enumerate(argv) if a == "--date" and i + 1 < len(argv)),
                None)
    metro = next((argv[i + 1] for i, a in enumerate(argv) if a == "--metro" and i + 1 < len(argv)),
                 "ashburn")
    allow = "--allow-paid" in argv
    if not date:
        print("--date YYYY-MM-DD is required. Dates with a cached heatmap for %s: %s"
              % (metro, ", ".join(cached_heatmap_dates(metro)) or "none"))
        return 2

    clat, clon = M.site_centre(metro)
    banner("ENV FOR REPLAY   %s %s   [%s]" % (metro, date, "PAID" if allow else "dry run"))
    print("   point            : %.5f, %.5f  (this site's committed centre)" % (clat, clon))
    print("   window           : %s 00:00-23:00 site-local, filter_type 2 -> 24 hourly values"
          % date)
    print("   cached heatmaps  : %s" % (", ".join(cached_heatmap_dates(metro)) or "none"))
    print("   cost             : %s credits, one call" % format(ENV_PARAMS_CREDITS, ","))
    if date not in cached_heatmap_dates(metro):
        print("   ⚠ NOTE: %s has no cached heatmap for %s, so this would not make a replay "
              "date-consistent." % (metro, date))
    if mode != "run":
        print("\n   Nothing spent. `run --date %s --allow-paid` makes the call." % date)
        return 0
    if not allow:
        print("\n   --allow-paid not given. Refusing to spend.")
        return 5

    key = load_key()
    before = credits_remaining(key)
    tag = "env_replay_%s_%s" % (metro, date)
    r = submit_poll(key, "env_params", payload(metro, date), tag, require_data=False)
    after = credits_remaining(key)
    locs = ((r.get("result") or {}).get("locations") or [])
    params = (locs[0].get("parameters") if locs else None) or (
        {k: v for k, v in locs[0].items() if isinstance(v, list)} if locs else {})
    n_vals = sum(1 for v in (params or {}).values() if isinstance(v, list) for x in v
                 if x is not None)
    rec = vendor_rec(r, tiles=n_vals)
    cls = classify_vendor(rec)
    print("\n   -> %s" % vendor_sentence(cls, rec))
    print("      %d field(s), %d non-null hourly value(s)" % (len(params or {}), n_vals))
    print("      meter %s -> %s   spent %s" % (format(before, ","), format(after, ","),
                                               format(before - after, ",")))

    # The fixture is saved by `submit_poll` under `tag`; `live.saved_fortyguard_env` finds it by
    # scanning for env-shaped responses and matching the DATE INSIDE, not the filename, so nothing
    # downstream depends on this name. The spend record is what the ledger needs.
    path = os.path.join(RESULTS, "live_env_spend.json")
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        doc = {"purpose": "every paid env_params call, so the spend ledger sees it",
               "endpoint": "env_params", "runs": []}
    doc.setdefault("runs", []).append({
        "requested_day_site_local": date, "metro": metro, "class": cls,
        "credits": max(0, before - after), "activity_id": rec.get("activity_id"),
        "credits_before": before, "credits_after": after,
        "n_fields": len(params or {}), "n_values": n_vals,
        "purpose": "date-matched environmental data so a replay of the %s heatmap is consistent"
                   % date})
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, allow_nan=False)

    ok = n_vals > 0
    verdict(ok,
            "SAVED - %d hourly values for %s at %s. A replay of that date's heatmap now uses "
            "FortyGuard humidity and air quality FROM THE SAME DAY, and the mismatch warning "
            "should disappear on its own rather than being silenced."
            % (n_vals, date, metro),
            "NO DATA - %s returned %s. Nothing saved; the replay keeps its honest mismatch "
            "warning." % (date, cls))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
