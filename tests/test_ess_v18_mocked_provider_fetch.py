"""Mock GitHub API + ZIP negative tests. No network, no native Actions dispatch."""
import hashlib, io, json, os, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from scripts import ess_v18_provider_native_fetch as native
from scripts.ess_v18_two_run_contract import REQUIRED

PRODUCER="456123"
CONSUMER="789321"
SHA="a"*40
WORKFLOW=".github/workflows/ess-openshell-v18-producer-only.yml"
REPO="lbkapcsolat-dotcom/evidence-gate"

def make_archive():
    payload={name:name.encode() for name in REQUIRED}
    payload["export-manifest.json"]=json.dumps({"source_run_id":PRODUCER,"source_sha":SHA,
        "canonical_registry_file_sha256":hashlib.sha256(payload[REQUIRED[0]]).hexdigest(),
        "pinned_event_set_file_sha256":hashlib.sha256(payload[REQUIRED[1]]).hexdigest()}).encode()
    payload["producer-sha256.txt"]="".join(hashlib.sha256(payload[n]).hexdigest()+"  "+n+"\n" for n in REQUIRED).encode()
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        for name,data in payload.items(): z.writestr(name,data)
    return b.getvalue()

class MockNativeFetchTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.env={"GITHUB_REPOSITORY":REPO,"GITHUB_TOKEN":"fake-token","ESS_V18_PRODUCER_RUN_ID":PRODUCER,
          "ESS_V18_EXPECTED_PRODUCER_SHA":SHA,"ESS_V18_EXPECTED_PRODUCER_WORKFLOW":WORKFLOW,
          "GITHUB_RUN_ID":CONSUMER,"GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"b"*40,
          "RUNNER_TEMP":self.t.name,"GITHUB_ENV":str(Path(self.t.name)/"github_env")}
        self.run={"id":int(PRODUCER),"status":"completed","conclusion":"success","head_sha":SHA,
          "repository":{"full_name":REPO},"path":WORKFLOW,"event":"workflow_dispatch","run_attempt":1}
        self.archive=make_archive()
        self.artifact={"id":999,"name":"ess-v18-producer-"+PRODUCER,"expired":False,
          "workflow_run":{"id":int(PRODUCER)},"digest":"sha256:"+hashlib.sha256(self.archive).hexdigest()}
        self.fetch_calls=[]
    def fake_fetch(self,url,token,accept="application/vnd.github+json"):
        self.fetch_calls.append(url)
        if url.endswith("/actions/runs/"+PRODUCER): return json.dumps(self.run).encode()
        if "/artifacts?per_page=100" in url:return json.dumps({"total_count":1,"artifacts":[self.artifact]}).encode()
        if url.endswith("/zip"):return self.archive
        raise AssertionError(url)
    def invoke(self):
        with patch.dict(os.environ,self.env,clear=True),patch.object(native,"fetch",side_effect=self.fake_fetch),patch.object(native,"verify_zip_custody",return_value={"verdict":"PASS"}):
            native.main()
    def reject(self,code):
        with self.assertRaisesRegex(ValueError,"HOLD_"+code):self.invoke()
        self.assertFalse(Path(self.env["GITHUB_ENV"]).exists())
    def test_valid_mock(self):
        self.invoke()
        e=Path(self.env["GITHUB_ENV"]).read_text()
        self.assertIn("PINNED_V1_8_SOURCE_RUN="+PRODUCER,e)
        self.assertIn("PINNED_V1_8_ARTIFACT_ID=999",e)
    def test_wrong_run_sha(self):
        self.run["head_sha"]="c"*40
        self.reject("PRODUCER_SHA")
    def test_wrong_workflow(self):
        self.run["path"]=".github/workflows/legacy.yml"
        self.reject("PRODUCER_WORKFLOW")
    def test_wrong_repo(self):
        self.run["repository"]["full_name"]="other/repo"
        self.reject("PRODUCER_REPOSITORY")
    def test_wrong_event(self):
        self.run["event"]="push"
        self.reject("PRODUCER_EVENT")
    def test_failed_run(self):
        self.run["conclusion"]="failure"
        self.reject("PRODUCER_STATUS")
    def test_wrong_artifact_digest(self):
        self.artifact["digest"]="sha256:"+"0"*64
        self.reject("ARCHIVE_DIGEST")
    def test_expired_artifact(self):
        self.artifact["expired"]=True
        self.reject("ARTIFACT_LIVE_RUN")
    def test_archive_extra_member(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            with zipfile.ZipFile(io.BytesIO(self.archive)) as old:
                for item in old.infolist():z.writestr(item.filename,old.read(item))
            z.writestr("unexpected.txt",b"bad")
        self.archive=b.getvalue()
        self.artifact["digest"]="sha256:"+hashlib.sha256(self.archive).hexdigest()
        self.reject("ZIP_MEMBER_SET")
    def test_manifest_source_mismatch(self):
        self.archive=make_archive().replace(b"nonexistent-marker",b"other")
        # A manifest mismatch requires rebuilding the ZIP; exercise a wrong run ID via a ZIP rewrite.
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            with zipfile.ZipFile(io.BytesIO(self.archive)) as old:
                for item in old.infolist():
                    data=old.read(item)
                    if item.filename=="export-manifest.json":data=data.replace(PRODUCER.encode(),b"111111")
                    z.writestr(item.filename,data)
        self.archive=b.getvalue()
        self.artifact["digest"]="sha256:"+hashlib.sha256(self.archive).hexdigest()
        self.reject("MANIFEST_PRODUCER")

if __name__=="__main__":unittest.main()
