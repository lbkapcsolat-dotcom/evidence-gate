import hashlib, tempfile, unittest, zipfile
from pathlib import Path
from scripts.ess_v18_two_run_contract import REQUIRED
from scripts.ess_v18_zip_payload_custody import ARCHIVE_REQUIRED
from scripts.ess_v18_zip_payload_custody import verify_zip_custody

class ZipCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.payload = self.root / "payload"
        self.payload.mkdir()
        for name in REQUIRED:
            (self.payload / name).write_bytes(name.encode())
        with (self.payload / "producer-sha256.txt").open("w") as out:
            for name in REQUIRED:
                out.write(hashlib.sha256((self.payload/name).read_bytes()).hexdigest()+"  "+name+"\n")
        self.archive = self.root / "producer.zip"
        self.repack()

    def repack(self, replace=None, extra=None):
        with zipfile.ZipFile(self.archive, "w") as z:
            for name in ARCHIVE_REQUIRED:
                z.writestr(name, (replace or {}).get(name, (self.payload/name).read_bytes()))
            if extra: z.writestr(extra, b"unexpected")
        self.digest = "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_valid(self):
        self.assertEqual(verify_zip_custody(self.archive,self.payload,self.digest)["member_count"],len(ARCHIVE_REQUIRED))

    def test_payload_tamper(self):
        (self.payload / REQUIRED[0]).write_bytes(b"tamper")
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_PAYLOAD_MISMATCH"):
            verify_zip_custody(self.archive,self.payload,self.digest)

    def test_archive_digest_tamper(self):
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_PROVIDER_DIGEST"):
            verify_zip_custody(self.archive,self.payload,"sha256:"+"0"*64)

    def test_archive_member_tamper(self):
        self.repack(replace={REQUIRED[0]:b"tamper"})
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_PAYLOAD_MISMATCH"):
            verify_zip_custody(self.archive,self.payload,self.digest)

    def test_extra_member(self):
        self.repack(extra="../escape")
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_MEMBER_SET"):
            verify_zip_custody(self.archive,self.payload,self.digest)

    def test_missing_archive(self):
        self.archive.unlink()
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_MISSING"):
            verify_zip_custody(self.archive,self.payload,self.digest)
