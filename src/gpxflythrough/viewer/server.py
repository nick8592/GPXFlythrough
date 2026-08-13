"""Static file server with track data injection for the interactive viewer."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

_INJECT_MARKER = '<script type="module"'

_MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".wasm": "application/wasm",
    ".ico": "image/x-icon",
    ".map": "application/json",
}


class ViewServer:
    """Serves the renderer dist/ directory with track data injected into index.html."""

    def __init__(self, dist_dir: Path, payload_json: str) -> None:
        """Initialize the view server with dist directory and payload."""
        self._dist_dir: Path = dist_dir
        self._payload_json: str = payload_json
        self._server: ThreadingHTTPServer | None = None
        self._port: int = 0

    @property
    def port(self) -> int:
        """Return the bound port number."""
        return self._port

    def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        """Start the server. Returns the bound port."""
        dist_dir = self._dist_dir
        payload_json = self._payload_json

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                url_path = self.path.split("?")[0] or "/"
                file_path = dist_dir / (
                    url_path[1:] if url_path != "/" else "index.html"
                )

                if not file_path.is_file():
                    self.send_error(404)
                    return

                try:
                    content = file_path.read_bytes()
                except OSError:
                    self.send_error(500)
                    return

                # Inject track data into index.html
                if url_path == "/" or url_path.endswith("index.html"):
                    html = content.decode("utf-8")
                    inject = (
                        f"<script>globalThis.__trackData = {payload_json};</script>\n"
                    )
                    html = html.replace(_INJECT_MARKER, inject + _INJECT_MARKER)
                    content = html.encode("utf-8")

                ext = file_path.suffix.lower()
                content_type = _MIME_TYPES.get(ext, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                _ = self.wfile.write(content)

            @override
            def log_message(self, format: str, *args: object) -> None:
                # Suppress default request logging
                pass

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._port = self._server.server_address[1]

        # Run server in a daemon thread
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()

        return self._port

    def stop(self) -> None:
        """Stop the server gracefully."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
