"""Tests for image conversion tools."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from markdown_converter.errors import ConversionError, FileValidationError
from markdown_converter.image_tools import convert_image, images_to_pdf


def _make_image(path: Path, mode: str = "RGB", color=(255, 0, 0)) -> Path:
    Image.new(mode, (20, 20), color).save(path)
    return path


def test_convert_image_basic_format_change(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "a.png")
    result = convert_image(src, tmp_path / "a.bmp", "BMP")
    assert result.success
    assert (tmp_path / "a.bmp").exists()
    with Image.open(tmp_path / "a.bmp") as img:
        assert img.format == "BMP"


def test_convert_image_flattens_transparency_for_jpeg(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "a.png", mode="RGBA", color=(255, 0, 0, 128))
    result = convert_image(src, tmp_path / "a.jpg", "JPEG")
    assert result.success
    with Image.open(tmp_path / "a.jpg") as img:
        assert img.mode == "RGB"  # no alpha channel in JPEG


def test_convert_image_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileValidationError):
        convert_image(tmp_path / "nope.png", tmp_path / "out.png", "PNG")


def test_convert_image_rejects_unsupported_extension(tmp_path: Path) -> None:
    bad = tmp_path / "file.xyz"
    bad.write_bytes(b"not an image")
    with pytest.raises(FileValidationError):
        convert_image(bad, tmp_path / "out.png", "PNG")


def test_convert_image_rejects_corrupted_image(tmp_path: Path) -> None:
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not actually a png")
    with pytest.raises(FileValidationError):
        convert_image(fake, tmp_path / "out.png", "PNG")


def test_images_to_pdf_combines_in_order(tmp_path: Path) -> None:
    img1 = _make_image(tmp_path / "a.png", color=(255, 0, 0))
    img2 = _make_image(tmp_path / "b.png", color=(0, 255, 0))
    result = images_to_pdf([img1, img2], tmp_path / "combined.pdf")
    assert result.success
    assert len(PdfReader(str(tmp_path / "combined.pdf")).pages) == 2


def test_images_to_pdf_requires_at_least_one_image(tmp_path: Path) -> None:
    with pytest.raises(ConversionError):
        images_to_pdf([], tmp_path / "out.pdf")


def test_images_to_pdf_handles_transparent_images(tmp_path: Path) -> None:
    img = _make_image(tmp_path / "a.png", mode="RGBA", color=(0, 0, 255, 100))
    result = images_to_pdf([img], tmp_path / "out.pdf")
    assert result.success
