# Chapter 1 L0 live-smoke gate decision — 2026-08-14

## Decision

Authorize exactly the fixed S1-S3 live smoke slots with Paratera model
`DeepSeek-V4-Flash`. This decision does not authorize the 15-case
pilot or any 45-run repetition.

## Frozen configuration

- sampling: temperature 0, top-p 1, cache disabled;
- retries: zero model retries and zero tool retries;
- per model call: at most 1,024 completion tokens;
- per run: 12 model turns, 10 tool calls (Scientist 4, Engineer 8), 600 seconds,
  and 70,000 recorded total tokens;
- first comparison, if separately authorized after smoke review: 15 single
  matched runs in seeded balanced order;
- failure policy: preserve the partial run and stop the batch; never replace a
  failed case or silently change provider/model.

The former SiliconFlow price estimate is not reused for Paratera. Paratera
uses token-based billing, but its account-specific V4-Flash price must be read
from the provider console. The 70,000-token ceiling remains the hard exposure
limit; every run records provider usage metadata for the actual cost audit.

The provider-call timeout remains 120 seconds. The longer run wall-time only
accommodates the serial recovery chain and observed variable model latency; it
does not relax token, turn, tool-call or retry limits.

## L0 verification

- complete suite after live-smoke remediation: 102 tests passed;
- clean virtual environment: 101 unittest cases passed;
- control-plane/evaluator coverage: 90% branch-aware coverage (threshold 85%);
- `compileall` and `git diff --check`: passed;
- panel/source integrity, evaluator isolation, redaction, missing-key,
  timeout/API failure, budget and non-overwrite tests: passed;
- Paratera provider probe: `/models` and a minimal V4-Flash chat completion
  returned HTTP 200; no credential was written to tracked files.

The untracked local environment flag remains the independent second gate.
