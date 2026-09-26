#!/usr/bin/env python3
"""Markdown Converter - entry point.

    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def run() -> int:
    """Launch the GUI, reporting missing dependencies in plain language."""
    try:
        from markdown_converter.gui.app import run as run_app
    except ImportError as exc:
        package = getattr(exc, "name", None) or "a required package"
        sys.stderr.write(
            f"\n[ERROR] Markdown Converter could not start: '{package}' is not installed.\n\n"
            "Install the dependencies first:\n\n"
            "    pip install -r requirements.txt\n\n"
        )
        return 2
    return run_app()


if __name__ == "__main__":
    raise SystemExit(run())
