#!/usr/bin/env bash
# ESS V1.8 offline tests: no network, no GitHub API, no authority mutation.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
python3 -m compileall -q scripts/ess_v18_two_run_contract.py scripts/ess_v18_consumer_preflight_adapter.py scripts/ess_v18_zip_payload_custody.py tests/test_ess_v18_two_run_contract.py
python3 -m unittest -v tests.test_ess_v18_two_run_contract
python3 -m unittest discover -v -s tests -p 'test_ess_v18_zip_payload_custody.py'
