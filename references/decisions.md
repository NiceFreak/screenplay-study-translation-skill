# Design Decisions

This file records key design decisions made during the development of the screenplay-study-translation skill.

Each entry explains what was decided, why, and what was explicitly ruled out.

-----

## Output Format

### HTML as primary output; EPUB as mobile output; PDF deprecated

**Decision:** Final reader outputs are static HTML and EPUB. HTML remains the
primary review and desktop reading surface. EPUB replaces PDF as the supported
mobile reading output. PDF output is deprecated in v0.3; `scripts/export_pdf.py`
is retained for historical reference only.

**Reason:**

- Translated Chinese text does not fit cleanly into source page boundaries
- HTML is easier to inspect on desktop and mobile
- HTML is cheaper to iterate and suitable for static hosting (GitHub Pages)
- Page-aligned PDF forces translated content into source page constraints, producing crowded output
- EPUB gives mobile readers navigation and reflow without reintroducing PDF page
  constraints

**Ruled out:**

- Do not treat PDF as a supported output target
- Do not match generated pages to source PDF pages
- Do not add PDF export back to the normal workflow

### Reader-facing title comes from user-supplied Chinese title

**Decision:** New translation projects require a user-supplied Chinese film
title. HTML cover and reader-facing title surfaces use this value, while the
source/original title remains in `project.title`.

**Reason:**

- Film title translation is an editorial decision, not a reliable filename,
  subtitle, or model-inference result
- Stable reader-facing titles keep generated HTML, cover metadata, and project
  configuration aligned
- Keeping original and Chinese titles separate avoids overwriting source
  bibliographic information

### Edition-wide explanations belong in reading notes, not body notes

**Decision:** Global formatting conventions, renderer behavior, and
edition-wide handling notes belong in the HTML reading note or professional
terms section. Body `note` entries are limited to source screenplay
notes/instructions and subtitle-supplied annotations.

**Reason:**

- Repeated body notes pollute the screenplay reading surface
- Edition-wide conventions should be explained once
- Body notes should preserve source evidence, not describe renderer policy

### Restore source-visible format from structured batch data

**Decision:** When source-visible formatting or screenplay structure matters to
reading, capture it in the batch schema surface first: entry type, markers,
layout metadata, front matter, or inline markup. Generated HTML restores the
reading shape from that data; generated HTML should not be hand-edited.

**Reason:**

- The same formal translation should support preview, audit, and final reader
  output
- Hand-edited HTML breaks reproducibility and auditability
- Schema-supported preservation scales better than project-specific hot patches

### HTML reflow is presentation-layer rendering over batch JSON

**Decision:** Translation batch JSON remains the structured source of truth.
Chinese reading reflow is performed only by the HTML renderer as presentation
logic. It must not rewrite batch entries, source order, page mapping, markers,
or entry-level traceability.

**Reason:**

- Chinese reading layout should not be constrained by PDF physical line breaks
- Batch JSON must remain reusable for validation, audit, preview, final HTML,
  and EPUB export
- Renderer-level reflow improves readability while preserving reproducibility
  and traceability

**Renderer guardrail:**

- Reflow protection must be entry-type aware. A dash-prefixed `action` line
  remains action prose and must not be treated as an HTML list item or protected
  block. The renderer must not reset action prose continuity merely because an
  action translation begins with `- `.

-----

## Translation

### Final-quality intent from first pass

**Decision:** Every translation batch is written at final quality from the start. No rough-translation pass.

**Reason:**

- Rough translation creates a rewrite loop that multiplies token cost
- User cannot reliably catch translation mistakes from the source language
- Quality control must be automated, not delegated to user review

### Provided subtitles are authoritative for dialogue translation

**Decision:** When high-quality Chinese subtitles are provided, use subtitle
content directly for dialogue translations. AI translates non-dialogue
screenplay elements and uses subtitle style as the main calibration source.

**Reason:**

- User-provided subtitle quality is a project input decision, not an automated
  validation target
- Direct subtitle use improves dialogue consistency and preserves established
  localization choices
- Screenplay translation still needs AI handling for action, scene headings,
  parentheticals, format markers, and screen text

-----

## Source Structure

### Never invent scene numbers

**Decision:** Scene numbers are reconstructed from source only. Sequential numbering is never invented.

**Reason:**

- Invented numbers break structural audits
- Missing scene numbers are a script-type signal, not an extraction failure
- Reading drafts and public PDFs legitimately omit production scene numbers

### Extraction rules as auditable heuristics

**Decision:** No extraction rule is treated as a universal truth. Every rule is a heuristic that must be validated against source evidence.

**Reason:**

- Different screenplays use different house styles
- A rule that works for one screenplay may silently corrupt another
- Hard-coded assumptions produce failures that are difficult to trace

-----

## Pipeline

### 5–10 pages per translation batch

**Decision:** Translation is processed in batches of 5–10 displayed screenplay pages.

**Reason:**

- Keeps token cost per session manageable
- Makes validation and error isolation easier
- Allows partial delivery and incremental review

### Source signal scan before translation

**Decision:** A Stage 2 source signal report must be produced before translation begins.

**Reason:**

- Format anomalies discovered mid-translation require new sessions to fix, multiplying token cost
- Early signal recording makes structure evidence visible before it affects batch output
- Each screenplay has unique formatting patterns that cannot be assumed in advance
- Stage 2 should record known, warning, and noise signals without upgrading scanner rules

### Continuous batch execution is a controlled runtime exception

**Decision:** Translation remains batch-step based. Continuous batch execution
is allowed only when the user explicitly authorizes it, and each batch still
must complete, validate, and determine the next range independently. The run
stops on FAIL, UNCERTAIN, tool errors, unclear next ranges, or any need to
change global rules.

**Reason:**

- Full-project translation should minimize manual restart friction after the
  first style gate
- Validation must remain the real boundary between batches
- Unbounded multi-batch execution previously created unstable planning and made
  failures harder to isolate

### Current batch context packages reduce agent context cost

**Decision:** A translation batch may use a generated
`work/context/batch-context-pXXX-YYY.json` package as its default read surface.
The package is a compact, read-only compression of existing artifacts for one
displayed-page range. It is not a new pipeline stage or validation gate.

**Reason:**

- Full `source-lines.json`, subtitle JSON, and marker inventories are expensive
  for an agent to reread for every batch
- Local packaging preserves the batch execution boundary while reducing token
  cost
- Subtitle candidates can be presented as advisory evidence without making
  mechanical matching authoritative
- Existing validation remains attached to formal translated batch JSON and HTML
  audit output

### Token optimization must preserve current-range source text

**Decision:** v0.3 token optimization is limited to read-only cost observation,
advisory batch planning, and compact auxiliary context fields. It must not
remove or summarize current-range screenplay source entries that require
translation.

**Reason:**

- Translation quality depends on full local screenplay wording, structure, and
  rhythm
- Source-text compression would shift quality risk to the user or to later
  repair passes
- Cost savings are safer when taken from repeated metadata, subtitle candidate
  verbosity, warning/noise signal volume, and previous-batch continuity length
- Batch planning remains advisory and cannot override runtime execution
  constraints or validation gates

### Final cost estimates are automatic observation artifacts

**Decision:** Final project delivery automatically exports
`work/reports/cost-report.json` after final HTML audit passes. The report uses
detected or default model pricing metadata to estimate project-level USD cost
without requiring routine user input.

**Reason:**

- Cost reporting should not add setup burden for normal skill users
- The estimate is useful as project-scale feedback even when runtime billing
  usage is unavailable
- Model/pricing values remain overrideable for advanced correction, but the
  default path must be automatic and explicitly marked as non-billing data

### Smoke test data must be fully isolated from project input materials

**Decision:** All smoke test fixtures and test case data must use only
synthetic, abstract, or structurally representative content. No text from
real screenplay PDFs, subtitle files, or existing translation artifacts
may appear in test or fixture files, regardless of fragment length.

**Reason:**

- Input materials are assumed to be under copyright protection
- Test data exists to verify code logic and pipeline structure, not to
  carry real content
- Using real content creates copyright exposure risk in open source
  distribution

**Ruled out:**

- Do not use real character names, dialogue, scene descriptions, or plot
  content in any test or fixture context
- Do not treat "short excerpt" or "just a few lines" as exempt

### Translation flavor optimization deferred pending real cost data

**Decision:** Translation flavor optimization is deferred to the next
screenplay project. No changes to flavor generation logic in v0.3.

**Reason:**

- style-profile.json is generated by a local deterministic script with no
  AI token cost
- The original optimization assumption (high token cost from global
  semantic analysis) was incorrect
- Real token cost distribution can only be measured from a clean
  production run on a new screenplay
- Optimization direction should follow measured data, not assumptions

**Next step:**

Run cost_report.py after the first full translation run on the next
screenplay. Use the output to identify actual token cost sources before
designing any optimization.

**Ruled out:**

- Do not optimize flavor generation based on assumed cost sources
- Do not introduce fixed label sets or simplified output formats without
  first measuring what is actually expensive

-----

## System Architecture

### Three-layer constraint system

**Decision:** Constraints are split across three files with distinct responsibilities.

```
AI_AGENT_CONTRACT      → runtime behavior rules
AI_AGENT_PROJECT_SPEC  → static pipeline description
SKILL.md               → translation and extraction knowledge
```

**Reason:**

- A single file mixing behavior rules, pipeline steps, and domain knowledge becomes difficult to maintain
- Changes to one layer should not require changes to another
- Clear separation makes it easier to identify where a failure originates

### References as knowledge library

**Decision:** Detailed domain knowledge lives in `references/`, not in `SKILL.md`.

**Reason:**

- SKILL.md should remain concise and scannable
- Reference files can be read selectively based on task needs
- Separating knowledge from instructions reduces token cost per session

### AST-first as long-term direction, not current-version implementation

**Decision:** Maintain the current raw text + structured JSON mixed-layer
architecture. Record AST-first as a v0.3-or-later long-term direction; do not
implement it in v0.2.

**Reason:**

- Current rules are distributed across multiple layers, but the system is still
  moving in the right direction
- AST-first would be a high-cost architectural rewrite that is not justified for
  the current version
- Translation quality and structural stability are already acceptable for the
  current workflow

**Reference:**

- Independent architecture audit concluded `PARTIAL`: AST-first can reduce
  structural review cost, but cannot by itself eliminate human review. See
  work logs or conversation record.

-----

## Information Retention

### Out-of-scope findings must be recorded

**Decision:** When an issue is detected but cannot be handled in the current pipeline stage, it must be written to work artifacts, validation reports, or execution logs. Silent discard is not allowed.

**Reason:**

- Issues discovered in one stage often affect later stages
- Silent discard causes the same issue to be rediscovered repeatedly
- Recorded findings can be reviewed and acted on at the appropriate stage

-----

## Tool Selection

### Translation tasks must run in the correct agent context

**Decision:** All translation, validation, and stage gate tasks must be executed in a Codex session with the skill loaded.

**Reason:**

- Tools that do not read AGENTS.md or skill constraint files have no access to project path, terminology, or style profile
- Tasks executed outside this context produce path errors, format corruption, and untranslated proper nouns
- Constraint files are only effective when read by the agent at session start

**Evidence:**

- A batch executed outside the correct tool context produced files in the wrong directory, corrupted JSON output, and untranslated character names

-----

## Style Consistency

### Style profile as cross-session style anchor

**Decision:** A style-profile.json is generated after Stage 2 and read by every subsequent translation session.

**Reason:**

- AI has no memory across sessions
- Without a persistent style reference, tone and terminology drift across batches
- High-quality subtitle translations provide the primary style anchor when
  subtitles are present

### Subtitle dialogue and proper nouns take priority over AI judgment

**Decision:** When subtitles provide dialogue translation, use it directly for
dialogue entries. When subtitles provide a proper noun translation, that
translation is used and recorded in terminology.md.

**Reason:**

- Subtitles reflect established localization choices for this specific film
- AI judgment on dialogue phrasing and proper nouns is inconsistent across
  sessions
- Consistency requires a single authoritative source per project

**Evidence:**

- A proper noun was translated differently by AI versus subtitles in the same project, requiring manual correction and terminology table update

### Terminology baseline is generated automatically before batch translation

**Decision:** After PDF extraction and optional subtitle parsing, generate a
project-local terminology baseline before the first translation batch. Routine
user confirmation is not required. Escalate only high-impact ambiguity,
conflicting evidence, or terms that affect the user-supplied Chinese title.

**Reason:**

- Rechecking core proper nouns and terms in every batch wastes tokens and
  increases drift risk
- Subtitle-derived terminology and source recurrence are strong enough for a
  baseline in ordinary cases
- User review should focus on first-batch format/style acceptance and final
  reader acceptance, not routine terminology bookkeeping

-----

## Human-in-the-Loop

### First batch HITL gate combines style profile confirmation and translation review

**Decision:** Style profile confirmation and first batch review are merged into a single user confirmation step.

**Reason:**

- Both confirm the same thing: whether AI understood the screenplay’s style correctly
- Separating them adds an unnecessary intervention point with no additional decision value
- After this single confirmation, remaining batches run without per-batch user
  confirmation

-----

### Entry Configuration is Platform-Specific; Core Assets are Reusable

**Decision:** AGENTS.md and agents/openai.yaml are entry configuration for a
specific agent platform. references/, scripts/, and assets/ are reusable core
assets and should avoid platform-specific assumptions where practical.

**Reason:**

- Different agent platforms have their own instruction injection mechanisms
- When migrating to a new platform, entry configuration is the first layer to adapt
- Knowledge and execution logic should remain portable unless a platform feature is required

-----

### Subtitle Alignment Uses Semantic Correspondence, Not Fixed Match Rates

**Decision:** Subtitle alignment should be evaluated against semantic
correspondence, screenplay source type, and local evidence, not against a fixed
match-rate or string-similarity threshold. See references/subtitle_alignment.md
for label rules and references/industry_conventions.md for source-type
guidance.

**Reason:**

- Differences between drafts and the final film may be normal, not system errors
- Fixed thresholds imply calibration data this skill does not have
- String similarity is unreliable across English screenplay source and Chinese
  subtitles
- Source type should be recorded in the Stage 2 signal notes when known
