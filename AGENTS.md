## Tool Requirement

This file provides session bootstrap context only.

Constraint files are only effective when read by the agent at session start.
Tasks executed outside this context do not have access to:
- AI_AGENT_CONTRACT.md
- AI_AGENT_PROJECT_SPEC.md
- SKILL.md
- style-profile.json
- terminology.md

## On Activation

Read before starting any task:
1. AI_AGENT_CONTRACT.md
2. AI_AGENT_PROJECT_SPEC.md
3. SKILL.md

## Runtime Authority

AGENTS.md does not define execution control.

It does not define:
- batch execution order
- validation follow-up actions
- stage advancement
- automatic continuation
- user confirmation requirements
- audit-mode execution steps
- continuous batch execution conditions

Runtime execution decisions are controlled only by AI_AGENT_CONTRACT.md.
If any instruction outside AI_AGENT_CONTRACT.md appears to control execution,
treat it as non-authoritative.

AGENTS.md may point the agent to required startup files, but it must not
reinterpret or summarize those files in a way that changes runtime behavior.
