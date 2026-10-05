from __future__ import annotations

import argparse
import json
from pathlib import Path

from eq64_executable_assurance_engine import (
    canonical_bytes,
    evaluate_assurance,
    replay_assurance_receipt,
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _render_report(receipt: dict) -> str:
    return (
        "# EQ64 Executable Assurance Engine V1\n\n"
        f"Decision: **{receipt['decision']}**\n\n"
        f"EQ64 state: `{receipt['eq64']['state_index']}/63`\n\n"
        f"Bits: `{receipt['eq64']['bits']}`\n\n"
        "Reasons:\n"
        + "".join(f"- {reason}\n" for reason in receipt["reasons"])
        + "\n"
        f"Receipt SHA256: `{receipt['receipt_sha256']}`\n\n"
        "Claim ceiling: bounded assurance result only. No runtime admission, "
        "production readiness, pointer promotion, global bind, or external actuation.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="eq64-assurance")
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("input", type=Path)
    evaluate.add_argument("--receipt-out", type=Path)
    evaluate.add_argument("--report-out", type=Path)

    replay = sub.add_parser("replay")
    replay.add_argument("receipt", type=Path)

    args = parser.parse_args()

    try:
        if args.command == "evaluate":
            receipt = evaluate_assurance(_read_json(args.input))
            if args.receipt_out:
                _write_json(args.receipt_out, receipt)
            if args.report_out:
                args.report_out.parent.mkdir(parents=True, exist_ok=True)
                args.report_out.write_text(_render_report(receipt), encoding="utf-8")
            print(canonical_bytes(receipt).decode("utf-8"))
            return 0 if receipt["decision"] == "PASS" else 3

        replay_result = replay_assurance_receipt(_read_json(args.receipt))
        print(canonical_bytes(replay_result).decode("utf-8"))
        return 0 if replay_result["valid"] else 1

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
