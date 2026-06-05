# Industry Conventions

Use these conventions as default judgment, not as hard-coded proof. Source PDFs may be reading drafts, spec scripts, production drafts, shooting scripts, teleplays, animation scripts, or publicity/award-season exports.

Read this file before writing or changing extraction heuristics for real screenplay projects. Its purpose is to prevent ordinary industry variation from being misdiagnosed as a PDF extraction bug.

## Script Type First

- Reading drafts, spec scripts, and public "read the screenplay" PDFs may omit production metadata such as scene numbers, revision colors, locked pages, and omitted-scene bookkeeping.
- Shooting scripts and active production drafts commonly include scene numbers, revisions, omitted scenes, A/B pages, and other production-control markers.
- Do not fail a project only because no scene numbers are present. Fail only when the source appears to contain scene numbers but extraction cannot reconcile them.
- If scene numbers are absent, build reader navigation from scene headings/slugs such as `INT.` and `EXT.`. Label it as scene navigation, not numbered scene index, and never invent scene numbers.

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

## Sources

- Final Draft, "How do I number scenes?": scene numbering belongs under `Production > Scene Numbers`; standard screenplay numbering applies to scene headings and can draw numbers left/right. <https://kb.finaldraft.com/hc/en-us/articles/27810301418132-How-do-I-number-scenes>
- Final Draft 10 User Guide, Production Menu: scenes traditionally are not numbered until pre-production; scene numbering is not recommended for spec scripts. <https://www.finaldraft.com/downloads/manuals/fd10win.pdf>
- Final Draft, "How do I omit a scene?": `OMITTED` is for active production because scene numbers must not change. <https://kb.finaldraft.com/hc/en-us/articles/27810683389460-How-do-I-omit-a-scene>
- Final Draft, "Screenplay Formatting and Elements": scene headings start scenes and identify interior/exterior, location, and time of day. <https://www.finaldraft.com/learn/screenplay-formatting-elements/>
- Screenwriting.io, "Should I put scene numbers in my screenplay?": production staff number scenes when a script is going into production. <https://screenwriting.io/should-i-put-scene-numbers-in-my-screenplay/>
- Final Draft, "How to Use Voice Over in a Screenplay": distinguishes voice-over from off-screen dialogue. <https://www.finaldraft.com/blog/how-to-use-voice-over-in-a-screenplay-formatting-and-best-practices-explained>
