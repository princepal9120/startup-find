"""Local HTTP server so non-Python agents (curl, JS, anything) can query startup-find."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .db import (q_companies, q_stats, q_batches, q_company, get_conn,
                 coerce, DEFAULT_DB)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # quiet

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        db = qs.get("db", DEFAULT_DB)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path in ("/", "/health"):
                return self._send(200, {"status": "ok", "service": "startup-find"})
            if path == "/stats":
                return self._send(200, q_stats(db))
            if path == "/batches":
                return self._send(200, q_batches(db))
            if path == "/companies":
                def _b(v): return v.lower() == "true" if v in ("true", "false") else None
                rows = q_companies(
                    db,
                    int(qs.get("limit", 50)), int(qs.get("offset", 0)),
                    qs.get("batch"), qs.get("industry"), qs.get("country"),
                    _b(qs.get("is_hiring", "")), _b(qs.get("top_company", "")),
                    qs.get("search"), qs.get("source"))
                return self._send(200, {"companies": rows, "total": len(rows)})
            if path == "/search":
                if "q" not in qs:
                    return self._send(400, {"error": "missing q"})
                rows = q_companies(
                    db, int(qs.get("limit", 50)), 0, None, None, None, None, None,
                    qs.get("q"), qs.get("source"))
                return self._send(200, {"companies": rows, "total": len(rows)})
            if path == "/company":
                row = (q_company(db, slug=qs["slug"]) if "slug" in qs
                       else q_company(db, cid=int(qs["id"])) if "id" in qs else None)
                if not row:
                    return self._send(404, {"error": "not found"})
                return self._send(200, row)
            return self._send(404, {"error": "unknown route"})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": str(e)})


def serve(host: str = "127.0.0.1", port: int = 8731):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"startup-find serving on http://{host}:{port}  (Ctrl-C to stop)")
    print("  GET /stats  /batches  /companies?batch=...&is_hiring=true  "
          "/search?q=...  /company?slug=...  /company?id=...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
