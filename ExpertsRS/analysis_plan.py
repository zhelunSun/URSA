"""Versioned, path-free chapter boundary; no knowledge repository dependency."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_status: Literal["candidate", "needs-review", "verified"] = "candidate"


class AnalysisPlan(BaseModel):
    """Information requirements, not executable nodes or a scientific approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["analysis-plan-v1"] = "analysis-plan-v1"
    plan_id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    revision: str = Field(min_length=1)
    original_goal: str = Field(min_length=1, max_length=4000)
    execution_goal: str = Field(min_length=1, max_length=2000)
    aoi: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    required_deliverables: tuple[str, ...] = Field(min_length=1)
    conditions: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)
    deferred_requirements: tuple[str, ...] = ()
    sources: tuple[SourceIdentity, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.required_deliverables)) != len(self.required_deliverables):
            raise ValueError("Analysis plan deliverables must be unique")
        if len({s.source_id for s in self.sources}) != len(self.sources):
            raise ValueError("Analysis plan source IDs must be unique")
        return self

    def fingerprint(self) -> str:
        data = json.dumps(self.model_dump(mode="json"), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def admit_classification(self, request) -> None:
        """The initial adapter supports one explicitly bounded product slice."""
        if request.domain_profile != "classification-v1":
            raise ValueError("analysis-plan-v1 currently requires classification-v1")
        if set(self.required_deliverables) != {"class_composition", "classification_map"}:
            raise ValueError("Unsupported analysis-plan deliverables; no silent substitution")
        if self.year != request.product_year or self.execution_goal != request.request:
            raise ValueError("Run year/goal disagrees with frozen analysis plan")

    def validate_task(self, task: dict) -> None:
        if task["goal"] != self.execution_goal:
            raise ValueError("Workflow may not rewrite the frozen information goal")
        if not set(self.required_deliverables).issubset(task["requested_outputs"]):
            raise ValueError("Workflow omitted a frozen information requirement")
        if task.get("constraints", {}).get("year") != self.year:
            raise ValueError("Workflow year disagrees with frozen analysis plan")
