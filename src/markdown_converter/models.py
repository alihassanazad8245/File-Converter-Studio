"""Typed data structures shared across the application."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class DocumentStats:
    """Smart document statistics computed from the rendered document."""

    word_count: int = 0
    character_count: int = 0
    reading_time_minutes: float = 0.0
    heading_count: int = 0
    image_count: int = 0
    link_count: int = 0
    code_block_count: int = 0
    table_count: int = 0
    heading_breakdown: dict[str, int] = field(default_factory=dict)  # {"h1": 1, "h2": 3, ...}


@dataclass(slots=True)
class QualityIssue:
    """One issue found by the Markdown quality checker."""

    severity: str  # "warning" or "error"
    message: str
    detail: str = ""


@dataclass(slots=True)
class QualityReport:
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {"issues": [asdict(i) for i in self.issues], "is_clean": self.is_clean}


@dataclass(slots=True)
class ConversionResult:
    """Outcome of converting one source file to one output format."""

    source_path: str
    output_path: str
    format: str
    success: bool
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class HistoryEntry:
    """One row in the conversion history log."""

    source_path: str
    output_path: str
    format: str
    timestamp: str
    status: str  # "completed" or "failed"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            source_path=data.get("source_path", ""),
            output_path=data.get("output_path", ""),
            format=data.get("format", ""),
            timestamp=data.get("timestamp", _now_iso()),
            status=data.get("status", "completed"),
        )

    @classmethod
    def from_result(cls, result: ConversionResult) -> "HistoryEntry":
        return cls(
            source_path=result.source_path, output_path=result.output_path,
            format=result.format, timestamp=_now_iso(),
            status="completed" if result.success else "failed",
        )
