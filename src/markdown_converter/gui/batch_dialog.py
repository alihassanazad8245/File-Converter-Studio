"""Batch conversion dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout,
)

from ..config import ConversionOptions, SUPPORTED_OUTPUT_FORMATS
from ..engine import ConversionRequest
from ..history import append_history
from ..models import ConversionResult
from ..worker import run_conversion_in_background
from .result_dialog import ResultDialog


class BatchDialog(QDialog):
    """Select multiple Markdown files and convert them all to the chosen formats."""

    def __init__(self, options: ConversionOptions, overwrite_behavior: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Conversion")
        self.resize(560, 480)
        self._options = options
        self._overwrite = "replace" if overwrite_behavior == "ask" else overwrite_behavior
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Markdown files to convert:"))
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        file_buttons = QHBoxLayout()
        add_btn = QPushButton("Add Files…")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("secondary")
        remove_btn.clicked.connect(self._remove_selected)
        file_buttons.addWidget(add_btn)
        file_buttons.addWidget(remove_btn)
        file_buttons.addStretch(1)
        layout.addLayout(file_buttons)

        layout.addWidget(QLabel("Convert to:"))
        formats_row = QHBoxLayout()
        self.format_checks: dict[str, QCheckBox] = {}
        for fmt in SUPPORTED_OUTPUT_FORMATS:
            check = QCheckBox(fmt.upper())
            if fmt in ("pdf", "docx", "html"):
                check.setChecked(True)
            formats_row.addWidget(check)
            self.format_checks[fmt] = check
        layout.addLayout(formats_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel_btn = QPushButton("Close")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        self.convert_btn = QPushButton("Convert All")
        self.convert_btn.clicked.connect(self._start_conversion)
        actions.addWidget(cancel_btn)
        actions.addWidget(self.convert_btn)
        layout.addLayout(actions)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Markdown files", "", "Markdown files (*.md *.markdown *.txt)",
        )
        for path in paths:
            existing = [self.file_list.item(i).data(1) for i in range(self.file_list.count())]
            if path in existing:
                continue
            item = QListWidgetItem(Path(path).name)
            item.setData(1, path)
            item.setToolTip(path)
            self.file_list.addItem(item)

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def _selected_formats(self) -> list[str]:
        return [fmt for fmt, check in self.format_checks.items() if check.isChecked()]

    def _start_conversion(self) -> None:
        file_count = self.file_list.count()
        formats = self._selected_formats()
        if file_count == 0:
            self.status_label.setText("Add at least one Markdown file first.")
            self.status_label.setObjectName("warning")
            return
        if not formats:
            self.status_label.setText("Choose at least one output format.")
            self.status_label.setObjectName("warning")
            return

        requests = [
            ConversionRequest(
                source_path=Path(self.file_list.item(i).data(1)), formats=formats,
                same_folder=True, options=self._options,
            )
            for i in range(file_count)
        ]

        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, file_count)
        self.status_label.setObjectName("muted")

        self._thread, self._worker = run_conversion_in_background(
            requests, self._overwrite,
            on_progress=self._on_progress, on_finished=self._on_finished, on_failed=self._on_failed,
        )

    def _on_progress(self, index: int, total: int, current_path: str) -> None:
        self.progress_bar.setValue(index)
        self.status_label.setText(f"Converting {Path(current_path).name} ({index + 1}/{total})…")

    def _on_finished(self, results: list[ConversionResult]) -> None:
        self.progress_bar.setValue(self.progress_bar.maximum())
        for result in results:
            append_history(result)
        self.convert_btn.setEnabled(True)
        succeeded = sum(1 for r in results if r.success)
        self.status_label.setText(f"Done: {succeeded}/{len(results)} conversions succeeded.")
        ResultDialog(results, parent=self).exec()

    def _on_failed(self, message: str) -> None:
        self.convert_btn.setEnabled(True)
        self.status_label.setText(f"Batch conversion failed: {message}")
        self.status_label.setObjectName("error")
