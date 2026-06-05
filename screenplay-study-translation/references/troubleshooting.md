# Troubleshooting

Use this file when a real project behaves differently from fixtures or expectations. Prefer source evidence, script type, and validation output over quick one-off fixes.

## Source Structure

### No Scene Numbers

- Check `industry_conventions.md` before treating this as a failure.
- Do not invent scene numbers. Use scene-heading navigation in HTML.
- If side-margin candidates exist but are not paired or credible, keep them in validation reports as `WARN`, not promoted source markers.

### Unmatched Scene-Number Candidates

- Inspect candidate text, coordinates, source layer, and nearby body text.
- Single letters or body-text fragments in margins are usually extraction noise.
- Single-sided or unusual house-style numbering may be valid, but should be promoted only after a fixture and validation rule cover it.

### Page Numbers Missing Or Offset

- Verify title pages and displayed screenplay pages separately.
- Infer missing printed page numbers only from a stable explicit sequence.
- Keep original PDF page, displayed page, inferred printed page, and correction reason in work artifacts.

### Title Page Text Missing

- Check whether the PDF uses normal text rows, raw text operators, flipped coordinates, or embedded images.
- If title-page text is in images only, OCR may be needed.
- Do not drop title-page author, draft, or contact metadata silently; place reader-relevant metadata in `front_matter`.

### Duplicated Or Split Text

- Use coordinate-aware merging before translation.
- Record merge assumptions and counts.
- Do not merge across lines when it changes dialogue order or parenthetical scope.

## Translation Batches

### Draft Placeholders In Final Output

- Run `validate_batch.py --final`.
- Replace every `待译...` placeholder before final HTML.
- Do not use `draft_batch.py` output as translation.

### Raw Format Markers In Chinese Translation

- Translate `CONT'D`, `MORE`, `V.O.`, `O.S.`, `O.C.`, `OMITTED`, transitions, and camera/format markers.
- Preserve structured markers in `markers`; use translated reader text in `translation`.

### Subtitle Labels Look Wrong

- When subtitles are present, labels may be `字幕匹配`, `字幕差异`, or `字幕未见`.
- Treat reference subtitles as evidence, not authority.
- Remove subtitle labels entirely when subtitles are absent.

## HTML Output

### Navigation Missing

- If source scene numbers exist, verify scene-heading entries contain `scene_no` or `split_scene` markers.
- If source scene numbers are absent, verify there are `scene_heading` entries so scene-heading navigation can be built.
- Never add fake scene numbers just to populate navigation.

### Links Broken

- Run `audit.py --html ...`.
- Fix generated ids, anchors, or entry ordering in batch generation, not by hand-editing final HTML.

### Reader Markup Not Rendering

- Check that final batch uses `__proper name__`, `**emphasis**`, and `*term*` markup where applicable.
- Run `build_html.py` or `finalize_html.py`; do not manually write HTML spans in batch translations.

## PDF Output

### PDF Too Small Or Crowded

- Do not solve this by shrinking Chinese text into page-aligned source pages.
- Page-aligned PDF is no longer a target.
- If PDF output is reopened, use a reflowed A4 reading/print layout.
- Preserve source positions with labels such as "原版第 X 页" instead of matching generated PDF pages to source PDF pages.

### PDF Page Count Mismatch

- A reflowed reading PDF is expected to have its own page count.
- Do not treat generated PDF page count mismatch as a failure unless the project explicitly defines a PDF-specific count contract.
- Verify that source-location labels still identify the correct original screenplay pages.

## Process

### A New Failure Mode Appears

- First classify it: industry convention, project-specific house style, source PDF defect, extraction bug, translation bug, or renderer bug.
- Add or update a reference note before changing heuristics if the issue is domain knowledge.
- Add a small positive and negative fixture before changing extraction or audit logic.
- Keep generated real-project artifacts out of git.
