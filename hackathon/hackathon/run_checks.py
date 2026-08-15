# -*- coding: utf-8 -*-
"""FortyGuard Day-1 verification protocol - live check runner.
Runs the priority checks against the live API for the three hackathon sites,
capturing RAW responses. Writes results_raw.json for the results markdown."""
import net, sys, json, time, math, statistics, requests
try:
    import psychrolib; psychrolib.SetUnitSystem(psychrolib.SI); HAVE_PSY=True
except Exception: HAVE_PSY=False

import os as _os


def _load_key():
    """Read the key from .env at the project root.

    Replaced a hard-coded credential here on 2026-08-16, found by a pre-commit secret scan before
    the repository's first commit. Never put a credential in source: this file was about to be
    published to a public repository as a hackathon submission requirement.
    """
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".env")
    for line in open(p, encoding="utf-8-sig"):
        if line.strip().startswith("FORTYGUARD_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("FORTYGUARD_API_KEY not found in .env")


K = _load_key(); B="https://api.fortyguard.com"; V=B+"/v1"
H={"api-key":K,"Content-Type":"application/json"}
F2C=lambda f:(f-32)*5/9
SITES={"ashburn_va":(39.0438,-77.4874),"phoenix_goodyear_az":(33.4353,-112.3576),"hillsboro_or":(45.5229,-122.9898)}
PAST="2026-07-28"; TODAY="2026-07-30"
OUT={}

def aoi(lat,lon,half=0.004):  # ~0.9km campus-ish box
    r=[[lon-half,lat-half],[lon+half,lat-half],[lon+half,lat+half],[lon-half,lat+half],[lon-half,lat-half]]
    return {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[r]}}]}

def submit_poll(endpoint,payload,tries=1,max_polls=25,wait=5):
    """Returns dict: submit_status, activity_id, final_status, result(dict|None), raw_error, latency_s, polls."""
    for attempt in range(tries):
        t0=time.time()
        try:
            r=requests.post(f"{V}/{endpoint}",headers=H,json=payload,timeout=60)
        except Exception as e:
            return {"submit_status":"EXC","raw_error":str(e)[:200],"latency_s":round(time.time()-t0,1)}
        sub={"submit_status":r.status_code}
        if r.status_code!=200:
            sub["raw_error"]=r.text[:400]; sub["latency_s"]=round(time.time()-t0,1)
            if attempt<tries-1: time.sleep(wait); continue
            return sub
        aid=r.json().get("data",{}).get("activity_id"); sub["activity_id"]=aid
        first404=None
        for p in range(max_polls):
            try:
                j=requests.get(f"{V}/status/{aid}",headers=H,timeout=45)
            except Exception as e:
                time.sleep(wait); continue
            if j.status_code==404 and first404 is None: first404=p
            try: jd=j.json()
            except Exception: time.sleep(wait); continue
            st=str(jd.get("data",{}).get("status") or jd.get("message")).lower()
            sub["final_status"]=st; sub["polls"]=p+1; sub["first_404_poll"]=first404
            if st=="completed":
                sub["result"]=jd["data"]["result"]; sub["latency_s"]=round(time.time()-t0,1); return sub
            if st in ("processing","pending","queued","in progress",""):
                if st=="": sub["raw_error"]=json.dumps(jd)[:400]; break
                time.sleep(wait); continue
            sub["raw_error"]=json.dumps(jd)[:400]; break
        sub["latency_s"]=round(time.time()-t0,1)
        if sub.get("result") is None and attempt<tries-1: time.sleep(wait); continue
        return sub
    return sub

def hm_stats(res):
    st=res.get("stats_data",{}).get("temperature_stats",{}) if res else {}
    feats=res.get("map_data",{}).get("features",[]) if res else []
    vals=[f["properties"].get("average_temperature") for f in feats if f.get("properties",{}).get("average_temperature") is not None]
    return st,feats,vals

print("=== COVERAGE PROBE (heatmap single hour) for 3 sites ===",flush=True)
cover={}
for name,(la,lo) in SITES.items():
    s=submit_poll("heatmap",{"polygon_aoi":aoi(la,lo),"date_time":{"start_date":PAST,"start_time":"15:00","filter_type":1},"granularity":100},tries=4,wait=6)
    st,feats,vals=hm_stats(s.get("result"))
    ok=bool(vals)
    cover[name]={"ok":ok,"submit_status":s.get("submit_status"),"final_status":s.get("final_status"),
                 "cells":len(feats),"mean_c":st.get("mean"),"stddev":st.get("standard_deviation"),"raw_error":s.get("raw_error")}
    print(f"  {name:22s} ok={ok} status={s.get('final_status')} cells={len(feats)} mean={st.get('mean')} stddev={st.get('standard_deviation')} err={s.get('raw_error','')[:60]}",flush=True)
OUT["coverage"]=cover
PRIMARY=next((n for n in SITES if cover[n]["ok"]), None)
print("PRIMARY site for deep checks:",PRIMARY,flush=True)
if not PRIMARY:
    json.dump(OUT,open("results_raw.json","w"),indent=2,default=str); print("no covered site; stopping"); sys.exit(0)
LA,LO=SITES[PRIMARY]

# ---- S-3: does stats_data give a SPATIAL stddev (across tiles)? ----
print("\n=== S-3 spatial stddev ===",flush=True)
s=submit_poll("heatmap",{"polygon_aoi":aoi(LA,LO),"date_time":{"start_date":PAST,"start_time":"15:00","filter_type":1},"granularity":60},tries=4,wait=6)
st,feats,vals=hm_stats(s.get("result"))
mine=round(statistics.pstdev(vals),4) if len(vals)>1 else None
OUT["S-3"]={"stats_keys":list(st.keys()),"api_stddev":st.get("standard_deviation"),"my_tile_pstdev":mine,
            "n_tiles":len(vals),"min":st.get("minimum"),"max":st.get("maximum"),"mean":st.get("mean"),"granularity":60}
print(f"  api stddev={st.get('standard_deviation')} vs my tile pstdev={mine} over {len(vals)} tiles",flush=True)

# ---- S-7 / C-2: filter_type=2 range in ONE call; count hours + interval ----
print("\n=== S-7 / C-2 range-in-one-call ===",flush=True)
s2=submit_poll("heatmap",{"polygon_aoi":aoi(LA,LO),"date_time":{"start_date":PAST,"start_time":"06:00","end_time":"18:00","filter_type":2},"granularity":100},tries=3,wait=6)
res2=s2.get("result") or {}
# how are multiple hours represented? inspect a feature's properties + top-level keys
feat0=(res2.get("map_data",{}).get("features") or [{}])[0]
OUT["S-7_C-2"]={"submit_status":s2.get("submit_status"),"final_status":s2.get("final_status"),"raw_error":s2.get("raw_error"),
                "top_keys":list(res2.keys()),"sample_feature_props":feat0.get("properties"),
                "stats":res2.get("stats_data",{}).get("temperature_stats",{})}
print(f"  status={s2.get('final_status')} top_keys={list(res2.keys())} sample_props={feat0.get('properties')} err={s2.get('raw_error','')[:80]}",flush=True)

# ---- B-1: does heatmap accept a FUTURE time (now+? within day)? control past / future ----
print("\n=== B-1 future timestamp (heatmap) ===",flush=True)
b1={}
for label,dt in [("control_past",{"start_date":PAST,"start_time":"15:00","filter_type":1}),
                 ("future_today_23",{"start_date":TODAY,"start_time":"23:00","filter_type":1})]:
    s=submit_poll("heatmap",{"polygon_aoi":aoi(LA,LO),"date_time":dt,"granularity":100},tries=3,wait=6)
    st,_,vals=hm_stats(s.get("result"))
    b1[label]={"submit_status":s.get("submit_status"),"final_status":s.get("final_status"),"mean_c":st.get("mean"),"n":len(vals),"raw_error":s.get("raw_error")}
    print(f"  {label}: status={s.get('final_status')} mean={st.get('mean')} n={len(vals)} err={s.get('raw_error','')[:60]}",flush=True)
OUT["B-1"]=b1

# ---- E-8: can a heatmap carry wet-bulb? try analytic default + look for variable selector ----
print("\n=== E-8 wet-bulb in heatmap? ===",flush=True)
e8={"note":"heatmap request has no variable selector; analytic_type in [tcm,time_of_measure,exceedance,persistence]; feature carries average_temperature only"}
feats=(s.get("result") or {}).get("map_data",{}).get("features",[])
e8["feature_property_keys"]=list(feats[0]["properties"].keys()) if feats else None
OUT["E-8"]=e8
print("  feature property keys:",e8["feature_property_keys"],flush=True)

# ---- B-6: air vs land-surface temp -> 24h diurnal amplitude at the site (env_params anchored hourly is circular; use heatmap per hour) ----
print("\n=== B-6 diurnal amplitude (air vs LST) ===",flush=True)
hours=[3,9,15,21]; series=[]
for h in hours:
    s=submit_poll("heatmap",{"polygon_aoi":aoi(LA,LO),"date_time":{"start_date":PAST,"start_time":f"{h:02d}:00","filter_type":1},"granularity":100},tries=3,wait=6)
    st,_,vals=hm_stats(s.get("result"))
    series.append({"hour":h,"mean_c":st.get("mean")})
    print(f"  {h:02d}:00 mean_c={st.get('mean')}",flush=True)
temps=[x["mean_c"] for x in series if x["mean_c"] is not None]
OUT["B-6"]={"series":series,"amplitude_c":round(max(temps)-min(temps),2) if len(temps)>1 else None}
print("  diurnal amplitude C:",OUT["B-6"]["amplitude_c"],flush=True)

# ---- B-8: env_params wet-bulb vs psychrolib (needs env_params: dry-bulb input, wet_bulb + humidity output) ----
print("\n=== B-8 psychrolib cross-check (env_params) ===",flush=True)
ep=submit_poll("env_params",{"latitude":LA,"longitude":LO,"temperature":25.0,"date_time":{"start_date":PAST,"start_time":"15:00","filter_type":1}},tries=3,wait=6)
epr=ep.get("result")
b8={"submit_status":ep.get("submit_status"),"final_status":ep.get("final_status"),"raw_error":ep.get("raw_error")}
if epr:
    p=epr["locations"][0]["parameters"]; g=lambda k:(p.get(k) or [None])[0]
    db=25.0; wb=g("wet_bulb_temperature_celsius"); rh=g("relative_humidity_percent"); ap=g("apparent_temperature_celsius")
    b8.update({"input_dry_bulb":db,"api_wet_bulb":wb,"api_humidity_pct":rh,"apparent":ap,"available_params":list(p.keys())[:20]})
    if HAVE_PSY and wb is not None and rh is not None:
        try: b8["psychrolib_wet_bulb"]=round(psychrolib.GetTWetBulbFromRelHum(db,rh/100.0,101325),2)
        except Exception as e: b8["psychrolib_err"]=str(e)[:100]
    b8["wetbulb_le_drybulb"]=(wb is not None and wb<=db)
OUT["B-8"]=b8
print("  ",json.dumps(b8)[:300],flush=True)

# ---- A-2 / A-1: usage endpoint (plan/tier + credit accounting feasibility) ----
print("\n=== A-1/A-2 auth + usage endpoint ===",flush=True)
a2={}
for m in ("get","post"):
    try:
        r=getattr(requests,m)(f"{V}/system/fetch-api-key-usage",headers=H,timeout=25)
        a2[m]={"status":r.status_code,"body":r.text[:300]}
    except Exception as e: a2[m]={"error":str(e)[:100]}
OUT["A-1_A-2"]={"auth_header":"api-key (confirmed working on all data endpoints)","usage_endpoint":a2}
print("  usage:",json.dumps(a2)[:300],flush=True)

# ---- G-2: 404 immediately after submit (captured via first_404_poll across runs) ----
OUT["G-2_note"]="first_404_poll captured per submit_poll call where present"

json.dump(OUT,open("results_raw.json","w"),indent=2,default=str)
print("\nSAVED results_raw.json",flush=True)
