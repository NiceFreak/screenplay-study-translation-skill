# Subtitle Alignment

Reference subtitles are optional, but high-quality Chinese subtitles are
strongly recommended. When provided, subtitle content is used directly for
dialogue translation and subtitle style is the primary style-profile input.
Subtitle quality is judged by the user; the skill does not automatically
validate translation quality.

## With Subtitles

Normalize subtitles first with `scripts/parse_subtitles.py`. Supported fixture-tested formats are `.ass`, `.srt`, and `.vtt`.

Use neutral labels:

- `字幕匹配`: screenplay and subtitle are semantically consistent. Minor
  wording, tone, punctuation, segmentation, or numeric-detail differences do not
  change the translation judgment.
- `字幕差异`: a candidate subtitle exists, but the content differs materially
  enough to affect translation judgment.
- `字幕未见`: no corresponding subtitle can be found for the dialogue.

Do not require word-for-word matching.

Do not use a fixed string-similarity threshold as the authority for these
labels unless it has been calibrated against real project data. This is
especially important for English screenplay source and Chinese subtitles, where
cross-language wording similarity is not meaningful. Use semantic
correspondence in context as the rule, and keep any mechanical matcher advisory.

Evaluate subtitle labels at the expression-unit level rather than the raw
physical line level. A single screenplay dialogue unit may be split across
multiple PDF text rows, and a single subtitle expression may also be split
across multiple subtitle lines or events. When that happens, the label should
describe the whole spoken unit, not each fragment independently.

When a screenplay utterance is split across rows, combine the rows before
assigning a subtitle label. When a subtitle expression is split across multiple
events, combine the relevant subtitle evidence before assigning a label.
Mixed labels inside one spoken turn are a sign that the comparison granularity
is too small.

## Proper Nouns

When subtitles provide translations for proper nouns, use them for:

- character names
- place names
- fixed titles or nicknames
- organization names
- recurring cultural, historical, or religious proper nouns

This priority applies to dialogue and project terminology. It does not apply to
action description, scene headings, parentheticals, format markers, or other
non-dialogue elements, which AI translates using `style-profile.json`.

Record subtitle-derived proper nouns in the generated project's local
`references/terminology.md`, not in the skill-level terminology reference.

## Subtitle Annotations

Subtitle annotations such as translator notes, comment-style events, or `注:`
lines are reader-note evidence, not dialogue and not terminology entries.

For each project, collect subtitle annotations into a project-local annotation
list. Insert an annotation into a batch only when the annotated concept appears
in that batch's screenplay source range. Use a schema-supported `note` entry
near the first local source occurrence; do not insert future-range annotations
early.

## Expression-Unit Matching

Mark as `字幕匹配` when the expression unit matches, even if:

- subtitle segmentation differs
- wording, tone, punctuation, or number formatting differs slightly
- a count-in, repeated word, hesitation, or sentence tail is slightly shortened
- Chinese subtitles use naturalized phrasing
- one small word is missing but scene function is unchanged

Mark as `字幕差异` when the difference changes:

- speaker
- information
- story function
- media source
- action
- scene context

## Without Subtitles

Do not emit subtitle labels. AI translates all elements and may use terminology
notes or version notes when useful.

Translation quality depends on model judgment when subtitles are absent.
