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
            '{"kind":"report","summary":"...","artifact_refs":["artifact-id"]}. '
            "If input_data_available is true, the local runtime already has the input; do not ask for a file path or upload. "
            "Clarify only when the requested analysis goal, metric, or output is semantically ambiguous. "
            "Do not ask for sensor, bands, raster metadata, spatial coverage, or file format when input data is available; "
            "the Scientist and registered tools must inspect those technical preconditions. "
            "When phase is report, artifact_refs must contain every artifact_id listed in artifact_manifest exactly once; "
            "do not omit a validated artifact and do not invent an ID. "
            "Do not include paths, data values, or prose outside JSON."
        ),
        "Scientist": (
            "Return exactly one JSON object: either "
            '{"kind":"plan","operation":"ndvi|greenspace|lst","next_action":"read_raster_metadata"} '
            'or {"kind":"stop","reason":"..."}. '
            "For a new supplied raster, next_action must be read_raster_metadata; otherwise use only a listed registered tool name. "
            "Do not include paths, tool arguments, or prose outside JSON."
        ),
        "Engineer": (
            "Return exactly one JSON object: an action using only a listed tool binding "
            '({"kind":"action","tool_name":"...","artifact_refs":["artifact-id"],"parameters":{}}), '
            'a handoff ({"kind":"handoff","target":"Manager"}), '
            'a stop ({"kind":"stop","reason":"..."}), or '
            'a revision ({"kind":"revise","next_action":"registered_tool"}). '
            "If phase is revision_required after a failed observation, return revise before any retry action. "
            "Follow current_plan.next_action before another tool when it is a listed tool that has not yet succeeded. "
            "Do not repeat a successful tool unless a revised plan explicitly requires it. "
            "When the request's required artifacts are already present (including area_statistics for green-cover work), hand off to Manager instead of adding another action. "
            "When the requested outputs have been produced successfully, hand off to Manager for the report. "
            "Never include paths or unlisted parameters; do not include prose outside JSON."
        ),
    }
