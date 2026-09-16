"""Pick a PDF backend: poppler CLI tools if present, else PyMuPDF, else none."""
import shutil


def detect() -> str:
    if shutil.which("pdftoppm") and shutil.which("pdftotext"):
        return "poppler"
    try:
        import fitz  # noqa: F401  (PyMuPDF)
        return "pymupdf"
    except ImportError:
        return "none"


def page_count(pdf: str, backend: str) -> int:
    if backend == "poppler" and shutil.which("pdfinfo"):
        import re
        import subprocess
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        if m:
            return int(m.group(1))
    if backend in ("poppler", "pymupdf"):
        try:
            import fitz
            with fitz.open(pdf) as doc:
                return doc.page_count
        except ImportError:
            pass
    return 0
