"""Explicit, no-fallback provider construction for the unified runtime."""

from __future__ import annotations

import os
from typing import Any

from .decisions import AutoGenSelectorDecisionProvider
from .models import ProviderConfig


class ProviderFailure(RuntimeError):
    """Sanitized provider failure that is safe to persist in a trace."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


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
            temperature=config.temperature,
            top_p=config.top_p,
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


def _role_instructions() -> dict[str, str]:
    """Only redacted runtime state and a typed decision schema reach the model."""
    return {
        "Manager": (
            "Return exactly one JSON object: either "
            '{"kind":"clarify","question":"..."} or '
            '{"kind":"handoff","target":"Scientist"}. '
            "Do not include paths, data values, or prose outside JSON."
        ),
        "Scientist": (
            "Return exactly one JSON object: either "
            '{"kind":"plan","operation":"ndvi|greenspace|lst","next_action":"registered_tool"} '
            'or {"kind":"stop","reason":"..."}. '
            "Do not include paths, tool arguments, or prose outside JSON."
        ),
        "Engineer": (
            "Return exactly one JSON object: an action using only a listed tool binding "
            '({"kind":"action","tool_name":"...","artifact_refs":["artifact-id"],"parameters":{}}), '
            'a handoff ({"kind":"handoff","target":"Manager"}), a stop, or a revise. '
            "Never include paths or unlisted parameters; do not include prose outside JSON."
        ),
    }
