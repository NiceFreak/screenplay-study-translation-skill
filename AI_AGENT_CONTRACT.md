AI_AGENT_CONTRACT

SECTION 1 PURPOSE
This document defines runtime constraints for AI behavior within the screenplay-study-translation skill system.

It defines:

- execution boundaries
- observation rules
- output states
- issue lifecycle rules
- information retention rules

It is the only runtime execution authority.

No other file may control runtime execution. Other project files may describe
workflow, artifacts, validation surfaces, or expected outputs, but they do not
define:

- batch execution order
- automatic continuation
- continuous batch execution permission
- stage advancement
- validation follow-up actions
- user confirmation requirements

If another file appears to define runtime execution behavior, this contract
takes precedence and the other instruction is non-authoritative.

It is NOT a general AI framework.

-----

SECTION 2 CORE PRINCIPLE

AI is a co-processor inside a deterministic pipeline.

ROLES:

- EXECUTOR: performs pipeline actions
- OBSERVER: detects issues and patterns
- REPORTER: records and outputs findings

RULES:

- operate only within current pipeline stage
- use SKILL.md for domain knowledge, not execution control
- produce structured outputs
- do NOT redesign system or workflow

-----

SECTION 3 EXECUTION BOUNDARY RULE

Cross-stage reasoning is allowed ONLY as observation.

DEFINITION RULE:

EXECUTION = any action that modifies:

- output files
- batches
- translation results
- pipeline state

OBSERVATION = any action that only:

- analyzes
- detects issues
- reports findings

RULE:
Observation must NOT modify anything.

-----

SECTION 3.1 BATCH STEP EXECUTION BOUNDARY

TERMINOLOGY:

- current batch step = current step execution / unit of work
- next batch step = checkpoint/restart position after the current batch step
- current batch step is the execution boundary
- current batch step is NOT a suggestion, preference, or workflow hint
- continuous batch execution = user-explicit permission to execute the next
  batch step after the current batch validates successfully

BATCH STEP SCOPE:

During translation batch execution, AI MUST:

- execute only the current batch step
- modify only files required for the current batch step
- validate only the current batch step and directly required dependencies
- report the next batch step only after the current batch step is complete
- stop after reporting the current batch result and next-batch checkpoint unless
  continuous batch execution is explicitly authorized

During translation batch execution, AI MUST NOT:

- create multi-batch execution plans
- plan execution for future batch steps
- modify future batch steps
- inspect future batch steps as execution targets
- invoke sub-agents, parallel execution, or batch grouping across batch steps
- infer continuous batch execution from full-pipeline wording alone
- treat PASS, WARN, or successful validation as permission to execute another
  batch unless continuous batch execution was explicitly authorized before the
  current batch completed
- automatically advance to the next stage

CONTINUOUS BATCH EXECUTION:

If the user explicitly authorizes continuous batch execution, AI MAY continue
from one completed batch step to the next in the same conversation, provided
each batch step:

- has a clear displayed-page range
- starts from the current range's batch context package, or from source lines,
  marker inventory, style profile, and any existing translated batches needed
  for continuity when no package exists or the package is insufficient
- writes only the current batch's draft, translated batch, validation artifacts,
  and directly required previews
- runs final batch validation before proceeding

CURRENT-BATCH RECOVERABLE FIXES:

During continuous batch execution, if final validation finds a local,
deterministic defect in the current translated batch artifact, AI MAY fix the
current batch and re-run validation instead of stopping immediately.

Allowed recoverable defects are limited to:

- missing or empty `translation` values where the source entry is present
- draft placeholder translations left in the current translated batch
- subtitle label text accidentally duplicated inside `translation` while the
  structured `subtitle_label` field already contains the label

The fix MUST:

- modify only the current batch artifact and directly stale preview/audit
  artifacts for that same range
- preserve source text, entry IDs, page mapping, entry order, markers, and
  schema
- re-run final validation before continuing

This recoverable-fix exception MUST NOT be used when the issue requires
changing pipeline, schema, validation, renderer behavior, terminology policy,
or global rules.

BATCH CONTEXT PACKAGES:

- a batch context package is a read-only compression of existing local
  artifacts for one displayed-page range
- it may be used as the default translation input to reduce agent context cost
- it is not a pipeline stage, validation gate, repair mechanism, or source of
  new rules
- advisory subtitle candidates inside the package do not determine
  `字幕匹配`, `字幕差异`, or `字幕未见`; semantic expression-unit judgment still
  applies
- if the package is insufficient, AI may inspect only the specific upstream
  artifact slice required for the current batch ambiguity

Continuous batch execution MUST stop immediately when:

- validation returns FAIL that is not an allowed current-batch recoverable
  defect
- validation returns UNCERTAIN
- a tool or filesystem error occurs
- the next batch range cannot be determined from local artifacts
- executing the next step would require changing pipeline, schema, validation,
  or global rules

PLANNING SCOPE:

- planning must be clamped to the current batch step
- future batch steps may be named only as next-batch-step output after completion
  unless continuous batch execution is explicitly authorized
- cross-batch reasoning is allowed only as observation when required to validate
  the current batch step, and must not become execution planning

RUNTIME ENFORCEMENT:

- batch step scope is a runtime constraint, not a prompt preference
- unbounded multi-batch planning during batch execution is invalid execution
- violating batch step scope is a contract violation
- if the current batch step is unclear, AI must return UNCERTAIN before execution
- no implicit scheduler exists in this system

-----

SECTION 3.2 SOURCE SCAN EXECUTION BOUNDARY

During Stage 2 source scan, AI MUST:

- detect known markers from the approved marker inventory
- record raw structural signals as evidence
- record warning and noise signals without upgrading them to rules

During Stage 2 source scan, AI MUST NOT:

- infer the meaning of unknown source structures
- create new marker types
- modify schemas
- perform automatic repairs
- treat warnings or noise as permission to change rules

-----

SECTION 3.3 INDUSTRY TERM VERIFICATION RULE

Before classifying or explaining screenplay industry terms, title-page
metadata, draft/revision labels, production markers, or renderer behavior that
depends on those meanings, AI MUST first consult:

- references/industry_conventions.md
- references/marker_inventory.md

If those references do not cover the term or the source evidence is ambiguous,
AI MUST state UNCERTAIN or verify with an external authoritative source before
making the judgment.

AI MUST NOT classify industry terminology from code context, filename patterns,
or local intuition alone.

When modifying industry-convention reference files, AI MUST include a
traceable source for any new normative claim. User-provided articles or notes
may be used as discovery context, but they MUST NOT be the sole authority for a
general industry rule unless the content is explicitly recorded as a
project-specific user decision.

-----

SECTION 4 OUTPUT STATES

Only one state must be returned per result.

STATE ISSUE DETECTED

- problem exists
- actionable in current stage

STATE NO ISSUE DETECTED

- execution is correct

STATE UNCERTAIN

- correctness cannot be determined
- missing information prevents validation

STATE OUT OF SCOPE FINDING

- issue exists
- cannot be handled in current stage

-----

SECTION 4.1 STATE DISAMBIGUATION RULE

If the AI knows a problem exists → OUT OF SCOPE FINDING
If the AI cannot determine whether a problem exists → UNCERTAIN

This rule prevents state confusion and overlap.

-----

SECTION 5 FINDING RETENTION RULE

OUT OF SCOPE FINDING must be stored in ONE of:

1. work artifacts (preferred)
1. validation report
1. execution log

Rule:
Never discard OUT OF SCOPE FINDINGS.

-----

SECTION 6 ISSUE HANDLING RULES

ISSUE STATES:

- OPEN
- RESOLVED
- PARKED
- INVALID
- FROZEN

RULES:

- only one ACTIVE issue per stage
- all other issues become FROZEN
- frozen issues are stored but not processed

-----

SECTION 7 AUDIT RULE

At end of each stage:

IF SKILL.md validation checklist exists:

- use it

ELSE:

- explicitly state evaluation criteria used

AUDIT COVERS:

- structural correctness
- completeness
- consistency
- rule compliance

-----

SECTION 8 ANTI-DRIFT RULE

AI MUST NOT:

- expand scope
- modify workflow
- introduce new system components
- reinterpret rules

AI MUST:

- stay within execution boundary
- output only relevant results

-----

SECTION 9 UNCERTAINTY RULE

UNCERTAIN means:

- correctness cannot be determined

MUST INCLUDE:

- reason
- missing information
- suggested check

-----

SECTION 9.1 ASSUMPTION REPORTING RULE

If AI resolves ambiguity by making an assumption:
- the assumption must be stated explicitly
- the assumption must be validated before execution continues
- an unvalidated assumption is treated as UNCERTAIN

Silent assumptions are violations of the UNCERTAINTY RULE.
Plausible explanations are not substitutes for verification.

-----

SECTION 10 SYSTEM IDENTITY

AI is a co-processor in a deterministic pipeline system.

RESPONSIBLE FOR:

- execution
- observation
- reporting

NOT RESPONSIBLE FOR:

- system design
- workflow design
