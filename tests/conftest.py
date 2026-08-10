"""Shared test fixtures — raw GPX XML strings and parsed domain objects."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from gpxflythrough.models import (
    BPM,
    RPM,
    Celsius,
    Latitude,
    Longitude,
    Meters,
    MetersPerSecond,
    SanitizationStats,
    SanitizedTrack,
    TrackData,
    TrackPoint,
    TrackSegment,
    Waypoint,
)

# ── GPX XML fixtures ────────────────────────────────────────────────


@pytest.fixture
def minimal_gpx() -> str:
    """Simple GPX with 1 track, 1 segment, 3 points, elevation, time."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Test Hike</name>
    <type>Hiking</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <ele>125.0</ele>
        <time>2025-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="25.0340" lon="121.5660">
        <ele>130.0</ele>
        <time>2025-01-15T08:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def multi_segment_gpx() -> str:
    """GPX with 2 track segments (simulating GPS interruption)."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Tunnel Walk</name>
    <type>Walking</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <ele>125.0</ele>
        <time>2025-01-15T08:01:00Z</time>
      </trkpt>
    </trkseg>
    <trkseg>
      <trkpt lat="25.0400" lon="121.5700">
        <ele>150.0</ele>
        <time>2025-01-15T08:30:00Z</time>
      </trkpt>
      <trkpt lat="25.0405" lon="121.5705">
        <ele>155.0</ele>
        <time>2025-01-15T08:31:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def garmin_extensions_gpx() -> str:
    """GPX with Garmin TrackPointExtension (HR, cadence, speed, temperature)."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1"
  xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
  <trk>
    <name>Run with HR</name>
    <type>Running</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>145</gpxtpx:hr>
            <gpxtpx:cad>85</gpxtpx:cad>
            <gpxtpx:speed>2.8</gpxtpx:speed>
            <gpxtpx:atemp>28.5</gpxtpx:atemp>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <ele>125.0</ele>
        <time>2025-01-15T08:01:00Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>152</gpxtpx:hr>
            <gpxtpx:cad>88</gpxtpx:cad>
            <gpxtpx:speed>3.1</gpxtpx:speed>
            <gpxtpx:atemp>29.0</gpxtpx:atemp>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def missing_elevation_gpx() -> str:
    """GPX where some points have no elevation."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Mixed Elevation</name>
    <type>Hiking</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <time>2025-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="25.0340" lon="121.5660">
        <ele>130.0</ele>
        <time>2025-01-15T08:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def timestamp_gap_gpx() -> str:
    """GPX with a 60-second gap between two points."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Gap Walk</name>
    <type>Walking</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <ele>125.0</ele>
        <time>2025-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="25.0340" lon="121.5660">
        <ele>130.0</ele>
        <time>2025-01-15T08:02:00Z</time>
      </trkpt>
      <trkpt lat="25.0360" lon="121.5680">
        <ele>140.0</ele>
        <time>2025-01-15T08:03:10Z</time>
      </trkpt>
      <trkpt lat="25.0370" lon="121.5690">
        <ele>145.0</ele>
        <time>2025-01-15T08:04:10Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def gps_spike_gpx() -> str:
    """GPX with an impossible speed spike (>150 km/h).

    Points are 1 second apart. The spike point jumps ~500m in 1s (~1800 km/h).
    """
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Spike Track</name>
    <type>Hiking</type>
    <trkseg>
      <trkpt lat="25.0330" lon="121.5650">
        <ele>120.0</ele>
        <time>2025-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="25.0335" lon="121.5655">
        <ele>122.0</ele>
        <time>2025-01-15T08:00:01Z</time>
      </trkpt>
      <trkpt lat="25.0370" lon="121.5710">
        <ele>121.0</ele>
        <time>2025-01-15T08:00:02Z</time>
      </trkpt>
      <trkpt lat="25.0340" lon="121.5660">
        <ele>124.0</ele>
        <time>2025-01-15T08:00:03Z</time>
      </trkpt>
      <trkpt lat="25.0345" lon="121.5665">
        <ele>126.0</ele>
        <time>2025-01-15T08:00:04Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def waypoint_gpx() -> str:
    """GPX with only waypoints, no tracks."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="25.0330" lon="121.5650">
    <ele>120.0</ele>
    <name>Summit</name>
    <time>2025-01-15T08:00:00Z</time>
  </wpt>
  <wpt lat="25.0400" lon="121.5700">
    <ele>80.0</ele>
    <name>Trailhead</name>
  </wpt>
</gpx>"""


@pytest.fixture
def empty_gpx() -> str:
    """Minimal valid GPX with no tracks or waypoints."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
  xmlns="http://www.topografix.com/GPX/1/1">
</gpx>"""


@pytest.fixture
def nangang_path() -> Path:
    """Path to the real Nangang Ridge Hike example GPX file."""
    root = Path(__file__).resolve().parent.parent
    return root / "examples" / "Nangang_Ridge_Hike.gpx"


# ── Parsed domain-object fixtures ──────────────────────────────────


@pytest.fixture
def minimal_track() -> TrackData:
    """A simple 3-point track for unit-testing sanitize / export."""
    return TrackData(
        name="Test Hike",
        activity_type="Hiking",
        time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
        segments=(
            TrackSegment(points=(
                TrackPoint(
                    latitude=Latitude(25.0330),
                    longitude=Longitude(121.5650),
                    elevation=Meters(120.0),
                    time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
                ),
                TrackPoint(
                    latitude=Latitude(25.0335),
                    longitude=Longitude(121.5655),
                    elevation=Meters(125.0),
                    time=datetime(2025, 1, 15, 8, 1, 0, tzinfo=UTC),
                ),
                TrackPoint(
                    latitude=Latitude(25.0340),
                    longitude=Longitude(121.5660),
                    elevation=Meters(130.0),
                    time=datetime(2025, 1, 15, 8, 2, 0, tzinfo=UTC),
                ),
            )),
        ),
    )


@pytest.fixture
def clean_sanitized_track(minimal_track: TrackData) -> SanitizedTrack:
    """A SanitizedTrack with clean data (no changes expected)."""
    stats = SanitizationStats(
        original_points=3,
        final_points=3,
        outliers_removed=0,
        points_interpolated=0,
        segments_merged=0,
        gaps_detected=0,
    )
    return SanitizedTrack(track=minimal_track, stats=stats)


@pytest.fixture
def track_with_extensions() -> TrackData:
    """Track data with Garmin extensions populated."""
    return TrackData(
        name="Run with HR",
        activity_type="Running",
        time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
        segments=(
            TrackSegment(points=(
                TrackPoint(
                    latitude=Latitude(25.0330),
                    longitude=Longitude(121.5650),
                    elevation=Meters(120.0),
                    time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
                    speed=MetersPerSecond(2.8),
                    heart_rate=BPM(145),
                    cadence=RPM(85),
                    temperature=Celsius(28.5),
                ),
                TrackPoint(
                    latitude=Latitude(25.0335),
                    longitude=Longitude(121.5655),
                    elevation=Meters(125.0),
                    time=datetime(2025, 1, 15, 8, 1, 0, tzinfo=UTC),
                    speed=MetersPerSecond(3.1),
                    heart_rate=BPM(152),
                    cadence=RPM(88),
                    temperature=Celsius(29.0),
                ),
            )),
        ),
    )


@pytest.fixture
def track_with_waypoints() -> TrackData:
    """Track data with waypoints and no segments."""
    return TrackData(
        name="",
        activity_type=None,
        time=None,
        segments=(),
        waypoints=(
            Waypoint(
                latitude=Latitude(25.0330),
                longitude=Longitude(121.5650),
                elevation=Meters(120.0),
                name="Summit",
                time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
            ),
            Waypoint(
                latitude=Latitude(25.0400),
                longitude=Longitude(121.5700),
                elevation=Meters(80.0),
                name="Trailhead",
                time=None,
            ),
        ),
    )


@pytest.fixture
def track_none_elevation() -> TrackData:
    """Track data where points have no elevation."""
    return TrackData(
        name="No Elevation",
        activity_type="Hiking",
        time=None,
        segments=(
            TrackSegment(points=(
                TrackPoint(
                    latitude=Latitude(25.0330),
                    longitude=Longitude(121.5650),
                    elevation=None,
                    time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC),
                ),
                TrackPoint(
                    latitude=Latitude(25.0335),
                    longitude=Longitude(121.5655),
                    elevation=None,
                    time=datetime(2025, 1, 15, 8, 1, 0, tzinfo=UTC),
                ),
            )),
        ),
    )
