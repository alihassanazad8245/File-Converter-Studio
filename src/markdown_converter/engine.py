"""The conversion engine.

Coordinates parsing, output-path resolution, and dispatch to the correct
per-format converter. Used directly by tests (no Qt involved) and wrapped by
:mod:`.worker` for non-blocking use from the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConversionOptions
from .converters.docx_converter import DocxConverter
from .converters.html_converter import HtmlConverter
from .converters.json_converter import JsonConverter
from .converters.md_converter import MarkdownConverter
from .converters.pdf_converter import PdfConverter
from .converters.txt_converter import TxtConverter
from .errors import AppError, ConversionError, OutputPathError
from .models import ConversionResult
from .parser import load_any_document
from .validators import (
    build_output_filename,
    ensure_writable_directory,
    resolve_collision,
    resolve_output_directory,
    validate_source_path,
)

_CONVERTERS = {
    "pdf": PdfConverter(),
    "docx": DocxConverter(),
    "html": HtmlConverter(),
    "txt": TxtConverter(),
    "md": MarkdownConverter(),
    "json": JsonConverter(),
}


@dataclass(slots=True)
class ConversionRequest:
    """Everything needed to convert one source file into one or more formats."""

    source_path: Path
    formats: list[str]
    same_folder: bool = True
    custom_output_dir: str = ""
    custom_filename: str = ""
    on_collision: str = "ask"  # "ask" is resolved by the caller before reaching the engine
    options: ConversionOptions | None = None
    allowed_extensions: tuple[str, ...] | None = None  # None = Markdown-only defaults


def convert_one(
    source_path: Path, output_format: str, output_path: Path, options: ConversionOptions,
) -> ConversionResult:
    """Convert a single already-validated source file to one format at one path.

    Works from any supported input type (Markdown, TXT, HTML, or DOCX) -
    :func:`~.parser.load_any_document` normalises all of them to the same
    HTML tree every converter already knows how to walk.
    """
    if output_format not in _CONVERTERS:
        raise ConversionError(f"Unsupported output format: '{output_format}'")

    try:
        doc = load_any_document(source_path)
    except (OSError, ValueError) as exc:
        raise ConversionError(f"Could not read source file: {source_path}") from exc

    converter = _CONVERTERS[output_format]
    return converter.convert(doc, output_path, options)


def resolve_and_convert(
    request: ConversionRequest, on_collision: str = "replace",
) -> list[ConversionResult]:
    """Validate the source, resolve every output path, and run every requested
    format conversion. ``on_collision`` must already be a concrete decision
    ("replace" or "new_copy") - "ask" is a UI-layer concern resolved before
    this function is called."""
    source_path = validate_source_path(str(request.source_path), request.allowed_extensions)
    output_dir = resolve_output_directory(source_path, request.same_folder, request.custom_output_dir)
    ensure_writable_directory(output_dir)

    options = request.options or ConversionOptions()
    results: list[ConversionResult] = []

    for fmt in request.formats:
        filename = build_output_filename(source_path, fmt, request.custom_filename)
        target = output_dir / filename
        resolved = resolve_collision(target, on_collision)
        if resolved is None:
            results.append(ConversionResult(
                source_path=str(source_path), output_path=str(target), format=fmt,
                success=False, message="Skipped: output file already exists.",
            ))
            continue
        try:
            results.append(convert_one(source_path, fmt, resolved, options))
        except (ConversionError, OutputPathError) as exc:
            results.append(ConversionResult(
                source_path=str(source_path), output_path=str(resolved), format=fmt,
                success=False, message=exc.message,
            ))

    return results


def convert_batch(
    requests: list[ConversionRequest], on_collision: str = "replace",
    progress_callback=None,
) -> list[ConversionResult]:
    """Run several conversion requests, reporting progress after each file.

    ``progress_callback(index, total, source_path)`` is called before each
    file starts, if provided - used by the GUI to update a progress bar
    without the engine knowing anything about Qt.
    """
    all_results: list[ConversionResult] = []
    total = len(requests)
    for index, request in enumerate(requests):
        if progress_callback:
            progress_callback(index, total, str(request.source_path))
        try:
            all_results.extend(resolve_and_convert(request, on_collision))
        except AppError as exc:
            all_results.append(ConversionResult(
                source_path=str(request.source_path), output_path="", format=",".join(request.formats),
                success=False, message=exc.message,
            ))
    return all_results
