# ExpertsRS system-convergence audit — 2026-08-13

## Executive finding

Before this change, the repository contained valid but parallel assets: the
published AG2 notebook/reaction demo, a framework-independent workflow
harness, and a D3-light evaluator that selected its own role phases.  Passing
their focused tests did **not** establish a complete agent system.

The authoritative research path is now `ExpertsRSSystem.run()` / `.resume()`
and `python -m ExpertsRS`.  It owns user input, clarification, plan versions,
permission decisions, tool execution, artifacts, checkpoints, traces and final
reporting.  The legacy notebook and AG2 files remain historical reproduction
assets and are deliberately not imported by the new package.

## Capability-to-evidence matrix

| User capability | Authority | Runtime boundary | Evidence |
| --- | --- | --- | --- |
| Submit a local raster analysis request | `RunRequest` / CLI `run` | Pydantic request + allowed roots | `ExpertsRS.test_system.test_ndvi_returns_report_artifacts_and_a_redacted_trace` |
| Ask an underspecified question and continue | `ExpertsRSSystem.resume` | persisted `state.json`, same run ID | `test_clarification_can_resume_the_same_run` |
| Make an NDVI map | Engineer action → `LocalToolExecutor` | registry + local permission policy + isolated output folder | `test_ndvi_returns_report_artifacts_and_a_redacted_trace` |
| Recover from a local write failure | revised `PlanVersion` | checkpoint references valid NDVI artifact | `test_recovery_reuses_ndvi_checkpoint_without_recomputing` |
| Reject unsupported/invalid science | Scientist stop | catalog/precondition boundary | `test_unsupported_and_scientifically_invalid_requests_stop` and scientific-precondition tests |
| Reject file-system escape | runtime permission gate | `LocalPermissionPolicy` before tool call | `test_data_outside_the_allowed_root_is_denied_without_tool_side_effects` |
| Inspect/reproduce a result | run directory | immutable `state.json`, `trace.jsonl`, `result.json`, artifacts | system tests plus `WorkflowTrace` tests |

## Asset classification

| Classification | Assets | Rule |
| --- | --- | --- |
| Main runtime | `ExpertsRS/__init__.py`, `models.py`, `system.py`, `decisions.py`, `__main__.py`, `tools/`, `workflow/` | New user-facing work must enter only through `run`/`resume`. |
| Historical reproduction | `ExpertsRS_notebook.ipynb`, `react_demo.py`, `react_orchestration.py`, `run_react_pilot.py`, `prompts.py` | Use only with `legacy_requirements.txt`; no main-runtime imports. |
| Evaluation-only | `ExpertsRS/evaluation/ch1/` | It assesses the main runtime; it may not predefine agent phases or be used as the interactive entry point. |
| Obsolete/duplicate main-path concepts | AG2 selector/executor wiring and the direct D3 model connector | Retained for provenance while live D3 remains gated; not part of main execution. |

## Findings and priority

- **P0 resolved:** `test_tools.py` no longer calls `sys.exit()` during discovery.
- **P0 resolved:** outputs are run- and action-scoped; existing run IDs cannot
  overwrite prior outputs.
- **P0 resolved:** local read/write authorization is evaluated before execution.
- **P1 resolved:** plan/recovery/trace state is one runtime-owned source of truth.
- **P1 remaining:** a configured modern AutoGen model client must be exercised
  behind `AutoGenSelectorDecisionProvider` before any live D3 authorization.
- **P2 remaining:** D3 evaluator migration should call `ExpertsRSSystem` for
  B1/B2/B3 after the model-adapter protocol is frozen; the former D3 runner is
  still a no-API historical preflight fixture.
- **P3 deferred by scope:** web API, multi-tenancy, distributed workers,
  enterprise IAM and automated data-download workflows.

## Evidence boundaries

Offline system tests demonstrate the integrated local runtime using scripted
role decisions and real raster tools.  They do not demonstrate live-model
quality, provider reliability, thematic accuracy beyond the existing tool
tests, or D3 treatment effects.  A live claim requires the separately reviewed
model provider, disclosure boundary, hashes, budget and smoke protocol.
