# Chapter 1 L0 live-smoke gate decision — 2026-08-14

## Decision

Authorize exactly the fixed S1-S3 live smoke slots with SiliconFlow model
`deepseek-ai/DeepSeek-V4-Flash`. This decision does not authorize the 15-case
pilot or any 45-run repetition.

## Frozen configuration

- sampling: temperature 0, top-p 1, cache disabled;
- retries: zero model retries and zero tool retries;
- per model call: at most 1,024 completion tokens;
- per run: 12 model turns, 10 tool calls (Scientist 4, Engineer 6), 300 seconds,
  and 18,000 recorded total tokens;
- first comparison, if separately authorized after smoke review: 15 single
  matched runs in seeded balanced order;
- failure policy: preserve the partial run and stop the batch; never replace a
  failed case or silently change provider/model.

At the provider's 2026-08-14 displayed V4-Flash prices (CNY 1/M input tokens
and CNY 2/M output tokens), the conservative 18,000-token ceiling implies less
than CNY 0.04 per run if charged entirely at the higher output rate, or less
than CNY 0.60 for 15 runs. Actual usage should be lower; provider billing is
the authoritative cost record.

## L0 verification

- complete suite: 101 tests passed;
- clean virtual environment: 101 unittest cases passed;
- control-plane/evaluator coverage: 90% branch-aware coverage (threshold 85%);
- `compileall` and `git diff --check`: passed;
- panel/source integrity, evaluator isolation, redaction, missing-key,
  timeout/API failure, budget and non-overwrite tests: passed;
- provider probe: `/models` and a minimal V4-Flash chat completion returned
  HTTP 200; no credential was written to tracked files.

The untracked local environment flag remains the independent second gate.
