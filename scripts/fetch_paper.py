#!/usr/bin/env python3
"""Resolve a paper reference (URL or local path), download the PDF, collect metadata.

  scripts/fetch_paper.py https://arxiv.org/pdf/1706.03762 --dir ~/Downloads/ReadPaper
  scripts/fetch_paper.py ~/Downloads/some-paper.pdf       --dir ~/Downloads/ReadPaper
  scripts/fetch_paper.py <ref> --dir DIR --slug my-slug    override the folder name
  scripts/fetch_paper.py <ref> --dir DIR --offline         never touch the network

The PDF lands in <dir>/pdfs/<slug>.pdf; the note goes to <dir>/papers/<slug>/ (note_dir). Output is one JSON object:
  slug, pdf, title, authors, published (v1 date, ISO), latest_version, latest_date,
  arxiv_id, url_abs, url_pdf, comments, primary_category, source_kind, warnings

For arXiv references the metadata comes from the abs page (title, authors, submission
history, comments such as "Accepted at NeurIPS 2017"). For a local PDF the first page is
scanned for an arXiv stamp so the same metadata can be fetched. Otherwise the PDF's own
metadata and the filename are used, and `published` is left null for you to fill in.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _backend import detect  # noqa: E402

UA = "read-paper/0.1 (+https://github.com/parktune/read-paper)"
ARXIV_ID = re.compile(r"(?:(?<=/)|^|arXiv:)((?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", re.I)
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def warn(msgs: list, m: str) -> None:
    msgs.append(m)
    print(f"warning: {m}", file=sys.stderr)


def http_get(url: str, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", errors="replace")


def arxiv_id_from(text: str):
    m = ARXIV_ID.search(text)
    return re.sub(r"v\d+$", "", m.group(1)) if m else None


def parse_date(s: str):
    m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", s)
    if not m:
        return None
    return datetime(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))).date().isoformat()


def arxiv_metadata(aid: str, warnings: list) -> dict:
    page = http_get(f"https://arxiv.org/abs/{aid}")
    meta = lambda name: [html.unescape(x) for x in re.findall(rf'<meta name="{name}" content="([^"]*)"', page)]
    title = (meta("citation_title") or [""])[0]
    authors = meta("citation_author")
    # Submission history: "[v1] Mon, 12 Jun 2017 17:57:34 UTC (1,102 KB)"
    versions = re.findall(r"\[v(\d+)\](?:</a>)?(?:</strong>)?\s*\w+,\s*(\d{1,2} \w{3} \d{4})", page)
    published = latest_date = None
    latest_version = None
    if versions:
        versions.sort(key=lambda v: int(v[0]))
        published = parse_date(versions[0][1])
        latest_version, latest_date = int(versions[-1][0]), parse_date(versions[-1][1])
    else:
        warn(warnings, "could not parse submission history; published date unknown")
    comments = re.search(r'<td class="tablecell comments[^"]*">(.*?)</td>', page, re.S)
    primary = re.search(r'<span class="primary-subject">(.*?)</span>', page)
    return {
        "title": " ".join(title.split()),
        "authors": authors,
        "published": published,
        "latest_version": latest_version,
        "latest_date": latest_date,
        "arxiv_id": aid,
        "url_abs": f"https://arxiv.org/abs/{aid}",
        "url_pdf": f"https://arxiv.org/pdf/{aid}",
        "comments": " ".join(html.unescape(re.sub(r"<[^>]+>", "", comments.group(1))).split()) if comments else None,
        "primary_category": html.unescape(primary.group(1)) if primary else None,
    }


def slugify(title: str, fallback: str) -> str:
    head = title.split(":")[0] if ":" in title and len(title.split(":")[0].split()) <= 4 else title
    s = unicodedata.normalize("NFKD", head).encode("ascii", "ignore").decode()
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", s.lower()).split() if w]
    words = words[:6]
    return "-".join(words) or fallback


def pdf_first_page_text(pdf: str) -> str:
    backend = detect()
    try:
        if backend == "poppler":
            return subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, "-"], capture_output=True, text=True).stdout
        if backend == "pymupdf":
            import fitz
            with fitz.open(pdf) as doc:
                return doc[0].get_text("text")
    except Exception:
        pass
    return ""


def pdf_info_title(pdf: str):
    if shutil.which("pdfinfo"):
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"^Title:\s+(.+)$", out, re.M)
        t = m.group(1).strip() if m else ""
        # Reject the junk producers leave behind ("Subject:", "Microsoft Word - draft.docx", "untitled")
        if len(t.split()) >= 3 and not t.endswith(":") and not re.search(r"\.(docx?|tex|pdf)$|microsoft word|untitled", t, re.I):
            return t
    return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ref", help="URL or local PDF path")
    p.add_argument("--dir", required=True, help="save directory (PDF goes to <dir>/pdfs/)")
    p.add_argument("--slug")
    p.add_argument("--offline", action="store_true")
    a = p.parse_args()

    warnings: list = []
    save_dir = Path(a.dir).expanduser().resolve()
    pdf_dir = save_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    result = {"title": None, "authors": [], "published": None, "latest_version": None, "latest_date": None,
              "arxiv_id": None, "url_abs": None, "url_pdf": None, "comments": None, "primary_category": None}

    is_url = re.match(r"https?://", a.ref) is not None
    local_src = None if is_url else Path(a.ref).expanduser().resolve()
    if local_src and not local_src.is_file():
        sys.exit(f"error: file not found: {local_src}")

    aid = arxiv_id_from(a.ref) if is_url and "arxiv.org" in a.ref else None
    if local_src:
        aid = arxiv_id_from(pdf_first_page_text(str(local_src)))
    source_kind = "arxiv" if aid else ("url" if is_url else "local")

    if aid and not a.offline:
        try:
            result.update(arxiv_metadata(aid, warnings))
        except Exception as e:  # network down, page layout changed, ...
            warn(warnings, f"arXiv metadata fetch failed ({e}); fill in metadata by hand")
            result["arxiv_id"] = aid
    elif aid:
        result["arxiv_id"] = aid

    # Decide the slug before downloading so the PDF gets its final name.
    fallback = (local_src.stem if local_src else (aid or Path(a.ref).stem or "paper")).lower()
    tmp_title = result["title"]
    if not tmp_title and local_src:
        tmp_title = pdf_info_title(str(local_src))
    slug = a.slug or slugify(tmp_title or "", re.sub(r"[^a-z0-9]+", "-", fallback).strip("-"))
    pdf_path = pdf_dir / f"{slug}.pdf"

    if local_src:
        if local_src != pdf_path:
            shutil.copy2(local_src, pdf_path)
    else:
        if a.offline:
            sys.exit("error: --offline given but the reference is a URL")
        url = result["url_pdf"] if aid else a.ref
        data = http_get(url, binary=True)
        if not data.startswith(b"%PDF"):
            sys.exit(f"error: {url} did not return a PDF")
        pdf_path.write_bytes(data)
        if not aid:
            result["url_pdf"] = a.ref

    if not result["title"]:
        result["title"] = pdf_info_title(str(pdf_path)) or slug.replace("-", " ").title()
        warn(warnings, "title/authors/published date were not fetched; confirm them from the PDF's first page")

    result.update({"slug": slug, "pdf": str(pdf_path), "source_kind": source_kind, "warnings": warnings,
                   "note_dir": str(save_dir / "papers" / slug), "read": datetime.now().date().isoformat()})
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
