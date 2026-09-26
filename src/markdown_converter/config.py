"""Central configuration: paths, defaults, supported formats, and presets.

All application data (settings, history) lives under a local ``.appdata``
folder next to the source tree, in plain JSON - no registry, no hidden
system-wide folders, easy to inspect or delete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPDATA_DIR = PROJECT_ROOT / ".appdata"
SETTINGS_FILE = APPDATA_DIR / "settings.json"
HISTORY_FILE = APPDATA_DIR / "history.json"

SUPPORTED_INPUT_EXTENSIONS = (".md", ".markdown", ".txt")
DOCUMENT_INPUT_EXTENSIONS = (".md", ".markdown", ".txt", ".html", ".htm", ".docx")
SUPPORTED_OUTPUT_FORMATS = ("pdf", "docx", "html", "txt", "md", "json")

SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tiff")
IMAGE_OUTPUT_FORMATS = ("PNG", "JPEG", "BMP", "WEBP", "GIF", "TIFF")

MAX_HISTORY_ENTRIES = 200
MAX_FILE_SIZE_MB = 25  # very large files get a warning, not a hard block

#: python-markdown extensions used for every conversion.
MARKDOWN_EXTENSIONS = [
    "extra", "tables", "fenced_code", "codehilite", "toc",
    "sane_lists", "nl2br", "attr_list",
]
MARKDOWN_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "noclasses": False},
    "toc": {"anchorlink": False},
}


@dataclass(slots=True)
class PdfOptions:
    page_size: str = "A4"  # A4, Letter, Legal
    orientation: str = "portrait"  # portrait, landscape
    margin_mm: int = 20
    font_family: str = "Helvetica"
    font_size: int = 11
    include_toc: bool = False
    include_title_page: bool = False


@dataclass(slots=True)
class DocxOptions:
    font_family: str = "Calibri"
    font_size: int = 11
    include_toc: bool = False


@dataclass(slots=True)
class HtmlOptions:
    standalone: bool = True
    embed_css: bool = True
    theme: str = "light"  # light, dark
    syntax_highlighting: bool = True


@dataclass(slots=True)
class ConversionOptions:
    """Bundle of all format-specific option groups for one conversion job."""

    pdf: PdfOptions = field(default_factory=PdfOptions)
    docx: DocxOptions = field(default_factory=DocxOptions)
    html: HtmlOptions = field(default_factory=HtmlOptions)


#: Named presets applying a full set of sensible option combinations.
PRESETS: dict[str, ConversionOptions] = {
    "Simple PDF": ConversionOptions(
        pdf=PdfOptions(page_size="A4", font_size=11, include_toc=False, include_title_page=False),
    ),
    "Academic Report": ConversionOptions(
        pdf=PdfOptions(page_size="A4", font_size=12, include_toc=True, include_title_page=True,
                      font_family="Times-Roman"),
        docx=DocxOptions(font_family="Times New Roman", font_size=12, include_toc=True),
    ),
    "Technical Documentation": ConversionOptions(
        pdf=PdfOptions(page_size="Letter", font_size=10, include_toc=True, include_title_page=False),
        html=HtmlOptions(theme="dark", syntax_highlighting=True),
    ),
    "Clean Web Page": ConversionOptions(
        html=HtmlOptions(standalone=True, embed_css=True, theme="light", syntax_highlighting=True),
    ),
    "Professional Document": ConversionOptions(
        pdf=PdfOptions(page_size="A4", font_size=11, include_title_page=True),
        docx=DocxOptions(font_family="Calibri", font_size=11),
    ),
}

DEFAULT_PRESET = "Simple PDF"
