"""First-launch / empty-state drop zone."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from .. import __app_name__
from ..config import SUPPORTED_INPUT_EXTENSIONS


class DropZone(QFrame):
    """Shown when no document is loaded. Accepts a dragged-and-dropped file."""

    file_dropped = Signal(str)
    browse_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(280)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        title = QLabel(__app_name__)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Edit and convert Markdown into beautiful documents.")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        drop_label = QLabel("📄  Drop a Markdown file here")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("font-size: 15px; margin-top: 10px;")
        layout.addWidget(drop_label)

        browse_btn = QPushButton("Browse Markdown File")
        browse_btn.setFixedWidth(220)
        browse_btn.clicked.connect(self.browse_clicked.emit)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        formats_label = QLabel("Supported output: PDF • DOCX • HTML • TXT • MD • JSON")
        formats_label.setObjectName("muted")
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(formats_label)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(SUPPORTED_INPUT_EXTENSIONS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(SUPPORTED_INPUT_EXTENSIONS):
                self.file_dropped.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()
