#!/usr/bin/env python3
"""Find and crop figures from a PDF.

Workflow:
  1. scout  — render candidate pages at low resolution (80 DPI) and look at them
  2. crop   — cut the figure out at 200 DPI; crop coordinates are the scout
              pixel coordinates multiplied by 2.5 (200 / 80)

  scripts/pdf_figures.py scout paper.pdf 1 4 /tmp/scout
  scripts/pdf_figures.py crop  paper.pdf 3 125 125 1463 875 figures/fig1-overview.png
  scripts/pdf_figures.py backend

crop arguments: <page> <x> <y> <width> <height> in pixels at --dpi (default 200).
Exit code 2 means no backend is installed (run scripts/setup.py).
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _backend import detect  # noqa: E402

SCOUT_DPI = 80
CROP_DPI = 200


def scout(pdf: str, first: int, last: int, out_dir: str, dpi: int, backend: str) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(pdf).stem
    if backend == "poppler":
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(first), "-l", str(last), pdf, str(out / f"{stem}_p")],
                       check=True)
        return sorted(str(p) for p in out.glob(f"{stem}_p*.png"))
    if backend == "pymupdf":
        import fitz
        paths = []
        with fitz.open(pdf) as doc:
            for i in range(first - 1, min(last, doc.page_count)):
                path = out / f"{stem}_p-{i + 1}.png"
                doc[i].get_pixmap(dpi=dpi).save(str(path))
                paths.append(str(path))
        return paths
    raise SystemExit(2)


def crop(pdf: str, page: int, x: int, y: int, w: int, h: int, out: str, dpi: int, backend: str) -> None:
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if backend == "poppler":
        prefix = out_path.with_suffix("")
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                        "-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h), pdf, str(prefix)], check=True)
        # pdftoppm appends -<page>; rename to the requested name
        produced = sorted(out_path.parent.glob(f"{prefix.name}-*.png"))
        if produced:
            shutil.move(str(produced[-1]), str(out_path))
        return
    if backend == "pymupdf":
        import fitz
        scale = 72.0 / dpi
        clip = fitz.Rect(x * scale, y * scale, (x + w) * scale, (y + h) * scale)
        with fitz.open(pdf) as doc:
            doc[page - 1].get_pixmap(dpi=dpi, clip=clip).save(str(out_path))
        return
    raise SystemExit(2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scout")
    s.add_argument("pdf"); s.add_argument("first", type=int); s.add_argument("last", type=int); s.add_argument("out_dir")
    s.add_argument("--dpi", type=int, default=SCOUT_DPI)
    c = sub.add_parser("crop")
    c.add_argument("pdf"); c.add_argument("page", type=int)
    for n in ("x", "y", "w", "h"):
        c.add_argument(n, type=int)
    c.add_argument("out"); c.add_argument("--dpi", type=int, default=CROP_DPI)
    sub.add_parser("backend")
    a = p.parse_args()
    backend = detect()
    if a.cmd == "backend":
        print(json.dumps({"backend": backend}))
        return
    if backend == "none":
        print("no PDF backend (poppler or PyMuPDF); run scripts/setup.py", file=sys.stderr)
        raise SystemExit(2)
    if a.cmd == "scout":
        paths = scout(a.pdf, a.first, a.last, a.out_dir, a.dpi, backend)
        print(json.dumps({"backend": backend, "dpi": a.dpi, "crop_scale": CROP_DPI / a.dpi, "pages": paths}, indent=2))
    else:
        crop(a.pdf, a.page, a.x, a.y, a.w, a.h, a.out, a.dpi, backend)
        print(json.dumps({"backend": backend, "dpi": a.dpi, "out": a.out}))


if __name__ == "__main__":
    main()
