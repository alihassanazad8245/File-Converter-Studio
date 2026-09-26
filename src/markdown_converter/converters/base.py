"""Shared interface every format converter implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..config import ConversionOptions
from ..models import ConversionResult
from ..parser import ParsedDocument


class BaseConverter(ABC):
    """One converter per output format. Stateless - safe to reuse."""

    format_name: str = "base"

    @abstractmethod
    def convert(
        self, doc: ParsedDocument, output_path: Path, options: ConversionOptions,
    ) -> ConversionResult:
        """Write the converted file to ``output_path`` and report the outcome."""
        raise NotImplementedError
