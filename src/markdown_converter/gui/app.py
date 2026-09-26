"""QApplication bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .. import __app_name__
from .main_window import MainWindow


def run() -> int:
    """Create the QApplication, show the main window, and run the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    window = MainWindow()
    window.show()
    return app.exec()
