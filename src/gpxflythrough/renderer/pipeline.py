"""Render pipeline — orchestrates GPX → JSON → Node renderer → MP4."""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from urllib.request import pathname2url

from gpxflythrough.parser import parse_gpx_file
from gpxflythrough.renderer.exceptions import RendererError
from gpxflythrough.renderer.schema import (
    RenderOptions,
    build_render_payload,
    validate_render_options,
)
from gpxflythrough.renderer.subprocess import (
    drain_subprocess_stderr,
    spawn_render_subprocess,
)
from gpxflythrough.sanitize import sanitize


def render_pipeline(
    gpx_path: Path,
    output_mp4: Path,
    opts: RenderOptions,
) -> Path:
    """Run the full render pipeline.

    GPX → sanitize → JSON → Node renderer → MP4.

    Args:
        gpx_path: Path to the input GPX file.
        output_mp4: Path for the output MP4 video.
        opts: Render configuration options.

    Returns:
        Path to the produced MP4 file.

    Raises:
        RenderSchemaError: If render options are invalid.
        RendererError: If the renderer subprocess fails.
    """
    validate_render_options(opts)

    track = parse_gpx_file(gpx_path)
    sanitized = sanitize(track)

    payload_bytes = build_render_payload(sanitized, opts)

    tmp_json = tempfile.NamedTemporaryFile(  # noqa: SIM115
        suffix=".json",
        prefix="gpxflythrough-",
        dir=tempfile.gettempdir(),
        delete=False,
    )
    try:
        _ = tmp_json.write(payload_bytes)
        tmp_json.close()

        file_url = f"file://{pathname2url(tmp_json.name)}"

        args = [
            "--input",
            file_url,
            "--output",
            str(output_mp4),
            "--resolution",
            opts.resolution,
            "--fps",
            str(opts.fps),
            "--height",
            str(opts.height_m),
            "--duration",
            str(opts.duration_s),
            "--cache-dir",
            opts.cache_dir,
        ]
        if opts.no_terrain:
            args.append("--no-terrain")
        if opts.ffmpeg_path is not None:
            args.extend(["--ffmpeg-path", opts.ffmpeg_path])
        if opts.ion_token is not None:
            args.extend(["--token", opts.ion_token])

        proc = spawn_render_subprocess(args)

        exit_code = proc.wait()

        stderr_log = Path(f"{tmp_json.name}.stderr.log")
        stderr_content = drain_subprocess_stderr(proc, stderr_log)

        if exit_code != 0:
            msg = (
                f"Renderer exited with code {exit_code}.\n"
                f"stderr: {stderr_content[:2000]}"
            )
            raise RendererError(msg)

        if not output_mp4.exists():
            msg = f"Renderer exited 0 but output file not found: {output_mp4}"
            raise RendererError(msg)

        return output_mp4

    finally:
        with contextlib.suppress(OSError):
            Path(tmp_json.name).unlink(missing_ok=True)
