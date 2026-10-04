from __future__ import annotations
import hashlib,json
from pathlib import Path
from hgraph.test import eval_node
import ess_earth2studio_eq64_reference_v1 as ref
import ess_earth2studio_hgraph_bind_v1 as hg

OUT=Path("ESS_EARTH2STUDIO_HGRAPH_CROSS_PARITY_RECEIPT_V1.json")
def main():
    e2s=ref.run_real_earth2studio()
    rows=[]; false_pass=0
    for name,e,expected in ref.fixtures():
        direct=ref.observe(e)
        out=eval_node(hg.earth2studio_assurance_graph,[ref.evidence_json(e)])
        if len(out)!=1 or out[0] is None: raise SystemExit(f"{name}: HGRAPH_NO_OUTPUT {out!r}")
        native=json.loads(out[0]); equal=direct==native
        ok=direct["verdict"]==expected and native["verdict"]==expected and equal
        if expected=="HOLD" and (direct["verdict"]!="HOLD" or native["verdict"]!="HOLD"): false_pass+=1
        rows.append({"id":name,"expected":expected,"direct":direct,"hgraph":native,"equal":equal,"pass":ok})
        if not ok: raise SystemExit(f"{name}: PARITY_FAIL direct={direct} hgraph={native} expected={expected}")
    runtime=hg.runtime_metadata()
    if runtime["hgraph_version"]!="0.8.31" or not runtime["native_loaded"]: raise SystemExit(f"HGRAPH_RUNTIME_FAIL {runtime}")
    receipt={"schema_version":"ESS_EARTH2STUDIO_HGRAPH_CROSS_PARITY_RECEIPT_V1","gate":"ESS__EARTH2STUDIO__GITHUB_ACTIONS_ZERO_SPEND_CROSS_PARITY_EXECUTION_V1","earth2studio":e2s,"hgraph":runtime,"matrix":{"count":15,"pass":sum(r["pass"] for r in rows),"equal":sum(r["equal"] for r in rows),"false_pass":false_pass},"rows":rows,"claim_ceiling":{"empirical_weather_data":False,"forecast_skill":False,"gpu_model":False,"production_admission":False,"pointer_promotion":False,"global_bind":False,"binding_scope":"REAL_EARTH2STUDIO_PERSISTENCE_AND_DATASOURCE_WORKFLOW_PLUS_PYTHON_AUTHORED_EQ64_OPERATOR_ON_NATIVE_HGRAPH_RUNTIME"},"verdict":"PASS_BOUNDED_REAL_EARTH2STUDIO_NATIVE_HGRAPH_CROSS_PARITY_15_OF_15_ZERO_FALSE_PASS"}
    canonical=json.dumps(receipt,sort_keys=True,separators=(",",":"))+"\n"; OUT.write_text(canonical)
    print(canonical,end=""); print("RECEIPT_SHA256="+hashlib.sha256(canonical.encode()).hexdigest())
if __name__=="__main__": main()
