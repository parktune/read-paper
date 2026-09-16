---
name: read-paper
description: Read a research paper from a URL (arXiv or any PDF link) or a local PDF and write a structured Markdown note with cropped figures plus cross-paper concept notes into a directory the user chooses. Use when the user says "read this paper", "summarize this paper", "take notes on", "/read-paper", or gives an arXiv link or a PDF path and wants it organized.
argument-hint: "[article-url | article-filepath]"
---

# read-paper

Turn one paper into a durable note. The note is a by-product of actually reading the
paper: read the whole text, look at the figures, then write. Do not paraphrase the abstract.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/`. Every script prints JSON; read it.

## 0. Resolve the argument

`$ARGUMENTS` is the paper reference: a URL (`https://arxiv.org/pdf/1706.03762`,
`https://arxiv.org/abs/1706.03762`, or any direct PDF link) or a local path.

If it is empty, ask for it with `AskUserQuestion` (one question, options like
"I'll paste an arXiv URL" / "I'll give a local path"; the user types the value under Other).
Do not fail silently.

## 1. Ask where to save — always, and always as a tool call

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" options
```

Then call `AskUserQuestion`. This step is never skipped, even when a config exists.
Build the save-directory options in this order and drop the ones that do not apply:

1. `recommended` from the script (`~/Downloads/ReadPaper/`) — label it `(Recommended)`, first.
2. Each entry of `recent` — "Last used" for the first one.
3. A directory that fits the current project, if there is one (e.g. the working repo has a
   `papers/`, `notes/`, or `docs/` directory, or the user mentioned one earlier).
4. Nothing else. The built-in "Other" lets the user type a path.

If `first_run` is true, or `domain` is null, add two more questions **to the same call**:

- **Research domain** — free text via Other; offer 3 neutral examples as options
  (e.g. "computational biology", "recommender systems", "speech recognition"). This is
  what the Personal Take section is written from.
- **Note language** — options: "Same as our conversation (Recommended)", "English", "Other".

Write all user-visible strings as literal UTF-8, never `\uXXXX` escapes.

## 2. Check the PDF backend

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" --json
```

- `backend` is `poppler` or `pymupdf`: continue.
- `backend` is `none`: ask with `AskUserQuestion` before doing anything:
  "Install poppler (`<install_poppler>`) (Recommended)" / "Install PyMuPDF (`<install_pymupdf>`)" /
  "Continue without figures". Run the install command only after the user picks it.
  Never install anything without that explicit choice. If they decline, the note is written
  without figures and the report says so.

## 3. Fetch the paper and its metadata

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_paper.py" "<ref>" --dir "<save-dir>"
```

The PDF is saved to `<save-dir>/pdfs/<slug>.pdf`. The JSON gives `title`, `authors`,
`published` (arXiv **v1** date), `latest_version`, `latest_date`, `comments` (often the venue),
`slug`, `note_dir`, `read` (today), and `warnings`.

- If `published` is null, find the date yourself: the arXiv stamp on page 1
  (`arXiv:XXXX.XXXXXvN [cs.XX] 12 Jun 2017`), the venue footer, or the copyright line. If you
  still cannot, ask the user; do not invent a date.
- Override the slug with `--slug` when the automatic one is poor (too long, or a
  generic word). The slug names the folder, the PDF, and the wikilink target.

## 4. Read the paper

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_text.py" "<pdf>" --out "<scratch>/<slug>.txt"
```

Read the whole text (in chunks if long). While reading, note:

- the one-sentence thesis (what changed, compared with what, by how much);
- every equation you will need, with its notation;
- the 2–3 figures that carry the argument (usually the overview diagram and the main result);
- the key numbers and the strongest baseline;
- what the authors concede in limitations, and what they do not.

Then look at the context that already exists in `<save-dir>`:

```bash
ls "<save-dir>"/concepts/ 2>/dev/null
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" tags --dir "<save-dir>"
```

Read the concept notes this paper touches. Reuse existing tags before inventing new ones.

## 5. Crop the figures

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_figures.py" scout "<pdf>" <first> <last> "<scratch>/scout"
```

Open the scout PNGs with the Read tool and locate each figure. Scout is 80 DPI; crop is
200 DPI, so multiply scout pixel coordinates by 2.5:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_figures.py" crop "<pdf>" <page> <x> <y> <w> <h> "<note_dir>/figures/fig1-<short-name>.png"
```

Open each crop and confirm it is tight (no neighbouring text, no cut labels). Re-crop if not.
Two to three figures; more only if the paper is unusually visual.

## 6. Write the note

Path: `<note_dir>/<slug>.md`. Start from `${CLAUDE_PLUGIN_ROOT}/templates/note.md` and fill
every placeholder; delete guidance text in `{{...}}`.

Fixed conventions:

- **First line**: `📄 Published: **YYYY-MM-DD** (arXiv vN · venue) · Source: [abs](…) · [pdf](…) · Affiliations · Read: YYYY-MM-DD`.
  Publication date comes **before** the read date — how recent the work is matters more than
  when you read it. If a later version exists, add it: `(arXiv v1 · v7 2023-08-02 · NeurIPS 2017)`.
- **Callout**: one blockquote line with 💡 stating the thesis.
- **Sections, in this order**: Summary · Background and Motivation · Method (with `##` per
  component) · Results · Limitations · Personal Take · Related Concepts.
- **Math**: `$$` blocks for display equations, `$...$` inline. Define symbols before use.
- **Results**: a table with the paper's number and the strongest baseline's number, then the
  ablations that change the conclusion. No adjectives without a number next to them.
- **Personal Take**: written from the configured research domain, in first person. What
  transfers to that domain, what does not and why, what you would try first. This is the
  section that makes the note worth keeping; do not make it a restatement of Summary.
- **Related Concepts**: `[[concept-name]]` links to files in `<save-dir>/concepts/`, one line
  each on how the paper bears on that concept.
- **Language**: the configured note language (default: the language of the conversation).
  Keep the section headings in that language too, except code, math, and proper names.
- **Depth**: roughly 1,500–2,500 words. Each of Summary, Method, Results, Limitations,
  Personal Take is a real section, not a paragraph.
- Plain declarative prose. No emoji beyond the two above, no marketing verbs.

## 7. Update the concept notes

For each concept the paper genuinely bears on (typically 2–4), create or update
`<save-dir>/concepts/<concept-name>.md` from `${CLAUDE_PLUGIN_ROOT}/templates/concept.md`.

A concept note is **not** a paper summary. It holds the understanding that cuts across
papers: what the concept is, what each paper adds (`[[<slug>]]` with the specific claim and a
number), where the papers disagree, what is open. When a new paper contradicts something in an
existing note, rewrite the paragraph rather than appending a caveat. Link concepts to each
other with `[[other-concept]]`.

Use kebab-case file names. Check `ls concepts/` before creating a file to avoid near-duplicates
(`attention-mechanism.md` vs `self-attention.md`).

## 8. Remember the choices

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" record --dir "<save-dir>" --domain "<domain>" --language "<lang>" --backend "<backend>"
```

Pass `--domain` and `--language` only when they were asked this run.

## 9. Report

Tell the user, briefly:

- the note path, the figure count, and the concept notes created or updated;
- the publication date and version you used, and where it came from;
- anything you could not do (no figures, unconfirmed date) and why.

Do not paste the note into the chat. If the user has a Notion or Atlassian MCP server
connected and asks to publish, the Markdown can be uploaded as is — the first line and
section structure carry over unchanged; figures go through that server's file-upload tool.

## Rules

- The save-directory question (step 1) is always an `AskUserQuestion` call, never plain text,
  never skipped.
- Nothing is installed, and nothing is written outside `<save-dir>` and the scratch directory,
  without the user choosing it.
- Every fact in the note comes from the paper text or figures. If the text does not support a
  number, leave it out.
- The user's own words in the config (domain, language) are written back exactly as given.
