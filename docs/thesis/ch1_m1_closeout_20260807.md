# Chapter 1 M1 Closeout: Trace-Native Workflow Prototype

> Date: 2026-08-07
>
> Audit update: the minimum software-method kernel and the scientific
> preconditions exercised by one scripted fixture are verified locally.
> Formal P0--P3 evaluation and an integrated live-LLM path remain open.

> **2026-08-09 architecture clarification:** this closeout remains the factual
> evidence package for the implemented static workflow baseline. It is not the
> final Chapter 1 method definition. The accepted forward method keeps the
> original user-facing Manager–Scientist–Engineer/Executor architecture and
> narrows its increment to adjustable layered planning, a progressively
> materialized Plan–Execution graph, and checkpoint-based local recovery. Those
> three objects are design-frozen but not yet integrated in code; see
> [`ch1_evidence_system/scope_gate.md`](ch1_evidence_system/scope_gate.md).

> **2026-08-07 audit and remediation checkpoint:** the audit downgraded the
> first pilot after finding a band-position error and a nodata count violation.
> ADR-002 then moved band, nodata, grid, area, reflectance-scale and LST
> preconditions into tools, contracts, prompts and tests. The regenerated pilot
> resolves B8/B4 to stack positions 7/3 and keeps nodata outside both classes.
> This re-admits the run as diagnostic scientific-precondition evidence, not as
> validated greenspace accuracy or method-effect evidence.

## Implemented baseline in one page

The implemented static baseline represents an implicit chat-driven plan with a
small set of inspectable objects and deterministic transitions:

```text
user intent
   -> TaskSpec
   -> WorkflowGraph over versioned OperatorSpec contracts
   -> validate_workflow
        -> valid: execute / inspect
        -> one unique safe missing output: targeted repair -> revalidate
        -> ambiguous, unsupported, or otherwise blocked: controlled stop
   -> WorkflowTrace(plan, findings, repair/stop, calls, artifacts, final status)
```

`TaskSpec` isolates goal, AOI/time, expected outputs, constraints, validation
needs and unresolved questions from the chat transcript. `WorkflowGraph` makes
artifact dependencies explicit. Eighteen adapters give the existing ExpertsRS
tool names minimal typed `OperatorSpec` declarations, and an introspection test
now rejects adapter/callable signature drift. The validator checks unknown
operators/artifacts, missing inputs, type mismatch, invalid order, local file
preconditions, missing expected outputs, required semantic bands/config and
declared output contracts. Repair is deliberately narrow:
it adds only a uniquely determined missing-output step and otherwise stops.

The ReAct-style upgrade is a supporting orchestration path, not an additional
scientific claim. Scientist and Engineer select tools; Executor alone executes
them; each observation returns to its requesting agent before a new decision.
Per-agent budgets and decision/tool/observation/handoff events make this path
inspectable. It remains separate from the published notebook and from the typed
workflow method so framework behavior does not define the Chapter 1 claim.
The current ReAct runner and typed workflow runner remain separate: a live LLM
does not yet generate a `WorkflowGraph` that is validated/repaired and then
executed through one unified trace.

## Closed evidence loop

One command from `ExpertsRS/` runs the no-API closeout:

```powershell
python run_m1_closeout.py
```

It covers four layers: scientific, benchmark, workflow and ReAct unit tests;
all 18 registered tool checks; deterministic repair and controlled-stop trace generation; and a
scripted pilot that actually reads the local Sentinel-2 scene and generates
two raster artifacts and a ReAct trace. The 2026-08-07 20:10 CST run passed 33
tests and 13 tool checks. The readable evidence manifest is
[`../evidence/ch1_m1/README.md`](../evidence/ch1_m1/README.md).

The earlier zero tool-call count is resolved as a recording-path defect. The
scripted pilot wrote `tool_call` events but bypassed the separate counter update;
recording an event now atomically updates its counter. A regression test covers
the scripted path, and the real-tool pilot asserts the expected final counts of
two Scientist calls and two Engineer calls.

## Claim boundary

The closeout permits this statement:

> 已分别实现并测试面向遥感工作流的 typed representation、执行前验证、有限局部修复/受控停止，以及 ReAct-style observation routing 与可检查 trace 的最小软件机制。

The three evidence levels must remain separate:

| Level | Current status | Permitted interpretation |
| --- | --- | --- |
| Scripted no-API pilot | Executed with verified B8/B4 resolution and nodata invariants for one fixture | Tool integration, observability and encoded scientific-precondition behavior; no thematic accuracy |
| Real LLM workflow | Runnable surface exists; no closeout result claimed | Engineering readiness only |
| Matched formal experiment | P0--P3 remains future work | Required before claiming improved LLM planning reliability or method effect |

Therefore M1 does not claim that real LLM planning reliability improved, that
arbitrary workflows are repairable, that multi-agent systems are generally
superior, or that a durable/distributed runtime has been completed. The
published ExpertsRS cases and 20-request benchmark remain prior feasibility
evidence and are not relabelled as evidence for the new mechanism.

## Thesis and interview handoff

The defensible narrative is: the published prototype exposed a planning
reliability and auditability gap; this upgrade introduced typed workflow objects,
machine validation, conservative local repair/stop, and trace evidence; an
independent audit then found scientific-semantic defects, which were converted
into fail-closed contracts and regression fixtures before the pilot was rerun.
The minimum kernel is locally implemented, while untracked source prevents a
rebuildable release and causal benefit still requires matched P0--P3 evidence.

The candidate downstream interfaces are `TaskSpec`, `OperatorSpec`,
`WorkflowGraph`, typed violations, `RepairDecision`, and `WorkflowTrace` event
records. Chapter 2 can now prepare evidence-governed scientific constraints
against these objects. Chapter 1 should only reopen for the matched effect
study, a demonstrated interface defect, or a thesis-level claim change—not for
UI, new roles, distributed execution, or broad runtime expansion.

The interface defects found by the 2026-08-07 audit meet that reopen condition.
The reusable audit, claim registry and writing materials now live under
[`ch1_evidence_system/`](ch1_evidence_system/README.md).
