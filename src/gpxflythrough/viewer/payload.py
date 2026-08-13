"""Build the track render payload for the interactive viewer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import orjson

from gpxflythrough.models import SanitizedTrack

# ── Types ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ViewOptions:
    """Options for the interactive viewer."""

    theme: Literal["dark", "light"] = "dark"
    no_terrain: bool = False
    height_m: float = 50.0
    ion_token: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────


_EARTH_RADIUS_M = 6_371_008.8


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance between two points in meters."""
    lat1_r, lon1_r, lat2_r, lon2_r = (
        math.radians(lat1),
        math.radians(lon1),
        math.radians(lat2),
        math.radians(lon2),
    )
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Public API ───────────────────────────────────────────────────────


def build_view_payload(track: SanitizedTrack, opts: ViewOptions) -> bytes:
    """Build the JSON payload for the TypeScript viewer engine."""
    data = track.track

    # 1. Compute Bounds
    all_pts = data.all_points
    if not all_pts:
        bounds: dict[str, float] = {
            "min_lat": 0.0,
            "max_lat": 0.0,
            "min_lon": 0.0,
            "max_lon": 0.0,
            "min_ele": 0.0,
            "max_ele": 0.0,
        }
    else:
        lats = [float(p.latitude) for p in all_pts]
        lons = [float(p.longitude) for p in all_pts]
        eles = [float(p.elevation) if p.elevation is not None else 0.0 for p in all_pts]
        bounds = {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_ele": min(eles),
            "max_ele": max(eles),
        }

    # 2. Compute Segments
    processed_segments: list[dict[str, object]] = []
    for idx, seg in enumerate(data.segments):
        pts = seg.points
        if not pts:
            continue

        start_time = pts[0].time
        start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if start_time else None

        duration = 0.0
        if start_time and pts[-1].time:
            duration = (pts[-1].time - start_time).total_seconds()

        segment_points: list[dict[str, object]] = []
        cumulative_m = 0.0
        total_len = 0.0

        for i, p in enumerate(pts):
            if i > 0:
                prev = pts[i - 1]
                dist = _haversine_meters(
                    float(prev.latitude),
                    float(prev.longitude),
                    float(p.latitude),
                    float(p.longitude),
                )
                cumulative_m += dist
                total_len += dist

            segment_points.append(
                {
                    "lat": float(p.latitude),
                    "lon": float(p.longitude),
                    "ele": (float(p.elevation) if p.elevation is not None else None),
                    "time": (p.time.strftime("%Y-%m-%dT%H:%M:%SZ") if p.time else None),
                    "cumulative_m": cumulative_m,
                    "speed": float(p.speed) if p.speed is not None else None,
                    "hr": (p.heart_rate if p.heart_rate is not None else None),
                    "cad": p.cadence if p.cadence is not None else None,
                    "temp": (
                        float(p.temperature) if p.temperature is not None else None
                    ),
                }
            )

        processed_segments.append(
            {
                "index": idx,
                "start_time_iso": start_iso,
                "duration_s": duration,
                "length_m": total_len,
                "points": segment_points,
            }
        )

    # 3. Waypoints
    processed_waypoints: list[dict[str, object]] = [
        {
            "lat": float(wp.latitude),
            "lon": float(wp.longitude),
            "ele": (float(wp.elevation) if wp.elevation is not None else None),
            "name": wp.name,
            "time": (wp.time.strftime("%Y-%m-%dT%H:%M:%SZ") if wp.time else None),
        }
        for wp in data.waypoints
    ]

    # 4. Assemble Payload
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "track": {
            "name": data.name,
            "activity_type": data.activity_type,
            "bounds": bounds,
            "segments": processed_segments,
            "waypoints": processed_waypoints,
        },
        "render": {
            "fps": 60,
            "resolution": {"label": "browser", "width": 0, "height": 0},
            "camera": {
                "mode": "follow",
                "height_above_terrain_m": opts.height_m,
                "lookahead_m": 100.0,
                "pitch_deg": -15.0,
            },
            "theme": opts.theme,
            "overlays": [],
            "no_terrain": opts.no_terrain,
        },
    }

    return orjson.dumps(
        payload,
        option=(
            orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_UTC_Z | orjson.OPT_NAIVE_UTC
        ),
    )
