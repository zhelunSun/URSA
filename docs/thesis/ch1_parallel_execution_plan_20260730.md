# Chapter 1 Parallel Execution Plan

> Date: 2026-07-30
> Upstream title: 基于多智能体的城市森林遥感工作流构建
> Status: active implementation plan; published evidence and the existing
> notebook remain immutable baselines.

## 1. Repository ownership

URSA owns the runnable implementation and matched local experiment for:

- typed task and operator semantics;
- workflow graph construction and validation;
- targeted repair;
- explicit runtime events and trace manifests.

The thesis control plane owns the claim and chapter boundary. Chapter 2 owns the
scientific content of knowledge constraints. Chapter 3 owns user-facing
reliability evaluation.

## 2. Baseline preservation

Do not rewrite the published ExpertsRS evidence or silently modernize the
notebook and then compare it with historical results.

Preserve:

- `ExpertsRS/ExpertsRS_notebook.ipynb` as the published-style prototype surface;
- the current 18-tool registry and tool tests;
- the paper's two cases and 20-request benchmark as prior evidence.

New runtime components should initially be added beside the notebook, with
adapters added only after unit tests pass.

## 3. Minimal implementation surface

Proposed package boundary:

```text
ExpertsRS/workflow/
  specs.py
  graph.py
  validator.py
  repair.py
  events.py
  trace.py
  adapters.py
```

This path is a reversible engineering choice, not a thesis claim.

## 4. Work packages

| WP | Codex work | Deliverable | Gate |
| --- | --- | --- | --- |
| R0 | Snapshot current operator registry and tool tests | baseline manifest | 18 tools resolve to stable IDs |
| R1 | Define `TaskSpec`, `OperatorSpec`, `WorkflowGraph` | versioned Python models + JSON examples | round-trip serialization and schema tests |
| R2 | Implement deterministic validator | typed violation records | detects missing input, type, precondition, dependency and validation gaps |
| R3 | Implement targeted repair protocol | repair request/result and before/after graph diff | unaffected subgraph preserved or explicit stop |
| R4 | Implement event/trace writer | `WorkflowTrace` + manifest | original plan, violations, repairs, calls, artifacts and final state inspectable |
| R5 | Build small P0--P3 pilot | matched run package and error analysis | same model/task/tools/budget where required |

## 5. Human participation

R0--R4 are reversible implementation work and do not require continuous human
approval. Codex should pause only before:

1. promoting the implementation into a formal Chapter 1 novelty claim;
2. choosing a formal experiment scale;
3. changing or deleting the published notebook path;
4. accepting a method framing that overlaps Spatial-Agent or another direct
   comparator without a written difference.

The human Gate A package must contain:

- recommended minimal Chapter 1 claim;
- closest comparator and non-claimable overlap;
- pilot evidence;
- work required for formal scaling;
- stop/fallback option.

## 6. Evaluation-first order

Implement the validator and trace before Agent orchestration changes. The first
pilot may use stored or generated plans without a full new multi-agent runtime.
This separates the scientific question from framework migration.

Only after R1--R4 pass should the notebook or a new runner consume the workflow
package.

## 7. Explicit non-goals

- no LangGraph migration merely for modernity;
- no distributed runtime, UI or observability platform;
- no Agent RL, memory or self-evolution;
- no automatic Git commits of user work;
- no claim that multi-agent is universally better than single-agent;
- no dependency on the full Chapter 2 knowledge base.

## 8. Process record

Every non-trivial implementation step should record:

- source commit/worktree status;
- schema or protocol version;
- test command and result;
- generated artifact path;
- whether the change is engineering support, diagnostic evidence or
  claim-relevant evidence;
- unresolved anomaly and retry lineage.

Raw runs remain in URSA. Only evidence pointers and accepted conclusions return
to `research-harness`.
