# read-paper — Specification

Status: clarified requirement, 2026-09-16. This file is the reference for the implementation.

## Goal

A Claude Code plugin, `read-paper`, that turns a paper (PDF URL or local path) into a
structured Markdown note with cropped figures, saved to a directory the user chooses,
plus a set of cross-paper concept notes. It generalizes a private Notion/Confluence
workflow into a local-file workflow that anyone can use without any account.

## Origin

The skill ports these conventions from the author's private research workflow:

- First line states the **publication date before the read date** (recency matters more).
- Fixed section structure with a one-line thesis up front.
- Key figures (2–3) cropped from the PDF, each with a caption.
- Math in LaTeX; core numbers in tables.
- A "Personal Take" section written from the reader's own research domain
  ("how does this apply to my problem"), not generic critique.
- Concept notes (`concepts/`) that accumulate understanding across papers and link to
  each other with `[[wikilinks]]`.
- Notes are a by-product of reading — no separate "summary session".

## Packaging and distribution

- One GitHub repository, `read-paper`, that is both the plugin and its marketplace:
  `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- Install: `claude plugin marketplace add <owner>/read-paper` then
  `claude plugin install read-paper`.
- Contents: `skills/read-paper/SKILL.md`, `scripts/` (setup, PDF text extraction,
  figure crop, config read/write), `README.md`, `LICENSE`.
- All documentation, skill text, and script comments are in **English**.

## Invocation

```
/read-paper [article-url | article-filepath]
```

Examples:

```
/read-paper https://arxiv.org/pdf/1706.03762
/read-paper https://arxiv.org/abs/1706.03762
/read-paper ~/Downloads/attention-is-all-you-need.pdf
```

Exactly one positional argument. With no argument the skill asks for the URL or path
(`AskUserQuestion` with free text) instead of failing.

Input handling:

- arXiv URL (abs or pdf): download the PDF; read title, authors, and **v1 date** from the
  arXiv abs page; record the arXiv id.
- Other URL: download the PDF; publication date from the PDF first page or user input.
- Local path: use as is; publication date from the PDF first page (arXiv stamp) or user input.

## Step 1 — ask where to save (mandatory tool call)

The first action is an `AskUserQuestion` call asking for the save directory. Options,
in this order:

1. `~/Downloads/ReadPaper/` — **(Recommended)**, always present.
2. The most recently used directory from the config file — only if one exists and differs from 1.
3. A directory that fits the current project context (e.g. a `papers/` or `notes/` dir
   in the working repo) — only if such a context exists.
4. Free text via the built-in "Other" option.

On the **first run** (no config found) the same call also asks:

- Research domain (free text with examples: "computational biology", "recommender systems",
  "speech recognition"). Used for the Personal Take section.
- Note language: default "same as the conversation"; may be fixed to one language.

Never skip the question, even when a config exists — the config only changes the options.

## Configuration

- Per-directory: `<save-dir>/.read-paper.json`
- Global fallback: `~/.config/read-paper/config.json`
- Fields: `last_dir`, `recent_dirs` (max 5), `domain`, `note_language`, `figure_backend`.
- Written by `scripts/config.py` so the skill and scripts share one reader/writer.

## Output layout

```
<save-dir>/
  .read-paper.json
  pdfs/<slug>.pdf
  <slug>/
    <slug>.md
    figures/fig1-<short-name>.png
    figures/fig2-<short-name>.png
  concepts/
    <concept-name>.md
```

`<slug>` is the kebab-case short name of the paper (e.g. `attention-is-all-you-need`, `resnet`).

## Note format (`<slug>/<slug>.md`)

Front matter:

```yaml
---
title: "<full title including subtitle>"
venue: "<venue or arXiv id> (<institution> <year>)"
published: YYYY-MM-DD
read: YYYY-MM-DD
tags: [tag1, tag2]
source: <url>
---
```

Body, in the language chosen (default: the conversation language):

1. First paragraph:
   `📄 Published: **YYYY-MM-DD** (arXiv vN or venue) · Source: <links> · <institutions> · Read: YYYY-MM-DD`
   Publication date **before** read date.
2. One-line thesis as a blockquote callout (`> 💡 ...`).
3. Sections: `# Summary` / `# Background and Motivation` / `# Method` (with `##`) /
   `# Results` (key numbers as tables) / `# Limitations` /
   `# Personal Take` (from the configured domain: what transfers to my problem, what does not) /
   `# Related Concepts` (list of `[[concept-name]]` links to `concepts/`).
4. Math: `$$` blocks for display, `$...$` inline. Figures: `![caption](figures/figN-name.png)`
   with a caption line; 2–3 key figures.
5. Depth: each of Summary, Method, Results, Limitations, Personal Take is substantive
   (roughly 1,500–2,500 words total, not an abstract rewrite).

Tags: reuse tags already present across existing notes in `<save-dir>` before inventing new ones.

## Concept notes (`concepts/`)

- Before writing the paper note, scan existing `concepts/*.md` and identify which concepts the
  paper touches.
- Create or update one file per concept. A concept note is **not** a copy of the paper
  summary; it holds understanding that cuts across papers and cites papers by slug
  (`[[<slug>]]`). Concepts link to each other with `[[concept-name]]`.
- Obsidian-compatible: plain `[[wikilinks]]`, no plugin-specific syntax.

## Figures and PDF text — dependencies

`scripts/setup.sh` (run on install or first use):

1. Check for poppler (`pdftoppm`, `pdftotext`). If missing, print the install command for the
   detected OS (`apt install poppler-utils`, `brew install poppler`, `choco install poppler`)
   and **ask** before installing. Never install without explicit approval.
2. If the user declines or install fails, try PyMuPDF (`python -c "import fitz"`); offer
   `pip install pymupdf` under the same rule.
3. If neither is available, continue: produce the Markdown note without figures and say so.

`scripts/pdf_text.py` and `scripts/crop_figure.py` use whichever backend is available
(poppler first, then PyMuPDF) and expose the same CLI either way. Crop coordinates are
given in points at 200 DPI, as in the original pipeline.

## Notion / Confluence

Not automated. `README.md` contains one short section: if a Notion or Atlassian MCP server
is connected, the generated Markdown can be uploaded as is (figures via the server's file
upload), and the first-line and section conventions carry over unchanged.

## Out of scope

- Publishing automation, Notion database schemas, Confluence storage-format conversion.
- Any personal or company-specific identifiers.
- Non-English documentation.

## Constraints

- The save-directory question is always a tool call (`AskUserQuestion`), never plain text.
- No installation, download outside the chosen directory, or network call beyond fetching
  the paper without the user's approval.
- Non-ASCII strings in tool-call parameters are written as literal UTF-8, never `\uXXXX`.
- The author's existing private workflow (`~/work/research`) is left untouched.

## Success criteria

On a fresh machine and account:

1. `claude plugin marketplace add <owner>/read-paper` + install succeeds.
2. `/read-paper https://arxiv.org/pdf/<id>` first asks for the save directory (and domain on
   first run).
3. The chosen directory receives `pdfs/`, `<slug>/<slug>.md`, `<slug>/figures/*.png`,
   and created/updated `concepts/*.md`.
4. A second run offers the previous directory as an option.
5. Without poppler and PyMuPDF the note is still produced, minus figures, with a clear message.

## Decisions log

| Question | Decision |
|---|---|
| Packaging | Plugin (skill + scripts); the GitHub repo doubles as marketplace |
| Notion / Confluence | Local Markdown only; README note that MCP upload is possible |
| Concept notes | Included, under `<save-dir>/concepts/` |
| Note language | Follows the conversation; docs in English |
| Remembering paths | Config file + recent directory offered as an option |
| Personal Take domain | Asked on first run, stored in config |
| PDF dependencies | poppler first (setup offers install), PyMuPDF fallback, else no figures |
| Names | repo `read-paper`, skill `/read-paper`, default dir `~/Downloads/ReadPaper/` |
