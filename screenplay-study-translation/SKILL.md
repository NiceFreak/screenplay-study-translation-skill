---
name: screenplay-study-translation
description: Translate, annotate, audit, and export HTML screenplay study editions from screenplay PDFs with optional reference subtitles; use for bilingual screenplay translation, subtitle alignment, scene-number reconstruction, screenplay terminology, and static HTML study editions.
---

# Screenplay Study Translation

Use this skill to create a translated screenplay study edition from a screenplay PDF. Reference subtitles are optional.

Codex should act as both:

- a senior screenplay/subtitle translator who preserves dialogue rhythm, cultural context, screenplay atmosphere, and professional terminology
- a rigorous document engineer who extracts, audits, and exports screenplay structure reproducibly

## Core Workflow

0. Establish the screenplay-format knowledge baseline before changing tooling.
   Read or update `references/industry_conventions.md` before interpreting unusual source structure as an extraction problem.
1. Inspect the project and configuration before changing files.
   If no project exists, initialize one with `scripts/init_project.py`.
2. Extract source PDF structure before translating.
3. Independently scan source markers such as scene numbers, `OMITTED`, `CONT'D`, `MORE`, parentheticals, transitions, and camera/format terms.
4. Run source audit gates before generating formal translation output.
   For real samples, run `scripts/validate_sample.py` before translating.
5. Translate in small batches, usually 5-10 screenplay pages.
6. Finalize HTML with `scripts/finalize_html.py`.
7. Run output audits before finalizing.

## Operating Principles

- Preserve the screenplay as a document, not only as dialogue.
- Translate action, atmosphere, scene headings, character cues, dialogue, parentheticals, transitions, on-screen text, sound/effects, omitted scenes, and format markers.
- Never replace action description with generic summaries.
- Treat reference subtitles as helpful evidence, not authority.
- If subtitles are absent, still produce a high-quality screenplay translation; omit subtitle-specific labels.
- Reconstruct scene numbers from the source. Never invent sequential scene numbers.
- Treat missing scene numbers as a script-type signal, not an automatic error. Reading drafts and public screenplay PDFs may omit production scene numbers; use scene-heading navigation when numbers are absent.
- Treat extraction rules as auditable heuristics, not universal truths. Do not turn one project's formatting into a hard-coded global rule.
- Auto-correct obvious, low-risk source or extraction defects when context makes the fix clear; record the correction in work artifacts, but do not burden the reader with noise.
- Keep page mapping explicit and consistent.
- Minimize token cost: use targeted search, structured reports, and small batch outputs.
- Produce translation batches at final-quality intent from the first pass. Do not rely on a rough-translation -> user catches errors -> rewrite loop.
- Treat audit and final outputs as different presentations of the same formal translation: audit may show engineering metadata, while final output hides technical noise.
- Assume readers may have limited source-language confidence. Do not make user review the primary translation quality gate.

## Must-Read References

Read only what the task needs:

Project flow:

- `references/workflow.md` for end-to-end project workflow.
- `references/configuration.md` when creating or editing project configuration.
- `references/engineering.md` when editing scripts or project tooling.

Source structure:

- `references/industry_conventions.md` when source structure looks unusual, especially when scene numbers, omitted scenes, or production markers are missing or ambiguous.
- `references/marker_inventory.md` when scanning or auditing source markers.
- `references/source_lines.md` when extracting PDF text rows or generating draft batches.
- `references/validation.md` when creating or running audits.

Translation and output:

- `references/batch_schema.md` when creating or validating translation batches.
- `references/terminology.md` when handling screenplay/camera/format terms.
- `references/subtitle_alignment.md` when reference subtitles are present.
- `references/troubleshooting.md` when validation, extraction, translation, or HTML output behaves unexpectedly.

## Output Defaults

- Work batches live under `work/batches/`.
- Final HTML lives under `dist/`.
- Merge multiple validated translated batches with `scripts/merge_batches.py` before full-project HTML output.
- `scripts/finalize_html.py` may auto-select the largest `translated-*.json` batch from `work/batches/` for final HTML delivery.
- HTML may include a collapsible scene index.
- Do not produce page-aligned PDFs as a normal target. If PDF output is deliberately reopened, prefer a reflowed A4 reading/print edition that labels source locations as "原版第 X 页" instead of forcing translated content into matching source pages.
- Remove task labels, duplicate indexes, debug notes, and workflow artifacts from final output.

## Validation Checklist

Before finalizing, verify:

- source page mapping is explicit
- source scene numbers are preserved as strings
- `OMITTED`, `CONT'D`, `MORE`, split scene markers, and side-margin scene numbers are audited against output
- subtitle labels are absent when no subtitles are provided
- no raw screenplay terms appear without translation or explanation
- HTML scene index links resolve
