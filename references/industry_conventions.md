# Industry Conventions

Use these conventions as default judgment, not as hard-coded proof. Source PDFs may be reading drafts, spec scripts, production drafts, shooting scripts, teleplays, animation scripts, or publicity/award-season exports.

Read this file before writing or changing extraction heuristics for real screenplay projects. Its purpose is to prevent ordinary industry variation from being misdiagnosed as a PDF extraction bug.

## Script Type First

- Reading drafts, spec scripts, and public "read the screenplay" PDFs may omit production metadata such as scene numbers, revision colors, locked pages, and omitted-scene bookkeeping.
- Shooting scripts and active production drafts commonly include scene numbers, revisions, omitted scenes, A/B pages, and other production-control markers.
- Do not fail a project only because no scene numbers are present. Fail only when the source appears to contain scene numbers but extraction cannot reconcile them.
- If scene numbers are absent, build reader navigation from scene headings/slugs such as `INT.` and `EXT.`. Label it as scene navigation, not numbered scene index, and never invent scene numbers.

## Standard Format Baseline

- Common screenplay elements include scene headings, action, character cues,
  dialogue, parentheticals, transitions, shots, continueds/extensions, and
  general/text elements. Treat these as source document structures first, not
  ordinary prose.
- Cover or title pages commonly include the title, writing credits such as
  `Written by`, `Screenplay by`, `Story by`, source-material credits such as
  `Based on`, draft dates, contact blocks, copyright notices, and revision
  metadata. Placement varies by source. Translate reader-facing title-page
  metadata into project-local `references/front_matter.md`; do not make the
  renderer infer semantic labels from raw title-page rows.
- Margins, indentation, page-number position, and physical line counts are
  source-format evidence. Preserve page mapping and visible structure where
  useful, but do not force HTML output to mimic U.S. letter layout or page
  timing.
- Action text generally describes visible or audible story information. Source
  emphasis such as uppercase sound cues, underlines, italics, or bold should be
  treated as visible format evidence and preserved through the existing batch
  markup surface when it affects reading or audit.

## Scene Numbers

- Scene numbers are production metadata. They are usually added when a script goes into production or pre-production, not while reading or submitting a spec script.
- Standard numbered screenplays place numbers beside scene headings, often on both left and right margins.
- Once scene numbers are locked, inserted scenes may use letter suffixes such as `28A`; deleted production scenes may be represented as `OMITTED` while preserving the original number.
- Some formats may number or letter other elements, especially multicam TV, animation, interactive, multimedia, or house-style scripts. Treat these as format-specific evidence, not global rules.

## Scene Headings

- Scene headings, also called sluglines, are ordinary screenplay structure and should be translated even when no scene numbers exist.
- A typical scene heading communicates interior/exterior status, location, and time of day.
- Scene-heading navigation should use the source heading order. It may include a short translated heading and displayed page number, but it must not imply source scene numbering.

## Voice And Position

- `V.O.` indicates voice-over: narration, inner speech, reading, remote speech, or commentary that usually does not originate from a visible speaker physically in the scene.
- `O.S.` indicates off-screen: the speaker is in the scene's physical space but outside the frame.
- `O.C.` is often used similarly to off-camera/off-screen, with house-style variation.
- For translation, distinguish `V.O.` from `O.S.`. Prefer "旁白" or "画外叙述" for narrative `V.O.`, and "离画" for `O.S.` / `O.C.` when the character belongs to the current scene space.

## Omitted Scenes

- `OMITTED` is strongest evidence of a numbered production or revision workflow. In active production, the omitted marker preserves numbering continuity after a scene is removed.
- In unnumbered reading drafts, a deleted scene may simply be absent. Do not create an `OMITTED` entry unless the source shows one.

## Revision Colors

- Revision-color labels such as `White Draft`, `Blue`, `Pink`, `Yellow`,
  `Green`, `Goldenrod`, `Salmon`, `Cherry`, `Buff`, and `Tan` are industry
  production/revision terminology, not extraction noise by default.
- `White Draft` commonly refers to the original or base issue before colored
  revision pages. Later color labels may appear on title pages, page headers, or
  revision records.
- Treat revision-color labels as title-page or production metadata when the
  source presents them that way. Do not hard-code a fixed color sequence as a
  renderer rule; record and translate the visible source metadata in the
  project-local front matter artifact.

## Screenplay Source Type and Subtitle Alignment

Reference subtitles are timed text synced to video and audio. When the user
provides them for a project, they are the dialogue translation source, but they
are not a source-text transcript for extraction, structure, or non-dialogue
screenplay elements.

When the source screenplay and reference subtitles come from different versions,
`字幕差异` and `字幕未见` may reflect normal version differences. Do not treat
subtitle mismatch alone as an extraction or translation error.

Use screenplay source type as alignment context:

- Read-the-screenplay releases and post-production published scripts should
  usually align more closely with the final film, while still allowing subtitle
  compression, scene cuts, and localization choices.
- Production drafts, shooting scripts, and revised drafts may differ from the
  final film in scene order, dialogue, or omitted material.
- First drafts, early drafts, and spec scripts may have limited subtitle
  coverage. Use subtitles only where local correspondence is visible.
- Teleplays vary by production and episode version. Prefer local scene and
  dialogue evidence over a global match expectation.

When source type is known, record it in the Stage 2 signal report or
confirmation notes. Add it to `project.yaml` only if the project has a defined field
for that metadata. Adjust subtitle alignment reports accordingly, but keep
extraction failures tied to source evidence such as missing pages, broken text
order, or marker loss.

## Sources

- Final Draft, "What are script elements?": General, Scene Heading, Action,
  Character, Dialogue, Parenthetical, Transition, Shot, Cast List, continueds,
  and extensions.
  <https://kb.finaldraft.com/hc/en-us/articles/27646947570196-What-are-script-elements>
- Final Draft, "How do I number scenes?": scene numbering belongs under `Production > Scene Numbers`; standard screenplay numbering applies to scene headings and can draw numbers left/right. <https://kb.finaldraft.com/hc/en-us/articles/27810301418132-How-do-I-number-scenes>
- Final Draft 10 User Guide, Production Menu: scenes traditionally are not numbered until pre-production; scene numbering is not recommended for spec scripts. <https://www.finaldraft.com/downloads/manuals/fd10win.pdf>
- Final Draft, "How do I omit a scene?": `OMITTED` is for active production because scene numbers must not change. <https://kb.finaldraft.com/hc/en-us/articles/27810683389460-How-do-I-omit-a-scene>
- Final Draft, "Screenplay Formatting and Elements": scene headings start scenes and identify interior/exterior, location, and time of day. <https://www.finaldraft.com/learn/screenplay-formatting-elements/>
- Final Draft, "What are the standard revision set colors?": lists the
  standard revision color order beginning with Production White and continuing
  through Blue, Pink, Yellow, Green, Goldenrod, Buff, Salmon, Cherry, and later
  double-color sets. <https://kb.finaldraft.com/hc/en-us/articles/15575314119316-What-are-the-standard-revision-set-colors>
- Screenwriting.io, "Should I put scene numbers in my screenplay?": production staff number scenes when a script is going into production. <https://screenwriting.io/should-i-put-scene-numbers-in-my-screenplay/>
- Final Draft, "How to Use Voice Over in a Screenplay": distinguishes voice-over from off-screen dialogue. <https://www.finaldraft.com/blog/how-to-use-voice-over-in-a-screenplay-formatting-and-best-practices-explained>
- Apple Final Cut Pro User Guide, "Intro to captions": captions are timed text synced with video and audio; subtitles translate dialogue for foreign-language films and TV shows. <https://support.apple.com/en-gb/guide/final-cut-pro/ver00e40835d/mac>
- Netflix, "Timed Text Style Guide: General Requirements": timed text follows timing, line treatment, positioning, and delivery guidelines. <https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements>
