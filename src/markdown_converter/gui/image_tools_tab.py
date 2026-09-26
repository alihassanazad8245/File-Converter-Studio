"""Image Converter tab: format conversion and combining images into a PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import image_tools
from ..config import IMAGE_OUTPUT_FORMATS
from ..worker import run_callable_in_background

_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tiff)"


class ImageToolsTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Images (add one or more; order matters for 'Combine into PDF'):"))
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        file_buttons = QHBoxLayout()
        add_btn = QPushButton("Add Images…")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("secondary")
        remove_btn.clicked.connect(self._remove_selected)
        up_btn = QPushButton("Move Up")
        up_btn.setObjectName("secondary")
        up_btn.clicked.connect(lambda: self._move_selected(-1))
        down_btn = QPushButton("Move Down")
        down_btn.setObjectName("secondary")
        down_btn.clicked.connect(lambda: self._move_selected(1))
        file_buttons.addWidget(add_btn)
        file_buttons.addWidget(remove_btn)
        file_buttons.addWidget(up_btn)
        file_buttons.addWidget(down_btn)
        file_buttons.addStretch(1)
        layout.addLayout(file_buttons)

        convert_row = QHBoxLayout()
        convert_row.addWidget(QLabel("Convert each to:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(IMAGE_OUTPUT_FORMATS)
        convert_row.addWidget(self.format_combo)
        convert_btn = QPushButton("Convert…")
        convert_btn.clicked.connect(self._do_convert)
        convert_row.addWidget(convert_btn)
        convert_row.addStretch(1)
        layout.addLayout(convert_row)

        pdf_row = QHBoxLayout()
        pdf_btn = QPushButton("Combine All into One PDF…")
        pdf_btn.clicked.connect(self._do_combine_pdf)
        pdf_row.addWidget(pdf_btn)
        pdf_row.addStretch(1)
        layout.addLayout(pdf_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select images", "", _FILTER)
        for path in paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(1, path)
            item.setToolTip(path)
            self.file_list.addItem(item)

    def _remove_selected(self) -> None:
        row = self.file_list.currentRow()
        if row >= 0:
            self.file_list.takeItem(row)

    def _move_selected(self, delta: int) -> None:
        row = self.file_list.currentRow()
        new_row = row + delta
        if row < 0 or not (0 <= new_row < self.file_list.count()):
            return
        item = self.file_list.takeItem(row)
        self.file_list.insertItem(new_row, item)
        self.file_list.setCurrentRow(new_row)

    def _paths(self) -> list[Path]:
        return [Path(self.file_list.item(i).data(1)) for i in range(self.file_list.count())]

    def _run(self, func, on_success_message) -> None:
        self.status_label.setObjectName("muted")
        self.status_label.setText("Working…")

        def succeeded(result):
            self.status_label.setObjectName("success")
            self.status_label.setText(on_success_message(result))

        def failed(message):
            self.status_label.setObjectName("error")
            self.status_label.setText(f"Failed: {message}")

        self._thread, self._worker = run_callable_in_background(func, succeeded, failed)

    def _do_convert(self) -> None:
        paths = self._paths()
        if not paths:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Add at least one image first.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return
        fmt = self.format_combo.currentText()
        ext = "jpg" if fmt == "JPEG" else fmt.lower()

        def convert_all():
            results = []
            for path in paths:
                output = Path(out_dir) / f"{path.stem}.{ext}"
                results.append(image_tools.convert_image(path, output, fmt))
            return results

        self._run(convert_all, lambda results: f"Converted {len(results)} image(s) to {fmt}.")

    def _do_combine_pdf(self) -> None:
        paths = self._paths()
        if not paths:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Add at least one image first.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save PDF As", "images.pdf", "PDF files (*.pdf)")
        if not output:
            return
        self._run(lambda: image_tools.images_to_pdf(paths, Path(output)), lambda r: r.message)
