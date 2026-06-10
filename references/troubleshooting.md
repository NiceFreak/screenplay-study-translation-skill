# Troubleshooting

Use this file when a real project behaves differently from fixtures or expectations. Prefer source evidence, script type, and validation output over quick one-off fixes.

-----

## How to Add a New Entry

When a new failure mode is discovered:

1. Classify it first:
- industry convention (normal for this script type)
- project-specific house style
- source PDF defect
- extraction bug
- translation bug
- renderer bug
1. Add it under the relevant section using this format:

### [Symptom]

- what it looks like
- why it happens
- how to fix it
- whether a fixture or validation rule should be added

1. If the failure reveals missing domain knowledge:
- update `references/industry_conventions.md` before changing heuristics
1. If the failure appears to require a new extraction or audit rule:
- record the source evidence as a warning signal first
- add positive and negative fixture coverage before changing logic outside Stage 2

-----

## Source Structure

### No Scene Numbers

- Check `industry_conventions.md` before treating this as a failure.
- Do not invent scene numbers. Use scene-heading navigation in HTML.
- If side-margin candidates exist but are not paired or credible, keep them as warning signals, not known source markers.

### Unmatched Scene-Number Candidates

- Inspect candidate text, coordinates, source layer, and nearby body text.
- Single letters or body-text fragments in margins are usually extraction noise.
- Single-sided or unusual house-style numbering may be valid, but Stage 2 should only record it as a warning signal.

### Page Numbers Missing Or Offset

- Verify title pages and displayed screenplay pages separately.
- Infer missing printed page numbers only from a stable explicit sequence.
- Keep original PDF page, displayed page, inferred printed page, and correction reason in work artifacts.

### Source-Lines Missing A Visible Page

- If a physical PDF page is visible in a reader but absent from `source-lines.json`, classify it as an extraction bug first.
- Check whether the PDF content stream is compressed and whether stream bytes are read by `/Length` instead of by a loose `endstream` delimiter.
- Rerun `extract_pdf.py`, then `validate_sample.py`, and reconfirm Stage 2 before creating new draft batches.

### Title Page Text Missing

- Check whether the PDF uses normal text rows, raw text operators, flipped coordinates, or embedded images.
- If title-page text is in images only, OCR may be needed.
- Do not drop title-page author, draft, or contact metadata silently; place reader-relevant metadata in `front_matter`.

### Duplicated Or Split Text

- Use coordinate-aware merging before translation.
- Record merge assumptions and counts.
- Do not merge across lines when it changes dialogue order or parenthetical scope.

-----

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
- For dialogue entries, use subtitle content directly when a corresponding
  subtitle exists.
- Use `字幕差异` only when the content differs materially enough to affect
  translation judgment.
- Remove subtitle labels entirely when subtitles are absent.

### Mixed Subtitle Labels Inside One Spoken Turn

- This usually means the comparison granularity is too small.
- Check whether the screenplay dialogue was split into multiple PDF rows before
  label assignment.
- Check whether the subtitle evidence was split into multiple lines or events
  before comparison.
- Combine the relevant rows or events into one expression unit before judging
  `字幕匹配`, `字幕差异`, or `字幕未见`.
- Do not treat the mixed labels as independent translation judgments for each
  fragment.

-----

## HTML Output

### Navigation Missing

- If source scene numbers exist, verify scene-heading entries contain `scene_no` or `split_scene` markers.
- If source scene numbers are absent, verify there are `scene_heading` entries so scene-heading navigation can be built.
- Never add fake scene numbers just to populate navigation.

### Links Broken

- Run `audit.py --html ...`.
- Fix generated ids, anchors, or entry ordering in batch generation, not by hand-editing final HTML.

### Reader Markup Not Rendering

- Check that final batch uses `__proper name__`, `**source emphasis**`, `*source italic*`, and `[[reader annotation]]` markup where applicable.
- For source revision asterisks, use trailing `[[*]]`; the HTML renderer should place it at the right end of the screenplay line.
- Run `build_html.py` or `finalize_html.py`; do not manually write HTML spans in batch translations.

### Source Formatting Flattened

- Check whether source evidence shows the signal has a screenplay, production, or reading function.
- If it does, encode the signal in batch JSON first with an existing entry type, `markers`, layout metadata, or inline markup, then update the renderer if that existing structured data is not being visually restored.
- If confidence is low, keep it in warning/noise records instead of reader output.
- Do not hand-edit generated HTML or translate a formatting-only signal as if it were story prose.

### Reader Notes Not Visually Distinct

- Check that source annotations, translator notes, and front-matter notes are represented as schema-supported `note` entries.
- `note` entries should render with a distinct reader-note style, separate from screenplay action, dialogue, and scene-heading body text.
- Do not solve this by adding ad hoc punctuation or labels inside the translated text when the entry type can carry the distinction.

### Reading Progress Not Restored

- Confirm the generated HTML contains a stable `data-progress-key` on the `.screenplay-study` root.
- Check whether the browser allows `localStorage` for the current file or hosting origin.
- Do not restore saved scroll position when the URL contains a hash; explicit scene-index and page anchors take priority.

-----

## PDF Output

### PDF Too Small Or Crowded

- Do not solve this by shrinking Chinese text into page-aligned source pages.
- Page-aligned PDF is no longer a target.
- If PDF output is reopened, use a reflowed A4 reading/print layout.
- Preserve source positions with labels such as “原剧本第 X 页” instead of matching generated PDF pages to source PDF pages.

### PDF Page Count Mismatch

- A reflowed reading PDF is expected to have its own page count.
- Do not treat generated PDF page count mismatch as a failure unless the project explicitly defines a PDF-specific count contract.
- Verify that source-location labels still identify the correct original screenplay pages.

-----

## Process

### A New Failure Mode Appears

- First classify it: industry convention, project-specific house style, source PDF defect, extraction bug, translation bug, or renderer bug.
- Add or update a reference note before changing heuristics if the issue is domain knowledge.
- Record unknown structure as a warning or noise signal before changing extraction or audit logic.
- Add a small positive and negative fixture before changing extraction or audit logic outside Stage 2.
- Keep generated real-project artifacts out of git.
