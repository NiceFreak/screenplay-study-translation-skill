# Task Brief Template

Two phases. **Can you state Scope and Acceptance?**

- **Yes** → you are in **execution**: fill the Task brief below.
- **No** → the requirement is still fuzzy: run **Discovery** first (it produces a
  filled Task brief), then execute. Never let AI write code while the requirement
  is fuzzy — that is where the iteration multiplier explodes.

Rationale and the full loop: `references/ai_change_workflow.md`.

## Discovery brief (requirement still fuzzy — investigate only, no code)

```
## Discovery
- Rough goal:   <even a vague sentence: the pain or the outcome I want>
- Undecided:    <what I can't pin down — do X or Y, where it lives, whether to do it at all>
- Known limits: <budget, must-not-break, time, scope ceiling>

Ask the agent to (read-only, NO code changes):
1. Ask me clarifying questions until Scope and "done" are decidable.
2. Investigate the relevant code read-only and report what is actually there.
3. Propose 2-3 concrete approaches with tradeoffs (effort, risk, cost).
4. Recommend one and draft a filled Task brief for my approval.
```

Discovery is cheap: it is read + ask + propose, with no edit/test/rerun loops and
no whole-repo churn. Letting the agent interview you is the cheapest way to
extract a requirement that is still only in your head. Use a strong model here
(judgment matters) — it stays cheap because it is read-only and short. The
expensive thrash is writing code while the requirement is fuzzy; Discovery
converts fuzzy into a brief so execution is one clean pass.

## Task brief (execution — Scope and Acceptance are known)

```
## Task brief
- Goal:        <one sentence: what is true after this change>
- Scope:       <the specific file(s)/function(s) to touch — name them>
- Acceptance:  <how it is verified done — e.g. "smoke green + grep X in output">
- Out of scope:<what NOT to touch and what NOT to add>
- Model:       <cheap model for mechanical edits / strong model for design>
```

Then: ask the agent to propose a plan against this brief and approve it before
any code; implement one brief at a time; verify with the cheap deterministic
gates (`python3 scripts/smoke.py`, `ruff check scripts`,
`ruff format --check scripts`, `python3 -m compileall scripts`).
