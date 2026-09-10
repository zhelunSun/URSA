"""Reserved Chapter 2 JSON boundary; no knowledge implementation or scheduler."""
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceReference(Contract):
    evidence_id: str = Field(min_length=1)
    kind: Literal["computed_product", "knowledge_source"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class KnowledgeRequest(Contract):
    schema_version: Literal["ch3-knowledge-port-v1"] = "ch3-knowledge-port-v1"
    request_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    evidence: tuple[EvidenceReference, ...] = ()
    max_model_calls: int = Field(default=0, ge=0)
    max_tool_calls: int = Field(default=0, ge=0)


class KnowledgeResponse(Contract):
    schema_version: Literal["ch3-knowledge-port-v1"] = "ch3-knowledge-port-v1"
    request_id: str = Field(min_length=1)
    status: Literal["available", "unavailable", "failed"]
    answer: str | None = None
    conditions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    source_run_id: str | None = None
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @model_validator(mode="after")
    def preserve_unavailability(self):
        if self.status == "available":
            if not self.answer or not self.evidence or not self.source_run_id or not self.conditions:
                raise ValueError("Available knowledge requires answer, provenance and applicability")
        elif self.answer is not None or self.evidence or not self.reason:
            raise ValueError("Unavailable/failed knowledge cannot carry a supported answer")
        return self


class KnowledgePort(Protocol):
    def query(self, request: KnowledgeRequest) -> KnowledgeResponse: ...


class UnavailableKnowledgePort:
    def query(self, request: KnowledgeRequest) -> KnowledgeResponse:
        return KnowledgeResponse(
            request_id=request.request_id, status="unavailable", total_tokens=0,
            reason="Chapter 2 knowledge service is not connected",
            limitations=("No knowledge-based method selection or ecological interpretation is available",),
        )


def validate_exchange(request: KnowledgeRequest, response: KnowledgeResponse) -> None:
    """Transport/provenance shape only; hashes and scientific entailment need external verification."""
    if response.request_id != request.request_id:
        raise ValueError("Knowledge response belongs to another request")
    if response.model_calls > request.max_model_calls or response.tool_calls > request.max_tool_calls:
        raise ValueError("Knowledge service exceeded its delegated call budget")

