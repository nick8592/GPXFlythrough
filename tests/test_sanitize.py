"""Unit tests for gpxflythrough.sanitize — sanitize function."""

from __future__ import annotations

from datetime import UTC, datetime

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
from gpxflythrough.sanitize import sanitize

# ── Helpers ─────────────────────────────────────────────────────────


def _make_point(
    lat: float = 25.0330,
    lon: float = 121.5650,
    ele: float | None = 120.0,
    time: datetime | None = None,
) -> TrackPoint:
    """Create a TrackPoint with sensible defaults."""
    return TrackPoint(
        latitude=Latitude(lat),
        longitude=Longitude(lon),
        elevation=Meters(ele) if ele is not None else None,
        time=time,
    )


def _ts(minute: int, second: int = 0) -> datetime:
    """Create a UTC timestamp at 08:MM:SS on 2025-01-15."""
    return datetime(2025, 1, 15, 8, minute, second, tzinfo=UTC)


# ── Clean data ──────────────────────────────────────────────────────


class TestSanitizeClean:
    """Tests for sanitizing already-clean data."""

    def test_zero_outliers_when_clean_data(self, minimal_track: TrackData) -> None:
        """Given clean data with normal speeds, no outliers are removed."""
        result = sanitize(minimal_track)
        assert result.stats.outliers_removed == 0

    def test_zero_interpolated_when_all_elevation_present(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given all points have elevation, nothing is interpolated."""
        result = sanitize(minimal_track)
        assert result.stats.points_interpolated == 0

    def test_gaps_detected_when_60s_spaced_timestamps(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given consecutive 60s-spaced timestamps, gaps_detected equals 2."""
        result = sanitize(minimal_track)
        assert result.stats.gaps_detected == 2

    def test_zero_gaps_when_points_spaced_within_threshold(self) -> None:
        """Given points 5s apart, gaps_detected is 0."""
        track = TrackData(
            name="Fast Track",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(time=_ts(0, 0)),
                        _make_point(lat=25.0331, time=_ts(0, 5)),
                        _make_point(lat=25.0332, time=_ts(0, 10)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.gaps_detected == 0

    def test_final_points_equals_original_when_clean(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given clean data, final_points equals original_points."""
        result = sanitize(minimal_track)
        assert result.stats.final_points == result.stats.original_points

    def test_returns_sanitized_track_type(self, minimal_track: TrackData) -> None:
        """Given any track, sanitize returns a SanitizedTrack."""
        result = sanitize(minimal_track)
        assert isinstance(result, SanitizedTrack)

    def test_stats_type_is_sanitization_stats(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given any track, stats field is SanitizationStats."""
        result = sanitize(minimal_track)
        assert isinstance(result.stats, SanitizationStats)


# ── Speed spike removal ────────────────────────────────────────────


class TestSanitizeSpeedSpike:
    """Tests for outlier removal with impossible speed."""

    def test_outlier_removed_when_speed_exceeds_threshold(self) -> None:
        """Given a spike point >150 km/h from both neighbors, it is removed."""
        # Points 1s apart, spike point jumps ~500m (way >41.67 m/s)
        track = TrackData(
            name="Spike",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(lat=25.0330, lon=121.5650, time=_ts(0, 0)),
                        _make_point(lat=25.0331, lon=121.5651, time=_ts(0, 1)),
                        _make_point(lat=25.0370, lon=121.5710, time=_ts(0, 2)),  # spike
                        _make_point(lat=25.0332, lon=121.5652, time=_ts(0, 3)),
                        _make_point(lat=25.0333, lon=121.5653, time=_ts(0, 4)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.outliers_removed >= 1

    def test_final_points_decreases_when_outlier_removed(self) -> None:
        """Given a spike outlier, final_points < original_points."""
        track = TrackData(
            name="Spike",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(lat=25.0330, lon=121.5650, time=_ts(0, 0)),
                        _make_point(lat=25.0331, lon=121.5651, time=_ts(0, 1)),
                        _make_point(lat=25.0370, lon=121.5710, time=_ts(0, 2)),  # spike
                        _make_point(lat=25.0332, lon=121.5652, time=_ts(0, 3)),
                        _make_point(lat=25.0333, lon=121.5653, time=_ts(0, 4)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.final_points < result.stats.original_points


# ── Timestamp gap detection ─────────────────────────────────────────


class TestSanitizeGapDetection:
    """Tests for timestamp gap counting."""

    def test_gap_counted_when_interval_exceeds_threshold(self) -> None:
        """Given a 60s gap between two points, gaps_detected is 1."""
        track = TrackData(
            name="Gap",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(time=_ts(0, 0)),
                        _make_point(lat=25.0331, time=_ts(0, 5)),
                        _make_point(lat=25.0332, time=_ts(0, 10)),
                        # 60s gap here
                        _make_point(lat=25.0360, time=_ts(1, 10)),
                        _make_point(lat=25.0361, time=_ts(1, 15)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.gaps_detected == 1

    def test_no_gap_when_interval_within_threshold(self) -> None:
        """Given points 10s apart, gaps_detected is 0 (boundary: not >10)."""
        track = TrackData(
            name="No Gap",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(time=_ts(0, 0)),
                        _make_point(lat=25.0331, time=_ts(0, 10)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        # 10s is NOT > 10s threshold (strictly greater)
        assert result.stats.gaps_detected == 0

    def test_multiple_gaps_counted(self) -> None:
        """Given two gaps >10s, gaps_detected is 2."""
        track = TrackData(
            name="Multi Gap",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(time=_ts(0, 0)),
                        _make_point(lat=25.0331, time=_ts(0, 5)),
                        # first gap: 30s
                        _make_point(lat=25.0340, time=_ts(0, 35)),
                        _make_point(lat=25.0341, time=_ts(0, 40)),
                        # second gap: 20s
                        _make_point(lat=25.0350, time=_ts(1, 0)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.gaps_detected == 2


# ── Elevation interpolation ─────────────────────────────────────────


class TestSanitizeElevationInterpolation:
    """Tests for elevation interpolation from neighbors."""

    def test_none_elevation_filled_from_neighbors(self) -> None:
        """Given a point with None elevation between two known, it is interpolated."""
        track = TrackData(
            name="Interp",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(ele=120.0, time=_ts(0, 0)),
                        _make_point(ele=None, time=_ts(0, 5)),
                        _make_point(ele=130.0, time=_ts(0, 10)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        # The middle point should have been interpolated
        assert result.stats.points_interpolated == 1
        # Find the interpolated point
        interp_point = result.track.segments[0].points[1]
        assert interp_point.elevation is not None
        # Should be between 120 and 130
        assert 120.0 <= float(interp_point.elevation) <= 130.0

    def test_all_missing_elevation_stays_none(self) -> None:
        """Given all points with None elevation, none can be interpolated."""
        track = TrackData(
            name="All None",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=(
                        _make_point(ele=None, time=_ts(0, 0)),
                        _make_point(lat=25.0331, ele=None, time=_ts(0, 5)),
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.stats.points_interpolated == 0
        for point in result.track.all_points:
            assert point.elevation is None


# ── Smoothing ──────────────────────────────────────────────────────


class TestSanitizeSmoothing:
    """Tests for Savitzky-Golay smoothing step."""

    def test_output_point_count_equals_input_when_no_outliers(self) -> None:
        """Given clean data, smoothing preserves point count."""
        track = TrackData(
            name="Smooth",
            activity_type="Hiking",
            time=None,
            segments=(
                TrackSegment(
                    points=tuple(
                        _make_point(
                            lat=25.0330 + i * 0.0001,
                            lon=121.5650 + i * 0.0001,
                            time=_ts(0, i),
                        )
                        for i in range(20)
                    )
                ),
            ),
        )
        result = sanitize(track)
        assert result.track.total_points == 20

    def test_segment_count_preserved(self, minimal_track: TrackData) -> None:
        """Given 1 segment, the sanitized track also has 1 segment."""
        result = sanitize(minimal_track)
        assert result.track.total_segments == 1


# ── Empty segment ──────────────────────────────────────────────────


class TestSanitizeEmptySegment:
    """Tests for handling empty segments."""

    def test_no_error_when_empty_segment(self) -> None:
        """Given a segment with zero points, sanitize completes without error."""
        track = TrackData(
            name="Empty Seg",
            activity_type=None,
            time=None,
            segments=(TrackSegment(points=()),),
        )
        result = sanitize(track)
        assert result.stats.original_points == 0
        assert result.stats.final_points == 0

    def test_zero_gaps_when_empty_segment(self) -> None:
        """Given an empty segment, gaps_detected is 0."""
        track = TrackData(
            name="Empty Seg",
            activity_type=None,
            time=None,
            segments=(TrackSegment(points=()),),
        )
        result = sanitize(track)
        assert result.stats.gaps_detected == 0
