"""Read-only hash check of the four historical v0.5.3 evidence-index files.

This verifies indexed files only, not completeness of every nested run artifact.
It never generates replacement evidence, extracts archives, or calls a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


INDEX = {
    "v2_acceptance_0efd090/acceptance_manifest.json":
        "358B709A907F523955B361B4007FA2E6BD7C974288AEF33BCE276902227DD89D",
    "v2_authorized_pilot_0efd090/v2_pilot_summary.json":
        "6C4F59098937AC895496BA175316B19CE7B086EAB19189C7F43B068512548D78",
    "v2_user_agent_smoke_bb7c8bf/user_agent_summary.json":
        "E60073E3B39F8B06D7B5BF595AEA1D87E398B1B38DF505B90653A2240B19A31C",
    "v2_closeout_0efd090_cli/ndvi_cli/result.json":
        "1F3CBFF84A429E04549DDCC7975B46B707F4308015679CEC3DD25AF7FDA9360D",
}


def inspect(root: Path) -> dict:
    records = []
    for relative, expected in INDEX.items():
        path = root / relative
        actual = None
        status = "missing"
        if path.is_file():
            try:
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                actual = digest.hexdigest().upper()
                status = "matched" if actual == expected else "mismatch"
            except OSError:
                status = "unreadable"
        records.append({"path": relative, "status": status,
                        "expected_sha256": expected, "actual_sha256": actual})
    return {"kind": "v053_indexed_file_check", "root": str(root.resolve()),
            "records": records,
            "all_indexed_files_match": all(item["status"] == "matched" for item in records),
            "full_run_package_completeness": "not_assessed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="Directory containing v2_acceptance_0efd090 etc., normally ExpertsRS/results/ch1_d3_light.")
    args = parser.parse_args()
    result = inspect(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_indexed_files_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
