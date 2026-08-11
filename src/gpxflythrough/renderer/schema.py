"""Core schema and payload builder for the renderer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import orjson

from gpxflythrough.models import (
    SanitizedTrack,
)
from gpxflythrough.renderer.exceptions import RenderSchemaError

# ── Types ────────────────────────────────────────────────────────────

Resolution = Literal["720p", "1080p", "4k"]

_RESOLUTION_MAP: dict[Resolution, tuple[int, int]] = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}


@dataclass(frozen=True, slots=True)
class RenderOptions:
    """Rendering configuration options."""

    mode: str = "3d"
    resolution: Resolution = "1080p"
    fps: int = 30
    camera_mode: str = "follow"
    height_m: float = 50.0
    duration_s: float = 30.0
    no_terrain: bool = False
    cache_dir: str = ""
    ffmpeg_path: str | None = None
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

def validate_render_options(opts: RenderOptions) -> None:
    """Validate render options against pipeline constraints."""
    if opts.resolution not in _RESOLUTION_MAP:
        msg = f"Invalid resolution: {opts.resolution}"
        raise RenderSchemaError(msg)

    if opts.fps not in {24, 30, 60}:
        msg = f"Invalid FPS: {opts.fps}. Supported: 24, 30, 60"
        raise RenderSchemaError(msg)

    if opts.height_m <= 0:
        msg = f"height_m must be positive: {opts.height_m}"
        raise RenderSchemaError(msg)

    if opts.duration_s <= 0:
        msg = f"duration_s must be positive: {opts.duration_s}"
        raise RenderSchemaError(msg)

    if opts.mode != "3d":
        msg = f"Only mode '3d' is supported in Phase 1: {opts.mode}"
        raise RenderSchemaError(msg)

    if opts.camera_mode != "follow":
        msg = f"Only camera_mode 'follow' is supported in Phase 1: {opts.camera_mode}"
        raise RenderSchemaError(msg)

    if not opts.no_terrain and opts.ion_token is None:
        msg = "ion_token is required when terrain rendering is enabled"
        raise RenderSchemaError(msg)


def build_render_payload(track: SanitizedTrack, opts: RenderOptions) -> bytes:
    """Build the JSON payload for the TypeScript render engine."""
    data = track.track

    # 1. Compute Bounds
    all_pts = data.all_points
    if not all_pts:
        bounds = {
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
    processed_segments = []
    for idx, seg in enumerate(data.segments):
        pts = seg.points
        if not pts:
            continue

        start_time = pts[0].time
        start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if start_time else None

        duration = 0.0
        if start_time and pts[-1].time:
            duration = (pts[-1].time - start_time).total_seconds()

        segment_points = []
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

            segment_points.append({
                "lat": float(p.latitude),
                "lon": float(p.longitude),
                "ele": float(p.elevation) if p.elevation is not None else None,
                "time": p.time.strftime("%Y-%m-%dT%H:%M:%SZ") if p.time else None,
                "cumulative_m": cumulative_m,
                "speed": float(p.speed) if p.speed is not None else None,
                "hr": p.heart_rate if p.heart_rate is not None else None,
                "cad": p.cadence if p.cadence is not None else None,
                "temp": float(p.temperature) if p.temperature is not None else None,
            })

        processed_segments.append({
            "index": idx,
            "start_time_iso": start_iso,
            "duration_s": duration,
            "length_m": total_len,
            "points": segment_points,
        })

    # 3. Waypoints
    processed_waypoints = [
        {
            "lat": float(wp.latitude),
            "lon": float(wp.longitude),
            "ele": float(wp.elevation) if wp.elevation is not None else None,
            "name": wp.name,
            "time": wp.time.strftime("%Y-%m-%dT%H:%M:%SZ") if wp.time else None,
        }
        for wp in data.waypoints
    ]

    # 4. Assemble Payload
    res_val = _RESOLUTION_MAP[opts.resolution]
    payload = {
        "schema_version": "1.0.0",
        "track": {
            "name": data.name,
            "activity_type": data.activity_type,
            "bounds": bounds,
            "segments": processed_segments,
            "waypoints": processed_waypoints,
        },
        "render": {
            "fps": opts.fps,
            "resolution": {
                "label": opts.resolution,
                "width": res_val[0],
                "height": res_val[1],
            },
            "camera": {
                "mode": opts.camera_mode,
                "height_above_terrain_m": opts.height_m,
                "lookahead_m": 100.0,
                "pitch_deg": -15.0,
            },
            "theme": "dark",
            "overlays": [],
            "no_terrain": opts.no_terrain,
        },
    }

    return orjson.dumps(
        payload,
        option=orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_UTC_Z | orjson.OPT_NAIVE_UTC,
    )
