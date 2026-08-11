"""Refresh machine-verifiable facts used by the Chapter 1 writing materials."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = Path("ExpertsRS/ExpertsRS_notebook.ipynb")
EARLIEST_NOTEBOOK_REF = "19db55bf2a819e8b07722233330d1b541bd3f764"
PUBLISHED_STYLE_NOTEBOOK_REF = "878e84b4fa7098df837aa92101ca595e11fb3f73"
RUNTIME_BRANCH = "origin/codex/ch1-runtime-foundation"


def git(*args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return completed.stdout.strip()


def git_object_json(ref: str, path: Path) -> dict:
    return json.loads(git("show", f"{ref}:{path.as_posix()}"))


def python_surface(path: Path) -> tuple[int, int]:
    files = sorted(path.rglob("*.py")) if path.exists() else []
    lines = sum(len(file.read_text(encoding="utf-8").splitlines()) for file in files)
    return len(files), lines


def function_defaults(path: Path, function_name: str) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            names = [argument.arg for argument in node.args.args]
            values = [ast.literal_eval(default) for default in node.args.defaults]
            return dict(zip(names[-len(values):], values))
    return {}


def raster_band_snapshot() -> tuple[list[str], str]:
    try:
        import rasterio
    except ImportError:
        return [], "rasterio unavailable; semantic band check not run"

    raster = REPO / "ExpertsRS/data/Sentinel2_Dongcheng_20230718.tif"
    with rasterio.open(raster) as source:
        descriptions = [item or "<missing>" for item in source.descriptions]

    defaults = function_defaults(REPO / "ExpertsRS/tools/index_kit.py", "calculate_ndvi")
    def resolve(reference: object) -> tuple[int | None, str]:
        if isinstance(reference, str) and not reference.isdigit():
            matches = [index for index, label in enumerate(descriptions, start=1) if label == reference]
            return (matches[0], reference) if len(matches) == 1 else (None, "<unresolved>")
        try:
            position = int(reference)
        except (TypeError, ValueError):
            return None, "<invalid>"
        label = descriptions[position - 1] if 0 < position <= len(descriptions) else "<out-of-range>"
        return position, label

    nir_reference = defaults.get("nir_band")
    red_reference = defaults.get("red_band")
    nir_position, nir_label = resolve(nir_reference)
    red_position, red_label = resolve(red_reference)
    verdict = (
        f"calculate_ndvi defaults {nir_reference!r}/{red_reference!r} resolve by exact "
        f"band descriptions to stack positions {nir_position}/{red_position} "
        f"({nir_label}/{red_label})"
    )
    if (nir_label, red_label) != ("B8", "B4"):
        verdict += "; SEMANTIC MISMATCH"
    return descriptions, verdict


def code_block(value: str) -> str:
    return value if value else "<clean>"


def build_snapshot() -> str:
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current") or "<detached>"
    status = git("status", "--short")
    current_hash = git("hash-object", NOTEBOOK.as_posix())
    head_hash = git("rev-parse", f"HEAD:{NOTEBOOK.as_posix()}")
    original_hash = git("rev-parse", f"{EARLIEST_NOTEBOOK_REF}:{NOTEBOOK.as_posix()}")
    published_style_hash = git("rev-parse", f"{PUBLISHED_STYLE_NOTEBOOK_REF}:{NOTEBOOK.as_posix()}")
    current_nb = json.loads((REPO / NOTEBOOK).read_text(encoding="utf-8"))
    original_nb = git_object_json(EARLIEST_NOTEBOOK_REF, NOTEBOOK)
    runtime_exists = bool(git("show-ref", "--verify", f"refs/remotes/{RUNTIME_BRANCH}", check=False))
    runtime_commits = git("rev-list", "--count", f"main..{RUNTIME_BRANCH}") if runtime_exists else "0"

    tool_files, tool_lines = python_surface(REPO / "ExpertsRS/tools")
    workflow_files, workflow_lines = python_surface(REPO / "ExpertsRS/workflow")
    react_files = [
        REPO / "ExpertsRS/react_orchestration.py",
        REPO / "ExpertsRS/react_demo.py",
        REPO / "ExpertsRS/run_react_pilot.py",
        REPO / "ExpertsRS/run_m1_closeout.py",
        REPO / "ExpertsRS/run_d2_closeout.py",
    ]
    existing_react = [path for path in react_files if path.exists()]
    react_lines = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in existing_react)
    descriptions, band_verdict = raster_band_snapshot()

    results = REPO / "ExpertsRS/results"
    latest_trace = max(results.glob("react_pilot_*.json"), key=lambda path: path.stat().st_mtime, default=None)
    closeout = results / "ch1_m1_closeout"
    d2_closeout = results / "ch1_d2_closeout"

    return f"""# Chapter 1 Current Repository Snapshot

> Generated by `python scripts/ch1_materials_snapshot.py` at {datetime.now().astimezone().isoformat(timespec='seconds')}.
>
> This file records machine-verifiable repository facts. It does not promote a scientific claim.

## Source state

- branch: `{branch}`
- HEAD: `{head}`
- working tree:

```text
{code_block(status)}
```

## Notebook preservation

- live path: `{NOTEBOOK.as_posix()}`
- working-tree object: `{current_hash}`
- HEAD object: `{head_hash}`
- unchanged relative to HEAD: `{str(current_hash == head_hash).lower()}`
- current notebook cells: `{len(current_nb['cells'])}`
- earliest 2025 notebook ref: `{EARLIEST_NOTEBOOK_REF}`
- original notebook object: `{original_hash}`
- original notebook cells: `{len(original_nb['cells'])}`
- May 2025 renamed/published-style object: `{published_style_hash}` at `{PUBLISHED_STYLE_NOTEBOOK_REF}`
- exact-original/current equality: `{str(current_hash == original_hash).lower()}`

Interpretation must therefore distinguish “the current published-style notebook
was not touched by the M1 sidecar upgrade” from “the notebook was never changed.”

## Upgrade surfaces

| Surface | Python files | Lines | Repository state |
| --- | ---: | ---: | --- |
| standardized tools | {tool_files} | {tool_lines} | tracked on `main` |
| typed workflow | {workflow_files} | {workflow_lines} | inspect `git status` above |
| ReAct/closeout entry points | {len(existing_react)} | {react_lines} | inspect `git status` above |
| broad runtime exploration | branch | {runtime_commits} commits ahead of `main` | `{RUNTIME_BRANCH}`; not merged |

## Dataset semantic check

- raster stack descriptions: `{', '.join(descriptions) if descriptions else '<not read>'}`
- current tool-default resolution: **{band_verdict}**

This check is intentionally factual: rasterio band positions and Sentinel-2
physical band identifiers are not interchangeable when the stack omits bands.

## Generated evidence presence

- latest ReAct pilot trace: `{latest_trace.relative_to(REPO).as_posix() if latest_trace else '<missing>'}`
- repair trace exists: `{str((closeout / 'repair_trace.json').exists()).lower()}`
- controlled-stop trace exists: `{str((closeout / 'controlled_stop_trace.json').exists()).lower()}`
- D2 adaptive trace exists: `{str((d2_closeout / 'adaptive_recovery_trace.json').exists()).lower()}`
- D2 process graph exists: `{str((d2_closeout / 'adaptive_process_graph.json').exists()).lower()}`
- D2 readable summary exists: `{str((d2_closeout / 'adaptive_pilot_summary.json').exists()).lower()}`

Generated `results/` are ignored by Git. A writing claim must therefore cite a
tracked readable manifest or a deliberately archived experiment package, not
only a timestamped local result.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "docs/thesis/ch1_evidence_system/snapshots/current_repository_snapshot.md",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_snapshot(), encoding="utf-8")
    print(f"Chapter 1 snapshot written to: {output}")


if __name__ == "__main__":
    main()
