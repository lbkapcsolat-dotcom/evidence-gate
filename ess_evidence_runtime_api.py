from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ess_evidence_runtime import build_receipt, replay_receipt

class Handler(BaseHTTPRequestHandler):
    server_version="ESS-Evidence-Runtime/1"
    def log_message(self,fmt,*args): pass
    def _send(self,status,obj):
        b=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_POST(self):
        if self.path not in ("/v1/admit","/v1/replay"):
            return self._send(404,{"error":"not_found"})
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<=0 or n>1048576:
                return self._send(413,{"error":"invalid_content_length"})
            obj=json.loads(self.rfile.read(n))
            out=build_receipt(obj) if self.path=="/v1/admit" else replay_receipt(obj)
            return self._send(200 if self.path=="/v1/admit" or out["valid"] else 409,out)
        except (json.JSONDecodeError,KeyError,TypeError,ValueError) as e:
            return self._send(400,{"error":str(e)})

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=8765)
    a=p.parse_args()
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()

if __name__=="__main__":
    main()
