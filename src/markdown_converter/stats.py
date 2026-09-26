"""Document statistics and the structure inspector.

Pure functions over a parsed document - no I/O, trivially testable.
"""

from __future__ import annotations

import re

from .models import DocumentStats
from .parser import ParsedDocument

_WORDS_PER_MINUTE = 200


def compute_stats(doc: ParsedDocument) -> DocumentStats:
    """Compute word/character counts, reading time, and element counts."""
    text = doc.soup.get_text(separator=" ")
    words = re.findall(r"\S+", text)
    word_count = len(words)

    heading_breakdown: dict[str, int] = {}
    heading_count = 0
    for level in range(1, 7):
        count = len(doc.soup.find_all(f"h{level}"))
        if count:
            heading_breakdown[f"h{level}"] = count
        heading_count += count

    return DocumentStats(
        word_count=word_count,
        character_count=len(text),
        reading_time_minutes=round(max(word_count, 1) / _WORDS_PER_MINUTE, 1),
        heading_count=heading_count,
        image_count=len(doc.soup.find_all("img")),
        link_count=len(doc.soup.find_all("a")),
        code_block_count=len(doc.soup.find_all("pre")),
        table_count=len(doc.soup.find_all("table")),
        heading_breakdown=heading_breakdown,
    )
