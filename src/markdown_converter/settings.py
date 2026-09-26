"""Application settings, persisted as plain JSON.

No registry, no OS-specific config store - just a JSON file under
``.appdata/`` next to the project, so it's easy to inspect, back up, or
delete. Writes are atomic (temp file + swap) to survive a crash mid-write.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import APPDATA_DIR, DEFAULT_PRESET, SETTINGS_FILE
from .errors import SettingsError


@dataclass(slots=True)
class Settings:
    """All user-configurable, persisted application settings."""

    theme: str = "system"  # "light", "dark", "system"
    default_output_format: str = "pdf"
    default_output_directory: str = ""  # empty = "same folder as source"
    same_folder_default: bool = True
    overwrite_behavior: str = "ask"  # "ask", "replace", "new_copy"
    editor_font_size: int = 13
    editor_word_wrap: bool = True
    editor_line_numbers: bool = True
    editor_theme: str = "light"
    pdf_default_page_size: str = "A4"
    pdf_default_margin_mm: int = 20
    pdf_default_font: str = "Helvetica"
    active_preset: str = DEFAULT_PRESET
    window_width: int = 1200
    window_height: int = 800

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        settings = cls()
        for key in asdict(settings):
            if key in data:
                setattr(settings, key, data[key])
        return settings


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise SettingsError(f"Could not write settings to '{path}'.") from exc


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, or return built-in defaults if none saved / corrupted."""
    path = path if path is not None else SETTINGS_FILE
    if not path.exists():
        return Settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    return Settings.from_dict(raw)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Persist settings to disk."""
    path = path if path is not None else SETTINGS_FILE
    _atomic_write(path, json.dumps(settings.to_dict(), indent=2))


def reset_settings(path: Path | None = None) -> Settings:
    """Reset to built-in defaults and persist immediately."""
    defaults = Settings()
    save_settings(defaults, path)
    return defaults


def ensure_appdata_dir(path: Path | None = None) -> None:
    directory = path if path is not None else APPDATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
