"""Unit tests for gpxflythrough.parser — parse_gpx and parse_gpx_file."""

from __future__ import annotations

from pathlib import Path

import pytest

from gpxflythrough.models import TrackData
from gpxflythrough.parser import GPXParseError, parse_gpx, parse_gpx_file

# ── parse_gpx: minimal GPX ──────────────────────────────────────────


class TestParseGpxMinimal:
    """Tests for parsing a minimal 3-point GPX."""

    def test_returns_track_data_when_valid_gpx(self, minimal_gpx: str) -> None:
        """Given a valid minimal GPX, parse_gpx returns a TrackData instance."""
        result = parse_gpx(minimal_gpx)
        assert isinstance(result, TrackData)

    def test_correct_point_count_when_minimal_gpx(self, minimal_gpx: str) -> None:
        """Given a 3-point GPX, total_points equals 3."""
        result = parse_gpx(minimal_gpx)
        assert result.total_points == 3

    def test_correct_segment_count_when_minimal_gpx(self, minimal_gpx: str) -> None:
        """Given a 1-segment GPX, total_segments equals 1."""
        result = parse_gpx(minimal_gpx)
        assert result.total_segments == 1

    def test_name_extracted_when_present(self, minimal_gpx: str) -> None:
        """Given a track named 'Test Hike', the name is extracted."""
        result = parse_gpx(minimal_gpx)
        assert result.name == "Test Hike"

    def test_activity_type_extracted_when_present(self, minimal_gpx: str) -> None:
        """Given a track type 'Hiking', activity_type is 'Hiking'."""
        result = parse_gpx(minimal_gpx)
        assert result.activity_type == "Hiking"

    def test_elevation_parsed_when_present(self, minimal_gpx: str) -> None:
        """Given points with elevation, each point has non-None elevation."""
        result = parse_gpx(minimal_gpx)
        for point in result.all_points:
            assert point.elevation is not None

    def test_time_parsed_when_present(self, minimal_gpx: str) -> None:
        """Given points with timestamps, each point has non-None time."""
        result = parse_gpx(minimal_gpx)
        for point in result.all_points:
            assert point.time is not None


# ── parse_gpx: multi-segment ────────────────────────────────────────


class TestParseGpxMultiSegment:
    """Tests for parsing a GPX with 2 track segments."""

    def test_segment_count_equals_2_when_two_segments(
        self,
        multi_segment_gpx: str,
    ) -> None:
        """Given 2 segments, total_segments equals 2."""
        result = parse_gpx(multi_segment_gpx)
        assert result.total_segments == 2

    def test_points_not_bridged_when_two_segments(
        self,
        multi_segment_gpx: str,
    ) -> None:
        """Given 2 segments, each segment has its own 2 points (not merged)."""
        result = parse_gpx(multi_segment_gpx)
        assert len(result.segments[0].points) == 2
        assert len(result.segments[1].points) == 2


# ── parse_gpx: Garmin extensions ────────────────────────────────────


class TestParseGpxGarminExtensions:
    """Tests for parsing Garmin TrackPointExtension data."""

    def test_heart_rate_extracted_when_present(
        self,
        garmin_extensions_gpx: str,
    ) -> None:
        """Given Garmin HR extension, heart_rate is populated."""
        result = parse_gpx(garmin_extensions_gpx)
        hr_values = [
            p.heart_rate for p in result.all_points if p.heart_rate is not None
        ]
        assert len(hr_values) == 2
        assert hr_values[0] == 145

    def test_cadence_extracted_when_present(
        self,
        garmin_extensions_gpx: str,
    ) -> None:
        """Given Garmin cad extension, cadence is populated."""
        result = parse_gpx(garmin_extensions_gpx)
        cad_values = [p.cadence for p in result.all_points if p.cadence is not None]
        assert len(cad_values) == 2
        assert cad_values[0] == 85

    def test_speed_extracted_when_present(
        self,
        garmin_extensions_gpx: str,
    ) -> None:
        """Given Garmin speed extension, speed is populated."""
        result = parse_gpx(garmin_extensions_gpx)
        speed_values = [p.speed for p in result.all_points if p.speed is not None]
        assert len(speed_values) == 2
        assert speed_values[0] is not None
        assert abs(float(speed_values[0]) - 2.8) < 0.1

    def test_temperature_extracted_when_present(
        self,
        garmin_extensions_gpx: str,
    ) -> None:
        """Given Garmin atemp extension, temperature is populated."""
        result = parse_gpx(garmin_extensions_gpx)
        temp_values = [
            p.temperature for p in result.all_points if p.temperature is not None
        ]
        assert len(temp_values) == 2
        assert temp_values[0] is not None
        assert abs(float(temp_values[0]) - 28.5) < 0.1


# ── parse_gpx: missing elevation ────────────────────────────────────


class TestParseGpxMissingElevation:
    """Tests for parsing GPX where some points lack elevation."""

    def test_elevation_none_when_missing(self, missing_elevation_gpx: str) -> None:
        """Given a point with no <ele> tag, its elevation is None."""
        result = parse_gpx(missing_elevation_gpx)
        # Middle point has no elevation in the fixture
        assert result.segments[0].points[1].elevation is None

    def test_elevation_present_when_provided(self, missing_elevation_gpx: str) -> None:
        """Given points with <ele> tags, their elevation is not None."""
        result = parse_gpx(missing_elevation_gpx)
        assert result.segments[0].points[0].elevation is not None
        assert result.segments[0].points[2].elevation is not None


# ── parse_gpx: waypoints only ───────────────────────────────────────


class TestParseGpxWaypoints:
    """Tests for parsing a GPX with only waypoints."""

    def test_no_segments_when_waypoints_only(self, waypoint_gpx: str) -> None:
        """Given a GPX with only waypoints, total_segments equals 0."""
        result = parse_gpx(waypoint_gpx)
        assert result.total_segments == 0

    def test_waypoints_extracted_when_present(self, waypoint_gpx: str) -> None:
        """Given 2 waypoints, the waypoints tuple has length 2."""
        result = parse_gpx(waypoint_gpx)
        assert len(result.waypoints) == 2

    def test_waypoint_name_extracted_when_present(self, waypoint_gpx: str) -> None:
        """Given a waypoint named 'Summit', the name is extracted."""
        result = parse_gpx(waypoint_gpx)
        assert result.waypoints[0].name == "Summit"

    def test_waypoint_elevation_extracted_when_present(
        self,
        waypoint_gpx: str,
    ) -> None:
        """Given a waypoint with elevation, it is extracted."""
        result = parse_gpx(waypoint_gpx)
        assert result.waypoints[0].elevation is not None


# ── parse_gpx: empty GPX ────────────────────────────────────────────


class TestParseGpxEmpty:
    """Tests for parsing an empty GPX (no tracks, no waypoints)."""

    def test_zero_segments_when_empty(self, empty_gpx: str) -> None:
        """Given an empty GPX, total_segments equals 0."""
        result = parse_gpx(empty_gpx)
        assert result.total_segments == 0

    def test_zero_waypoints_when_empty(self, empty_gpx: str) -> None:
        """Given an empty GPX, waypoints tuple is empty."""
        result = parse_gpx(empty_gpx)
        assert len(result.waypoints) == 0

    def test_empty_name_when_no_tracks(self, empty_gpx: str) -> None:
        """Given an empty GPX with no tracks, name defaults to empty string."""
        result = parse_gpx(empty_gpx)
        assert result.name == ""


# ── parse_gpx: invalid input ────────────────────────────────────────


class TestParseGpxInvalid:
    """Tests for error handling on invalid GPX input."""

    def test_raises_gpx_parse_error_when_invalid_xml(self) -> None:
        """Given malformed XML, parse_gpx raises GPXParseError."""
        with pytest.raises(GPXParseError):
            _ = parse_gpx("<not-valid-xml>")

    def test_returns_empty_track_when_non_gpx_xml(self) -> None:
        """Given valid XML that is not GPX, parse_gpx returns empty TrackData."""
        result = parse_gpx("<root>not gpx</root>")
        assert result.total_points == 0
        assert result.total_segments == 0

    def test_path_is_none_when_string_input(self) -> None:
        """Given a string input that fails, the error path is None."""
        with pytest.raises(GPXParseError) as exc_info:
            _ = parse_gpx("<not-valid-xml>")
        assert exc_info.value.path is None


# ── parse_gpx_file ──────────────────────────────────────────────────


class TestParseGpxFile:
    """Tests for parse_gpx_file."""

    def test_raises_gpx_parse_error_when_file_not_found(self) -> None:
        """Given a non-existent file path, parse_gpx_file raises GPXParseError."""
        fake_path = Path.home() / "does_not_exist_12345.gpx"
        with pytest.raises(GPXParseError) as exc_info:
            _ = parse_gpx_file(fake_path)
        assert exc_info.value.path is not None
        assert "does_not_exist_12345" in exc_info.value.path

    def test_parses_real_file_when_valid(self, nangang_path: Path) -> None:
        """Given the real Nangang GPX file, it parses with >0 points."""
        result = parse_gpx_file(nangang_path)
        assert result.total_points > 0

    def test_real_file_has_segments(self, nangang_path: Path) -> None:
        """Given the real Nangang GPX file, it has at least one segment."""
        result = parse_gpx_file(nangang_path)
        assert result.total_segments >= 1

    def test_real_file_name_not_empty(self, nangang_path: Path) -> None:
        """Given the real Nangang GPX file, name is not empty."""
        result = parse_gpx_file(nangang_path)
        assert result.name != ""

    def test_path_in_error_when_invalid_content(self, tmp_path: Path) -> None:
        """Given a file with invalid content, error contains the file path."""
        bad_file = tmp_path / "bad.gpx"
        _ = bad_file.write_text("<not-gpx>", encoding="utf-8")
        with pytest.raises(GPXParseError) as exc_info:
            _ = parse_gpx_file(bad_file)
        assert exc_info.value.path is not None
        assert "bad.gpx" in exc_info.value.path
