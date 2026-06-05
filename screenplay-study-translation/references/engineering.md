# Engineering

This skill should be maintained like software, not a pile of one-off scripts.

## Principles

- Make the smallest change that solves the current problem.
- Do not refactor unrelated code while fixing translation or extraction bugs.
- Keep scripts focused and composable.
- Move logic to shared modules only when it is actually reused.
- Keep `SKILL.md` concise and move detailed domain knowledge, schemas, validation rules, and troubleshooting into `references/`.
- Prefer configuration over hard-coded film-specific data.
- Prefer source evidence and validation over hard-coded format assumptions.
- Establish domain conventions before encoding extraction heuristics. A missing or unusual structure may be normal for the script type.
- Auto-fix obvious local defects only when the fix is deterministic and traceable.
- Keep generated output reproducible.
- Do not commit real screenplay PDFs, subtitle files, or generated project outputs.
- Do not let mechanical formatting debt accumulate. Run Ruff on touched scripts when practical.
- Keep pure formatting changes separate from behavioral changes so reviews can distinguish style churn from logic changes.

## Hard-Coded Rule Guardrails

- Do not promote a pattern observed in one screenplay into a universal rule without a validation check and a fixture.
- Do not promote a failure observed in one screenplay into an extraction bug before checking industry conventions and script type.
- Regex may classify candidates, but it should not be the only authority for source structure such as scene numbers.
- Prefer a candidate -> validate -> promote flow. Preserve raw source text and expose assumptions such as margin width, page size, pairing rules, and text extraction coverage.
- Hard-coded defaults are acceptable for synthetic fixtures and CLI convenience only. Real-project assumptions should be configurable or reported in validation output.
- When changing extraction heuristics, add both a positive fixture and a negative fixture for the failure mode being fixed.
- If a heuristic could silently drop source structure, report the dropped or unmatched candidates as `WARN` before relying on the output.
- Keep project-specific terminology separate from general screenplay terminology. Do not bake a creator's personal wording into global validation rules.
- Do not confuse auto-correction with silent mutation. Store the original value, corrected value, reason, and confidence when practical.

## Reference Completeness

Before expanding tooling for a new capability, make sure the reference layer has enough coverage for:

- long-form workflow and validation standards
- domain conventions and industry norms
- file schemas and configuration contracts
- terminology and translation style decisions
- troubleshooting symptoms, causes, and remedies
- known failure modes and fixture expectations

Add references when the knowledge is reusable or too detailed for `SKILL.md`. Keep reference files one level below `references/` so they remain discoverable.

## Script Layers

Keep scripts small and composable. Do not merge them into a single CLI until the workflow has been validated across multiple real screenplays.

### Primary Workflow Scripts

These are the scripts an agent is most likely to use in a real project:

- `init_project.py`: create project config and directories
- `validate_sample.py`: run first-pass real sample structure validation
- `extract_pdf.py`: extract source text rows and coordinates into `source-lines.json`
- `scan_markers.py`: build source marker inventory
- `parse_subtitles.py`: normalize optional subtitles
- `draft_batch.py`: create placeholder translation batches from source lines and markers
- `merge_batches.py`: merge validated translated batches before final full-project HTML output
- `build_html.py`: build batch or final HTML while preserving structured markers
- `finalize_html.py`: validate final batch, build HTML, audit output, and optionally clean transient files
- `clean_project.py`: clean transient preview outputs from a generated project after milestone output is built

### Validation And Audit Scripts

These scripts gate structure and output quality:

- `validate_batch.py`: validate translation batch JSON shape
- `audit_draft.py`: inspect generated draft batches before formal translation
- `audit.py`: validate source, HTML output, and optional displayed-page ranges

### Legacy Or Experimental Output Scripts

These scripts are not part of the v0.1 HTML-first target. Keep them out of the normal user workflow unless the project deliberately reopens that output path:

- `export_pdf.py`: deterministic PDF smoke/export interface retained for experiments

### Development Fixture Scripts

These scripts support tests, fixtures, and internal validation. They should not be presented as the normal user workflow:

- `make_sample_batch.py`: create marker-only structure previews, not translation drafts
- `batch_markers.py`: derive a marker inventory from a batch for fixture and range-audit workflows
- `make_pdf_fixture.py`: create synthetic PDF fixtures
- `assert_marker_counts.py`: assert fixture marker counts
- `smoke.py`: run deterministic regression tests

## Quality Gates

Run the low-cost smoke gate first:

```bash
python screenplay-study-translation/scripts/smoke.py
```

The smoke gate generates its PDF scan fixture in a temporary directory and does not write generated artifacts into the repository.

Committed fixtures should be small, synthetic, and legally safe. Generated files belong in `work/`, `dist/`, or a temporary directory unless they are deliberately tiny fixture expectations.

Recommended full checks:

```bash
python -m compileall screenplay-study-translation/scripts
python -m ruff check screenplay-study-translation/scripts
python -m ruff format --check screenplay-study-translation/scripts
```

When a formatting backlog exists, clear it as a dedicated style-only change:

```bash
python -m ruff format screenplay-study-translation/scripts
python screenplay-study-translation/scripts/smoke.py
python -m ruff check screenplay-study-translation/scripts
python -m ruff format --check screenplay-study-translation/scripts
```

If optional dependencies are not installed, at minimum run syntax checks and the project audit.

For repository template smoke tests, use:

```bash
python screenplay-study-translation/scripts/audit.py screenplay-study-translation/assets/project.example.yaml --allow-missing-inputs
```

Do not use `--allow-missing-inputs` for real project delivery audits.

## Token And Cost Control

- Use targeted search and structured reports.
- Print only differences and compact statistics.
- Work in 5-10 page batches.
- Produce and audit HTML before considering any publishing layer.
