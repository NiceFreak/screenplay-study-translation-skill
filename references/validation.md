# Validation

Validation is a gate, not a final courtesy check. It should catch structural failures before the user performs translation-quality review.

## Result Levels

- `FAIL`: must fix before final output
- `WARN`: high-risk item for human or model review
- `INFO`: statistics

Reports should print only differences, locations, and compact summaries. Do not dump full screenplay text.

For first real-file validation, use `scripts/validate_sample.py`. It validates Stage 1-2 only by default, should avoid translation output, and should create:

- `work/reports/sample-validation.txt`
- `work/reports/subtitle-report.txt` when subtitles are configured
- `work/logs/stage-1-2-findings.json`

Run `scripts/extract_pdf.py` before `scripts/validate_sample.py`. Validation must first check the Stage 1 extraction completeness gate:

- compare the physical PDF page count with the physical pages represented in `source-lines.json`
- if `source-lines.json` is missing, invalid, or does not cover every physical PDF page, output `UNCERTAIN`
- halt before Stage 2 source scan when extraction completeness is not verified
- do not infer why pages are missing without explicit source evidence

Use `--include-output-audit` only when intentionally checking existing reader
outputs from a previous stage. PDF output is deprecated; any configured PDF
audit is legacy-only.

Before Stage 3 batch creation, confirm Stage 2 signal recording with `scripts/confirm_stage2.py`. It writes `work/logs/stage-2-confirmation.json`. Stage 3 draft creation must fail when this confirmation is missing, stale, or unapproved.

`scripts/diagnostic_report.py` may write
`work/diagnostic/diagnostic_report.json` after Stage 2 validation artifacts
exist. This report is observation-only: it summarizes system state, key signals,
existing failure-mode matches, likely causes, and recommended checks. It must
not change validation results, gates, contracts, schemas, or trigger automatic
repair behavior.

## Assumption Checks

Validation should report structural assumptions before translation begins:

- page size and page mapping source
- scene-number margin and pairing behavior
- known structural signals
- unclassified warning signals
- low-confidence noise signals
- whether credible scene numbers were absent and navigation should fall back to scene headings
- unsupported or suspicious PDF text extraction patterns
- fallback text-count checks used instead of structured markers
- source-lines displayed page coverage and any missing displayed pages

Do not treat a clean count as reliable when the underlying extraction assumptions are hidden.

## Auto-Correction Policy

Some source or extraction defects should be fixed automatically when the correction is obvious, local, low-risk, and recoverable from context. Examples include a missing printed page number in an otherwise continuous page sequence, extraction-split words that can be rejoined by coordinates, or a clear one-character OCR/text-layer split at a line edge.

Auto-corrections should:

- preserve the original source text in work artifacts
- record what was corrected and why in compact metadata or reports
- avoid changing literary meaning, dialogue wording, scene numbering, or chronology without review
- stay invisible in final reader-facing output unless the correction changes interpretation

Escalate to `WARN` or `FAIL` when the correction is ambiguous, global, meaning-changing, or dependent on project-specific judgment.

For printed page numbers, infer missing values only from a stable explicit sequence across extracted pages. Store both `display_page` and inferred `printed_page`; do not rewrite PDF page numbers or source marker coordinates.

## Required Audits

Source-to-output checks:

- known marker counts from `references/marker_inventory.md` vs generated HTML
  structured markers
- source scene numbers vs HTML scene numbers
- when source scene numbers are absent, verify that final output does not invent numbered scene markers; scene-heading navigation is acceptable
- scene number checks count source marker instances, including left/right side-margin duplicates
- source `OMITTED` count and numbered omitted scenes vs output
- source `CONT'D` count vs speaker continuation marks
- source `MORE` count vs output continuation-page marks
- source split scene markers vs output anchors and scene index
- `V.O.`, `O.S.`, and `O.C.` marker counts vs translated speaker/source labels
- page count, page mapping, and HTML displayed-page coverage

For partial samples, audit the same displayed page range as the generated batch. Use `scripts/audit.py --display-page-start N --display-page-end M` so partial HTML is not compared against the full-project marker inventory and missing HTML pages are reported explicitly.

HTML checks:

- no duplicate final scene index
- no task labels in final output
- no debug or workflow sections
- screenplay-body structure markers use `data-marker-type` or `marker-*`
- scene index links resolve
- no raw screenplay terms without Chinese translation or explanation
- no subtitle labels when subtitles are absent
- no stale generic action-summary text
- internal links such as scene index anchors resolve to existing HTML element ids
- `data-display-page` coverage matches the requested displayed screenplay page range
- inline reader markup renders as HTML underline, bold, italic, or reader-annotation styling without exposing raw markup characters in final output
- trailing `[[*]]` source revision marks render as right-aligned revision asterisks, not inline reader annotations
- confirmed source-visible formatting and screenplay structure captured in entry type, markers, layout metadata, or inline markup is represented in generated HTML rather than normalized into ordinary prose
- final HTML includes local reading-progress save and restore behavior without overriding explicit hash navigation

Batch checks:

- batch JSON follows `references/batch_schema.md`
- no subtitle labels when subtitles are absent
- when subtitles are present, dialogue entries follow
  `references/subtitle_alignment.md` at the expression-unit level
- every entry keeps source page and display page
- every entry has non-empty source and translation text
- final batches pass `scripts/validate_batch.py --final`, with no draft placeholders or raw untranslated screenplay format markers
- final batches use reader inline markup when applicable: `__proper names__`, `**source emphasis**`, `*source italic*`, and `[[reader annotations]]`
- draft batch structure is audited before translation, including suspicious dialogue runs, unclosed parentheticals, scene headings without scene-number markers, and placeholder translations
- project-specific terminology checks should use the generated project's local
  `references/terminology.md`
- machine-checkable terminology should favor stable terms that do not create
  substring conflicts with longer names or phrases
- when a source term appears in one entry, validation expects the corresponding
  Chinese term in that entry; cross-entry literary phrasing may require a
  documented exception or warning
- reader `note` entries are allowed additions when tied to evidence in the same
  batch range; structure checks should exclude those notes from source-entry
  preservation counts and expect them to render with distinct note styling

## Warnings

Warn, do not fail, for:

- unknown uppercase terms
- no credible scene numbers in a reading/spec/public screenplay PDF
- final batches with no inline reader markup
- project-specific or author-specific terminology
- unusually short translations for long action blocks
- subtitle matches with low confidence
- frequent subtitle differences in a small range
- new proper names without project term entries
- short or ambiguous project terms that may match inside longer source terms

Unknown structural source evidence should be recorded as warning or noise signals,
not promoted into marker schema. Unknown terms should be recorded for
classification into:

- general screenplay terminology
- project-specific terminology
- author-specific usage
- extraction noise

## Failure Philosophy

If a structural audit fails, repair extraction, marker mapping, or generation logic first. Do not let final output depend on hand edits that cannot be reproduced.
