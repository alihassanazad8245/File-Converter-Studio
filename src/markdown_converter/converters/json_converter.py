"""Markdown -> structured JSON converter.

Walks the same rendered HTML tree as every other converter and produces a
genuine structural representation - headings with levels, paragraphs, list
items, table rows, code blocks with their language (when detected), images,
and links - not just the raw HTML string.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from bs4.element import NavigableString, Tag

from ..config import ConversionOptions
from ..models import ConversionResult
from ..parser import ParsedDocument
from .base import BaseConverter


def _pre_to_code_block(pre) -> dict[str, Any]:
    code = pre.find("code")
    language = ""
    if code and code.get("class"):
        classes = [c for c in code.get("class") if c.startswith("language-")]
        language = classes[0].replace("language-", "") if classes else ""
    return {"type": "code_block", "language": language, "code": pre.get_text()}


def _node_to_dict(element) -> dict[str, Any] | None:
    if isinstance(element, NavigableString):
        text = str(element).strip()
        return {"type": "text", "content": text} if text else None
    if not isinstance(element, Tag):
        return None

    name = element.name
    if name and len(name) == 2 and name[0] == "h" and name[1].isdigit():
        return {"type": "heading", "level": int(name[1]), "text": element.get_text(strip=True)}
    if name == "p":
        return {"type": "paragraph", "text": element.get_text(strip=True)}
    if name in ("ul", "ol"):
        return {
            "type": "list", "ordered": name == "ol",
            "items": [li.get_text(strip=True) for li in element.find_all("li", recursive=False)],
        }
    if name == "table":
        rows = element.find_all("tr")
        return {"type": "table", "rows": [
            [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])] for row in rows
        ]}
    if name == "pre":
        return _pre_to_code_block(element)
    if name == "div" and "codehilite" in (element.get("class") or []):
        pre = element.find("pre")
        if pre:
            return _pre_to_code_block(pre)
    if name == "blockquote":
        return {"type": "blockquote", "text": element.get_text(strip=True)}
    if name == "hr":
        return {"type": "horizontal_rule"}
    if name == "img":
        return {"type": "image", "src": element.get("src", ""), "alt": element.get("alt", "")}

    text = element.get_text(strip=True)
    return {"type": "block", "tag": name, "text": text} if text else None


class JsonConverter(BaseConverter):
    format_name = "json"

    def convert(self, doc: ParsedDocument, output_path: Path, options: ConversionOptions) -> ConversionResult:
        start = time.monotonic()

        nodes = []
        for element in doc.soup.find_all(recursive=False):
            node = _node_to_dict(element)
            if node:
                nodes.append(node)

        images = [{"src": img.get("src", ""), "alt": img.get("alt", "")} for img in doc.soup.find_all("img")]
        links = [{"href": a.get("href", ""), "text": a.get_text(strip=True)} for a in doc.soup.find_all("a")]

        structure = {
            "title": doc.title,
            "nodes": nodes,
            "images": images,
            "links": links,
        }
        output_path.write_text(json.dumps(structure, indent=2, ensure_ascii=False), encoding="utf-8")

        return ConversionResult(
            source_path=str(doc.source_dir), output_path=str(output_path), format="json",
            success=True, message="Structured JSON created successfully.",
            duration_seconds=round(time.monotonic() - start, 3),
        )
