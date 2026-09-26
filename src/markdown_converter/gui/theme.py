"""Light and dark QSS stylesheets.

A modern flat look: rounded corners, generous spacing, one accent colour,
no default-Windows-forms grey. Both themes are tuned so every Markdown
element (headings, links, inline code, code blocks, tables, blockquotes)
stays clearly readable - the same requirement the HTML converter's CSS
follows, kept visually consistent between the two.
"""

from __future__ import annotations

_SHARED = """
QWidget { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 13px; }
QPushButton { border-radius: 8px; padding: 8px 16px; border: none; font-weight: 600; }
QPushButton:disabled { opacity: 0.5; }
QLineEdit, QComboBox, QSpinBox { border-radius: 6px; padding: 6px 10px; border: 1px solid; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 8px 16px; border-radius: 6px; margin: 2px; }
QProgressBar { border-radius: 6px; text-align: center; border: none; }
QProgressBar::chunk { border-radius: 6px; }
QListWidget, QTableWidget, QTreeWidget { border-radius: 8px; border: 1px solid; padding: 4px; }
QScrollBar:vertical { width: 10px; background: transparent; }
QScrollBar::handle:vertical { border-radius: 5px; min-height: 24px; }
QMenuBar { padding: 2px; spacing: 4px; }
QMenuBar::item { padding: 6px 12px; border-radius: 6px; background: transparent; }
QMenu { padding: 6px; }
QMenu::item {
    padding: 8px 36px 8px 16px;
    border-radius: 6px;
    min-width: 220px;
}
QMenu::separator { height: 1px; margin: 6px 8px; }
QMenu::icon { padding-left: 8px; }
"""

LIGHT_QSS = _SHARED + """
QWidget { background: #ffffff; color: #1b1f24; }
QMainWindow, QDialog { background: #f7f8fa; }
QPushButton { background: #2563eb; color: white; }
QPushButton:hover { background: #1d4ed8; }
QPushButton#secondary { background: #eef1f5; color: #1b1f24; }
QPushButton#secondary:hover { background: #e2e6eb; }
QPushButton#danger { background: #dc2626; color: white; }
QLineEdit, QComboBox, QSpinBox { background: #ffffff; border-color: #d8dee4; color: #1b1f24; }
QLineEdit:focus, QComboBox:focus { border-color: #2563eb; }
QTabBar::tab { background: #eef1f5; color: #5a6672; }
QTabBar::tab:selected { background: #2563eb; color: white; }
QProgressBar { background: #eef1f5; color: #1b1f24; }
QProgressBar::chunk { background: #2563eb; }
QListWidget, QTableWidget, QTreeWidget { background: #ffffff; border-color: #d8dee4; }
QMenuBar { background: #ffffff; }
QMenuBar::item:selected { background: #eef1f5; }
QMenu { background: #ffffff; border: 1px solid #d8dee4; }
QMenu::item { color: #1b1f24; }
QMenu::item:selected { background: #2563eb; color: white; }
QMenu::item:disabled { color: #a7afba; }
QMenu::separator { background: #e2e6eb; }
QLabel#muted { color: #5a6672; }
QLabel#success { color: #16a34a; font-weight: 600; }
QLabel#warning { color: #d97706; font-weight: 600; }
QLabel#error { color: #dc2626; font-weight: 600; }
QFrame#card { background: #ffffff; border: 1px solid #d8dee4; border-radius: 10px; }
QFrame#dropzone { background: #f2f5f8; border: 2px dashed #2563eb; border-radius: 12px; }
"""

DARK_QSS = _SHARED + """
QWidget { background: #0d1117; color: #e6edf3; }
QMainWindow, QDialog { background: #0d1117; }
QPushButton { background: #2f81f7; color: white; }
QPushButton:hover { background: #4c93f8; }
QPushButton#secondary { background: #21262d; color: #e6edf3; }
QPushButton#secondary:hover { background: #30363d; }
QPushButton#danger { background: #f85149; color: white; }
QLineEdit, QComboBox, QSpinBox { background: #161b22; border-color: #30363d; color: #e6edf3; }
QLineEdit:focus, QComboBox:focus { border-color: #2f81f7; }
QTabBar::tab { background: #161b22; color: #9198a1; }
QTabBar::tab:selected { background: #2f81f7; color: white; }
QProgressBar { background: #161b22; color: #e6edf3; }
QProgressBar::chunk { background: #2f81f7; }
QListWidget, QTableWidget, QTreeWidget { background: #161b22; border-color: #30363d; }
QMenuBar { background: #0d1117; }
QMenuBar::item:selected { background: #21262d; }
QMenu { background: #161b22; border: 1px solid #30363d; }
QMenu::item { color: #e6edf3; }
QMenu::item:selected { background: #2f81f7; color: white; }
QMenu::item:disabled { color: #6e7681; }
QMenu::separator { background: #30363d; }
QLabel#muted { color: #9198a1; }
QLabel#success { color: #3fb950; font-weight: 600; }
QLabel#warning { color: #d29922; font-weight: 600; }
QLabel#error { color: #f85149; font-weight: 600; }
QFrame#card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
QFrame#dropzone { background: #161b22; border: 2px dashed #2f81f7; border-radius: 12px; }
"""


def stylesheet_for(theme: str) -> str:
    """Return the QSS for "light" or "dark". Unknown values fall back to light."""
    return DARK_QSS if theme == "dark" else LIGHT_QSS


def preview_css_for(theme: str) -> str:
    """CSS injected into the QTextBrowser live preview, matching the app theme."""
    if theme == "dark":
        return """
        body { background:#0d1117; color:#e6edf3; font-family:-apple-system,"Segoe UI",sans-serif; }
        h1,h2,h3 { color:#e6edf3; } a { color:#4c93f8; }
        code { background:#21262d; color:#e6edf3; padding:2px 4px; border-radius:4px; }
        pre { background:#161b22; padding:10px; border-radius:8px; border:1px solid #30363d; }
        table { border-collapse:collapse; } th,td { border:1px solid #30363d; padding:5px 8px; }
        th { background:#21262d; }
        blockquote { border-left:3px solid #2f81f7; margin:8px 0; padding:4px 10px;
          background:#161b22; color:#9198a1; }
        """
    return """
    body { background:#ffffff; color:#1b1f24; font-family:-apple-system,"Segoe UI",sans-serif; }
    h1,h2,h3 { color:#1b1f24; } a { color:#2563eb; }
    code { background:#f2f5f8; color:#1b1f24; padding:2px 4px; border-radius:4px; }
    pre { background:#f6f8fa; padding:10px; border-radius:8px; border:1px solid #d8dee4; }
    table { border-collapse:collapse; } th,td { border:1px solid #d8dee4; padding:5px 8px; }
    th { background:#f2f5f8; }
    blockquote { border-left:3px solid #2563eb; margin:8px 0; padding:4px 10px;
      background:#f2f5f8; color:#5a6672; }
    """
