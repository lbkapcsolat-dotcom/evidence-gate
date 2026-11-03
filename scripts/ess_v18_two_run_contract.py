#!/usr/bin/env python3
"""ESS V1.8 two-run identity and byte contract. Fail closed; no network or writes."""
import hashlib, json, re, sys
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
REQUIRED = ("canonical-registry.json", "pinned-event-set.jsonl", "v1_7-final-receipt.json", "export-manifest.json")

def require(condition, code):
    if not condition:
        raise ValueError("HOLD_" + code)

def verify(contract, manifest, artifact, payload_dir, archive_path=None):
    p, c = contract["producer"], contract["consumer"]
    require(str(p["run_id"]).isdigit() and str(c["run_id"]).isdigit(), "RUN_ID")
    require(str(p["run_id"]) != str(c["run_id"]), "NOT_TWO_RUNS")
    require(int(p["run_attempt"]) > 0 and int(c["run_attempt"]) > 0, "ATTEMPT")
    require(HEX40.fullmatch(p["commit_sha"]) is not None, "COMMIT_SHA")
    require(HEX40.fullmatch(c["commit_sha"]) is not None, "CONSUMER_COMMIT")
    require(p["status"] == "completed" and p["conclusion"] == "success", "PRODUCER_STATUS")
    require(p["repository"] == c["repository"] == artifact["repository"], "REPOSITORY")
    require(p["workflow_path"] == artifact["workflow_path"], "WORKFLOW")
    require(artifact["run_id"] == p["run_id"] and artifact["run_attempt"] == p["run_attempt"], "ARTIFACT_RUN")
    require(artifact["count_matching_name"] == 1 and artifact["expired"] is False, "ARTIFACT_UNIQUE_LIVE")
    require(isinstance(artifact["id"], int) and artifact["id"] > 0, "ARTIFACT_ID")
    require(DIGEST.fullmatch(artifact["provider_digest"]) is not None, "PROVIDER_DIGEST")
    require(artifact["name"] == "ess-v18-producer-" + str(p["run_id"]), "ARTIFACT_NAME")
    require(manifest["source_run_id"] == str(p["run_id"]) and manifest["source_sha"] == p["commit_sha"], "MANIFEST_SOURCE")
    require(contract["expected_producer_commit"] == p["commit_sha"], "EXPECTED_COMMIT")
    require(contract["expected_producer_workflow"] == p["workflow_path"], "EXPECTED_WORKFLOW")
    files = {}
    for name in REQUIRED:
        path = payload_dir / name
        require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_" + name)
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    require(files["canonical-registry.json"] == manifest["canonical_registry_file_sha256"], "REGISTRY_SHA256")
    require(files["pinned-event-set.jsonl"] == manifest["pinned_event_set_file_sha256"], "EVENT_SHA256")
    require(files["v1_7-final-receipt.json"] == manifest["v1_7_final_receipt_file_sha256"], "V17_SHA256")
    require(json.loads((payload_dir / "export-manifest.json").read_text()) == manifest, "MANIFEST_BYTES")
    require(manifest["synthetic_uid"] is False, "SYNTHETIC_UID")
    # Independently hash the downloaded archive bytes, never trust a boolean.
    require(archive_path is not None, "ARCHIVE_BYTES_MISSING")
    archive = Path(archive_path)
    require(archive.is_file() and not archive.is_symlink(), "ARCHIVE_BYTES_MISSING")
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    require(archive_hash == artifact["provider_digest"][7:], "ARCHIVE_DIGEST_MISMATCH")
    return {"verdict": "PASS_TWO_RUN_IDENTITY_AND_SOURCE_BYTES", "producer_run": p["run_id"], "consumer_run": c["run_id"], "files_sha256": files, "strict_cross_event": "NOT_EVALUATED"}

def main():
    require(len(sys.argv) == 5, "USAGE")
    contract = json.loads(Path(sys.argv[1]).read_text())
    artifact = json.loads(Path(sys.argv[2]).read_text())
    root = Path(sys.argv[3])
    manifest = json.loads((root / "export-manifest.json").read_text())
    print(json.dumps(verify(contract, manifest, artifact, root, Path(sys.argv[4])), sort_keys=True))

if __name__ == "__main__":
    try: main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
