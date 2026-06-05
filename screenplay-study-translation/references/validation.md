# Validation

Validation is a gate, not a final courtesy check. It should catch structural failures before the user performs translation-quality review.

## Result Levels

- `FAIL`: must fix before final output
- `WARN`: high-risk item for human or model review
- `INFO`: statistics

Reports should print only differences, locations, and compact summaries. Do not dump full screenplay text.

For first real-file validation, use `scripts/validate_sample.py`. It should create `work/reports/sample-validation.txt` and avoid translation output.

## Assumption Checks

Validation should report structural assumptions before translation begins:

- page size and page mapping source
- scene-number margin and pairing behavior
- unmatched scene-number candidates
- whether credible scene numbers were absent and navigation should fall back to scene headings
- unsupported or suspicious PDF text extraction patterns
- fallback text-count checks used instead of structured markers

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

- source scene numbers vs HTML scene numbers
- when source scene numbers are absent, verify that final output does not invent numbered scene markers; scene-heading navigation is acceptable
- scene number checks count source marker instances, including left/right side-margin duplicates
- source `OMITTED` count and numbered omitted scenes vs output
- source `CONT'D` count vs speaker continuation marks
- source `MORE` count vs output continuation-page marks
- source split scene markers vs output anchors and scene index
- `V.O.`, `O.S.`, and `O.C.` marker counts vs translated speaker/source labels
- page count and page mapping

For partial samples, audit the same displayed page range as the generated batch. Use `scripts/audit.py --display-page-start N --display-page-end M` so partial HTML is not compared against the full-project marker inventory.

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
- inline reader markup renders as HTML underline, bold, or italic without exposing raw markup characters in final output

Batch checks:

- batch JSON follows `references/batch_schema.md`
- no subtitle labels when subtitles are absent
- every entry keeps source page and display page
- every entry has non-empty source and translation text
- final batches pass `scripts/validate_batch.py --final`, with no draft placeholders or raw untranslated screenplay format markers
- final batches use reader inline markup when applicable: `__proper names__`, `**sound/on-screen emphasis**`, and `*screenplay terms*`
- draft batch structure is audited before translation, including suspicious dialogue runs, unclosed parentheticals, scene headings without scene-number markers, and placeholder translations

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

Unknown terms should be recorded for classification into:

- general screenplay terminology
- project-specific terminology
- author-specific usage
- extraction noise

## Failure Philosophy

If a structural audit fails, repair extraction, marker mapping, or generation logic first. Do not let final output depend on hand edits that cannot be reproduced.
