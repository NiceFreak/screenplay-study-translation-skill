AI_AGENT_PROJECT_SPEC

PROJECT: screenplay-study-translation

-----

1. PURPOSE

This document describes the project-level structure for generating a translated screenplay study edition from screenplay PDFs with optional subtitles.

It describes:

- pipeline stages
- file structure
- expected artifacts
- validation surfaces
- output requirements

It is a static project description. Runtime execution boundaries and runtime
decisions are defined only by AI_AGENT_CONTRACT.

It has no runtime control over execution order, stage advancement, validation
follow-up actions, automatic continuation, or user confirmation requirements.

-----

2. INPUTS

Required:

- screenplay PDF
- user-supplied Chinese film title

Optional:

- subtitles (.ass / .srt / .vtt)

-----

3. OUTPUTS

Primary reader output:

- dist/screenplay-study.html
- dist/screenplay-study.epub

Deprecated output:

- PDF output is not supported in v0.3. `scripts/export_pdf.py` is retained as
  historical reference only.

Intermediate outputs:

- extracted source markers
- project-local terminology baseline
- optional batch context packages
- optional batch plan report
- cost observation report (auto-generated at finalization)
- translation batches (JSON)
- validation reports
- optional observation-only diagnostic report

-----

4. PIPELINE STAGES

STAGE 1: EXTRACTION

- extract text from PDF

Extraction completeness can be represented by comparing total PDF page count
against extracted JSON page count. Runtime handling follows AI_AGENT_CONTRACT.

STAGE 2: SOURCE SCAN

- detect known markers such as CONT'D, OMITTED, MORE, side-margin scene labels,
  and voice/source-position markers
- extract raw structural signals without assigning new marker types
- record unmatched raw signals and low-confidence noise candidates
- output a Stage 2 signal report

STAGE 2 SIGNAL REPORT contains:

- structural_signal: known markers and candidate structural evidence
- warning_signal: unmatched or risky signals requiring review
- noise_signal: ignored low-confidence candidates recorded for traceability

Stage 2 signal reports represent source evidence without changing marker rules,
schemas, or source text.

OBSERVATION ARTIFACT:
- output: work/diagnostic/diagnostic_report.json
- timing: after Stage 2 validation artifacts exist
- scope: read-only explanation of system state, key signals, existing
  failure-mode matches, likely causes, and recommended checks
- non-goals: no pipeline stage, no gate behavior, no schema change, no repair,
  no optimization trigger

STYLE PROFILE ARTIFACT:
- output: work/style-profile.json
- style profile is used as consistency reference for translation batches
- when subtitles are provided, subtitle style is the primary style-profile input
- first-batch style notes may be recorded as a review artifact

TERMINOLOGY BASELINE ARTIFACT:
- output: generated project's local references/terminology.md or equivalent
  project-local terminology artifact
- timing: after PDF and optional subtitles are extracted, before the first
  translation batch
- source: subtitle-derived proper nouns when available; otherwise source
  recurrence and context
- user confirmation: not required routinely; only high-impact ambiguity,
  conflicting evidence, or title-affecting terms are escalated

STAGE 3: BATCH CREATION

- split screenplay into 5–10 page batches
- create translation batch JSON

STAGE 4: TRANSLATION

- translate batch content
- preserve:
  - dialogue
  - action
  - formatting
  - scene structure
  - page references
- each batch records its relationship to work/style-profile.json when available
- deviations from style profile may be represented in validation output
- when subtitles are provided:
  - dialogue translations use subtitle content directly
  - subtitle label decisions follow references/subtitle_alignment.md
  - label decisions should be made on expression units, not raw physical rows,
    when a spoken turn is split across multiple screenplay rows or subtitle
    events
  - when a matched subtitle event is stable, optional subtitle timestamp fields
    may be persisted on dialogue entries for later observation; this does not
    imply scene alignment, difference typing, or timeline analysis
  - AI translates non-dialogue elements: action description, scene headings,
    parentheticals, format markers, and on-screen text
- when subtitles are absent, AI translates all elements and quality depends on
  model judgment

BATCH CONTEXT PACKAGE ARTIFACT:
- output: work/context/batch-context-pXXX-YYY.json
- timing: after Stage 2 confirmation and before translating the current batch
- scope: compact read-only package for one displayed-page range, including
  current source entries, local markers/signals, advisory subtitle candidates,
  relevant terminology, style summary, and previous-batch continuity
- non-goals: no pipeline stage, no validation gate, no subtitle-match authority,
  no schema change, no repair, no rule creation
- reference: references/batch_context.md

BATCH PLAN ARTIFACT:
- output: work/reports/batch-plan.json
- scope: deterministic advisory 5-10 page range planning from local source
  density and marker density
- non-goals: no pipeline stage, no validation gate, no automatic continuation,
  no runtime execution control
- reference: references/workflow.md

COST OBSERVATION ARTIFACT:
- output: work/reports/cost-report.json
- scope: read-only artifact-size and rough token observation for cost analysis
- finalization: generated automatically by finalize_html.py after final HTML
  audit passes
- non-goals: no billing authority, no validation gate, no permission to reduce
  current-range source text
- reference: references/engineering.md

When no reference subtitles are provided, terminology artifacts may include:
- character names
- place names
- cultural concepts
- generated baseline term records
- explicitly escalated term decisions when needed

STAGE 5: VALIDATION

- batch validation reports
- structural integrity checks
- marker consistency checks

STAGE 6: FINALIZATION

- merged batch artifact
- final HTML artifact
- final EPUB artifact for mobile reading
- navigation structure
- cover with user-supplied Chinese title and translated physical title-page
  information when source rows are available
- reading note for edition-wide conventions and professional terms
- final validation summary artifact

-----

5. WORKING DIRECTORY STRUCTURE

project/
project.yaml
inputs/
screenplay.pdf
subtitles.*
work/
batches/
logs/
extracted/
dist/
screenplay-study.html
screenplay-study.epub

-----

6. VALIDATION SURFACES

Validation reports can represent:

- scene structure integrity
- page mapping consistency
- marker preservation
- batch completeness
- HTML navigation correctness
- EPUB package readability and navigation correctness

-----

7. TRANSLATION CONTENT MODEL

Translation output preserves:

- screenplay structure (not only dialogue)
- scene hierarchy
- cinematic intent
- formatting signals

Translation output avoids:

- flatten structure into summary
- remove markers
- normalize away screenplay-specific formatting
- add body notes for edition-wide formatting conventions

-----

8. BATCH ARTIFACTS

- 5–10 pages per batch (default)
- sequential source order
- no overlapping content between batches
- stable, traceable batch IDs

-----

9. ERROR HANDLING REFERENCE

Project artifacts may record issues, warnings, uncertainty, and signals in
work/logs or validation reports. Runtime handling of those records is governed
only by AI_AGENT_CONTRACT.

-----

10. SYSTEM BOUNDARY

This file describes WHAT the system contains and produces.

It has no authority over:

- AI behavior rules (handled by AI_AGENT_CONTRACT)
- runtime decision logic
- classification rules
