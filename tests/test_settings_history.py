"""Tests for settings and history persistence."""

from __future__ import annotations

from pathlib import Path

from markdown_converter.history import (
    append_history,
    clear_history,
    load_history,
    recent_files,
    remove_entry,
)
from markdown_converter.models import ConversionResult
from markdown_converter.settings import Settings, load_settings, save_settings

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def test_load_settings_missing_file_returns_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "nope.json")
    assert settings.theme == "system"
    assert settings.default_output_format == "pdf"


def test_load_settings_corrupted_file_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not valid json")
    settings = load_settings(path)
    assert settings.theme == "system"


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = Settings(theme="dark", editor_font_size=16, pdf_default_page_size="Letter")
    save_settings(original, path)
    loaded = load_settings(path)
    assert loaded.theme == "dark"
    assert loaded.editor_font_size == 16
    assert loaded.pdf_default_page_size == "Letter"


def test_settings_from_dict_ignores_unknown_keys() -> None:
    settings = Settings.from_dict({"theme": "dark", "totally_unknown_key": 123})
    assert settings.theme == "dark"


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #


def _result(source="a.md", output="a.pdf", fmt="pdf", success=True) -> ConversionResult:
    return ConversionResult(source_path=source, output_path=output, format=fmt, success=success)


def test_load_history_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_history(tmp_path / "nope.json") == []


def test_append_and_load_history_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_history(_result("a.md", "a.pdf"), path)
    append_history(_result("b.md", "b.html", fmt="html"), path)
    entries = load_history(path)
    assert len(entries) == 2
    assert entries[0].source_path == "a.md"
    assert entries[1].format == "html"


def test_append_history_records_failed_status(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_history(_result(success=False), path)
    entries = load_history(path)
    assert entries[0].status == "failed"


def test_remove_entry_by_index(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_history(_result("a.md", "a.pdf"), path)
    append_history(_result("b.md", "b.pdf"), path)
    remaining = remove_entry(0, path)
    assert len(remaining) == 1
    assert remaining[0].source_path == "b.md"


def test_clear_history(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_history(_result(), path)
    clear_history(path)
    assert load_history(path) == []


def test_recent_files_deduplicates_and_orders_newest_first(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    append_history(_result("a.md", "a.pdf"), path)
    append_history(_result("b.md", "b.pdf"), path)
    append_history(_result("a.md", "a.html", fmt="html"), path)  # a.md converted again
    recents = recent_files(path)
    paths = [r["path"] for r in recents]
    assert paths[0] == "a.md"  # most recent
    assert paths.count("a.md") == 1  # deduplicated


def test_recent_files_respects_limit(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    for i in range(5):
        append_history(_result(f"file{i}.md", f"file{i}.pdf"), path)
    recents = recent_files(path, limit=3)
    assert len(recents) == 3
