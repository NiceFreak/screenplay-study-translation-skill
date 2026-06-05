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

- `page_heading`
- `scene_heading`
- `action`
- `character`
- `parenthetical`
- `dialogue`
- `transition`
- `format_marker`
- `note`

## Rules

- Preserve source order.
- Keep `pdf_page` and `display_page` explicit on every entry.
- Treat `display_page` as the user-facing page range for samples, translation batches, and range audits.
- Preserve source scene numbers as strings inside entry markers. Do not convert them into invented sequential integers.
- `translation` must be non-empty except intentionally empty layout entries, which should be avoided.
- Marker types must match `references/marker_inventory.md`.
- Entry `markers` are rendered into HTML `data-marker-type` attributes by `scripts/build_html.py`.
- Do not emit subtitle labels when `has_subtitles` is false.
- When subtitles are present, labels may be `字幕匹配`, `字幕差异`, or `字幕未见`.
- Formal translation batches should be written at final-quality intent. Audit and final reader outputs may present different metadata, but they should share the same translation text.
- Batch files are work artifacts. Final reader outputs should not expose batch IDs or task workflow labels.
- Optional `front_matter` contains title-page or cover-page information such as source title, author, draft date, contact block, or rights notes. It renders in the HTML cover area, not as screenplay page 0.

## Inline Markup

Formal translation text should use lightweight inline markup for reader-facing HTML when applicable:

- `__proper name__` renders as underlined proper names, places, titles, or program names
- `**emphasis**` renders as bold sound, on-screen emphasis, or screenplay emphasis
- `*term*` renders as italic screenplay terminology, abbreviations, or format notes

Use markup sparingly and consistently. Do not use it to encode source structure that belongs in `markers`. A final batch with no inline markup at all should be treated as suspicious unless the source range genuinely contains no proper names, emphasis, sounds, screen text, or screenplay terms.

## Relationships

- `scripts/draft_batch.py` creates placeholder batches from `source-lines.json` and `source-markers.json`.
- Translation work replaces placeholders in `translation`; it should not change `source`, page fields, or marker identity without a structural reason.
- `scripts/validate_batch.py` checks the batch shape.
- `scripts/validate_batch.py --final` additionally rejects draft placeholders and raw untranslated screenplay format markers.
- `scripts/build_html.py` renders the batch into reader-facing HTML while preserving structured markers for audit.
