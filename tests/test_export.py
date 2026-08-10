"""Unit tests for gpxflythrough.export.

Covers to_json, to_geojson, write_json, write_geojson.
"""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest

from gpxflythrough.export import to_geojson, to_json, write_geojson, write_json
from gpxflythrough.models import (
    SanitizedTrack,
    TrackData,
)


def _loads(data: bytes) -> dict[str, object]:
    """Parse JSON bytes into a typed dict for assertion access."""
    result: dict[str, object] = orjson.loads(data)
    return result


def _as_list(val: object) -> list[object]:
    """Assert a value is a list and return it."""
    assert isinstance(val, list)
    return val


def _as_dict(val: object) -> dict[str, object]:
    """Assert a value is a dict and return it."""
    assert isinstance(val, dict)
    return val


# ── to_json ─────────────────────────────────────────────────────────


class TestToJson:
    """Tests for JSON serialization."""

    def test_produces_valid_json_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, to_json returns valid JSON bytes."""
        result = to_json(minimal_track)
        assert isinstance(result, bytes)
        parsed = _loads(result)
        assert isinstance(parsed, dict)

    def test_correct_structure_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, JSON has name, segments, and waypoints keys."""
        parsed = _loads(to_json(minimal_track))
        assert "name" in parsed
        assert "segments" in parsed
        assert "waypoints" in parsed

    def test_name_matches_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData named 'Test Hike', JSON name equals 'Test Hike'."""
        parsed = _loads(to_json(minimal_track))
        assert parsed["name"] == "Test Hike"

    def test_activity_type_included_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData with activity_type, JSON includes it."""
        parsed = _loads(to_json(minimal_track))
        assert parsed["activity_type"] == "Hiking"

    def test_segments_count_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData with 1 segment, JSON has 1 segment."""
        parsed = _loads(to_json(minimal_track))
        segments = _as_list(parsed["segments"])
        assert len(segments) == 1

    def test_points_in_segment_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData with 3 points, JSON segment has 3 points."""
        parsed = _loads(to_json(minimal_track))
        segments = _as_list(parsed["segments"])
        first_seg = _as_dict(segments[0])
        points = _as_list(first_seg["points"])
        assert len(points) == 3

    def test_includes_stats_when_sanitized_track(
        self,
        clean_sanitized_track: SanitizedTrack,
    ) -> None:
        """Given a SanitizedTrack, JSON includes a stats key."""
        parsed = _loads(to_json(clean_sanitized_track))
        assert "stats" in parsed

    def test_stats_values_when_sanitized_track(
        self,
        clean_sanitized_track: SanitizedTrack,
    ) -> None:
        """Given a SanitizedTrack with clean data, stats show zero changes."""
        parsed = _loads(to_json(clean_sanitized_track))
        stats = _as_dict(parsed["stats"])
        assert stats["outliers_removed"] == 0
        assert stats["points_interpolated"] == 0
        assert stats["gaps_detected"] == 0

    def test_no_stats_key_when_plain_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a plain TrackData (not SanitizedTrack), JSON has no stats key."""
        parsed = _loads(to_json(minimal_track))
        assert "stats" not in parsed

    def test_extensions_included_when_present(
        self,
        track_with_extensions: TrackData,
    ) -> None:
        """Given a track with extensions, JSON points include hr/cad/speed/temp."""
        parsed = _loads(to_json(track_with_extensions))
        segments = _as_list(parsed["segments"])
        first_seg = _as_dict(segments[0])
        points = _as_list(first_seg["points"])
        first_point = _as_dict(points[0])
        assert first_point["hr"] is not None
        assert first_point["cad"] is not None
        assert first_point["speed"] is not None
        assert first_point["temp"] is not None


# ── to_geojson ──────────────────────────────────────────────────────


class TestToGeojson:
    """Tests for GeoJSON serialization."""

    def test_produces_valid_geojson_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, to_geojson returns a valid GeoJSON FeatureCollection."""
        parsed = _loads(to_geojson(minimal_track))
        assert parsed["type"] == "FeatureCollection"

    def test_features_present_when_track_data(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, GeoJSON has a features array."""
        parsed = _loads(to_geojson(minimal_track))
        features = _as_list(parsed["features"])
        assert len(features) >= 1

    def test_linestring_feature_when_track_segment(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData with a segment, GeoJSON feature is a LineString."""
        parsed = _loads(to_geojson(minimal_track))
        features = _as_list(parsed["features"])
        feature = _as_dict(features[0])
        assert feature["type"] == "Feature"
        geometry = _as_dict(feature["geometry"])
        assert geometry["type"] == "LineString"

    def test_point_feature_when_waypoints(
        self,
        track_with_waypoints: TrackData,
    ) -> None:
        """Given a TrackData with waypoints, GeoJSON has Point features."""
        parsed = _loads(to_geojson(track_with_waypoints))
        features = _as_list(parsed["features"])
        point_features = [
            f
            for f in features
            if isinstance(f, dict)
            and _as_dict(f.get("geometry", {})).get("type") == "Point"
        ]
        assert len(point_features) == 2

    def test_coordinates_lon_lat_order_when_track(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, GeoJSON coordinates follow [lon, lat] order."""
        parsed = _loads(to_geojson(minimal_track))
        features = _as_list(parsed["features"])
        feature = _as_dict(features[0])
        geometry = _as_dict(feature["geometry"])
        coords = _as_list(geometry["coordinates"])
        first_coord = _as_list(coords[0])
        # [lon, lat] — lon=121.5650, lat=25.0330
        assert first_coord[0] == pytest.approx(121.5650, abs=0.001)
        assert first_coord[1] == pytest.approx(25.0330, abs=0.001)

    def test_coordinates_lon_lat_ele_order_when_elevated(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData with elevation, GeoJSON coordinates are [lon, lat, ele]."""
        parsed = _loads(to_geojson(minimal_track))
        features = _as_list(parsed["features"])
        feature = _as_dict(features[0])
        geometry = _as_dict(feature["geometry"])
        coords = _as_list(geometry["coordinates"])
        first_coord = _as_list(coords[0])
        assert len(first_coord) == 3  # [lon, lat, ele]
        assert first_coord[2] == pytest.approx(120.0, abs=0.1)

    def test_two_position_coordinates_when_none_elevation(
        self,
        track_none_elevation: TrackData,
    ) -> None:
        """Given points with None elevation, GeoJSON coordinates have 2 positions."""
        parsed = _loads(to_geojson(track_none_elevation))
        features = _as_list(parsed["features"])
        feature = _as_dict(features[0])
        geometry = _as_dict(feature["geometry"])
        coords = _as_list(geometry["coordinates"])
        for coord_obj in coords:
            coord = _as_list(coord_obj)
            assert len(coord) == 2  # [lon, lat] only, no elevation

    def test_segment_index_in_properties_when_track(
        self,
        minimal_track: TrackData,
    ) -> None:
        """Given a TrackData, segment feature properties include segment_index."""
        parsed = _loads(to_geojson(minimal_track))
        features = _as_list(parsed["features"])
        feature = _as_dict(features[0])
        props = _as_dict(feature["properties"])
        assert props["segment_index"] == 0

    def test_waypoint_name_in_properties(
        self,
        track_with_waypoints: TrackData,
    ) -> None:
        """Given a waypoint with name, Point feature properties include name."""
        parsed = _loads(to_geojson(track_with_waypoints))
        features = _as_list(parsed["features"])
        point_features = [
            f
            for f in features
            if isinstance(f, dict)
            and _as_dict(f.get("geometry", {})).get("type") == "Point"
        ]
        first_point = _as_dict(point_features[0])
        props = _as_dict(first_point["properties"])
        assert props["name"] == "Summit"


# ── write_json / write_geojson ──────────────────────────────────────


class TestWriteJson:
    """Tests for file-based JSON export."""

    def test_write_json_creates_file_when_valid(
        self,
        minimal_track: TrackData,
        tmp_path: Path,
    ) -> None:
        """Given a TrackData, write_json creates a file at the given path."""
        output = tmp_path / "output.json"
        write_json(minimal_track, output)
        assert output.exists()

    def test_write_json_content_matches_to_json(
        self,
        minimal_track: TrackData,
        tmp_path: Path,
    ) -> None:
        """Given a TrackData, write_json file content matches to_json output."""
        output = tmp_path / "output.json"
        write_json(minimal_track, output)
        file_content = output.read_bytes()
        assert file_content == to_json(minimal_track)


class TestWriteGeojson:
    """Tests for file-based GeoJSON export."""

    def test_write_geojson_creates_file_when_valid(
        self,
        minimal_track: TrackData,
        tmp_path: Path,
    ) -> None:
        """Given a TrackData, write_geojson creates a file at the given path."""
        output = tmp_path / "output.geojson"
        write_geojson(minimal_track, output)
        assert output.exists()

    def test_write_geojson_content_matches_to_geojson(
        self,
        minimal_track: TrackData,
        tmp_path: Path,
    ) -> None:
        """Given a TrackData, write_geojson file content matches to_geojson."""
        output = tmp_path / "output.geojson"
        write_geojson(minimal_track, output)
        file_content = output.read_bytes()
        assert file_content == to_geojson(minimal_track)
