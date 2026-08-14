# Paratera S1–S3 live-smoke result — 2026-08-14

Frozen commit: `a4006dc`. Provider/model: Paratera `DeepSeek-V4-Flash`.
The local API gate was closed immediately after the batch.

| Smoke | Case | Result | Evidence | Usage / wall time |
| --- | --- | --- | --- | --- |
| S1 | task-02 / B2 adaptive | PASS, completed | metadata → NDVI → map; valid report and trace | 14,058 tokens / 35.9 s |
| S2 | task-11 / B3 checkpoint | PASS, completed | one injected failure, plan v2, checkpoint reuse, one NDVI, recovery artifacts and report | 45,323 tokens / 62.7 s |
| S3 | task-13 / B2 adaptive | PASS, needs clarification | one metric clarification; no tool action | 844 tokens / 6.8 s |

The authoritative non-overwriting run package is
`ExpertsRS/results/ch1_d3_light/paratera_smoke_a4006dc/`. Earlier SiliconFlow
and Paratera failures remain preserved as anomalies and are not merged into
these passing results.

## L1 status

The technical S1-S3 gate and run-package review are passed. On 2026-08-14 the
researcher authorized exactly one 15-case matched pilot using the same Paratera
model, frozen budgets and seeded balanced order. The new pilot runner writes a
batch manifest before its first API call and a token/time summary after all 15
external evaluations pass; any failure preserves the partial batch and stops.
