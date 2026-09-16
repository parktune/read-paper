---
name: setup
description: One-time configuration for read-paper — research domain, default save directory, concept-notes directory, note language, figure count, note length, and optional Notion / Confluence publishing targets. Use when the user runs "/read-paper:setup", says "configure read-paper", "set up read-paper", "change my read-paper settings", or when /read-paper finds no configuration.
argument-hint: "[--dir <save-dir>]"
---

# read-paper setup

Collect the reader's preferences once and store them, so `/read-paper` never has to ask
about them again. Every question below goes through `AskUserQuestion`; user-visible strings are
literal UTF-8 (never `\uXXXX`). Ask in the language the user is speaking.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/`. Run them with `python3`, or `python` on
Windows when `python3` is not on PATH. Never install anything without an explicit choice.

Re-running setup is normal: show the current value of each setting in the question and let the
user keep it (offer "Keep: <current>" as the first option). This applies to **every** step
below, including the Notion and Confluence destinations, credentials, and per-target defaults
— never silently carry a stored destination forward without showing it.

## 0. Where the settings go

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" show
```

Settings are global by default. If the user passed `--dir <path>` (or asks for settings that
apply to one directory only), write with `config.py set ... --dir <path>` instead; those values
override the global ones for that directory.

## 1. Domain, directory, language (one call, 3 questions)

1. **Research domain** — free text (the user types it under Other). Offer three neutral examples
   as options, e.g. "computational biology", "recommender systems", "speech recognition". The
   Personal Take section of every note is written from this viewpoint.
2. **Default save directory** — options: `~/Documents/ReadPaper` (Recommended), the current
   working directory if it looks like a notes/papers folder, Other. This is the directory
   `/read-paper` recommends on every run; the user can still pick another directory each time.
3. **Note language** — "Same as the conversation (Recommended)", "English", Other.

## 2. Concepts, figures, length (one call, 3 questions)

1. **Concept-notes directory** — "Inside the save directory: `<save-dir>/concepts` (Recommended)"
   or Other. Concept notes accumulate across papers, so people who keep several paper
   directories often want one shared concepts directory.
2. **Figures per note** — "4–5 (Recommended)", "2–3", "1", "None".
3. **Note length** — "2,000–3,000 words (Recommended)", "Short: 1,000–1,500", "Long: 3,500+".
   Word counts are approximate and language-agnostic; tables count.

## 3. Publishing targets (one multi-select question)

Ask **where notes should also be published**, `multiSelect: true`:

- `[ ] Notion` — a Papers database
- `[ ] Confluence` — a page under a parent page or folder

When a target is already configured, put its current destination and default in the label,
e.g. `Notion (current: Papers DB · always)` / `Confluence (current: Papers folder · ask)`, so
unchecking it is a visible decision. A target that was configured and is now unchecked gets
`publish.<target>.enabled=false` (its destination stays in the file for a later re-enable).

Nothing selected means local Markdown only; skip to step 6.

Before asking, check which MCP tools exist in this session: Notion needs `notion-create-pages`,
`notion-fetch`, `notion-create-database`; Confluence needs `createConfluencePage`,
`getConfluencePage`. If a target's tools are missing, still let the user select it, but then
record `publish.<target>.enabled=false` with a note in the report that they should connect
the MCP server and re-run setup — do not try to configure a target you cannot reach.

## 4. Notion (only if selected)

If a Notion destination is already stored, first ask: "Keep: <database title> (<url>)"
(Recommended) / "Change". On Keep, skip to the default question below.

Otherwise ask with one `AskUserQuestion`: "Paste the URL of an existing Papers database" (Other)
or "Create a new Papers database for me (Recommended)".

**Existing database**: call `notion-fetch` on the URL. Read the data source id and the
property schema. Map the note's fields onto existing properties by type and name — title
property → `title`; a date property named like read/읽은/date → `read`; a date named like
published/발행 → `published`; multi_select → `tags`; a rich_text named like summary/요약 →
`summary`; url named like confluence → `confluence`; another rich_text named like
source/venue/출처 → `source`. Show the mapping to the user in a short table and confirm with
`AskUserQuestion` ("Looks right" / "Let me correct it"). Fields with no matching property are
simply not written.

**New database**: ask where to put it — a page URL (Other) or "My private pages
(Recommended)". Then `notion-create-database` with title `Papers` and properties:

| property | type |
|---|---|
| Name | title |
| Source | rich_text |
| Published | date |
| Read | date |
| Tags | multi_select (no options yet) |
| Summary | rich_text |
| Confluence | url |

Then ask the default: "Publish to Notion on every run (Recommended)" / "Only when I ask"
(with "Keep: <current>" first when re-running).

Record:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" set \
  publish.notion.enabled=true publish.notion.default=always \
  publish.notion.url="<db url>" publish.notion.data_source_id="<id>" \
  'publish.notion.properties={"title":"Name","source":"Source","published":"Published","read":"Read","tags":"Tags","summary":"Summary","confluence":"Confluence"}'
```

(`default` is `always` or `ask`.)

## 5. Confluence (only if selected)

If a Confluence destination is already stored, first ask: "Keep: <parent title> (<url>)"
(Recommended) / "Change". On Keep, also keep the stored credentials unless the user says
otherwise, and skip to the default question below.

Otherwise ask for the **parent page or folder URL** (Other; no default — every space is laid
out differently, so nothing is guessed). Call `getConfluencePage` (or
`getPagesInConfluenceSpace` / `search` when the URL is a folder or short link) to resolve the
site (`https://<x>.atlassian.net`), `spaceId` and the parent `id`. Confirm the resolved title
with the user.

Figures need the REST API because the MCP server cannot upload attachments. Ask one
`AskUserQuestion`: "Store an Atlassian API token in the config file (chmod 600)",
"I will set ATL_SITE / ATL_EMAIL / ATL_TOKEN environment variables myself", or
"Skip — publish text without figures". If storing, ask for email and token as free text
(explain the token comes from https://id.atlassian.com/manage-profile/security/api-tokens).

Then ask the default: "Publish to Confluence on every run" / "Only when I ask (Recommended)"
(with "Keep: <current>" first when re-running).

Record:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" set \
  publish.confluence.enabled=true publish.confluence.default=ask \
  publish.confluence.url="<parent url>" publish.confluence.site="https://<x>.atlassian.net" \
  publish.confluence.space_id="<spaceId>" publish.confluence.parent_id="<id>" \
  publish.confluence.email="<email>" publish.confluence.token="<token>"
```

Omit `email`/`token` when the user chose environment variables or no figures; set
`publish.confluence.figures=false` for the last case.

## 6. PDF backend

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --json
```

If `backend` is `none`, ask: "Install poppler: `<install_poppler>` (Recommended)" /
"Install PyMuPDF: `<install_pymupdf>`" / "Skip for now (notes without figures)". Run the
install command only when chosen, then re-check.

## 7. Write the core settings and finish

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" set \
  domain="<domain>" save_dir="<dir>" note_language="<lang>" concepts_dir="<dir>" \
  figures="<4-5>" note_length="<2000-3000>" setup_done=true
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" show
```

Report the final settings as a short table with the config file path, and say how to change
one later (re-run `/read-paper:setup`, or edit the JSON). If setup was started from inside a
`/read-paper` run, continue that run now without asking the user to repeat the command.
