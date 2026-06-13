# Task Brief Template

Copy the block below and fill it in before asking AI to change code. If you
cannot fill in **Acceptance**, the requirement is not clear enough to code yet —
clarify first. Rationale and the full loop: `references/ai_change_workflow.md`.

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
