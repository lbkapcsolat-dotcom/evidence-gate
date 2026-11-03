#!/usr/bin/env python3
"""Offline structural admission gate for split ESS V1.8 workflows.
Requires PyYAML. Never claims GitHub native registration or runtime success.
"""
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    raise SystemExit("HOLD_YAML_PARSER_UNAVAILABLE")

BASE=Path(".github/workflows")
PRODUCER=BASE/"ess-openshell-v18-producer-only.yml"
CONSUMER=BASE/"ess-openshell-v18-consumer-only.yml"
LEGACY=BASE/"ess-openshell-v18-producer-consumer.yml"

def require(ok,code):
    if not ok: raise ValueError("HOLD_"+code)

def parse(path):
    # PyYAML 1.1 treats 'on' as boolean; accept either representation.
    doc=yaml.safe_load(path.read_text())
    require(isinstance(doc,dict),"YAML_DOCUMENT")
    events=doc.get("on",doc.get(True))
    require(isinstance(events,dict) and "workflow_dispatch" in events,"MANUAL_DISPATCH")
    require(set(doc.get("permissions",{}))<= {"contents","actions"},"PERMISSIONS")
    require(doc.get("permissions",{}).get("contents")=="read","CONTENTS_READ")
    require(doc.get("permissions",{}).get("actions")=="read","ACTIONS_READ")
    require(isinstance(doc.get("jobs"),dict),"JOBS")
    return doc

def check(producer,consumer):
    p=parse(producer); c=parse(consumer)
    require(set(p["jobs"])=={"producer"},"PRODUCER_JOB_SET")
    require(set(c["jobs"])=={"consumer"},"CONSUMER_JOB_SET")
    require("needs" not in c["jobs"]["consumer"],"SAME_RUN_DEPENDENCY")
    psteps=p["jobs"]["producer"].get("steps",[])
    csteps=c["jobs"]["consumer"].get("steps",[])
    require(any("actions/upload-artifact@v4"==x.get("uses") for x in psteps),"PRODUCER_UPLOAD")
    require(any("actions/checkout@v4"==x.get("uses") for x in csteps),"CONSUMER_CHECKOUT")
    commands="\n".join(str(x.get("run","")) for x in csteps)
    require("scripts.ess_v18_provider_native_fetch" in commands,"NATIVE_FETCH")
    require("scripts.ess_v18_consumer_preflight_adapter" in commands,"PREFLIGHT")
    require("scripts.ess_v18_zip_payload_custody" in commands,"ZIP_CUSTODY")
    require("HOLD_TWO_RUN_PROVIDER_AUTHENTICATION_NOT_WIRED" not in commands,"OLD_BLOCKER")
    require("Download exact producer from same run" not in str(csteps),"SAME_RUN_DOWNLOAD")
    return "PASS_SPLIT_STATIC_STRUCTURE"

def main():
    require(LEGACY.is_file(),"LEGACY_FILE_MISSING")
    print(check(PRODUCER,CONSUMER))
    print("LEGACY_COMBINED_WORKFLOW=EXCLUDED_FROM_TWO_RUN_ADMISSION")
    print("NATIVE_REGISTRATION=NOT_EVALUATED")
    print("RUNTIME_EXECUTION=NOT_EVALUATED")

if __name__=="__main__":
    try: main()
    except (ValueError,OSError,yaml.YAMLError) as e:
        print(str(e),file=sys.stderr)
        sys.exit(1)
