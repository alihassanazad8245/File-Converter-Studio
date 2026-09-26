"""Markdown -> standalone HTML converter."""

from __future__ import annotations

import time
from pathlib import Path

from pygments.formatters import HtmlFormatter

from ..config import ConversionOptions
from ..models import ConversionResult
from ..parser import ParsedDocument, embed_local_images_as_data_uris
from .base import BaseConverter

_LIGHT_CSS = """
:root { --fg:#1b1f24; --bg:#ffffff; --muted:#5a6672; --accent:#2563eb;
  --line:#d8dee4; --chip:#f2f5f8; --code-bg:#f6f8fa; }
"""
_DARK_CSS = """
:root { --fg:#e6edf3; --bg:#0d1117; --muted:#9198a1; --accent:#58a6ff;
  --line:#30363d; --chip:#161b22; --code-bg:#161b22; }
"""
_BASE_CSS = """
* { box-sizing: border-box; }
body { margin:0; padding:2.5rem 1.5rem; background:var(--bg); color:var(--fg);
  font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
main { max-width: 860px; margin: 0 auto; }
h1,h2,h3,h4,h5,h6 { line-height:1.3; margin-top:2rem; margin-bottom:0.75rem; }
h1 { font-size:2rem; border-bottom:2px solid var(--accent); padding-bottom:.4rem; }
h2 { font-size:1.5rem; border-bottom:1px solid var(--line); padding-bottom:.3rem; }
p { margin: 0.9rem 0; }
a { color: var(--accent); }
code { background:var(--code-bg); padding:.15rem .4rem; border-radius:4px;
  font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.9em; }
pre { background:var(--code-bg); padding:1rem; border-radius:8px; overflow-x:auto;
  border:1px solid var(--line); }
pre code { background: none; padding: 0; }
table { border-collapse:collapse; width:100%; margin:1.2rem 0; }
th,td { border:1px solid var(--line); padding:.5rem .75rem; text-align:left; }
th { background:var(--chip); }
blockquote { margin:1rem 0; padding:.4rem 1rem; border-left:4px solid var(--accent);
  background:var(--chip); color:var(--muted); }
img { max-width:100%; border-radius:6px; }
hr { border:none; border-top:1px solid var(--line); margin:2rem 0; }
"""

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{theme_css}
{base_css}
{pygments_css}
</style>
</head>
<body><main>
{body}
</main></body>
</html>
"""


class HtmlConverter(BaseConverter):
    format_name = "html"

    def convert(self, doc: ParsedDocument, output_path: Path, options: ConversionOptions) -> ConversionResult:
        start = time.monotonic()
        opts = options.html
        html_body, missing_images = embed_local_images_as_data_uris(doc.html_body, doc.source_dir)

        if opts.standalone:
            theme_css = _DARK_CSS if opts.theme == "dark" else _LIGHT_CSS
            pygments_css = ""
            if opts.syntax_highlighting:
                pygments_css = HtmlFormatter(style="monokai" if opts.theme == "dark" else "default").get_style_defs(".codehilite")
            content = _TEMPLATE.format(
                title=doc.title, theme_css=theme_css, base_css=_BASE_CSS,
                pygments_css=pygments_css, body=html_body,
            )
        else:
            content = html_body

        output_path.write_text(content, encoding="utf-8")
        warnings = [f"Image not found: {src}" for src in missing_images]
        return ConversionResult(
            source_path=str(doc.source_dir), output_path=str(output_path), format="html",
            success=True, message="HTML created successfully.", warnings=warnings,
            duration_seconds=round(time.monotonic() - start, 3),
        )
