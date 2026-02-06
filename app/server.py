from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
import cgi

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.service import TuneFindService

WEB_DIR = BASE_DIR / "web"


class TuneFindHandler(BaseHTTPRequestHandler):
    server_version = "TuneFindHTTP/0.1"

    def _service(self) -> TuneFindService:
        return TuneFindService(Path(self.server.data_dir))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            return self._send_file(WEB_DIR / "index.html")
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            return self._send_file(WEB_DIR / "static" / relative)
        if parsed.path == "/beats":
            params = urlparse(self.path).query
            owner_id = ""
            if params:
                parts = params.split("=")
                if len(parts) == 2 and parts[0] == "owner_id":
                    owner_id = parts[1]
            if not owner_id:
                return self._send_json({"error": "owner_id is required"}, status=400)
            service = self._service()
            return self._send_json(service.list_beats(owner_id), status=200)
        if parsed.path == "/health":
            return self._send_json({"status": "ok"})
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        if parsed.path not in {"/upload", "/search"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        ctype, _ = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected multipart/form-data")
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        owner_id = form.getfirst("owner_id")
        if not owner_id:
            return self._send_json({"error": "owner_id is required"}, status=400)

        file_item = form["file"] if "file" in form else None
        if not file_item or not file_item.file or not file_item.filename:
            return self._send_json({"error": "file is required"}, status=400)

        file_bytes = file_item.file.read()
        service = self._service()

        try:
            if parsed.path == "/upload":
                result = service.upload_beat(owner_id, file_item.filename, file_bytes)
            else:
                top_k = form.getfirst("top_k", "5")
                result = service.search_by_hum(owner_id, file_bytes, top_k=int(top_k))
        except ValueError as err:
            return self._send_json({"error": str(err)}, status=400)

        self._send_json(result, status=200)


def run(host: str = "0.0.0.0", port: int = 8000, data_dir: str = "data") -> None:
    httpd = HTTPServer((host, port), TuneFindHandler)
    httpd.data_dir = data_dir
    print(f"TuneFind server running on http://{host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run TuneFind local server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    run(args.host, args.port, args.data_dir)
