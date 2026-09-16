#!/usr/bin/env python3
"""Convert a read-paper note (standard Markdown) to Notion-flavored Markdown.

  python3 scripts/md2notion.py note.md --uploads uploads.json --out body.md [--meta meta.json]

uploads.json maps image paths as written in the note to Notion file-upload ids:
  {"figures/fig1-overview.png": "3f2a...-...-..."}
Images without a mapping are dropped (their caption is kept as an italic line) and listed
in the summary printed to stderr.

Conversions:
  front matter          removed; written to --meta as JSON (title, venue, published, read, tags, source)
  > 💡 text             -> <callout icon="💡" color="blue_bg"> ... </callout>
  | pipe | table |      -> <table header-row="true"> <tr><td>..</td></tr> </table>
  $x$ inline math       -> $`x`$        ($$ blocks unchanged)
  ![cap](figures/x.png) -> ![cap](file-upload://<id>)
Everything else (headings, lists, bold, links, code) is passed through.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _md import IMAGE, INLINE_MATH, split_front_matter  # noqa: E402


def convert(body: str, uploads: dict):
    out, missing, used = [], [], 0
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # $$ blocks pass through untouched
        if line.strip().startswith("$$"):
            out.append(line); i += 1
            while i < len(lines) and not lines[i].strip().startswith("$$"):
                out.append(lines[i]); i += 1
            if i < len(lines):
                out.append(lines[i]); i += 1
            continue
        # blockquote callout
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip()); i += 1
            text = " ".join(b for b in buf if b)
            icon = "💡"
            m = re.match(r"^(\S)\s+(.*)$", text)
            if m and not m.group(1).isalnum():
                icon, text = m.group(1), m.group(2)
            out += [f'<callout icon="{icon}" color="blue_bg">', INLINE_MATH.sub(r"$`\1`$", text), "</callout>"]
            continue
        # pipe table
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<table header-row="true">')
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{INLINE_MATH.sub(chr(36) + '`' + chr(92) + '1`' + chr(36), c)}</td>" for c in r) + "</tr>")
            out.append("</table>")
            continue
        m = IMAGE.match(line)
        if m:
            cap, path = m.group(1), m.group(2)
            if path in uploads:
                used += 1
                out.append(f"![{cap}](file-upload://{uploads[path]})")
            else:
                missing.append(path)
                if cap:
                    out.append(f"*{cap}*")
            i += 1
            continue
        out.append(INLINE_MATH.sub(r"$`\1`$", line))
        i += 1
    return "\n".join(out), missing, used


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("note")
    p.add_argument("--uploads", help="JSON file: image path -> file-upload id")
    p.add_argument("--out", required=True)
    p.add_argument("--meta")
    a = p.parse_args()
    src = Path(a.note).read_text(encoding="utf-8")
    meta, body = split_front_matter(src)
    uploads = json.loads(Path(a.uploads).read_text(encoding="utf-8")) if a.uploads else {}
    out, missing, used = convert(body, uploads)
    Path(a.out).write_text(out, encoding="utf-8")
    if a.meta:
        Path(a.meta).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": a.out, "chars": len(out), "figures": used,
                      "missing_figures": missing, "callouts": out.count("<callout"), "tables": out.count("<table")}))


if __name__ == "__main__":
    main()
