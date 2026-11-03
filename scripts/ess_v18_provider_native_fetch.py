#!/usr/bin/env python3
"""GitHub-native two-run producer fetch. Authenticated API over HTTPS; fail closed."""
import hashlib, json, os, re, sys, urllib.request, urllib.error
from pathlib import Path
from scripts.ess_v18_two_run_contract import require
from scripts.ess_v18_zip_payload_custody import verify_zip_custody
import zipfile

def fetch(url, token, accept="application/vnd.github+json"):
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":accept,"X-GitHub-Api-Version":"2022-11-28","User-Agent":"ESS-V18-custody"})
    with urllib.request.urlopen(req,timeout=30) as response:
        return response.read()

def main():
    repo=os.environ["GITHUB_REPOSITORY"]
    token=os.environ["GITHUB_TOKEN"]
    producer_id=os.environ["ESS_V18_PRODUCER_RUN_ID"]
    expected_sha=os.environ["ESS_V18_EXPECTED_PRODUCER_SHA"]
    workflow=os.environ["ESS_V18_EXPECTED_PRODUCER_WORKFLOW"]
    consumer_id=os.environ["GITHUB_RUN_ID"]
    require(re.fullmatch(r"[1-9][0-9]*",producer_id) is not None,"PRODUCER_ID")
    require(producer_id!=consumer_id,"NOT_TWO_RUNS")
    require(re.fullmatch(r"[0-9a-f]{40}",expected_sha) is not None,"EXPECTED_SHA")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo) is not None,"REPOSITORY")
    require(workflow.startswith(".github/workflows/") and ".." not in workflow,"WORKFLOW_PATH")
    base="https://api.github.com/repos/"+repo
    run=json.loads(fetch(base+"/actions/runs/"+producer_id,token))
    require(str(run["id"])==producer_id and run["status"]=="completed" and run["conclusion"]=="success","PRODUCER_STATUS")
    require(run["head_sha"]==expected_sha,"PRODUCER_SHA")
    require(run["repository"]["full_name"]==repo,"PRODUCER_REPOSITORY")
    require(run["path"]==workflow,"PRODUCER_WORKFLOW")
    require(run["event"]=="workflow_dispatch","PRODUCER_EVENT")
    require(int(run["run_attempt"])==1,"PRODUCER_ATTEMPT")
    artifacts=json.loads(fetch(base+"/actions/runs/"+producer_id+"/artifacts?per_page=100",token))
    require(artifacts["total_count"]<=100,"ARTIFACT_PAGINATION")
    name="ess-v18-producer-"+producer_id
    matching=[a for a in artifacts["artifacts"] if a["name"]==name]
    require(len(matching)==1,"ARTIFACT_UNIQUE")
    a=matching[0]
    require(not a["expired"] and a["workflow_run"]["id"]==int(producer_id),"ARTIFACT_LIVE_RUN")
    digest=a.get("digest","")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}",digest) is not None,"ARTIFACT_DIGEST")
    require(a["id"]>0,"ARTIFACT_ID")
    archive_bytes=fetch(base+"/actions/artifacts/"+str(a["id"])+"/zip",token,"application/vnd.github+json")
    require(hashlib.sha256(archive_bytes).hexdigest()==digest[7:],"ARCHIVE_DIGEST")
    root=Path(os.environ["RUNNER_TEMP"])/"ess_v18_two_run"
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    archive=root/"producer.zip"
    archive.write_bytes(archive_bytes)
    payload=root/"payload"
    payload.mkdir(mode=0o700,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        # Never extract untrusted ZIP members before validation.
        from scripts.ess_v18_two_run_contract import REQUIRED
        names=[i.filename for i in z.infolist()]
        require(len(names)==len(set(names)) and set(names)==set(REQUIRED),"ZIP_MEMBER_SET")
        for item in z.infolist():
            require(not item.is_dir() and item.file_size<=50_000_000,"ZIP_MEMBER_UNSAFE")
            (payload/item.filename).write_bytes(z.read(item))
    verify_zip_custody(archive,payload,digest)
    manifest=json.loads((payload/"export-manifest.json").read_text())
    require(manifest["source_run_id"]==producer_id and manifest["source_sha"]==expected_sha,"MANIFEST_PRODUCER")
    contract={"producer":{"run_id":int(producer_id),"run_attempt":run["run_attempt"],"commit_sha":expected_sha,"status":run["status"],"conclusion":run["conclusion"],"repository":repo,"workflow_path":workflow},"consumer":{"run_id":int(consumer_id),"run_attempt":int(os.environ["GITHUB_RUN_ATTEMPT"]),"commit_sha":os.environ["GITHUB_SHA"],"repository":repo},"expected_producer_commit":expected_sha,"expected_producer_workflow":workflow}
    metadata={"repository":repo,"workflow_path":workflow,"run_id":int(producer_id),"run_attempt":run["run_attempt"],"count_matching_name":1,"expired":False,"id":a["id"],"name":name,"provider_digest":digest}
    (root/"contract.json").write_text(json.dumps(contract))
    (root/"provider.json").write_text(json.dumps(metadata))
    with open(os.environ["GITHUB_ENV"],"a") as out:
        for key,value in {"ESS_V18_CONTRACT":root/"contract.json","ESS_V18_PROVIDER_METADATA":root/"provider.json","ESS_V18_PRODUCER_ARCHIVE":archive,"ESS_V18_PRODUCER_FILES":payload,"PINNED_V1_8_SOURCE_RUN":producer_id,"PINNED_V1_8_SOURCE_SHA":expected_sha}.items():
            print(f"{key}={value}",file=out)
    print(json.dumps({"verdict":"PASS_PROVIDER_NATIVE_FETCH_AND_ARCHIVE","producer_run":producer_id,"artifact_id":a["id"],"archive_sha256":digest[7:]}))

if __name__=="__main__":
    try: main()
    except (ValueError,KeyError,OSError,urllib.error.URLError,zipfile.BadZipFile) as exc:
        print("HOLD_PROVIDER_FETCH: "+str(exc),file=sys.stderr)
        sys.exit(1)
