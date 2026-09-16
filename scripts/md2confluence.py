#!/usr/bin/env python3
"""Convert a read-paper note (standard Markdown) to the Confluence HTML+ body the Atlassian
MCP server accepts (createConfluencePage / updateConfluencePage with contentFormat=html).

  python3 scripts/md2confluence.py note.md --out body.html [--figures figures.json]

figures.json maps image paths as written in the note to the <figure ...> snippet printed
by confluence_upload.py:
  {"figures/fig1-overview.png": "<figure data-type=\\"media-single\\" ...>...</figure>"}
Without a mapping, each image becomes a {{FIG:<path>|<caption>}} placeholder to replace later.

Handles: front matter (removed), headings (#/##/###), bullet/numbered lists (one level),
pipe tables, > blockquote -> info panel, $$ blocks -> easy-math-block macro, $x$ inline math
(best-effort LaTeX -> unicode + sub/sup), `code`, **bold**, *italic*, [text](url) links.
Spot-check the output: it is a best-effort converter, not a full Markdown/LaTeX parser.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _md import IMAGE, INLINE_MATH, split_front_matter, tex_inline_html  # noqa: E402


def inline(s: str) -> str:
    holds = []

    def hold(x):
        holds.append(x)
        return f"\x00{len(holds) - 1}\x00"

    s = INLINE_MATH.sub(lambda m: hold(tex_inline_html(m.group(1))), s)
    s = re.sub(r"`([^`]+)`", lambda m: hold("<code>" + html.escape(m.group(1)) + "</code>"), s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               lambda m: hold(f'<a href="{m.group(2)}">{html.escape(m.group(1))}</a>'), s)
    s = html.escape(s, quote=False)
    s = s.replace(r"\*", "\x01")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", s)
    s = s.replace("\x01", "*")
    return re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], s)


def math_block(tex: str) -> str:
    params = json.dumps({"macroParams": {"body": {"value": tex.strip()}}}, ensure_ascii=False).replace("'", "&#39;")
    return ('<div data-type="extension" data-extension-key="easy-math-block" '
            'data-extension-type="com.atlassian.confluence.macro.core" '
            f"data-parameters='{params}'></div>")


def convert(body: str, figures: dict):
    out, placeholders = [], []
    lines = body.split("\n")
    i, list_type = 0, None

    def close_list():
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1; continue
        if line.strip().startswith("$$"):
            buf = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("$$"):
                buf.append(lines[i]); i += 1
            i += 1
            close_list(); out.append(math_block("\n".join(buf))); continue
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip()); i += 1
            close_list()
            out.append('<div data-type="panel-info"><p>' + inline(" ".join(b for b in buf if b)) + "</p></div>")
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            close_list()
            h = ["<table><tbody>"]
            for ri, r in enumerate(rows):
                tag = "th" if ri == 0 else "td"
                h.append("<tr>" + "".join(f"<{tag}><p>{inline(c)}</p></{tag}>" for c in r) + "</tr>")
            h.append("</tbody></table>")
            out.append("".join(h)); continue
        m = re.match(r"^(#{1,3}) (.*)$", line)
        if m:
            close_list(); out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>"); i += 1; continue
        m = IMAGE.match(line)
        if m:
            cap, path = m.group(1), m.group(2)
            close_list()
            if path in figures:
                snippet = figures[path]
                if cap and "<figcaption>" not in snippet:
                    snippet = snippet.replace("</figure>", f"<figcaption>{inline(cap)}</figcaption></figure>")
                out.append(snippet)
            else:
                placeholders.append(path)
                out.append(f"{{{{FIG:{path}|{inline(cap)}}}}}")
            i += 1; continue
        m = re.match(r"^[-*] (.*)$", line)
        if m:
            if list_type != "ul":
                close_list(); out.append("<ul>"); list_type = "ul"
            out.append(f"<li><p>{inline(m.group(1))}</p></li>"); i += 1; continue
        m = re.match(r"^\d+\. (.*)$", line)
        if m:
            if list_type != "ol":
                close_list(); out.append("<ol>"); list_type = "ol"
            out.append(f"<li><p>{inline(m.group(1))}</p></li>"); i += 1; continue
        # paragraph: join consecutive non-empty plain lines
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |[-*] |\d+\. |\||>|!\[|\$\$)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        close_list(); out.append(f"<p>{inline(' '.join(buf))}</p>")
    close_list()
    return "\n".join(out), placeholders


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("note"); p.add_argument("--out", required=True); p.add_argument("--figures")
    a = p.parse_args()
    meta, body = split_front_matter(Path(a.note).read_text(encoding="utf-8"))
    figures = json.loads(Path(a.figures).read_text(encoding="utf-8")) if a.figures else {}
    out, placeholders = convert(body, figures)
    Path(a.out).write_text(out, encoding="utf-8")
    print(json.dumps({"out": a.out, "title": meta.get("title"), "chars": len(out),
                      "math_blocks": out.count("easy-math-block"), "tables": out.count("<table>"),
                      "panels": out.count("panel-info"), "figures": out.count("<figure"),
                      "placeholders": placeholders}))


if __name__ == "__main__":
    main()
