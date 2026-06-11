---
name: screenplay-study-translation
description: Translate, annotate, audit, and export HTML screenplay study editions from screenplay PDFs with optional reference subtitles; use for bilingual screenplay translation, subtitle alignment, scene-number reconstruction, screenplay terminology, and static HTML study editions.
---

# Screenplay Study Translation — Knowledge Reference

This file defines translation principles, extraction heuristics, and reference structure for the screenplay-study-translation project.

It does NOT define pipeline stages or AI behavior rules.

- Pipeline stages → AI_AGENT_PROJECT_SPEC
- AI behavior rules → AI_AGENT_CONTRACT

-----

## 1. Translation Principles

- Preserve the screenplay as a document, not only as dialogue.
- When reference subtitles are provided, use subtitle content directly for
  dialogue translations. Follow `references/subtitle_alignment.md` for label
  decisions.
- AI translates non-dialogue elements: action, atmosphere, scene headings,
  character cues, parentheticals, transitions, on-screen text, sound/effects,
  omitted scenes, and format markers.
- When subtitles are absent, AI translates all screenplay elements.
- Never replace action description with generic summaries.
- Use the overall subtitle translation style as the primary input for
  `style-profile.json`; apply that style profile to non-dialogue translation.
- Subtitle quality is judged by the user. The skill parses and applies provided
  subtitles, but does not automatically validate translation quality.
- Require a user-supplied Chinese film title when initializing a new translation
  project. Use it for reader-facing HTML title and cover text; do not infer it
  from filenames, subtitles, or model judgment.
- Generate a terminology baseline automatically after source extraction and
  subtitle normalization. Do not require routine user confirmation; escalate
  only high-impact ambiguity, conflicting evidence, or title-affecting terms.
- For formal batch translation, prefer a current-range batch context package
  when available; it is a token-saving read-only summary, not a validation gate
  or a replacement for batch validation.
- When subtitles provide a proper noun translation, that translation takes
  priority over AI judgment. It must be recorded in references/terminology.md
  and applied consistently across all batches.
- When subtitles contain annotations or explanatory notes distinct from
  dialogue translation, annotations must be included in the HTML output
  as reader notes, not dialogue. Never silently drop subtitle annotations.
- If subtitles are absent, omit subtitle-specific labels.
- When subtitles are absent, output quality depends on model judgment.
- Preserve cinematic intent, dialogue rhythm, and cultural context.
- Produce translation at final-quality intent from the first pass.

-----

## 2. Extraction Principles

- Reconstruct scene numbers from the source. Never invent sequential scene numbers.
- Treat missing scene numbers as a script-type signal, not an automatic error. Reading drafts and public PDFs may omit production scene numbers.
- Treat extraction rules as auditable heuristics, not universal truths. Do not turn one project’s formatting into a hard-coded global rule.
- Keep page mapping explicit and consistent throughout extraction.
- Auto-correct obvious, low-risk source defects when context makes the fix clear; record corrections in work artifacts.

-----

## 3. Source Marker Handling

Independently scan and record:

- Scene numbers
- OMITTED scenes
- CONT’D markers
- MORE markers
- Parentheticals
- Transitions
- Camera and format terms
- Side-margin scene numbers

Stage 2 is a signal scan, not a rule-upgrade step. Record known markers as
structural signals, unmatched structural evidence as warning signals, and
low-confidence ignored candidates as noise signals. Do not create new marker
types or schema fields from a single source scan.

Audit all markers against output before finalization.

-----

## 4. Reader Assumptions

- Assume readers may have limited source-language confidence.
- Do not make user review the primary translation quality gate.
- No raw screenplay terms should appear without translation or explanation.

-----

## 5. Output Principles

- Remove task labels, duplicate indexes, debug notes, and workflow artifacts from final HTML output.
- HTML must include a collapsible scene index with working navigation links.
- Generated HTML should restore confirmed source-visible screenplay formatting
  and structure after it has been captured in batch JSON, markers, layout
  metadata, or inline markup. Do not flatten source formatting signals into
  ordinary prose when source evidence shows they affect how the screenplay reads
  on the page.
- Do not produce page-aligned PDFs. If PDF output is needed, prefer a reflowed A4 reading edition that labels source locations as “原剧本第 X 页”.
- Audit and final outputs are different presentations of the same formal translation: audit may show engineering metadata; final output hides technical noise.
- For full-project delivery, include a project-local `references/reading_guide.md`
  as a reader guide near the front of the HTML. The guide is AI-authored project
  prose, not renderer inference or a subtitle statistics report.

-----

## 6. Validation Checklist

This is the project-specific checklist referenced by AI_AGENT_CONTRACT Section 7.

Before finalizing, verify:

- Stage 2 signal report produced before translation begins
- source page mapping is explicit
- source scene numbers are preserved as strings
- `OMITTED`, `CONT'D`, `MORE`, split scene markers, and side-margin scene numbers are audited against output
- subtitle labels are absent when no subtitles are provided
- no raw screenplay terms appear without translation or explanation
- HTML scene index links resolve
- work batches live under `work/batches/`
- final HTML lives under `dist/`

-----

## 7. Must-Read References

Read only what the task needs:

**Project flow:**

- `references/workflow.md` — end-to-end project workflow
- `references/configuration.md` — project configuration
- `references/engineering.md` — scripts and tooling

**Source structure:**

- `references/industry_conventions.md` — unusual source structure, missing markers
- `references/marker_inventory.md` — scanning and auditing source markers
- `references/source_lines.md` — PDF text extraction and draft batches
- `references/validation.md` — audit creation and execution

**Translation and output:**

- `references/batch_context.md` — compact current-batch context packages
- `references/reading_guide.md` — reader guide artifact and compact guide-context workflow
- `references/batch_schema.md` — translation batch format and validation
- `references/terminology.md` — screenplay, camera, and format terms
- `references/subtitle_alignment.md` — subtitle alignment (when subtitles are present)
- `references/troubleshooting.md` — unexpected behavior in extraction, translation, or HTML output
