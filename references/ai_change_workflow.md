# AI Change Workflow (Cost-Controlled)

How to drive AI-assisted code changes on this project without burning tokens on
avoidable rework. This is about the **development process**, not runtime
behavior (runtime rules live in `AI_AGENT_CONTRACT.md`).

## Why this exists

The expensive part of building with AI is rarely the final code. It is the
thrash before it. Development cost behaves like:

```
change cost ≈ iterations × context re-read per iteration
              ↑ unclear requirements      ↑ large repo / large files / long logs
```

Both terms are multipliers. Unclear requirements inflate the iteration count;
a large file or a whole-repo dump inflates the per-iteration price. A clean
squashed history hides this thrash — it is the residue of the iterations, not
evidence they were cheap.

The countermeasure is the same discipline used for any maintained codebase:
clear acceptance criteria, a plan gate before code, small focused changes, and
cheap deterministic verification.

## Before asking AI to change code: fill this brief

Copy the fill-in brief from `references/task_brief_template.md`, complete it, and
give it to the agent. If you cannot fill in **Acceptance**, the requirement is
not clear enough to code yet — clarify first.

## The loop

1. **Brief.** Write the task brief above. No Acceptance line → not ready.
2. **Plan, then approve.** Ask the agent to propose a plan against the brief and
   approve it *before* any code is written. Catching a wrong direction at the
   plan stage costs a few hundred tokens; catching it after 500 lines costs a
   full rewrite.
3. **Implement one brief at a time.** Point the agent at the named files only.
4. **Verify with the cheap deterministic gates** (no API tokens):
   ```
   python3 scripts/smoke.py
   python3 -m compileall scripts
   ruff check scripts
   ruff format --check scripts
   ```
   Green plus the Acceptance line met = done. Stop polishing.
5. **Commit small.** Squashing on merge is fine — clean history is good; it is
   not the cost problem.

## Context discipline (cuts the per-iteration price)

- Name the specific files. Do not dump the whole repo into context.
- On a test failure, paste the single failing assertion, not the entire log.
- Keep modules small. A large file means every touch re-reads the whole file
  (this is why `smoke.py` check definitions live in `smoke_checks/`).
- New session for an unrelated task; same session for related iterations so the
  stable prefix stays cache-warm.

## Model tiering for changes

- Mechanical edits (lint fixes, renames, test plumbing, doc tweaks) → a cheap
  model is enough.
- Genuine design or cross-cutting changes → reserve the strong model.

## Build to learn vs build to use

Decide which mode you are in before you start. When building to **learn**, the
rework is the point and its cost is tuition. When building to **use**, freeze
scope hard and resist scope creep — that is where avoidable spend accumulates.
