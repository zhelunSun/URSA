"""Runnable ReAct-style ExpertsRS entry point; the published notebook is untouched."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import autogen

from llm_config_list import config_list
from prompts import engineer_prompt, executor_prompt, manager_prompt, scientist_prompt, user_proxy_prompt
from react_orchestration import (
    ENGINEER_REACT_PROTOCOL,
    SCIENTIST_REACT_PROTOCOL,
    ReActRoutingState,
    make_react_speaker_selection,
    register_selector_executor_tools,
)
from tools import get_all_tools


def _tool_llm_config() -> dict:
    candidates = autogen.filter_config(config_list, {"tags": ["deepseek-v3"]}) or config_list
    if not candidates:
        raise RuntimeError("No LLM configuration found. Configure .env before running react_demo.py.")
    return {"cache_seed": 1, "temperature": 0, "timeout": 180, "config_list": candidates}


def build_react_chat(run_id: str | None = None):
    """Build the ReAct variant with selector/executor tool registration."""
    run_id = run_id or datetime.now().strftime("react_%Y%m%d%H%M%S")
    llm_config = _tool_llm_config()
    user_proxy = autogen.UserProxyAgent(
        name="User", system_message=user_proxy_prompt, code_execution_config=False, human_input_mode="ALWAYS"
    )
    manager = autogen.AssistantAgent(name="Manager", system_message=manager_prompt, llm_config=llm_config)
    scientist = autogen.AssistantAgent(
        name="Scientist", system_message=scientist_prompt + SCIENTIST_REACT_PROTOCOL, llm_config=llm_config
    )
    engineer = autogen.AssistantAgent(
        name="Engineer", system_message=engineer_prompt + ENGINEER_REACT_PROTOCOL, llm_config=llm_config
    )
    executor = autogen.UserProxyAgent(
        name="Executor", system_message=executor_prompt, human_input_mode="NEVER", code_execution_config=False
    )

    register_selector_executor_tools(scientist, engineer, executor, get_all_tools())
    trace_path = Path(__file__).resolve().parent / "results" / f"{run_id}.json"
    routing_state = ReActRoutingState(run_id=run_id, trace_path=trace_path)
    groupchat = autogen.GroupChat(
        agents=[user_proxy, manager, scientist, engineer, executor],
        messages=[],
        max_round=30,
        speaker_selection_method=make_react_speaker_selection(
            manager, user_proxy, scientist, engineer, executor, routing_state
        ),
    )
    chat_admin = autogen.GroupChatManager(name="Chat_Admin", llm_config=llm_config, groupchat=groupchat)
    return user_proxy, chat_admin, routing_state


if __name__ == "__main__":
    user, chat_admin, state = build_react_chat()
    user.initiate_chat(
        chat_admin,
        message="I need a greenspace mask for Dongcheng, Beijing using the available Sentinel-2 data.",
    )
    state.finalise("chat_ended")
    print(f"ReAct trace written to: {state.trace_path}")
