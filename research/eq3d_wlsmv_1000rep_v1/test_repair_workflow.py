#!/usr/bin/env python3
"""Fail-closed structural/shell regression for the expensive EQ3D M4 repair workflow."""
import json
import subprocess
from pathlib import Path

path = Path(".github/workflows/eq3d-wlsmv-repair-v1.yml")
proc = subprocess.run(
    ["ruby", "-ryaml", "-rjson", "-e",
     "puts JSON.generate(YAML.load_file(ARGV.fetch(0)))", str(path)],
    check=True, text=True, capture_output=True,
)
workflow = json.loads(proc.stdout)
assert isinstance(workflow, dict), "HOLD_WORKFLOW_NOT_MAPPING"
triggers = workflow.get("on", workflow.get("true"))
assert isinstance(triggers, dict), "HOLD_WORKFLOW_NO_TRIGGER"
push = triggers.get("push")
assert isinstance(push, dict), "HOLD_WORKFLOW_NO_EXPLICIT_PUSH_TRIGGER"
assert push.get("branches") == ["eq3d-wlsmv-1000rep-grid-v1"], "HOLD_TRIGGER_BRANCH"
assert push.get("paths") == [".github/eq3d/RUN_M4_REPAIR_APPROVED.txt"], "HOLD_TRIGGER_PATH"
assert "pull_request" not in triggers, "HOLD_EXPENSIVE_PR_TRIGGER"
assert workflow.get("permissions") == {"contents": "read", "actions": "read"}, "HOLD_WORKFLOW_PERMISSIONS"
jobs = workflow.get("jobs")
assert isinstance(jobs, dict), "HOLD_MISSING_JOBS"
assert set(jobs) == {"plan", "repair-grid", "sensitivity", "aggregate"}, "HOLD_UNEXPECTED_JOBS"
assert jobs["repair-grid"]["strategy"]["fail-fast"] is False, "HOLD_FAIL_FAST"
assert jobs["repair-grid"]["strategy"]["max-parallel"] <= 20, "HOLD_EXCESS_PARALLELISM"
assert jobs["repair-grid"]["timeout-minutes"] <= 180, "HOLD_EXCESS_JOB_TIMEOUT"
assert jobs["aggregate"]["timeout-minutes"] <= 45, "HOLD_EXCESS_AGGREGATION_TIMEOUT"

def exact_step(job, name):
    matches = [step for step in jobs[job]["steps"] if step.get("name") == name]
    assert len(matches) == 1, f"HOLD_STEP_COUNT_{job}_{name}"
    return matches[0]

verify = exact_step("aggregate", "Verify every grid.csv against the corresponding SHA256.txt")
assert "PASS_SHARD_CSV_SHA256_READBACK_48_OF_48" in verify["run"], "HOLD_CSV_SHA_READBACK_MARKER"
assert "sha256sum" in verify["run"], "HOLD_NO_SHA256"
assert 'test "$count" -eq 48' in verify["run"], "HOLD_SHA_SHARD_COUNT"
exact_step("aggregate", "Aggregate 12x1000 exact grid")
receipt = exact_step("aggregate", "Emit merge-readiness fence")
assert 'r.get("final_verdict")' in receipt["run"], "HOLD_RECEIPT_FIELD"
assert 'r.get("overall")' not in receipt["run"], "HOLD_OLD_RECEIPT_FIELD"
assert "NO_GLOBAL_BIND" in receipt["run"], "HOLD_GLOBAL_BIND_FENCE"
assert "NO_EMPIRICAL_3D_VALIDATION" in receipt["run"], "HOLD_EMPIRICAL_CLAIM_FENCE"
assert "NO_PRODUCTION_ADMISSION" in receipt["run"], "HOLD_PRODUCTION_FENCE"
sensitivity = exact_step("sensitivity", "Download source sensitivity artifact")
assert "PASS_SENSITIVITY_MANIFEST_3_OF_3" in sensitivity["run"], "HOLD_SENSITIVITY_MANIFEST_GATE"
assert "45fb48447e9978c0bbdefb8b2c3e9d3d8b45f73a768d84d8bb8316d8514e4e29" in sensitivity["run"], "HOLD_SENSITIVITY_MANIFEST_PIN"
exact_step("repair-grid", "Verify row-contract regression")

checked = 0
for job_name, job in jobs.items():
    assert isinstance(job.get("steps"), list), f"HOLD_NO_STEPS_{job_name}"
    for step in job["steps"]:
        script = step.get("run")
        if script is None:
            continue
        assert isinstance(script, str), f"HOLD_INVALID_RUN_{job_name}"
        shell = subprocess.run(["bash", "-n"], input=script,
                               text=True, capture_output=True)
        assert shell.returncode == 0, (
            f"HOLD_SHELL_SYNTAX_{job_name}_{step.get('name')}: "
            f"{shell.stderr.strip()}"
        )
        checked += 1
assert checked >= 10, "HOLD_TOO_FEW_LINTED_RUN_STEPS"
print(f"PASS_REPAIR_WORKFLOW_YAML_AND_BASH_SYNTAX checked={checked}")
