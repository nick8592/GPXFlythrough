"""GPX parser — converts raw GPX XML into typed domain models.

Boundary module: gpxpy objects enter here, ``TrackData`` exits.
All downstream code operates on the typed domain models only.
"""

from __future__ import annotations

from collections.abc import Sized
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

import gpxpy
import gpxpy.gpx

from gpxflythrough.models import (
    BPM,
    RPM,
    Celsius,
    Latitude,
    Longitude,
    Meters,
    MetersPerSecond,
    TrackData,
    TrackPoint,
    TrackSegment,
    Waypoint,
)

if TYPE_CHECKING:
    from pathlib import Path

# Garmin TrackPointExtension namespace (Clark notation)
_TPE_NS = "{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}"


def _get_tag(ext: object) -> str | None:
    """Safely extract the ``.tag`` attribute from an extension element."""
    tag = getattr(ext, "tag", None)
    return tag if isinstance(tag, str) else None


def _get_text(ext: object) -> str | None:
    """Safely extract the ``.text`` attribute from an extension element."""
    text = getattr(ext, "text", None)
    return text if isinstance(text, str) else None


def _get_children(parent: object) -> list[object]:
    """Collect children of an XML Element via sequence iteration.

    ``xml.etree.ElementTree.Element`` is iterable via ``__getitem__``
    (sequence protocol) rather than ``__iter__``. We detect this by
    checking for ``__len__`` and ``__getitem__``, then iterate by index.
    """
    length: int = len(parent) if isinstance(parent, Sized) else 0
    if length == 0:
        return []
    getter = getattr(parent, "__getitem__", None)
    if getter is None:
        return []
    return [getter(i) for i in range(length)]


@dataclass(frozen=True, slots=True)
class GPXParseError(Exception):
    """Raised when GPX content cannot be parsed.

    Attributes:
        path: File path that failed, or ``None`` for raw-string input.
        detail: Human-readable description of the failure.
    """

    path: str | None
    detail: str

    @override
    def __str__(self) -> str:
        loc = self.path or "<string>"
        return f"GPX parse error ({loc}): {self.detail}"


def _child_float(parent: object, local_name: str) -> float | None:
    """Find a child by local name and parse its text as float."""
    target = f"{_TPE_NS}{local_name}"
    for child in _get_children(parent):
        if _get_tag(child) == target:
            text = _get_text(child)
            if text is not None:
                return float(text)
    return None


def _child_int(parent: object, local_name: str) -> int | None:
    """Find a child by local name and parse its text as int."""
    val = _child_float(parent, local_name)
    if val is None:
        return None
    return int(val)


def _extract_extensions(
    extensions: list[object],
) -> tuple[MetersPerSecond | None, BPM | None, RPM | None, Celsius | None]:
    """Extract Garmin TrackPointExtension data from gpxpy extensions list."""
    speed: MetersPerSecond | None = None
    heart_rate: BPM | None = None
    cadence: RPM | None = None
    temperature: Celsius | None = None

    for ext in extensions:
        tag = _get_tag(ext)
        if tag is None:
            continue
        local = tag.split("}", 1)[-1] if "}" in tag else tag
        if local != "TrackPointExtension":
            continue
        speed = (
            MetersPerSecond(v)
            if (v := _child_float(ext, "speed")) is not None
            else None
        )
        heart_rate = BPM(v) if (v := _child_int(ext, "hr")) is not None else None
        cadence = RPM(v) if (v := _child_int(ext, "cad")) is not None else None
        temperature = (
            Celsius(v) if (v := _child_float(ext, "atemp")) is not None else None
        )

    return speed, heart_rate, cadence, temperature


def _convert_point(pt: gpxpy.gpx.GPXTrackPoint) -> TrackPoint:
    """Convert a gpxpy track point to a domain ``TrackPoint``."""
    elevation = Meters(pt.elevation) if pt.elevation is not None else None
    speed, heart_rate, cadence, temperature = _extract_extensions(
        pt.extensions,
    )
    if pt.speed is not None and speed is None:
        speed = MetersPerSecond(pt.speed)

    return TrackPoint(
        latitude=Latitude(pt.latitude),
        longitude=Longitude(pt.longitude),
        elevation=elevation,
        time=pt.time,
        speed=speed,
        heart_rate=heart_rate,
        cadence=cadence,
        temperature=temperature,
    )


def _convert_waypoint(wp: gpxpy.gpx.GPXWaypoint) -> Waypoint:
    """Convert a gpxpy waypoint to a domain ``Waypoint``."""
    elevation = Meters(wp.elevation) if wp.elevation is not None else None
    return Waypoint(
        latitude=Latitude(wp.latitude),
        longitude=Longitude(wp.longitude),
        elevation=elevation,
        name=wp.name,
        time=wp.time,
    )


def parse_gpx(gpx_content: str) -> TrackData:
    """Parse a GPX XML string into typed ``TrackData``.

    Args:
        gpx_content: Raw GPX XML string.

    Returns:
        Fully typed track data with segments, waypoints, and extensions.

    Raises:
        GPXParseError: The XML is malformed or cannot be interpreted as GPX.
    """
    try:
        gpx = gpxpy.parse(gpx_content)
    except gpxpy.gpx.GPXXMLSyntaxException as exc:
        raise GPXParseError(path=None, detail=str(exc)) from exc
    except ValueError as exc:
        raise GPXParseError(path=None, detail=str(exc)) from exc

    segments: list[TrackSegment] = []
    for track in gpx.tracks:
        for seg in track.segments:
            points = tuple(_convert_point(p) for p in seg.points)
            segments.append(TrackSegment(points=points))

    waypoints = tuple(_convert_waypoint(w) for w in gpx.waypoints)

    name = gpx.tracks[0].name if gpx.tracks and gpx.tracks[0].name else ""
    activity_type = gpx.tracks[0].type if gpx.tracks and gpx.tracks[0].type else None

    return TrackData(
        name=name,
        activity_type=activity_type,
        time=gpx.time,
        segments=tuple(segments),
        waypoints=waypoints,
    )


def parse_gpx_file(path: Path) -> TrackData:
    """Read a GPX file and parse it into typed ``TrackData``.

    Args:
        path: Path to the ``.gpx`` file.

    Returns:
        Fully typed track data with segments, waypoints, and extensions.

    Raises:
        GPXParseError: File I/O failure or GPX content is invalid.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GPXParseError(path=str(path), detail=str(exc)) from exc

    try:
        return parse_gpx(content)
    except GPXParseError as exc:
        if exc.path is None:
            raise GPXParseError(path=str(path), detail=exc.detail) from exc
        raise
