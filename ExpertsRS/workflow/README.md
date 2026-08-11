# ExpertsRS Workflow Runtime

This package is a framework-independent harness layer added beside the published
AutoGen notebook. It makes the existing remote-sensing tool layer inspectable
before execution without altering the historical prototype.

```text
static baseline: TaskSpec -> WorkflowGraph -> validator -> repair/stop

adaptive path:  plan version -> permitted action -> real observation
                         -> revised plan/checkpoint -> process graph view
```

## Runtime contracts

- `TaskSpec`: goal, AOI/time, expected artifacts and validation needs.
- `OperatorSpec`: stable tool ID, typed inputs/outputs, preconditions, failure
  modes and default configuration. `adapters.py` contracts all 18 public tools.
- `WorkflowGraph`: explicit artifact/data dependencies instead of inferring state
  from chat history.
- `validate_workflow`: deterministic checks for unknown tools/artifacts, missing
  inputs, type mismatches, invalid order, file preconditions and missing outputs.
- `apply_targeted_repair`: adds a unique safe missing-output step, or records a
  correct stop when repair would be ambiguous.
- `WorkflowTrace`: JSON execution trajectory that records plan, validations,
  repair decisions and final artifacts. New events add stable IDs, order,
  responsibility and typed references without changing legacy payloads.
- `PlanVersion`: keeps the original and revised plans instead of overwriting
  history; a recovery plan can point to its triggering observation and restart
  checkpoint.
- `build_process_graph`: deterministically derives a compact process view from
  recorded facts. It is not an up-front execution script or graph database.
- `Checkpoint`: references validated artifacts and a logical resume position;
  it does not copy files or undo external effects.
- `LocalPermissionPolicy`: default-deny local boundary for the current 18 tools.
  It is an interface for the single Executor, not an enterprise IAM system.

## Run

From `ExpertsRS/`:

```powershell
python test_workflow.py
python test_adaptive_runtime.py
python workflow/run_pilot.py
python workflow/run_closeout.py
python run_d2_closeout.py
```

The pilot writes a trace to `results/workflow_trace_greenspace_pilot.json`.
It validates a Sentinel-2 greenspace plan and repairs its intentionally omitted
thresholding step; it does not call an external LLM or overwrite the notebook.

`run_closeout.py` is the M1 evidence runner. It writes a successful targeted-
repair trace and an expected controlled-stop trace under
`results/ch1_m1_closeout/`. For the complete no-API regression, real-tool pilot,
and both traces, run `python run_m1_closeout.py` from `ExpertsRS/`.

`run_d2_closeout.py` runs the bounded D2 package: focused interface tests plus
one real-tool, no-API fault fixture. The fixture deliberately requests missing
band `B99`, records the tool failure, restarts from the verified-metadata
checkpoint, succeeds with semantic `B8/B4`, and denies one output outside
`results/`. Evidence is written under `results/ch1_d2_closeout/`. It tests the
Chapter 1 mechanism only; it is not a thematic-accuracy or live-LLM experiment.
