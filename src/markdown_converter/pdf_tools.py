"""PDF utility tools: merge, split/remove pages, compress, PDF -> images,
PDF -> DOCX.

Built on ``pypdf`` (pure Python, page-level operations) and ``PyMuPDF``
(rendering pages to images and driving ``pdf2docx``). No external binaries
required.
"""

from __future__ import annotations

import time
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .errors import ConversionError, FileValidationError
from .models import ConversionResult


def _validate_pdf(path: Path) -> Path:
    if not path.exists():
        raise FileValidationError(f"File does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise FileValidationError(f"Not a PDF file: {path}")
    try:
        PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - pypdf raises various parse errors
        raise FileValidationError(f"'{path.name}' could not be read as a PDF.") from exc
    return path


def get_pdf_info(path: Path) -> dict:
    """Page count and file size for one PDF, shown in the UI before an action."""
    path = _validate_pdf(path)
    reader = PdfReader(str(path))
    return {"pages": len(reader.pages), "size_bytes": path.stat().st_size}


def merge_pdfs(paths: list[Path], output_path: Path) -> ConversionResult:
    """Merge two or more PDFs, in the given order, into one file."""
    start = time.monotonic()
    if len(paths) < 2:
        raise ConversionError("Select at least two PDFs to merge.")

    writer = PdfWriter()
    for path in paths:
        reader = PdfReader(str(_validate_pdf(path)))
        for page in reader.pages:
            writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)

    return ConversionResult(
        source_path=", ".join(p.name for p in paths), output_path=str(output_path),
        format="pdf", success=True,
        message=f"Merged {len(paths)} PDFs ({sum(len(PdfReader(str(p)).pages) for p in paths)} pages total).",
        duration_seconds=round(time.monotonic() - start, 3),
    )


def _parse_page_spec(spec: str, page_count: int) -> list[int]:
    """Parse a page spec like ``1,3,5-7`` into a sorted list of 0-based indices."""
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = (int(x) for x in part.split("-", 1))
            except ValueError as exc:
                raise ConversionError(f"Invalid page range: '{part}'") from exc
            if start < 1 or end > page_count or start > end:
                raise ConversionError(f"Page range out of bounds: '{part}' (document has {page_count} pages)")
            indices.update(range(start - 1, end))
        else:
            try:
                page = int(part)
            except ValueError as exc:
                raise ConversionError(f"Invalid page number: '{part}'") from exc
            if page < 1 or page > page_count:
                raise ConversionError(f"Page {page} is out of bounds (document has {page_count} pages)")
            indices.add(page - 1)
    return sorted(indices)


def remove_pages(input_path: Path, page_spec: str, output_path: Path) -> ConversionResult:
    """Remove the given 1-based pages (e.g. ``"2,4-6"``) from a PDF."""
    start = time.monotonic()
    reader = PdfReader(str(_validate_pdf(input_path)))
    total = len(reader.pages)
    to_remove = set(_parse_page_spec(page_spec, total))
    if len(to_remove) >= total:
        raise ConversionError("Cannot remove every page - the output would be empty.")

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in to_remove:
            writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_path), format="pdf", success=True,
        message=f"Removed {len(to_remove)} page(s); {total - len(to_remove)} page(s) remain.",
        duration_seconds=round(time.monotonic() - start, 3),
    )


def extract_pages(input_path: Path, page_spec: str, output_path: Path) -> ConversionResult:
    """Extract only the given 1-based pages (e.g. ``"1,3,5-7"``) into a new PDF."""
    start = time.monotonic()
    reader = PdfReader(str(_validate_pdf(input_path)))
    total = len(reader.pages)
    keep = _parse_page_spec(page_spec, total)
    if not keep:
        raise ConversionError("No valid pages were specified to extract.")

    writer = PdfWriter()
    for i in keep:
        writer.add_page(reader.pages[i])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_path), format="pdf", success=True,
        message=f"Extracted {len(keep)} page(s) into a new PDF.",
        duration_seconds=round(time.monotonic() - start, 3),
    )


def compress_pdf(input_path: Path, output_path: Path) -> ConversionResult:
    """Reduce a PDF's file size using lossless stream compression.

    This uses pypdf's built-in content-stream compression - genuinely
    reduces size for most PDFs (especially ones with verbose or
    uncompressed content streams), but is more modest than dedicated tools
    like Ghostscript, which can also recompress embedded images. Documented
    honestly rather than oversold.
    """
    start = time.monotonic()
    input_path = _validate_pdf(input_path)
    before_size = input_path.stat().st_size

    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)

    after_size = output_path.stat().st_size
    saved_pct = round((1 - after_size / before_size) * 100, 1) if before_size else 0.0
    message = (
        f"Compressed {before_size / 1024:.0f} KB -> {after_size / 1024:.0f} KB "
        f"({saved_pct:+.1f}%)." if after_size < before_size else
        "No further reduction was possible - this PDF is already efficiently compressed."
    )

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_path), format="pdf",
        success=True, message=message,
        duration_seconds=round(time.monotonic() - start, 3),
    )


def pdf_to_images(input_path: Path, output_dir: Path, image_format: str = "png", dpi: int = 150) -> ConversionResult:
    """Render every page of a PDF to a separate image file."""
    start = time.monotonic()
    import pymupdf

    input_path = _validate_pdf(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)

    try:
        document = pymupdf.open(str(input_path))
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(f"Could not open PDF: {exc}") from exc

    created: list[str] = []
    try:
        for i, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix)
            out_path = output_dir / f"{stem}_page{i}.{image_format.lower()}"
            pixmap.save(str(out_path))
            created.append(str(out_path))
    finally:
        document.close()

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_dir), format=image_format.lower(),
        success=True, message=f"Created {len(created)} image(s) in {output_dir}.",
        duration_seconds=round(time.monotonic() - start, 3),
    )


def pdf_to_docx(input_path: Path, output_path: Path) -> ConversionResult:
    """Convert a PDF into an editable Word document, via ``pdf2docx``.

    Layout reconstruction (text position, basic tables) is a best effort -
    complex multi-column layouts or heavily designed PDFs may not convert
    perfectly. This is a real, documented limitation of PDF->DOCX conversion
    in general, not specific to this tool.
    """
    start = time.monotonic()
    from pdf2docx import Converter

    input_path = _validate_pdf(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        converter = Converter(str(input_path))
        try:
            converter.convert(str(output_path))
        finally:
            converter.close()
    except Exception as exc:  # noqa: BLE001 - pdf2docx can raise various internal errors
        raise ConversionError(f"PDF to Word conversion failed: {exc}") from exc

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_path), format="docx",
        success=True, message="Word document created. Complex layouts may need minor cleanup.",
        duration_seconds=round(time.monotonic() - start, 3),
    )
