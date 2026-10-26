"""Read the authoritative trace during a run; UI code never owns runtime state."""
from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from pathlib import Path


def run_directory(output_dir: str | Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("Invalid run ID")
    root = Path(output_dir).resolve()
    directory = (root / run_id).resolve()
    if directory.parent != root:
        raise ValueError("Run directory escapes output root")
    return directory


def read_events(output_dir: str | Path, run_id: str, *, after: int = 0) -> dict:
    """Cursor is the last sequence number, not a byte offset. Ignore partial tail."""
    if not isinstance(after, int) or isinstance(after, bool) or after < 0:
        raise ValueError("Event cursor must be a non-negative integer")
    path = run_directory(output_dir, run_id) / "trace.jsonl"
    events = []
    cursor = 0
    if path.is_file():
        with path.open("rb") as stream:
            for line in stream:
                if not line.endswith(b"\n"):
                    break
                event = json.loads(line)
                cursor += 1
                if event["sequence_no"] != cursor or event["event_id"] != f"{run_id}:e{cursor:04d}":
                    raise ValueError("Trace sequence or run identity is invalid")
                if cursor > after:
                    events.append(event)
    if after > cursor:
        raise ValueError("Event cursor is ahead of this run")
    return {"schema_version": "expertsrs-events-v1", "run_id": run_id,
            "cursor": cursor, "events": events}


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def run_lease(directory: Path):
    """Reject concurrent writers. A stale lock requires explicit inspection."""
    path = directory / ".run.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ValueError("Run is already active or has an unreconciled worker lock") from error
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink()
