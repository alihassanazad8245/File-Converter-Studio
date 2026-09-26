"""Typed exceptions used across the application.

Every error the UI shows to the user derives from :class:`AppError`, so the
GUI can present a friendly message with an optional "Show Details" expander
instead of a raw traceback.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all expected, user-facing errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class FileValidationError(AppError):
    """Raised when a source Markdown file path is invalid."""


class OutputPathError(AppError):
    """Raised when an output path cannot be resolved or written to."""


class ConversionError(AppError):
    """Raised when a specific format conversion fails."""


class SettingsError(AppError):
    """Raised when settings cannot be loaded or saved."""
