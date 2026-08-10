"""Export module — serialize track data to JSON and GeoJSON.

Consumes TrackData or SanitizedTrack from the models layer and produces
byte payloads suitable for file I/O or HTTP response bodies. All
serialization uses orjson for performance; datetime values are emitted
as ISO 8601 strings with UTC trailing-Z notation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import orjson

from gpxflythrough.models import (
    SanitizationStats,
    SanitizedTrack,
    TrackData,
    TrackPoint,
    TrackSegment,
    Waypoint,
)

if TYPE_CHECKING:
    from pathlib import Path

# orjson flags: serialize dataclasses, format UTC datetimes with "Z"
_ORJSON_OPTS = orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_UTC_Z | orjson.OPT_NAIVE_UTC

TrackInput = TrackData | SanitizedTrack
"""Union type for functions that accept raw or sanitized track data."""


# ── Internal helpers ──────────────────────────────────────────────


def _unwrap(track: TrackInput) -> tuple[TrackData, SanitizationStats | None]:
    """Return the TrackData and optional stats from a TrackInput."""
    if isinstance(track, SanitizedTrack):
        return track.track, track.stats
    return track, None


def _point_to_dict(pt: TrackPoint) -> dict[str, object]:
    """Convert a TrackPoint to a JSON-friendly dict."""
    return {
        "lat": pt.latitude,
        "lon": pt.longitude,
        "ele": pt.elevation,
        "time": pt.time,
        "speed": pt.speed,
        "hr": pt.heart_rate,
        "cad": pt.cadence,
        "temp": pt.temperature,
    }


def _segment_to_dict(seg: TrackSegment) -> dict[str, object]:
    """Convert a TrackSegment to a JSON-friendly dict."""
    return {"points": [_point_to_dict(p) for p in seg.points]}


def _waypoint_to_dict(wp: Waypoint) -> dict[str, object]:
    """Convert a Waypoint to a JSON-friendly dict."""
    return {
        "lat": wp.latitude,
        "lon": wp.longitude,
        "ele": wp.elevation,
        "name": wp.name,
        "time": wp.time,
    }


def _stats_to_dict(stats: SanitizationStats) -> dict[str, int]:
    """Convert SanitizationStats to a JSON-friendly dict."""
    return {
        "original_points": stats.original_points,
        "final_points": stats.final_points,
        "outliers_removed": stats.outliers_removed,
        "points_interpolated": stats.points_interpolated,
        "segments_merged": stats.segments_merged,
        "gaps_detected": stats.gaps_detected,
    }


def _geojson_coords(pt: TrackPoint) -> list[float]:
    """Build a GeoJSON coordinate array [lon, lat] or [lon, lat, ele]."""
    coords: list[float] = [float(pt.longitude), float(pt.latitude)]
    if pt.elevation is not None:
        coords.append(float(pt.elevation))
    return coords


# ── Public API ────────────────────────────────────────────────────


def to_json(track: TrackInput) -> bytes:
    """Serialize track data to a JSON byte payload.

    Args:
        track: Raw TrackData or SanitizedTrack to export.

    Returns:
        UTF-8 encoded JSON bytes with the full track structure.
    """
    data, stats = _unwrap(track)
    result: dict[str, object] = {
        "name": data.name,
        "activity_type": data.activity_type,
        "time": data.time,
        "segments": [_segment_to_dict(s) for s in data.segments],
        "waypoints": [_waypoint_to_dict(w) for w in data.waypoints],
    }
    if stats is not None:
        result["stats"] = _stats_to_dict(stats)
    return orjson.dumps(result, default=_orjson_default, option=_ORJSON_OPTS)


def to_geojson(track: TrackInput) -> bytes:
    """Serialize track data as a GeoJSON FeatureCollection (RFC 7946).

    Each track segment becomes a LineString Feature with properties
    ``name`` and ``segment_index``. Each waypoint becomes a Point
    Feature with property ``name``.  Coordinates follow GeoJSON
    axis order: [longitude, latitude, elevation?].

    Args:
        track: Raw TrackData or SanitizedTrack to export.

    Returns:
        UTF-8 encoded GeoJSON FeatureCollection bytes.
    """
    data, _stats = _unwrap(track)
    features: list[dict[str, object]] = []

    for idx, seg in enumerate(data.segments):
        coordinates: list[list[float]] = [_geojson_coords(p) for p in seg.points]
        properties: dict[str, object] = {
            "name": data.name,
            "segment_index": idx,
        }
        if data.time is not None:
            properties["time"] = data.time.isoformat()
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
                "properties": properties,
            }
        )

    for wp in data.waypoints:
        wp_properties: dict[str, object] = {"name": wp.name}
        if wp.time is not None:
            wp_properties["time"] = wp.time.isoformat()
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": _geojson_coords(
                        TrackPoint(
                            latitude=wp.latitude,
                            longitude=wp.longitude,
                            elevation=wp.elevation,
                            time=None,
                        )
                    ),
                },
                "properties": wp_properties,
            }
        )

    feature_collection: dict[str, object] = {
        "type": "FeatureCollection",
        "features": features,
    }
    return orjson.dumps(feature_collection, option=_ORJSON_OPTS)


def write_json(track: TrackInput, path: Path) -> None:
    """Write track data as JSON to the given file path.

    Args:
        track: Raw TrackData or SanitizedTrack to export.
        path: Destination file path.
    """
    _ = path.write_bytes(to_json(track))


def write_geojson(track: TrackInput, path: Path) -> None:
    """Write track data as GeoJSON to the given file path.

    Args:
        track: Raw TrackData or SanitizedTrack to export.
        path: Destination file path.
    """
    _ = path.write_bytes(to_geojson(track))


# ── orjson default serializer ─────────────────────────────────────


def _orjson_default(obj: object) -> object:
    """Fallback serializer for types orjson cannot handle natively.

    Handles NewType-wrapped floats/ints by unwrapping to their
    primitive value.
    """
    if isinstance(obj, float):
        return obj
    if isinstance(obj, int):
        return obj
    msg = f"Type {type(obj).__name__} is not serializable"
    raise TypeError(msg)
