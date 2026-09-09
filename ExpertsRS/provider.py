"""Explicit, no-fallback provider construction for the unified runtime."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

from .decisions import AutoGenSelectorDecisionProvider
from .models import ProviderConfig


class ProviderFailure(RuntimeError):
    """Sanitized provider failure that is safe to persist in a trace."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def classify_provider_exception(error: Exception) -> ProviderFailure:
    """Convert transport/protocol failures to a stable, non-secret terminal cause."""
    if isinstance(error, TimeoutError):
        return ProviderFailure("provider_timeout", "The provider request timed out.")
    name = type(error).__name__.lower()
    if "timeout" in name:
        return ProviderFailure("provider_timeout", "The provider request timed out.")
    if "http" in name or "api" in name or "connection" in name:
        return ProviderFailure("provider_api_error", f"Provider request failed: {type(error).__name__}.")
    return ProviderFailure("provider_response_error", f"Provider response failed validation: {type(error).__name__}.")


def create_autogen_live_provider(config: ProviderConfig) -> AutoGenSelectorDecisionProvider:
    """Construct exactly the requested provider or fail before any request.

    Credentials remain in process environment only.  This factory never falls
    back to scripted execution, another model, or another endpoint.
    """
    api_key = os.getenv(config.api_key_env, "")
    base_url = os.getenv(config.base_url_env, "")
    if not api_key or api_key == "your-api-key":
        raise ProviderFailure("missing_api_key", f"No usable API key is set in {config.api_key_env}.")
    if not base_url:
        raise ProviderFailure("missing_base_url", f"No provider base URL is set in {config.base_url_env}.")
    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=config.model,
            api_key=api_key,
            base_url=base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
            temperature=config.temperature,
            top_p=config.top_p,
            max_tokens=config.max_completion_tokens,
            **({"extra_body": {"enable_thinking": config.enable_thinking}}
               if config.enable_thinking is not None else {}),
            model_info={
                "vision": False,
                "function_calling": False,
                "json_output": True,
                "family": "unknown",
                "structured_output": True,
            },
        )
        return AutoGenSelectorDecisionProvider.create(client, _role_instructions())
    except ProviderFailure:
        raise
    except Exception as error:
        raise ProviderFailure("provider_initialization_failed", type(error).__name__) from error


def redacted_provider_base_url(config: ProviderConfig) -> str:
    """Return only the stable endpoint identity that may enter a manifest."""
    raw = os.getenv(config.base_url_env, "")
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/..."
    return "configured_unparseable_endpoint" if raw else "not_configured"


def _role_instructions() -> dict[str, str]:
    """Only redacted runtime state and a typed decision schema reach the model."""
    return {
        "Manager": (
            "Return exactly one JSON object: either "
            '{"kind":"clarify","question":"..."} or '
            '{"kind":"handoff","target":"Scientist"}, or, when phase is report, '
            '{"kind":"report","summary":"...","artifact_refs":["artifact-id"],"deliverables":[...]}. '
            "If input_data_available is true, the local runtime already has the input; do not ask for a file path or upload. "
            "Clarify only when the requested analysis goal, metric, or output is semantically ambiguous. "
            "A request for vegetation health or health condition without a named metric (for example NDVI, green cover, or a physiological indicator) is semantically ambiguous and must receive one concise clarification question. "
            "A named index or operator (for example NDSI, NDVI, or LST) is specific enough to hand off to Scientist; do not ask the user to define it. "
            "Do not ask for sensor, bands, raster metadata, spatial coverage, or file format when input data is available; "
            "the Scientist and registered tools must inspect those technical preconditions. "
            "When phase is report, artifact_refs must contain every artifact_id listed in artifact_manifest exactly once; "
            "do not omit a validated artifact and do not invent an ID. "
            "When report_deliverables is supplied, copy every factual deliverable exactly: preserve its value, unit, scope, "
            "and artifact_refs.  In particular, never rename a valid-image-pixel percentage as an administrative-area rate. "
            "delivery_obligations are runtime-owned user obligations: do not omit, rename, downgrade, or add to them. "
            "Include it as the report JSON field deliverables. Every deliverable object must contain exactly "
            "deliverable_id, status, value, unit, scope, artifact_refs; copy status too. "
            "For phase report, the required shape is "
            "{\"kind\":\"report\",\"summary\":\"...\",\"artifact_refs\":[\"...\"],\"deliverables\":[{\"deliverable_id\":\"...\",\"status\":\"delivered\",\"value\":\"...\",\"unit\":null,\"scope\":\"...\",\"artifact_refs\":[\"...\"]}]}. "
            "Do not include paths, data values, or prose outside JSON."
        ),
        "Scientist": (
            "Return exactly one JSON object: either "
            '{"kind":"plan","task":{"task_id":"...","goal":"...","expected_outputs":["..."],"requested_outputs":["..."],"required_metrics":["..."],"constraints":{}},'
            '"workflow":{"workflow_id":"...","input_artifacts":[{"artifact_id":"input_raster","artifact_type":"raster"}],"nodes":[...]}} '
            'or {"kind":"revise","reason":"...","base_plan_id":"...","affected_node_ids":["..."],"task":...,"workflow":...} '
            'or {"kind":"stop","reason":"..."}. '
            "Every expected_outputs entry must be exactly one of metadata, index_raster, mask_raster, map, area_statistics. "
            "Every node must have exactly node_id, operator_id, inputs, output_artifact_id, config, depends_on. "
            "operator_id must be a full listed identifier, never a short tool name. inputs must be an object, never input_artifact_ids. config must be an object, never safe_parameters. "
            "For an NDVI map, use this exact structural pattern (replace only task_id and goal): "
            '{"kind":"plan","task":{"task_id":"ndvi_task","goal":"...","expected_outputs":["metadata","index_raster","map"],"requested_outputs":["ndvi_map"],"required_metrics":[],"constraints":{"operation":"ndvi"}},'
            '"workflow":{"workflow_id":"ndvi_workflow","input_artifacts":[{"artifact_id":"input_raster","artifact_type":"raster"}],"nodes":['
            '{"node_id":"metadata","operator_id":"expertsrs.read_raster_metadata.v1","inputs":{"file_path":"input_raster"},"output_artifact_id":"metadata","config":{},"depends_on":[]},'
            '{"node_id":"ndvi","operator_id":"expertsrs.calculate_ndvi.v1","inputs":{"file_path":"input_raster"},"output_artifact_id":"ndvi_raster","config":{},"depends_on":["metadata"]},'
            '{"node_id":"index_map","operator_id":"expertsrs.plot_index_map.v1","inputs":{"file_path":"ndvi_raster"},"output_artifact_id":"ndvi_map","config":{},"depends_on":["ndvi"]}]}}. '
            "For green cover, add threshold (expertsrs.apply_threshold.v1, input ndvi_raster, output greenspace_mask, config {\"threshold_low\":0.3}, depends_on ndvi), "
            "then thematic_map (expertsrs.plot_thematic_map.v1) and area_statistics (expertsrs.calculate_area.v1) from greenspace_mask; expected_outputs must include mask_raster and area_statistics, required_metrics must be [\"green_cover_rate\"]. "
            "For a vegetation-coverage request, requested_outputs must include exactly vegetation_coverage_map and green_cover_rate; thematic_map is the vegetation coverage map, never the NDVI map. "
            "delivery_obligations are mandatory runtime-owned outputs: you may add supported outputs but may not omit, rename, or downgrade one. "
            "The only raw input artifact is input_raster; never include a URI, path, data value, or unlisted tool. "
            "For an initial supplied raster, metadata must be the first eligible node before analysis nodes. "
            "If the user requests a named index/operator that is absent from available_tools, return stop with a concise unsupported-catalog reason; do not ask the user to define it and do not substitute another index. "
            "For phase revision_required, return a full revised graph whose affected_node_ids include the observed failed node and only its downstream subgraph; base_plan_id must equal active_plan_id. "
            "Do not include paths, tool arguments, or prose outside JSON."
        ),
        "Engineer": (
            "Return exactly one JSON object: an action selecting exactly one eligible plan node "
            '({"kind":"action","node_id":"..."}), '
            'a handoff ({"kind":"handoff","target":"Manager"}), '
            'or a stop ({"kind":"stop","reason":"..."}). '
            "Choose only an ID in eligible_node_ids.  Do not name a tool, artifact reference, parameter, path or retry strategy; the runtime binds those from the Scientist plan. "
            "If phase is revision_required, do not act: the Scientist must revise the plan. "
            "For an LST precondition task, stop after metadata rather than inventing an LST action. "
            "Hand off only after every planned node has succeeded. "
            "When the requested outputs have been produced successfully, hand off to Manager for the report. "
            "Do not include prose outside JSON."
        ),
    }
