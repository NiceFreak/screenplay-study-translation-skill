# Marker Inventory

`source-markers.json` records screenplay structure markers extracted from the source PDF. It is the contract between marker scanning, HTML generation, and audit.

It does not store ordinary screenplay body text. Body rows belong in `source-lines.json`; translated rows belong in batch JSON.

## File Shape

```json
{
  "version": 1,
  "source": {
    "screenplay_pdf": "screenplay.pdf"
  },
  "markers": [
    {
      "type": "contd",
      "pdf_page": 23,
      "display_page": 22,
      "text": "(CONT'D)",
      "source_layer": "flipped",
      "x": 301.4,
      "y": 580
    }
  ]
}
```

## Required Fields

- `type`: normalized marker type
- `pdf_page`: physical PDF page number, 1-based
- `text`: source text as recovered
- `source_layer`: where the marker came from, such as `normal`, `flipped`, or `raw`

## Optional Fields

- `display_page`: screenplay-facing page number after project page mapping
- `x`, `y`: source coordinates when available
- `scene_no`: original scene number as a string
- `scene_key`: normalized scene label used only for pairing/comparison
- `position`: for scene numbers, usually `left` or `right`
- `context`: short nearby text for debugging

## Marker Types

Core marker types:

- `scene_no`
- `omitted`
- `contd`
- `more`
- `split_scene`
- `voice_or_position`
- `transition`
- `unknown_uppercase`

Audit should compare marker counts by `type` and, when possible, by page. Unknown markers should usually produce `WARN`, not `FAIL`.

For user-facing page selection and partial audits, use `display_page`. Use `pdf_page` only when checking physical PDF extraction behavior.

Split scene numbers such as `73pt2`, `73 pt2`, or `73 part 2` should use `type: "split_scene"` and keep the original string in `scene_no`. Do not normalize them into invented sequential scene numbers.

Standard screenplay scene numbers usually appear as left/right margin pairs.
The scanner should not rely on pure numeric scene numbers. Treat short margin labels as scene-number candidates by position and shape, including Roman numerals and digit-letter variants, while treating body text numbers as noise. A standard screenplay candidate should become an audited marker when the same label is paired on the left and right margins of the same source line.

Pairing is a validation heuristic, not a universal law. If a source uses single-sided numbers, unusual margin placement, or nonstandard labels, the extractor should report unmatched candidates rather than silently inventing or dropping scene numbers.

No credible `scene_no` markers is not by itself a failure; see `industry_conventions.md`. Keep the marker inventory free of invented scene numbers and let HTML fall back to scene-heading navigation.

`source-markers.json` should contain promoted, auditable markers. Scanner assumptions, extraction statistics, and unmatched candidates belong in validation reports such as `work/reports/sample-validation.txt`, so final marker inventories stay stable while uncertainty remains visible.

## HTML Contract

Generated HTML should mark screenplay structure with `data-marker-type` or a `marker-*` class:

```html
<span class="scene-no marker-scene_no" data-marker-type="scene_no">73</span>
<span class="marker-contd" data-marker-type="contd">（续）</span>
```

Use these markers only for screenplay-body structure, not for navigation indexes or explanatory notes. Text fallback exists for old outputs, but structured markers are the audit source of truth.

When `audit.require_structured_markers` is true, matching translated text is not enough. The generated HTML must include the structured marker for every audited source marker instance.
