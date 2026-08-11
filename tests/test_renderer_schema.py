"""Unit tests for the renderer schema and payload builder.
"""

from __future__ import annotations

import json
import pytest
from datetime import UTC, datetime

from gpxflythrough.models import (
    SanitizationStats,
    SanitizedTrack,
    TrackData,
)
from gpxflythrough.renderer.exceptions import RenderSchemaError
from gpxflythrough.renderer.schema import (
    RenderOptions,
    build_render_payload,
    validate_render_options,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sanitized_with_extensions(track_with_extensions):
    return SanitizedTrack(
        track=track_with_extensions,
        stats=SanitizationStats(
            original_points=2,
            final_points=2,
            outliers_removed=0,
            points_interpolated=0,
            segments_merged=0,
            gaps_detected=0,
        ),
    )


@pytest.fixture
def empty_sanitized_track():
    track = TrackData(name="Empty", activity_type=None, time=None, segments=())
    return SanitizedTrack(
        track=track,
        stats=SanitizationStats(
            original_points=0,
            final_points=0,
            outliers_removed=0,
            points_interpolated=0,
            segments_merged=0,
            gaps_detected=0,
        ),
    )


@pytest.fixture
def track_with_waypoints_sanitized(track_with_waypoints):
    return SanitizedTrack(
        track=track_with_waypoints,
        stats=SanitizationStats(
            original_points=0,
            final_points=0,
            outliers_removed=0,
            points_interpolated=0,
            segments_merged=0,
            gaps_detected=0,
        ),
    )


# ── Tests ────────────────────────────────────────────────────────────

class TestBuildPayload:
    def test_bounds_correct_when_track(self, clean_sanitized_track):
        opts = RenderOptions()
        payload_bytes = build_render_payload(clean_sanitized_track, opts)
        payload = json.loads(payload_bytes)

        bounds = payload["track"]["bounds"]
        assert bounds["min_lat"] == 25.0330
        assert bounds["max_lat"] == 25.0340
        assert bounds["min_lon"] == 121.5650
        assert bounds["max_lon"] == 121.5660
        assert bounds["min_ele"] == 120.0
        assert bounds["max_ele"] == 130.0

    def test_per_point_cumulative_monotonic(self, clean_sanitized_track):
        opts = RenderOptions()
        payload_bytes = build_render_payload(clean_sanitized_track, opts)
        payload = json.loads(payload_bytes)

        points = payload["track"]["segments"][0]["points"]
        distances = [p["cumulative_m"] for p in points]
        assert distances == sorted(distances)
        assert distances[0] == 0.0
        assert distances[-1] > 0

    def test_segments_length_matches_haversine(self, clean_sanitized_track):
        opts = RenderOptions()
        payload_bytes = build_render_payload(clean_sanitized_track, opts)
        payload = json.loads(payload_bytes)

        seg = payload["track"]["segments"][0]
        assert seg["length_m"] > 0
        # 3 points, distance is roughly the same between each in the fixture
        # 25.0330, 121.5650 -> 25.0335, 121.5655 is ~70m
        assert 100 < seg["length_m"] < 200

    def test_timestamps_iso_utc_z(self, clean_sanitized_track):
        opts = RenderOptions()
        payload_bytes = build_render_payload(clean_sanitized_track, opts)
        payload = json.loads(payload_bytes)

        seg = payload["track"]["segments"][0]
        assert seg["start_time_iso"] == "2025-01-15T08:00:00Z"
        assert payload["track"]["segments"][0]["points"][0]["time"] == "2025-01-15T08:00:00Z"

    def test_null_for_missing_extensions(self, sanitized_with_extensions):
        # Create a hybrid track where some points have extensions and some don't
        # But we can just test a minimal one first to see if they are null
        from gpxflythrough.models import TrackPoint, TrackSegment, TrackData
        from datetime import timezone

        p1 = TrackPoint(
            latitude=25.0, longitude=121.0, elevation=100.0,
            time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            speed=None, heart_rate=None, cadence=None, temperature=None
        )
        p2 = TrackPoint(
            latitude=25.1, longitude=121.1, elevation=110.0,
            time=datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc),
            speed=2.5, heart_rate=140, cadence=80, temperature=25.0
        )

        track = TrackData(
            name="Mixed", activity_type="Running", time=None,
            segments=(TrackSegment(points=(p1, p2)),),
        )
        sanitized = SanitizedTrack(track=track, stats=SanitizationStats(0,0,0,0,0,0))

        payload = json.loads(build_render_payload(sanitized, RenderOptions()))
        pts = payload["track"]["segments"][0]["points"]

        assert pts[0]["speed"] is None
        assert pts[0]["hr"] is None
        assert pts[1]["speed"] == 2.5
        assert pts[1]["hr"] == 140

    def test_schema_version_is_1_0_0(self, clean_sanitized_track):
        payload = json.loads(build_render_payload(clean_sanitized_track, RenderOptions()))
        assert payload["schema_version"] == "1.0.0"

    def test_render_section_matches_options(self, clean_sanitized_track):
        opts = RenderOptions(fps=60, resolution="4k", height_m=80.0, no_terrain=True)
        payload = json.loads(build_render_payload(clean_sanitized_track, opts))

        render = payload["render"]
        assert render["fps"] == 60
        assert render["resolution"]["label"] == "4k"
        assert render["resolution"]["width"] == 3840
        assert render["camera"]["height_above_terrain_m"] == 80.0
        assert render["no_terrain"] is True

    def test_waypoints_included(self, track_with_waypoints_sanitized):
        payload = json.loads(build_render_payload(track_with_waypoints_sanitized, RenderOptions()))
        waypoints = payload["track"]["waypoints"]
        assert len(waypoints) == 2
        assert waypoints[0]["name"] == "Summit"
        assert waypoints[1]["name"] == "Trailhead"

    def test_empty_track_produces_valid_payload(self, empty_sanitized_track):
        payload = json.loads(build_render_payload(empty_sanitized_track, RenderOptions()))
        assert payload["track"]["segments"] == []
        assert payload["track"]["bounds"]["min_lat"] == 0.0

    def test_resolution_map_in_payload(self, clean_sanitized_track):
        opts = RenderOptions(resolution="720p")
        payload = json.loads(build_render_payload(clean_sanitized_track, opts))
        res = payload["render"]["resolution"]
        assert res["label"] == "720p"
        assert res["width"] == 1280
        assert res["height"] == 720


class TestValidateOptions:
    def test_valid_defaults_pass(self):
        # defaults: no_terrain=False, ion_token=None -> should fail
        # Need a token for defaults to pass
        opts = RenderOptions(ion_token="valid-token")
        validate_render_options(opts)

    def test_raises_when_no_terrain_false_and_no_token(self):
        opts = RenderOptions(no_terrain=False, ion_token=None)
        with pytest.raises(RenderSchemaError, match="ion_token is required"):
            validate_render_options(opts)

    def test_raises_when_invalid_resolution(self):
        # We have to cast to any/bypass type check for test
        opts = RenderOptions(resolution="8k") # type: ignore
        with pytest.raises(RenderSchemaError, match="Invalid resolution"):
            validate_render_options(opts)

    def test_raises_when_invalid_fps(self):
        opts = RenderOptions(fps=45)
        with pytest.raises(RenderSchemaError, match="Invalid FPS"):
            validate_render_options(opts)

    def test_raises_when_negative_height(self):
        opts = RenderOptions(height_m=-10.0)
        with pytest.raises(RenderSchemaError, match="height_m must be positive"):
            validate_render_options(opts)

    def test_raises_when_negative_duration(self):
        opts = RenderOptions(duration_s=0)
        with pytest.raises(RenderSchemaError, match="duration_s must be positive"):
            validate_render_options(opts)

    def test_raises_when_mode_not_3d(self):
        opts = RenderOptions(mode="2d") # type: ignore
        with pytest.raises(RenderSchemaError, match="Only mode '3d' is supported"):
            validate_render_options(opts)

    def test_raises_when_camera_not_follow(self):
        opts = RenderOptions(camera_mode="birdseye") # type: ignore
        with pytest.raises(RenderSchemaError, match="Only camera_mode 'follow' is supported"):
            validate_render_options(opts)

    def test_no_terrain_true_without_token_passes(self):
        opts = RenderOptions(no_terrain=True, ion_token=None)
        validate_render_options(opts)
