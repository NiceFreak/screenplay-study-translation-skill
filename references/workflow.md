# Workflow

## 0. Domain Baseline

Before building or revising tooling, establish the screenplay-format baseline:

- read `references/industry_conventions.md`
- identify whether the source is likely a reading draft, spec script, production draft, shooting script, teleplay, or other house format
- separate industry conventions from extraction failures
- record unknown or source-specific conventions as notes instead of turning them into hard-coded rules

Do this before treating missing scene numbers, unusual page numbering, omitted scenes, voice-position markers, or slugline variants as bugs.

When a real project does not match expectations, consult `references/troubleshooting.md` before writing a project-specific fix.

## 1. Intake

Collect:

- screenplay PDF path
- user-supplied Chinese film title
- optional subtitle path
- source and target languages
- desired HTML output path
- page mapping rule
- likely script type when known: reading draft, spec script, production draft, shooting script, teleplay, or other house format

If the user provides an existing generated project, inspect its scripts before editing outputs.

If the project has no `project.yaml`, initialize the standard directory structure with `scripts/init_project.py`. Do not move or copy user PDFs unless explicitly requested; write their paths into configuration.

Use `scripts/extract_pdf.py` to create `work/source-lines.json` before source validation or translation batch creation. Treat it as source review data, not as proof that PDF extraction is complete.

For a first real sample, run `scripts/validate_sample.py` after extraction and before translation. It should produce a compact signal report under `work/reports/`.

After PDF and optional subtitles are extracted, generate the project-local
terminology baseline before the first translation batch. This is an automated
setup artifact, not a routine user confirmation gate. Use subtitle-derived
proper nouns when available; otherwise use source recurrence and context.
Escalate only high-impact ambiguity, conflicting evidence, or title-affecting
terms.

Write project-local `references/front_matter.md` for reader-facing cover and
title-page translations before the first HTML output. Include concrete
translations for title-page metadata instead of leaving raw PDF rows for the
renderer to interpret.

After the terminology baseline, write project-local `references/reader_notes.md`
for edition-wide reading conventions and screenplay-format professional terms.
The renderer uses this artifact for the HTML reading note instead of deriving
terms from each batch.

## 2. Source Extraction

Extract structured source data:

- physical PDF page
- displayed screenplay page
- text rows with coordinates
- scene headings
- side-margin scene numbers
- character cues
- dialogue
- parentheticals
- action blocks
- transitions and camera/format markers

Do not assume a PDF has a clean text layer. Visible text may be split across normal text rows, side-margin small text, flipped-coordinate drawing operations, repeated content streams, or non-body objects.

After extraction, verify completeness before source scanning:

- compare total physical PDF page count with the physical pages represented in `source-lines.json`
- if any physical page is missing from `source-lines.json`, classify the result as `UNCERTAIN`
- do not infer that a missing page is blank or ignorable without explicit source evidence
- repair extraction and rerun `scripts/extract_pdf.py` before continuing to source scan

## 3. Source Signal Scan

Before translating, build a source signal inventory:

- known marker types and standard screenplay-format candidates listed in
  `references/marker_inventory.md`
- unmatched all-caps, margin, revision, camera/shot, transition, or
  source-specific format evidence that should remain observable before
  translation

Stage 2 records three layers:

- `structural_signal`: known markers and structural candidates
- `warning_signal`: unclassified raw structural evidence that needs review
- `noise_signal`: low-confidence candidates ignored by the scanner

The marker inventory is the source of truth for known structure audits. Warning
and noise signals are traceability records, not schema extensions or rule
upgrades.

If no credible scene numbers are found, follow `references/industry_conventions.md`: record the absence, do not invent numbers, and use scene-heading navigation when useful.

## 4. Source Audit Gate

Do not produce formal translation output if source structure is not trustworthy.

Use `scripts/validate_sample.py` for the first real-file pass. Treat its report as the signal record between setup and translation.

Before creating translation draft batches, write a Stage 2 signal confirmation with `scripts/confirm_stage2.py`. The confirmation acknowledges that Stage 2 signals were recorded; it must not upgrade warning or noise signals into marker rules.

Fail the gate when:

- page mapping is ambiguous
- scene numbers appear to exist but cannot be reconciled
- omitted scenes lack source numbers where numbers exist
- marker extraction is clearly incomplete
- PDF duplicate text makes counts unreliable

Do not fail only because scene numbers are absent. See `references/industry_conventions.md` before treating missing production markers as a source problem.

## 5. Translation

Translate in small batch steps. Preserve all source content unless the user
explicitly asks for summary.

Each translation batch step should complete one current batch, run final batch
validation, and report the next batch step. Full-project automation resumes from
the reported next batch step. Continuous batch execution is allowed only when
explicitly authorized by the user and must follow `AI_AGENT_CONTRACT.md`; each
batch remains its own validated step, and FAIL, UNCERTAIN, tool errors, or
unclear next ranges stop the run.

Each formal translation batch should be written with final-quality intent on the first pass. A sample batch calibrates style, structure, and output format; it is not permission to produce a low-quality rough translation and rely on the user to catch mistakes. Keep token cost low by avoiding repeated full rewrites.

Human review should be limited to the planned gates: first-batch style
confirmation and final full-reader acceptance. Do not require per-batch user
confirmation after the style gate unless validation returns FAIL or UNCERTAIN.

When subtitles are present, parse them into normalized JSON before style
profiling, alignment, or translation review.

Use the project-local terminology baseline for every batch. During later
batches, add only genuinely new recurring terms or conflict resolutions; do not
rerun a full terminology review for each batch.

When high-quality Chinese subtitles are provided, use subtitle content directly
for dialogue translations and follow `references/subtitle_alignment.md` for
subtitle labels at the expression-unit level. AI translates non-dialogue
elements: action description, scene headings, parentheticals, format markers,
screen text, and reader notes.

Use the overall subtitle translation style as the primary input to
`work/style-profile.json`, then apply that style profile to non-dialogue
translation. Subtitle quality is judged by the user; this skill does not
automatically validate subtitle translation quality.

When subtitles are absent, omit subtitle labels and translate all elements with
professional screenplay judgment. Output quality depends on model judgment.

Create batch JSON that follows `references/batch_schema.md` before rendering HTML. Validate each batch with `scripts/validate_batch.py`.

Use `scripts/make_sample_batch.py` only for structural preview and pipeline validation from `source-markers.json`. It is not a translation draft and must not replace source-text extraction or human/model translation batches.

Use `scripts/draft_batch.py` to create a draft skeleton from `source-lines.json` before translation. Its translations are placeholders and must be replaced by actual translation work.

`draft_batch.py` requires `work/logs/stage-2-confirmation.json`. If Stage 2 signal records change, rerun `scripts/confirm_stage2.py` before creating new draft batches.

For low-cost samples or staged translation, pass `--display-page-start` and `--display-page-end` to create a draft batch for only the requested displayed screenplay pages. This is a workflow convenience only; it must not change source extraction, marker inventory, or page mapping rules.

Before formal translation of a current batch, prefer
`scripts/package_batch_context.py` to generate
`work/context/batch-context-pXXX-YYY.json` for the same displayed-page range.
Use that package as the default agent context instead of reading full
`source-lines.json`, full subtitles, or the full marker inventory. See
`references/batch_context.md`. If the package is insufficient, inspect only the
specific upstream artifact slice needed for the current batch ambiguity.

Exploratory or overlapping draft batches may be created while choosing the
formal batch range. Once the formal range is selected, delete abandoned or
superseded draft batch files before continuing translation. Keep only the
current batch draft and any already validated translated batches needed for the
reader output, so later stages cannot mistake a trial batch for active work.

When multiple translated batches make up one reader output, validate each batch first, then merge them with `scripts/merge_batches.py`. Do not let final HTML silently use only one 5-10 page batch as if it were the full screenplay.

Audit and final reader outputs must share the same formal translation text. Audit versions may expose batch IDs, structure types, marker counts, placeholder checks, and other engineering metadata. Final reader outputs should hide that noise and keep only reading aids such as page numbers, scene numbers, scene index, conventions, and necessary notes.

## 6. HTML Build

Batch HTML is a work artifact. Final HTML is the reading artifact.

Use HTML as the review, delivery, and reading format. It is easier to inspect on desktop and mobile, cheaper to iterate, and suitable for static hosting.

For final reader output, prefer `scripts/finalize_html.py`. It validates the final batch, builds HTML, runs the project audit for the selected displayed page range, and can optionally clean transient files. If no batch path is provided, it selects the largest `translated-*.json` batch under `work/batches/`.

Use `scripts/build_html.py` directly for previews and debugging. Generated screenplay-body markers must remain machine-readable so `scripts/audit.py` can compare them with the marker inventory.

When new source-visible formatting or screenplay structure appears, first decide
whether source evidence shows a screenplay, production, or reading function. If
so, capture it in the batch JSON with the existing schema surface before
rendering. Use entry types, markers, layout metadata, or inline markup as
appropriate, and let the HTML renderer restore the page-reading shape. Keep
low-confidence extraction artifacts in warning/noise records instead of reader
output. Do not solve format preservation by hand-editing generated HTML files.

When auditing a partial or full reader output, pass the intended displayed screenplay page range. The audit should report the HTML's actual `data-display-page` coverage and fail when expected body pages are missing, so a local 5-10 page batch cannot be mistaken for a larger reader output.

Final HTML should include:

- cover
- user-supplied Chinese title and translated physical title-page information
  when source rows are available
- reading note
- edition-wide format conventions and professional terms
- conventions
- scene index when source numbers exist, or scene-heading navigation when source numbers are absent
- page-ordered screenplay body
- structured marker attributes for screenplay-body scene numbers and format markers
- local reading-progress save and restore using browser storage

Final HTML should not include:

- task labels
- repeated indexes
- debug data
- duplicate covers
- temporary workflow notes
- repeated body notes for edition-wide formatting conventions

## 7. Static Publishing

GitHub Pages is the natural publishing extension for v0.1 because the final artifact is static HTML.

Static publishing should happen only after `scripts/finalize_html.py` and HTML audit pass. Keep generated project outputs out of the skill repository unless the user is intentionally publishing a specific reading edition.

## 8. Optional PDF Reflow

Page-aligned PDF is no longer a target. It made the Chinese edition crowded because translated text, annotations, and subtitle labels had to fit into the same physical page as the source.

If PDF output is deliberately reopened, treat it as a comfortable reading/print artifact:

- allow Chinese content to reflow across A4 pages
- use larger readable Chinese text and relaxed line spacing
- keep source-location labels such as "原剧本第 X 页"
- do not expose generated PDF page numbers as if they were source screenplay pages
- do not force one translated page to match one source PDF page

HTML remains the default review and delivery format.

## 9. Final Audit

Final audit compares source markers and HTML output. Structural failures must be fixed in extraction or generation, not by one-off manual edits to final files.
