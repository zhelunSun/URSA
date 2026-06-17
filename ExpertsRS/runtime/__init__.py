"""Runtime foundation for the formal ExpertsRS agent system.

The original notebook remains the paper prototype. This package provides
framework-neutral state, tool, and artifact primitives for the upgraded system.
"""

from .state import (
    AgentRole,
    ArtifactRecord,
    HumanCheckpoint,
    RunState,
    ToolCallRecord,
    WorkflowPhase,
)
from .artifacts import RunArtifactStore
from .contracts import (
    ArtifactContract,
    ParameterContract,
    ToolContract,
    ValidationIssue,
    get_tool_contract,
    list_tool_contracts,
    validate_contract_registry,
)
from .evaluator import EvaluationResult, RuntimeEvaluator
from .tasks import vegetation_mapping_ndvi_threshold
from .tool_runtime import ToolRuntime
from .workflow import RuntimeWorkflow

__all__ = [
    "AgentRole",
    "ArtifactRecord",
    "ArtifactContract",
    "EvaluationResult",
    "HumanCheckpoint",
    "ParameterContract",
    "RunArtifactStore",
    "RunState",
    "RuntimeEvaluator",
    "RuntimeWorkflow",
    "ToolContract",
    "ToolCallRecord",
    "ToolRuntime",
    "ValidationIssue",
    "WorkflowPhase",
    "get_tool_contract",
    "list_tool_contracts",
    "validate_contract_registry",
    "vegetation_mapping_ndvi_threshold",
]
