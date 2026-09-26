"""Conversion result dialog: shows what was created and lets the user open it."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..models import ConversionResult


class ResultDialog(QDialog):
    """Shown once after Convert finishes: one row per requested format."""

    def __init__(self, results: list[ConversionResult], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Conversion Result")
        self.setMinimumWidth(480)
        self._results = results

        layout = QVBoxLayout(self)

        succeeded = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        if succeeded and not failed:
            headline = QLabel(f"✓ {len(succeeded)} file(s) created" if len(succeeded) > 1
                              else "✓ Conversion Complete")
            headline.setObjectName("success")
        elif succeeded and failed:
            headline = QLabel(f"⚠ {len(succeeded)} succeeded, {len(failed)} failed")
            headline.setObjectName("warning")
        else:
            headline = QLabel("✕ Conversion Failed")
            headline.setObjectName("error")
        headline.setStyleSheet("font-size: 16px;")
        layout.addWidget(headline)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        rows_widget = QWidget()
        rows_layout = QVBoxLayout(rows_widget)

        for result in results:
            rows_layout.addWidget(self._build_row(result))
        rows_layout.addStretch(1)
        scroll.setWidget(rows_widget)
        layout.addWidget(scroll)

        for result in results:
            if result.warnings:
                for w in result.warnings:
                    warn_label = QLabel(f"⚠ {w}")
                    warn_label.setObjectName("warning")
                    layout.addWidget(warn_label)

        button_row = QHBoxLayout()
        convert_another = QPushButton("Convert Another")
        convert_another.setObjectName("secondary")
        convert_another.clicked.connect(self.accept)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(convert_another)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def _build_row(self, result: ConversionResult) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)

        icon = "✓" if result.success else "✕"
        label = QLabel(f"{icon}  {Path(result.output_path).name or '(no output)'}  "
                      f"[{result.format.upper()}]")
        label.setObjectName("success" if result.success else "error")
        row_layout.addWidget(label)
        row_layout.addStretch(1)

        if result.success and Path(result.output_path).exists():
            open_file = QPushButton("Open File")
            open_file.setObjectName("secondary")
            open_file.clicked.connect(lambda _=False, p=result.output_path: self._open_file(p))
            open_folder = QPushButton("Open Folder")
            open_folder.setObjectName("secondary")
            open_folder.clicked.connect(lambda _=False, p=result.output_path: self._open_folder(p))
            row_layout.addWidget(open_file)
            row_layout.addWidget(open_folder)
        else:
            reason = QLabel(result.message)
            reason.setObjectName("muted")
            row_layout.addWidget(reason)

        return row

    @staticmethod
    def _open_file(path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @staticmethod
    def _open_folder(path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
