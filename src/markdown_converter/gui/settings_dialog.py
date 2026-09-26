"""Settings dialog: appearance, conversion, editor, PDF, advanced."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

from .. import settings as settings_module
from ..settings import Settings


class SettingsDialog(QDialog):
    """Edits a copy of :class:`Settings`; only persisted on Save."""

    def __init__(self, current: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(480, 420)
        self.result_settings: Settings | None = None

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._appearance_tab(current), "Appearance")
        tabs.addTab(self._conversion_tab(current), "Conversion")
        tabs.addTab(self._editor_tab(current), "Editor")
        tabs.addTab(self._pdf_tab(current), "PDF")
        tabs.addTab(self._advanced_tab(current), "Advanced")

        buttons = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._reset)
        buttons.addWidget(reset_btn)
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def _appearance_tab(self, current: Settings) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(current.theme)
        form.addRow("Theme", self.theme_combo)
        return widget

    def _conversion_tab(self, current: Settings) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.default_format_combo = QComboBox()
        self.default_format_combo.addItems(["pdf", "docx", "html", "txt", "md", "json"])
        self.default_format_combo.setCurrentText(current.default_output_format)
        form.addRow("Default format", self.default_format_combo)

        self.same_folder_check = QCheckBox("Save to same folder as source by default")
        self.same_folder_check.setChecked(current.same_folder_default)
        form.addRow(self.same_folder_check)

        dir_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit(current.default_output_directory)
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(self.output_dir_edit)
        dir_row.addWidget(browse_btn)
        form.addRow("Default output folder", dir_row)

        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItems(["ask", "replace", "new_copy"])
        self.overwrite_combo.setCurrentText(current.overwrite_behavior)
        form.addRow("If file exists", self.overwrite_combo)
        return widget

    def _editor_tab(self, current: Settings) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setValue(current.editor_font_size)
        form.addRow("Font size", self.font_size_spin)

        self.word_wrap_check = QCheckBox("Word wrap")
        self.word_wrap_check.setChecked(current.editor_word_wrap)
        form.addRow(self.word_wrap_check)

        self.line_numbers_check = QCheckBox("Line numbers")
        self.line_numbers_check.setChecked(current.editor_line_numbers)
        form.addRow(self.line_numbers_check)
        return widget

    def _pdf_tab(self, current: Settings) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.pdf_page_size_combo = QComboBox()
        self.pdf_page_size_combo.addItems(["A4", "Letter", "Legal"])
        self.pdf_page_size_combo.setCurrentText(current.pdf_default_page_size)
        form.addRow("Default page size", self.pdf_page_size_combo)

        self.pdf_margin_spin = QSpinBox()
        self.pdf_margin_spin.setRange(5, 50)
        self.pdf_margin_spin.setSuffix(" mm")
        self.pdf_margin_spin.setValue(current.pdf_default_margin_mm)
        form.addRow("Default margin", self.pdf_margin_spin)

        self.pdf_font_edit = QLineEdit(current.pdf_default_font)
        form.addRow("Default font", self.pdf_font_edit)
        return widget

    def _advanced_tab(self, current: Settings) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            "Settings and history are stored as plain JSON files next to the "
            "application (.appdata/). Nothing is sent anywhere - all conversion "
            "happens locally on this machine."
        ))
        layout.addStretch(1)
        return widget

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose default output folder")
        if directory:
            self.output_dir_edit.setText(directory)

    def _reset(self) -> None:
        confirm = QMessageBox.question(self, "Reset Settings", "Reset all settings to defaults?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.result_settings = settings_module.reset_settings()
            self.accept()

    def _save(self) -> None:
        new_settings = Settings(
            theme=self.theme_combo.currentText(),
            default_output_format=self.default_format_combo.currentText(),
            default_output_directory=self.output_dir_edit.text(),
            same_folder_default=self.same_folder_check.isChecked(),
            overwrite_behavior=self.overwrite_combo.currentText(),
            editor_font_size=self.font_size_spin.value(),
            editor_word_wrap=self.word_wrap_check.isChecked(),
            editor_line_numbers=self.line_numbers_check.isChecked(),
            pdf_default_page_size=self.pdf_page_size_combo.currentText(),
            pdf_default_margin_mm=self.pdf_margin_spin.value(),
            pdf_default_font=self.pdf_font_edit.text(),
        )
        settings_module.save_settings(new_settings)
        self.result_settings = new_settings
        self.accept()
