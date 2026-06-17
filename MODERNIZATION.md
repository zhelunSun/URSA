# Ch1 Modernization Plan - From Prototype Workflow to RS Agent Runtime

> Status: active foundation work
> Branch target: `codex/ch1-runtime-foundation`
> Principle: keep the AutoGen notebook as the paper prototype archive, and build the dissertation-grade system as a runtime-first architecture.

## Current Baseline

The public repository currently contains the paper prototype:

```text
ExpertsRS_notebook.ipynb
AutoGen GroupChat + handwritten speaker_selection
Agents: User -> Manager -> Scientist -> Engineer -> Executor
States: Clarify -> Define -> Solve -> Report, inferred from chat history
Tools: 18 standardized remote sensing tools registered through function_map + OpenAI-style tool schemas
```

This is good as a reproducible window for the published prototype, but it is too thin as the long-term dissertation system. The weakness is not only that the workflow is simple. The deeper issue is that task state, tool contracts, artifacts, evaluation, budget, and human checkpoints are not first-class system objects.

## Architecture Decision

Preserve the notebook as historical prototype code. Build the formal Ch1 system around a remote-sensing agent runtime:

```text
User intent
  -> explicit RunState
  -> multi-agent planning and verification nodes
  -> typed RS tool runtime
  -> artifact/provenance store
  -> evaluator and human checkpoints
  -> user-facing report
```

The runtime should be framework-tolerant. The first foundation layer should not depend on LangGraph, AutoGen, or any single agent framework. It should expose stable state, tool, and artifact interfaces that can later be driven by LangGraph, AutoGen v0.4, or another orchestrator.

## Why Runtime First

Modern research-agent systems increasingly treat the environment as the core object. Useful references:

- EurekAgent: explicit state graph, artifacts, budget control, resumability, human interface, and isolated evaluation.
- Earth-Agent and related EO agents: MCP-style tool ecosystems, tool trajectory evaluation, and multi-modal remote-sensing task coverage.
- AI Scientist-style systems: experiment loops, reviewers, and evaluation around complete research cycles.

The lesson for Ch1 is: do not merely add more agents. Make domain constraints, tools, evidence, and provenance first-class citizens.

## Minimum Dissertation-Grade System

The smallest system that can credibly support the dissertation should include:

1. Explicit state
   - user request, AOI, time period, resolution, selected data, methods, assumptions, pending questions, current phase
   - tool calls, artifacts, errors, decisions, checkpoints

2. Tool runtime
   - stable tool registry
   - input/output contracts
   - success/error handling
   - unit, CRS, nodata, band semantics added progressively

3. Artifact and provenance layer
   - one run directory per task
   - `run_manifest.json`
   - tool trace
   - output raster/map/report records
   - framework/model/cost metadata when available

4. Evaluator layer
   - final answer checks
   - tool trajectory checks
   - parameter sanity checks
   - spatial/output artifact checks

5. Human checkpoints
   - request clarification
   - plan approval
   - risky action approval
   - final acceptance or revision

6. Multi-agent nodes
   - Manager: user intent and report
   - Scientist: method and data reasoning
   - Engineer: tool execution plan
   - Verifier/Evaluator: correctness and provenance
   - Executor is demoted from a chat role into the runtime/tool layer unless code execution is truly needed.

## Framework Direction

### AutoGen

Keep AutoGen for the prototype archive. Current notebook-based AutoGen GroupChat is not ideal as the formal runtime because state, persistence, and evaluation are implicit. AutoGen v0.4 may still be useful for multi-agent conversation or GraphFlow experiments, but the long-term system should not be coupled to AutoGen's chat abstractions.

### LangGraph

LangGraph is a strong candidate for the next orchestration layer because it naturally supports explicit state, durable execution, persistence, human-in-the-loop interrupts, and graph nodes. The runtime foundation should be designed so a LangGraph adapter can drive it later.

### Claude Code CLI

Claude Code CLI is potentially valuable for the Engineer agent as an external coding/execution assistant, especially for complex glue code, debugging, and repository edits. It should be treated as an optional engineering backend, not as the foundation itself. The foundation must work even when this backend is absent.

### Multi-API Agents

Different agents can later use different model providers:

- Manager: fast, low-cost conversational model
- Scientist: stronger reasoning model plus knowledge retrieval
- Engineer: coding-capable model or Claude Code CLI backend
- Verifier: independent model/provider for critique and error detection

This is an important engineering improvement, but it belongs after the runtime can record model identity, cost, tool traces, and artifacts.

### Knowledge and Literature Retrieval

The research/scientist agent should eventually connect to:

- curated remote-sensing method knowledge
- dataset catalog and band ontology
- local dissertation notes
- academic search or paper retrieval

This is high leverage, but it should enter through the state/tool interface, not as ad-hoc prompt stuffing. The first runtime layer should define where retrieved evidence is stored and how it is cited.

## Phased Upgrade Plan

### Phase 0 - Archive and Stabilize Prototype

- Keep `ExpertsRS_notebook.ipynb` runnable as the paper reproduction window.
- Avoid mixing prototype reproduction code with the formal runtime.
- Add an archive tag when the runtime branch is ready, for example `paper-prototype-v0.2`.

### Phase 1 - Runtime Foundation

- Add `ExpertsRS/runtime/`.
- Define explicit `RunState`, `ToolCallRecord`, `ArtifactRecord`, and checkpoint structures.
- Add a `ToolRuntime` wrapper around the existing 18 RS tools.
- Add a `RunArtifactStore` that writes `run_manifest.json`.
- Add a minimal smoke workflow that can call tools through the runtime.
- Add tests without changing the notebook.

### Phase 2 - Typed RS Tool Contracts

- Enrich tool metadata with units, CRS expectations, nodata handling, band semantics, and output artifact classes.
- Make tool outputs easier to validate automatically.
- Add task templates for common RS workflows such as vegetation mapping, water extraction, LST, burn mapping, and zonal statistics.

### Phase 3 - Orchestration Upgrade

- Add a LangGraph adapter or comparable graph runtime.
- Convert Manager/Scientist/Engineer/Verifier into graph nodes over `RunState`.
- Add human checkpoints for request approval, plan approval, and final review.
- Keep AutoGen notebook as historical reference, not the active architecture.

### Phase 4 - Evaluation Harness

- Build curated benchmark tasks with expected tool trajectories and output constraints.
- Evaluate plan quality, parameter quality, artifact completeness, and final report faithfulness.
- Record model/provider/cost/runtime metadata for each run.

### Phase 5 - Advanced Agent Backends

- Add per-agent model routing.
- Connect Scientist to literature and domain knowledge retrieval.
- Connect Engineer to Claude Code CLI or another coding backend for complex repo-level tasks.
- Expose selected tools through MCP where it improves interoperability.

## Immediate Implementation Scope

The first implementation should be deliberately small:

```text
ExpertsRS/runtime/
  __init__.py
  state.py
  artifacts.py
  tool_runtime.py
  workflow.py

ExpertsRS/test_runtime.py
```

Success criteria:

- existing `ExpertsRS/test_tools.py` still passes
- new runtime test passes
- no notebook behavior changes
- one runtime run can produce a manifest and tool trace

