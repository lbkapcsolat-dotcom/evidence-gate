#!/usr/bin/env python3
"""Prospective seed-schedule proposal: zero model fitting, zero data generation."""
import csv, hashlib, json, pathlib, sys

BASE = pathlib.Path("research/eq3d_wlsmv_1000rep_v1")
PROTOCOL = BASE / "PROSPECTIVE_HELDOUT_AND_WLSMV_COMPARISON_PROTOCOL_V1.md"
GRID = BASE / "grid.R"
TRUTHS = ("M3", "M4", "M5", "M7")
ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("prereg-out")
ROOT.mkdir(exist_ok=True, parents=True)
sha = lambda b: hashlib.sha256(b).hexdigest()
protocol_digest = sha(PROTOCOL.read_bytes())
assert sha(GRID.read_bytes()) == "f2fb934da472e965b9fbfc0d56f0a395e2688b9dbdd693b4209b02cd801532b37d", "HOLD_SOURCE_GRID_SHA256"
# Historical seeds: all 3 Ns × 4 truths × all 1000 reps, plus prior 2 × 1 bounded fixtures.
original=set()
for n in (4800,6000,7200):
    for idx,truth in enumerate(TRUTHS,1):
        for rep in range(1,1001):
            shard=(rep-1)//250
            original.add(260611020+n*10000+idx*1000000+shard*1000+rep)
for idx in (2,3):  # bounded M4 and M5: N=480, shard=0, rep=1
    original.add(260611020+480*10000+idx*1000000+1)
seen=set()
rows=[]
for truth in TRUTHS:
    for rep in range(1,251):
        payload=f"EQ3D_HELDOUT_V1|{truth}|{rep}|{protocol_digest}".encode("utf-8")
        digest=sha(payload)
        seed=int.from_bytes(bytes.fromhex(digest[:8]),"big") & 0x7fffffff
        assert 1<=seed<=2147483647, "HOLD_SEED_DOMAIN"
        assert seed not in original and seed not in seen, "HOLD_SEED_COLLISION"
        seen.add(seed)
        rows.append((truth,rep,seed,digest))
csvpath=ROOT/"HELDOUT_SEED_SCHEDULE_V1.csv"
with csvpath.open("w",encoding="utf-8",newline="") as f:
    w=csv.writer(f,lineterminator="\n")
    w.writerow(("truth","rep","seed","sha256_preimage"))
    w.writerows(rows)
assert len(rows)==1000 and len(seen)==1000
manifest={
    "gate":"EQ3D_PROSPECTIVE_V1_PRE_REGISTRATION_SEED_LOCK_AND_INDEPENDENT_METHOD_REVIEW_GATE",
    "status":"PROPOSED_FROZEN_SEEDS_NOT_EXECUTION_AUTHORITY",
    "protocol_sha256":protocol_digest,
    "grid_blob_sha1":"674dacbc2813b26be3a4c8fa80c9560b115d5a0b",
    "seed_schedule_sha256":sha(csvpath.read_bytes()),
    "seeds":1000,
    "truths":list(TRUTHS),
    "attempts_per_truth":250,
    "historic_seed_exclusion_count":len(original),
    "collision_count":0,
    "seed_algorithm":"SHA256('EQ3D_HELDOUT_V1|truth|rep|protocol_sha256'), first four bytes, bit-and 0x7fffffff, zero/collision => HOLD",
    "prior_grid_source_run":41586168086,
    "prior_fixture_run":41983775160,
    "independent_statistical_review":"MISSING",
    "lavaan_0_7_2_versioned_difference_method_review":"MISSING",
    "runtime_authorization":"MISSING",
    "comparison_method_admission":"HOLD",
    "claim_ceiling":["NO_EMPIRICAL_VALIDATION","NO_GLOBAL_BIND","NO_PRODUCTION_ADMISSION","NO_HELDOUT_EXECUTION"]
}
jpath=ROOT/"SEED_LOCK_MANIFEST_V1.json"
jpath.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("PASS_SEED_SCHEDULE_1000_UNIQUE_EXCLUDED_HISTORIC")
print("PROTOCOL_SHA256="+protocol_digest)
print("SEED_SCHEDULE_SHA256="+manifest["seed_schedule_sha256"])
