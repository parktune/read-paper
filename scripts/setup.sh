#!/usr/bin/env bash
# Check the tools read-paper needs for PDF text and figure extraction.
#
#   scripts/setup.sh          human-readable status and install hints
#   scripts/setup.sh --json   machine-readable status
#
# Backends, in order of preference:
#   1. poppler  (pdftoppm, pdftotext, pdfinfo)  — fast, exact
#   2. PyMuPDF  (python3 -c "import fitz")      — pure pip install
# With neither, notes are still produced, just without figures.
#
# This script never installs anything. It only prints the command to run.
set -uo pipefail

have() { command -v "$1" >/dev/null 2>&1; }

poppler=false; pymupdf=false; python=false
have pdftoppm && have pdftotext && poppler=true
have python3 && python=true
$python && python3 -c "import fitz" >/dev/null 2>&1 && pymupdf=true

os="$(uname -s)"
case "$os" in
  Darwin) hint_poppler="brew install poppler" ;;
  Linux)
    if have apt-get; then hint_poppler="sudo apt-get install -y poppler-utils"
    elif have dnf; then hint_poppler="sudo dnf install -y poppler-utils"
    elif have pacman; then hint_poppler="sudo pacman -S poppler"
    else hint_poppler="install poppler-utils with your package manager"; fi ;;
  MINGW*|MSYS*|CYGWIN*) hint_poppler="choco install poppler   (or: scoop install poppler)" ;;
  *) hint_poppler="install poppler for your OS" ;;
esac
hint_pymupdf="python3 -m pip install --user pymupdf"

backend=none
$poppler && backend=poppler
! $poppler && $pymupdf && backend=pymupdf

if [[ "${1:-}" == "--json" ]]; then
  printf '{"backend":"%s","poppler":%s,"pymupdf":%s,"python3":%s,"os":"%s","install_poppler":"%s","install_pymupdf":"%s"}\n' \
    "$backend" "$poppler" "$pymupdf" "$python" "$os" "$hint_poppler" "$hint_pymupdf"
  exit 0
fi

echo "read-paper setup check"
echo "  python3 : $python"
echo "  poppler : $poppler"
echo "  PyMuPDF : $pymupdf"
echo "  backend : $backend"
if [[ $backend == none ]]; then
  echo
  echo "No PDF backend found. Notes will be written without figures until one is installed:"
  echo "  poppler (recommended): $hint_poppler"
  echo "  PyMuPDF (fallback)   : $hint_pymupdf"
elif [[ $backend == pymupdf ]]; then
  echo
  echo "Using PyMuPDF. poppler is faster for large PDFs: $hint_poppler"
fi
