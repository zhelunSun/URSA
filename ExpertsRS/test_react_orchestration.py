"""No-API regression tests for ReAct routing, budgets, and trace events."""

import json
import tempfile
import unittest
from pathlib import Path

from react_orchestration import ReActRoutingState, make_react_speaker_selection, register_selector_executor_tools
from run_react_pilot import _decision


class FakeAgent:
    def __init__(self, name):
        self.name = name
        self.llm_tools = []
        self.execution_tools = []

    def register_for_llm(self, **kwargs):
        def register(func):
            self.llm_tools.append((kwargs["name"], func))
            return func
        return register

    def register_for_execution(self, **kwargs):
        def register(func):
            self.execution_tools.append((kwargs["name"], func))
            return func
        return register


class FakeGroupChat:
    def __init__(self, messages):
        self.messages = messages


def tool_message(name, tool="calculate_ndvi", content="Decision: inspect real data first."):
    return {"role": "assistant", "name": name, "content": content, "tool_calls": [
        {"id": "call-1", "type": "function", "function": {"name": tool, "arguments": "{}"}}
    ]}


class ReActRoutingTests(unittest.TestCase):
    def setUp(self):
        self.manager = FakeAgent("Manager")
        self.user = FakeAgent("User")
        self.scientist = FakeAgent("Scientist")
        self.engineer = FakeAgent("Engineer")
        self.executor = FakeAgent("Executor")
        self.state = ReActRoutingState("test")
        self.route = make_react_speaker_selection(
            self.manager, self.user, self.scientist, self.engineer, self.executor, self.state
        )

    def test_scientist_observation_returns_to_scientist(self):
        group = FakeGroupChat([{"role": "user", "content": "task"}, tool_message("Scientist", "read_raster_metadata")])
        self.assertIs(self.route(self.scientist, group), self.executor)
        group.messages.append({"role": "tool", "name": "Executor", "content": "{'success': True, 'data': {'count': 12}}"})
        self.assertIs(self.route(self.executor, group), self.scientist)

    def test_engineer_observation_returns_to_engineer(self):
        group = FakeGroupChat([{"role": "user", "content": "task"}, tool_message("Engineer")])
        self.assertIs(self.route(self.engineer, group), self.executor)
        group.messages.append({"role": "tool", "name": "Executor", "content": "{'success': False, 'message': 'bad path'}"})
        self.assertIs(self.route(self.executor, group), self.engineer)

    def test_only_plain_handoffs_advance_global_workflow(self):
        group = FakeGroupChat([{"role": "user", "content": "task"}, {"role": "assistant", "name": "Scientist", "content": "Plan: use NDVI."}])
        self.assertIs(self.route(self.scientist, group), self.engineer)
        group.messages[-1] = {"role": "assistant", "name": "Engineer", "content": "Result: mask saved."}
        self.assertIs(self.route(self.engineer, group), self.manager)

    def test_budget_stops_extra_scientist_action(self):
        self.state.tool_calls_by_agent["Scientist"] = 4
        group = FakeGroupChat([{"role": "user", "content": "task"}, tool_message("Scientist", "list_available_data_files")])
        self.assertIsNone(self.route(self.scientist, group))
        self.assertTrue(self.state.finalised)

    def test_trace_contains_react_events(self):
        group = FakeGroupChat([{"role": "user", "content": "task"}, tool_message("Engineer")])
        self.route(self.engineer, group)
        group.messages.append({"role": "tool", "name": "Executor", "content": "{'success': True}"})
        self.route(self.executor, group)
        self.state.finalise("completed")
        with tempfile.TemporaryDirectory() as directory:
            path = self.state.trace.write(Path(directory) / "trace.json")
            events = json.loads(path.read_text(encoding="utf-8"))["events"]
            event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types, ["decision", "tool_call", "tool_observation", "final_status"])
        self.assertEqual(events[1]["payload"]["cumulative_tool_calls"], 1)
        self.assertEqual(events[-1]["payload"]["tool_calls"], {"Scientist": 0, "Engineer": 1})

    def test_scripted_recording_path_updates_tool_call_count(self):
        self.state.record_tool_call("Scientist", tool_message("Scientist", "read_raster_metadata"))
        self.state.record_tool_call("Engineer", tool_message("Engineer", "calculate_ndvi"))
        self.state.finalise("completed")
        self.assertEqual(self.state.tool_calls_by_agent, {"Scientist": 1, "Engineer": 1})
        self.assertEqual(
            self.state.trace.events[-1]["payload"]["tool_calls"],
            {"Scientist": 1, "Engineer": 1},
        )

    def test_scripted_pilot_records_reconstructable_arguments(self):
        arguments = {"file_path": "scene.tif", "nir_band": "B8", "red_band": "B4"}
        _decision(self.state, "Engineer", "Decision: compute NDVI.", "calculate_ndvi", arguments)
        call = self.state.trace.events[-1]["payload"]["calls"][0]["function"]
        self.assertEqual(json.loads(call["arguments"]), arguments)

    def test_selector_executor_registration_is_split(self):
        def list_available_data_files():
            """List files."""
        def read_raster_metadata():
            """Read metadata."""
        def calculate_ndvi():
            """Calculate NDVI."""
        register_selector_executor_tools(self.scientist, self.engineer, self.executor, [
            list_available_data_files, read_raster_metadata, calculate_ndvi
        ])
        self.assertEqual([name for name, _ in self.scientist.llm_tools], ["list_available_data_files", "read_raster_metadata"])
        self.assertEqual(len(self.engineer.llm_tools), 3)
        self.assertEqual(len(self.executor.execution_tools), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
