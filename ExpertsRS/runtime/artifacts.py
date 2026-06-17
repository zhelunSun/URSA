"""Run artifact storage for ExpertsRS runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import RunState


class RunArtifactStore:
    """Create and update a per-run artifact directory.

    The store records state snapshots and manifests. Heavy raster/map outputs can
    remain where tools write them, while the manifest keeps stable references.
    """

    def __init__(self, base_dir: str | Path | None = None, run_id: str | None = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[1] / "results" / "runs"
        self.base_dir = Path(base_dir)
        self.run_id = run_id
        self.run_dir: Path | None = None

    def bind(self, state: RunState) -> Path:
        if self.run_id is None:
            self.run_id = state.run_id
        self.run_dir = self.base_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def path(self, name: str) -> Path:
        if self.run_dir is None:
            raise RuntimeError("Artifact store is not bound to a RunState")
        return self.run_dir / name

    def write_state(self, state: RunState, name: str = "state.json") -> Path:
        self.bind(state)
        target = self.path(name)
        state.save(target)
        return target

    def write_manifest(self, state: RunState, extra: dict[str, Any] | None = None) -> Path:
        self.bind(state)
        payload = {
            "version": 1,
            "run_id": state.run_id,
            "phase": state.phase,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "user_request": state.user_request,
            "structured_request": state.structured_request,
            "selected_data": state.selected_data,
            "method_plan": state.method_plan,
            "assumptions": state.assumptions,
            "tool_calls": [item.__dict__ for item in state.tool_calls],
            "artifacts": [item.__dict__ for item in state.artifacts],
            "checkpoints": [item.__dict__ for item in state.checkpoints],
            "decisions": state.decisions,
            "errors": state.errors,
            "metrics": state.metrics,
            "extra": extra or {},
        }
        target = self.path("run_manifest.json")
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def write_text_artifact(
        self,
        state: RunState,
        name: str,
        content: str,
        kind: str = "text",
        label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        self.bind(state)
        target = self.path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        state.add_artifact(kind=kind, path=str(target), label=label, metadata=metadata)
        self.write_manifest(state)
        return target
