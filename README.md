# read-paper

A [Claude Code](https://claude.com/claude-code) plugin that turns a paper into a note you
will actually reopen. Linux, macOS and Windows.

```
/read-paper:setup                                   once
/read-paper https://arxiv.org/pdf/1706.03762        every paper
/read-paper ~/Downloads/some-paper.pdf
```

Give it an arXiv link, any PDF URL, or a local file. It asks where to save, reads the whole
paper, crops the four or five figures that carry the argument, writes a structured Markdown
note (2,000–3,000 words by default), updates
the concept notes the paper touches, and — if you configured it — publishes the same note to
Notion and/or Confluence.

The notes are plain files in a folder you choose. No git, no database, no account required.

## What you get

```
~/Documents/ReadPaper/                  (or wherever you chose)
├── .read-paper.json                    per-directory overrides (optional)
├── pdfs/
│   └── attention-is-all-you-need.pdf
├── attention-is-all-you-need/
│   ├── attention-is-all-you-need.md    the note
│   └── figures/
│       ├── fig1-architecture.png
│       └── fig2-bleu-table.png
└── concepts/                           cross-paper notes, [[wikilinked]]
    ├── self-attention.md               (can live elsewhere: see setup)
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
claude plugin marketplace add parktune/read-paper
claude plugin install read-paper@read-paper
```

Python 3.10+ is required. For figure cropping and text extraction, one of:

- **poppler** (recommended): `brew install poppler` · `sudo apt-get install poppler-utils` · `winget install oschwartz10612.Poppler`
- **PyMuPDF** (fallback): `python3 -m pip install --user pymupdf`

Without either, the note is still written, just without figures. Setup offers the install
command but never runs it without your say-so.

## Setup

`/read-paper:setup` asks, once:

| Setting | Default |
|---|---|
| Research domain (drives the Personal Take section) | — |
| Default save directory | `~/Documents/ReadPaper` |
| Concept-notes directory | `<save-dir>/concepts` |
| Note language | same as the conversation |
| Figures per note · note length | 4–5 · 2,000–3,000 words |
| Publish to Notion · Confluence | off |

For **Notion** you paste a Papers database URL, or let setup create one (Name, Source,
Published, Read, Tags, Summary, Confluence). For **Confluence** you paste the parent page or
folder URL; figures need an Atlassian API token (the MCP server cannot upload attachments),
which you can store in the config file or provide as `ATL_SITE` / `ATL_EMAIL` / `ATL_TOKEN`.
Each target has a default — publish on every run, or only when you ask — and you can override
it in plain words on any run ("also put this one in Confluence").

Both need the matching MCP server connected in Claude Code (`claude mcp add --transport http
-s user notion https://mcp.notion.com/mcp`, `claude mcp add --transport http -s user atlassian
https://mcp.atlassian.com/v1/sse`). Without it the target is skipped and the report says so.

Settings live in one JSON file you can edit by hand — `~/.config/read-paper/config.json`
(Linux/macOS) or `%APPDATA%\read-paper\config.json` (Windows) — with optional per-directory
overrides in `<save-dir>/.read-paper.json`. Re-run `/read-paper:setup` any time; it shows the
current values. If you run `/read-paper` before setup, setup runs first and the paper follows.

## How a run goes

1. **Where to save?** — one question: your default (recommended), recent directories, a
   project-local directory if one fits, or a path you type.
2. **Fetch** — downloads the PDF; for arXiv it reads title, authors, submission history
   (v1 date and latest version) and the comments line from the abs page. A local PDF with
   an arXiv stamp gets the same treatment.
3. **Read** — the full text, not the abstract.
4. **Figures** — renders candidate pages at low resolution, picks the figures, crops them at 200 DPI.
5. **Write** — the note, then the concept notes it touches (create or update, never append-only).
6. **Publish** — Notion and/or Confluence per your defaults; failures never touch the local note.

## Scripts

All in `scripts/`, all print JSON, all usable on their own, all cross-platform Python:

| Script | Purpose |
|---|---|
| `setup.py [--json]` | detect poppler / PyMuPDF, print install hints (never installs) |
| `config.py options\|show\|set\|record\|tags` | read and write settings (`set key=value`, dotted keys nest) |
| `fetch_paper.py <ref> --dir DIR [--slug S] [--offline]` | download the PDF, arXiv metadata, slug |
| `pdf_text.py <pdf> [--pages a-b] [--out f]` | text extraction (layout-preserving) |
| `pdf_figures.py scout\|crop` | page thumbnails at 80 DPI; crops at 200 DPI |
| `md2notion.py note.md --uploads map.json --out body.md` | note → Notion-flavored Markdown |
| `md2confluence.py note.md --out body.html [--figures map.json]` | note → Confluence HTML+ (math macros, panels, tables) |
| `confluence_upload.py <page-id> <png>` | attach a figure via REST, print the `<figure>` snippet |

## License

MIT
