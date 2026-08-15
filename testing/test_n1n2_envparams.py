# -*- coding: utf-8 -*-
"""N-1 and N-2  ---  PAID.  Three env_params calls, ~8,700 credits nominal.

N-1  Does env_params vary spatially? Every env_params call ever made has been at ONE point.
     If it returns regional values regardless of coordinates, per-site anchoring of wet-bulb /
     solar / air quality is an illusion.
     Smart choice of points: use the HOTTEST and COOLEST tiles from the saved heatmap. If the
     heatmap says they differ by ~1.5 C and env_params says they are identical, that is decisive.

N-2  Is the air-quality data a forecast or a nowcast? Same point, future hour vs past hour.

Control: `elevation` MUST differ between two points. It is a terrain lookup, so if elevation is
identical the coordinates were not honoured at all and the whole test is void.
"""
import json, sys, statistics
from common import (load_field, load_key, credits_remaining, submit_poll, banner,
                    save_result, verdict, hav, assert_non_empty)

PARAMS = ["wet_bulb_temperature_celsius", "relative_humidity_percent",
          "air_quality_o3:idx", "air_quality_pm2p5:idx", "apparent_temperature_celsius"]


def pick_points():
    """Hottest and coolest tiles from the saved day-B field, forced >=2 km apart."""
    f = load_field("DC_2026-07-28")
    if not f:
        return (39.0100, -77.4460, None), (39.0100, -77.3882, None), None
    tiles = [(la, lo, p.get("average_temperature")) for la, lo, p in f
             if p.get("average_temperature") is not None]
    tiles.sort(key=lambda t: t[2])
    cool = tiles[0]
    hot = tiles[-1]
    # if they happen to be close together, take the hottest tile >=2 km from the coolest
    if hav((cool[0], cool[1]), (hot[0], hot[1])) < 2000:
        for t in reversed(tiles):
            if hav((cool[0], cool[1]), (t[0], t[1])) >= 2000:
                hot = t
                break
    return cool, hot, hav((cool[0], cool[1]), (hot[0], hot[1]))


def call_point(key, lat, lon, date, hour, tag):
    payload = {"latitude": round(lat, 5), "longitude": round(lon, 5), "temperature": 25.0,
               "date_time": {"start_date": date, "start_time": hour, "filter_type": 1}}
    r = submit_poll(key, "env_params", payload, tag)
    if not r.get("ok"):
        print("      FAILED: %s" % r.get("error"))
        return None
    ok, why = assert_non_empty(r["result"])
    if not ok:
        print("      EMPTY RESULT: %s" % why)
        return None
    loc = r["result"]["locations"][0]
    p = loc["parameters"]
    g = lambda k: (p.get(k) or [None])[0]
    out = {k: g(k) for k in PARAMS}
    out["elevation"] = loc.get("elevation")
    out["solar_ghi"] = (loc.get("solar_irradiance") or {}).get("clear_sky", {}).get("ghi")
    out["_secs"] = r["secs"]
    return out


def main():
    banner("N-1 / N-2  Does env_params vary in SPACE and in TIME?   [PAID - 3 calls]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))

    cool, hot, sep = pick_points()
    print("\n   points chosen from the saved 17,862-tile field:")
    print("      COOLEST tile  %.5f, %.5f   heatmap says %.4f C" % (cool[0], cool[1], cool[2] or 0))
    print("      HOTTEST tile  %.5f, %.5f   heatmap says %.4f C" % (hot[0], hot[1], hot[2] or 0))
    if sep:
        print("      separation %.0f m   heatmap difference %.4f C" % (sep, (hot[2] - cool[2])))

    print("\n   CALL 1/3  cool point, past hour ...")
    a = call_point(key, cool[0], cool[1], "2026-07-28", "15:00", "n1_cool_past")
    print("   CALL 2/3  hot point, same hour ...")
    b = call_point(key, hot[0], hot[1], "2026-07-28", "15:00", "n1_hot_past")
    print("   CALL 3/3  cool point, FUTURE hour ...")
    c = call_point(key, cool[0], cool[1], "2026-08-10", "20:00", "n2_cool_future")

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER : %s    SPENT: %s" % (format(after, ","), format(before - after, ",")))

    if not (a and b):
        print("\n   N-1 could not run.")
        return 2

    print("\n   --- N-1  SPATIAL VARIATION ---")
    print("   %-34s %12s %12s %10s" % ("parameter", "cool point", "hot point", "diff"))
    diffs = {}
    for k in ["elevation", "solar_ghi"] + PARAMS:
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            d = vb - va
            diffs[k] = d
            print("   %-34s %12.4f %12.4f %10.4f" % (k, va, vb, d))
        else:
            print("   %-34s %12s %12s %10s" % (k, va, vb, "-"))

    elev_differs = abs(diffs.get("elevation", 0)) > 0.5
    varying = [k for k, d in diffs.items() if k != "elevation" and abs(d) > 1e-6]
    print("\n   elevation differs (proves coordinates were honoured): %s" % elev_differs)
    print("   parameters that vary between the two points: %s" % (varying if varying else "NONE"))

    n1_ok = elev_differs and len(varying) >= 2
    verdict(n1_ok,
            "PASS - env_params genuinely varies with location. Per-site anchoring is real.",
            "FAIL - env_params returns regional values. WORKAROUND (already in the design): anchor "
            "humidity/solar regionally and derive local quantities from the 60 m TEMPERATURE field, "
            "which does vary. The solver only needs temperature + wind, so the core is unaffected; "
            "the generator-window layer weakens.")

    n2_ok = None
    if c:
        print("\n   --- N-2  FORECAST OR NOWCAST? ---")
        print("   %-34s %12s %12s" % ("parameter", "past 15:00", "future 20:00"))
        tdiff = []
        for k in ["solar_ghi"] + PARAMS:
            va, vc = a.get(k), c.get(k)
            if isinstance(va, (int, float)) and isinstance(vc, (int, float)):
                print("   %-34s %12.4f %12.4f" % (k, va, vc))
                tdiff.append(abs(vc - va))
        n2_ok = any(d > 1e-6 for d in tdiff)
        verdict(n2_ok,
                "PASS - values differ across time, so env_params serves genuine future estimates.",
                "FAIL - identical across time. Air quality is a nowcast; derive an ozone-formation "
                "index from the temperature forecast instead and label it as derived.")

    save_result("n1n2_envparams.json", {"before": before, "after": after, "spent": before - after,
                                        "cool": {"lat": cool[0], "lon": cool[1], "heatmap_c": cool[2]},
                                        "hot": {"lat": hot[0], "lon": hot[1], "heatmap_c": hot[2]},
                                        "separation_m": sep, "a": a, "b": b, "c": c,
                                        "n1_pass": n1_ok, "n2_pass": n2_ok})
    return 0 if n1_ok else 1


if __name__ == "__main__":
    sys.exit(main())
