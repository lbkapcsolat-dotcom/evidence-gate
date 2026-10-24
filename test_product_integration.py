import json
import tempfile
import unittest
from pathlib import Path

from github_workflow_adapter import adapt_github_workflow_payload
from live_source_collector import HttpResponse, parse_source_url, run_url
from unified_evidence_source_runner import detect_source_type, run_unified


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)

    def request(self, url, *, headers=None):
        if not self.responses:
            raise AssertionError(f"unexpected request: {url}")
        return self.responses.pop(0)


def json_response(value, status=200):
    return HttpResponse(status, {}, json.dumps(value).encode("utf-8"))


class ProductIntegrationTests(unittest.TestCase):
    def test_github_adapter_success(self):
        payload = {
            "repository": "o/r",
            "head_sha": "abc",
            "required_workflows": ["ci"],
            "workflow_runs": [{
                "run_id": 1,
                "name": "ci",
                "status": "completed",
                "conclusion": "success",
            }],
        }
        adapted = adapt_github_workflow_payload(payload)
        self.assertEqual(
            adapted["evidence"][0]["assessment"],
            "supports",
        )

    def test_drive_adapter_hash_mismatch_conflicts(self):
        payload = {
            "scope_name": "artifact",
            "required_artifacts": [{
                "drive_file_id": "f",
                "expected": {"sha256": "a" * 64},
            }],
            "drive_records": [{
                "drive_file_id": "f",
                "retrieval_status": "ok",
                "sha256": "b" * 64,
            }],
        }
        result, _ = run_unified(payload)
        self.assertEqual(
            result["classification"]["status"],
            "CONFLICTING",
        )

    def test_unified_auto_selects_github(self):
        payload = {
            "repository": "o/r",
            "head_sha": "abc",
            "required_workflows": ["ci"],
            "workflow_runs": [{
                "run_id": 1,
                "name": "ci",
                "status": "completed",
                "conclusion": "success",
            }],
        }
        self.assertEqual(
            detect_source_type(payload),
            "github_workflows",
        )
        result, receipt = run_unified(payload)
        self.assertEqual(
            result["classification"]["status"],
            "SUPPORTED",
        )
        self.assertTrue(receipt["engine_identity_pass"])

    def test_unified_auto_selects_drive(self):
        payload = {
            "scope_name": "artifact",
            "required_artifacts": [{
                "drive_file_id": "f",
                "expected": {"name": "x.zip"},
            }],
            "drive_records": [{
                "drive_file_id": "f",
                "retrieval_status": "ok",
                "name": "x.zip",
            }],
        }
        self.assertEqual(
            detect_source_type(payload),
            "google_drive",
        )
        result, _ = run_unified(payload)
        self.assertEqual(
            result["classification"]["status"],
            "SUPPORTED",
        )

    def test_url_parser_accepts_real_shapes(self):
        self.assertEqual(
            parse_source_url(
                "https://github.com/o/r/pull/7"
            ).provider,
            "github",
        )
        self.assertEqual(
            parse_source_url(
                "https://drive.google.com/file/d/file1/view"
            ).provider,
            "google_drive",
        )

    def test_live_github_url_to_result_and_receipt(self):
        registry = {
            "registry_version": "test-v1",
            "github": {
                "o/r": {"required_workflows": ["ci"]}
            },
            "google_drive": {},
        }
        transport = FakeTransport([
            json_response({
                "state": "open",
                "draft": True,
                "merged": False,
                "head": {"sha": "abc"},
            }),
            json_response({
                "workflow_runs": [{
                    "id": 1,
                    "run_number": 1,
                    "name": "ci",
                    "status": "completed",
                    "conclusion": "success",
                }],
            }),
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy = root / "policy.json"
            policy.write_text(
                json.dumps(registry),
                encoding="utf-8",
            )
            out = root / "out"
            result, receipt = run_url(
                "https://github.com/o/r/pull/7",
                policy_path=policy,
                output_dir=out,
                transport=transport,
            )
            self.assertEqual(
                result["evidence_gate"]["classification"]["status"],
                "SUPPORTED",
            )
            self.assertEqual(
                receipt["execution_status"],
                "PASS",
            )
            self.assertEqual(
                sorted(p.name for p in out.iterdir()),
                ["receipt.json", "result.json"],
            )

    def test_live_drive_url_to_result_and_receipt(self):
        expected_hash = (
            "ba7816bf8f01cfea414140de5dae2223"
            "b00361a396177a9cb410ff61f20015ad"
        )
        registry = {
            "registry_version": "test-v1",
            "github": {},
            "google_drive": {
                "file1": {
                    "scope_name": "artifact",
                    "expected": {
                        "name": "x.zip",
                        "mime_type": "application/zip",
                        "size_bytes": 3,
                        "sha256": expected_hash,
                    },
                }
            },
        }
        transport = FakeTransport([
            json_response({
                "id": "file1",
                "name": "x.zip",
                "mimeType": "application/zip",
                "size": "3",
                "parents": ["folder"],
            }),
            HttpResponse(200, {}, b"abc"),
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy = root / "policy.json"
            policy.write_text(
                json.dumps(registry),
                encoding="utf-8",
            )
            result, receipt = run_url(
                "https://drive.google.com/file/d/file1/view",
                policy_path=policy,
                output_dir=root / "out",
                transport=transport,
                drive_token="test-token",
            )
            self.assertEqual(
                result["evidence_gate"]["classification"]["status"],
                "SUPPORTED",
            )
            self.assertEqual(
                receipt["execution_status"],
                "PASS",
            )


if __name__ == "__main__":
    unittest.main()
