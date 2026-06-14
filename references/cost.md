# Translation Cost Notes

How to reason about and measure the cost of producing a study edition. The
concern here is the recurring model-token cost of translating a screenplay, kept
separate from the one-time cost of building the skill.

## Two cost buckets

- **Development cost** — building and changing the skill: scripts, rules, and
  rework. One-time, amortized across every future translation; not a recurring
  bill. Rendering and reading-experience work falls here: build the script once,
  reuse it for free on every project, with no per-translation token cost.
- **Translation cost** — the model tokens spent translating one screenplay. This
  is the recurring cost and the only one worth minimizing.

Keep the two apart when measuring. A session that mixes code changes, design
discussion, and translation cannot report a clean translation cost.

## Measuring translation cost

Run this in a session dedicated to translation, so the number is not polluted by
development or rework:

1. Start a fresh session used only for translation — no code changes, no
   requirement changes.
2. Have inputs ready: screenplay PDF, bilingual subtitles, Chinese title.
3. Run the standard flow: 生成预览 → confirm the first-batch style →
   预览通过，继续跑完整本 → 生成成品 HTML → 导出 EPUB.
4. If a code bug surfaces, note it and fix it in a separate development session.
5. Record the session's token usage / cost (Claude Code `/cost`, or the
   provider console's usage by date or workspace).
6. That figure is the screenplay's translation cost; divide by displayed pages
   for a per-page number.

`scripts/cost_report.py` reports an artifact-size proxy, not billing. Do not
treat its USD estimate as the real cost.

## Cost levers and current status

| Lever | Effect | Status |
|-------|--------|--------|
| Reuse bilingual-subtitle Chinese for matched dialogue | model reuses instead of inventing → less output and reasoning | enabled (policy) |
| Compact per-batch context (`package_batch_context.py`) | feed only the current page range, not full files | enabled |
| 5–10 page batches | amortize fixed per-batch overhead | enabled (config) |
| Prompt caching of skill / contract / terminology | cut repeated input cost across batches | runtime-level (depends on the agent harness, not the skill) |
| Model tiering (cheaper bulk + strong model for gates) | lower $/token on bulk batches | not used (a single model keeps style and terminology consistent) |

Most token levers are already engaged. Prompt caching is a runtime setting rather
than a code change. Model tiering is the main remaining lever, and it trades a
style/consistency risk for savings — adopt it only with calibration on real
output.
