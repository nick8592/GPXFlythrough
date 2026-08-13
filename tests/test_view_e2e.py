"""End-to-end tests for the viewer pipeline.

Verifies the full flow: GPX → parse → sanitize → payload → server → HTTP response.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import orjson
import pytest

from gpxflythrough.parser import parse_gpx_file
from gpxflythrough.sanitize import sanitize
from gpxflythrough.viewer.payload import ViewOptions, build_view_payload
from gpxflythrough.viewer.server import ViewServer

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
NANGANG_GPX = EXAMPLES_DIR / "Nangang_Ridge_Hike.gpx"

skip_if_no_example = pytest.mark.skipif(
    not NANGANG_GPX.is_file(),
    reason="Example GPX file not found",
)


@pytest.fixture()
def dist_dir(tmp_path: Path) -> Path:
    """Create a minimal dist directory mimicking the Vite build output."""
    index_html = tmp_path / "index.html"
    index_html.write_text(
        "<!DOCTYPE html><html><head></head><body>"
        '<div id="cesiumContainer"></div>'
        '<script type="module" src="/src/main.ts"></script>'
        "</body></html>"
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index.js").write_text(
        'console.log("renderer bundle");'
    )
    return tmp_path


class TestViewerE2E:
    @skip_if_no_example
    def test_full_pipeline_with_real_gpx(
        self, dist_dir: Path
    ) -> None:
        track = parse_gpx_file(NANGANG_GPX)
        sanitized = sanitize(track)

        opts = ViewOptions(no_terrain=True, theme="dark")
        payload_bytes = build_view_payload(sanitized, opts)
        payload_json = payload_bytes.decode("utf-8")

        parsed = orjson.loads(payload_bytes)
        assert parsed["schema_version"] == "1.0.0"
        assert len(parsed["track"]["segments"]) > 0
        assert parsed["render"]["no_terrain"] is True

        server = ViewServer(dist_dir, payload_json)
        port = server.start()
        try:
            response = urlopen(f"http://127.0.0.1:{port}/")
            html = response.read().decode("utf-8")
            assert "globalThis.__trackData" in html
            assert "cesiumContainer" in html
        finally:
            server.stop()

    @skip_if_no_example
    def test_payload_has_nangang_track_data(
        self, dist_dir: Path
    ) -> None:
        track = parse_gpx_file(NANGANG_GPX)
        sanitized = sanitize(track)

        payload_bytes = build_view_payload(sanitized, ViewOptions())
        payload_json = payload_bytes.decode("utf-8")

        server = ViewServer(dist_dir, payload_json)
        port = server.start()
        try:
            response = urlopen(f"http://127.0.0.1:{port}/")
            html = response.read().decode("utf-8")
            assert "南港" in html or "Nangang" in html
        finally:
            server.stop()

    @skip_if_no_example
    def test_serves_static_assets(
        self, dist_dir: Path
    ) -> None:
        track = parse_gpx_file(NANGANG_GPX)
        sanitized = sanitize(track)
        payload_bytes = build_view_payload(sanitized, ViewOptions())
        payload_json = payload_bytes.decode("utf-8")

        server = ViewServer(dist_dir, payload_json)
        port = server.start()
        try:
            response = urlopen(
                f"http://127.0.0.1:{port}/assets/index.js"
            )
            content = response.read().decode("utf-8")
            assert "renderer bundle" in content
        finally:
            server.stop()

    @skip_if_no_example
    def test_cumulative_meters_non_decreasing(self) -> None:
        track = parse_gpx_file(NANGANG_GPX)
        sanitized = sanitize(track)

        payload_bytes = build_view_payload(sanitized, ViewOptions())
        parsed = orjson.loads(payload_bytes)

        for seg in parsed["track"]["segments"]:
            prev_cum = -1.0
            for pt in seg["points"]:
                assert pt["cumulative_m"] >= prev_cum
                prev_cum = pt["cumulative_m"]
