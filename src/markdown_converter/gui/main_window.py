"""The main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QRadioButton, QSpinBox, QSplitter, QStackedWidget, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from .. import __app_name__, __author__, __instagram__, __version__
from ..config import PRESETS, SUPPORTED_OUTPUT_FORMATS, ConversionOptions
from ..engine import ConversionRequest
from ..errors import AppError
from ..history import append_history, recent_files
from ..models import ConversionResult
from ..parser import parse_markdown
from ..quality import check_quality
from ..settings import Settings, load_settings, save_settings
from ..stats import compute_stats
from ..validators import (
    build_output_filename,
    resolve_output_directory,
    validate_source_path,
)
from ..worker import run_conversion_in_background
from .batch_dialog import BatchDialog
from .document_converter_tab import DocumentConverterTab
from .dropzone import DropZone
from .editor_widget import MarkdownEditor
from .history_dialog import HistoryDialog
from .image_tools_tab import ImageToolsTab
from .pdf_tools_tab import PdfToolsTab
from .result_dialog import ResultDialog
from .settings_dialog import SettingsDialog
from .theme import preview_css_for, stylesheet_for


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings: Settings = load_settings()
        self.source_path: Path | None = None
        self._thread = None
        self._worker = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._refresh_preview_and_info)

        self.setWindowTitle(__app_name__)
        self.resize(self.settings.window_width, self.settings.window_height)

        self._build_menu()
        self._build_central_widget()
        self.setAcceptDrops(True)
        self.statusBar().showMessage(f"{__app_name__} v{__version__} ready.", 3000)

        self.apply_theme(self.settings.theme)

    # ------------------------------------------------------------------ #
    # Menu + shortcuts
    # ------------------------------------------------------------------ #

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        self._add_action(file_menu, "&Open Markdown…", "Ctrl+O", self._browse_file)
        self._add_action(file_menu, "&Save / Export", "Ctrl+S", self._on_convert_clicked)
        self._add_action(file_menu, "Save &As…", "Ctrl+Shift+S", self._browse_output_dir)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Batch Conversion…", "Ctrl+B", self._open_batch_dialog)
        file_menu.addSeparator()
        self.recent_menu = QMenu("Recent Files", self)
        file_menu.addMenu(self.recent_menu)
        self._refresh_recent_files_menu()
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", "Ctrl+Q", self.close)

        view_menu = menu_bar.addMenu("&View")
        self._add_action(view_menu, "Focus &Preview", "Ctrl+P", lambda: self.tabs.setCurrentIndex(0))
        light_action = self._add_action(view_menu, "Light Theme", None, lambda: self.apply_theme("light"))
        dark_action = self._add_action(view_menu, "Dark Theme", None, lambda: self.apply_theme("dark"))

        settings_menu = menu_bar.addMenu("&Settings")
        self._add_action(settings_menu, "&Preferences…", "Ctrl+,", self._open_settings_dialog)
        self._add_action(settings_menu, "Conversion &History", "Ctrl+Shift+H", self._open_history_dialog)

        help_menu = menu_bar.addMenu("&Help")
        self._add_action(help_menu, "About", None, self._show_about)

    def _add_action(self, menu: QMenu, text: str, shortcut: str | None, slot) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _refresh_recent_files_menu(self) -> None:
        self.recent_menu.clear()
        entries = recent_files(limit=8)
        if not entries:
            empty = QAction("(no recent files)", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for entry in entries:
            path = entry["path"]
            action = QAction(Path(path).name, self)
            action.setToolTip(path)
            action.triggered.connect(lambda _=False, p=path: self._load_file(p))
            self.recent_menu.addAction(action)

    # ------------------------------------------------------------------ #
    # Central layout
    # ------------------------------------------------------------------ #

    def _build_central_widget(self) -> None:
        self.main_tabs = QTabWidget()
        self.setCentralWidget(self.main_tabs)

        self.stack = QStackedWidget()
        self.dropzone = DropZone()
        self.dropzone.browse_clicked.connect(self._browse_file)
        self.dropzone.file_dropped.connect(self._load_file)
        self.stack.addWidget(self.dropzone)
        self.stack.addWidget(self._build_editor_page())

        self.main_tabs.addTab(self.stack, "Markdown Editor")
        self.main_tabs.addTab(DocumentConverterTab(), "Document Converter")
        self.main_tabs.addTab(PdfToolsTab(), "PDF Tools")
        self.main_tabs.addTab(ImageToolsTab(), "Image Converter")

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self._build_file_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor = MarkdownEditor()
        self.editor.set_editor_font_size(self.settings.editor_font_size)
        self.editor.set_word_wrap_enabled(self.settings.editor_word_wrap)
        self.editor.set_line_numbers_enabled(self.settings.editor_line_numbers)
        self.editor.textChanged.connect(self._debounce.start)
        splitter.addWidget(self.editor)

        self.tabs = QTabWidget()
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.tabs.addTab(self.preview, "Live Preview")
        self.info_panel = self._build_info_panel()
        self.tabs.addTab(self.info_panel, "Document Info")
        splitter.addWidget(self.tabs)
        splitter.setSizes([600, 600])
        layout.addWidget(splitter, stretch=1)

        layout.addWidget(self._build_output_panel())
        return page

    def _build_file_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("card")
        layout = QHBoxLayout(bar)

        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setObjectName("muted")
        layout.addWidget(self.file_info_label, stretch=1)

        change_btn = QPushButton("Change File…")
        change_btn.setObjectName("secondary")
        change_btn.clicked.connect(self._browse_file)
        layout.addWidget(change_btn)
        return bar

    def _build_info_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.stats_label = QLabel("Load a document to see statistics.")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        layout.addWidget(QLabel("<b>Document Check</b>"))
        self.quality_label = QLabel("—")
        self.quality_label.setWordWrap(True)
        layout.addWidget(self.quality_label)
        layout.addStretch(1)
        return widget

    def _build_output_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)

        location_row = QHBoxLayout()
        self.same_folder_radio = QRadioButton("Same folder as source")
        self.choose_folder_radio = QRadioButton("Choose another folder")
        self.same_folder_radio.setChecked(self.settings.same_folder_default)
        self.choose_folder_radio.setChecked(not self.settings.same_folder_default)
        group = QButtonGroup(self)
        group.addButton(self.same_folder_radio)
        group.addButton(self.choose_folder_radio)
        location_row.addWidget(self.same_folder_radio)
        location_row.addWidget(self.choose_folder_radio)
        self.output_dir_edit = QLineEdit(self.settings.default_output_directory)
        self.output_dir_edit.setPlaceholderText("Output folder path…")
        browse_dir_btn = QPushButton("Browse…")
        browse_dir_btn.setObjectName("secondary")
        browse_dir_btn.clicked.connect(self._browse_output_dir)
        location_row.addWidget(self.output_dir_edit, stretch=1)
        location_row.addWidget(browse_dir_btn)
        layout.addLayout(location_row)
        self.same_folder_radio.toggled.connect(self._sync_output_dir_enabled)
        self._sync_output_dir_enabled()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Output filename:"))
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("(same as source file name)")
        name_row.addWidget(self.filename_edit, stretch=1)
        layout.addLayout(name_row)

        formats_row = QHBoxLayout()
        formats_row.addWidget(QLabel("Convert to:"))
        self.format_checks: dict[str, QCheckBox] = {}
        for fmt in SUPPORTED_OUTPUT_FORMATS:
            check = QCheckBox(fmt.upper())
            if fmt == self.settings.default_output_format:
                check.setChecked(True)
            formats_row.addWidget(check)
            self.format_checks[fmt] = check
        formats_row.addStretch(1)
        layout.addLayout(formats_row)

        actions_row = QHBoxLayout()
        preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()))
        self.preset_combo.setCurrentText(self.settings.active_preset)
        actions_row.addWidget(preset_label)
        actions_row.addWidget(self.preset_combo)

        advanced_btn = QPushButton("Advanced Settings")
        advanced_btn.setObjectName("secondary")
        advanced_btn.clicked.connect(self._open_advanced_dialog)
        actions_row.addWidget(advanced_btn)

        batch_btn = QPushButton("Batch Conversion…")
        batch_btn.setObjectName("secondary")
        batch_btn.clicked.connect(self._open_batch_dialog)
        actions_row.addWidget(batch_btn)

        actions_row.addStretch(1)
        self.convert_btn = QPushButton("Convert  (Ctrl+Enter)")
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        actions_row.addWidget(self.convert_btn)
        convert_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        convert_shortcut.activated.connect(self._on_convert_clicked)
        layout.addLayout(actions_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        return panel

    def _sync_output_dir_enabled(self) -> None:
        enabled = self.choose_folder_radio.isChecked()
        self.output_dir_edit.setEnabled(enabled)

    # ------------------------------------------------------------------ #
    # File loading
    # ------------------------------------------------------------------ #

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Markdown File", "", "Markdown files (*.md *.markdown *.txt)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, raw_path: str) -> None:
        try:
            path = validate_source_path(raw_path)
        except AppError as exc:
            QMessageBox.warning(self, "Could Not Open File", exc.message)
            return

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            QMessageBox.warning(self, "Could Not Read File", str(exc))
            return

        self.source_path = path
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)

        size_kb = path.stat().st_size / 1024
        self.file_info_label.setText(f"{path.name}  •  {size_kb:.1f} KB  •  {path.parent}")
        self.filename_edit.setPlaceholderText(path.stem)

        self.stack.setCurrentIndex(1)
        self._refresh_preview_and_info()
        self.statusBar().showMessage(f"Loaded {path.name}", 3000)

    # ------------------------------------------------------------------ #
    # Preview + document info
    # ------------------------------------------------------------------ #

    def _refresh_preview_and_info(self) -> None:
        if self.source_path is None:
            return
        text = self.editor.toPlainText()
        doc = parse_markdown(text, self.source_path.parent)

        theme = self._effective_theme()
        css = preview_css_for(theme)
        self.preview.setHtml(f"<style>{css}</style>{doc.html_body}")

        stats = compute_stats(doc)
        heading_line = ", ".join(f"{k.upper()}: {v}" for k, v in stats.heading_breakdown.items()) or "none"
        self.stats_label.setText(
            f"<b>Words:</b> {stats.word_count:,}  &nbsp; "
            f"<b>Characters:</b> {stats.character_count:,}  &nbsp; "
            f"<b>Reading time:</b> {stats.reading_time_minutes} min<br>"
            f"<b>Headings:</b> {stats.heading_count} ({heading_line})<br>"
            f"<b>Images:</b> {stats.image_count} &nbsp; "
            f"<b>Links:</b> {stats.link_count} &nbsp; "
            f"<b>Code blocks:</b> {stats.code_block_count} &nbsp; "
            f"<b>Tables:</b> {stats.table_count}"
        )

        report = check_quality(doc)
        if report.is_clean:
            self.quality_label.setText("✓ No issues found.")
        else:
            lines = [f"⚠ {issue.message}" + (f" — {issue.detail}" if issue.detail else "")
                    for issue in report.issues]
            self.quality_label.setText("<br>".join(lines))

    # ------------------------------------------------------------------ #
    # Output location
    # ------------------------------------------------------------------ #

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if directory:
            self.output_dir_edit.setText(directory)
            self.choose_folder_radio.setChecked(True)

    def _selected_formats(self) -> list[str]:
        return [fmt for fmt, check in self.format_checks.items() if check.isChecked()]

    def _current_options(self) -> ConversionOptions:
        return PRESETS.get(self.preset_combo.currentText(), ConversionOptions())

    # ------------------------------------------------------------------ #
    # Advanced (per-job) options dialog
    # ------------------------------------------------------------------ #

    def _open_advanced_dialog(self) -> None:
        options = self._current_options()
        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced Conversion Settings")
        layout = QVBoxLayout(dialog)

        pdf_group = QGroupBox("PDF")
        pdf_form = QFormLayout(pdf_group)
        page_size = QComboBox()
        page_size.addItems(["A4", "Letter", "Legal"])
        page_size.setCurrentText(options.pdf.page_size)
        pdf_form.addRow("Page size", page_size)
        orientation = QComboBox()
        orientation.addItems(["portrait", "landscape"])
        orientation.setCurrentText(options.pdf.orientation)
        pdf_form.addRow("Orientation", orientation)
        margin = QSpinBox()
        margin.setRange(5, 50)
        margin.setSuffix(" mm")
        margin.setValue(options.pdf.margin_mm)
        pdf_form.addRow("Margin", margin)
        font_size = QSpinBox()
        font_size.setRange(8, 20)
        font_size.setValue(options.pdf.font_size)
        pdf_form.addRow("Font size", font_size)
        title_page = QCheckBox("Include title page")
        title_page.setChecked(options.pdf.include_title_page)
        pdf_form.addRow(title_page)
        toc_check = QCheckBox("Include table of contents")
        toc_check.setChecked(options.pdf.include_toc)
        pdf_form.addRow(toc_check)
        layout.addWidget(pdf_group)

        html_group = QGroupBox("HTML")
        html_form = QFormLayout(html_group)
        html_theme = QComboBox()
        html_theme.addItems(["light", "dark"])
        html_theme.setCurrentText(options.html.theme)
        html_form.addRow("Theme", html_theme)
        layout.addWidget(html_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            options.pdf.page_size = page_size.currentText()
            options.pdf.orientation = orientation.currentText()
            options.pdf.margin_mm = margin.value()
            options.pdf.font_size = font_size.value()
            options.pdf.include_title_page = title_page.isChecked()
            options.pdf.include_toc = toc_check.isChecked()
            options.html.theme = html_theme.currentText()
            self._job_options_override = options

    # ------------------------------------------------------------------ #
    # Convert
    # ------------------------------------------------------------------ #

    def _on_convert_clicked(self) -> None:
        if self.source_path is None:
            QMessageBox.information(self, "No File Loaded", "Open a Markdown file first.")
            return
        formats = self._selected_formats()
        if not formats:
            QMessageBox.information(self, "No Format Selected", "Choose at least one output format.")
            return

        same_folder = self.same_folder_radio.isChecked()
        custom_dir = self.output_dir_edit.text()
        custom_name = self.filename_edit.text()
        options = getattr(self, "_job_options_override", None) or self._current_options()

        try:
            output_dir = resolve_output_directory(self.source_path, same_folder, custom_dir)
        except AppError as exc:
            QMessageBox.warning(self, "Invalid Output Folder", exc.message)
            return

        existing = [
            output_dir / build_output_filename(self.source_path, fmt, custom_name)
            for fmt in formats
        ]
        existing = [p for p in existing if p.exists()]

        collision_strategy = self.settings.overwrite_behavior
        if existing and collision_strategy == "ask":
            names = "\n".join(p.name for p in existing)
            box = QMessageBox(self)
            box.setWindowTitle("File Already Exists")
            box.setText(f"These file(s) already exist:\n\n{names}\n\nWhat would you like to do?")
            replace_btn = box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
            copy_btn = box.addButton("Save as New Copy", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked is replace_btn:
                collision_strategy = "replace"
            elif clicked is copy_btn:
                collision_strategy = "new_copy"
            else:
                return
        elif collision_strategy == "ask":
            collision_strategy = "replace"

        request = ConversionRequest(
            source_path=self.source_path, formats=formats, same_folder=same_folder,
            custom_output_dir=custom_dir, custom_filename=custom_name, options=options,
        )

        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate for a single-file job
        self.statusBar().showMessage(f"Converting to {', '.join(f.upper() for f in formats)}…")

        self._thread, self._worker = run_conversion_in_background(
            [request], collision_strategy,
            on_progress=lambda i, t, p: None,
            on_finished=self._on_convert_finished,
            on_failed=self._on_convert_failed,
        )

    def _on_convert_finished(self, results: list[ConversionResult]) -> None:
        self.convert_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        for result in results:
            append_history(result)
        succeeded = sum(1 for r in results if r.success)
        if succeeded == len(results):
            self.statusBar().showMessage(f"✓ {succeeded} file(s) created successfully.", 5000)
        else:
            self.statusBar().showMessage(f"⚠ {succeeded}/{len(results)} conversions succeeded.", 5000)
        self._refresh_recent_files_menu()
        ResultDialog(results, parent=self).exec()

    def _on_convert_failed(self, message: str) -> None:
        self.convert_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Conversion Failed", message)

    # ------------------------------------------------------------------ #
    # Dialogs
    # ------------------------------------------------------------------ #

    def _open_batch_dialog(self) -> None:
        dialog = BatchDialog(self._current_options(), self.settings.overwrite_behavior, parent=self)
        dialog.exec()
        self._refresh_recent_files_menu()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_settings:
            self.settings = dialog.result_settings
            self.apply_theme(self.settings.theme)
            self.editor.set_editor_font_size(self.settings.editor_font_size)
            self.editor.set_word_wrap_enabled(self.settings.editor_word_wrap)
            self.editor.set_line_numbers_enabled(self.settings.editor_line_numbers)
            self.statusBar().showMessage("Settings saved.", 3000)

    def _open_history_dialog(self) -> None:
        HistoryDialog(parent=self).exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, f"About {__app_name__}",
            f"<h3>{__app_name__}</h3>"
            f"<p>Version {__version__}</p>"
            f"<p>Convert Markdown, Word, HTML, and text documents into PDF, DOCX, HTML, TXT, "
            f"and structured JSON — plus PDF tools (merge, split, compress, PDF ↔ images/Word) "
            f"and image format conversion. Everything runs entirely offline.</p>"
            f"<p>Built by {__author__} — Instagram: @{__instagram__}</p>",
        )

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #

    def _effective_theme(self) -> str:
        if self.settings.theme == "system":
            return "light"  # a safe, always-readable default when the OS theme is unknown
        return self.settings.theme

    def apply_theme(self, theme: str) -> None:
        self.settings.theme = theme
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet_for(self._effective_theme()))
        if self.source_path is not None:
            self._refresh_preview_and_info()

    # ------------------------------------------------------------------ #
    # Drag & drop on the whole window (once a document is already loaded)
    # ------------------------------------------------------------------ #

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._load_file(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        self.settings.window_width = self.width()
        self.settings.window_height = self.height()
        self.settings.active_preset = self.preset_combo.currentText()
        save_settings(self.settings)
        super().closeEvent(event)
