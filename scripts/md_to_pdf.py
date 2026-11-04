#!/usr/bin/env python3
"""Turn summary Markdown files into PDFs with headless Chrome or Edge.

    python -m scripts.md_to_pdf "temp/summaries/attended-lectures/2026-10-08 操作系统.md"
    python -m scripts.md_to_pdf temp/summaries/attended-lectures --out-dir temp/pdf

A folder converts every ``.md`` in it.  The PDF lands next to the source unless
``--out-dir`` is given.  Needs Chrome or Edge.  ``$math$`` renders with KaTeX from a
CDN, so formulas stay raw text when offline.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown

BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist"

PAGE = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="{katex}/katex.min.css">
<script src="{katex}/katex.min.js"></script>
<script src="{katex}/contrib/auto-render.min.js"></script>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ font: 11pt/1.65 "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; color: #222; }}
h1, h2, h3 {{ line-height: 1.3; break-after: avoid; }}
pre, code {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 9.5pt; }}
pre {{ background: #f5f5f5; padding: 8px 10px; white-space: pre-wrap; break-inside: avoid; }}
code {{ background: #f5f5f5; padding: 0 3px; }}
pre code {{ background: none; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; break-inside: avoid; }}
th, td {{ border: 1px solid #bbb; padding: 4px 8px; text-align: left; }}
blockquote {{ margin-left: 0; padding-left: 12px; border-left: 3px solid #ccc; color: #555; }}
</style>
{body}
<script>renderMathInElement(document.body, {{delimiters: [
  {{left: "$$", right: "$$", display: true}}, {{left: "$", right: "$", display: false}}]}});</script>
"""


def find_browser() -> str:
    """Return the path of an installed Chrome or Edge."""
    for path in BROWSERS:
        if os.path.isfile(path):
            return path
    found = shutil.which("chrome") or shutil.which("msedge")
    if found:
        return found
    raise FileNotFoundError("Chrome or Edge not found")


def convert(md_path: Path, pdf_path: Path, browser: str) -> None:
    """Render one Markdown file to a PDF."""
    body = markdown.markdown(md_path.read_text(encoding="utf-8"),
                             extensions=["tables", "fenced_code", "sane_lists"])
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(PAGE.format(title=md_path.stem, body=body, katex=KATEX), encoding="utf-8")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             "--virtual-time-budget=10000",
             f"--user-data-dir={tmp}", f"--print-to-pdf={pdf_path.resolve()}",
             page.as_uri()],
            check=True, capture_output=True, timeout=120)


def main() -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="Markdown files or folders")
    ap.add_argument("--out-dir", help="write PDFs here instead of next to the source")
    args = ap.parse_args()

    browser = find_browser()
    sources = [f for p in map(Path, args.paths)
               for f in (sorted(p.glob("*.md")) if p.is_dir() else [p])]
    for src in sources:
        out = Path(args.out_dir) / (src.stem + ".pdf") if args.out_dir \
            else src.with_suffix(".pdf")
        convert(src, out, browser)
        print(out)


if __name__ == "__main__":
    main()
