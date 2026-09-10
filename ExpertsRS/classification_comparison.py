"""K0 development adapters: existing URSA scheduler versus one tool-loop agent."""
import asyncio
import json
import time
from pathlib import Path

from .classification_bridge import (factual_deliverables, invoke, make_record, public_facts,
                                    resolve_arguments, tool_contracts, validate_final)
from .decisions import _decode_single_json_object
from .domain import obligations
from .system import ExpertsRSSystem, LocalToolExecutor


COMMON_INSTRUCTIONS = (
    "You are performing the public remote-sensing task. You have only the listed classification tools and bound logical resources. "
    "No shell, arbitrary files, web or other tools are available. Knowledge service status is unavailable. "
    "Decide whether the resources, tool capabilities and evidence suffice for the requested result. "
    "Ask a targeted question for missing user information, or stop with a specific unsupported-capability/evidence reason. "
    "Do not substitute a different task or assert evidence you do not have. Tool counts describe this product, not independently validated accuracy, true area or ecological function. "
    "Use only listed resource and produced artifact IDs; never supply paths. year must equal product_year. "
    "For product reporting, factual_deliverables are actual computed facts available to both systems: copy them without changing values, scope or references. "
    "Output one JSON object only; preserve unsuccessful attempts."
)


def role_instructions():
    return {
        "Manager": COMMON_INSTRUCTIONS + (
            ' Initially return {"kind":"clarify","question":"..."} or {"kind":"handoff","target":"Scientist"}. '
            'When phase=report return {"kind":"report","summary":"...","artifact_refs":["..."],"deliverables":[...]}. '
            "Reference all produced artifacts and copy factual_deliverables exactly."
        ),
        "Scientist": COMMON_INSTRUCTIONS + (
            ' Return {"kind":"stop","reason":"..."} or {"kind":"plan","task":{"task_id":"...","goal":"...",'
            '"expected_outputs":["composition_table","map"],"requested_outputs":["class_composition","classification_map"],'
            '"required_metrics":[],"constraints":{}},"workflow":{"workflow_id":"...","input_artifacts":'
            '[{"artifact_id":"...","artifact_type":"raster or aoi"}],"nodes":[...]}}. '
            "Declare only supplied input resources. Each node has node_id, operator_id, inputs (parameter to logical artifact ID), "
            "output_artifact_id, config (year), depends_on (node IDs). Use full operator_id from tool_contracts. "
            "Node IDs for the two product obligations are composition and classification_map. Every output logical ID must be distinct from input IDs. "
            "Map consumes composition output and depends_on its producer. No legacy NDVI metadata/index node is needed. "
            "During revision_required either stop or return kind=revise with reason, base_plan_id=active_plan_id, affected_node_ids and full task/workflow. "
            "A revision cannot replace the original task."
        ),
        "Engineer": COMMON_INSTRUCTIONS + (
            ' Return {"kind":"action","node_id":"..."} for one eligible_node_id, '
            '{"kind":"handoff","target":"Manager"} only after all nodes succeeded, or {"kind":"stop","reason":"..."}. '
            "Runtime resolves inputs/parameters from the accepted Scientist graph."
        ),
    }


SINGLE_INSTRUCTIONS = COMMON_INSTRUCTIONS + (
    ' Choose your own next tool with {"kind":"tool","tool":"...","inputs":{"parameter":"resource-or-artifact-id"},"parameters":{"year":2025}}, '
    'or {"kind":"clarify","question":"..."}, or {"kind":"stop","reason":"..."}, '
    'or {"kind":"final","answer":"...","artifact_refs":["..."],"deliverables":[...]}. '
    "No plan graph or role handoff is required. A tool producing an intermediate product returns its artifact ID; subsequent tools may use it. "
    "In a final answer reference all produced artifacts and copy factual_deliverables exactly."
)


def required_products(packet):
    return ["class_composition", "classification_map"] if "class_counts" in packet["deliverables"] else []


def shared_view(packet, state):
    return {"public_task":packet, "tool_contracts":tool_contracts(state["product_year"]),
            "required_product_deliverables":required_products(packet),
            "knowledge_status":"unavailable", "available_artifacts":public_facts(state),
            "factual_deliverables":factual_deliverables(state)}


class ContextProvider:
    def __init__(self, inner, packet):
        self.inner, self.packet, self.state = inner, packet, None

    async def decide(self, role, view):
        return await self.inner.decide(role, {**view, **shared_view(self.packet, self.state)})

    async def save_state(self):
        saver = getattr(self.inner, "save_state", None)
        return await saver() if callable(saver) else None

    async def load_state(self, state):
        loader = getattr(self.inner, "load_state", None)
        if callable(loader):
            await loader(state)


class ClassificationComparisonSystem(ExpertsRSSystem):
    """Only domain adapters differ; run/resume/drive/plan/action scheduling is inherited."""
    def __init__(self, packet, provider, **kwargs):
        self.context_provider = ContextProvider(provider, packet)
        self.packet = packet
        super().__init__(provider=self.context_provider, **kwargs)

    def _request_obligations(self, request):
        # Public output requirements, never expected behavior or grading labels.
        return obligations() if "class_counts" in self.packet["deliverables"] else []

    async def run(self, request):
        if request.domain_profile != "classification-v1" or request.classification_admission != "ch3-k0-dev-v1":
            raise ValueError("Comparison adapter requires explicit classification development contract")
        if request.request != self.packet["request"] or request.product_year != self.packet["product_year"]:
            raise ValueError("Run request disagrees with public task")
        if set(request.input_resources) != {r["resource_id"] for r in self.packet["resources"]}:
            raise ValueError("Run resources disagree with public task")
        return await super().run(request)

    def _initial_state(self, request, run_id, run_dir):
        state = super()._initial_state(request, run_id, run_dir)
        for reference in self.packet["resources"]:
            actual = state["input_resources"][reference["resource_id"]]
            if actual["sha256"] != reference["sha256"] or actual.get("components",{}) != reference.get("components",{}):
                raise ValueError("Admitted resource changed since the public packet was frozen")
        return state

    async def _decide(self, state, role):
        self.context_provider.state = state
        return await super()._decide(state, role)

    def _domain_arguments(self, state, node, operator):
        inputs = {key: (value if value in state["input_resources"] else state["workflow_artifact_records"].get(value, value))
                  for key, value in node.inputs.items()}
        try:
            return resolve_arguments(state, operator.tool_name, inputs, node.config), None
        except (OSError, ValueError, TypeError, KeyError) as error:
            return None, str(error)

    def _record_artifact(self, state, trace, action_id, tool_name, result, *, plan_node_id=None):
        record = make_record(state, action_id, tool_name, result, plan_node_id)
        if record:
            state["artifacts"].append(record.model_dump(mode="json"))
            trace.record_artifact(record.artifact_id,"Executor",action_id,str(record.uri),True,
                                  artifact_type=record.artifact_type,plan_node_id=plan_node_id)
        return record


class SingleDecisionProvider:
    """One persistent AutoGen AssistantAgent using the same model client as URSA."""
    def __init__(self, model_client):
        from autogen_agentchat.agents import AssistantAgent
        self.model_client = model_client
        self.agent = AssistantAgent("single_agent", model_client=model_client, system_message=SINGLE_INSTRUCTIONS)

    async def decide(self, role, state):
        from autogen_agentchat.messages import TextMessage
        from autogen_core import CancellationToken
        response = await self.agent.on_messages([TextMessage(content=json.dumps(state,ensure_ascii=False),source="user")], CancellationToken())
        message = response.chat_message
        decision = _decode_single_json_object(message.content)
        usage = message.models_usage
        if usage is None:
            raise ValueError("Missing model usage")
        decision["_provider_usage"] = {"prompt_tokens":usage.prompt_tokens,"completion_tokens":usage.completion_tokens,
                                        "total_tokens":usage.prompt_tokens+usage.completion_tokens}
        return decision


async def run_single(packet, resources, destination, provider, budgets, executor=None):
    run_id = destination.name
    destination.mkdir(parents=True,exist_ok=False)
    state = {"run_id":run_id,"run_dir":str(destination.resolve()),"product_year":packet["product_year"],
             "input_resources":resources,"allowed_data_roots":sorted({str(Path(r['path']).resolve().parent) for r in resources.values()}),
             "artifacts":[],"budgets":budgets,"tool_calls":0,"tool_events":[],"decisions":[],"observations":[],
             "status":"running","answer":None,"model_calls":0,"total_tokens":0,
             "required_product_deliverables":required_products(packet)}
    start = time.monotonic()
    executor = executor or LocalToolExecutor()

    def persist():
        state["wall_seconds"] = time.monotonic()-start
        (destination/"state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

    try:
        while state["status"] == "running":
            remaining = budgets["max_wall_time_seconds"]-(time.monotonic()-start)
            if state["model_calls"] >= budgets["max_model_turns"] or state["total_tokens"] >= budgets["max_total_tokens_recorded"] or remaining <= 0:
                state.update(status="controlled_stop",answer="run_budget_exhausted")
                break
            state["model_calls"] += 1
            persist()
            decision = await asyncio.wait_for(provider.decide("Single", {**shared_view(packet,state),
                "observations":state["observations"],"remaining_tool_budget":budgets["max_tool_calls"]-state["tool_calls"]}),remaining)
            usage = decision.pop("_provider_usage", {})
            if any(not isinstance(usage.get(k),int) or usage[k] < 0 for k in ("prompt_tokens","completion_tokens","total_tokens")) or usage["total_tokens"] != usage["prompt_tokens"]+usage["completion_tokens"]:
                raise ValueError("Missing or invalid model usage")
            state["total_tokens"] += usage["total_tokens"]
            state["decisions"].append(decision)
            if state["total_tokens"] > budgets["max_total_tokens_recorded"]:
                state.update(status="controlled_stop", answer="total_token_budget_exhausted")
                break
            kind = decision.get("kind")
            required = {"tool":{"kind","tool","inputs","parameters"}, "clarify":{"kind","question"},
                        "stop":{"kind","reason"},"final":{"kind","answer","artifact_refs","deliverables"}}
            if kind not in required or set(decision) != required[kind]:
                raise ValueError("Invalid single-agent decision schema")
            if kind == "tool":
                state["observations"].append(invoke(state,decision["tool"],decision["inputs"],decision["parameters"],executor))
            elif kind == "clarify":
                if not isinstance(decision["question"],str) or not decision["question"].strip():
                    raise ValueError("Empty clarification")
                state.update(status="needs_clarification",answer=decision["question"])
            elif kind == "stop":
                if not isinstance(decision["reason"],str) or not decision["reason"].strip():
                    raise ValueError("Empty stop reason")
                state.update(status="controlled_stop",answer=decision["reason"])
            else:
                if not isinstance(decision["answer"],str) or not decision["answer"].strip():
                    raise ValueError("Empty final answer")
                validate_final(state,decision["artifact_refs"],decision["deliverables"])
                state.update(status="completed",answer=decision["answer"])
            persist()
    except Exception as error:
        state.update(status="failed",error_type=type(error).__name__,answer="Runtime or provider failure; inspect preserved journal")
    finally:
        persist()
    return state
