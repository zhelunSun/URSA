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
from .backends import (
    AgentBackendConfig,
    BackendCallRecord,
    DEFAULT_BACKEND_PLAN,
    add_evidence,
    backend_plan_to_dict,
    finish_backend_call,
    start_backend_call,
)
from .evaluator import EvaluationResult, RuntimeEvaluator
from .langgraph_adapter import describe_langgraph_adapter, require_langgraph
from .orchestration import (
    NodeResult,
    RuntimeOrchestrator,
    build_vegetation_orchestrator,
)
from .tasks import vegetation_mapping_ndvi_threshold
from .tool_runtime import ToolRuntime
from .workflow import RuntimeWorkflow

__all__ = [
    "AgentRole",
    "AgentBackendConfig",
    "ArtifactRecord",
    "ArtifactContract",
    "BackendCallRecord",
    "DEFAULT_BACKEND_PLAN",
    "EvaluationResult",
    "HumanCheckpoint",
    "ParameterContract",
    "RunArtifactStore",
    "RunState",
    "RuntimeEvaluator",
    "RuntimeOrchestrator",
    "RuntimeWorkflow",
    "NodeResult",
    "ToolContract",
    "ToolCallRecord",
    "ToolRuntime",
    "ValidationIssue",
    "WorkflowPhase",
    "add_evidence",
    "backend_plan_to_dict",
    "finish_backend_call",
    "get_tool_contract",
    "list_tool_contracts",
    "describe_langgraph_adapter",
    "require_langgraph",
    "start_backend_call",
    "build_vegetation_orchestrator",
    "validate_contract_registry",
    "vegetation_mapping_ndvi_threshold",
]
