#!/usr/bin/env python3
"""Check the tools read-paper needs. Works on Linux, macOS and Windows.

  python3 scripts/setup.py           human-readable status and install hints
  python3 scripts/setup.py --json    machine-readable status

Backends, in order of preference:
  1. poppler  (pdftoppm, pdftotext, pdfinfo)   fast, exact
  2. PyMuPDF  (import fitz)                     pure pip install
With neither, notes are still produced, just without figures.

This script never installs anything. It only prints the command to run.
"""
import json
import platform
import shutil
import sys


def main() -> None:
    poppler = bool(shutil.which("pdftoppm") and shutil.which("pdftotext"))
    try:
        import fitz  # noqa: F401
        pymupdf = True
    except ImportError:
        pymupdf = False

    system = platform.system()
    if system == "Darwin":
        hint_poppler = "brew install poppler"
    elif system == "Windows":
        hint_poppler = "winget install oschwartz10612.Poppler   (or: choco install poppler / scoop install poppler); then add its bin folder to PATH"
    elif shutil.which("apt-get"):
        hint_poppler = "sudo apt-get install -y poppler-utils"
    elif shutil.which("dnf"):
        hint_poppler = "sudo dnf install -y poppler-utils"
    elif shutil.which("pacman"):
        hint_poppler = "sudo pacman -S poppler"
    else:
        hint_poppler = "install poppler-utils with your package manager"
    py = "python" if system == "Windows" else "python3"
    hint_pymupdf = f"{py} -m pip install --user pymupdf"

    backend = "poppler" if poppler else ("pymupdf" if pymupdf else "none")
    status = {
        "backend": backend, "poppler": poppler, "pymupdf": pymupdf,
        "python": sys.version.split()[0], "python_cmd": py, "os": system,
        "install_poppler": hint_poppler, "install_pymupdf": hint_pymupdf,
    }
    if "--json" in sys.argv[1:]:
        print(json.dumps(status))
        return
    print("read-paper setup check")
    for k in ("os", "python", "poppler", "pymupdf", "backend"):
        print(f"  {k:8}: {status[k]}")
    if backend == "none":
        print("\nNo PDF backend found. Notes will be written without figures until one is installed:")
        print(f"  poppler (recommended): {hint_poppler}")
        print(f"  PyMuPDF (fallback)   : {hint_pymupdf}")
    elif backend == "pymupdf":
        print(f"\nUsing PyMuPDF. poppler is faster for large PDFs: {hint_poppler}")


if __name__ == "__main__":
    main()
