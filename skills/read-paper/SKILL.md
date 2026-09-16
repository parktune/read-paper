---
name: read-paper
description: Read a research paper from a URL (arXiv or any PDF link) or a local PDF and write a structured Markdown note with cropped figures plus cross-paper concept notes, then publish to Notion / Confluence if configured. "/read-paper setup" configures domain, directories, language, analysis detail level and publishing targets. Use when the user says "read this paper", "summarize this paper", "take notes on", "/read-paper", "configure read-paper", or gives an arXiv link or a PDF path and wants it organized.
argument-hint: "[article-url | article-filepath | setup]"
---

# read-paper

Turn one paper into a durable note. The note is a by-product of actually reading the
paper: read the whole text, look at the figures, then write. Do not paraphrase the abstract.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/`. Every script prints JSON; read it. Run them
with `python3`, or `python` on Windows when `python3` is not on PATH. Use forward slashes in
paths; the scripts handle the rest on every OS.

## 0. Resolve the argument

If `$ARGUMENTS` is `setup` (optionally followed by `--dir <path>`), read
`${CLAUDE_PLUGIN_ROOT}/skills/read-paper/setup.md`, follow it, and stop — there is no paper
in that case.

Otherwise `$ARGUMENTS` is the paper reference: a URL (`https://arxiv.org/pdf/1706.03762`,
`https://arxiv.org/abs/1706.03762`, or any direct PDF link) or a local path.

If it is empty, ask for it with `AskUserQuestion` (one question, options like
"I'll paste an arXiv URL" / "I'll give a local path"; the user types the value under Other).
Do not fail silently.

## 1. Load settings; run setup if there are none

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" options
```

If `configured` is false, read `${CLAUDE_PLUGIN_ROOT}/skills/read-paper/setup.md` and follow it now,
in this same turn. When it finishes, come back here and continue — do not ask the user to run
anything again. Re-run `config.py options` afterwards.

## 2. Ask where to save — always, and always as a tool call

Call `AskUserQuestion` on every run, even with a full config. Options, in this order, dropping
the ones that do not apply:

1. `recommended` from the script (the configured default) — label it `(Recommended)`, first.
2. Each entry of `recent` — "Last used" for the first one.
3. A directory that fits the current project, if there is one (e.g. the working repo has a
   `papers/`, `notes/`, or `docs/` directory, or the user mentioned one earlier).
4. Nothing else. The built-in "Other" lets the user type a path.

If `detail` in the settings is `ask`, add a **second question to the same call**: the analysis
detail level — `standard (Recommended)` / `brief` / `deep` (see the table in step 6). If `detail`
is a fixed level, do not ask; but if the user's message asks for a different depth in plain words
("just a quick summary", "go deep on this one"), that wins for this run.

Do not ask about domain or language here; those come from setup. Write all user-visible
strings as literal UTF-8, never `\uXXXX` escapes.

Then read the effective settings for the chosen directory (per-directory overrides apply):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" show --dir "<save-dir>"
```

`domain`, `note_language`, `concepts_dir`, `detail`, and `publish` drive the rest of the run.

## 3. Check the PDF backend

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --json
```

- `backend` is `poppler` or `pymupdf`: continue.
- `backend` is `none`: ask with `AskUserQuestion` before doing anything:
  "Install poppler (`<install_poppler>`) (Recommended)" / "Install PyMuPDF (`<install_pymupdf>`)" /
  "Continue without figures". Run the install command only after the user picks it. If they
  decline, the note is written without figures and the report says so.

## 4. Fetch the paper and its metadata

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_paper.py" "<ref>" --dir "<save-dir>"
```

The PDF is saved to `<save-dir>/pdfs/<slug>.pdf`. The JSON gives `title`, `authors`,
`published` (arXiv **v1** date), `latest_version`, `latest_date`, `comments` (often the venue),
`slug`, `note_dir`, `read` (today), and `warnings`.

- **Slug**: the automatic slug is the title's first words, which is often poor. Prefer the name
  people call the paper — the model or method name from the title before a colon, the arXiv
  `comments`, the project page, or the first paragraph (e.g. `dreamer4`, `resnet`,
  `attention-is-all-you-need`). Re-run with `--slug <name>` when the automatic one is a
  truncated sentence. The slug names the folder, the PDF, and the wikilink target.
- If `published` is null, find the date yourself: the arXiv stamp on page 1
  (`arXiv:XXXX.XXXXXvN [cs.XX] 12 Jun 2017`), the venue footer, or the copyright line. If you
  still cannot, ask the user; do not invent a date.

## 5. Read the paper

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_text.py" "<pdf>" --out "<scratch>/<slug>.txt"
```

Read the whole text (in chunks if long). While reading, note:

- the one-sentence thesis (what changed, compared with what, by how much);
- every equation you will need, with its notation;
- the figures that carry the argument (usually the overview diagram and the main result);
- the key numbers and the strongest baseline;
- what the authors concede in limitations, and what they do not.

Then look at the context that already exists:

```bash
ls "<concepts_dir>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" tags --dir "<save-dir>"
```

Read the concept notes this paper touches. Reuse existing tags before inventing new ones.

## 6. Detail level, then crop the figures

The detail level is one dial for the whole run:

| | brief | standard | deep |
|---|---|---|---|
| Length | ~1,000 words | 2,000–3,000 words | 3,500+ words |
| Figures | 1 (overview) | 2–3 | 4–5, including the decisive ablation |
| Sections | Background and Limitations one paragraph each; Method without `##` | full structure | full structure + ablation table + appendix findings |
| Concept notes | one line added to existing notes only, no new files | 2–4 created or updated | created/updated, and existing paragraphs rewritten where the paper changes them |

Word counts include tables and are approximate; for languages without word spacing count
space-separated units the same way.

Figures: the overview diagram and the main result table or plot come first; then the ablation
or analysis figure that changes the conclusion.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_figures.py" scout "<pdf>" <first> <last> "<scratch>/scout"
```

Open the scout PNGs with the Read tool and locate each figure. Scout is 80 DPI; crop is
200 DPI, so multiply scout pixel coordinates by 2.5:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_figures.py" crop "<pdf>" <page> <x> <y> <w> <h> "<note_dir>/figures/fig1-<short-name>.png"
```

Open each crop and confirm it is tight (no neighbouring text, no cut labels). Re-crop if not.

## 7. Write the note

Path: `<note_dir>/<slug>.md`. Start from `${CLAUDE_PLUGIN_ROOT}/templates/note.md` and fill
every placeholder; delete guidance text in `{{...}}`.

Fixed conventions:

- **First line**: `📄 Published: **YYYY-MM-DD** (arXiv vN · venue) · Source: [abs](…) · [pdf](…) · Affiliations · Read: YYYY-MM-DD`.
  Publication date comes **before** the read date — how recent the work is matters more than
  when you read it. If a later version exists, add it: `(arXiv v1 · v7 2023-08-02 · NeurIPS 2017)`.
- **Callout**: one blockquote line starting with 💡 stating the thesis.
- **Sections, in this order**: Summary · Background and Motivation · Method (with `##` per
  component) · Results · Limitations · Personal Take · Related Concepts.
- **Math**: `$$` blocks for display equations, `$...$` inline. Define symbols before use.
- **Results**: a pipe table with the paper's number and the strongest baseline's number, then
  the ablations that change the conclusion. No adjectives without a number next to them.
- **Personal Take**: written from the configured `domain`, in first person. What transfers to
  that domain, what does not and why, what you would try first. This is the section that makes
  the note worth keeping; do not make it a restatement of Summary.
- **Related Concepts**: `[[concept-name]]` links to files in `concepts_dir`, one line each on
  how the paper bears on that concept.
- **Language**: `note_language` (`conversation` = the language the user is writing in). Section
  headings follow it too, except code, math, and proper names.
- **Depth**: per the detail level table in step 6. At `standard` and `deep`, each of Summary,
  Method, Results, Limitations, Personal Take is a real section, not a paragraph; at `brief`
  the Personal Take still gets a full paragraph — it is the part worth keeping.
- Plain declarative prose. No emoji beyond the two above, no marketing verbs.
- Images as `![caption](figures/figN-name.png)` on their own line — the converters rely on it.

## 8. Update the concept notes

For each concept the paper genuinely bears on (typically 2–4 at `standard`), create or update
`<concepts_dir>/<concept-name>.md` from `${CLAUDE_PLUGIN_ROOT}/templates/concept.md`. At `brief`
only add one line per existing note that the paper touches and create nothing; at `deep` also
rewrite paragraphs the paper contradicts or sharpens.

A concept note is **not** a paper summary. It holds the understanding that cuts across
papers: what the concept is, what each paper adds (`[[<slug>]]` with the specific claim and a
number), where the papers disagree, what is open. When a new paper contradicts something in an
existing note, rewrite the paragraph rather than appending a caveat. Link concepts to each
other with `[[other-concept]]`.

Use kebab-case file names. Check the directory listing before creating a file to avoid
near-duplicates (`attention-mechanism.md` vs `self-attention.md`).

## 9. Publish (Notion, Confluence)

Decide per target from `publish.<target>`: `enabled` false → skip; `default` `always` → publish;
`default` `ask` → publish only if the user asked in this conversation ("also put it in
Confluence"). The user's words override the default in both directions ("skip Notion this
time"). A publish failure never undoes the local note; report it and move on.

If the target's MCP tools are not available in this session, skip it and say so in the report.

### Notion

1. Upload each figure: `notion-create-file-upload` (one per PNG), then POST the file to the
   returned `upload_url` with the returned headers (use `curl -F` or Python `urllib`). Collect
   `{"figures/figN-name.png": "<file-upload id>"}` into `<scratch>/uploads.json`.
2. Convert:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/md2notion.py" "<note>" --uploads "<scratch>/uploads.json" --out "<scratch>/notion.md" --meta "<scratch>/meta.json"
   ```
3. Tags: the multi-select must already contain every tag. Fetch the data source, and if any
   tag is new, add it with `notion-update-data-source` (`ALTER COLUMN "<Tags>" SET MULTI_SELECT(...)`
   listing **all existing options plus the new ones**) before creating the page.
4. `notion-create-pages` with parent `{data_source_id}` from config, properties mapped through
   `publish.notion.properties` (title ← `title` + ` (<institution> <year>)`, source ← `venue`,
   published/read ← dates, tags, summary ← the 💡 line), and `content` = the converted body.
5. `notion-fetch` the new page and confirm the figure count and headings.

### Confluence

1. Convert once to get the title and placeholders:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/md2confluence.py" "<note>" --out "<scratch>/conf.html"
   ```
2. `createConfluencePage` with `spaceId`, `parentId` from config, `contentFormat: html`, the
   note title, and a one-line placeholder body. Keep the returned page id.
3. If figures are enabled for Confluence (`publish.confluence.figures` is not false and
   credentials exist), attach each PNG:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence_upload.py" <page-id> "<note_dir>/figures/figN-name.png"
   ```
   and collect `{"figures/figN-name.png": "<snippet>"}` into `<scratch>/figures.json`. Re-run
   `md2confluence.py` with `--figures "<scratch>/figures.json"`.
4. `updateConfluencePage` with the final HTML.
5. `getConfluencePage` with `contentFormat: atlas_doc_format` and check: every `easy-math-block`
   extension has a non-empty `macroParams.body.value`, the media count equals the figure count,
   the table count matches.
6. If a Notion page was created and its mapping has `confluence`, write the page URL into that
   property with `notion-update-page`.

## 10. Remember the directory and report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" record --dir "<save-dir>"
```

Tell the user, briefly:

- the note path, the figure count, and the concept notes created or updated;
- the publication date and version you used, and where it came from;
- the Notion / Confluence URLs, or why a target was skipped;
- anything you could not do (no figures, unconfirmed date) and why.

Do not paste the note into the chat.

## Rules

- The save-directory question (step 2) is always an `AskUserQuestion` call, never plain text,
  never skipped. Domain and language are never asked here — that is `/read-paper setup`.
- Nothing is installed, published, or written outside `<save-dir>`, `concepts_dir`, and the
  scratch directory without the user's configuration or explicit words.
- No git operations. The save directory is just files; whether it is under version control is
  not this skill's concern.
- Every fact in the note comes from the paper text or figures. If the text does not support a
  number, leave it out.
