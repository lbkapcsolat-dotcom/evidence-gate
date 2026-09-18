from __future__ import annotations
import argparse, json
from pathlib import Path
from ess_evidence_runtime import build_receipt, replay_receipt

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="command",required=True)
    for name in ("admit","replay"):
        x=s.add_parser(name); x.add_argument("input",type=Path)
    a=p.parse_args()
    try:
        obj=json.loads(a.input.read_text(encoding="utf-8"))
        out=build_receipt(obj) if a.command=="admit" else replay_receipt(obj)
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"error":str(e)},sort_keys=True)); return 2
    print(json.dumps(out,sort_keys=True,separators=(",",":")))
    return 0 if a.command=="admit" or out["valid"] else 1

if __name__=="__main__":
    raise SystemExit(main())
