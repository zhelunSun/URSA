# Chapter 1 Upgrade Freeze: Published Baseline to Trace-Native Planning

> Date: 2026-07-29
> Status: accepted Chapter 1 boundary for pre-outline work; task counts and
> implementation framework remain chapter-local decisions.

## 1. Evidence already carried by the published paper

The published ExpertsRS paper already establishes an initial feasibility claim:

- a Data--Tools--Brain conceptual framework;
- a three-LLM-agent prototype organized by a four-state workflow;
- two end-to-end case studies from vague user requests to remote-sensing outputs;
- a 20-request validation set with 10 single-step and 10 multi-step requests;
- comparisons against a base LLM and a single-agent system;
- planning correctness, result correctness and token use as metrics.

The multi-step result reported in the paper was 50% planning correctness and
40% result correctness for ExpertsRS, compared with no more than 20% for the
two baselines. These results are prior evidence, not the new thesis experiment.

The original evaluation has known boundaries:

- one Sentinel-2 scene and one Beijing ROI;
- a small request set;
- one remote-sensing PhD reviewer;
- endpoint/planning correctness rather than typed executability or trace quality;
- no matched test of validation, targeted repair, persistence or replay.

The thesis must not re-label this work as evidence for the new method.

## 2. Current implementation upgrade

The current local implementation adds:

- 18 standardized remote-sensing tools in four tool kits;
- a common callable registry and generated tool schemas;
- tool-first Engineer instructions;
- dynamic data discovery and structured result paths;
- executable tool verification tests.

This is a real Tool-layer upgrade. It is not yet a complete runtime upgrade.
The notebook still relies mainly on:

- AutoGen GroupChat;
- hand-written `speaker_selection`;
- conversation messages as implicit state;
- keyword-based transitions and failure detection;
- no durable checkpoint, event trace, replay or graph validator.

## 3. Frozen scientific increment

Chapter 1 moves from:

> a multi-agent prototype can complete remote-sensing tasks

to:

> structured task and operator semantics, workflow validation and targeted
> repair improve the executability and auditability of remote-sensing planning.

The scientific core is frozen to four parts:

1. **Task and workflow representation**
   - `TaskSpec`;
   - `OperatorSpec`;
   - `WorkflowGraph`.
2. **Machine-checkable validation**
   - missing input;
   - incompatible type;
   - unmet precondition;
   - invalid dependency/order;
   - uncovered output or validation obligation.
3. **Targeted repair**
   - repair the affected subgraph;
   - preserve unaffected steps;
   - stop or request information when repair is unsupported.
4. **Trace-native execution**
   - explicit state and events;
   - original plan, findings, repairs, calls, artifacts and final status;
   - replayable run manifest.

## 4. Supporting runtime features

The following support the scientific method but are not separate novelty claims:

- explicit serializable runtime state;
- basic token, wall-clock and iteration budgets;
- checkpoint/resume where proportionate to task length;
- tool error normalization;
- model/tool/version provenance;
- deterministic replay of validators and available tool results.

Sandboxing, OpenTelemetry integration, distributed scheduling, UI and framework
migration are optional engineering work, not Chapter 1 completion gates.

## 5. Evaluation boundary

Chapter 1 must include its own matched local experiment:

- P0: direct/free-form plan;
- P1: structured `TaskSpec`;
- P2: P1 + typed operators + graph validation;
- P3: P2 + targeted repair.

The main study should hold model, task, available tools, output expectations and
budget constant where the comparison requires matching. Faults should include
missing data, unavailable tool, incompatible input, invalid order and missing
validation.

Primary outcomes:

- executable-valid plan rate;
- violation counts by family;
- unsupported-repair/appropriate-stop rate;
- affected-subgraph edit size;
- trace completeness.

Goal coverage, tool choice, cost, latency and human quality judgments remain
separate outcomes.

The published ExpertsRS configuration is a historical baseline. It may be
reproduced as a supplementary condition, but its old results cannot be mixed
with the new matched study.

## 6. Chapter boundary

- Chapter 1 owns task/workflow/runtime mechanics.
- Chapter 2 owns the scientific content and evidence status of constraints.
- Chapter 3 owns the reliability evaluation framework, long-horizon/fault
  scenarios, user utility and experience reuse.

Chapter 1 does not claim:

- invention of geospatial workflow graphs in general;
- general Agent harness engineering;
- domain knowledge reliability;
- Agent RL, long-term memory or self-evolution;
- superiority of multi-agent architecture in every task.

## 7. Opening-evidence gate

Before the outline is treated as opening-ready, Chapter 1 should provide:

1. versioned schema examples covering several task families;
2. a working validator and at least one targeted-repair path;
3. a small P0--P3 pilot using matched conditions;
4. inspectable traces and a result manifest;
5. an explicit comparison with the evidence already published in ExpertsRS.

