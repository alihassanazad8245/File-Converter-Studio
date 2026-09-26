"""PDF Tools tab: merge, split/remove pages, compress, PDF -> images, PDF -> DOCX."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import pdf_tools
from ..worker import run_callable_in_background


def _browse_pdf(parent) -> str:
    path, _ = QFileDialog.getOpenFileName(parent, "Select PDF", "", "PDF files (*.pdf)")
    return path


def _browse_save_pdf(parent, default_name: str) -> str:
    path, _ = QFileDialog.getSaveFileName(parent, "Save PDF As", default_name, "PDF files (*.pdf)")
    return path


class PdfToolsTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)
        tool_row = QHBoxLayout()
        tool_row.addWidget(QLabel("Tool:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItems([
            "Merge PDFs", "Split / Remove Pages", "Compress PDF",
            "PDF to Images", "PDF to Word",
        ])
        self.tool_combo.currentIndexChanged.connect(self._on_tool_changed)
        tool_row.addWidget(self.tool_combo)
        tool_row.addStretch(1)
        layout.addLayout(tool_row)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_merge_page())
        self.stack.addWidget(self._build_split_page())
        self.stack.addWidget(self._build_compress_page())
        self.stack.addWidget(self._build_to_images_page())
        self.stack.addWidget(self._build_to_docx_page())
        layout.addWidget(self.stack)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def _on_tool_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.status_label.setText("")

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

    # -- Merge ----------------------------------------------------------- #

    def _build_merge_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Select two or more PDFs, in the order you want them merged:"))
        self.merge_list = QListWidget()
        layout.addWidget(self.merge_list)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Add PDFs…")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._merge_add_files)
        up_btn = QPushButton("Move Up")
        up_btn.setObjectName("secondary")
        up_btn.clicked.connect(lambda: self._move_selected(self.merge_list, -1))
        down_btn = QPushButton("Move Down")
        down_btn.setObjectName("secondary")
        down_btn.clicked.connect(lambda: self._move_selected(self.merge_list, 1))
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("secondary")
        remove_btn.clicked.connect(lambda: self._remove_selected(self.merge_list))
        buttons.addWidget(add_btn)
        buttons.addWidget(up_btn)
        buttons.addWidget(down_btn)
        buttons.addWidget(remove_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        merge_btn = QPushButton("Merge PDFs…")
        merge_btn.clicked.connect(self._do_merge)
        layout.addWidget(merge_btn)
        return widget

    def _merge_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF files (*.pdf)")
        for path in paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(1, path)
            item.setToolTip(path)
            self.merge_list.addItem(item)

    @staticmethod
    def _move_selected(list_widget: QListWidget, delta: int) -> None:
        row = list_widget.currentRow()
        new_row = row + delta
        if row < 0 or not (0 <= new_row < list_widget.count()):
            return
        item = list_widget.takeItem(row)
        list_widget.insertItem(new_row, item)
        list_widget.setCurrentRow(new_row)

    @staticmethod
    def _remove_selected(list_widget: QListWidget) -> None:
        row = list_widget.currentRow()
        if row >= 0:
            list_widget.takeItem(row)

    def _do_merge(self) -> None:
        paths = [Path(self.merge_list.item(i).data(1)) for i in range(self.merge_list.count())]
        if len(paths) < 2:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Add at least two PDFs to merge.")
            return
        output = _browse_save_pdf(self, "merged.pdf")
        if not output:
            return
        self._run(lambda: pdf_tools.merge_pdfs(paths, Path(output)), lambda r: r.message)

    # -- Split / Remove Pages -------------------------------------------- #

    def _build_split_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        file_row = QHBoxLayout()
        self.split_file_edit = QLineEdit()
        self.split_file_edit.setPlaceholderText("Select a PDF…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._split_browse)
        file_row.addWidget(self.split_file_edit, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        self.split_info_label = QLabel("")
        self.split_info_label.setObjectName("muted")
        layout.addWidget(self.split_info_label)

        mode_row = QHBoxLayout()
        self.extract_radio = QRadioButton("Keep only these pages")
        self.remove_radio = QRadioButton("Remove these pages")
        self.extract_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.extract_radio)
        group.addButton(self.remove_radio)
        mode_row.addWidget(self.extract_radio)
        mode_row.addWidget(self.remove_radio)
        layout.addLayout(mode_row)

        pages_row = QHBoxLayout()
        pages_row.addWidget(QLabel("Pages (e.g. 1,3,5-7):"))
        self.split_pages_edit = QLineEdit()
        pages_row.addWidget(self.split_pages_edit, stretch=1)
        layout.addLayout(pages_row)

        go_btn = QPushButton("Apply…")
        go_btn.clicked.connect(self._do_split)
        layout.addWidget(go_btn)
        return widget

    def _split_browse(self) -> None:
        path = _browse_pdf(self)
        if not path:
            return
        self.split_file_edit.setText(path)
        try:
            info = pdf_tools.get_pdf_info(Path(path))
            self.split_info_label.setText(f"{info['pages']} page(s), {info['size_bytes'] / 1024:.0f} KB")
        except Exception as exc:  # noqa: BLE001
            self.split_info_label.setText(f"Could not read file: {exc}")

    def _do_split(self) -> None:
        path = self.split_file_edit.text().strip()
        spec = self.split_pages_edit.text().strip()
        if not path or not spec:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose a PDF and enter a page list first.")
            return
        default_name = "extracted.pdf" if self.extract_radio.isChecked() else "removed.pdf"
        output = _browse_save_pdf(self, default_name)
        if not output:
            return
        func = pdf_tools.extract_pages if self.extract_radio.isChecked() else pdf_tools.remove_pages
        self._run(lambda: func(Path(path), spec, Path(output)), lambda r: r.message)

    # -- Compress ---------------------------------------------------------- #

    def _build_compress_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            "Reduces file size using lossless stream compression. Results vary - "
            "already-optimised PDFs may not shrink further."
        ))
        file_row = QHBoxLayout()
        self.compress_file_edit = QLineEdit()
        self.compress_file_edit.setPlaceholderText("Select a PDF…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(lambda: self.compress_file_edit.setText(_browse_pdf(self) or self.compress_file_edit.text()))
        file_row.addWidget(self.compress_file_edit, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        go_btn = QPushButton("Compress…")
        go_btn.clicked.connect(self._do_compress)
        layout.addWidget(go_btn)
        return widget

    def _do_compress(self) -> None:
        path = self.compress_file_edit.text().strip()
        if not path:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose a PDF first.")
            return
        output = _browse_save_pdf(self, "compressed.pdf")
        if not output:
            return
        self._run(lambda: pdf_tools.compress_pdf(Path(path), Path(output)), lambda r: r.message)

    # -- PDF to Images ------------------------------------------------------ #

    def _build_to_images_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        file_row = QHBoxLayout()
        self.images_file_edit = QLineEdit()
        self.images_file_edit.setPlaceholderText("Select a PDF…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(lambda: self.images_file_edit.setText(_browse_pdf(self) or self.images_file_edit.text()))
        file_row.addWidget(self.images_file_edit, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Image format:"))
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["png", "jpeg"])
        format_row.addWidget(self.image_format_combo)
        format_row.addStretch(1)
        layout.addLayout(format_row)

        go_btn = QPushButton("Choose Output Folder & Convert…")
        go_btn.clicked.connect(self._do_to_images)
        layout.addWidget(go_btn)
        return widget

    def _do_to_images(self) -> None:
        path = self.images_file_edit.text().strip()
        if not path:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose a PDF first.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return
        fmt = self.image_format_combo.currentText()
        self._run(
            lambda: pdf_tools.pdf_to_images(Path(path), Path(out_dir), fmt),
            lambda r: r.message,
        )

    # -- PDF to Word ------------------------------------------------------ #

    def _build_to_docx_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            "Converts a PDF into an editable Word document. Complex, heavily "
            "designed layouts may need minor manual cleanup afterward."
        ))
        file_row = QHBoxLayout()
        self.docx_file_edit = QLineEdit()
        self.docx_file_edit.setPlaceholderText("Select a PDF…")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(lambda: self.docx_file_edit.setText(_browse_pdf(self) or self.docx_file_edit.text()))
        file_row.addWidget(self.docx_file_edit, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        go_btn = QPushButton("Convert to Word…")
        go_btn.clicked.connect(self._do_to_docx)
        layout.addWidget(go_btn)
        return widget

    def _do_to_docx(self) -> None:
        path = self.docx_file_edit.text().strip()
        if not path:
            self.status_label.setObjectName("warning")
            self.status_label.setText("Choose a PDF first.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save Word Document As",
                                                Path(path).stem + ".docx", "Word documents (*.docx)")
        if not output:
            return
        self._run(lambda: pdf_tools.pdf_to_docx(Path(path), Path(output)), lambda r: r.message)
