"""Optional LangGraph adapter surface for ExpertsRS runtime orchestration."""

from __future__ import annotations

from .orchestration import RuntimeOrchestrator


def describe_langgraph_adapter(orchestrator: RuntimeOrchestrator) -> dict:
    """Return a serializable graph description without requiring LangGraph."""
    return {
        "start_node": orchestrator.start_node,
        "nodes": sorted(orchestrator.nodes),
        "runtime_state": "RunState",
        "note": "Install langgraph and wrap these node handlers when enabling durable graph execution.",
    }


def require_langgraph():
    try:
        import langgraph  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("LangGraph is optional. Install langgraph to enable a concrete graph adapter.") from exc
    return True
