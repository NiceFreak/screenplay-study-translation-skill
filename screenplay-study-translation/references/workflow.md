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
- optional subtitle path
- source and target languages
- desired HTML output path
- page mapping rule
- likely script type when known: reading draft, spec script, production draft, shooting script, teleplay, or other house format

If the user provides an existing generated project, inspect its scripts before editing outputs.

If the project has no `project.yaml`, initialize the standard directory structure with `scripts/init_project.py`. Do not move or copy user PDFs unless explicitly requested; write their paths into configuration.

For a first real sample, run `scripts/validate_sample.py` before translation. It should produce a compact structure report under `work/reports/`.

Use `scripts/extract_pdf.py` to create `work/source-lines.json` when preparing translation batches. Treat it as source review data, not as proof that PDF extraction is complete.

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

## 3. Source Marker Scan

Before translating, build a source marker inventory:

- scene numbers
- `OMITTED`
- `CONT'D`
- `MORE`
- split or continuation scene numbers such as `pt2`, `pt3`
- `INT.`, `EXT.`, `V.O.`, `O.S.`, `O.C.`
- transitions and camera/format markers
- unusual uppercase terms

The marker inventory is the source of truth for structure audits.

If no credible scene numbers are found, follow `references/industry_conventions.md`: record the absence, do not invent numbers, and use scene-heading navigation when useful.

## 4. Source Audit Gate

Do not produce formal translation output if source structure is not trustworthy.

Use `scripts/validate_sample.py` for the first real-file pass. Treat its report as the boundary between setup and translation.

Fail the gate when:

- page mapping is ambiguous
- scene numbers appear to exist but cannot be reconciled
- omitted scenes lack source numbers where numbers exist
- marker extraction is clearly incomplete
- PDF duplicate text makes counts unreliable

Do not fail only because scene numbers are absent. See `references/industry_conventions.md` before treating missing production markers as a source problem.

## 5. Translation

Translate in small batches. Preserve all source content unless the user explicitly asks for summary.

Each formal translation batch should be written with final-quality intent on the first pass. A sample batch calibrates style, structure, and output format; it is not permission to produce a low-quality rough translation and rely on the user to catch mistakes. Keep token cost low by avoiding repeated full rewrites.

Use reference subtitles for rhythm, established names, and likely film wording. Do not copy subtitle errors when the screenplay meaning is clear.

When subtitles are absent, omit subtitle labels and translate directly with professional screenplay and subtitle judgment.

When subtitles are present, parse them into normalized JSON before alignment or translation review.

Create batch JSON that follows `references/batch_schema.md` before rendering HTML. Validate each batch with `scripts/validate_batch.py`.

Use `scripts/make_sample_batch.py` only for structural preview and pipeline validation from `source-markers.json`. It is not a translation draft and must not replace source-text extraction or human/model translation batches.

Use `scripts/draft_batch.py` to create a draft skeleton from `source-lines.json` before translation. Its translations are placeholders and must be replaced by actual translation work.

For low-cost samples or staged translation, pass `--display-page-start` and `--display-page-end` to create a draft batch for only the requested displayed screenplay pages. This is a workflow convenience only; it must not change source extraction, marker inventory, or page mapping rules.

When multiple translated batches make up one reader output, validate each batch first, then merge them with `scripts/merge_batches.py`. Do not let final HTML silently use only one 5-10 page batch as if it were the full screenplay.

Audit and final reader outputs must share the same formal translation text. Audit versions may expose batch IDs, structure types, marker counts, placeholder checks, and other engineering metadata. Final reader outputs should hide that noise and keep only reading aids such as page numbers, scene numbers, scene index, conventions, and necessary notes.

## 6. HTML Build

Batch HTML is a work artifact. Final HTML is the reading artifact.

Use HTML as the review, delivery, and reading format. It is easier to inspect on desktop and mobile, cheaper to iterate, and suitable for static hosting.

For final reader output, prefer `scripts/finalize_html.py`. It validates the final batch, builds HTML, runs the project audit for the selected displayed page range, and can optionally clean transient files. If no batch path is provided, it selects the largest `translated-*.json` batch under `work/batches/`.

Use `scripts/build_html.py` directly for previews and debugging. Generated screenplay-body markers must remain machine-readable so `scripts/audit.py` can compare them with the marker inventory.

Final HTML should include:

- cover
- reading note
- conventions
- scene index when source numbers exist, or scene-heading navigation when source numbers are absent
- page-ordered screenplay body
- structured marker attributes for screenplay-body scene numbers and format markers

Final HTML should not include:

- task labels
- repeated indexes
- debug data
- duplicate covers
- temporary workflow notes

## 7. Static Publishing

GitHub Pages is the natural publishing extension for v0.1 because the final artifact is static HTML.

Static publishing should happen only after `scripts/finalize_html.py` and HTML audit pass. Keep generated project outputs out of the skill repository unless the user is intentionally publishing a specific reading edition.

## 8. Optional PDF Reflow

Page-aligned PDF is no longer a target. It made the Chinese edition crowded because translated text, annotations, and subtitle labels had to fit into the same physical page as the source.

If PDF output is deliberately reopened, treat it as a comfortable reading/print artifact:

- allow Chinese content to reflow across A4 pages
- use larger readable Chinese text and relaxed line spacing
- keep source-location labels such as "原版第 X 页"
- do not expose generated PDF page numbers as if they were source screenplay pages
- do not force one translated page to match one source PDF page

HTML remains the default review and delivery format.

## 9. Final Audit

Final audit compares source markers and HTML output. Structural failures must be fixed in extraction or generation, not by one-off manual edits to final files.
