"""Tests for the viewer static server."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import pytest

from gpxflythrough.viewer.server import ViewServer


@pytest.fixture
def dist_dir(tmp_path: Path) -> Path:
    """Create a minimal dist directory with index.html."""
    index_html = tmp_path / "index.html"
    _ = index_html.write_text(
        "<!DOCTYPE html><html><head></head><body>"
        + '<div id="cesiumContainer"></div>'
        + '<script type="module" src="/src/main.ts"></script>'
        + "</body></html>"
    )
    return tmp_path


class TestViewServer:
    def test_starts_and_returns_port(self, dist_dir: Path) -> None:
        server = ViewServer(dist_dir, '{"test": true}')
        port = server.start()
        assert port > 0
        try:
            response = urlopen(f"http://127.0.0.1:{port}/")
            html = response.read().decode("utf-8")
            assert "globalThis.__trackData" in html
        finally:
            server.stop()

    def test_injects_track_data(self, dist_dir: Path) -> None:
        payload = '{"schema_version":"1.0.0"}'
        server = ViewServer(dist_dir, payload)
        port = server.start()
        try:
            response = urlopen(f"http://127.0.0.1:{port}/")
            html = response.read().decode("utf-8")
            assert 'globalThis.__trackData = {"schema_version":"1.0.0"}' in html
        finally:
            server.stop()

    def test_serves_static_files(self, dist_dir: Path) -> None:
        _ = (dist_dir / "test.js").write_text("console.log('hello');")
        server = ViewServer(dist_dir, "{}")
        port = server.start()
        try:
            response = urlopen(f"http://127.0.0.1:{port}/test.js")
            content = response.read().decode("utf-8")
            assert "console.log" in content
            assert "javascript" in response.headers.get("Content-Type", "")
        finally:
            server.stop()

    def test_404_for_missing(self, dist_dir: Path) -> None:
        server = ViewServer(dist_dir, "{}")
        port = server.start()
        try:
            with pytest.raises(Exception, match=""):  # noqa: PT011
                urlopen(f"http://127.0.0.1:{port}/nonexistent.js")
        finally:
            server.stop()

    def test_stop_closes_server(self, dist_dir: Path) -> None:
        server = ViewServer(dist_dir, "{}")
        port = server.start()
        server.stop()
        with pytest.raises(Exception, match=""):  # noqa: PT011
            urlopen(f"http://127.0.0.1:{port}/", timeout=1)
