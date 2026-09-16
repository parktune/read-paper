# read-paper — Specification

Status: clarified requirement, 2026-09-16 (setup and publishing added the same day). This file is the reference for the implementation.

## Goal

A Claude Code plugin, `read-paper`, that turns a paper (PDF URL or local path) into a
structured Markdown note with cropped figures, saved to a directory the user chooses,
plus a set of cross-paper concept notes. It generalizes a private Notion/Confluence
workflow into a local-file workflow that anyone can use without any account.

## Origin

The skill ports these conventions from the author's private research workflow:

- First line states the **publication date before the read date** (recency matters more).
- Fixed section structure with a one-line thesis up front.
- Key figures (4–5) cropped from the PDF, each with a caption.
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
- Runs on Linux, macOS and Windows: every script is Python (no shell scripts), paths go
  through `pathlib`, no symlinks, `python3` with a `python` fallback on Windows.
- No git. The plugin exists so that notes do **not** have to live in a git repository; it
  never commits, and never assumes the save directory is a repo.

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

## Setup: `/read-paper:setup` (one-time, re-runnable)

A second skill collects every preference so `/read-paper` never asks about them. Questions,
each via `AskUserQuestion`, showing the current value when re-run:

1. Research domain (free text) — drives the Personal Take section.
2. Default save directory — `~/Documents/ReadPaper` recommended.
3. Note language — same as the conversation (default) / English / other.
4. Concept-notes directory — `<save-dir>/concepts` by default; may point elsewhere so several
   paper directories share one concepts directory.
5. Figures per note (4–5 default) and note length (2,000–3,000 words default). On re-run every
   step, including publishing destinations and credentials, shows "Keep: <current>" first.
6. Publishing targets, **multi-select checkboxes**: `[ ] Notion  [ ] Confluence`.
   - Notion: paste a Papers database URL, or let setup create one (`Name`, `Source`,
     `Published`, `Read`, `Tags`, `Summary`, `Confluence`). For an existing database setup reads
     the schema, proposes a field→property mapping, and confirms it.
   - Confluence: paste the parent page/folder URL; setup resolves site, `spaceId`, `parentId`
     via MCP. Figures need a REST API token (stored in the config file with mode 600, or via
     `ATL_SITE`/`ATL_EMAIL`/`ATL_TOKEN`), otherwise text-only publishing.
   - Per target, a default: publish on every run (`always`) or only on request (`ask`).
   - A target whose MCP tools are not present is recorded as disabled with a note to reconnect.
7. PDF backend check with install hints; installs only on explicit choice.

Writes `setup_done=true`. If `/read-paper` finds no configuration it runs setup inline and
then continues with the paper in the same turn.

## Step 1 of a run — ask where to save (mandatory tool call)

The first action after loading settings is an `AskUserQuestion` call asking for the save
directory — on **every** run, even with a full configuration. Options, in this order:

1. The configured default directory — **(Recommended)**, always present.
2. Recently used directories from the config file — only if they exist and differ from 1.
3. A directory that fits the current project context (e.g. a `papers/` or `notes/` dir
   in the working repo) — only if such a context exists.
4. Free text via the built-in "Other" option.

Domain and language are never asked in a run.

## Configuration

- Global: `~/.config/read-paper/config.json` (Linux/macOS, honours `XDG_CONFIG_HOME`) or
  `%APPDATA%\read-paper\config.json` (Windows). Mode 600 where supported (may hold a token).
- Per-directory overrides: `<save-dir>/.read-paper.json`.
- Keys: `domain`, `save_dir`, `concepts_dir`, `note_language`, `figures`, `note_length`,
  `setup_done`, `recent_dirs`, `last_dir`,
  `publish.notion.{enabled,default,url,data_source_id,properties}`,
  `publish.confluence.{enabled,default,url,site,space_id,parent_id,email,token,figures}`.
- Read and written only through `scripts/config.py` (`options`, `show`, `set KEY=VALUE`,
  `record`, `tags`).

## Output layout

```
<save-dir>/
  .read-paper.json
  pdfs/<slug>.pdf
  <slug>/
    <slug>.md
    figures/fig1-<short-name>.png
    figures/fig2-<short-name>.png
  concepts/                 (or the configured concepts_dir)
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
   with a caption line; 4–5 key figures.
5. Depth: each of Summary, Method, Results, Limitations, Personal Take is substantive
   (roughly 2,000–3,000 words total including tables, not an abstract rewrite).

Tags: reuse tags already present across existing notes in `<save-dir>` before inventing new ones.

## Concept notes (`concepts/`)

- Before writing the paper note, scan existing `concepts/*.md` and identify which concepts the
  paper touches.
- Create or update one file per concept. A concept note is **not** a copy of the paper
  summary; it holds understanding that cuts across papers and cites papers by slug
  (`[[<slug>]]`). Concepts link to each other with `[[concept-name]]`.
- Obsidian-compatible: plain `[[wikilinks]]`, no plugin-specific syntax.

## Figures and PDF text — dependencies

`scripts/setup.py` (run by setup and at the start of every run; Python, so it works on Windows too):

1. Check for poppler (`pdftoppm`, `pdftotext`). If missing, print the install command for the
   detected OS (`apt install poppler-utils`, `brew install poppler`, `choco install poppler`)
   and **ask** before installing. Never install without explicit approval.
2. If the user declines or install fails, try PyMuPDF (`python -c "import fitz"`); offer
   `pip install pymupdf` under the same rule.
3. If neither is available, continue: produce the Markdown note without figures and say so.

`scripts/pdf_text.py` and `scripts/crop_figure.py` use whichever backend is available
(poppler first, then PyMuPDF) and expose the same CLI either way. Crop coordinates are
given in points at 200 DPI, as in the original pipeline.

## Publishing (Notion, Confluence)

Performed by the plugin itself through the user's own MCP servers, after the local note is
written. Per target: `enabled` false → skip; `default` `always` → publish; `default` `ask` →
only when the user asked in this conversation; the user's words override the default either
way. A publishing failure never undoes the local note.

- **Notion**: figures via `notion-create-file-upload` + POST; `scripts/md2notion.py` converts the
  note (front matter → properties JSON, `> 💡` → callout, pipe tables → `<table>`, `$x$` →
  `$\`x\`$`, images → `file-upload://`); new tags are added to the multi-select first;
  `notion-create-pages` into the configured data source with the configured property mapping;
  verified with `notion-fetch`.
- **Confluence**: `scripts/md2confluence.py` converts to HTML+ (info panel, `easy-math-block`
  extension, tables, `{{FIG:...}}` placeholders); `createConfluencePage` placeholder →
  `scripts/confluence_upload.py` attaches figures via REST and prints `<figure>` snippets →
  re-convert with `--figures` → `updateConfluencePage` → ADF verification (macro bodies
  non-empty, media and table counts). The page URL is written back to the Notion page's
  `Confluence` property when both targets are configured.

## Out of scope

- Confluence REST fallback for page creation (only attachments use REST); Notion has no fallback.
- Named profiles, git automation, writing-style settings.
- Any personal or company-specific identifiers.
- Non-English documentation.

## Constraints

- The save-directory question is always a tool call (`AskUserQuestion`), never plain text.
- No installation, download outside the chosen directory, or network call beyond fetching
  the paper without the user's approval.
- Non-ASCII strings in tool-call parameters are written as literal UTF-8, never `\uXXXX`.
- The author's existing private workflow (`~/work/research`) is left untouched.
- No git operations of any kind.

## Success criteria

On a fresh machine and account (any of Linux, macOS, Windows):

1. `claude plugin marketplace add parktune/read-paper` + install succeeds.
2. `/read-paper:setup` alone stores every setting above; a Notion Papers database is created
   when the user asks for one.
3. `/read-paper https://arxiv.org/pdf/<id>` asks one question (save directory) and produces
   `pdfs/`, `<slug>/<slug>.md`, `<slug>/figures/*.png`, created/updated concept notes in the
   configured concepts directory, and the configured publications.
4. `/read-paper` without prior setup runs setup inline and then processes the paper.
5. Without poppler and PyMuPDF the note is still produced, minus figures, with a clear message;
   without the MCP servers the local note is produced and the targets are reported as skipped.

## Decisions log

| Question | Decision |
|---|---|
| Packaging | Plugin (skill + scripts); the GitHub repo doubles as marketplace |
| Notion / Confluence | Published by the plugin via the user's MCP servers; targets chosen in setup with multi-select; per-target default always/ask (revised 2026-09-16) |
| Concept notes | Included, under `<save-dir>/concepts/` |
| Note language | Follows the conversation; docs in English |
| Remembering paths | Config file + recent directory offered as an option; the question is asked on every run |
| Personal Take domain | Asked in `/read-paper:setup`, stored in config (no first-run questions) |
| PDF dependencies | poppler first (setup offers install), PyMuPDF fallback, else no figures |
| Names | repo `read-paper`, skills `/read-paper` and `/read-paper:setup`, default dir `~/Documents/ReadPaper/` |
| Missing config | `/read-paper` runs setup inline, then continues |
| Config scope | one global file + per-directory overrides |
| Extra setup items | concepts directory, figure count, note length |
| Defaults (2026-09-16, after first real use) | 4–5 figures, 2,000–3,000 words; setup re-run confirms destinations with Keep/Change |
| Platforms | Linux, macOS, Windows; Python-only scripts, no git |
