"""Command-line entry point for the authoritative ExpertsRS runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .models import RunRequest
from .system import ExpertsRSSystem


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the unified ExpertsRS research runtime.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Start a new non-overwriting run.")
    run.add_argument("--request", required=True, help="Natural-language remote-sensing request.")
    run.add_argument("--data", action="append", default=[], type=Path, help="Allowed local GeoTIFF path; repeat for multiple inputs.")
    run.add_argument("--output-dir", required=True, type=Path, help="Parent directory for immutable run directories.")
    run.add_argument("--run-id", help="Optional stable run identifier.")
    resume = commands.add_parser("resume", help="Resume a run waiting for clarification.")
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--answer", required=True)
    resume.add_argument("--output-dir", required=True, type=Path)
    return parser


async def _main_async(args: argparse.Namespace) -> int:
    system = ExpertsRSSystem()
    try:
        if args.command == "run":
            result = await system.run(RunRequest(
                request=args.request, data_paths=args.data, output_dir=args.output_dir, run_id=args.run_id,
            ))
        else:
            result = await system.resume(args.run_id, args.answer, args.output_dir)
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        print(json.dumps({"status": "request_rejected", "message": str(error)}, ensure_ascii=False, indent=2))
        return 2
    print(result.model_dump_json(indent=2))
    return 0 if result.status.value != "failed" else 1


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
