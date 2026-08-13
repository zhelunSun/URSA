# Agent handoff: unified-runtime checkpoint

## Current execution authority

Read `PLAN.md` first.  It freezes the remaining work into
W1--W5 task packets and distinguishes the current offline method baseline from
the later live-model evidence gate.  A workhorse chat must take exactly one
packet; it must not redesign the thesis claim, comparison conditions, or
legacy/new-system boundary.

## Safe starting point

- Branch: `codex/ch1-unified-runtime`.
- Branch relationship: it is two commits ahead of
  `codex/ch1-baseline-20260811` (`64bfbdc`); the baseline and historical
  notebook remain unchanged.
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
python -m unittest discover -s ExpertsRS -v
python -m compileall -q ExpertsRS
git diff --check
```

Read `UNIFIED_RUNTIME_REVIEW_PACKET.md` before proposing an architectural
change.  Live model/API work is explicitly out of scope until the researcher
opens the documented approval gate.

The 2026-08-13 verified test baseline is 75 passing tests.  Do not repeat the
older 43-test figure from narrative material without refreshing its upstream
evidence surfaces.
