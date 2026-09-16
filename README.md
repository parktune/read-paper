# read-paper

A [Claude Code](https://claude.com/claude-code) plugin that turns a paper into a note you
will actually reopen.

```
/read-paper https://arxiv.org/pdf/1706.03762
/read-paper ~/Downloads/some-paper.pdf
```

Give it an arXiv link, any PDF URL, or a local file. It asks where to save, reads the whole
paper, crops the two or three figures that carry the argument, and writes a structured
Markdown note plus a set of concept notes that accumulate understanding across papers.
Everything is local files. No Notion, Confluence, or any other account is involved.

## What you get

```
~/Downloads/ReadPaper/                  (or wherever you chose)
├── .read-paper.json                    domain, language, backend for this directory
├── pdfs/
│   └── attention-is-all-you-need.pdf
├── attention-is-all-you-need/
│   ├── attention-is-all-you-need.md    the note
│   └── figures/
│       ├── fig1-architecture.png
│       └── fig2-bleu-table.png
└── concepts/
    ├── self-attention.md               cross-paper notes, [[wikilinked]]
    └── positional-encoding.md
```

The note opens with the **publication date before the read date** — how recent the work
is matters more than when you read it:

```
📄 Published: **2017-06-12** (arXiv v1 · v7 2023-08-02 · NeurIPS 2017) · Source: [abs](…) · [pdf](…) · Google Brain · Google Research · Read: 2026-09-16

> 💡 One line that states what changed, compared with what, by how much.

# Summary
# Background and Motivation
# Method
# Results            ← key numbers as a table against the strongest baseline
# Limitations
# Personal Take      ← written from *your* research domain, in first person
# Related Concepts   ← [[links]] into concepts/
```

Notes and concept files are plain Markdown with `[[wikilinks]]`, so the directory opens
directly as an [Obsidian](https://obsidian.md) vault.

## Install

```
claude plugin marketplace add pty2792/read-paper
claude plugin install read-paper@read-paper
```

Then, for figure cropping and text extraction, one of:

- **poppler** (recommended): `brew install poppler` · `sudo apt-get install poppler-utils` · `choco install poppler`
- **PyMuPDF** (fallback): `python3 -m pip install --user pymupdf`

Run `scripts/setup.sh` from the plugin directory to see what is detected. Without either,
the note is still written, just without figures. The skill will offer the install command
on first use but never runs it without your say-so.

## How a run goes

1. **Where to save?** — a question with `~/Downloads/ReadPaper/` recommended, your recent
   directories, a project-local directory if one fits, or a path you type. On the first run
   it also asks your research domain (for the Personal Take section) and the note language
   (default: whatever language you are talking in).
2. **Fetch** — downloads the PDF; for arXiv it reads title, authors, submission history
   (v1 date and latest version) and the comments line from the abs page. A local PDF with
   an arXiv stamp gets the same treatment.
3. **Read** — the full text, not the abstract.
4. **Figures** — renders candidate pages at low resolution, picks the figures, crops them at 200 DPI.
5. **Write** — the note, then the concept notes it touches (create or update, never append-only).
6. **Remember** — the directory, domain and language, so next time they are one click away.

## Configuration

| File | Holds |
|---|---|
| `~/.config/read-paper/config.json` | recent directories, default domain and language |
| `<save-dir>/.read-paper.json` | domain, note language, figure backend for that directory |

Both are plain JSON you can edit. Delete them to get the first-run questions again.

## Publishing to Notion or Confluence

Not built in, on purpose: everyone's workspace is different. If you have a Notion or
Atlassian MCP server connected in Claude Code, ask it to upload the note — the Markdown
maps straight onto a Notion page or a Confluence page, and the figures go through that
server's file-upload tool. The first line and section structure carry over unchanged.

## Scripts

All in `scripts/`, all print JSON, all usable on their own:

| Script | Purpose |
|---|---|
| `setup.sh [--json]` | detect poppler / PyMuPDF, print install hints (never installs) |
| `config.py options\|show\|record\|tags` | read and write the two config files; list tags already in use |
| `fetch_paper.py <ref> --dir DIR [--slug S] [--offline]` | download the PDF, arXiv metadata, slug |
| `pdf_text.py <pdf> [--pages a-b] [--out f]` | text extraction (layout-preserving) |
| `pdf_figures.py scout\|crop` | page thumbnails at 80 DPI; crops at 200 DPI |

Python 3.10+ and the standard library only; the PDF work goes through poppler or PyMuPDF.

## License

MIT
