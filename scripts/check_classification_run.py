"""External product-consistency check; never imported into runtime/model context.

The reference describes the same existing raster, not independent thematic gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(run_dir, reference_path):
    root = run_dir.resolve()
    result = json.loads((root / "result.json").read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    table_records = [a for a in result["artifacts"] if a["artifact_type"] == "composition_table"]
    if len(table_records) != 1:
        raise ValueError("Expected exactly one composition artifact")
    record = table_records[0]
    table_path = Path(record["uri"]).resolve()
    if not table_path.is_relative_to(root):
        raise ValueError("Composition artifact leaves the run directory")
    table = json.loads(table_path.read_text(encoding="utf-8"))["data"]
    expected = reference["aoi"]
    checks = {
        "completed": result["status"] == "completed",
        "explicit_offline_identity": result["execution_mode"] == "scripted-offline" and result["provider"] == "scripted",
        "raster_identity": table["provenance"]["raster_sha256"] == reference["intake"]["sha256"],
        "aoi_identity": all(table["provenance"]["aoi_component_hashes"].get(Path(a["path"]).suffix) == a["sha256"]
                            for a in reference["aoi_components"]),
        "product_year": table["year"] == reference["product_year"],
        "class_counts": table["counts"] == expected["counts"],
        "valid_pixels": table["valid_pixels"] == expected["valid_pixels"],
        "nodata_pixels": table["nodata_pixels"] == expected["nodata_pixels"],
        "aoi_pixel_centres": table["aoi_pixel_centres"] == expected["aoi_pixel_centres"],
        "fractions": set(table["fractions"]) == set(expected["fractions"]) and all(
            abs(table["fractions"][name] - value) <= 1e-12 for name, value in expected["fractions"].items()),
        "artifact_hashes": True,
    }
    for artifact in result["artifacts"]:
        path = Path(artifact["uri"]).resolve()
        checks["artifact_hashes"] &= path.is_relative_to(root) and path.is_file() and file_hash(path) == artifact["metadata"]["artifact_sha256"]
        for secondary in artifact["metadata"].get("secondary_outputs", []):
            path = Path(secondary["path"]).resolve()
            checks["artifact_hashes"] &= path.is_relative_to(root) and path.is_file() and file_hash(path) == secondary["sha256"]
    return {"kind": "classification_same_product_consistency", "run_id": result["run_id"],
            "reference_sha256": file_hash(reference_path), "result_sha256": file_hash(root / "result.json"),
            "checks": checks, "passed": all(checks.values()), "model_calls": 0,
            "scientific_validity": "not_assessed", "system_effect": "not_assessed",
            "boundary": "Same-product computation parity only; shared source algorithm, not independent thematic gold."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = check(args.run_dir, args.reference)
    payload = json.dumps(receipt, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(payload + "\n")
    print(payload)
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
