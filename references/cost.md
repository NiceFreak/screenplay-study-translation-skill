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

A clean baseline is a prerequisite, not just a report: do not adopt any
quality-for-cost lever (model tiering, reduced reasoning budget) without one,
because without it you can neither confirm the saving nor detect a quality
regression.

## Which costs are safe to cut

Not every token is equally safe to remove. Whether a cost can be cut depends on
whether removing it degrades output the reader cannot independently verify. This
follows from `SKILL.md` §1 — non-dialogue is the load-bearing surface, and
subtitles are the primary external anchor for non-dialogue quality:

- Dialogue cost is safe to compress: it is reused from subtitles, and the reader
  has the bilingual subtitle as a parallel check.
- Non-dialogue quality is load-bearing and must not be traded for savings: it
  has no subtitle backstop and the reader depends entirely on it.

Any lever that saves tokens by degrading non-dialogue translation — a cheaper
bulk model, a trimmed reasoning budget on translation batches — spends exactly
the quality the reader cannot verify, and conflicts with the tool's purpose.

## Cost levers and current status

| Lever | Effect | Status |
|-------|--------|--------|
| Reuse bilingual-subtitle Chinese for matched dialogue | model reuses instead of inventing → less output and reasoning | enabled (policy) |
| Compact per-batch context (`package_batch_context.py`) | feed only the current page range, not full files | enabled |
| 5–10 page batches | amortize fixed per-batch overhead | enabled (config) |
| Prompt caching of skill / contract / terminology | cut repeated input cost across batches | runtime-level; main zero-risk lever in ideal usage — run one screenplay in one continuous session |
| Model tiering (cheaper bulk + strong model for gates) | lower $/token on bulk batches | not recommended — targets non-dialogue quality (SKILL.md §1) |

Most token levers are already engaged. Prompt caching is a runtime setting rather
than a code change, and in the intended scenario it is the main zero-risk lever
(see below). Model tiering is not recommended for this tool: once subtitle reuse
takes over dialogue, the model's remaining work is almost entirely non-dialogue —
the load-bearing surface (SKILL.md §1) — so a cheaper bulk model spends exactly
the quality the reader cannot verify. Treat it only as a theoretical option for
future batch types with little judgment load, and never adopt it (or any
quality-for-cost trade) without a real `/cost` baseline to verify both the saving
and that quality did not regress.

## Ideal usage is near the cost floor

The intended scenario is an official standard screenplay PDF plus high-quality
bilingual subtitles whose quality the user verifies. There, subtitle reuse
already minimizes dialogue output and reasoning, and clean extraction removes
structural-ambiguity reasoning and rework, so the architecture sits near its
translation-cost floor. The one large, zero-risk lever left is prompt caching:
run one screenplay in a single continuous session so the stable prefix (skill,
contract, terminology, style profile) stays cache-warm and each batch's
incremental input collapses to the compact `batch-context-pXXX.json` package. Do
not start a new session per batch — that discards the cache. Every remaining
lever trades non-dialogue quality and is not appropriate here.
