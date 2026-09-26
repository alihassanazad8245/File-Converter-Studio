"""Markdown quality checks.

Scope is deliberately honest: local image/link paths are checked for actual
existence on disk; remote (http/https) links are only counted, never
"verified" (that would need a network call this tool doesn't make). Every
issue found is a real, checkable fact about the document - nothing here is
guessed or simulated.
"""

from __future__ import annotations

from collections import Counter

from .models import QualityIssue, QualityReport
from .parser import ParsedDocument, is_remote_url, resolve_local_path

_LONG_LINE_THRESHOLD = 200


def check_quality(doc: ParsedDocument) -> QualityReport:
    """Run every quality check against a parsed document."""
    issues: list[QualityIssue] = []

    issues += _check_broken_images(doc)
    issues += _check_broken_local_links(doc)
    issues += _check_empty_headings(doc)
    issues += _check_missing_alt_text(doc)
    issues += _check_duplicate_headings(doc)
    issues += _check_long_lines(doc)

    return QualityReport(issues=issues)


def _check_broken_images(doc: ParsedDocument) -> list[QualityIssue]:
    issues = []
    for img in doc.soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        resolved = resolve_local_path(src, doc.source_dir)
        if resolved is not None and not resolved.is_file():
            issues.append(QualityIssue(
                severity="warning", message="Image not found",
                detail=src,
            ))
    return issues


def _check_broken_local_links(doc: ParsedDocument) -> list[QualityIssue]:
    issues = []
    for link in doc.soup.find_all("a"):
        href = link.get("href", "")
        if not href or is_remote_url(href) or href.startswith("#"):
            continue
        resolved = resolve_local_path(href, doc.source_dir)
        if resolved is not None and not resolved.exists():
            issues.append(QualityIssue(
                severity="warning", message="Local link target not found",
                detail=href,
            ))
    return issues


def _check_empty_headings(doc: ParsedDocument) -> list[QualityIssue]:
    issues = []
    for level in range(1, 7):
        for heading in doc.soup.find_all(f"h{level}"):
            if not heading.get_text(strip=True):
                issues.append(QualityIssue(
                    severity="warning", message=f"Empty h{level} heading", detail="",
                ))
    return issues


def _check_missing_alt_text(doc: ParsedDocument) -> list[QualityIssue]:
    missing = [img.get("src", "?") for img in doc.soup.find_all("img") if not img.get("alt")]
    if not missing:
        return []
    return [QualityIssue(
        severity="warning",
        message=f"{len(missing)} image(s) missing alt text",
        detail=", ".join(missing[:5]) + ("…" if len(missing) > 5 else ""),
    )]


def _check_duplicate_headings(doc: ParsedDocument) -> list[QualityIssue]:
    texts = [h.get_text(strip=True) for level in range(1, 7) for h in doc.soup.find_all(f"h{level}")]
    counts = Counter(t for t in texts if t)
    duplicates = [text for text, n in counts.items() if n > 1]
    if not duplicates:
        return []
    return [QualityIssue(
        severity="warning", message=f"{len(duplicates)} duplicate heading text(s)",
        detail=", ".join(duplicates[:5]),
    )]


def _check_long_lines(doc: ParsedDocument) -> list[QualityIssue]:
    long_lines = [
        i + 1 for i, line in enumerate(doc.source_text.splitlines())
        if len(line) > _LONG_LINE_THRESHOLD
    ]
    if not long_lines:
        return []
    return [QualityIssue(
        severity="warning",
        message=f"{len(long_lines)} very long line(s) (over {_LONG_LINE_THRESHOLD} characters)",
        detail=f"Lines: {', '.join(str(n) for n in long_lines[:8])}"
               + ("…" if len(long_lines) > 8 else ""),
    )]
