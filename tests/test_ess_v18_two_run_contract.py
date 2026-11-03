#!/usr/bin/env python3
"""Offline negative tests for ESS V1.8 two-run contract."""
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from scripts.ess_v18_two_run_contract import verify

H = "a"*40
def sha(b): return hashlib.sha256(b).hexdigest()

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("canonical-registry.json","pinned-event-set.jsonl","v1_7-final-receipt.json"):
            (self.root/name).write_bytes(name.encode())
        self.manifest = dict(source_run_id="101",source_sha=H,synthetic_uid=False,
            canonical_registry_file_sha256=sha(b"canonical-registry.json"),
            pinned_event_set_file_sha256=sha(b"pinned-event-set.jsonl"),
            v1_7_final_receipt_file_sha256=sha(b"v1_7-final-receipt.json"))
        (self.root/"export-manifest.json").write_text(json.dumps(self.manifest))
        p=dict(run_id=101,run_attempt=1,commit_sha=H,status="completed",conclusion="success",
               repository="example/evidence-gate",workflow_path=".github/workflows/producer.yml")
        c=dict(run_id=102,run_attempt=1,commit_sha=H,repository=p["repository"])
        self.contract=dict(producer=p,consumer=c,expected_producer_commit=H,
                           expected_producer_workflow=p["workflow_path"],
                           provider_archive_digest_independently_verified=True,
                           provider_archive_sha256="b"*64)
        self.artifact=dict(repository=p["repository"],workflow_path=p["workflow_path"],
                           run_id=101,run_attempt=1,count_matching_name=1,expired=False,
                           id=123,name="ess-v18-producer-101",provider_digest="sha256:"+"b"*64)

    def test_baseline(self):
        self.assertEqual(verify(self.contract,self.manifest,self.artifact,self.root)["verdict"],
                         "PASS_TWO_RUN_IDENTITY_AND_SOURCE_BYTES")

    def reject(self, edit, expected):
        c,m,a=copy.deepcopy((self.contract,self.manifest,self.artifact))
        edit(c,m,a)
        with self.assertRaisesRegex(ValueError,"HOLD_"+expected):
            verify(c,m,a,self.root)

    def test_negative_matrix(self):
        cases=[
            (lambda c,m,a:c["producer"].update(commit_sha="c"*40),"MANIFEST_SOURCE"),
            (lambda c,m,a:c["consumer"].update(run_id=101),"NOT_TWO_RUNS"),
            (lambda c,m,a:c["producer"].update(conclusion="failure"),"PRODUCER_STATUS"),
            (lambda c,m,a:c["producer"].update(run_attempt=2),"ARTIFACT_RUN"),
            (lambda c,m,a:a.update(count_matching_name=2),"ARTIFACT_UNIQUE_LIVE"),
            (lambda c,m,a:a.update(expired=True),"ARTIFACT_UNIQUE_LIVE"),
            (lambda c,m,a:a.update(provider_digest=""),"PROVIDER_DIGEST"),
            (lambda c,m,a:a.update(run_id=999),"ARTIFACT_RUN"),
            (lambda c,m,a:a.update(workflow_path="wrong"),"WORKFLOW"),
            (lambda c,m,a:c.update(expected_producer_commit="d"*40),"EXPECTED_COMMIT"),
            (lambda c,m,a:c.update(provider_archive_digest_independently_verified=False),"ARCHIVE_DIGEST_READBACK"),
            (lambda c,m,a:c.update(provider_archive_sha256="f"*64),"ARCHIVE_DIGEST_MISMATCH"),
            (lambda c,m,a:m.update(synthetic_uid=True),"SYNTHETIC_UID"),
        ]
        for edit,expected in cases:
            with self.subTest(expected=expected): self.reject(edit,expected)

    def test_corrupted_file(self):
        (self.root/"canonical-registry.json").write_text("tampered")
        with self.assertRaisesRegex(ValueError,"HOLD_REGISTRY_SHA256"):
            verify(self.contract,self.manifest,self.artifact,self.root)

if __name__ == "__main__":
    unittest.main()
