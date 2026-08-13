"""Tests for the viewer payload builder."""

from __future__ import annotations

from datetime import UTC, datetime

import orjson

from gpxflythrough.models import (
    Latitude,
    Longitude,
    Meters,
    SanitizationStats,
    SanitizedTrack,
    TrackData,
    TrackPoint,
    TrackSegment,
)
from gpxflythrough.viewer.payload import ViewOptions, build_view_payload


def _make_track(
    name: str = "Test",
    points: list[TrackPoint] | None = None,
) -> SanitizedTrack:
    if points is None:
        points = [
            TrackPoint(
                latitude=Latitude(25.033),
                longitude=Longitude(121.565),
                elevation=Meters(120.0),
                time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
            ),
            TrackPoint(
                latitude=Latitude(25.034),
                longitude=Longitude(121.566),
                elevation=Meters(130.0),
                time=datetime(2025, 1, 15, 8, 2, 0, tzinfo=UTC),
            ),
        ]
    track = TrackData(
        name=name,
        activity_type="hiking",
        time=points[0].time if points else None,
        segments=(TrackSegment(points=tuple(points)),),
        waypoints=(),
    )
    return SanitizedTrack(
        track=track,
        stats=SanitizationStats(
            original_points=len(points),
            final_points=len(points),
            outliers_removed=0,
            points_interpolated=0,
            segments_merged=0,
            gaps_detected=0,
        ),
    )


class TestBuildViewPayload:
    def test_returns_valid_json(self) -> None:
        track = _make_track()
        result = build_view_payload(track, ViewOptions())
        parsed = orjson.loads(result)
        assert isinstance(parsed, dict)

    def test_schema_version(self) -> None:
        track = _make_track()
        result = orjson.loads(build_view_payload(track, ViewOptions()))
        assert result["schema_version"] == "1.0.0"

    def test_empty_track(self) -> None:
        empty_track = SanitizedTrack(
            track=TrackData(
                name="Empty",
                activity_type=None,
                time=None,
                segments=(),
                waypoints=(),
            ),
            stats=SanitizationStats(0, 0, 0, 0, 0, 0),
        )
        result = orjson.loads(build_view_payload(empty_track, ViewOptions()))
        assert result["track"]["segments"] == []
        assert result["track"]["bounds"]["min_lat"] == 0.0

    def test_no_terrain_propagates(self) -> None:
        track = _make_track()
        result = orjson.loads(build_view_payload(track, ViewOptions(no_terrain=True)))
        assert result["render"]["no_terrain"] is True

    def test_theme_propagates(self) -> None:
        track = _make_track()
        result = orjson.loads(build_view_payload(track, ViewOptions(theme="light")))
        assert result["render"]["theme"] == "light"

    def test_cumulative_m_and_length(self) -> None:
        track = _make_track()
        result = orjson.loads(build_view_payload(track, ViewOptions()))
        seg = result["track"]["segments"][0]
        assert seg["points"][0]["cumulative_m"] == 0.0
        assert seg["points"][-1]["cumulative_m"] > 0
        assert seg["length_m"] > 0

    def test_render_section_defaults(self) -> None:
        track = _make_track()
        result = orjson.loads(build_view_payload(track, ViewOptions()))
        render = result["render"]
        assert render["fps"] == 60
        assert render["resolution"]["label"] == "browser"
        assert render["camera"]["mode"] == "follow"
