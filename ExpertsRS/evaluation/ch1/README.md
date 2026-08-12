# Chapter 1 benchmark-20 evidence package

## Status and purpose

This package preserves the original 20-request evaluation set and its lineage.
It may later provide a small regression panel for Chapter 1, but the current
Chapter 1 method is evaluated on role handoff, plan/action/observation
consistency, progressive graph materialization, terminal state, artifact
closure, local recovery, and runtime cost. It is not a pixel-accuracy benchmark
and does not establish the scientific correctness of remote-sensing products.

`benchmark_20_admission_gold_v0.json` is an archived Sol-high draft. Its
scientific-risk, proxy-validity, and claim-boundary annotations mixed Chapter 2
knowledge questions into Chapter 1 runtime evaluation. It is retained for
provenance but marked `superseded_draft_do_not_use_for_ch1_metrics`; researcher
sign-off on those 20 admission labels is no longer the next Chapter 1 gate.

## Frozen sources

- Original source:
  `D:/codes/User-centric RS/ExpertsRS/validation_new/benchmark_20.json`
- Original SHA-256:
  `595B546B4ADEF7C7F2AD8122296DC60C51343ECFE21903A5D38D817D5A6EFB65`
- An identical copy also exists under the historical `validation_single`
  directory.
- The frozen in-repository semantic copy is `benchmark_20_original.json`; do
  not edit it. Its byte hash is
  `F779D5B5BB3DD44F7AE3ECAD81C3F4D2F3FDC6070F07E41F6F73E358CD097D2D`
  because repository line endings differ, while parsed JSON equality has been
  verified.
- The historical split is 10 `single step` and 10 `multi step` requests.

The historical multi-agent run directory still contains one chat history and
generated artifacts for each of the 20 requests (147 files, about 113 MB). No
per-request planning/result correctness labels or a reproducible gold rubric
were found in the inspected validation directories.

## Data discontinuity that must remain explicit

The historical and modern rasters are different evidence objects.

| Track | Raster contract | SHA-256 |
| --- | --- | --- |
| Historical Table 2 track | 784 x 1284, EPSG:4326, 26 bands, no descriptions, `1.79e+308` nodata | `ACAD5A9A4E594BBEDC4E0883B8939B2D7C56253B1AA20B220912B1C982B11A7E` |
| Modern runtime track | 604 x 1280, EPSG:32650, 10 m, 10 described bands B2--B12, no declared nodata | `557E28C8E947C609DD57E20E7854DF0F775648223F8BC2197BC8297A4C739F9F` |

The 26-band historical stack appears to contain 12 Sentinel-2 reflectance
bands followed by auxiliary products such as AOT/WVP/SCL/TCI/masks, but it has
no embedded band names. Historical code therefore relied on assumed stack
positions. The modern dataset deliberately makes spectral semantics explicit.

Consequently, new results must not be presented as a strict before/after
replication of Table 2. Table 2 is a historical baseline; the modern benchmark
is a matched-context runtime evaluation.

## Prompt preservation policy

Do not overwrite the original questions. Their weaknesses are useful runtime
fixtures.

- Keep clean supported requests such as false colour, NDVI, NDWI, EVI, water,
  and green-cover calculation.
- Preserve underspecified terms such as vegetation health, open space, and
  "near" as source material. Chapter 1 may test whether an externally supplied
  unresolved question is routed and recorded correctly; deciding the scientific
  question itself is Chapter 2 work.
- Preserve scientifically unsupported requests such as Sentinel-2 LST, urban
  heat island, road networks, flood accumulation, relief-site suitability, and
  causal greening mitigation as Chapter 2 candidate fixtures. Chapter 1 may use
  their already-declared failure/stop events to test terminal-state mechanics,
  but scientific stop correctness is not a Chapter 1 gold label.
- Record grammar or missing inherited context in annotations. A future
  normalized prompt set may be created only as a separate version after the
  original comparison track is frozen.

The archived draft admission distribution is seven `execute`, six
`ask_or_downgrade`, and seven `controlled_stop` preferred actions. Those labels
remain useful as a record of a discarded evaluation interpretation, not as a
Chapter 1 denominator. Questions such as whether an NDVI threshold is an
acceptable scientific proxy, whether a missing NDSI operator authorizes custom
formula code, or whether Sentinel-2 supports a substantive environmental claim
belong to knowledge/method validity review rather than the runtime's primary
success label.

## Minimal Chapter 1 evaluation

The primary observations should remain simple and reproducible:

1. **Plan/action consistency**: whether the next action is justified by the
   current plan and available observation.
2. **Observation-driven revision**: whether new evidence changes only the
   affected plan/graph region and records the reason.
3. **Execution closure**: whether the run ends with the requested artifacts and
   a complete trace/graph, or an explicit terminal state rather than false
   success.
4. **Recovery locality**: whether a seeded failure resumes from a valid logical
   checkpoint without redoing unaffected work.

Report tool calls, model turns, actual API tokens, wall-clock time, repairs,
and human interventions as secondary cost/behavior measures. Do not collapse
them into one opaque score.

Mechanism tests should separately report seeded failure detection, branch
creation, branch selection, and recovery behavior. Twenty natural-language
tasks are too few to claim broad statistical superiority; they are a regression
panel and continuity bridge to the original paper. A small matched subset is
enough for the first adaptive-path pilot.

## D3-light five-task panel

`d3_light_panel_v1.json` freezes a five-task candidate panel selected directly
from the unchanged 20 requests:

| Source ID | Runtime role | Why it remains in Chapter 1 |
| ---: | --- | --- |
| 2 | clean supported control | Measures ordinary artifact closure and adaptive overhead without a seeded failure |
| 3 | missing registered tool | Tests explicit capability stop and prevents false substitution |
| 10 | data-precondition stop | Tests whether real metadata prevents a false LST success |
| 11 | multi-step seeded recovery | Isolates plan revision and checkpoint reuse after one operational, non-scientific failure |
| 13 | Manager clarification boundary | Tests user-facing unresolved-question routing without deciding what “vegetation health” scientifically means |

The panel does not edit the original prompts. It compares three matched
conditions: `B1_static`, `B2_adaptive`, and `B3_checkpoint`. Only task 11 has a
seeded failure: the first threshold write fails after NDVI succeeds. This leaves
the scientific method unchanged and makes recovery locality observable.

The JSON includes expected terminal states and required runtime evidence, but
these contracts belong to the external evaluator. They must not be inserted
into an Agent prompt or otherwise leak into the tested trajectory. The panel is
currently `frozen_candidate_panel_no_api`; selecting it does not authorize API
calls or promote any effect claim.

## D3-light run protocol (frozen, no API)

The single runner and external scorer have been exercised across all 15 slots
using a deterministic substitute for the decision model. This proves that the
case matrix, one seeded operational failure, terminal states, artifact checks,
plan-revision/checkpoint expectations, graph construction, and evaluator
separation fit together. It does **not** substitute for a real-model run.

The proposed live configuration is deliberately conservative: one existing
tool-capable model family (`DEEPSEEK_MODEL`, default
`deepseek-ai/DeepSeek-V3`), temperature `0`, no response cache, 30 group-chat
rounds, 12 model turns, 10 total tool calls, 300 seconds, 6,000 completion
tokens and 18,000 recorded tokens per run. Model and tool retries are zero:
network/API failures become recorded terminal outcomes rather than hidden
replacement runs. The exact values, hashes, versions, usage metadata and wall
time are emitted in each planned run manifest.

The future live provider remains intentionally unimplemented. It must implement
the runner's small decision interface while preserving the existing
Manager–Scientist–Engineer–Executor routing; it may not expose fixtures or
scoring contracts to the agents. Live calls require two separate approvals:
the frozen JSON gate and a local environment flag. Both are currently closed.

## Relationship to the historical Table 2

Retain the original columns as historical vocabulary, with tighter modern
definitions:

- `Planning Correctness Rate` becomes plan/action consistency plus correct
  observation-driven revision.
- `Result Correctness Rate` becomes execution closure and recovery correctness
  for Chapter 1; it must
  not be described as pixel-level thematic accuracy.
- `Average Token Consumption` remains a cost measure, but new runs must use
  actual model usage metadata and matched prompts/budgets.

The displayed historical table contains at least one arithmetic inconsistency:
Base LLM result correctness is shown as 5% for single-step, 0% for multi-step,
and 5% total. With equal 10/10 groups, the first two values average to 2.5%,
not 5%. The per-case labels and denominator convention are currently missing,
so the value must be marked `historical_reported`, not silently recalculated.

Current historical chat artifacts also report zero API cost/usage in several
saved `ChatResult` objects, and the inspected utility can disable usage
tracking. The provenance of the published token totals therefore remains an
open audit item.

## Evaluation boundary across thesis chapters

| Chapter | Evaluation question | Suitable evidence |
| --- | --- | --- |
| Chapter 1: system method/runtime | Can a user-facing domain-agent system adjust plans from real observations, materialize an auditable execution graph, and recover locally? | Unit/integration fixtures, a matched benchmark subset, graph/trace completeness, recovery locality and cost |
| Chapter 2: knowledge and scientific contracts | Are proposed constraints supported, relevant, conflict-aware, and able to cause correct action changes? | Evidence spans, constraint gold, invalid/missing/conflicting fixtures, admission/enforcement comparison |
| Chapter 3: end-to-end evaluation | Does the complete research system improve task outcomes and remain robust across tasks/data/users? | Independent task sets, scientific outcome graders, spatial/quantitative accuracy where available, robustness and human review |

## Gate progress after scientific-precondition remediation

Completed locally on 2026-08-07:

- semantic band resolution, nodata invariants, adapter signatures, and the
  Sentinel-2-to-LST stop condition;
- deterministic tests for the newly encoded scientific preconditions;
- a regenerated scripted pilot with reconstructable arguments.

Before spending material API budget:

1. Implement one matched runner for the already frozen `B1/B2/B3` contracts;
   do not maintain three unrelated scripts.
2. Keep the evaluator view outside Agent context and dry-run all 15 case slots
   with deterministic or fake-model responses.
3. Freeze the live model, sampling configuration, prompts, per-run budgets,
   timeout and retry policy, then obtain explicit approval for API use.
4. Run the 15-case live integration smoke before deciding whether three
   repeated runs (45 total) or any expansion beyond the five tasks is justified.
