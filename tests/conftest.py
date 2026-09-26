"""Shared pytest fixtures and setup.

Sets ``QT_QPA_PLATFORM=offscreen`` before any Qt import happens, so the GUI
construction tests run in CI/headless environments (and for you, right now)
without needing a real display or any manual environment setup.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture()
def qapp():
    """A shared QApplication instance for tests that construct widgets."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
