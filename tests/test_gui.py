"""GUI construction tests, run headlessly via the offscreen Qt platform
(set automatically by conftest.py).

These verify the window and every dialog build without crashing and that
loading a file correctly updates the editor, preview, and stats panels.
They do not call ``.exec()`` on any modal dialog, since that would block
waiting for user interaction.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def main_window(qapp, tmp_path, monkeypatch):
    from markdown_converter import history as history_module
    from markdown_converter import settings as settings_module

    monkeypatch.setattr(settings_module, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(history_module, "HISTORY_FILE", tmp_path / "history.json")

    from markdown_converter.gui.main_window import MainWindow
    window = MainWindow()
    yield window
    window.close()


def test_main_window_constructs_with_empty_state(main_window) -> None:
    assert main_window.stack.currentIndex() == 0  # dropzone shown first
    assert main_window.source_path is None


def test_loading_a_file_switches_to_editor_view(main_window, tmp_path: Path) -> None:
    src = tmp_path / "demo.md"
    src.write_text("# Demo\n\nHello world.\n", encoding="utf-8")
    main_window._load_file(str(src))

    assert main_window.stack.currentIndex() == 1
    assert main_window.source_path == src
    assert "Hello world" in main_window.editor.toPlainText()
    assert "Demo" in main_window.preview.toPlainText()


def test_loading_invalid_file_shows_warning_not_crash(main_window, tmp_path: Path, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    main_window._load_file(str(tmp_path / "nonexistent.md"))
    assert main_window.source_path is None
    assert main_window.stack.currentIndex() == 0


def test_stats_and_quality_update_on_load(main_window, tmp_path: Path) -> None:
    src = tmp_path / "demo.md"
    src.write_text("# Title\n\n![missing](nope.png)\n", encoding="utf-8")
    main_window._load_file(str(src))
    assert "Words" in main_window.stats_label.text()
    assert "Image not found" in main_window.quality_label.text() or "nope.png" in main_window.quality_label.text()


def test_selected_formats_reflects_checked_boxes(main_window) -> None:
    for fmt, check in main_window.format_checks.items():
        check.setChecked(fmt in ("pdf", "html"))
    assert set(main_window._selected_formats()) == {"pdf", "html"}


def test_same_folder_radio_disables_output_dir_field(main_window) -> None:
    main_window.same_folder_radio.setChecked(True)
    assert not main_window.output_dir_edit.isEnabled()
    main_window.choose_folder_radio.setChecked(True)
    assert main_window.output_dir_edit.isEnabled()


def test_apply_theme_updates_settings(main_window) -> None:
    main_window.apply_theme("dark")
    assert main_window.settings.theme == "dark"
    main_window.apply_theme("light")
    assert main_window.settings.theme == "light"


# --------------------------------------------------------------------------- #
# Dialogs construct without crashing
# --------------------------------------------------------------------------- #


def test_settings_dialog_constructs(qapp) -> None:
    from markdown_converter.gui.settings_dialog import SettingsDialog
    from markdown_converter.settings import Settings

    dialog = SettingsDialog(Settings())
    assert dialog.theme_combo.currentText() == "system"


def test_history_dialog_constructs_empty(qapp, tmp_path, monkeypatch) -> None:
    from markdown_converter import history as history_module
    monkeypatch.setattr(history_module, "HISTORY_FILE", tmp_path / "history.json")

    from markdown_converter.gui.history_dialog import HistoryDialog
    dialog = HistoryDialog()
    assert dialog._entries == []


def test_batch_dialog_constructs(qapp) -> None:
    from markdown_converter.config import ConversionOptions
    from markdown_converter.gui.batch_dialog import BatchDialog

    dialog = BatchDialog(ConversionOptions(), "ask")
    assert dialog.file_list.count() == 0
    assert dialog._selected_formats() == ["pdf", "docx", "html"]


def test_result_dialog_constructs_with_success(qapp) -> None:
    from markdown_converter.gui.result_dialog import ResultDialog
    from markdown_converter.models import ConversionResult

    results = [ConversionResult(source_path="a.md", output_path="/tmp/a.pdf",
                                format="pdf", success=True, message="ok")]
    dialog = ResultDialog(results)
    assert dialog is not None


def test_result_dialog_constructs_with_failure(qapp) -> None:
    from markdown_converter.gui.result_dialog import ResultDialog
    from markdown_converter.models import ConversionResult

    results = [ConversionResult(source_path="a.md", output_path="", format="pdf",
                                success=False, message="failed")]
    dialog = ResultDialog(results)
    assert dialog is not None


def test_main_window_has_all_four_tabs(main_window) -> None:
    titles = [main_window.main_tabs.tabText(i) for i in range(main_window.main_tabs.count())]
    assert titles == ["Markdown Editor", "Document Converter", "PDF Tools", "Image Converter"]


def test_pdf_tools_tab_constructs(qapp) -> None:
    from markdown_converter.gui.pdf_tools_tab import PdfToolsTab

    tab = PdfToolsTab()
    assert tab.tool_combo.count() == 5
    assert tab.stack.count() == 5


def test_pdf_tools_tab_merge_requires_two_files(qapp) -> None:
    from markdown_converter.gui.pdf_tools_tab import PdfToolsTab

    tab = PdfToolsTab()
    tab._do_merge()  # no files added
    assert "at least two" in tab.status_label.text()


def test_image_tools_tab_constructs(qapp) -> None:
    from markdown_converter.gui.image_tools_tab import ImageToolsTab

    tab = ImageToolsTab()
    assert tab.format_combo.count() > 0
    assert tab.file_list.count() == 0


def test_image_tools_tab_convert_requires_files(qapp) -> None:
    from markdown_converter.gui.image_tools_tab import ImageToolsTab

    tab = ImageToolsTab()
    tab._do_convert()
    assert "at least one image" in tab.status_label.text()


def test_document_converter_tab_constructs(qapp) -> None:
    from markdown_converter.gui.document_converter_tab import DocumentConverterTab

    tab = DocumentConverterTab()
    assert tab.format_checks["pdf"].isChecked()
    assert not tab.format_checks["docx"].isChecked()


def test_document_converter_tab_requires_file(qapp) -> None:
    from markdown_converter.gui.document_converter_tab import DocumentConverterTab

    tab = DocumentConverterTab()
    tab._on_convert()
    assert "Choose a file" in tab.status_label.text()
