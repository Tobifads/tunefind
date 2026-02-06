from __future__ import annotations

import json
import mimetypes
import platform
import shutil
import sys
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import cgi

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.service import TuneFindService
from app.audio import _find_keyfinder_cli

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

    def _safe_json_error(self, err: Exception, status: int = 500) -> None:
        try:
            self._send_json({"error": str(err)}, status=status)
        except Exception:
            pass

    def _diagnostics(self) -> dict:
        try:
            import pydub  # noqa: F401
            pydub_ok = True
        except Exception:
            pydub_ok = False
        ffmpeg_path = shutil.which("ffmpeg")
        keyfinder_path = _find_keyfinder_cli()
        return {
            "status": "ok",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "ffmpeg": ffmpeg_path,
            "ffprobe": shutil.which("ffprobe"),
            "keyfinder": keyfinder_path,
            "keyfinder_required": True,
            "dependencies_ready": bool(ffmpeg_path and keyfinder_path),
            "pydub": pydub_ok,
        }

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
        try:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                return self._send_file(WEB_DIR / "index.html")
            if parsed.path.startswith("/static/"):
                return self._send_file(WEB_DIR / parsed.path.removeprefix("/static/"))
            if parsed.path == "/health":
                return self._send_json({"status": "ok"})
            if parsed.path == "/diagnostics":
                return self._send_json(self._diagnostics())
            if parsed.path == "/uploads":
                params = parse_qs(parsed.query or "")
                owner_id = params.get("owner_id", [None])[0]
                if not owner_id:
                    return self._send_json({"error": "owner_id is required"}, status=400)
                service = self._service()
                try:
                    return self._send_json(service.list_uploads(owner_id), status=200)
                except Exception as err:
                    return self._send_json({"error": str(err)}, status=500)
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as err:
            traceback.print_exc()
            self._safe_json_error(err)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        try:
            parsed = urlparse(self.path)
            if parsed.path not in {"/upload", "/search", "/uploads/delete", "/uploads/delete-one"}:
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
            bpm_raw = form.getfirst("bpm")
            bpm = int(bpm_raw) if bpm_raw and bpm_raw.isdigit() else None
            key = form.getfirst("key") or None
            skip_duplicates = form.getfirst("skip_duplicates") == "1"

            file_item = form["file"] if "file" in form else None
            if file_item is None:
                return self._send_json({"error": "file is required"}, status=400)

            service = self._service()

            try:
                if parsed.path == "/upload":
                    files = []
                    if isinstance(file_item, list):
                        for item in file_item:
                            if not item.file or not item.filename:
                                continue
                            files.append((item.filename, item.file.read()))
                    else:
                        if file_item.file is None or not file_item.filename:
                            return self._send_json({"error": "file is required"}, status=400)
                        files.append((file_item.filename, file_item.file.read()))

                    if not files:
                        return self._send_json({"error": "file is required"}, status=400)

                    result = service.upload_beats(owner_id, files, bpm=bpm, key=key, skip_duplicates=skip_duplicates)
                elif parsed.path == "/search":
                    top_k = form.getfirst("top_k", "5")
                    if file_item.file is None:
                        return self._send_json({"error": "file is required"}, status=400)
                    result = service.search_by_hum(owner_id, file_item.file.read(), top_k=int(top_k))
                elif parsed.path == "/uploads/delete-one":
                    beat_id = form.getfirst("beat_id")
                    if not beat_id:
                        return self._send_json({"error": "beat_id is required"}, status=400)
                    result = service.delete_upload(owner_id, beat_id)
                else:
                    result = service.delete_uploads(owner_id)
            except ValueError as err:
                return self._send_json({"error": str(err)}, status=400)
            except Exception as err:
                traceback.print_exc()
                return self._send_json({"error": str(err)}, status=500)

            self._send_json(result, status=200)
        except Exception as err:
            traceback.print_exc()
            self._safe_json_error(err)


def run(host: str = "0.0.0.0", port: int = 8000, data_dir: str = "data") -> None:
    httpd = HTTPServer((host, port), TuneFindHandler)
    httpd.data_dir = data_dir
    print(f"TuneFind server running on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run TuneFind local server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    run(args.host, args.port, args.data_dir)
