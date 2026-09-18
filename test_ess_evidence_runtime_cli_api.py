import json, subprocess, sys, tempfile, threading, urllib.request, unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from ess_evidence_runtime_api import Handler

BASE={"schema_version":"ESS_EVIDENCE_RUNTIME_V1","claim":"cli api","source":{"name":"x","version":1,"sha256":"a"*64},"execution":{"execution_id":"e","input_sha256":"b"*64,"output_sha256":"c"*64,"environment_id":"test"},"provider_readback":{"provider":"test","source_name":"x","source_version":1,"source_sha256":"a"*64,"fresh":True},"eq64":{"historical_identity":False,"fresh_readback":True,"semantic_contract":True,"baseline_bound":True,"admissible_execution":True,"negative_evidence":False},"claim_level":1,"previous_claim_level":0,"new_admissible_evidence":True}

class T(unittest.TestCase):
    def test_cli_admit_and_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"; p.write_text(json.dumps(BASE))
            r=subprocess.run([sys.executable,"ess_evidence_runtime_cli.py","admit",str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0)
            receipt=json.loads(r.stdout); self.assertEqual(receipt["admission"],"PASS")
            q=Path(d)/"r.json"; q.write_text(json.dumps(receipt))
            rr=subprocess.run([sys.executable,"ess_evidence_runtime_cli.py","replay",str(q)],capture_output=True,text=True)
            self.assertEqual(rr.returncode,0); self.assertTrue(json.loads(rr.stdout)["valid"])
    def test_api_uses_same_receipt_engine(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        th=threading.Thread(target=server.serve_forever,daemon=True); th.start()
        try:
            req=urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/admit",data=json.dumps(BASE).encode(),headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(req) as resp: out=json.load(resp)
            self.assertEqual(out["admission"],"PASS")
            self.assertFalse(out["runtime_admission"])
        finally:
            server.shutdown(); server.server_close()

if __name__=="__main__":
    unittest.main()
