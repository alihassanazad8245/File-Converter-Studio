"""Markdown parsing and HTML rendering.

Everything downstream (preview, PDF, DOCX, TXT, stats, quality checks) works
from the same rendered HTML tree, so there is exactly one Markdown parser to
maintain and every output format sees an identical interpretation of the
source document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import markdown as _markdown
from bs4 import BeautifulSoup

from .config import MARKDOWN_EXTENSION_CONFIGS, MARKDOWN_EXTENSIONS


@dataclass(slots=True)
class ParsedDocument:
    """A Markdown source rendered to HTML, with a few convenience fields."""

    source_text: str
    html_body: str
    title: str
    soup: BeautifulSoup
    source_dir: Path


def _detect_title(source_text: str, soup: BeautifulSoup) -> str:
    """Use the first H1 as the document title; fall back to 'Untitled'."""
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    first_line = source_text.strip().splitlines()[0] if source_text.strip() else ""
    return first_line.lstrip("#").strip() or "Untitled"


def parse_markdown(source_text: str, source_dir: Path) -> ParsedDocument:
    """Render Markdown source into a :class:`ParsedDocument`."""
    html_body = _markdown.markdown(
        source_text, extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS, output_format="html5",
    )
    soup = BeautifulSoup(html_body, "html.parser")
    title = _detect_title(source_text, soup)
    return ParsedDocument(
        source_text=source_text, html_body=html_body, title=title,
        soup=soup, source_dir=source_dir,
    )


def _txt_to_html(text: str) -> str:
    """Wrap plain text into paragraphs, splitting on blank lines."""
    import html as html_module

    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return "\n".join(
        f"<p>{html_module.escape(block).replace(chr(10), '<br>')}</p>" for block in blocks
    )


def _docx_to_html(path: Path) -> tuple[str, list[str]]:
    """Convert a .docx file to HTML using mammoth. Returns (html, warnings)."""
    import mammoth

    with path.open("rb") as handle:
        result = mammoth.convert_to_html(handle)
    warnings = [m.message for m in result.messages]
    return result.value, warnings


def load_any_document(path: Path) -> ParsedDocument:
    """Load a .md, .markdown, .txt, .html/.htm, or .docx file into a
    :class:`ParsedDocument`, so every converter can work from any supported
    input format without knowing the difference.

    For non-Markdown sources, ``source_text`` holds the best available plain
    text (used only by the long-line quality check and the TXT/MD exporters);
    the rendered HTML tree is what every converter actually walks.
    """
    suffix = path.suffix.lower()

    if suffix in (".md", ".markdown"):
        text = path.read_text(encoding="utf-8", errors="replace")
        return parse_markdown(text, path.parent)

    if suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")
        html_body = _txt_to_html(text)
        soup = BeautifulSoup(html_body, "html.parser")
        return ParsedDocument(source_text=text, html_body=html_body,
                              title=path.stem, soup=soup, source_dir=path.parent)

    if suffix in (".html", ".htm"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        body = soup.body
        html_body = body.decode_contents() if body else raw
        inner_soup = BeautifulSoup(html_body, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else _detect_title(raw, inner_soup)
        return ParsedDocument(source_text=inner_soup.get_text("\n"), html_body=html_body,
                              title=title, soup=inner_soup, source_dir=path.parent)

    if suffix == ".docx":
        html_body, _warnings = _docx_to_html(path)
        soup = BeautifulSoup(html_body, "html.parser")
        title = _detect_title(soup.get_text("\n"), soup) if soup.find("h1") else path.stem
        return ParsedDocument(source_text=soup.get_text("\n"), html_body=html_body,
                              title=title, soup=soup, source_dir=path.parent)

    raise ValueError(f"Unsupported input format: '{suffix}'")


def is_remote_url(url: str) -> bool:
    """Whether a link/image target is a remote URL rather than a local path."""
    parsed = urlparse(url)
    return bool(parsed.scheme) and parsed.scheme in ("http", "https", "ftp", "mailto")


def resolve_local_path(url: str, source_dir: Path) -> Path | None:
    """Resolve a relative or absolute local image/link path against the
    source file's directory. Returns None for remote URLs."""
    if is_remote_url(url) or url.startswith("#"):
        return None
    path = Path(url)
    return path if path.is_absolute() else (source_dir / path)


def embed_local_images_as_data_uris(html_body: str, source_dir: Path) -> tuple[str, list[str]]:
    """Replace local ``<img>`` src attributes with base64 data URIs.

    Needed for renderers (PDF/DOCX/Qt preview) that can't resolve relative
    filesystem paths on their own. Returns ``(new_html, missing_image_paths)``
    so the caller can surface "image not found" warnings without crashing.
    """
    import base64
    import mimetypes

    soup = BeautifulSoup(html_body, "html.parser")
    missing: list[str] = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or is_remote_url(src) or src.startswith("data:"):
            continue
        resolved = resolve_local_path(src, source_dir)
        if resolved is None or not resolved.is_file():
            missing.append(src)
            img["alt"] = f"[Image not found: {src}]" + (f" {img.get('alt', '')}" if img.get("alt") else "")
            img["src"] = ""
            continue
        try:
            data = resolved.read_bytes()
            mime, _ = mimetypes.guess_type(str(resolved))
            mime = mime or "image/png"
            img["src"] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        except OSError:
            missing.append(src)

    return str(soup), missing
