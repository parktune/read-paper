---
title: "{{TITLE}}"
venue: "{{VENUE}}"
published: {{PUBLISHED}}
read: {{READ}}
tags: [{{TAGS}}]
source: {{URL_ABS}}
pdf: ../pdfs/{{SLUG}}.pdf
---

📄 Published: **{{PUBLISHED}}** ({{VERSION_INFO}}) · Source: [abs]({{URL_ABS}}) · [pdf]({{URL_PDF}}) · {{AFFILIATIONS}} · Read: {{READ}}

> 💡 {{ONE_LINE_THESIS}}

# Summary

{{What the paper does, why it works, and what the evidence is. 3–5 paragraphs. Numbers over adjectives.}}

# Background and Motivation

{{The problem, what came before, and the gap this paper targets. Name the prior work it argues against.}}

# Method

{{Top-level design in prose, then one `##` per component. Notation defined before use. Display math in $$ blocks.}}

## {{Component 1}}

## {{Component 2}}

![{{Figure caption — what to look at, not just the paper's caption}}](figures/fig1-{{name}}.png)

# Results

{{Setup in one paragraph, then a table of the key numbers with the strongest baseline. Then ablations that actually change the conclusion.}}

| Setting | Metric | Ours | Baseline |
|---|---|---|---|

# Limitations

{{What the paper admits, and what it does not admit but the evidence shows. Compute, data, evaluation gaps.}}

# Personal Take

{{From the reader's domain ({{DOMAIN}}): what transfers, what does not, and what you would try first. Written in first person; this is a judgment, not a summary.}}

# Related Concepts

- [[{{concept-name}}]] — {{one line on how this paper bears on it}}
