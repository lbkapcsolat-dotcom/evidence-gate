#!/usr/bin/env python3
from __future__ import annotations
import csv, glob, hashlib, json, math, os
from collections import defaultdict

EXPECTED_N = [4800, 6000, 7200]
EXPECTED_TRUTH = ["M3","M4","M5","M7"]
EXPECTED_PER_CELL = 1000
TARGET = 0.90
LRT_MIN = 0.99

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

files = sorted(glob.glob("results/result_*.csv"))
rows=[]
manifest=[]
for path in files:
    manifest.append({"path":path,"sha256":sha256(path),"bytes":os.path.getsize(path)})
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["N"]=int(r["N"]); r["rep"]=int(r["rep"]); r["shard"]=int(r["shard"])
            r["m3_support"]=None if not r.get("m3_support") else int(float(r["m3_support"]))
            r["lrt_all_available"]=int(float(r.get("lrt_all_available") or 0))
            rows.append(r)

sens_path = "sensitivity/sensitivity_receipt.json"
sensitivity = None
if os.path.exists(sens_path):
    manifest.append({"path":sens_path,"sha256":sha256(sens_path),"bytes":os.path.getsize(sens_path)})
    with open(sens_path,encoding="utf-8") as f:
        sensitivity=json.load(f)

cells=defaultdict(list)
for r in rows:
    cells[(r["N"],r["truth"])].append(r)

cell_receipts=[]
by_n=defaultdict(dict)
all_complete=True
for N in EXPECTED_N:
    for truth in EXPECTED_TRUTH:
        rr=cells.get((N,truth),[])
        ok=[x for x in rr if x["status"]=="OK" and x["m3_support"] is not None]
        err=[x for x in rr if x["status"]!="OK" or x["m3_support"] is None]
        count=len(rr); ok_count=len(ok); err_count=len(err)
        support_rate=(sum(x["m3_support"] for x in ok)/ok_count) if ok_count else None
        decision_rate=(support_rate if truth=="M3" else 1.0-support_rate) if support_rate is not None else None
        lrt_rate=(sum(x["lrt_all_available"] for x in ok)/ok_count) if ok_count else None
        complete=(count==EXPECTED_PER_CELL and ok_count==EXPECTED_PER_CELL and err_count==0)
        pass_cell=bool(complete and decision_rate is not None and decision_rate>=TARGET and lrt_rate is not None and lrt_rate>=LRT_MIN)
        all_complete = all_complete and complete
        rec={
            "N":N,"truth":truth,"rows":count,"ok":ok_count,"errors":err_count,
            "m3_support_rate":support_rate,"decision_rate":decision_rate,
            "lrt_available_rate":lrt_rate,"complete":complete,"pass_cell":pass_cell
        }
        cell_receipts.append(rec)
        by_n[N][truth]=rec

passing_N=[]
for N in EXPECTED_N:
    if all(by_n[N].get(t,{}).get("pass_cell",False) for t in EXPECTED_TRUTH):
        passing_N.append(N)

first_pass=min(passing_N) if passing_N else None
recruited_target=(math.ceil((first_pass*1.2)/100)*100) if first_pass else None

if sensitivity is None:
    sensitivity_closure="HOLD_MISSING_SENSITIVITY_RECEIPT"
    sensitivity_ok=False
    method_status="HOLD"
else:
    esem=sensitivity.get("esem_crossloading_sensitivity")
    method=sensitivity.get("method_factor_detector")
    if method=="PASS":
        method_status="CLOSED_AVAILABLE"
    elif method=="FAIL_POSITIVE_CONTROL":
        method_status="CLOSED_REJECTED_BY_POSITIVE_CONTROL"
    else:
        method_status="HOLD"
    sensitivity_ok=(esem=="PASS" and method_status!="HOLD")
    sensitivity_closure=("PASS_ESEM_AND_METHOD_CLOSURE" if sensitivity_ok else "HOLD_SENSITIVITY")

if first_pass is not None and all_complete and sensitivity_ok:
    verdict="PASS_FINAL_RECRUITMENT_LOCK"
else:
    verdict="HOLD_FINAL_RECRUITMENT_LOCK"

receipt={
    "gate":"EQUILIBRIUM_CANONICAL_3D_DISTRIBUTED_EXACT_WLSMV_1000_REP_GRID_AND_METHOD_FACTOR_CLOSURE_V1",
    "grid":{
        "expected_cells":12,
        "expected_replications_per_cell":EXPECTED_PER_CELL,
        "total_expected_replications":12000,
        "result_files":len(files),
        "all_cells_complete":all_complete,
        "cells":cell_receipts
    },
    "sensitivity":{
        "closure":sensitivity_closure,
        "method_factor_status":method_status,
        "raw":sensitivity
    },
    "recruitment":{
        "first_analyzable_N_passing_all_cells":first_pass,
        "planning_yield_multiplier":1.2,
        "final_recruited_N":recruited_target
    },
    "final_verdict":verdict,
    "fences":[
        "NO_MERGE",
        "NO_GLOBAL_BIND",
        "NO_PRODUCTION_ADMISSION",
        "NO_EMPIRICAL_3D_VALIDATION"
    ]
}

with open("FINAL_RECRUITMENT_LOCK_RECEIPT.json","w",encoding="utf-8") as f:
    json.dump(receipt,f,indent=2,sort_keys=True)

with open("RESULT_MANIFEST.json","w",encoding="utf-8") as f:
    json.dump(manifest,f,indent=2,sort_keys=True)

with open("CELL_SUMMARY.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["N","truth","rows","ok","errors","m3_support_rate","decision_rate","lrt_available_rate","complete","pass_cell"])
    w.writeheader()
    w.writerows(cell_receipts)

print(json.dumps({
    "final_verdict":verdict,
    "first_pass_N":first_pass,
    "final_recruited_N":recruited_target,
    "all_complete":all_complete,
    "sensitivity_closure":sensitivity_closure,
    "method_factor_status":method_status
},indent=2,sort_keys=True))
