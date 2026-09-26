"""Image conversion tools: format conversion and combining images into a PDF.

Built entirely on Pillow - no system libraries needed.
"""

from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .config import SUPPORTED_IMAGE_EXTENSIONS
from .errors import ConversionError, FileValidationError
from .models import ConversionResult

# Formats that don't support transparency need a flattening step before saving.
_NO_ALPHA_FORMATS = {"JPEG", "BMP"}


def _validate_image(path: Path) -> Path:
    if not path.exists():
        raise FileValidationError(f"File does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported image type: '{path.suffix}'",
            details=f"Supported: {', '.join(SUPPORTED_IMAGE_EXTENSIONS)}",
        )
    try:
        with Image.open(path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise FileValidationError(f"'{path.name}' could not be read as an image.") from exc
    return path


def _prepare_for_format(img: Image.Image, output_format: str) -> Image.Image:
    """Flatten transparency onto white when the target format can't support it."""
    if output_format.upper() in _NO_ALPHA_FORMATS and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return img


def convert_image(input_path: Path, output_path: Path, output_format: str) -> ConversionResult:
    """Convert one image to a different format."""
    start = time.monotonic()
    input_path = _validate_image(input_path)
    fmt = output_format.upper()

    try:
        with Image.open(input_path) as img:
            prepared = _prepare_for_format(img, fmt)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = {"quality": 92} if fmt == "JPEG" else {}
            prepared.save(output_path, format=fmt, **save_kwargs)
    except (OSError, ValueError) as exc:
        raise ConversionError(f"Image conversion failed: {exc}") from exc

    return ConversionResult(
        source_path=str(input_path), output_path=str(output_path), format=fmt.lower(),
        success=True, message=f"Converted to {fmt}.",
        duration_seconds=round(time.monotonic() - start, 3),
    )


def images_to_pdf(input_paths: list[Path], output_path: Path) -> ConversionResult:
    """Combine one or more images, in the given order, into a single PDF."""
    start = time.monotonic()
    if not input_paths:
        raise ConversionError("Select at least one image.")

    pages: list[Image.Image] = []
    try:
        for path in input_paths:
            _validate_image(path)
            img = Image.open(path)
            if img.mode != "RGB":
                img = _prepare_for_format(img, "JPEG")
            pages.append(img)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = pages[0], pages[1:]
        first.save(output_path, save_all=True, append_images=rest)
    except (OSError, ValueError) as exc:
        raise ConversionError(f"Could not create PDF from images: {exc}") from exc
    finally:
        for page in pages:
            page.close()

    return ConversionResult(
        source_path=", ".join(p.name for p in input_paths), output_path=str(output_path),
        format="pdf", success=True, message=f"Combined {len(input_paths)} image(s) into one PDF.",
        duration_seconds=round(time.monotonic() - start, 3),
    )
