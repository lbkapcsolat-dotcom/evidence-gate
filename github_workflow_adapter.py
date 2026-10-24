from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


POLICY_VERSION = "github-workflow-adapter-v1"

_TERMINAL_NON_SUCCESS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
    "skipped",
}


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _run_order(run: Mapping[str, Any]) -> tuple[int, int]:
    run_number = run.get("run_number")
    run_id = run.get("run_id")
    number_key = run_number if isinstance(run_number, int) else -1
    id_key = run_id if isinstance(run_id, int) else -1
    return (number_key, id_key)


def assess_workflow_run(run: Mapping[str, Any]) -> tuple[str, str]:
    status = run.get("status")
    conclusion = run.get("conclusion")

    if not isinstance(status, str):
        return "insufficient", "workflow status is missing or not a string"

    status = status.strip().lower()
    if status != "completed":
        return "insufficient", f"workflow is not completed (status={status})"

    if not isinstance(conclusion, str):
        return "insufficient", "completed workflow has no usable conclusion"

    conclusion = conclusion.strip().lower()

    if conclusion == "success":
        return "supports", "required workflow completed successfully"

    if conclusion in _TERMINAL_NON_SUCCESS:
        return (
            "contradicts",
            f"required workflow completed without success (conclusion={conclusion})",
        )

    return "insufficient", f"unrecognized completed conclusion={conclusion}"


def adapt_github_workflow_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    repository = _require_string(payload.get("repository"), "repository")
    head_sha = _require_string(payload.get("head_sha"), "head_sha")

    required = payload.get("required_workflows")
    runs = payload.get("workflow_runs")

    if not isinstance(required, list) or not required:
        raise ValueError("required_workflows must be a non-empty list")
    if not isinstance(runs, list):
        raise ValueError("workflow_runs must be a list")

    required_names: list[str] = []
    seen_required: set[str] = set()
    for index, name in enumerate(required):
        normalized = _require_string(name, f"required_workflows[{index}]")
        if normalized in seen_required:
            raise ValueError(f"duplicate required workflow: {normalized}")
        seen_required.add(normalized)
        required_names.append(normalized)

    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for index, run in enumerate(runs):
        if not isinstance(run, Mapping):
            raise ValueError(f"workflow_runs[{index}] must be an object")
        name = run.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"workflow_runs[{index}].name must be a non-empty string"
            )
        by_name.setdefault(name.strip(), []).append(run)

    evidence: list[dict[str, Any]] = []

    for name in required_names:
        candidates = by_name.get(name, [])
        if not candidates:
            evidence.append(
                {
                    "source": f"github-actions:{repository}:{head_sha}:{name}",
                    "assessment": "insufficient",
                    "adapter": POLICY_VERSION,
                    "reason": "required workflow run is missing",
                    "workflow_name": name,
                    "head_sha": head_sha,
                }
            )
            continue

        selected = max(candidates, key=_run_order)
        assessment, reason = assess_workflow_run(selected)
        run_id = selected.get("run_id")
        source = (
            f"github-actions:run:{run_id}"
            if isinstance(run_id, int)
            else f"github-actions:{repository}:{head_sha}:{name}"
        )

        evidence.append(
            {
                "source": source,
                "assessment": assessment,
                "adapter": POLICY_VERSION,
                "reason": reason,
                "workflow_name": name,
                "head_sha": head_sha,
                "raw": {
                    "run_id": selected.get("run_id"),
                    "run_number": selected.get("run_number"),
                    "status": selected.get("status"),
                    "conclusion": selected.get("conclusion"),
                },
            }
        )

    claim = (
        f"All {len(required_names)} required GitHub Actions workflows for "
        f"{repository}@{head_sha} completed successfully."
    )

    return {
        "claim": claim,
        "evidence": evidence,
        "adapter": {
            "name": "github_workflow_adapter",
            "policy_version": POLICY_VERSION,
            "required_workflow_count": len(required_names),
            "raw_workflow_run_count": len(runs),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert GitHub Actions workflow-run JSON into Evidence Gate input."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("input JSON must contain an object")
        adapted = adapt_github_workflow_payload(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    rendered = json.dumps(adapted, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
