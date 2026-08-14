# Chapter 1 Paratera 5 × 3 live pilot result — 2026-08-14

Frozen commit: `2aeecd3` for the runtime/prompt policy, with the audited pilot
runner at `30c8075`. Provider/model: Paratera `DeepSeek-V4-Flash`. The local
API gate was closed immediately after the one completed batch.

## Batch integrity

- 15/15 scheduled slots completed and passed their external evaluator;
- provider/model, redacted endpoint identity, sampling, zero-retry policy,
  per-run budgets, code/panel hashes, actual usage and wall time are recorded
  in each run manifest;
- 15 traces and manifests exist; every required process graph and every
  referenced artifact is present;
- the frozen balanced order is in `pilot_batch_manifest.json`; aggregate usage
  and per-case outcomes are in `pilot_summary.json`;
- no failed run was overwritten or removed. Earlier failed provider/protocol
  attempts remain separately retained as anomalies.

## Execution outcomes

| Condition | Pass | Terminal statuses | Total tokens | Wall time |
| --- | ---: | --- | ---: | ---: |
| B1 static | 5/5 | 3 controlled stops, 1 clarification, 1 completed | 31,228 | 76.6 s |
| B2 adaptive | 5/5 | 2 controlled stops, 1 clarification, 2 completed | 66,365 | 137.5 s |
| B3 checkpoint | 5/5 | 2 controlled stops, 1 clarification, 2 completed | 68,807 | 132.7 s |
| **Total** | **15/15** | — | **166,400** | **346.7 s** |

The actual monetary charge is intentionally not estimated from another
provider's price sheet. Use the Paratera account billing record alongside the
per-case `usage` metadata in the run manifests.

## Evidence boundary

This is a completed real-model **integration pilot**, supporting that the
frozen runtime can execute its 5 × 3 condition matrix with auditable terminal
states, recovery evidence and bounded resources. It does **not** establish a
comparative mechanism effect or spatial/scientific accuracy: those require the
separate outcome-analysis and external-grading step before any Chapter 1
effectiveness claim.
