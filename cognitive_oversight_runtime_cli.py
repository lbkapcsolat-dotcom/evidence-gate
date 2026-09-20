from __future__ import annotations

import argparse
import json
from pathlib import Path

from cognitive_oversight_runtime import build_receipt, replay_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("admit", "replay"):
        p = sub.add_parser(name)
        p.add_argument("input", type=Path)
    args = parser.parse_args()

    try:
        obj = json.loads(args.input.read_text(encoding="utf-8"))
        out = build_receipt(obj) if args.command == "admit" else replay_receipt(obj)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2

    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0 if args.command == "admit" or out["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
