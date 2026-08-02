# Chapter 1 Alignment: Workflow Planning Method

> Date: 2026-07-17
> Upstream: `D:/projects/phd-thesis/research-harness/THESIS_STATE.md`
> Status: thesis-facing alignment memo; does not change the public URSA paper claim.

## Role in the thesis

URSA/ExpertsRS is the prototype base for Chapter 1, but the thesis contribution
must move from “a multi-agent system can run remote-sensing tasks” to a testable
planning method:

> natural-language requirement → structured task specification → typed operator
> composition → validated workflow graph → targeted repair → execution trace.

The public prototype and published paper remain prior system evidence. They do
not by themselves establish the new Chapter 1 method claim.

## Minimum research interface

### TaskSpec

Required fields: goal, AOI/time, available inputs, expected outputs, operational
constraints, epistemic-constraint references, validation needs, unresolved
questions.

### OperatorSpec

Each existing remote-sensing tool should expose: operator ID, input/output types,
preconditions, effects/artifacts, failure modes, cost hints and provenance fields.

### WorkflowGraph

Nodes are task/operator instances. Edges represent data/control dependencies.
The graph must make missing inputs, invalid type links, unmet preconditions and
uncovered outputs machine-checkable.

### WorkflowTrace

Record the original plan, validator findings, repair decisions, tool calls,
artifacts, failures and final status. Do not infer the research result from chat
history alone.

## Work packages

| WP | Work | Deliverable | Gate |
| --- | --- | --- | --- |
| C1-WP1 | Inventory current tools and workflow states | operator registry draft | Existing tools resolve to stable IDs and types |
| C1-WP2 | Define TaskSpec and graph schema | versioned schema + examples | Covers at least four task families without task-specific hacks |
| C1-WP3 | Build plan validator | structured violations | Detects type, precondition, data, order and validation gaps |
| C1-WP4 | Build targeted repair | before/after subgraph + repair reason | Repairs only affected subgraph or explicitly stops |
| C1-WP5 | Build evaluation task set | 12–20 pilot tasks + faults | Tasks separated from gold checks and hidden from planner |
| C1-WP6 | Run P0–P3 study | paired results + error analysis | Same model/task/budget where comparisons require matching |

## Experimental conditions

- P0: direct/free-form LLM plan;
- P1: structured TaskSpec;
- P2: P1 + typed operators + graph validation;
- P3: P2 + targeted repair.

Fault injection must include missing data, unavailable tool, incompatible input,
invalid order and missing validation. Primary outcomes are executable-valid plan
rate and violation-family counts. Goal coverage, tool choice, cost and human
quality judgments remain separate outcomes.

## Relationship to Chapter 2 and Chapter 3

- Chapter 2 supplies `EpistemicContract` through a stable planner input; Chapter
  1 owns the planning/repair machinery, not the scientific content of contracts.
- Chapter 3 instantiates generic sample-construction operators. Beijing products,
  thresholds, class semantics and map validation remain in Chapter 3.

## Do not do yet

- Do not prioritize UI, more agent roles or framework migration before the
  method loop is testable.
- Do not claim that an end-to-end successful demo proves better planning.
- Do not make Chapter 1 depend on the full Chapter 2 knowledge base; manually
  supplied constraints must remain a valid test path.

