# Failure Modes

Records recurring failure patterns observed in real projects.

Distinction from troubleshooting.md:

- troubleshooting.md: how to handle a symptom when it occurs
- failure_modes.md: why a class of problem keeps recurring, and how to prevent it

-----

## Entry Format

```
Name:
Symptoms:
Root Cause:
Prevention:
Remediation:
Status: OPEN / RESOLVED / MONITORED
```

Status meanings:

- `OPEN`: The failure mode is currently unmitigated or actively recurring.
- `RESOLVED`: A concrete gate, script check, contract rule, or regression
  prevents the known failure path.
- `MONITORED`: Guidance exists, but prevention still depends on agent judgment,
  project context, or future real-project evidence.

-----

## FM-001 Format Anomalies Discovered Mid-Translation

Name: Late Discovery of Format Anomalies
Symptoms: A non-standard formatting pattern is found partway through translation, requiring the batch to be interrupted and a new session opened to handle it.
Root Cause: No complete source signal scan was performed before translation began.
Prevention: Enforce the SOURCE SCAN signal report gate. Stage 2 records known structural signals, warning signals, and noise signals before STAGE 3 begins. `draft_batch.py` must block when the Stage 2 signal confirmation is missing, stale, or unapproved.
Remediation: Interrupt current batch, record the signal in the appropriate Stage 2 layer, then resume translation after the signal record is confirmed.
Status: RESOLVED

-----

## FM-002 Project-Specific Extraction Rules Promoted to Global Rules

Name: Single-Project Rule Pollution
Symptoms: A formatting handling pattern from one screenplay is hard-coded into scripts or prompts, causing errors on other screenplays.
Root Cause: No distinction made between rules specific to one screenplay and rules applicable to all screenplays.
Prevention: Before adding any extraction rule, check industry_conventions.md to confirm whether it is an industry convention or a project-specific pattern. Every rule should have both a positive and a negative fixture.
Remediation: Convert the rule to a configurable option or restrict its scope. Record in engineering.md under Hard-Coded Rule Guardrails.
Status: MONITORED

-----

## FM-003 OUT OF SCOPE FINDING Silently Discarded

Name: Cross-Stage Findings Lost
Symptoms: A problem detected in one stage is not recorded and resurfaces in a later stage, requiring repeated diagnosis.
Root Cause: When AI cannot handle an issue in the current stage, it silently ignores it rather than recording it.
Prevention: AI_AGENT_CONTRACT Finding Retention Rule requires all OUT OF SCOPE FINDINGs to be written to work artifacts, validation report, or execution log.
Remediation: Add the missing record to work/logs and classify it using the appropriate output state.
Status: MONITORED

-----

## FM-004 Draft Placeholders in Final Output

Name: Draft Placeholders Reaching Final Output
Symptoms: Final HTML contains untranslated placeholders or raw format markers.
Root Cause: Output from draft_batch.py was used directly as a translation batch without actual translation.
Prevention: All final translation batches must pass validate_batch.py –final. Any placeholder triggers FAIL.
Remediation: Replace all placeholders and re-run validation.
Status: RESOLVED

-----

## FM-005 Workflow Gates Exist in Documentation but Not in Project State

Name: Documentation-Only Quality Gates

Symptoms:
A workflow step is documented as mandatory, but project execution can continue without machine-verifiable evidence that the step was completed.

Examples include:

* source signal review not enforced by pipeline state
* finding retention depending on agent behavior
* issue lifecycle existing only in documentation
* batch integrity only partially validated

Root Cause:
Critical workflow gates are defined in project documentation and agent instructions, but are not represented as machine-readable project state or enforced by tooling.

The system relies on AI compliance rather than verifiable execution artifacts.

Prevention:
Treat documented workflow gates as hypotheses until a corresponding project artifact, validation report, or audit record exists.

When introducing a new gate, define:

* what artifact proves completion
* where the artifact is stored
* how later stages verify it

Remediation:
When a workflow failure is discovered, first determine whether the gate existed only in documentation.

If so:

1. Record the gap in failure_modes.md
2. Add the missing verification procedure to project documentation
3. Do not assume future agents will remember the requirement without evidence

Status: MONITORED

-----

## FM-006 PDF Content Stream Truncated At Newline Boundary

Name: PDF Stream Tail Byte Dropped
Symptoms: One physical PDF page is visible in a reader but has no rows in `source-lines.json`, causing a displayed screenplay page gap.
Root Cause: PDF content streams were extracted with a regex ending at `\nendstream`. If compressed stream data itself ended with a newline or carriage-return byte, the extractor treated that byte as the stream delimiter and truncated the compressed data. Flate decompression then failed and the whole page was silently lost.
Prevention: Read PDF stream bytes using `/Length` when available before falling back to delimiter-based extraction. Add regression coverage for compressed streams whose final byte is `\n` or `\r`.
Remediation: Fix stream extraction, rerun `extract_pdf.py`, rerun `validate_sample.py`, reconfirm Stage 2, and regenerate any affected draft batches.
Status: RESOLVED

-----

## FM-007 Draft Batch Promoted as Translated Batch

Name: False Resolution — Draft Promoted as Translation
Symptoms: translated-*.json files appear in work/batches/ but contain placeholder text instead of real translation. validate_batch.py without --final flag does not catch this.
Root Cause: AI resolved "how to continue translation" by copying draft files to translated files. This is a False Resolution failure — AI produced a plausible-sounding solution that bypassed the actual translation work.
Prevention: translated-*.json must only be produced by real translation work, never by scripts that copy or rename draft files. Always run validate_batch.py with --final when validating formal batches.
Remediation: Delete all incorrect translated-*.json files. Remove the script that produced the incorrect behavior. Resume translation from the corresponding draft batches.
Status: RESOLVED

-----

## FM-008 Full Automation Interpreted As Unbounded Multi-Batch Execution

Name: Unbounded Multi-Batch Execution Chain
Symptoms: A request to continue remaining batches expands into planning or
execution across many future batches, causing unstable sessions, long tool
chains, or loss of the current batch boundary.
Root Cause: Full-project automation was interpreted as permission to run all
remaining batches as one unbounded execution instead of a sequence of validated
batch steps.
Prevention: Follow AI_AGENT_CONTRACT Section 3.1. Continuous batch execution is
allowed only when explicitly authorized by the user; even then, each batch is a
separate validated step and the run stops on FAIL, UNCERTAIN, tool error, or an
unclear next range.
Remediation: Stop the unstable execution, identify the last validated translated
batch, and resume from the next batch step.
Status: RESOLVED

-----

## FM-009 Synthetic Threshold Promoted to Global Rule

Name: Uncalibrated Numeric Threshold
Symptoms: A numeric threshold introduced for a smoke fixture is documented as a
project rule, even though it has no real-project or industry calibration.
Root Cause: A deterministic test needed a clean pass/fail boundary, and the
fixture boundary was mistaken for domain guidance.
Prevention: Before documenting a threshold, identify the calibration dataset,
measurement target, and failure tradeoff. If those do not exist, write the rule
as qualitative guidance and keep mechanical checks advisory.
Remediation: Remove the fixed threshold from normative documentation and tests,
then point agents to the qualitative reference rule.
Status: RESOLVED

-----

## FM-010 Subtitle Labels Assigned Below The Spoken Unit

Name: Fragment-Level Subtitle Labeling
Symptoms: One spoken turn contains mixed `字幕匹配`, `字幕差异`, and `字幕未见` labels even though the source dialogue reads as one utterance.
Root Cause: Subtitle comparison was applied to raw PDF rows or individual subtitle events instead of the complete spoken expression. Both the screenplay and the reference subtitles may split one utterance across multiple physical rows, line breaks, or timed events.
Prevention: Build the comparison unit from adjacent dialogue rows and relevant subtitle events before assigning a label. Treat mixed labels inside one spoken turn as evidence that the comparison granularity is too small.
Remediation: Re-evaluate the affected dialogue at expression-unit level, update batch labels, and keep reference subtitle events as evidence rather than independent label authorities.
Status: MONITORED

-----

## FM-011 Source Emphasis Conflated With Reader Annotation

Name: Overloaded Inline Emphasis
Symptoms: Bold or italic reader styling is used for sound cues, screen text, terminology explanations, source emphasis, and PDF style preservation at the same time, making the rendered meaning ambiguous.
Root Cause: The batch schema had too few inline markup roles, so source styling and reader-facing explanatory emphasis shared the same HTML presentation.
Prevention: Preserve source bold and italic only when the source carries that style evidence. Use a separate reader annotation style for sound cues, screen text, screenplay terminology, abbreviations, and format notes.
Remediation: Move reader-facing hints to `[[...]]` markup, keep `**...**` and `*...*` for source emphasis/style, and verify that the reading note explains the distinction.
Status: RESOLVED

-----

## FM-012 Reader Notes Rendered As Screenplay Body Text

Name: Undifferentiated Reader Notes
Symptoms: Translator notes, source annotations, or explanatory front-matter notes appear with the same visual treatment as action or dialogue, making readers unable to distinguish source screenplay content from edition notes.
Root Cause: `note` entries used the same renderer path and CSS treatment as ordinary screenplay body entries.
Prevention: Treat `note` as a distinct schema entry type with separate HTML styling. Use `note` entries for reader-facing annotations tied to source evidence, and do not encode them as ordinary action text.
Remediation: Convert affected annotations to `type: "note"` entries, rebuild HTML with note styling, and verify that body-text audits still exclude notes from source-entry preservation counts.
Status: RESOLVED

-----

## FM-013 Subtitle Label Text Written Into Translation Field

Name: Subtitle Label Pollution In Translation Text
Symptoms: Dialogue renders with a styled subtitle label and then repeats the
same label as ordinary dialogue text, for example
`字幕差异字幕差异我不需要太空人。`.
Root Cause: During manual or agent-authored batch creation, the subtitle state
was written into both the structured `subtitle_label` field and the
reader-facing `translation` field. This violates batch schema separation:
metadata belongs in `subtitle_label`; translated spoken text belongs in
`translation`.
Prevention: Before writing or editing a translated batch, keep subtitle state
and translation text as separate fields. During continuous execution, treat any
label prefix inside `translation` while `subtitle_label` is present as a local
current-batch data defect, not as renderer behavior. Do not rely on renderer
normalization to hide schema pollution.
Remediation: Clean only the affected batch translations by removing duplicated
subtitle-label text from `translation`, preserve all source and mapping fields,
delete stale previews or audits for the same range if needed, and rerun
`validate_batch.py --final`.
Status: MONITORED

-----

## FM-014 Local Missing Translation During Continuous Batch Execution

Name: Current-Batch Translation Omission
Symptoms: One or more entries in a translated batch have an empty or missing
`translation` even though the corresponding source entry exists, or a visible
source row is skipped in the batch.
Root Cause: Long continuous execution can produce a local omission when the
agent writes a batch artifact entry by entry. This is distinct from source
extraction failure when the source row is present in extracted data.
Prevention: Always run final batch validation before advancing. During
authorized continuous execution, use the current-batch recoverable-fix path only
for local, deterministic omissions where source evidence is clear and no schema,
pipeline, validation, or terminology policy change is required.
Remediation: Fill the missing translation in the current batch only, preserving
entry IDs, order, source text, page mapping, markers, and schema. Rerun final
batch validation before continuing. If source evidence is absent from extracted
data, reclassify as an extraction defect instead.
Status: MONITORED

-----

## FM-015 Substring Terminology Warning Against A Longer Valid Term

Name: Short-Term Match Over Longer Contextual Term
Symptoms: Final validation reports a terminology warning for a short source
term even though the translation correctly follows a longer compound term in
context.
Root Cause: The terminology matcher can detect a shorter term inside a longer
phrase without fully resolving longest-match context. A valid translation may
therefore look like a term miss if judged only by substring evidence.
Prevention: Treat terminology warnings as evidence to inspect, not automatic
permission to rewrite. Check project terminology, source phrase boundaries, and
the longest applicable term before changing translation.
Remediation: Keep the correct contextual translation when source context
supports the longer term. Record the warning as a known validation limitation or
matcher evidence before changing validation behavior.
Status: MONITORED
