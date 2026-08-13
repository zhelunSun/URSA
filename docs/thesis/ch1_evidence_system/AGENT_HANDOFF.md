# Agent handoff: unified-runtime checkpoint

## Safe starting point

- Branch: `codex/ch1-unified-runtime`.
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
