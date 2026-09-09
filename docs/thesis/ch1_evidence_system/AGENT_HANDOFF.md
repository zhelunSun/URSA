# Agent handoff: unified-runtime checkpoint

## Current execution authority

Read the dated current-status overlay in `PLAN.md` first, then
`audits/20260909_repository_system_check.md`. The old WP1--WP5 packets are
historical; do not redispatch completed v2 work. The canonical writable checkout
is `D:/Projects/phd-thesis/URSA`; the `phd-research` checkout is recovery-only.
Use the control plane's current execution plan for chapter roles and scheduling.
Do not redesign the thesis claim, comparison conditions, or legacy/new-system boundary.

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

The 2026-09-09 canonical-checkout regression passed 121 tests. The older 75/43
counts describe historical checkpoints. M1, D2 and the offline NDVI CLI also
passed; no live model was called. Historical v0.5.3 live results remain frozen,
but their indexed raw run packages were absent from both inspected checkouts.
Recover and hash-check them before claiming present-day raw-evidence verification.

For Chapter 2/3 integration, read `PLAN.md` section 10.  Provider repositories
own their schemas and scientific/evaluation semantics; URSA owns only the
runtime ports and portable trial export.  Cross-chapter port work must stay on
a separate branch until the Chapter 1 live 5x3 experiment commit is frozen.
