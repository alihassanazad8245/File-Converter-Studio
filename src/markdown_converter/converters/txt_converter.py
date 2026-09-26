"""Markdown -> plain TXT converter (formatting stripped, structure kept)."""

from __future__ import annotations

import time
from pathlib import Path

from ..config import ConversionOptions
from ..models import ConversionResult
from ..parser import ParsedDocument
from .base import BaseConverter


class TxtConverter(BaseConverter):
    format_name = "txt"

    def convert(self, doc: ParsedDocument, output_path: Path, options: ConversionOptions) -> ConversionResult:
        start = time.monotonic()
        lines: list[str] = []
        for element in doc.soup.find_all(recursive=False):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue
            name = getattr(element, "name", "")
            if name and len(name) == 2 and name[0] == "h" and name[1].isdigit():
                lines.append(text.upper())
                lines.append("")
            else:
                lines.append(text)
                lines.append("")

        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return ConversionResult(
            source_path=str(doc.source_dir), output_path=str(output_path), format="txt",
            success=True, message="TXT created successfully.",
            duration_seconds=round(time.monotonic() - start, 3),
        )
