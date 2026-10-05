from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

GATE_ID = "CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_CANARY_V1"
OUT_DIR = Path("ch11c_live_sources")
MANIFEST_PATH = Path("CH11C__LIVE_FETCH_MANIFEST_V1.json")
MAX_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 30

ALLOWLIST = {
    "water": {
        "host": "environment.data.gov.uk",
        "path": "/flood-monitoring/id/measures/1100TH-flow--Mean-15_min-m3_s/readings",
        "provider": "Environment Agency",
        "role": "freshwater.internal_flow_rate",
    },
    "electricity": {
        "host": "data.elexon.co.uk",
        "path": "/bmrs/api/v1/datasets/INDO",
        "provider": "Elexon Insights Solution",
        "role": "electricity.consumption_rate",
    },
    "natural_gas": {
        "host": "transparency.entsog.eu",
        "path": "/api/v1/operationaldatas.csv",
        "provider": "ENTSOG Transparency Platform",
        "role": "natural_gas.import_rate",
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_allowed_url(url: str, source_id: str) -> None:
    spec = ALLOWLIST[source_id]
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError(f"HOLD_CH11C_NON_HTTPS:{source_id}")
    if parsed.hostname != spec["host"]:
        raise RuntimeError(
            f"HOLD_CH11C_REDIRECT_HOST_NOT_ALLOWED:{source_id}:{parsed.hostname}"
        )
    if parsed.path != spec["path"]:
        raise RuntimeError(
            f"HOLD_CH11C_PATH_NOT_ALLOWED:{source_id}:{parsed.path}"
        )


class AllowlistRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source_id = req.headers.get("X-Ch11c-Source-Id")
        if not source_id:
            raise RuntimeError("HOLD_CH11C_REDIRECT_SOURCE_ID_MISSING")
        check_allowed_url(newurl, source_id)
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            new_req.add_header("X-Ch11c-Source-Id", source_id)
        return new_req


def source_urls(now: datetime) -> dict[str, str]:
    d0 = (now - timedelta(days=1)).date().isoformat()
    d1 = (now + timedelta(days=1)).date().isoformat()
    water_q = urlencode({"_view": "full", "_sorted": "", "_limit": "1"})
    electricity_q = urlencode({"format": "json"})
    gas_q = urlencode({
        "indicator": "Physical Flow",
        "pointDirection": "de-tso-0005itp-00188entry",
        "from": d0,
        "to": d1,
        "periodType": "hour",
        "timeZone": "CET",
        "limit": "100",
        "offset": "0",
    })
    return {
        "water": f"https://environment.data.gov.uk/flood-monitoring/id/measures/1100TH-flow--Mean-15_min-m3_s/readings?{water_q}",
        "electricity": f"https://data.elexon.co.uk/bmrs/api/v1/datasets/INDO?{electricity_q}",
        "natural_gas": f"https://transparency.entsog.eu/api/v1/operationaldatas.csv?{gas_q}",
    }


def fetch_one(opener, source_id: str, url: str, fetched_at: str) -> dict:
    check_allowed_url(url, source_id)
    req = Request(
        url,
        method="GET",
        headers={
            "User-Agent": "Equilibrium-Stability-CH11C-ReadOnly-Canary/1.0",
            "Accept": "application/json,text/csv,text/plain,text/html;q=0.9,*/*;q=0.1",
            "X-Ch11c-Source-Id": source_id,
        },
    )
    with opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
        final_url = resp.geturl()
        check_allowed_url(final_url, source_id)
        status = int(getattr(resp, "status", 200))
        if status != 200:
            raise RuntimeError(f"HOLD_CH11C_HTTP_STATUS:{source_id}:{status}")
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise RuntimeError(f"HOLD_CH11C_RESPONSE_TOO_LARGE:{source_id}")
        content_type = resp.headers.get("Content-Type", "")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{source_id}.bin"
    path.write_bytes(data)

    spec = ALLOWLIST[source_id]
    return {
        "source_id": source_id,
        "provider": spec["provider"],
        "role": spec["role"],
        "method": "GET",
        "requested_url": url,
        "final_url": final_url,
        "http_status": status,
        "content_type": content_type,
        "fetched_at": fetched_at,
        "byte_length": len(data),
        "sha256": sha256_bytes(data),
        "local_capture": str(path),
        "external_write": False,
        "request_body_bytes": 0,
    }


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fetched_at = now.isoformat().replace("+00:00", "Z")
    urls = source_urls(now)
    opener = build_opener(AllowlistRedirectHandler())

    rows = []
    for source_id in ("water", "electricity", "natural_gas"):
        rows.append(fetch_one(opener, source_id, urls[source_id], fetched_at))

    manifest = {
        "schema_version": "CH11C_LIVE_FETCH_MANIFEST_V1",
        "gate_id": GATE_ID,
        "network_policy": {
            "read_only": True,
            "allowed_method": "GET",
            "request_body_bytes": 0,
            "credentials_used": False,
            "external_write": False,
            "external_actuation": False,
            "new_source_registration": False,
        },
        "allowlist": ALLOWLIST,
        "fetch_count": len(rows),
        "rows": rows,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    MANIFEST_PATH.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("CH11C_FETCH_MANIFEST_SHA256=" + sha256_bytes(canonical.encode("utf-8")))


if __name__ == "__main__":
    main()
