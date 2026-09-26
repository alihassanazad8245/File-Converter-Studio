"""Conversion history, persisted as plain JSON.

Recent Files is derived from this same log (unique source paths, most
recent first) rather than tracked separately - one source of truth, no
duplicated storage or synchronisation logic.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .config import HISTORY_FILE, MAX_HISTORY_ENTRIES
from .errors import SettingsError
from .models import ConversionResult, HistoryEntry


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
        raise SettingsError(f"Could not write history to '{path}'.") from exc


def load_history(path: Path | None = None) -> list[HistoryEntry]:
    """Load the conversion history, newest last. Corrupted files yield []."""
    path = path if path is not None else HISTORY_FILE
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    return [HistoryEntry.from_dict(item) for item in raw if isinstance(item, dict)]


def append_history(result: ConversionResult, path: Path | None = None) -> HistoryEntry:
    """Append one conversion result to the history log, capped at
    MAX_HISTORY_ENTRIES (oldest entries drop off first)."""
    path = path if path is not None else HISTORY_FILE
    entries = load_history(path)
    entry = HistoryEntry.from_result(result)
    entries.append(entry)
    if len(entries) > MAX_HISTORY_ENTRIES:
        entries = entries[-MAX_HISTORY_ENTRIES:]
    _atomic_write(path, json.dumps([e.to_dict() for e in entries], indent=2))
    return entry


def remove_entry(index: int, path: Path | None = None) -> list[HistoryEntry]:
    """Remove one history entry by position (0 = oldest) and persist."""
    path = path if path is not None else HISTORY_FILE
    entries = load_history(path)
    if 0 <= index < len(entries):
        entries.pop(index)
        _atomic_write(path, json.dumps([e.to_dict() for e in entries], indent=2))
    return entries


def clear_history(path: Path | None = None) -> None:
    path = path if path is not None else HISTORY_FILE
    _atomic_write(path, json.dumps([], indent=2))


def recent_files(path: Path | None = None, limit: int = 10) -> list[dict]:
    """Unique source files, most recently converted first.

    Each row is ``{"path": ..., "last_opened": ...}``. Derived entirely
    from the history log - there is no separate "recent files" store.
    """
    entries = load_history(path)
    seen: dict[str, str] = {}
    for entry in reversed(entries):  # newest first
        if entry.source_path and entry.source_path not in seen:
            seen[entry.source_path] = entry.timestamp
        if len(seen) >= limit:
            break
    return [{"path": p, "last_opened": t} for p, t in seen.items()]
