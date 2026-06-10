# Source Lines

`source-lines.json` records readable source text rows extracted from the screenplay PDF. It is the contract between PDF extraction and draft batch generation.

It is not the source of truth for side-margin structure markers. Scene numbers, `CONT'D`, `MORE`, `OMITTED`, and voice/source-position markers belong in `source-markers.json`.

## File Shape

```json
{
  "version": 1,
  "source": {
    "screenplay_pdf": "screenplay.pdf"
  },
  "assumptions": {
    "text_operator": "Tj",
    "displayed_page_offset": -1,
    "promoted_scene_markers_removed": true
  },
  "corrections": [
    {
      "type": "merge_character_rows",
      "original_count": 4388,
      "corrected_count": 154,
      "reason": "PDF text layer emits character-level Tj operations; rows are merged by page and y coordinate.",
      "confidence": "high"
    }
  ],
  "rows": [
    {
      "pdf_page": 2,
      "display_page": 1,
      "printed_page": 1,
      "text": "INT. ROOM - NIGHT",
      "x": 108.0,
      "y": 711.0,
      "source_layer": "merged",
      "parts": 18,
      "zone": "body"
    }
  ]
}
```

## Required Row Fields

- `pdf_page`: physical PDF page number, 1-based
- `display_page`: screenplay-facing page number after project page mapping
- `text`: recovered source text for the row
- `zone`: row role, usually `body` or `page_number`

## Optional Row Fields

- `printed_page`: printed page number inferred or extracted from the source
- `x`, `y`: source coordinates when available
- `source_layer`: extraction layer, such as `raw`, `merged`, or `normal`
- `parts`: number of lower-level text fragments merged into the row
- `style_spans`: optional range-based style evidence for bold, italic, or
  underline runs; style spans should not expose font names or font resources
  and should not assign semantic meaning by themselves

## Corrections

Corrections record deterministic extraction cleanup. They should preserve traceability and stay invisible in final reader-facing output.

Common correction types include:

- `remove_promoted_scene_markers`: remove scene numbers from body rows after they have been promoted into `source-markers.json`
- `merge_character_rows`: merge character-level PDF text operations into readable rows
- `infer_printed_page_numbers`: infer printed page mapping from stable explicit examples
- `fill_missing_printed_page_numbers`: fill local missing printed page numbers when the sequence is clear

Do not use corrections to change literary meaning, dialogue wording, scene order, or scene numbering.

## Relationship To Other Files

- `source-lines.json` feeds `scripts/draft_batch.py`.
- `source-markers.json` feeds structure audits and marker rendering.
- batch JSON combines source text rows with adjacent markers, but should preserve both `pdf_page` and `display_page`.

When partial samples are generated, filter by `display_page`, not `pdf_page`, unless the user explicitly asks for physical PDF pages.
