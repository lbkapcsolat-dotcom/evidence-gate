#!/usr/bin/env python3
"""Reject archive/payload divergence and unsafe ZIP members before consumer replay."""
import hashlib, json, stat, sys, zipfile
from pathlib import Path
from scripts.ess_v18_two_run_contract import require, REQUIRED

def verify_zip_custody(archive_path, payload_dir, provider_digest):
    archive = Path(archive_path)
    require(archive.is_file() and not archive.is_symlink(), "ZIP_MISSING")
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == provider_digest.removeprefix("sha256:"), "ZIP_PROVIDER_DIGEST")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        names = [m.filename for m in members]
        require(len(names) == len(set(names)), "ZIP_DUPLICATE_MEMBER")
        require(set(names) == set(REQUIRED), "ZIP_MEMBER_SET")
        for m in members:
            name = m.filename
            require(not m.is_dir() and not name.startswith("/") and ".." not in Path(name).parts, "ZIP_PATH")
            require((m.external_attr >> 16) & 0o170000 != stat.S_IFLNK, "ZIP_SYMLINK")
            require(m.file_size <= 50_000_000, "ZIP_SIZE_LIMIT")
            actual = (Path(payload_dir) / name)
            require(actual.is_file() and not actual.is_symlink(), "PAYLOAD_MISSING")
            require(hashlib.sha256(z.read(m)).digest() == hashlib.sha256(actual.read_bytes()).digest(), "ZIP_PAYLOAD_MISMATCH")
    return {"verdict":"PASS_ZIP_PAYLOAD_CUSTODY","member_count":len(members)}

if __name__ == "__main__":
    try:
        require(len(sys.argv) == 4, "USAGE")
        print(json.dumps(verify_zip_custody(sys.argv[1],sys.argv[2],sys.argv[3])))
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        print(str(e),file=sys.stderr)
        sys.exit(1)
