from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from eq64_executable_assurance_engine import canonical_bytes, replay_assurance_receipt

MANIFEST_SCHEMA = "EQ64_INDEPENDENT_REPRODUCTION_PACKAGE_MANIFEST_V1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(root: str | Path, relative_paths: Iterable[str]) -> dict[str, Any]:
    root = Path(root)
    entries: list[dict[str, Any]] = []
    for rel in sorted(set(relative_paths)):
        path = root / rel
        data = path.read_bytes()
        entries.append(
            {
                "path": rel,
                "size_bytes": len(data),
                "sha256": _sha256_bytes(data),
            }
        )

    body = {
        "schema_version": MANIFEST_SCHEMA,
        "files": entries,
    }
    return {
        **body,
        "manifest_sha256": _sha256_bytes(canonical_bytes(body)),
    }


def verify_manifest(root: str | Path, manifest: dict[str, Any]) -> bool:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        return False

    files = manifest.get("files")
    if not isinstance(files, list):
        return False

    body = {
        "schema_version": manifest.get("schema_version"),
        "files": files,
    }
    if manifest.get("manifest_sha256") != _sha256_bytes(canonical_bytes(body)):
        return False

    root = Path(root)
    for entry in files:
        if not isinstance(entry, dict):
            return False
        rel = entry.get("path")
        if not isinstance(rel, str):
            return False
        path = root / rel
        if not path.is_file():
            return False
        data = path.read_bytes()
        if len(data) != entry.get("size_bytes"):
            return False
        if _sha256_bytes(data) != entry.get("sha256"):
            return False
    return True


def verify_tamper_rejection(receipt_path: str | Path) -> bool:
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a JSON object")

    tampered = copy.deepcopy(receipt)
    tampered["decision"] = "HOLD" if receipt.get("decision") == "PASS" else "PASS"
    result = replay_assurance_receipt(tampered)
    return result.get("valid") is False


def write_manifest(root: str | Path, relative_paths: Iterable[str], output: str | Path) -> dict[str, Any]:
    manifest = build_manifest(root, relative_paths)
    Path(output).write_bytes(canonical_bytes(manifest))
    return manifest
