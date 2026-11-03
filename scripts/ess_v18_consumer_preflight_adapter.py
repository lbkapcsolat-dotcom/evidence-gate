#!/usr/bin/env python3
"""ESS V1.8 consumer preflight adapter. Fail closed until separate-run evidence is present.

The adapter does not fetch, trust, or synthesize GitHub provider metadata.
Provider run/artifact metadata must be independently collected and authenticated.
"""
import json, os, subprocess, sys
from pathlib import Path
from scripts.ess_v18_two_run_contract import verify, require

def main():
    require(os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch", "EVENT")
    require(os.getenv("GITHUB_REF_NAME") == "audit/ess-openshell-v18-producer-consumer-20261103", "BRANCH")
    contract_path = Path(os.environ["ESS_V18_CONTRACT"])
    artifact_path = Path(os.environ["ESS_V18_PROVIDER_METADATA"])
    source_dir = Path(os.environ["ESS_V18_PRODUCER_FILES"])
    contract = json.loads(contract_path.read_text())
    artifact = json.loads(artifact_path.read_text())
    consumer = contract["consumer"]
    require(str(consumer["run_id"]) == os.environ["GITHUB_RUN_ID"], "CONSUMER_RUN")
    require(consumer["commit_sha"] == os.environ["GITHUB_SHA"], "CONSUMER_SHA")
    require(consumer["repository"] == os.environ["GITHUB_REPOSITORY"], "CONSUMER_REPO")
    require(str(consumer["run_attempt"]) == os.environ["GITHUB_RUN_ATTEMPT"], "CONSUMER_ATTEMPT")
    require(str(contract["producer"]["run_id"]) != os.environ["GITHUB_RUN_ID"], "NOT_TWO_RUNS")
    manifest = json.loads((source_dir / "export-manifest.json").read_text())
    archive_path = Path(os.environ["ESS_V18_PRODUCER_ARCHIVE"])
    result = verify(contract, manifest, artifact, source_dir, archive_path)
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    try: main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
