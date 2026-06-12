# Batch Schema

Translation batches live in `work/batches/` as JSON before HTML rendering. The batch JSON is the contract between translation, audit, HTML rendering, and any future reflowed reading/print export.

A batch combines source text rows from `source-lines.json`, adjacent structure markers from `source-markers.json`, and formal Chinese translation text. It should not invent source structure that is absent from the upstream artifacts.

## Shape

```json
{
  "version": 1,
  "batch_id": "p001-010",
  "source_pages": {"start": 1, "end": 10},
  "has_subtitles": false,
  "front_matter": [
    {
      "id": "front-001",
      "type": "note",
      "pdf_page": 1,
      "display_page": 0,
      "source": "Written by Jane Example",
      "translation": "编剧：__简·埃克桑普尔__"
    }
  ],
  "entries": [
    {
      "id": "p001-e001",
      "type": "scene_heading",
      "pdf_page": 2,
      "display_page": 1,
      "source": "INT. ROOM - NIGHT",
      "translation": "内景。房间 - 夜",
      "markers": [
        {"type": "scene_no", "text": "1", "position": "left"}
      ]
    }
  ]
}
```

## Entry Types

| Type | Chinese label | Meaning |
|------|---------------|---------|
| `page_heading` | 页码标题 | Page heading or extracted page label. |
| `scene_heading` | 场景标题 | Scene location/time heading. |
| `action` | 动作描写 | Action, atmosphere, image, or scene description. |
| `character` | 角色提示 | Speaker cue. |
| `parenthetical` | 括号说明 | Delivery, action, or position note attached to dialogue. |
| `dialogue` | 对白 | Spoken or sung line content. |
| `transition` | 转场 | Transition line. |
| `format_marker` | 格式标记 | Screenplay formatting signal that should remain legible. |
| `note` | 读者注 | Reader-facing note or front matter entry. |

## Rules

- Preserve source order.
- Reader notes may be added as `type: "note"` entries when they are tied to
  source evidence in the same batch range, such as subtitle annotations or
  front matter. Do not use notes to replace screenplay translation. Reader
  notes should render with a distinct note style, not the same body styling as
  screenplay dialogue or action.
- Body `note` entries are limited to source screenplay notes/instructions and
  annotations supplied by subtitles. Global format explanations, renderer
  conventions, and edition-wide handling notes belong in the HTML reading note
  or professional-terms section, not among screenplay body entries.
- Keep `pdf_page` and `display_page` explicit on every entry.
- Treat `display_page` as the user-facing page range for samples, translation batches, and range audits.
- Preserve source scene numbers as strings inside entry markers. Do not convert them into invented sequential integers.
- `translation` must be non-empty except intentionally empty layout entries, which should be avoided.
- Marker types must match `references/marker_inventory.md`.
- Entry `markers` are rendered into HTML `data-marker-type` attributes by `scripts/build_html.py`.
- Do not emit subtitle labels when `has_subtitles` is false.
- When subtitles are present, labels may be `字幕匹配`, `字幕差异`, or `字幕未见`.
- Subtitle label state belongs only in the structured `subtitle_label` field.
  Do not prefix or embed `字幕匹配`, `字幕差异`, or `字幕未见` inside
  `translation`; `translation` contains only reader-facing translated text.
- When a dialogue entry has a stable matched subtitle event, it may also include
  optional subtitle timestamp fields:
  - `subtitle_event_index`: zero-based index in `work/subtitles.json`.
  - `subtitle_start`: subtitle event start time in seconds.
  - `subtitle_end`: subtitle event end time in seconds.
  These fields persist the matched subtitle time only. They do not encode scene
  alignment, difference type, confidence, or timeline analysis.
- When subtitles are present and a corresponding subtitle exists, dialogue entry
  `translation` should use the subtitle content directly. Non-dialogue entries
  are translated by AI using `work/style-profile.json`.
- Formal translation batches should be written at final-quality intent. Audit and final reader outputs may present different metadata, but they should share the same translation text.
- Batch files are work artifacts. Final reader outputs should not expose batch IDs or task workflow labels.
- Optional `front_matter` contains title-page or cover-page information such as source title, author, draft date, contact block, or rights notes. It renders in the HTML cover area, not as screenplay page 0.

## Structure Checks

When comparing a translated batch with its draft source batch, distinguish:

- original screenplay entries, which should preserve `id`, `type`, page fields,
  `source`, and marker identity unless a structural correction is documented
- `front_matter`, which may legally move title-page or cover-page material out
  of screenplay body entries
- reader `note` entries, which may be additional entries and should not count as
  source-entry drift

Overlapping sample batches should be labeled and audited as overlapping ranges,
not as a single continuous final sequence.

## Inline Markup

Formal translation text should use lightweight inline markup for reader-facing HTML when applicable:

| Markup | Role | Meaning |
|--------|------|---------|
| `__proper name__` | proper-name annotation | Renders as underlined proper names, places, titles, or program names. |
| `**emphasis**` | source bold/emphasis | Preserves source bold styling or explicit screenplay emphasis. |
| `*term*` | source italic/style | Preserves source italic styling or screenplay style evidence. |
| `[[term]]` | reader annotation | Renders as a reader annotation style for sound cues, screen text, screenplay terminology, abbreviations, or format notes that should not share the source emphasis styles or replace a `note` entry. |
| trailing `[[*]]` | source revision mark | Renders as a source revision asterisk aligned to the right end of the screenplay line. |

Use markup sparingly and consistently. Do not use it to encode source structure that belongs in `markers` or layout metadata. A final batch with no inline markup at all should be treated as suspicious unless the source range genuinely contains no proper names, emphasis, sounds, screen text, or screenplay terms.

If a source line ends with a standalone revision asterisk (`*`) in a production
or revised-draft context, preserve the asterisk as trailing `[[*]]` in the
translation. The HTML renderer treats this as a source revision mark, not a
reader annotation, and aligns it to the right end of the screenplay line.
Explain the convention once in the HTML reading note or professional-terms
section; do not add repeated body `note` entries for this global format rule.

For other source-visible residues or one-off glyphs, preserve them only when
local evidence suggests they carry screenplay structure, production status, or
reading intent. Low-confidence extraction artifacts should be recorded as
warning/noise signals upstream, not promoted into translated prose. If a
preserved mark needs explanation, use a body `note` only when the explanation
comes from a source screenplay note/instruction or a subtitle annotation. Use a
reader annotation only for local screenplay terminology or format hints tied to
that line. Put edition-wide explanations in the HTML reading note or
professional-terms section; do not invent a new special case unless the pattern
recurs or changes meaning across the project.

When a new source-visible format or screenplay structure appears, preserve the
source signal with the existing schema surface first: entry type, `markers`,
`layout`, or inline markup. Generated HTML should restore the source's reading
shape from that structured data. Do not hand-edit generated HTML, and do not
flatten the signal into ordinary translated prose unless the source formatting
has no reading or structural effect.

For project terms checked by validation, keep the core Chinese term in the same
entry as the triggering source term when practical. If natural Chinese requires
splitting a term across adjacent entries, record the exception or accept the
resulting warning.

## Relationships

- `scripts/draft_batch.py` creates placeholder batches from `source-lines.json` and `source-markers.json`.
- Translation work replaces placeholders in `translation`; it should not change `source`, page fields, or marker identity without a structural reason.
- `scripts/validate_batch.py` checks the batch shape.
- `scripts/validate_batch.py --final` additionally rejects draft placeholders and raw untranslated screenplay format markers.
- `scripts/build_html.py` renders the batch into reader-facing HTML while preserving structured markers for audit.
