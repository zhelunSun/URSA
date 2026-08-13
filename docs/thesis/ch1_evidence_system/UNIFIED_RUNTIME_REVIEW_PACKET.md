# ExpertsRS unified-runtime review packet

## Review purpose

This packet defines the 2026-08-13 offline engineering checkpoint for an
independent architecture review.  It deliberately separates verified facts,
historical compatibility, and open live-model claims.

## Authority map

```text
User / CLI / Python caller
        │ RunRequest
        ▼
ExpertsRSSystem.run / resume                    ← only public execution entry
        │ redacted decision view
        ▼
AutoGen SelectorGroupChat (Manager / Scientist / Engineer)
        │ structured role decision
        ▼
Runtime: budgets, plans, permissions, checkpoints, traces
        │ approved action only
        ▼
LocalToolExecutor → registered deterministic tools → per-run artifacts
        │
        └── RunResult + state.json + trace.jsonl + result.json + report.md
```

The AutoGen Team is only the model-facing conversation/state owner.  It cannot
grant a permission, select a filesystem path, create a checkpoint, or turn an
invalid action into execution.  Those are runtime decisions recorded in the
trace.  The runtime is the sole source of truth for domain state; the Team
state is saved only as a resumable framework-session supplement.

## Code map

| Concern | Authoritative files | Explicit non-authority |
| --- | --- | --- |
| Public API and CLI | `ExpertsRS/__init__.py`, `models.py`, `system.py`, `__main__.py` | notebook, `react_demo.py` |
| AgentChat boundary | `ExpertsRS/decisions.py` | AG2 StateFlow/ReAct code |
| Tools and scientific constraints | `ExpertsRS/tools/`, `ExpertsRS/workflow/` | evaluator-specific tool executor |
| D3 evaluation | `ExpertsRS/evaluation/ch1/` | user-facing entry points |
| Historical reproduction | `ExpertsRS_notebook.ipynb`, `react_demo.py`, `react_orchestration.py` | unified runtime imports |

## Verified offline claims

- A local request can return report, raster/map artifacts, trace and stable
  `RunResult` via the same Python API and CLI implementation.
- A clarification pauses the same run and resumes with the same identifier.
- Runtime checks permissions before tool execution, prevents output overwrite,
  records plan versions/checkpoints, and redacts local paths from model-facing
  observations and trace action arguments.
- A scripted modern AutoGen `SelectorGroupChat` executes named role decisions
  and its portable Team state is persisted by the runtime.
- All five D3 tasks × B1/B2/B3 conditions execute through `ExpertsRSSystem` in
  the offline gate.  The external evaluator consumes only trace/result data;
  it supplies neither a role phase nor a next action to the system.

## Evidence commands

Run from repository root after installation:

```powershell
python -m unittest discover -s ExpertsRS -v
python -m ExpertsRS run --request "Map NDVI for Dongcheng" `
  --data ExpertsRS/data/Sentinel2_Dongcheng_20230718.tif `
  --output-dir .test_tmp/manual
```

Key test groups:

| Test class | Level | It proves | It does not prove |
| --- | --- | --- | --- |
| `test_system.UnifiedSystemTests` | system-offline | API-to-tool lifecycle, stop/recovery/resume | live model reasoning quality |
| `test_autogen_adapter.AutoGenAdapterTests` | integration | modern Team dispatch and saved state | provider reliability/cost |
| `test_d3_light_dry_run.D3LightDryRunTests` | evaluation | 15 offline runtime/evaluator contracts | a live treatment effect |
| scientific/workflow/tool tests | unit/integration | contracts and deterministic tool behavior | thematic accuracy of a new study |

## Review questions

1. Is `ExpertsRSSystem` genuinely the only accepted input-to-output path for
   new work, or is any legacy path still treated as production?
2. Are role/team state and runtime state sufficiently separated, with no
   sensitive local context crossing the model boundary?
3. Does the D3 evaluator read evidence rather than prescribe the trajectory?
4. Are the frozen historical notebook and its AG2 dependencies sufficiently
   isolated to remain reproducible without contaminating the modern runtime?
5. Is the documented next gate—real-model smoke under an approved disclosure
   boundary—clear enough to prevent overclaiming offline evidence?

## Non-claims and next gate

This checkpoint does not claim live-model quality, model cost, scientific
thematic accuracy, or D3 treatment effects.  Before any such claim: install in
a clean environment, freeze provider/model/prompt hashes and budgets, review
the limited external disclosure boundary, then run exactly three live smokes
(NDVI, injected recovery, clarification) through the same public API.
