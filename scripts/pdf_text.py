#!/usr/bin/env python3
"""Extract text from a PDF with whichever backend is available.

  scripts/pdf_text.py paper.pdf                 whole document to stdout
  scripts/pdf_text.py paper.pdf --pages 1-3     page range (1-based, inclusive)
  scripts/pdf_text.py paper.pdf --out text.txt  write to a file instead
  scripts/pdf_text.py paper.pdf --info          page count and backend as JSON

Layout mode is used so tables and two-column pages stay readable.
Exit code 2 means no backend is installed (run scripts/setup.py).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _backend import detect, page_count  # noqa: E402


def parse_pages(spec: str | None):
    if not spec:
        return None, None
    if "-" in spec:
        a, b = spec.split("-", 1)
        return int(a), int(b)
    return int(spec), int(spec)


def extract(pdf: str, first, last, backend: str) -> str:
    if backend == "poppler":
        cmd = ["pdftotext", "-layout"]
        if first:
            cmd += ["-f", str(first), "-l", str(last)]
        return subprocess.run(cmd + [pdf, "-"], capture_output=True, text=True, check=True).stdout
    if backend == "pymupdf":
        import fitz
        with fitz.open(pdf) as doc:
            lo = (first or 1) - 1
            hi = last or doc.page_count
            return "\n\f".join(doc[i].get_text("text") for i in range(lo, hi))
    raise SystemExit(2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pdf")
    p.add_argument("--pages")
    p.add_argument("--out")
    p.add_argument("--info", action="store_true")
    a = p.parse_args()
    backend = detect()
    if a.info:
        print(json.dumps({"backend": backend, "pages": page_count(a.pdf, backend)}))
        return
    if backend == "none":
        print("no PDF backend (poppler or PyMuPDF); run scripts/setup.py", file=sys.stderr)
        raise SystemExit(2)
    first, last = parse_pages(a.pages)
    text = extract(a.pdf, first, last, backend)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {len(text)} chars to {a.out} ({backend})")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
