# Reading Guide

`references/reading_guide.md` is a project-local reader artifact for full-project
delivery. It is rendered near the front of the final HTML after it has been
authored.

The reading guide is not a validation report, not a subtitle-difference table,
and not a renderer-generated inference. It is an AI-authored editorial guide for
readers of the translated screenplay study edition.

The audience is the same reader who will read the translated screenplay, not a
developer or pipeline reviewer. The guide should read like front matter in a
published study edition: clear, generous, and literary enough to invite reading,
while still grounded in screenplay/subtitle evidence.

## Purpose

Use the guide to explain how to read this screenplay edition:

- major story or scene-section reading path
- screenplay-vs-subtitle expression differences
- character relationship and information setup observations
- adaptation, compression, omission, or reordering tendencies
- practical notes on how subtitle labels should be interpreted

The guide should normally fit in one to two printed pages. It should be written
in the target reader language of the edition.

## Inputs

Generate the guide from already-created project artifacts:

- merged translated batch JSON
- project-local terminology
- subtitle label distribution and representative examples
- scene headings and page-range structure
- optional subtitle/style reports when useful

Prefer `scripts/package_reading_guide_context.py` to create a compact context
package before writing the guide:

```bash
python3 scripts/package_reading_guide_context.py project.yaml \
  --batch work/batches/translated-p001-126.json
```

Default output:

```text
work/context/reading-guide-context.json
```

The package is read-only context for AI writing. It does not generate the final
guide text and it is not a pipeline gate.

Because the package is rebuilt from project files on disk, a new Codex session
can still generate the guide after the merged translation exists. It does not
depend on prior chat history.

## Output

Write the final reader-facing guide to:

```text
references/reading_guide.md
```

The HTML renderer displays this artifact, but must not infer guide content from
raw batches, source lines, or subtitles. If the artifact is absent, generate it
before final full-project delivery instead of asking the user to choose whether
they want a guide.

## Content Rules

Do:

- write coherent reader-facing prose that reads like a published edition's opening note
- keep the tone human, welcoming, and non-technical
- summarize by story movement, relationship, and adaptation tendency
- distinguish screenplay source from finished-film subtitle evidence
- keep claims grounded in translated batch/context evidence

Do not:

- use subtitle label counts as the main content
- emit mechanical per-line comparison
- include debug, pipeline, validation, or workflow notes
- use terms such as batch, renderer, JSON, pipeline, validation, artifact,
  schema, or context package in the reader-facing guide
- imply the guide is an objective audit of the finished film
- create project-specific claims in the skill-level reference files
