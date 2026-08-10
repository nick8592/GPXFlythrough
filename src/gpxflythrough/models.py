"""Domain models for GPX track data.

All structured data in the pipeline flows through these types.
Parse at the boundary (gpxpy → TrackData), then operate on typed values.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import NewType

# ── Branded primitives ──────────────────────────────────────────

Latitude = NewType("Latitude", float)
Longitude = NewType("Longitude", float)
Meters = NewType("Meters", float)
MetersPerSecond = NewType("MetersPerSecond", float)
BPM = NewType("BPM", int)  # heart rate
RPM = NewType("RPM", int)  # cadence
Celsius = NewType("Celsius", float)


# ── Core track types ────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TrackPoint:
    """Single recorded point on a GPS track."""

    latitude: Latitude
    longitude: Longitude
    elevation: Meters | None
    time: datetime | None
    speed: MetersPerSecond | None = None
    heart_rate: BPM | None = None
    cadence: RPM | None = None
    temperature: Celsius | None = None


@dataclass(frozen=True, slots=True)
class TrackSegment:
    """Contiguous sequence of track points.

    A new segment starts whenever GPS recording is interrupted
    (tunnel, paused device, etc.). Segments must NEVER be naively
    bridged — the path between segments is undefined.
    """

    points: tuple[TrackPoint, ...]


@dataclass(frozen=True, slots=True)
class Waypoint:
    """Standalone point of interest (POI) from a GPX file."""

    latitude: Latitude
    longitude: Longitude
    elevation: Meters | None
    name: str | None = None
    time: datetime | None = None


@dataclass(frozen=True, slots=True)
class TrackData:
    """Complete parsed track data from a single GPX file.

    This is the primary data structure that flows through the entire
    pipeline: parse → sanitize → export.
    """

    name: str
    activity_type: str | None
    time: datetime | None
    segments: tuple[TrackSegment, ...]
    waypoints: tuple[Waypoint, ...] = ()

    @property
    def all_points(self) -> tuple[TrackPoint, ...]:
        """Flatten all segments into a single point tuple."""
        points: list[TrackPoint] = []
        for segment in self.segments:
            points.extend(segment.points)
        return tuple(points)

    @property
    def total_points(self) -> int:
        """Total number of track points across all segments."""
        return sum(len(seg.points) for seg in self.segments)

    @property
    def total_segments(self) -> int:
        """Number of track segments."""
        return len(self.segments)


# ── Sanitization result types ───────────────────────────────────


@dataclass(frozen=True, slots=True)
class SanitizationStats:
    """Summary of what the sanitization pipeline changed."""

    original_points: int
    final_points: int
    outliers_removed: int
    points_interpolated: int
    segments_merged: int
    gaps_detected: int


@dataclass(frozen=True, slots=True)
class SanitizedTrack:
    """Track data after sanitization, with stats about what changed."""

    track: TrackData
    stats: SanitizationStats
