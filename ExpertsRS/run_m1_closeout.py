"""Run the complete no-API Chapter 1 M1 verification loop."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    commands = [
        (
            "scientific, benchmark, workflow, and ReAct unit tests",
            [
                sys.executable, "-m", "unittest", "-v",
                "test_scientific_preconditions.py", "test_ch1_benchmark.py",
                "test_workflow.py", "test_react_orchestration.py",
            ],
        ),
        ("18-tool verification", [sys.executable, "test_tools.py"]),
        ("repair and controlled-stop traces", [sys.executable, "workflow/run_closeout.py"]),
        ("scripted real-tool ReAct pilot", [sys.executable, "run_react_pilot.py"]),
    ]
    for label, command in commands:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False, stderr=subprocess.STDOUT)
        if completed.returncode:
            raise SystemExit(f"M1 closeout failed during: {label}")
    print("\nM1 no-API closeout: PASS")


if __name__ == "__main__":
    main()
