"""Loopback-only HTTP transport; application services own behavior and storage."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
from sandtable.map_builder.values import Invalid


class ViewerHttpServer(ThreadingHTTPServer):
    def __init__(self, address, application):
        self.application = application
        super().__init__(address, ViewerRequestHandler)


class ViewerRequestHandler(BaseHTTPRequestHandler):
    def _check_origin(self):
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host.split(":")[0] not in ("127.0.0.1", "localhost"):
            raise Invalid("Loopback hosts only.")
        if origin and origin != "http://" + host:
            raise Invalid("Cross-origin execution is not accepted.")

    def _send(self, value, status=200, content_type="application/json; charset=utf-8"):
        body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method):
        try:
            self._check_origin()
            path = urlparse(self.path).path
            app = self.server.application
            if method == "POST":
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2000000:
                    raise Invalid("Expected JSON under 2 MB.")
                value, status = app.post(path, json.loads(self.rfile.read(length)))
                return self._send(value, status)
            if path.startswith("/api/"):
                return self._send(app.get(path))
            name = "index.html" if path == "/" else path.lstrip("/")
            asset = (app.paths.assets / name).resolve()
            if (
                not asset.is_relative_to(app.paths.assets)
                or not asset.is_file()
                or asset.suffix not in (".html", ".js", ".css")
            ):
                raise FileNotFoundError()
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[
                asset.suffix
            ]
            return self._send(asset.read_bytes(), content_type=mime + "; charset=utf-8")
        except (BrokenPipeError, ConnectionResetError):
            pass
        except FileNotFoundError:
            self._send(dict(error="Not found or result is not ready."), 404)
        except (KeyError, TypeError, ValueError, Invalid) as error:
            self._send(dict(error=str(error)), 400)
        except Exception as error:
            self._send(dict(error="Server error: " + str(error)), 500)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")
