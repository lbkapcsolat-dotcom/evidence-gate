"""Independent, read-only check of the committed prospective seed schedule."""
import csv, hashlib, json, pathlib, sys

ROOT=pathlib.Path("research/eq3d_wlsmv_1000rep_v1")
DIR=ROOT/"preregistered_v1"
PROTOCOL_SHA="3238787440744c55020c6350df252cfcb7842c1f02642bf657cbf113295fe5cd"
GRID_SHA="eda14848607b60fd53bee529039fda9fc879237e89ae26ff013811f67cc9a8d9"
SCHEDULE_SHA="5acd606a4030825ff69af56be8f377e67ed4b50184c6068b8becc011cf0d8b19"
TRUTHS=("M3","M4","M5","M7")
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((ROOT/"PROSPECTIVE_HELDOUT_AND_WLSMV_COMPARISON_PROTOCOL_V1.md").read_bytes())==PROTOCOL_SHA, "HOLD_PROTOCOL_BYTES_CHANGED"
assert sha((ROOT/"grid.R").read_bytes())==GRID_SHA, "HOLD_GRID_BYTES_CHANGED"
schedule=(DIR/"HELDOUT_SEED_SCHEDULE_V1.csv").read_bytes()
assert sha(schedule)==SCHEDULE_SHA, "HOLD_SEED_SCHEDULE_BYTES_CHANGED"
manifest=json.loads((DIR/"SEED_LOCK_MANIFEST_V1.json").read_text(encoding="utf-8"))
assert manifest["protocol_sha256"]==PROTOCOL_SHA and manifest["grid_sha256"]==GRID_SHA and manifest["seed_schedule_sha256"]==SCHEDULE_SHA, "HOLD_MANIFEST_CUSTODY"
rows=list(csv.DictReader(schedule.decode("utf-8").splitlines()))
assert len(rows)==1000, "HOLD_EXPECTED_1000_SEEDS"
assert tuple(dict.fromkeys(r["truth"] for r in rows))==TRUTHS, "HOLD_TRUTH_ORDER"
original=set()
for n in (4800,6000,7200):
    for idx,t in enumerate(TRUTHS,1):
        for rep in range(1,1001):
            original.add(260611020+n*10000+idx*1000000+((rep-1)//250)*1000+rep)
for idx in (2,3):
    original.add(260611020+480*10000+idx*1000000+1)
seeds=set()
for i,r in enumerate(rows):
    truth=TRUTHS[i//250]; rep=i%250+1
    assert r["truth"]==truth and int(r["rep"])==rep, "HOLD_REP_OR_TRUTH_ORDER"
    digest=sha(f"EQ3D_HELDOUT_V1|{truth}|{rep}|{PROTOCOL_SHA}".encode())
    seed=int.from_bytes(bytes.fromhex(digest[:8]),"big") & 0x7fffffff
    assert r["sha256_preimage"]==digest and int(r["seed"])==seed, "HOLD_SEED_DERIVATION"
    assert 1<=seed<=2147483647 and seed not in original and seed not in seeds, "HOLD_SEED_COLLISION"
    seeds.add(seed)
assert len(seeds)==1000, "HOLD_UNIQUE_SEEDS"
assert manifest["independent_statistical_review"]=="MISSING"
assert manifest["runtime_authorization"]=="MISSING"
assert manifest["comparison_method_admission"]=="HOLD"
print("PASS_GITHUB_LOCKED_SEED_SCHEDULE_1000_OF_1000")
print("HOLD_INDEPENDENT_REVIEW_AND_RUNTIME_AUTHORIZATION")
