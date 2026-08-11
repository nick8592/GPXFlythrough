"""Unit tests for the render CLI subcommand."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gpxflythrough.cli import app

runner = CliRunner()


class TestRenderCli:
    """Tests for the `gpxflythrough render` command."""

    def test_render_help_shows_flags(self) -> None:
        """--help shows all expected flags."""
        result = runner.invoke(app, ["render", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--resolution" in result.output
        assert "--fps" in result.output
        assert "--camera" in result.output
        assert "--height" in result.output
        assert "--duration" in result.output
        assert "--no-terrain" in result.output
        assert "--output" in result.output

    def test_render_mode_2d_errors_with_phase_2(self) -> None:
        """--mode 2d exits with Phase 2 error."""
        result = runner.invoke(app, [
            "render", "--mode", "2d",
            "examples/Nangang_Ridge_Hike.gpx",
            "-o", "/tmp/x.mp4",
        ])
        assert result.exit_code == 1
        assert "Phase 2" in result.output

    def test_render_camera_birdseye_errors_with_phase_5(self) -> None:
        """--camera birdseye exits with Phase 5 error."""
        result = runner.invoke(app, [
            "render", "--camera", "birdseye",
            "examples/Nangang_Ridge_Hike.gpx",
            "-o", "/tmp/x.mp4",
        ])
        assert result.exit_code == 1
        assert "Phase 5" in result.output

    def test_render_camera_cinematic_errors_with_phase_5(self) -> None:
        """--camera cinematic exits with Phase 5 error."""
        result = runner.invoke(app, [
            "render", "--camera", "cinematic",
            "examples/Nangang_Ridge_Hike.gpx",
            "-o", "/tmp/x.mp4",
        ])
        assert result.exit_code == 1
        assert "Phase 5" in result.output

    def test_render_overlays_custom_errors_with_phase_4(self) -> None:
        """Custom --overlays exits with Phase 4 error."""
        result = runner.invoke(app, [
            "render", "--overlays", "hr",
            "examples/Nangang_Ridge_Hike.gpx",
            "-o", "/tmp/x.mp4",
        ])
        assert result.exit_code == 1
        assert "Phase 4" in result.output

    def test_render_theme_custom_errors_with_phase_5(self) -> None:
        """Custom --theme exits with Phase 5 error."""
        result = runner.invoke(app, [
            "render", "--theme", "light",
            "examples/Nangang_Ridge_Hike.gpx",
            "-o", "/tmp/x.mp4",
        ])
        assert result.exit_code == 1
        assert "Phase 5" in result.output

    def test_render_valid_flags_no_phase_errors(self) -> None:
        """Valid flags pass stub-gate without phase errors.

        render_pipeline is mocked to avoid spawning Node.js.
        """
        with patch(
            "gpxflythrough.cli.render_pipeline",
            return_value=Path("/tmp/x.mp4"),
        ):
            result = runner.invoke(app, [
                "render", "--no-terrain", "--camera", "follow",
                "examples/Nangang_Ridge_Hike.gpx",
                "-o", "/tmp/x.mp4",
            ])
        assert "Phase 2" not in result.output
        assert "Phase 4" not in result.output
        assert "Phase 5" not in result.output
