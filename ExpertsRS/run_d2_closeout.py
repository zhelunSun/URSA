"""Run the bounded no-API D2 regression and mechanism evidence package."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    commands = [
        (
            "existing and D2-focused unit tests",
            [
                sys.executable, "-m", "unittest", "-v",
                "test_adaptive_runtime.py", "test_workflow.py",
                "test_react_orchestration.py", "test_scientific_preconditions.py",
                "test_ch1_benchmark.py",
            ],
        ),
        (
            "real-tool adaptive recovery and permission fixture",
            [sys.executable, "-m", "workflow.run_adaptive_pilot"],
        ),
    ]
    for label, command in commands:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False, stderr=subprocess.STDOUT)
        if completed.returncode:
            raise SystemExit(f"D2 closeout failed during: {label}")
    print("\nD2 no-API closeout: PASS")


if __name__ == "__main__":
    main()
