from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from unified_evidence_source_runner import run_unified


COLLECTOR_VERSION = "live-source-collector-v1"
DEFAULT_POLICY_FILE = Path(__file__).with_name("source_policy_registry.json")
DEFAULT_OUTPUT_DIR = Path("live_evidence_run")
GITHUB_API = "https://api.github.com"
DRIVE_API = "https://www.googleapis.com/drive/v3"


class CollectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedSource:
    provider: str
    source_kind: str
    canonical_url: str
    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = None
    commit_sha: str | None = None
    drive_file_id: str | None = None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        req = urllib.request.Request(
            url,
            headers=dict(headers or {}),
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                req,
                timeout=self.timeout_seconds,
            ) as resp:
                return HttpResponse(
                    int(resp.status),
                    {k.lower(): v for k, v in resp.headers.items()},
                    resp.read(),
                )
        except urllib.error.HTTPError as exc:
            return HttpResponse(
                int(exc.code),
                {k.lower(): v for k, v in exc.headers.items()},
                exc.read(),
            )
        except urllib.error.URLError as exc:
            raise CollectorError(
                f"network_error: {exc.reason}"
            ) from exc


def _json(response: HttpResponse, context: str) -> dict[str, Any]:
    try:
        value = json.loads(response.body.decode("utf-8"))
    except Exception as exc:
        raise CollectorError(
            f"{context}: invalid JSON response"
        ) from exc
    if not isinstance(value, dict):
        raise CollectorError(f"{context}: JSON must be an object")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def parse_source_url(url: str) -> ParsedSource:
    if not isinstance(url, str) or not url.strip():
        raise CollectorError("source URL must be a non-empty string")

    parsed = urllib.parse.urlparse(url.strip())
    host = parsed.netloc.lower().split(":")[0]
    path = parsed.path.rstrip("/")

    if parsed.scheme not in {"http", "https"}:
        raise CollectorError("source URL must use http or https")

    if host in {"drive.google.com", "www.drive.google.com"}:
        match = re.fullmatch(r"/file/d/([^/]+)(?:/.*)?", path)
        if match:
            file_id = match.group(1)
            return ParsedSource(
                "google_drive",
                "file",
                f"https://drive.google.com/file/d/{file_id}/view",
                drive_file_id=file_id,
            )
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/open" and query.get("id"):
            file_id = query["id"][0]
            return ParsedSource(
                "google_drive",
                "file",
                f"https://drive.google.com/file/d/{file_id}/view",
                drive_file_id=file_id,
            )
        raise CollectorError("unsupported Google Drive URL")

    if host in {"github.com", "www.github.com"}:
        pr = re.fullmatch(r"/([^/]+)/([^/]+)/pull/(\d+)", path)
        if pr:
            owner, repo, number = pr.groups()
            return ParsedSource(
                "github",
                "pull_request",
                f"https://github.com/{owner}/{repo}/pull/{number}",
                owner=owner,
                repo=repo,
                pr_number=int(number),
            )
        commit = re.fullmatch(
            r"/([^/]+)/([^/]+)/commit/([0-9a-fA-F]{7,64})",
            path,
        )
        if commit:
            owner, repo, sha = commit.groups()
            return ParsedSource(
                "github",
                "commit",
                f"https://github.com/{owner}/{repo}/commit/{sha}",
                owner=owner,
                repo=repo,
                commit_sha=sha,
            )
        raise CollectorError("unsupported GitHub URL")

    raise CollectorError(f"unsupported source host: {host}")


def load_policy_registry(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectorError(f"cannot read policy registry: {exc}") from exc
    if not isinstance(value, dict):
        raise CollectorError("policy registry must contain an object")
    return value


def github_policy(
    registry: Mapping[str, Any],
    owner: str,
    repo: str,
) -> Mapping[str, Any]:
    policies = registry.get("github")
    key = f"{owner}/{repo}"
    if not isinstance(policies, Mapping):
        raise CollectorError("policy registry has no github section")
    policy = policies.get(key)
    if not isinstance(policy, Mapping):
        raise CollectorError(
            f"no frozen GitHub policy registered for repository {key}"
        )
    required = policy.get("required_workflows")
    if not isinstance(required, list) or not required:
        raise CollectorError(
            f"GitHub policy for {key} has no required_workflows"
        )
    return policy


def drive_policy(
    registry: Mapping[str, Any],
    file_id: str,
) -> Mapping[str, Any]:
    policies = registry.get("google_drive")
    if not isinstance(policies, Mapping):
        raise CollectorError("policy registry has no google_drive section")
    policy = policies.get(file_id)
    if not isinstance(policy, Mapping):
        raise CollectorError(
            f"no frozen Drive policy registered for file {file_id}"
        )
    if not isinstance(policy.get("expected"), Mapping):
        raise CollectorError(
            f"Drive policy for {file_id} has no expected constraints"
        )
    return policy


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": COLLECTOR_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def collect_github(
    source: ParsedSource,
    policy: Mapping[str, Any],
    transport: HttpTransport,
    token: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    assert source.owner and source.repo
    headers = _github_headers(token)

    if source.source_kind == "pull_request":
        assert source.pr_number is not None
        url = (
            f"{GITHUB_API}/repos/{source.owner}/{source.repo}"
            f"/pulls/{source.pr_number}"
        )
        response = transport.request(url, headers=headers)
        if response.status != 200:
            raise CollectorError(
                f"GitHub PR fetch failed with HTTP {response.status}"
            )
        pr = _json(response, "GitHub PR fetch")
        head = pr.get("head")
        if not isinstance(head, Mapping) or not isinstance(
            head.get("sha"),
            str,
        ):
            raise CollectorError("GitHub PR response has no head.sha")
        head_sha = head["sha"]
        snapshot = {
            "pull_request_number": source.pr_number,
            "pull_request_state": pr.get("state"),
            "pull_request_draft": pr.get("draft"),
            "pull_request_merged": pr.get("merged"),
            "head_sha": head_sha,
        }
    else:
        assert source.commit_sha is not None
        head_sha = source.commit_sha
        snapshot = {"commit_sha_from_url": head_sha}

    query = urllib.parse.urlencode(
        {"head_sha": head_sha, "per_page": 100}
    )
    url = (
        f"{GITHUB_API}/repos/{source.owner}/{source.repo}"
        f"/actions/runs?{query}"
    )
    response = transport.request(url, headers=headers)
    if response.status != 200:
        raise CollectorError(
            f"GitHub workflow fetch failed with HTTP {response.status}"
        )
    body = _json(response, "GitHub workflow fetch")
    raw_runs = body.get("workflow_runs")
    if not isinstance(raw_runs, list):
        raise CollectorError("GitHub response has no workflow_runs")

    runs = [
        {
            "run_id": item.get("id"),
            "run_number": item.get("run_number"),
            "name": item.get("name"),
            "status": item.get("status"),
            "conclusion": item.get("conclusion"),
        }
        for item in raw_runs
        if isinstance(item, Mapping)
    ]

    normalized = {
        "repository": f"{source.owner}/{source.repo}",
        "head_sha": head_sha,
        "required_workflows": list(policy["required_workflows"]),
        "workflow_runs": runs,
    }
    snapshot.update(
        {
            "provider": "github",
            "source_url": source.canonical_url,
            "workflow_runs": runs,
            "auth_mode": "token" if token else "anonymous",
        }
    )
    return normalized, snapshot


def collect_drive(
    source: ParsedSource,
    policy: Mapping[str, Any],
    transport: HttpTransport,
    token: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    assert source.drive_file_id
    file_id = source.drive_file_id
    headers = {
        "Accept": "application/json",
        "User-Agent": COLLECTOR_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    fields = "id,name,mimeType,size,parents,webViewLink"
    meta_url = (
        f"{DRIVE_API}/files/{urllib.parse.quote(file_id, safe='')}"
        f"?fields={urllib.parse.quote(fields, safe=',')}"
        "&supportsAllDrives=true"
    )
    meta_response = transport.request(meta_url, headers=headers)

    if meta_response.status == 404:
        record = {
            "drive_file_id": file_id,
            "retrieval_status": "not_found",
        }
        return (
            {
                "scope_name": policy["scope_name"],
                "required_artifacts": [
                    {
                        "drive_file_id": file_id,
                        "expected": dict(policy["expected"]),
                    }
                ],
                "drive_records": [record],
            },
            {
                "provider": "google_drive",
                "source_url": source.canonical_url,
                "metadata_http_status": 404,
            },
        )

    if meta_response.status in {401, 403}:
        record = {
            "drive_file_id": file_id,
            "retrieval_status": "unavailable",
        }
        return (
            {
                "scope_name": policy["scope_name"],
                "required_artifacts": [
                    {
                        "drive_file_id": file_id,
                        "expected": dict(policy["expected"]),
                    }
                ],
                "drive_records": [record],
            },
            {
                "provider": "google_drive",
                "source_url": source.canonical_url,
                "metadata_http_status": meta_response.status,
            },
        )

    if meta_response.status != 200:
        raise CollectorError(
            f"Drive metadata fetch failed with HTTP {meta_response.status}"
        )

    meta = _json(meta_response, "Drive metadata fetch")
    mime_type = meta.get("mimeType")
    raw_hash = None
    raw_size = None

    if not (
        isinstance(mime_type, str)
        and mime_type.startswith("application/vnd.google-apps.")
    ):
        media_url = (
            f"{DRIVE_API}/files/{urllib.parse.quote(file_id, safe='')}"
            "?alt=media&supportsAllDrives=true"
        )
        media_response = transport.request(media_url, headers=headers)
        if media_response.status == 200:
            raw_hash = sha256_bytes(media_response.body)
            raw_size = len(media_response.body)

    record = {
        "drive_file_id": file_id,
        "retrieval_status": "ok",
        "name": meta.get("name"),
        "mime_type": mime_type,
        "size_bytes": raw_size if raw_size is not None else meta.get("size"),
        "sha256": raw_hash,
        "parent_ids": meta.get("parents"),
    }
    normalized = {
        "scope_name": policy["scope_name"],
        "required_artifacts": [
            {
                "drive_file_id": file_id,
                "expected": dict(policy["expected"]),
            }
        ],
        "drive_records": [record],
    }
    snapshot = {
        "provider": "google_drive",
        "source_url": source.canonical_url,
        "metadata": meta,
        "raw_sha256": raw_hash,
        "raw_size_bytes": raw_size,
        "auth_mode": "token" if token else "anonymous",
    }
    return normalized, snapshot


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def run_url(
    source_url: str,
    *,
    policy_path: Path = DEFAULT_POLICY_FILE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: HttpTransport | None = None,
    github_token: str | None = None,
    drive_token: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = load_policy_registry(policy_path)
    source = parse_source_url(source_url)
    transport = transport or HttpTransport()

    if source.provider == "github":
        assert source.owner and source.repo
        normalized, snapshot = collect_github(
            source,
            github_policy(registry, source.owner, source.repo),
            transport,
            github_token,
        )
    else:
        assert source.drive_file_id
        normalized, snapshot = collect_drive(
            source,
            drive_policy(registry, source.drive_file_id),
            transport,
            drive_token,
        )

    unified_result, unified_receipt = run_unified(normalized)
    result = {
        "collector": COLLECTOR_VERSION,
        "source_url": source.canonical_url,
        "provider": source.provider,
        "source_kind": source.source_kind,
        "status": "PASS",
        "evidence_gate": unified_result,
    }
    receipt = {
        "collector": COLLECTOR_VERSION,
        "execution_status": "PASS",
        "source_url": source.canonical_url,
        "provider": source.provider,
        "source_kind": source.source_kind,
        "policy_registry_version": registry.get("registry_version"),
        "normalized_input_sha256": sha256_bytes(
            canonical_json_bytes(normalized)
        ),
        "live_snapshot_sha256": sha256_bytes(
            canonical_json_bytes(snapshot)
        ),
        "result_sha256": sha256_bytes(
            canonical_json_bytes(result)
        ),
        "live_snapshot": snapshot,
        "unified_runner_receipt": unified_receipt,
        "claim_ceiling": (
            "Only the frozen-policy claim for this registered source. "
            "Observed live values never create or widen the expected policy."
        ),
    }
    atomic_write_json(output_dir / "result.json", result)
    atomic_write_json(output_dir / "receipt.json", receipt)
    return result, receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a supported Drive or GitHub URL, normalize it, "
            "and run Evidence Gate."
        )
    )
    parser.add_argument("source_url")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    try:
        result, _ = run_url(
            args.source_url,
            policy_path=args.policy,
            output_dir=args.output_dir,
            github_token=os.getenv("GITHUB_TOKEN"),
            drive_token=os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN"),
        )
    except Exception as exc:
        atomic_write_json(
            args.output_dir / "result.json",
            {
                "collector": COLLECTOR_VERSION,
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        atomic_write_json(
            args.output_dir / "receipt.json",
            {
                "collector": COLLECTOR_VERSION,
                "execution_status": "ERROR",
                "claim_promoted": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return 2

    print(
        json.dumps(
            {
                "provider": result["provider"],
                "status": result["evidence_gate"]["classification"]["status"],
                "result_file": str(args.output_dir / "result.json"),
                "receipt_file": str(args.output_dir / "receipt.json"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
