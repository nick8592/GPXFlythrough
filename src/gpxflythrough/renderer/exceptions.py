"""Custom exceptions for the renderer pipeline."""

from __future__ import annotations


class RendererError(Exception):
    """Base exception for renderer errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        self.message: str = message
        super().__init__(message)


class FFmpegNotFoundError(RendererError):
    """Raised when FFmpeg binary cannot be found or is too old."""


class NodeNotFoundError(RendererError):
    """Raised when Node.js binary cannot be found."""


class RenderSchemaError(RendererError):
    """Raised when render options or payload validation fails."""
