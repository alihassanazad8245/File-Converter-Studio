"""Document Converter tab.

A simpler, file-based sibling to the Markdown Editor tab: pick a document
(.docx, .html, .txt, or .md), choose output formats, convert. No live
editing - for that, use the Markdown Editor tab.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from .. import __app_name__
from ..config import DOCUMENT_INPUT_EXTENSIONS, SUPPORTED_OUTPUT_FORMATS, ConversionOptions
from ..engine import ConversionRequest
from ..errors import AppError
from ..history import append_history
from ..models import ConversionResult
from ..validators import validate_source_path
from ..worker import run_conversion_in_background
from .result_dialog import ResultDialog

_FILTER = "Documents (*.docx *.html *.htm *.txt *.md *.markdown)"


class DocumentConverterTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Convert Word documents, HTML pages, plain text, or Markdown into "
            "any of the formats below."
        ))

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select a .docx, .html, .txt, or .md file…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.file_edit, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        location_row = QHBoxLayout()
        self.same_folder_radio = QRadioButton("Same folder as source")
        self.choose_folder_radio = QRadioButton("Choose another folder")
        self.same_folder_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.same_folder_radio)
        group.addButton(self.choose_folder_radio)
        location_row.addWidget(self.same_folder_radio)
        location_row.addWidget(self.choose_folder_radio)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setEnabled(False)
        browse_dir_btn = QPushButton("Browse…")
        browse_dir_btn.setObjectName("secondary")
        browse_dir_btn.clicked.connect(self._browse_output_dir)
        location_row.addWidget(self.output_dir_edit, stretch=1)
        location_row.addWidget(browse_dir_btn)
        layout.addLayout(location_row)
        self.choose_folder_radio.toggled.connect(self.output_dir_edit.setEnabled)

        formats_row = QHBoxLayout()
        formats_row.addWidget(QLabel("Convert to:"))
        self.format_checks: dict[str, QCheckBox] = {}
        for fmt in SUPPORTED_OUTPUT_FORMATS:
            check = QCheckBox(fmt.upper())
            if fmt == "pdf":
                check.setChecked(True)
            formats_row.addWidget(check)
            self.format_checks[fmt] = check
        formats_row.addStretch(1)
        layout.addLayout(formats_row)

        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(self._on_convert)
        layout.addWidget(convert_btn)
        self.convert_btn = convert_btn

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Select a document - {__app_name__}", "", _FILTER)
        if path:
            self.file_edit.setText(path)

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if directory:
            self.output_dir_edit.setText(directory)
            self.choose_folder_radio.setChecked(True)

    def _on_convert(self) -> None:
        formats = [fmt for fmt, check in self.format_checks.items() if check.isChecked()]
        if not self.file_edit.text().strip():
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose a file first.")
            return
        if not formats:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose at least one output format.")
            return

        try:
            source = validate_source_path(self.file_edit.text(), DOCUMENT_INPUT_EXTENSIONS)
        except AppError as exc:
            self.status_label.setObjectName("error")
            self.status_label.setText(exc.message)
            return

        request = ConversionRequest(
            source_path=source, formats=formats, same_folder=self.same_folder_radio.isChecked(),
            custom_output_dir=self.output_dir_edit.text(), options=ConversionOptions(),
            allowed_extensions=DOCUMENT_INPUT_EXTENSIONS,
        )

        self.convert_btn.setEnabled(False)
        self.status_label.setObjectName("muted")
        self.status_label.setText("Converting…")

        self._thread, self._worker = run_conversion_in_background(
            [request], "replace",
            on_progress=lambda i, t, p: None,
            on_finished=self._on_finished,
            on_failed=self._on_failed,
        )

    def _on_finished(self, results: list[ConversionResult]) -> None:
        self.convert_btn.setEnabled(True)
        for result in results:
            append_history(result)
        succeeded = sum(1 for r in results if r.success)
        self.status_label.setObjectName("success" if succeeded == len(results) else "warning")
        self.status_label.setText(f"{succeeded}/{len(results)} conversion(s) succeeded.")
        ResultDialog(results, parent=self).exec()

    def _on_failed(self, message: str) -> None:
        self.convert_btn.setEnabled(True)
        self.status_label.setObjectName("error")
        self.status_label.setText(f"Failed: {message}")
