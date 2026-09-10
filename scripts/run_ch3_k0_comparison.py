"""One frozen six-episode K0 development batch. No evaluator is loaded here."""
import argparse
import asyncio
import copy
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from autogen_core import EVENT_LOGGER_NAME
from dotenv import dotenv_values
from ExpertsRS.classification_bridge import file_hash, tool_contracts
from ExpertsRS.classification_comparison import (COMMON_INSTRUCTIONS, SINGLE_INSTRUCTIONS, ClassificationComparisonSystem,
    SingleDecisionProvider, role_instructions, run_single)
from ExpertsRS.models import InputResource, ProviderConfig, RunBudgets, RunRequest
from ExpertsRS.provider import create_autogen_live_provider, create_model_client
from scripts.run_flash_runtime_smoke import Journal, JournaledProvider, now, write_new

MODEL = "deepseek-ai/DeepSeek-V4-Flash"
CASE_FILES = ("DEV-COMPOSITION", "DEV-MISSING-AOI", "DEV-UNSUPPORTED-ECOLOGY")
ORDER = ((0,"U"),(0,"G"),(1,"G"),(1,"U"),(2,"U"),(2,"G"))
BUDGETS = RunBudgets(max_model_turns=12,max_tool_calls=10,max_tool_calls_engineer=10,
                    max_wall_time_seconds=600,max_total_tokens_recorded=70000)


def load_inputs(prepared_root, state_path):
    receipt = json.loads((prepared_root/"private/receipt.json").read_text(encoding="utf-8"))
    if receipt["status"] != "passed" or file_hash(state_path) != receipt["existing_state_sha256"]:
        raise ValueError("Preparation receipt or frozen source identity mismatch")
    bindings = json.loads(state_path.read_text(encoding="utf-8"))["input_resources"]
    packets, selected = [], []
    for index, name in enumerate(CASE_FILES):
        path = prepared_root/"public"/f"{name}.json"
        if file_hash(path) != receipt["public_packet_hashes"][path.name]:
            raise ValueError("Public packet changed since preparation")
        packet = json.loads(path.read_text(encoding="utf-8"))
        if set(packet) != {"schema_version","case_id","request","product_year","resources","deliverables","knowledge_status","tool_names"}:
            raise ValueError("Public packet contains unexpected fields")
        packet["case_id"] = f"K0-{index+1:02d}"  # Remove development filenames that hint at expected behavior.
        if packet["knowledge_status"] != "unavailable" or packet["tool_names"] != [t["name"] for t in tool_contracts(2025)]:
            raise ValueError("K0 knowledge/tool contract changed")
        available = {}
        for ref in packet["resources"]:
            resource = bindings[ref["resource_id"]]
            path = Path(resource["path"])
            if resource["artifact_type"] != ref["artifact_type"] or file_hash(path) != ref["sha256"]:
                raise ValueError("Resource binding identity mismatch")
            if resource.get("components",{}) != ref["components"]:
                raise ValueError("AOI component list mismatch")
            for suffix, expected in ref["components"].items():
                if file_hash(path.with_suffix(suffix)) != expected:
                    raise ValueError("AOI component identity mismatch")
            available[ref["resource_id"]] = copy.deepcopy(resource)
        packets.append(packet); selected.append(available)
    return packets, selected


async def run(args):
    if not args.allow_api:
        raise ValueError("Explicit --allow-api required before credential access")
    if args.output.exists():
        raise FileExistsError("Batch output exists; no overwrite or silent rerun")
    packets, resources = load_inputs(args.prepared_root,args.binding_state)
    git = lambda *a: subprocess.check_output(["git",*a],cwd=ROOT,text=True).strip()
    commit=git("rev-parse","HEAD")
    if git("status","--porcelain") or commit != git("rev-parse","@{upstream}"):
        raise ValueError("Commit and push a clean checkpoint before live execution")
    values=dotenv_values(args.credentials_file)
    key=values.get("SILICONFLOW_API_KEY") or ""
    base=(values.get("SILICONFLOW_BASE_URL") or "").rstrip("/")
    url=urlsplit(base)
    if not key or url.scheme != "https" or url.netloc != "api.siliconflow.cn" or url.path != "/v1" or url.query or url.fragment:
        raise ValueError("Expected existing SiliconFlow credentials and official endpoint")
    config=ProviderConfig(model=MODEL,api_key_env="SILICONFLOW_API_KEY",base_url_env="SILICONFLOW_BASE_URL",
                          enable_thinking=False,max_completion_tokens=4096)
    args.output.mkdir(parents=True,exist_ok=False)
    write_new(args.output/"public_packets.json",packets)
    write_new(args.output/"prompt_contracts.json",{"common":COMMON_INSTRUCTIONS,"U":role_instructions(),"G":SINGLE_INSTRUCTIONS,
                                                "tools":tool_contracts(2025)})
    manifest={"kind":"ch3-k0-six-episode-development","code_commit":commit,"created_at":now(),
        "model":MODEL,"provider_config":config.model_dump(),"endpoint":base,"per_episode_budget":BUDGETS.model_dump(),
        "scheduled_episodes":[f"{packets[i]['case_id']}_{c}" for i,c in ORDER],"maximum_model_decisions":72,
        "knowledge_status":"unavailable","evaluator_loaded":False,"input_resources":resources,
        "public_packets_sha256":file_hash(args.output/"public_packets.json"),
        "prompt_contracts_sha256":file_hash(args.output/"prompt_contracts.json"),
        "stop_policy":"One attempt per episode. Continue recorded task failures; stop batch on authentication/transport failure. No repairs or reruns.",
        "scope":"Development integration and same-product checking only; not held-out or causal mechanism evidence"}
    write_new(args.output/"batch_manifest.json",manifest)
    journal=Journal(args.output/"model_journal.jsonl",key)
    logger=logging.getLogger(EVENT_LOGGER_NAME)
    old_level,old_propagate=logger.level,logger.propagate
    logger.addHandler(journal);logger.setLevel(logging.INFO);logger.propagate=False
    old_env={k:os.environ.get(k) for k in (config.api_key_env,config.base_url_env)}
    os.environ[config.api_key_env],os.environ[config.base_url_env]=key,base
    episodes=[];started=[];batch_error=None
    try:
        for index, condition in ORDER:
            packet=packets[index]; episode_id=f"{packet['case_id']}_{condition}"
            started.append(episode_id);journal.case_id=episode_id
            print(json.dumps({"starting":episode_id,"at":now()}),flush=True)
            t=time.monotonic();inner=None
            try:
                if condition == "U":
                    inner=create_autogen_live_provider(config,role_instructions())
                    system=ClassificationComparisonSystem(packet,JournaledProvider(inner,journal))
                    request=RunRequest(request=packet["request"],domain_profile="classification-v1",classification_admission="ch3-k0-dev-v1",
                        product_year=packet["product_year"],input_resources={k:InputResource(path=r["path"],artifact_type=r["artifact_type"],sha256=r["sha256"]) for k,r in resources[index].items()},
                        output_dir=args.output,run_id=episode_id,budgets=BUDGETS,execution_mode="autogen-live",provider=config)
                    result=await system.run(request)
                    state=json.loads((args.output/episode_id/"state.json").read_text(encoding="utf-8"))
                    record={"episode_id":episode_id,"condition":condition,"status":result.status.value,
                            "tool_calls":result.validation.tool_calls,"model_decisions":result.validation.model_turns}
                else:
                    inner=SingleDecisionProvider(create_model_client(config))
                    state=await run_single(packet,resources[index],args.output/episode_id,JournaledProvider(inner,journal),BUDGETS.model_dump())
                    record={"episode_id":episode_id,"condition":condition,"status":state["status"],
                            "tool_calls":state["tool_calls"],"model_decisions":state["model_calls"]}
                responses=[r for r in journal.responses if r["case_id"] == episode_id]
                record.update(wall_seconds=round(time.monotonic()-t,3),response_count=len(responses),
                    actual_tokens=sum(r.get("prompt_tokens",0)+r.get("completion_tokens",0) for r in responses),
                    response_models=sorted({r["response"].get("model","unknown") for r in responses}),
                    finish_reasons=[c.get("finish_reason") for r in responses for c in r["response"].get("choices",[])])
                episodes.append(record);write_new(args.output/f"{episode_id}.receipt.json",record)
                print(json.dumps(record),flush=True)
                if record["model_decisions"] and not responses:
                    batch_error="no_response_transport_or_initialization_failure";break
                if any(e.get("event_type")=="provider_failed" and e.get("payload",{}).get("code") in {"provider_api_error","provider_timeout"} for e in state.get("trace",{}).get("events",[])):
                    batch_error="provider_transport_failure";break
                if condition == "G" and state.get("error_type") not in (None,"ValueError","TypeError","KeyError"):
                    batch_error="single_agent_transport_or_unexpected_failure";break
            finally:
                if inner is not None:
                    await inner.model_client.close()
    except Exception as error:
        batch_error=type(error).__name__
        journal.record("batch_error",{"error_type":batch_error})
    finally:
        summary={"kind":manifest["kind"],"finished_at":now(),"episodes":episodes,"batch_error":batch_error,
            "decision_attempts":journal.intents,"response_count":len(journal.responses),
            "actual_response_usage":{"prompt_tokens":sum(r.get("prompt_tokens",0) for r in journal.responses),
                                     "completion_tokens":sum(r.get("completion_tokens",0) for r in journal.responses)},
            "currency_cost":None,"unrun_episodes":[e for e in manifest["scheduled_episodes"] if e not in started],
            "interrupted_episodes":[e for e in started if e not in {r["episode_id"] for r in episodes}],
            "task_correctness":"requires_external_evaluation_and_readonly_content_review"}
        write_new(args.output/"batch_summary.json",summary)
        logger.removeHandler(journal);logger.setLevel(old_level);logger.propagate=old_propagate;journal.close()
        for k,v in old_env.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if batch_error is None and len(episodes)==6 else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-root",type=Path,required=True)
    parser.add_argument("--binding-state",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--credentials-file",type=Path,required=True)
    parser.add_argument("--allow-api",action="store_true")
    raise SystemExit(asyncio.run(run(parser.parse_args())))
