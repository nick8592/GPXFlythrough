"""CLI entry point for GPXFlythrough.

Provides ``parse``, ``info``, and ``render`` subcommands backed
by the parser, sanitization, export, and renderer modules.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from gpxflythrough.export import to_geojson, to_json, write_geojson, write_json
from gpxflythrough.models import SanitizedTrack, TrackData
from gpxflythrough.parser import GPXParseError, parse_gpx_file
from gpxflythrough.renderer.exceptions import RendererError
from gpxflythrough.renderer.pipeline import render_pipeline
from gpxflythrough.renderer.schema import RenderOptions, Resolution
from gpxflythrough.sanitize import sanitize

_DEFAULT_OUTPUT = Path("output.mp4")

app = typer.Typer(
    rich_markup_mode="rich",
    help="Convert GPX tracks into 2D/3D visualization videos.",
)

_ERR = Console(stderr=True)


def _print_track_table(
    console: Console,
    data: TrackData,
    sanitized: SanitizedTrack | None,
) -> None:
    """Print a rich summary table for parsed track data."""
    table = Table(title=data.name or "GPX Track")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Activity", data.activity_type or "unknown")
    table.add_row("Segments", str(data.total_segments))
    table.add_row("Points", str(data.total_points))
    if sanitized is not None:
        s = sanitized.stats
        table.add_row("Outliers removed", str(s.outliers_removed))
        table.add_row("Points interpolated", str(s.points_interpolated))
        table.add_row("Gaps detected", str(s.gaps_detected))
    console.print(table)


@app.command()
def parse(
    gpx_path: Annotated[
        Path,
        typer.Argument(help="Path to the GPX file.", exists=True),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path."),
    ] = None,
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: json or geojson.",
        ),
    ] = "json",
    no_sanitize: Annotated[
        bool,
        typer.Option("--no-sanitize", help="Skip data sanitization."),
    ] = False,
) -> None:
    """Parse and sanitize a GPX file, export as JSON or GeoJSON."""
    try:
        track = parse_gpx_file(gpx_path)
    except GPXParseError as exc:
        _ERR.print(f"[red]Parse error:[/red] {exc}")
        raise SystemExit(1) from None

    sanitized: SanitizedTrack | None = None
    if no_sanitize:
        result: TrackData | SanitizedTrack = track
    else:
        sanitized = sanitize(track)
        result = sanitized

    _print_track_table(Console(), track, sanitized)

    if fmt == "geojson":
        payload = to_geojson(result)
    elif fmt == "json":
        payload = to_json(result)
    else:
        _ERR.print(f"[red]Unknown format:[/red] {fmt!r} (use json or geojson)")
        raise SystemExit(1)

    if output is not None:
        write_fn = write_geojson if fmt == "geojson" else write_json
        write_fn(result, output)
        Console().print(f"Written to [green]{output}[/green]")
    else:
        _ = sys.stdout.buffer.write(payload)
        _ = sys.stdout.buffer.write(b"\n")


@app.command()
def info(
    gpx_path: Annotated[
        Path,
        typer.Argument(help="Path to the GPX file.", exists=True),
    ],
) -> None:
    """Show summary information about a GPX file."""
    try:
        track = parse_gpx_file(gpx_path)
    except GPXParseError as exc:
        _ERR.print(f"[red]Parse error:[/red] {exc}")
        raise SystemExit(1) from None

    points = track.all_points
    elevations = [p.elevation for p in points if p.elevation is not None]
    has_hr = any(p.heart_rate is not None for p in points)
    has_cad = any(p.cadence is not None for p in points)
    has_spd = any(p.speed is not None for p in points)

    console = Console()
    table = Table(title=track.name or "GPX Track Info")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Activity", track.activity_type or "unknown")
    table.add_row("Segments", str(track.total_segments))
    table.add_row("Total points", str(track.total_points))
    if elevations:
        table.add_row("Elevation min", f"{min(elevations):.1f} m")
        table.add_row("Elevation max", f"{max(elevations):.1f} m")
    table.add_row("Has HR data", "yes" if has_hr else "no")
    table.add_row("Has cadence", "yes" if has_cad else "no")
    table.add_row("Has speed", "yes" if has_spd else "no")
    if track.time is not None:
        table.add_row("Start time", track.time.isoformat())
    console.print(table)


@app.command()
def render(  # noqa: PLR0913, PLR0917
    gpx_path: Annotated[
        Path,
        typer.Argument(help="Path to the GPX file.", exists=True),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output MP4 file path."),
    ] = _DEFAULT_OUTPUT,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Render mode: 3d (2d coming in Phase 2).",
        ),
    ] = "3d",
    resolution: Annotated[
        str,
        typer.Option("--resolution", help="Resolution: 720p, 1080p, 4k."),
    ] = "1080p",
    fps: Annotated[
        int,
        typer.Option("--fps", help="Frames per second: 24, 30, 60."),
    ] = 30,
    camera: Annotated[
        str,
        typer.Option(
            "--camera",
            help="Camera mode: follow (others in Phase 5).",
        ),
    ] = "follow",
    height: Annotated[
        float,
        typer.Option(
            "--height",
            help="Camera height above terrain (meters).",
        ),
    ] = 50.0,
    duration: Annotated[
        float,
        typer.Option(
            "--duration",
            help="Animation duration (seconds).",
        ),
    ] = 30.0,
    no_terrain: Annotated[
        bool,
        typer.Option("--no-terrain", help="Disable terrain (flat ellipsoid)."),
    ] = False,
    cache_dir: Annotated[
        str,
        typer.Option(
            "--cache-dir",
            help="Chrome disk cache directory.",
        ),
    ] = "/tmp/gpx-renderer-chrome-cache",  # noqa: S108
    ffmpeg_path: Annotated[
        str | None,
        typer.Option("--ffmpeg-path", help="Path to ffmpeg binary."),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option("--token", help="Cesium Ion access token."),
    ] = None,
    overlays: Annotated[
        str,
        typer.Option("--overlays", help="Data overlays (Phase 4)."),
    ] = "elevation",
    theme: Annotated[
        str,
        typer.Option("--theme", help="Visual theme (Phase 5)."),
    ] = "dark",
) -> None:
    """Render a 3D flythrough video from a GPX track."""
    # Stub errors for future phases
    if mode == "2d":
        _ERR.print("[red]Error:[/red] 2D mode not yet supported — coming in Phase 2")
        raise SystemExit(1)
    if camera in ("birdseye", "cinematic", "orbit"):
        msg = (
            f"[red]Error:[/red] Camera '{camera}' not yet supported — coming in Phase 5"
        )
        _ERR.print(msg)
        raise SystemExit(1)
    if overlays != "elevation":
        _ERR.print("[red]Error:[/red] Custom overlays not yet supported — Phase 4")
        raise SystemExit(1)
    if theme != "dark":
        _ERR.print("[red]Error:[/red] Custom themes not yet supported — Phase 5")
        raise SystemExit(1)

    opts = RenderOptions(
        mode=mode,
        resolution=cast("Resolution", resolution),
        fps=fps,
        camera_mode=camera,
        height_m=height,
        duration_s=duration,
        no_terrain=no_terrain,
        cache_dir=cache_dir,
        ffmpeg_path=ffmpeg_path,
        ion_token=token,
    )

    try:
        result = render_pipeline(gpx_path, output, opts)
    except RendererError as exc:
        _ERR.print(f"[red]Render error:[/red] {exc.message}")
        raise SystemExit(1) from None
    except Exception as exc:  # noqa: BLE001
        _ERR.print(f"[red]Unexpected error:[/red] {exc}")
        raise SystemExit(1) from None
    else:
        Console().print(f"Video rendered: [green]{result}[/green]")
