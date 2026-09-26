"""Tests for PDF utility tools."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from markdown_converter.errors import ConversionError, FileValidationError
from markdown_converter.pdf_tools import (
    compress_pdf,
    extract_pages,
    get_pdf_info,
    merge_pdfs,
    pdf_to_docx,
    pdf_to_images,
    remove_pages,
)


def _make_pdf(path: Path, n_pages: int) -> Path:
    writer = PdfWriter()
    for _ in range(n_pages):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_get_pdf_info(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 3)
    info = get_pdf_info(pdf)
    assert info["pages"] == 3
    assert info["size_bytes"] > 0


def test_get_pdf_info_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileValidationError):
        get_pdf_info(tmp_path / "nope.pdf")


def test_get_pdf_info_rejects_non_pdf(tmp_path: Path) -> None:
    fake = tmp_path / "fake.pdf"
    fake.write_text("not a pdf")
    with pytest.raises(FileValidationError):
        get_pdf_info(fake)


def test_merge_pdfs_combines_all_pages(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    b = _make_pdf(tmp_path / "b.pdf", 3)
    result = merge_pdfs([a, b], tmp_path / "merged.pdf")
    assert result.success
    assert len(PdfReader(str(tmp_path / "merged.pdf")).pages) == 5


def test_merge_pdfs_requires_at_least_two(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2)
    with pytest.raises(ConversionError):
        merge_pdfs([a], tmp_path / "merged.pdf")


def test_remove_pages_single_and_range(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 6)
    result = remove_pages(pdf, "1,3-4", tmp_path / "out.pdf")
    assert result.success
    assert len(PdfReader(str(tmp_path / "out.pdf")).pages) == 3


def test_remove_pages_rejects_out_of_bounds(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 3)
    with pytest.raises(ConversionError):
        remove_pages(pdf, "5", tmp_path / "out.pdf")


def test_remove_pages_rejects_removing_everything(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 2)
    with pytest.raises(ConversionError):
        remove_pages(pdf, "1-2", tmp_path / "out.pdf")


def test_extract_pages_keeps_only_specified(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 6)
    result = extract_pages(pdf, "2,4-5", tmp_path / "out.pdf")
    assert result.success
    assert len(PdfReader(str(tmp_path / "out.pdf")).pages) == 3


def test_extract_pages_rejects_empty_spec(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 3)
    with pytest.raises(ConversionError):
        extract_pages(pdf, "", tmp_path / "out.pdf")


def test_compress_pdf_produces_valid_output(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 3)
    result = compress_pdf(pdf, tmp_path / "compressed.pdf")
    assert result.success
    assert (tmp_path / "compressed.pdf").exists()
    assert len(PdfReader(str(tmp_path / "compressed.pdf")).pages) == 3


def test_pdf_to_images_creates_one_file_per_page(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 3)
    out_dir = tmp_path / "images"
    result = pdf_to_images(pdf, out_dir, "png")
    assert result.success
    assert len(list(out_dir.glob("*.png"))) == 3


def test_pdf_to_docx_produces_a_file(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", 1)
    result = pdf_to_docx(pdf, tmp_path / "out.docx")
    assert result.success
    assert (tmp_path / "out.docx").exists()
