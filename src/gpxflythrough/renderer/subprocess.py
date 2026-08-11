"""Subprocess management for the Node.js renderer."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from gpxflythrough.renderer.exceptions import NodeNotFoundError, RendererError

_RENDERER_REL_PATH = Path("renderer") / "dist" / "bin" / "render.js"


def renderer_bin_path() -> Path:
    """Resolve the path to the built renderer CLI binary."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    bin_path = repo_root / _RENDERER_REL_PATH
    if not bin_path.exists():
        msg = (
            "Renderer not built — run: npm --prefix renderer run build\n"
            f"Expected: {bin_path}"
        )
        raise RendererError(msg)
    return bin_path


def node_bin_path() -> str:
    """Resolve the path to the Node.js binary."""
    node = shutil.which("node")
    if node is None:
        msg = "Node.js not found. Install Node.js >= 20: https://nodejs.org/"
        raise NodeNotFoundError(msg)
    return node


def spawn_render_subprocess(
    args: list[str],
) -> subprocess.Popen[str]:
    """Spawn the renderer subprocess with the given CLI arguments."""
    node = node_bin_path()
    renderer = renderer_bin_path()
    full_args = [node, str(renderer), *args]

    # Pass through PUPPETEER_EXECUTABLE_PATH if set in parent environment
    env = os.environ.copy()

    return subprocess.Popen(  # noqa: S603
        full_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )


def drain_subprocess_stderr(
    proc: subprocess.Popen[str],
    log_file: Path,
) -> str:
    """Read stderr from subprocess, write to log file, return content."""
    stderr_content = ""
    if proc.stderr is not None:
        stderr_content = proc.stderr.read()
        _ = log_file.write_text(stderr_content)
    return stderr_content
