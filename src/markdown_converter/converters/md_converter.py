"""Markdown -> Markdown converter.

Useful for the "same folder, different name/encoding" case, or as the
target when the user just wants a clean UTF-8, newline-normalised copy.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..config import ConversionOptions
from ..models import ConversionResult
from ..parser import ParsedDocument
from .base import BaseConverter


class MarkdownConverter(BaseConverter):
    format_name = "md"

    def convert(self, doc: ParsedDocument, output_path: Path, options: ConversionOptions) -> ConversionResult:
        start = time.monotonic()
        normalized = doc.source_text.replace("\r\n", "\n").replace("\r", "\n")
        output_path.write_text(normalized, encoding="utf-8")
        return ConversionResult(
            source_path=str(doc.source_dir), output_path=str(output_path), format="md",
            success=True, message="Markdown copy created successfully.",
            duration_seconds=round(time.monotonic() - start, 3),
        )
