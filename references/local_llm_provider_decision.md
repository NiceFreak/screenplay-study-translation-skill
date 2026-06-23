# Local LLM Provider Decision

This document records the decision from the local-model cost discussion on
2026-06-23. It is a product and engineering decision note only; it does not
define runtime execution control, pipeline stage transitions, validation gates,
or implementation details.

## Decision

Do not make a local model such as quantized Gemma 4 the default formal
translator for screenplay batches.

Treat local LLM support as an optional, experimental provider path that must
prove itself on current-batch translation quality, schema reliability, and
end-to-end repair cost before it can be used for production translation.

The preferred first step is a small A/B trial on one current batch, not a
full-provider rollout.

## Current Facts

- The repository does not currently contain a general LLM provider abstraction.
  Existing scripts extract source text, scan markers, create draft batches,
  package compact batch context, validate translated batch JSON, render HTML,
  merge batches, finalize HTML, and export EPUB.
- The actual translation boundary is the creation of a valid
  `work/batches/translated-pXXX-YYY.json` artifact.
- The stable integration surface is the translation batch JSON contract in
  `references/batch_schema.md`.
- `scripts/package_batch_context.py` already creates a compact read surface for
  the current displayed-page range. This is the natural input for any future
  provider, local or remote.
- `scripts/validate_batch.py --final` already checks the formal translated
  batch artifact. It can be reused after a local-model attempt.
- `scripts/cost_report.py` is an artifact-size proxy, not billing authority.
  Real translation cost must come from a clean translation session's runtime
  usage report or provider console.
- Existing cost controls are already active: subtitle reuse for matched
  dialogue, compact current-batch context, 5-10 page batches, and prompt-cache
  friendly continuous sessions.
- With high-quality Chinese subtitles, dialogue translation cost is already
  compressed. The remaining model-heavy work is mainly non-dialogue translation:
  action, atmosphere, scene headings, parentheticals, transitions, screen text,
  format markers, and reader-facing notes.
- Non-dialogue has no subtitle backstop. The reader depends on the model's
  translation quality there.
- As of 2026-06-23, Google's Gemma 4 documentation describes Gemma 4 as an open
  model family with official quantization-aware training variants for more
  efficient local deployment.
- As of 2026-06-23, Ollama documents OpenAI-compatible API surfaces that can be
  used by local applications. This makes a local provider technically plausible.

External references:

- Google Gemma 4 overview:
  <https://ai.google.dev/gemma/docs/core>
- Google Gemma 4 QAT announcement:
  <https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/>
- Ollama OpenAI compatibility:
  <https://docs.ollama.com/api/openai-compatibility>

Internal references:

- `references/batch_schema.md`
- `references/batch_context.md`
- `references/workflow.md`
- `references/cost.md`
- `scripts/package_batch_context.py`
- `scripts/validate_batch.py`
- `scripts/cost_report.py`

## Cost Assessment

A local model can reduce the recurring remote API bill for the translation
step. If the local model runs on already-owned hardware, the marginal provider
bill can approach zero.

This does not automatically mean the total cost of producing a screenplay study
edition goes down. The real cost includes:

- remote model tokens, when used
- local hardware time and energy
- setup and maintenance time
- failed JSON generations
- validation retries
- manual review time
- retranslation or repair by a stronger model
- quality regressions that reach final review

The current architecture is already close to its safe cost floor for the ideal
input case: official screenplay PDF plus high-quality bilingual subtitles. The
largest remaining zero-risk lever is still runtime prompt caching in one
continuous translation session.

Local-model use should therefore be evaluated as a total-cost experiment, not
as a token-price substitution.

## Quality Risk

The central risk is not whether a local model can produce Chinese text. The risk
is whether it can reliably produce final-quality screenplay study translation
inside the existing schema.

High-risk surfaces:

- Non-dialogue translation quality. This is the load-bearing surface of the
  edition and cannot be checked by readers who do not trust the source language.
- Scene headings and screenplay format markers. Literal or raw English residue
  can pass casual review while damaging the study edition.
- Terminology consistency. Subtitle-derived proper nouns and project-local
  terms must remain stable across batches.
- Subtitle label judgment. Dialogue labels must be decided at the
  expression-unit level, not by mechanically accepting advisory candidates.
- JSON and schema compliance. A provider that frequently emits malformed JSON or
  changes source fields will create repair work.
- Inline markup and structural preservation. Proper names, emphasis, screen
  text, revision marks, and source-visible structure must use the existing batch
  schema surface.
- Long-range continuity. Current-batch context includes a previous-batch tail,
  but local models may still drift in voice or terminology across a full script.
- False confidence. A local model may pass mechanical validation while still
  degrading prose quality.

Validation can catch some structural failures. It cannot fully prove literary,
cinematic, or professional translation quality.

## Engineering Feasibility

Local provider support is feasible because the system already has a narrow
artifact boundary:

1. Generate or read the current `batch-context-pXXX-YYY.json`.
2. Produce a `translated-pXXX-YYY.json` batch that preserves source IDs, entry
   order, page mapping, markers, and schema.
3. Run existing final batch validation.
4. Render an HTML preview from the same translated batch.

No renderer rewrite, batch schema change, or finalization change is required for
an initial experiment.

The smallest viable integration would be an optional translation executor that
turns one current batch context into one translated batch artifact. The executor
should not own stage advancement, continuous batch execution, validation policy,
or final HTML generation.

## Execution Plan

### Phase 0: Baseline

Before changing provider behavior, collect a clean baseline from a normal
translation session:

- Use one session dedicated to translation, not code changes or design work.
- Use the normal workflow and current strong model.
- Record real runtime cost from the runtime usage report or provider console.
- Keep `scripts/cost_report.py` output as a supporting artifact-size proxy only.
- Record validation failures, retries, and manual correction time.

Without this baseline, any claimed saving is uncertain.

### Phase 1: One-Batch Local Trial

Run a local model on exactly one 5-10 displayed-page batch.

Use a batch that contains a representative mix of:

- action description
- scene headings
- parentheticals
- dialogue with subtitle candidates
- proper nouns or project terms
- at least one formatting or markup-sensitive case when available

Compare local-model output against the baseline model on the same batch.

The trial should measure:

- final validation result
- malformed JSON rate
- placeholder or raw marker residue
- terminology warnings
- missing subtitle labels
- non-dialogue translation quality
- manual repair minutes
- whether a stronger model had to repair or retranslate the batch

### Phase 2: Limited Expansion

Only expand to more batches if Phase 1 passes both mechanical validation and
human quality review with low repair effort.

The second trial should include a different type of batch, such as a dense
action sequence, fragmented dialogue scene, or formatting-heavy page range.

### Phase 3: Optional Provider Documentation

If local trials are successful, document a provider option separately from the
core workflow.

The provider documentation should make clear:

- local provider use is optional
- provider output must still pass existing validation
- current-batch execution boundaries remain unchanged
- quality comparison against a strong baseline is required before production use
- local-model pricing should not be represented as real cost savings until
  repair time is counted

## Acceptance Criteria

A local provider can be considered production-eligible only if it satisfies all
of these conditions across representative batches:

- Produces valid translated batch JSON without manual structural repair.
- Preserves source IDs, source text, page fields, marker identity, entry order,
  and existing schema.
- Passes `scripts/validate_batch.py --final`.
- Reuses subtitle Chinese appropriately for matched dialogue.
- Assigns subtitle labels according to expression-unit judgment.
- Maintains project terminology without recurring warnings.
- Produces non-dialogue translation that is acceptable without a strong-model
  rewrite.
- Does not increase total elapsed production time after setup overhead is
  excluded.
- Shows a measured total-cost improvement against the baseline, including
  repair and review time.

## Non-Goals

- Do not replace the current workflow with a local-model-first workflow yet.
- Do not change batch schema to accommodate local-model weaknesses.
- Do not weaken validation to make local output pass.
- Do not treat lower token price as sufficient evidence of lower production
  cost.
- Do not use local models to trade away non-dialogue translation quality.
- Do not add provider-specific behavior to rendering, merging, finalization, or
  EPUB export.

## Recommended Position

Local Gemma 4-style models are worth testing because the artifact boundary is
clean and the potential remote API bill reduction is real.

They should not be trusted as the default production translator until measured
on this project's actual load-bearing surface: final-quality non-dialogue
screenplay translation under the existing batch schema.

The prudent path is:

1. Keep the current strong-model workflow as the production baseline.
2. Add local-provider support only as an optional experiment after baseline
   measurement.
3. Gate expansion by validation, human quality review, and total-cost evidence.

