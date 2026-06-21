# Ch1 Modernization Plan - From Prototype Workflow to RS Agent Runtime

> Status: Phase 1-6 foundation interfaces implemented; next checkpoint is autonomous-development control, evidence memory, benchmark cards, and MCP/backend adapters
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
- OpenEarth-Agent: adaptive data probing, workflow DAG construction, tool creation, and geoscience checking loops for open-environment EO.
- AI Scientist-style systems: experiment loops, reviewers, and evaluation around complete research cycles.
- OpenHands SDK-style engineering agents: event-sourced state, modular tool/workspace packages, sandbox/lifecycle control, and model routing.

The lesson for Ch1 is: do not merely add more agents. Make domain constraints, tools, evidence, and provenance first-class citizens.

## External Agent Scan - Calibration

The agent survey changes the priority order, but not the core architecture. The formal Ch1 system should not become a clone of Earth-Agent, OpenEarth-Agent, EurekAgent, AI Scientist, OpenHands, LangGraph, or MCP. It should use their strongest lessons to make the URSA thesis claim sharper.

### Primary references

| Reference | What to learn | What not to copy directly | Priority for URSA Runtime |
|---|---|---|---|
| Earth-Agent / Earth-Bench | EO agents need spectral/RGB/product awareness, domain tool ecosystems, and dual evaluation of tool trajectory plus final output. | Do not try to rebuild a 248-task benchmark immediately. Use it as evaluation grammar. | High: informs task cards, trajectory checks, and MCP interoperability. |
| OpenEarth-Agent / OpenEarth-Bench | Open EO requires data probing, adaptive workflow planning, DAG-style tool creation, and checking against geoscience rules. | Do not jump from 18 tools to massive open-ended tool creation before the closed-loop runtime is reliable. | High later: make data profiling and checker-driven repair a Phase 7/8 path. |
| EurekAgent | The environment is the agent product: permissions, artifacts, budget, human intervention, and isolated evaluation matter as much as prompts. | Do not overfit to metric-search scientific discovery. URSA tasks are geospatial workflows, not only scalar optimization. | Highest: drives the next control-plane checkpoint. |
| OpenHands SDK | Production agents need modular packages, event-sourced state, one mutable state source, sandbox/workspace abstraction, lifecycle control, and multi-provider routing. | Do not import a software-engineering agent wholesale as the RS runtime. | Highest for engineering hardening and long-running autonomous development. |
| AI Scientist / AI Scientist v2 | A credible research agent records idea-code-experiment-analysis-review loops and treats review as a first-class stage. | Do not promise automatic paper generation or autonomous scientific novelty for Ch1. | Medium: borrow experiment/reviewer structure for reports and evaluation. |
| LangGraph | Durable, stateful, human-in-the-loop graph orchestration is a good runtime adapter. | Do not make LangGraph the source of truth for RS state or artifacts. | Medium: adapter after core runtime and evaluator remain stable. |
| MCP | Standard tool/data interface improves interoperability across Claude Code, ChatGPT, IDEs, and future agents. | Do not expose tools through MCP before local contracts, permissions, and provenance are stable. | Medium-high: add as adapter, not foundation. |

### First-principles design rules

1. The unit of contribution is the remote-sensing task environment, not the chat transcript.
2. Every important action must become structured state: request, data, plan, tool call, artifact, evidence, error, checkpoint, evaluation, and cost.
3. The runtime must be able to answer five audit questions from `run_manifest.json`: what did the user ask, what data was used, what tools ran, where are the artifacts, and why did the verifier pass or fail.
4. Domain memory must be reviewable evidence, not free-floating conversation memory.
5. Open-ended tool creation is a future layer. The current foundation must first master deterministic closed-loop execution and evaluation.
6. Orchestration frameworks and agent backends are replaceable adapters. The RS runtime, contracts, artifact store, evidence store, and evaluator are the stable center.

### Recalibrated upgrade priority

1. P0 - Execution control plane for long-running autonomous development.
   - Fix the automation gap exposed by `VALIDATION-REPORT.md`: a plan file and script are not enough unless scheduling, environment, logs, and post-run validation are closed.
   - Standardize executable validation commands around script tests first: `python ExpertsRS/test_runtime.py`, `python ExpertsRS/test_tools.py`, and `python -m compileall -q ExpertsRS/runtime ExpertsRS/test_runtime.py`.
   - Track agent-produced run reports as ignored operational artifacts unless they are promoted into formal docs.

2. P1 - Evidence memory and benchmark inventory.
   - Add file-backed method cards, dataset cards, benchmark cards, and citation records.
   - Include the thesis-side 20-dataset benchmark only after the materials are located and converted into reviewed task cards.
   - Keep review status explicit: `system_generated`, `evidence_backed`, `expert_reviewed`, or `paper_reproduction`.

3. P2 - Data profiling and RS task expansion.
   - Make `discover data -> read metadata` a stronger first stage for every template.
   - Add water extraction, LST, burn mapping, and zonal statistics as deterministic templates before LLM-driven adaptive planning.
   - Add geoscience checks such as nodata ratio, CRS/resolution consistency, valid index range, empty-output detection, and map/report completeness.

4. P3 - MCP and backend adapters.
   - Expose selected runtime-safe tools through MCP only after contracts and provenance are attached.
   - Add Claude Code CLI as an optional Engineer backend that writes code or patches, but route all data products and validations back through the runtime manifest.
   - Keep model/provider/cost/latency routing in backend provenance.

5. P4 - Open-environment research agent layer.
   - Add adaptive data probing, plan aggregation, workflow DAG generation, code/tool creation, and checker-driven repair.
   - Treat generated tools as artifacts with contracts, tests, provenance, and review status before they become reusable tools.

### Sources reviewed

- Earth-Agent / Earth-Bench: https://arxiv.org/abs/2509.23141
- OpenEarth-Agent / OpenEarth-Bench: https://arxiv.org/abs/2603.22148
- OpenEarthAgent unified geospatial agents: https://arxiv.org/abs/2602.17665
- EurekAgent: https://arxiv.org/abs/2606.13662
- OpenHands SDK: https://arxiv.org/abs/2511.03690 and https://github.com/OpenHands/OpenHands
- AI Scientist: https://arxiv.org/abs/2408.06292 and https://github.com/SakanaAI/AI-Scientist
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- Model Context Protocol: https://modelcontextprotocol.io/docs/getting-started/intro

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

Status: implemented in `Add runtime foundation for ExpertsRS`.

### Phase 2 - Typed RS Tool Contracts

- Enrich tool metadata with units, CRS expectations, nodata handling, band semantics, and output artifact classes.
- Make tool outputs easier to validate automatically.
- Add task templates for common RS workflows such as vegetation mapping, water extraction, LST, burn mapping, and zonal statistics.

Status: implemented as a framework-neutral contract registry for the existing 18 tools. Next work is to enrich the contracts with stronger geospatial validation rules and use them in evaluator checks.

### Phase 3 - Evaluation Harness

- Build curated benchmark tasks with expected tool trajectories and output constraints.
- Evaluate plan quality, parameter quality, artifact completeness, and final report faithfulness.
- Record model/provider/cost/runtime metadata for each run.
- Keep the scope as a lightweight evaluation harness, not a new heavy benchmark paper.
- Add a benchmark inventory pass that collects existing remote-sensing agent benchmarks and the thesis-side 20-dataset benchmark materials before creating new tasks.
- Represent each benchmark candidate as a task card: user goal, domain, dataset/source, expected data choice, expected method/tool sequence, artifact requirements, grading rubric, and review status.

Status: deterministic evaluator implemented. Curated benchmark expansion remains future work and should start with a benchmark inventory, not new synthetic tasks.

### Phase 4 - Minimal RS Task Templates

- Build deterministic templates that prove the runtime can complete full remote-sensing tasks without LLM orchestration.
- Start with `vegetation_mapping_ndvi_threshold`.
- Expand later to water extraction, LST, burn mapping, and zonal statistics.
- Generate templates from three sources, in priority order: existing thesis tasks and datasets, accepted remote-sensing domain methods, and expert-reviewed synthetic task cards.
- Mark every template with `review_status`: `system_generated`, `evidence_backed`, `expert_reviewed`, or `paper_reproduction`.
- Do not treat unreviewed generated templates as thesis evidence; use them only for engineering smoke tests.

Status: first vegetation mapping template implemented. Next templates should be water extraction, LST, burn mapping, and zonal statistics, each with explicit review status.

### Phase 5 - Orchestration Upgrade

- Add a framework-neutral node orchestrator first.
- Convert Manager/Scientist/Engineer/Verifier/Reporter into graph nodes over `RunState`.
- Keep LangGraph as an optional adapter, not a hard runtime dependency.
- Keep AutoGen notebook as historical reference, not the active architecture.

Status: framework-neutral orchestrator implemented; concrete LangGraph durable execution remains future work.

### Phase 6 - Advanced Agent Backends

- Add per-agent model routing.
- Connect Scientist to literature and domain knowledge retrieval.
- Connect Engineer to Claude Code CLI or another coding backend for complex repo-level tasks.
- Expose selected tools through MCP where it improves interoperability.
- Add a file-backed evidence memory before live retrieval: method cards, dataset cards, benchmark cards, and citation records.
- Require every retrieved or generated knowledge item to enter `RunState.evidence` and `run_manifest.json`.
- Human review is required before evidence memory is used as thesis evidence, but not before using it as engineering context.

Status: provenance interfaces for backend calls, role routing, and evidence/citations implemented. Next work is file-backed evidence memory, benchmark cards, and then live providers/MCP/Claude Code CLI adapters.

## Evaluation Strategy

Evaluation is broader than a benchmark. The runtime should support three levels:

1. Engineering checks: unit/smoke tests for tools, contracts, manifests, and evaluator behavior.
2. Process evaluation: whether the workflow chooses reasonable data, methods, tools, parameters, artifacts, and limitations.
3. Benchmark/task-set evaluation: a curated set of task cards, including the thesis-side 20-dataset benchmark if the materials are available and reviewable.

The minimum dissertation-safe claim is process-level improvement: executability, traceability, evidence discipline, and verification quality. The project should avoid claiming a new general remote-sensing benchmark unless the task set is explicitly curated, documented, and reviewed.

## Autonomous Development Control

The validation report from the external agent run exposed an execution-chain problem: `PLAN.md`, `prompt.md`, and `auto-dev.ps1` existed, but the task was never registered with the scheduler, so the agent process did not start. This should be treated as a planning lesson for long-running autonomous development.

Before another long unattended run, the repository should have:

- a local preflight command that checks branch, Python executable, dependency availability, writable run directory, and expected validation commands
- a canonical validation command list that matches the current script-style tests:
  - `python ExpertsRS/test_runtime.py`
  - `python ExpertsRS/test_tools.py`
  - `python -m compileall -q ExpertsRS/runtime ExpertsRS/test_runtime.py`
- a heartbeat/log artifact for every autonomous run, for example `.ccp-running` plus `ccp-execution-YYYY-MM-DD.log`
- a post-run validator that checks whether a process actually launched, whether commits were created, and whether ignored operational reports should be promoted into tracked docs
- an explicit rule that generated planning files stay ignored unless their content is deliberately merged into `MODERNIZATION.md` or a formal design document

This control plane is now higher priority than adding another orchestration library. It reduces drift, makes overnight work auditable, and protects the thesis direction from accidental automation failures.

## Naming and Repository Strategy

Keep `ExpertsRS` as the archived prototype name for the paper reproduction window. Use a clearer formal system name for the runtime layer, for example:

- `URSA Runtime`: preferred for repository and portfolio continuity.
- `URSA-Agent`: good if the public identity should foreground the agent system.
- `ExpertsRS Runtime`: acceptable for backward compatibility, but it sounds more like a prototype extension than a dissertation-grade system.

Recommendation: keep the repository name `URSA`, keep `ExpertsRS/` for backward compatibility, and present the upgraded system publicly as `URSA Runtime: a verifiable remote-sensing agent workflow runtime`.

## Next Implementation Scope

```text
ExpertsRS/runtime/
  memory.py              # file-backed evidence, method, dataset, and benchmark cards
  benchmark_cards.py     # task-card schema and review-status gate
  preflight.py           # branch/env/test-command checks for unattended runs

ExpertsRS/tasks/
  water_extraction.py
  lst_mapping.py
  burn_mapping.py
  zonal_statistics.py

ExpertsRS/mcp_server/     # adapter only after contracts/provenance remain attached
```

Success criteria:

- `ExpertsRS_notebook.ipynb` remains untouched as the prototype archive
- `run_manifest.json` records request, data, tool trace, artifacts, evidence, backend provenance, and verifier result
- every new task card has `review_status` and source/evidence fields
- every autonomous run leaves a heartbeat/log and passes the canonical script tests
- MCP and Claude Code CLI never bypass `ToolRuntime`, artifact records, or evaluator checks
