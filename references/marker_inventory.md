# Marker Inventory

`source-markers.json` records screenplay structure signals extracted from the source PDF. It is the contract between marker scanning, HTML generation, and audit.

It does not store ordinary screenplay body text. Body rows belong in `source-lines.json`; translated rows belong in batch JSON.

## File Shape

```json
{
  "version": 1,
  "source": {
    "screenplay_pdf": "screenplay.pdf"
  },
  "known_markers": [
    {
      "type": "contd",
      "pdf_page": 23,
      "display_page": 22,
      "text": "(CONT'D)",
      "source_layer": "flipped",
      "x": 301.4,
      "y": 580
    }
  ],
  "unclassified_signals": [],
  "noise_candidates": [],
  "markers": []
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

Current `source-markers.json` known marker types:

| Type | Chinese label | Meaning |
|------|---------------|---------|
| `scene_no` | 场号 | Original source scene number. |
| `split_scene` | 分段场号 | Split or continued scene number such as part 2. |
| `omitted` | 删场标记 | Source `OMITTED` marker. |
| `contd` | 续标记 | Source `CONT'D` / `CONTINUED` marker. |
| `more` | 下页续标记 | Source `MORE` marker. |
| `voice_or_position` | 声音/位置标记 | `V.O.`, `O.S.`, `O.C.` and related speaker markers. |
| `transition` | 转场标记 | Structured transition marker. |

This list is the current machine-readable schema surface, not a complete
screenplay-format encyclopedia. Do not add a new marker `type` here unless the
scanner, HTML renderer, audit logic, and fixtures are updated together. The
standard-format taxonomy below is a reference list for Stage 2 observation and
gap analysis; unimplemented items should remain `unclassified_signals` or
`noise_candidates` until they have explicit tooling support.

Audit should compare known marker counts by `type` and, when possible, by page.
Unknown source evidence belongs in `unclassified_signals` or `noise_candidates`,
not in marker schema.

For user-facing page selection and partial audits, use `display_page`. Use `pdf_page` only when checking physical PDF extraction behavior.

Split scene numbers such as `73pt2`, `73 pt2`, or `73 part 2` should use `type: "split_scene"` and keep the original string in `scene_no`. Do not normalize them into invented sequential scene numbers.

Standard screenplay scene numbers usually appear as left/right margin pairs.
The scanner should not rely on pure numeric scene numbers. Treat short margin labels as scene-number candidates by position and shape, including Roman numerals and digit-letter variants, while treating body text numbers as noise. A standard screenplay candidate should become an audited marker when the same label is paired on the left and right margins of the same source line.

Pairing is a scanner heuristic, not a universal law. If a source uses single-sided numbers, unusual margin placement, or nonstandard labels, the scanner should record unmatched candidates as warning signals rather than inventing, dropping, or reclassifying scene numbers.

No credible `scene_no` markers is not by itself a failure; see `industry_conventions.md`. Keep the marker inventory free of invented scene numbers and let HTML fall back to scene-heading navigation.

`source-markers.json` should contain auditable known markers plus explicit signal records. `known_markers` and legacy `markers` contain only allowed marker types. `unclassified_signals` and `noise_candidates` preserve unknown evidence without upgrading it to schema.

## Standard Screenplay Marker Taxonomy

This taxonomy collects common Hollywood screenplay and production-script
signals. It is intentionally broader than the current scanner. Use it to decide
whether an observed source pattern is a known industry convention, a
project-specific house style, or low-confidence noise.

Source-priority note: public WGA.org pages reviewed for this update do not
publish a single authoritative screenplay-marker specification. The Writers
Guild Foundation primers are useful formatting references but explicitly operate
separately from WGAW. Final Draft documentation is treated as the primary
software-format source because it defines script elements and production
features used by many industry drafts.

### Scene Heading And Slug Signals

- Master scene heading intros: `INT.`, `EXT.`, `INT./EXT.`, `EXT./INT.`,
  `I/E`, `I/E.`, `E/I`, `E/I.`.
- Scene heading components: location text and time-of-day/status labels such as
  `DAY`, `NIGHT`, `MORNING`, `EVENING`, `DAWN`, `DUSK`, `LATER`,
  `MOMENTS LATER`, `SAME`, `CONTINUOUS`, `FLASHBACK`, `PRESENT`, and
  source-specific dates or years.
- Secondary slug/subheading signals: short all-caps location or beat headings
  inside a scene, such as `KITCHEN`, `HALLWAY`, `LATER`, or `ON THE SCREEN`.
- Scene numbers: left/right margin numbers or labels attached to scene headings,
  including numeric, Roman, lettered, and inserted labels such as `28A`,
  `A28`, `73pt2`, or `73 pt2`.

### Action, Shot, And Camera Signals

- Action is a standard screenplay element but is usually body text, not a marker
  by itself.
- Shot/camera headings are commonly all-caps lines such as `ANGLE ON`,
  `CLOSE ON`, `CLOSE UP`, `C.U.`, `ECU`, `WIDE SHOT`, `POV`, `REVERSE ANGLE`,
  `PAN`, `TILT`, `PUSH IN`, `PULL BACK`, `TRACKING`, `AERIAL`, `INSERT`,
  `INSERT SHOT`, `MONTAGE`, `SERIES OF SHOTS`, `INTERCUT`, and
  `END INTERCUT`.
- Screen-text and title-card signals include `SUPER:`, `TITLE:`, `TITLES:`,
  `MAIN TITLES`, `CHYRON:`, `CAPTION:`, `SUBTITLE:`, `TEXT:`, and
  `ON SCREEN:`.

### Character, Dialogue, And Parenthetical Signals

- Character cues are uppercase speaker names that precede dialogue. They are
  translation structure but are not currently source-marker records.
- Dialogue continuations and page-break markers include `(CONT'D)`,
  `(CONTINUED)`, `CONT'D`, `CONTINUED`, `(MORE)`, and `MORE`.
- Character extensions identify where speech originates, including `(V.O.)`,
  `(VO)`, `(O.S.)`, `(OS)`, `(O.C.)`, `(OC)`, `(ON PHONE)`, `(PHONE)`,
  `(RADIO)`, `(INTERCOM)`, `(FILTERED)`, `(PRE-LAP)`, and similar house-style
  source labels.
- Parentheticals are dialogue directions in parentheses below a character cue.
  They are structural translation context, but broad parenthetical detection is
  too noisy to promote into marker schema without layout evidence.
- Dual dialogue or simultaneous dialogue may be represented by side-by-side
  columns, paired dialogue blocks, or house-style labels such as
  `SIMULTANEOUSLY`.

### Transition Signals

- Common right-aligned or all-caps transitions include `CUT TO:`,
  `SMASH CUT TO:`, `MATCH CUT TO:`, `JUMP CUT TO:`, `HARD CUT TO:`,
  `DISSOLVE TO:`, `FADE IN:`, `FADE OUT.`, `FADE OUT:`, `FADE TO BLACK.`,
  `FADE TO BLACK:`, `WIPE TO:`, `IRIS OUT:`, `FLASH TO:`,
  `BACK TO SCENE:`, `BACK TO PRESENT:`, `INTERCUT WITH:`, and
  `END INTERCUT`.

### Production And Revision Signals

- Production scene bookkeeping includes scene numbers, inserted scene labels,
  A/B page labels, locked-page indicators, `OMITTED`, and omitted-scene
  retrieval marks or icons when extractable as text.
- Dialogue page-break production text includes `(MORE)` at the bottom of a
  page and `(CONT'D)` or `(CONTINUED)` at the top of the next page.
- Scene page-break production text includes `CONTINUED`, `CONTINUED:`, and
  numbered variants such as `CONTINUED: (2)`.
- Revision signals include right-margin revision marks, most commonly `*`.
  Production scripts may use another one- or two-character mark, revision text
  styling, or revision page colors. When the mark is text-extracted, keep the
  visible mark as source evidence; when only color/style carries the revision,
  record the limitation rather than inventing text.

### Television, Act, And House-Style Signals

- TV and multicam formats may include `COLD OPEN`, `TEASER`, `ACT ONE`,
  `END OF ACT ONE`, `ACT TWO`, `END OF ACT TWO`, `TAG`, `END OF SHOW`,
  `END OF EPISODE`, cast lists, music cues, and main-title cues.
- These are common industry signals but vary heavily by show, network, and
  template. Treat them as known format families, not universal requirements.

## Current Scanner Coverage

`scripts/scan_markers.py` currently recognizes these signals as known markers:

- `scene_no` and `split_scene`: paired left/right margin labels with numeric,
  Roman, single-letter, or digit-containing label shapes.
- `contd`: any extracted text containing `CONT'D` or `CONTINUED`.
- `more`: exact `MORE` or `(MORE)`.
- `omitted`: exact `OMITTED` or `OMMITTED`.
- `voice_or_position`: any extracted text containing `V.O.`, `O.S.`, or `O.C.`.

It also records all-caps structural-looking text as `unclassified_signals` and
low-confidence margin text as `noise_candidates`, but those records are not
known markers and are not audited as preserved structure.

`transition` is an allowed marker type in this document and the HTML/audit
contract, but the current scanner does not emit it.

### Standard Signals Not Currently Recognized As Known Markers

- Scene heading intros and sluglines: `INT.`, `EXT.`, `INT./EXT.`, `EXT./INT.`,
  `I/E`, location/time/status components, subheadings, `FLASHBACK`, `PRESENT`,
  `LATER`, `CONTINUOUS`.
- Transition markers: `CUT TO:`, `FADE IN:`, `FADE OUT.`, `FADE TO BLACK.`,
  `DISSOLVE TO:`, `SMASH CUT TO:`, `MATCH CUT TO:`, `JUMP CUT TO:`,
  `WIPE TO:`, `FLASH TO:`, `BACK TO SCENE:`, `BACK TO PRESENT:`,
  `INTERCUT WITH:`, `END INTERCUT`.
- Camera/shot and format lines: `ANGLE ON`, `CLOSE ON`, `CLOSE UP`, `C.U.`,
  `ECU`, `POV`, `REVERSE ANGLE`, `PAN`, `TILT`, `PUSH IN`, `PULL BACK`,
  `TRACKING`, `AERIAL`, `INSERT`, `INSERT SHOT`, `MONTAGE`,
  `SERIES OF SHOTS`.
- Screen-text/title signals: `SUPER:`, `TITLE:`, `TITLES:`, `MAIN TITLES`,
  `CHYRON:`, `CAPTION:`, `SUBTITLE:`, `TEXT:`, `ON SCREEN:`.
- Character and dialogue structure beyond existing continuation detection:
  uppercase character cues, parentheticals, dual dialogue, side-by-side
  dialogue, `SIMULTANEOUSLY`.
- Character extensions beyond dotted forms: `(VO)`, `(OS)`, `(OC)`,
  `(ON PHONE)`, `(PHONE)`, `(RADIO)`, `(INTERCOM)`, `(FILTERED)`,
  `(PRE-LAP)`.
- Production signals beyond existing `MORE`, `CONT'D`/`CONTINUED`, and
  `OMITTED`: A/B page labels, locked-page indicators, inserted scene/page
  labels not matching current margin-pair heuristics, and scene continuation
  variants that do not contain `CONTINUED`.
- Revision signals: right-margin `*`, alternate one- or two-character revision
  marks, revision page colors, and revision text styling.
- TV/act structure: `COLD OPEN`, `TEASER`, `ACT ONE`, `END OF ACT ONE`, `TAG`,
  `END OF SHOW`, `END OF EPISODE`, cast lists, music cues, and main-title cues.

## HTML Contract

Generated HTML should mark screenplay structure with `data-marker-type` or a `marker-*` class:

```html
<span class="scene-no marker-scene_no" data-marker-type="scene_no">73</span>
<span class="marker-contd" data-marker-type="contd">（续）</span>
```

Use these markers only for screenplay-body structure, not for navigation indexes or explanatory notes. Text fallback exists for old outputs, but structured markers are the audit source of truth.

When `audit.require_structured_markers` is true, matching translated text is not enough. The generated HTML must include the structured marker for every audited source marker instance.

## Reference Sources

- WGAW, "Screenwriters Handbook": official Guild career resource, not a
  screenplay marker specification.
  <https://www.wga.org/members/employment-resources/screenwriters-handbook>
- Writers Guild Foundation, "Screenplay Primers": formatting primers across
  screenplay concepts. WGF states that it operates separately from WGAW.
  <https://www.wgfoundation.org/screenplay-primers>
- Writers Guild Foundation, "Spec Script Formatting Primers": show-format
  survey and source-type caveat.
  <https://www.wgfoundation.org/script-formats>
- Final Draft, "What are script elements?": General, Scene Heading, Action,
  Character, Dialogue, Parenthetical, Transition, Shot, Cast List, continueds,
  and extensions.
  <https://kb.finaldraft.com/hc/en-us/articles/27646947570196-What-are-script-elements>
- Final Draft, "How do I number scenes?": standard scene numbers normally
  attach to scene headings; nonstandard numbering exists for other script
  types.
  <https://kb.finaldraft.com/hc/en-us/articles/27810301418132-How-do-I-number-scenes>
- Final Draft, "How do I omit a scene?": `OMITTED` replaces the deleted scene
  while preserving scene numbers in active production.
  <https://kb.finaldraft.com/hc/en-us/articles/27810683389460-How-do-I-omit-a-scene>
- Final Draft, "How do I modify or remove Mores and Continueds (CONT'Ds)?":
  standard dialogue and scene page-break text.
  <https://kb.finaldraft.com/hc/en-us/articles/27747514444180-How-do-I-modify-or-remove-Mores-and-Continueds-CONT-Ds>
- Final Draft, "How do I use Revision Mode?": revised text can create margin
  marks and page colors.
  <https://kb.finaldraft.com/hc/en-us/articles/27813588722708-How-do-I-use-Revision-Mode>
- Final Draft, "How do I select, modify or create a Revision Set?": `*` is the
  standard production-script revision mark; other short marks may be used.
  <https://kb.finaldraft.com/hc/en-us/articles/27815245815060-How-do-I-select-modify-or-create-a-Revision-Set>
