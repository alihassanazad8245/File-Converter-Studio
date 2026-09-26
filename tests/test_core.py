"""Tests for path validation, filename generation, parsing, stats, and quality checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_converter.errors import FileValidationError, OutputPathError
from markdown_converter.parser import (
    embed_local_images_as_data_uris,
    is_remote_url,
    parse_markdown,
    resolve_local_path,
)
from markdown_converter.quality import check_quality
from markdown_converter.stats import compute_stats
from markdown_converter.validators import (
    build_output_filename,
    resolve_collision,
    resolve_output_directory,
    sanitize_filename,
    validate_source_path,
)

# --------------------------------------------------------------------------- #
# Path validation
# --------------------------------------------------------------------------- #


def test_validate_source_path_rejects_empty_input() -> None:
    with pytest.raises(FileValidationError):
        validate_source_path("")


def test_validate_source_path_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileValidationError, match="does not exist"):
        validate_source_path(str(tmp_path / "nope.md"))


def test_validate_source_path_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(FileValidationError, match="folder"):
        validate_source_path(str(tmp_path))


def test_validate_source_path_rejects_wrong_extension(tmp_path: Path) -> None:
    bad = tmp_path / "notes.docx"
    bad.write_text("content")
    with pytest.raises(FileValidationError, match="Unsupported"):
        validate_source_path(str(bad))


def test_validate_source_path_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.md"
    empty.write_text("")
    with pytest.raises(FileValidationError, match="empty"):
        validate_source_path(str(empty))


def test_validate_source_path_accepts_valid_markdown(tmp_path: Path) -> None:
    good = tmp_path / "notes.md"
    good.write_text("# Hello")
    result = validate_source_path(str(good))
    assert result == good


def test_validate_source_path_strips_quotes(tmp_path: Path) -> None:
    good = tmp_path / "notes.md"
    good.write_text("# Hello")
    result = validate_source_path(f'"{good}"')
    assert result == good


# --------------------------------------------------------------------------- #
# Filename generation and collision handling
# --------------------------------------------------------------------------- #


def test_sanitize_filename_strips_invalid_characters() -> None:
    assert sanitize_filename('report:<>"/\\|?*.txt') == "report_.txt"


def test_sanitize_filename_empty_falls_back() -> None:
    assert sanitize_filename("   ") == "output"


def test_build_output_filename_uses_source_stem(tmp_path: Path) -> None:
    src = tmp_path / "research_notes.md"
    assert build_output_filename(src, "pdf") == "research_notes.pdf"


def test_build_output_filename_uses_custom_name(tmp_path: Path) -> None:
    src = tmp_path / "research_notes.md"
    assert build_output_filename(src, "pdf", "My Research Report") == "My Research Report.pdf"


def test_build_output_filename_strips_custom_extension(tmp_path: Path) -> None:
    src = tmp_path / "notes.md"
    assert build_output_filename(src, "docx", "already.pdf") == "already.docx"


def test_resolve_output_directory_same_folder(tmp_path: Path) -> None:
    src = tmp_path / "notes.md"
    src.write_text("x")
    assert resolve_output_directory(src, same_folder=True, custom_dir="") == tmp_path


def test_resolve_output_directory_custom_folder(tmp_path: Path) -> None:
    src = tmp_path / "notes.md"
    other = tmp_path / "converted"
    result = resolve_output_directory(src, same_folder=False, custom_dir=str(other))
    assert result == other


def test_resolve_output_directory_rejects_file_as_directory(tmp_path: Path) -> None:
    src = tmp_path / "notes.md"
    src.write_text("x")
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("x")
    with pytest.raises(OutputPathError):
        resolve_output_directory(src, same_folder=False, custom_dir=str(blocker))


def test_resolve_collision_no_existing_file_returns_target(tmp_path: Path) -> None:
    target = tmp_path / "out.pdf"
    assert resolve_collision(target, "replace") == target


def test_resolve_collision_replace_returns_same_path(tmp_path: Path) -> None:
    target = tmp_path / "out.pdf"
    target.write_text("existing")
    assert resolve_collision(target, "replace") == target


def test_resolve_collision_cancel_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "out.pdf"
    target.write_text("existing")
    assert resolve_collision(target, "cancel") is None


def test_resolve_collision_new_copy_finds_free_name(tmp_path: Path) -> None:
    target = tmp_path / "out.pdf"
    target.write_text("existing")
    (tmp_path / "out (1).pdf").write_text("also existing")
    result = resolve_collision(target, "new_copy")
    assert result == tmp_path / "out (2).pdf"


# --------------------------------------------------------------------------- #
# Markdown parsing
# --------------------------------------------------------------------------- #


def test_parse_markdown_detects_h1_as_title(tmp_path: Path) -> None:
    doc = parse_markdown("# My Report\n\nBody text.", tmp_path)
    assert doc.title == "My Report"


def test_parse_markdown_falls_back_to_untitled(tmp_path: Path) -> None:
    doc = parse_markdown("", tmp_path)
    assert doc.title == "Untitled"


def test_parse_markdown_renders_tables_and_code(tmp_path: Path) -> None:
    text = "| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nprint(1)\n```\n"
    doc = parse_markdown(text, tmp_path)
    assert doc.soup.find("table") is not None
    assert doc.soup.find("pre") is not None


def test_is_remote_url() -> None:
    assert is_remote_url("https://example.com/image.png")
    assert is_remote_url("mailto:test@example.com")
    assert not is_remote_url("images/diagram.png")
    assert not is_remote_url("../notes.md")


def test_resolve_local_path_relative(tmp_path: Path) -> None:
    result = resolve_local_path("images/pic.png", tmp_path)
    assert result == tmp_path / "images" / "pic.png"


def test_resolve_local_path_remote_returns_none(tmp_path: Path) -> None:
    assert resolve_local_path("https://example.com/pic.png", tmp_path) is None


def test_embed_local_images_reports_missing(tmp_path: Path) -> None:
    html = '<p><img src="missing.png" alt="x"></p>'
    new_html, missing = embed_local_images_as_data_uris(html, tmp_path)
    assert missing == ["missing.png"]
    assert "data:" not in new_html or "src=\"\"" in new_html


def test_embed_local_images_embeds_existing_image(tmp_path: Path) -> None:
    from PIL import Image

    img_path = tmp_path / "pic.png"
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(img_path)

    html = f'<p><img src="{img_path.name}" alt="x"></p>'
    new_html, missing = embed_local_images_as_data_uris(html, tmp_path)
    assert missing == []
    assert "data:image/png;base64," in new_html


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def test_compute_stats_counts_elements(tmp_path: Path) -> None:
    text = "# Title\n\n## Sub\n\nSome words here.\n\n- a\n- b\n\n[link](x.md)\n\n![img](x.png)\n"
    doc = parse_markdown(text, tmp_path)
    stats = compute_stats(doc)
    assert stats.heading_count == 2
    assert stats.heading_breakdown == {"h1": 1, "h2": 1}
    assert stats.link_count == 1
    assert stats.image_count == 1
    assert stats.word_count > 0


def test_compute_stats_empty_document(tmp_path: Path) -> None:
    doc = parse_markdown("", tmp_path)
    stats = compute_stats(doc)
    assert stats.word_count == 0
    assert stats.heading_count == 0


# --------------------------------------------------------------------------- #
# Quality checks
# --------------------------------------------------------------------------- #


def test_check_quality_clean_document(tmp_path: Path) -> None:
    doc = parse_markdown("# Title\n\nA short, clean paragraph.\n", tmp_path)
    report = check_quality(doc)
    assert report.is_clean


def test_check_quality_detects_broken_image(tmp_path: Path) -> None:
    doc = parse_markdown("![alt text](missing.png)", tmp_path)
    report = check_quality(doc)
    assert any("Image not found" in i.message for i in report.issues)


def test_check_quality_detects_missing_alt_text(tmp_path: Path) -> None:
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    doc = parse_markdown(f"![](pic.png)", tmp_path)
    report = check_quality(doc)
    assert any("alt text" in i.message for i in report.issues)


def test_check_quality_ignores_remote_links(tmp_path: Path) -> None:
    doc = parse_markdown("[external](https://example.com)", tmp_path)
    report = check_quality(doc)
    assert not any("Local link" in i.message for i in report.issues)


def test_check_quality_detects_duplicate_headings(tmp_path: Path) -> None:
    doc = parse_markdown("# Same\n\ntext\n\n# Same\n", tmp_path)
    report = check_quality(doc)
    assert any("duplicate heading" in i.message for i in report.issues)


def test_check_quality_detects_long_lines(tmp_path: Path) -> None:
    doc = parse_markdown("x" * 250, tmp_path)
    report = check_quality(doc)
    assert any("long line" in i.message for i in report.issues)
