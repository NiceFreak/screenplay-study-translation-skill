# Subtitle Alignment

Reference subtitles are optional. They help establish names, tone, rhythm, and film wording, but they are not the authority over the screenplay.

## With Subtitles

Normalize subtitles first with `scripts/parse_subtitles.py`. Supported fixture-tested formats are `.ass`, `.srt`, and `.vtt`.

Use neutral labels:

- `字幕匹配`: screenplay and subtitle broadly correspond in speaker, meaning, scene position, and narrative function
- `字幕差异`: screenplay and film/subtitle differ materially
- `字幕未见`: screenplay content has no subtitle match

Do not require word-for-word matching.

## Expression-Unit Matching

Mark as `字幕匹配` when the expression unit matches, even if:

- subtitle segmentation differs
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

Do not emit subtitle labels. Use direct translation, terminology notes, and version notes instead.

Translation quality must not degrade when subtitles are absent.
