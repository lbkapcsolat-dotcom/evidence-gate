from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cognitive_oversight_runtime import build_receipt, replay_receipt


class Handler(BaseHTTPRequestHandler):
    server_version = "ESS-Cognitive-Oversight-Runtime/1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, obj):
        body = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ("/v1/cognitive-oversight/admit", "/v1/cognitive-oversight/replay"):
            return self._send(404, {"error": "not_found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 1048576:
                return self._send(413, {"error": "invalid_content_length"})
            obj = json.loads(self.rfile.read(n))
            out = build_receipt(obj) if self.path.endswith("/admit") else replay_receipt(obj)
            return self._send(200 if self.path.endswith("/admit") or out["valid"] else 409, out)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return self._send(400, {"error": str(exc)})


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
