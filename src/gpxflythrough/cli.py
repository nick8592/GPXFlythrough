"""CLI entry point for GPXFlythrough.

Provides ``parse``, ``info``, and ``view`` subcommands backed by the
parser, sanitization, export, and viewer modules. The ``view`` command
supports both 2D (MapLibre) and 3D (CesiumJS) renderer modes.
"""

from __future__ import annotations

import shutil
import signal as _signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Annotated, Literal, cast

import typer
from rich.console import Console
from rich.table import Table

from gpxflythrough.export import to_geojson, to_json, write_geojson, write_json
from gpxflythrough.models import SanitizedTrack, TrackData
from gpxflythrough.parser import GPXParseError, parse_gpx_file
from gpxflythrough.sanitize import sanitize
from gpxflythrough.viewer.payload import ViewOptions, build_view_payload
from gpxflythrough.viewer.server import ViewServer

app = typer.Typer(
    rich_markup_mode="rich",
    help="Convert GPX tracks into interactive 2D/3D flythrough visualizations.",
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


def _resolve_dist_dir(mode: Literal["2d", "3d"] = "3d") -> Path:
    """Resolve the renderer dist/ directory, building if needed."""
    renderer_dir_name = "renderer2d" if mode == "2d" else "renderer"
    label = "2D map" if mode == "2d" else "3D"

    repo_root = Path(__file__).resolve().parent.parent.parent
    dist_dir = repo_root / renderer_dir_name / "dist"
    if dist_dir.is_dir():
        return dist_dir

    node_bin = shutil.which("node")
    if node_bin is None:
        msg = (
            "[red]Error:[/red] Node.js is required to build"
            f" the {label} renderer. Install Node.js 20+ and retry."
        )
        _ERR.print(msg)
        raise SystemExit(1) from None

    _ERR.print(f"[dim]Building {label} renderer (first run)…[/dim]")
    target_dir = repo_root / renderer_dir_name
    try:
        _ = subprocess.run(
            ["npm", "ci"],  # noqa: S607
            cwd=str(target_dir),
            check=True,
            capture_output=True,
            timeout=120,
        )
        _ = subprocess.run(
            ["npm", "run", "build"],  # noqa: S607
            cwd=str(target_dir),
            check=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.decode() if exc.stderr else str(exc)
        _ERR.print(f"[red]Build failed:[/red] {err_msg}")
        raise SystemExit(1) from None
    except FileNotFoundError:
        _ERR.print("[red]Error:[/red] npm not found. Install Node.js 20+ and retry.")
        raise SystemExit(1) from None

    if not dist_dir.is_dir():
        msg = f"[red]Error:[/red] Build completed but dist/ not found at {dist_dir}"
        _ERR.print(msg)
        raise SystemExit(1) from None

    return dist_dir


@app.command()
def view(  # noqa: PLR0913, PLR0917
    gpx_path: Annotated[
        Path,
        typer.Argument(help="Path to the GPX file.", exists=True),
    ],
    mode: Annotated[
        str,
        typer.Option("--mode", help="Viewer mode: 2d (MapLibre) or 3d (CesiumJS)."),
    ] = "3d",
    no_terrain: Annotated[
        bool,
        typer.Option("--no-terrain", help="Disable terrain (flat ellipsoid, 3D only)."),
    ] = False,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Don't open browser automatically."),
    ] = False,
    port: Annotated[
        int,
        typer.Option("--port", help="Server port (0 = random)."),
    ] = 0,
    theme: Annotated[
        str,
        typer.Option("--theme", help="Visual theme: dark or light."),
    ] = "dark",
    speed: Annotated[
        float,
        typer.Option("--speed", help="Initial playback speed (0.5, 1, 2, 4)."),
    ] = 1.0,
    height: Annotated[
        float,
        typer.Option("--height", help="Camera height above terrain (meters, 3D only)."),
    ] = 50.0,
    token: Annotated[
        str | None,
        typer.Option("--token", help="Cesium Ion access token (3D only)."),
    ] = None,
) -> None:
    """Open an interactive 2D or 3D flythrough viewer for a GPX track."""
    if mode not in {"2d", "3d"}:
        _ERR.print(f"[red]Error:[/red] Unknown mode: {mode!r} (use 2d or 3d)")
        raise SystemExit(1)

    if theme not in {"dark", "light"}:
        _ERR.print(f"[red]Error:[/red] Unknown theme: {theme!r} (use dark or light)")
        raise SystemExit(1)

    try:
        track = parse_gpx_file(gpx_path)
    except GPXParseError as exc:
        _ERR.print(f"[red]Parse error:[/red] {exc}")
        raise SystemExit(1) from None

    sanitized = sanitize(track)

    opts = ViewOptions(
        theme=cast("Literal['dark', 'light']", theme),
        no_terrain=no_terrain,
        height_m=height,
        ion_token=token,
    )
    payload_bytes = build_view_payload(sanitized, opts)
    payload_json = payload_bytes.decode("utf-8")

    dist_dir = _resolve_dist_dir(cast("Literal['2d', '3d']", mode))

    server = ViewServer(dist_dir, payload_json)
    bound_port = server.start(port=port)

    url = f"http://127.0.0.1:{bound_port}/"
    if speed != 1.0:
        url += f"?speed={speed}"

    viewer_label = "2D map" if mode == "2d" else "3D flythrough"
    msg = (
        f"\n  [bold green]GPXFlythrough {viewer_label}"
        + f" viewer running:[/bold green] {url}\n"
    )
    _ERR.print(msg)

    if not no_browser:
        try:
            _ = webbrowser.open(url)
        except Exception:  # noqa: BLE001
            _ERR.print("[dim]Could not open browser automatically.[/dim]")

    try:
        _signal.pause()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.stop()
        _ERR.print("\nViewer stopped.")
