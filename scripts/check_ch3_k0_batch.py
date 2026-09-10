"""External same-product checking; never imported by the model execution runner."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ExpertsRS.classification_bridge import file_hash, verify_records

REFERENCE_SHA="48ed17afda7de04a456b99470ceb437ce812a4f83f40e62204c2e57409221881"


def evaluate(batch, reference_path):
    if file_hash(reference_path) != REFERENCE_SHA:
        raise ValueError("External reference identity changed")
    reference=json.loads(reference_path.read_text(encoding="utf-8"))["aoi"]
    manifest=json.loads((batch/"batch_manifest.json").read_text(encoding="utf-8"))
    summary=json.loads((batch/"batch_summary.json").read_text(encoding="utf-8"))
    rows=[]
    for episode in summary["episodes"]:
        run_dir=batch/episode["episode_id"]
        state=json.loads((run_dir/"state.json").read_text(encoding="utf-8"))
        if episode["condition"] == "U":
            result=json.loads((run_dir/"result.json").read_text(encoding="utf-8"))
            answer=result.get("report") or "\n".join(result.get("questions",[]))
            if not answer:
                reasons=[e["payload"].get("reason","") for e in state.get("trace",{}).get("events",[]) if e["event_type"]=="run_terminal"]
                answer="\n".join(reasons)
        else:
            answer=state.get("answer")
        checks={"response_model_exact":episode["response_models"]==[manifest["model"]],
                "all_responses_stop":bool(episode["finish_reasons"]) and all(v=="stop" for v in episode["finish_reasons"])}
        try:
            verify_records(state);checks["artifact_hashes_valid"]=True
        except (OSError,ValueError,KeyError):
            checks["artifact_hashes_valid"]=False
        case_id=episode["episode_id"].rsplit("_",1)[0]
        if case_id == "K0-01":
            tables=[a for a in state["artifacts"] if a["artifact_type"]=="composition_table"]
            maps=[a for a in state["artifacts"] if a["artifact_type"]=="map"]
            checks.update(terminal_completed=episode["status"]=="completed",composition_present=bool(tables),map_present=bool(maps))
            if tables:
                table=tables[-1];data=table["metadata"]
                persisted=json.loads(Path(table["uri"]).read_text(encoding="utf-8"))["data"]
                checks["persisted_counts_match_manifest"]=persisted["counts"]==data["counts"]
                checks["counts_exact"]=data["counts"]==reference["counts"]
                checks["fractions_within_1e8"]=set(data["fractions"])==set(reference["fractions"]) and all(abs(data["fractions"][k]-v)<=1e-8 for k,v in reference["fractions"].items())
                for key in ("valid_pixels","nodata_pixels","aoi_pixel_centres"):
                    checks[key+"_exact"]=data[key]==reference[key]
                checks["count_conservation"]=sum(data["counts"].values())==data["valid_pixels"] and data["valid_pixels"]+data["nodata_pixels"]==data["aoi_pixel_centres"]
                inputs=manifest["input_resources"][0]
                checks["raster_source_exact"]=data["provenance"]["raster_sha256"]==inputs["classification"]["sha256"]
                checks["aoi_sources_exact"]=data["provenance"]["aoi_component_hashes"]==inputs["study_area"]["components"]
                checks["valid_pixel_denominator"]=data["scope"]["fraction_denominator"]=="valid_pixels (codes 0-7 only)"
                if maps:
                    m=maps[-1]["metadata"]
                    checks["map_same_counts"]=m["counts"]==data["counts"]
                    checks["map_same_sources"]=m["provenance"]["raster_sha256"]==data["provenance"]["raster_sha256"] and m["provenance"]["aoi_component_hashes"]==data["provenance"]["aoi_component_hashes"] and m["provenance"]["composition_sha256"]==table["metadata"]["artifact_sha256"]
        rows.append({**episode,"case_id":case_id,"machine_checks":checks,"all_machine_checks_pass":all(checks.values()),
            "answer_for_content_review":answer,"content_review":"pending",
            "figure_review":"pending" if any(a["artifact_type"]=="map" for a in state["artifacts"]) else "not_applicable",
            "scope":"State alone does not establish appropriate noncompletion or scientific correctness"})
    return {"reference_sha256":REFERENCE_SHA,"rows":rows,"unrun_episodes":summary["unrun_episodes"],
            "interrupted_episodes":summary["interrupted_episodes"],"overall_task_correctness":"pending_content_and_figure_review",
            "warning":"Same-product checking is not thematic accuracy, held-out generalization or a causal mechanism comparison"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch",type=Path,required=True)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=evaluate(args.batch,args.reference)
    with args.output.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({"rows":len(result["rows"]),"machine_checks_pass":[r["episode_id"] for r in result["rows"] if r["all_machine_checks_pass"]],"content_review":"pending"}))
