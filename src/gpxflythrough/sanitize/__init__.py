"""Data sanitization pipeline for GPX track data.

Applies outlier removal, gap detection, elevation interpolation,
and Savitzky-Golay smoothing to each segment independently.
"""

import math
from dataclasses import replace

from scipy.signal import savgol_filter

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

_GAP_THRESHOLD_SECS = 10.0
_MIN_INTERP_NEIGHBORS = 2
_MIN_OUTLIER_POINTS = 2
_SG_WINDOW = 11
_SG_POLYORDER = 3
_EARTH_RADIUS_M = 6_371_000.0


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two WGS-84 points in meters."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _speed_mps(prev: TrackPoint, curr: TrackPoint) -> float | None:
    """Compute implied speed (m/s) between consecutive points.

    Returns None if timestamps are missing or non-positive.
    """
    if prev.time is None or curr.time is None:
        return None
    dt = (curr.time - prev.time).total_seconds()
    if dt <= 0:
        return None
    dist = _haversine_meters(
        float(prev.latitude),
        float(prev.longitude),
        float(curr.latitude),
        float(curr.longitude),
    )
    return dist / dt


def _remove_outliers(
    points: tuple[TrackPoint, ...],
    max_speed_mps: float,
) -> tuple[tuple[TrackPoint, ...], int]:
    """Remove points with impossible speed from both predecessor and successor."""
    if len(points) <= _MIN_OUTLIER_POINTS:
        return points, 0
    keep: list[TrackPoint] = [points[0]]
    removed = 0
    for i in range(1, len(points) - 1):
        speed_in = _speed_mps(points[i - 1], points[i])
        speed_out = _speed_mps(points[i], points[i + 1])
        if (
            speed_in is not None
            and speed_out is not None
            and speed_in > max_speed_mps
            and speed_out > max_speed_mps
        ):
            removed += 1
        else:
            keep.append(points[i])
    keep.append(points[-1])
    return tuple(keep), removed


def _count_gaps(points: tuple[TrackPoint, ...]) -> int:
    """Count timestamp gaps exceeding the threshold between consecutive points."""
    gaps = 0
    for i in range(len(points) - 1):
        t0, t1 = points[i].time, points[i + 1].time
        if (
            t0 is not None
            and t1 is not None
            and (t1 - t0).total_seconds() > _GAP_THRESHOLD_SECS
        ):
            gaps += 1
    return gaps


def _interpolate_elevation(
    points: tuple[TrackPoint, ...],
) -> tuple[tuple[TrackPoint, ...], int]:
    """Interpolate missing elevation from bracketing neighbors with elevation."""
    known = [(i, p.elevation) for i, p in enumerate(points) if p.elevation is not None]
    if len(known) < _MIN_INTERP_NEIGHBORS:
        return points, 0
    known_idx = [k[0] for k in known]
    known_elev = [k[1] for k in known]
    result = list(points)
    count = 0
    for i, point in enumerate(points):
        if point.elevation is not None:
            continue
        left_j = right_j = -1
        for j, ki in enumerate(known_idx):
            if ki < i:
                left_j = j
            elif ki > i:
                right_j = j
                break
        if left_j == -1 or right_j == -1:
            continue
        li, ri = known_idx[left_j], known_idx[right_j]
        frac = (i - li) / (ri - li)
        interp = float(known_elev[left_j]) + frac * (
            float(known_elev[right_j]) - float(known_elev[left_j])
        )
        result[i] = replace(point, elevation=Meters(interp))
        count += 1
    return tuple(result), count


def _smooth_segment(points: tuple[TrackPoint, ...]) -> tuple[TrackPoint, ...]:
    """Apply Savitzky-Golay smoothing to latitude, longitude, and elevation."""
    if len(points) <= _SG_WINDOW:
        return points
    window = min(_SG_WINDOW, len(points))
    lats_arr = [float(p.latitude) for p in points]
    lons_arr = [float(p.longitude) for p in points]
    raw_lats = list(map(float, savgol_filter(lats_arr, window, _SG_POLYORDER)))
    raw_lons = list(map(float, savgol_filter(lons_arr, window, _SG_POLYORDER)))
    elev_known = [p.elevation for p in points if p.elevation is not None]
    raw_elevs: list[float] | None = (
        list(
            map(
                float,
                savgol_filter(
                    [float(e) for e in elev_known],
                    window,
                    _SG_POLYORDER,
                ),
            )
        )
        if len(elev_known) == len(points)
        else None
    )
    smoothed: list[TrackPoint] = []
    for i, p in enumerate(points):
        new_lat = Latitude(raw_lats[i])
        new_lon = Longitude(raw_lons[i])
        if raw_elevs is not None:
            new_elev = Meters(raw_elevs[i])
            smoothed.append(
                replace(p, latitude=new_lat, longitude=new_lon, elevation=new_elev),
            )
        else:
            smoothed.append(replace(p, latitude=new_lat, longitude=new_lon))
    return tuple(smoothed)


def sanitize(track: TrackData, *, max_speed_mps: float = 41.67) -> SanitizedTrack:
    """Sanitize track data through the full cleaning pipeline.

    Pipeline steps (per segment, in order):
      1. Outlier removal — drop points with impossible speed from both neighbors
      2. Gap detection — count timestamp gaps >10 s (segments are NOT bridged)
      3. Elevation interpolation — fill missing elevation from nearest neighbors
      4. Smoothing — Savitzky-Golay filter on lat / lon / elev

    Args:
        track: Raw track data to sanitize.
        max_speed_mps: Maximum plausible speed in m/s (default 41.67 ≈ 150 km/h).

    Returns:
        SanitizedTrack containing the cleaned TrackData and SanitizationStats.
    """
    original = track.total_points
    total_removed = 0
    total_gaps = 0
    total_interpolated = 0
    cleaned_segments: list[TrackSegment] = []
    for seg in track.segments:
        pts, removed = _remove_outliers(seg.points, max_speed_mps)
        total_removed += removed
        total_gaps += _count_gaps(pts)
        pts, interpolated = _interpolate_elevation(pts)
        total_interpolated += interpolated
        pts = _smooth_segment(pts)
        cleaned_segments.append(TrackSegment(points=pts))
    cleaned = replace(track, segments=tuple(cleaned_segments))
    stats = SanitizationStats(
        original_points=original,
        final_points=cleaned.total_points,
        outliers_removed=total_removed,
        points_interpolated=total_interpolated,
        segments_merged=0,
        gaps_detected=total_gaps,
    )
    return SanitizedTrack(track=cleaned, stats=stats)
