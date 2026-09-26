"""Source-file validation and output-path resolution.

Two responsibilities kept deliberately separate: validating that a Markdown
file can actually be read (:func:`validate_source_path`), and deciding where
a converted file should be written (:func:`resolve_output_path`), including
never silently overwriting an existing file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .config import MAX_FILE_SIZE_MB, SUPPORTED_INPUT_EXTENSIONS
from .errors import FileValidationError, OutputPathError

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def validate_source_path(raw_path: str, allowed_extensions: tuple[str, ...] | None = None) -> Path:
    """Validate a user-supplied source file path.

    Raises :class:`FileValidationError` with a specific, human-readable
    message for every failure mode: empty input, path doesn't exist, it's a
    directory, wrong extension, unreadable, or empty file.
    """
    extensions = allowed_extensions or SUPPORTED_INPUT_EXTENSIONS
    text = (raw_path or "").strip().strip('"').strip("'")
    if not text:
        raise FileValidationError("No file path was entered.")

    path = Path(text).expanduser()

    if not path.exists():
        raise FileValidationError(
            f"File does not exist: {path}",
            details="Check the path for typos, or use Browse to select the file.",
        )
    if path.is_dir():
        raise FileValidationError(
            f"'{path}' is a folder, not a file.",
            details="Select a specific file, not its containing folder.",
        )
    if path.suffix.lower() not in extensions:
        raise FileValidationError(
            f"Unsupported file type: '{path.suffix or '(none)'}'",
            details=f"Supported extensions: {', '.join(extensions)}",
        )
    if not os.access(path, os.R_OK):
        raise FileValidationError(
            f"Permission denied reading: {path}",
            details="Check the file's permissions, or that it isn't open exclusively "
                    "in another program.",
        )

    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError as exc:
        raise FileValidationError(f"Could not read file size for: {path}") from exc

    if size_mb == 0:
        raise FileValidationError(f"File is empty: {path}")

    return path


def is_large_file(path: Path) -> bool:
    """Whether a file is large enough to warrant a size warning in the UI."""
    try:
        return path.stat().st_size / (1024 * 1024) > MAX_FILE_SIZE_MB
    except OSError:
        return False


def sanitize_filename(name: str) -> str:
    """Strip characters that are invalid in filenames on any major OS.

    Consecutive invalid characters collapse into a single underscore, so
    e.g. a run of path-separator-like characters doesn't turn into a string
    of underscores.
    """
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name).strip().strip(".")
    return cleaned or "output"


def build_output_filename(source_path: Path, output_format: str, custom_name: str = "") -> str:
    """Build the output filename with the correct extension.

    If ``custom_name`` is given, it's sanitised and used as the stem
    (any extension the user typed is stripped and replaced with the
    correct one for ``output_format``). Otherwise the source file's stem
    is reused, e.g. ``report.md`` -> ``report.pdf``.
    """
    stem = Path(custom_name).stem if custom_name.strip() else source_path.stem
    stem = sanitize_filename(stem)
    return f"{stem}.{output_format.lower()}"


def resolve_output_directory(source_path: Path, same_folder: bool, custom_dir: str) -> Path:
    """Resolve the target directory per the user's output-location choice."""
    if same_folder or not custom_dir.strip():
        return source_path.parent

    directory = Path(custom_dir.strip()).expanduser()
    if directory.exists() and not directory.is_dir():
        raise OutputPathError(f"'{directory}' exists and is not a folder.")
    return directory


def resolve_collision(target_path: Path, on_collision: str) -> Path | None:
    """Resolve a filename collision per the chosen strategy.

    ``on_collision`` is one of ``"replace"``, ``"new_copy"``, or ``"cancel"``.
    Returns the path to actually write to, or ``None`` if the caller should
    cancel this file. ``"new_copy"`` appends " (1)", " (2)", etc. until a
    free name is found.
    """
    if not target_path.exists():
        return target_path
    if on_collision == "replace":
        return target_path
    if on_collision == "cancel":
        return None
    if on_collision == "new_copy":
        stem, suffix, parent = target_path.stem, target_path.suffix, target_path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
    raise OutputPathError(f"Unknown collision strategy: '{on_collision}'")


def ensure_writable_directory(directory: Path) -> None:
    """Create ``directory`` if needed and confirm it's writable."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputPathError(f"Could not create output folder: {directory}") from exc
    if not os.access(directory, os.W_OK):
        raise OutputPathError(f"Permission denied writing to: {directory}")
