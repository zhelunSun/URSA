# Agent handoff: unified-runtime checkpoint

## Current execution authority

Read `PLAN.md` first.  It freezes the remaining work into
WP1--WP5 task packets and distinguishes the current offline method baseline from
the later live-model evidence gate.  A workhorse chat must take exactly one
packet; it must not redesign the thesis claim, comparison conditions, or
legacy/new-system boundary.

## Safe starting point

- Canonical branch: `codex/ch1-v2-e1-structured-planning`.
- The old `codex/ch1-unified-runtime` and `codex/ch1-baseline-20260811`
  relationship is historical provenance, not the current execution entry.
  Protected notebook and v0.5.3 closeout milestones remain unchanged.
- New-system authority: `ExpertsRSSystem.run()` / `.resume()` and
  `python -m ExpertsRS` from repository root.
- Historical notebook: `ExpertsRS/ExpertsRS_notebook.ipynb`; keep it intact.
  It remains an AG2-era lightweight reproduction surface, using
  `ExpertsRS/legacy_requirements.txt`, and must not become an import dependency
  of the new package.

## Working rules

1. Do not add a second runner, scheduler, trace format, or model connector to
   the main path. Extend `RunRequest`, `ExpertsRSSystem`, and the existing
   executor boundary instead.
2. Runtime state is canonical. AutoGen Team state may be saved in
   `state.json` as a resumability supplement but must not duplicate permission,
   plan, artifact, or checkpoint facts.
3. Every model-facing view must omit absolute paths, raster content, keys,
   environment data, evaluator contracts, fixtures, gold and scores.
4. Put evaluator-only logic under `ExpertsRS/evaluation/`; it must inspect
   traces/results, not advance roles or actions.
5. Preserve immutable run directories: never overwrite an existing `run_id`.

## Required checks before a handoff

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q ExpertsRS
.\.venv\Scripts\python.exe ExpertsRS\run_m1_closeout.py
.\.venv\Scripts\python.exe ExpertsRS\run_d2_closeout.py
git lfs fsck --objects
git diff --check
```

Read `UNIFIED_RUNTIME_REVIEW_PACKET.md` before proposing an architectural
change.  Live model/API work is explicitly out of scope until the researcher
opens the documented approval gate.

The 2026-08-13 verified test baseline is 75 passing tests.  Do not repeat the
older 43-test figure from narrative material without refreshing its upstream
evidence surfaces.

For Chapter 2/3 integration, read `PLAN.md` section 10.  Provider repositories
own their schemas and scientific/evaluation semantics; URSA owns only the
runtime ports and portable trial export.  Cross-chapter port work must stay on
a separate branch until the Chapter 1 live 5x3 experiment commit is frozen.
