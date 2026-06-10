# Batch Context Package

`scripts/package_batch_context.py` builds a compact, read-only work package for
one displayed-page translation range.

It exists to reduce agent context cost during translation. It is not a pipeline
stage, not a validation gate, and not a replacement for source extraction,
marker inventory, subtitle normalization, style profile, terminology, or final
batch validation.

## Purpose

Use the package as the default material the agent reads for the current batch.
The agent should not read full `source-lines.json`, full `subtitles.json`, or
full `source-markers.json` unless the package is insufficient for a specific
local ambiguity.

## Command

```bash
python3 scripts/package_batch_context.py project.yaml \
  --display-page-start 11 \
  --display-page-end 15
```

Default output:

```text
work/context/batch-context-p011-015.json
```

Use `--include-source-rows` only when debugging extraction or page-boundary
issues. Normal translation should rely on `source_entries`, not raw source row
excerpts.

## Inputs

The packer reads existing project artifacts:

- `work/source-lines.json`
- `work/source-markers.json`
- `work/subtitles.json` when present
- `work/style-profile.json` when present
- project-local `references/terminology.md` when present
- previous translated batch tail when present

Stage 2 confirmation is required before packaging, matching the same pre-batch
boundary as `scripts/draft_batch.py`.

## Output Shape

```json
{
  "version": 1,
  "kind": "translation_batch_context",
  "project": {},
  "batch": {},
  "sources": {},
  "source_entries": [],
  "markers": [],
  "signals": {},
  "subtitle_candidates": {},
  "terminology": {},
  "style_summary": {},
  "continuity": {},
  "agent_notes": []
}
```

## Field Meaning

- `source_entries`: current batch source entries classified like a draft batch,
  without placeholder translations. This is the primary translation input.
- `markers`: known markers in the current range plus configured overlap.
- `signals`: nearby warning/noise records for traceability; these do not create
  new rules.
- `subtitle_candidates`: compact advisory subtitle evidence searched across
  the full subtitle file by source text and terminology evidence, without
  assuming subtitle order matches screenplay order. It may include
  `advisory_matches` per dialogue unit. If no reliable candidate is found, the
  candidate list should stay empty rather than guessing from timeline position.
  These candidates do not decide `字幕匹配`, `字幕差异`, or `字幕未见`; the agent still
  applies semantic expression-unit judgment.
- `terminology.relevant_terms`: current-range subset selected from the
  project-local terminology baseline.
- `style_summary`: compact style-profile summary for this batch.
- `continuity`: tail of the previous translated batch for voice, terminology,
  and page-boundary continuity.

## Constraints

- Do not edit package output by hand.
- Do not treat package output as validation evidence.
- Do not infer full-project subtitle alignment or scene order from advisory
  candidates.
- Do not use package generation to bypass Stage 2 confirmation.
- If the package lacks necessary local evidence, read the specific upstream
  artifact slice needed to resolve that ambiguity, then continue with the
  current batch only.
