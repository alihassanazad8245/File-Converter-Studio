"""Conversion history dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .. import history as history_module
from ..models import HistoryEntry


class HistoryDialog(QDialog):
    """Browse, open, remove, or clear past conversions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Conversion History")
        self.resize(720, 420)

        layout = QVBoxLayout(self)
        self._entries: list[HistoryEntry] = list(reversed(history_module.load_history()))

        if not self._entries:
            layout.addWidget(QLabel("No conversions yet. Convert a file to see it here."))
        else:
            self.table = QTableWidget(len(self._entries), 4)
            self.table.setHorizontalHeaderLabels(["Source", "Output", "When", "Status"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

            for row, entry in enumerate(self._entries):
                self.table.setItem(row, 0, QTableWidgetItem(Path(entry.source_path).name))
                self.table.setItem(row, 1, QTableWidgetItem(
                    f"{Path(entry.output_path).name} ({entry.format.upper()})"))
                self.table.setItem(row, 2, QTableWidgetItem(entry.timestamp.replace("T", " ")[:16]))
                status_item = QTableWidgetItem("✓ Completed" if entry.status == "completed" else "✕ Failed")
                self.table.setItem(row, 3, status_item)

            layout.addWidget(self.table)

            actions = QHBoxLayout()
            open_btn = QPushButton("Open Output")
            open_btn.setObjectName("secondary")
            open_btn.clicked.connect(self._open_selected)
            folder_btn = QPushButton("Open Folder")
            folder_btn.setObjectName("secondary")
            folder_btn.clicked.connect(self._open_selected_folder)
            remove_btn = QPushButton("Remove Entry")
            remove_btn.setObjectName("secondary")
            remove_btn.clicked.connect(self._remove_selected)
            clear_btn = QPushButton("Clear All")
            clear_btn.setObjectName("danger")
            clear_btn.clicked.connect(self._clear_all)
            actions.addWidget(open_btn)
            actions.addWidget(folder_btn)
            actions.addWidget(remove_btn)
            actions.addStretch(1)
            actions.addWidget(clear_btn)
            layout.addLayout(actions)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

    def _selected_entry(self) -> HistoryEntry | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._entries[rows[0].row()]

    def _open_selected(self) -> None:
        entry = self._selected_entry()
        if entry and Path(entry.output_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(entry.output_path))

    def _open_selected_folder(self) -> None:
        entry = self._selected_entry()
        if entry:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(entry.output_path).parent)))

    def _remove_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        # self._entries is newest-first (reversed); the underlying store is oldest-first.
        display_index = rows[0].row()
        store_index = len(self._entries) - 1 - display_index
        history_module.remove_entry(store_index)
        self.table.removeRow(display_index)
        self._entries.pop(display_index)

    def _clear_all(self) -> None:
        confirm = QMessageBox.question(
            self, "Clear History", "Remove all conversion history? This cannot be undone.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            history_module.clear_history()
            self.table.setRowCount(0)
            self._entries = []
