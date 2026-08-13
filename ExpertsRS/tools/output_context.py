"""Per-run output isolation for the legacy remote-sensing tool functions.

The original tools write to ``ExpertsRS/results``.  The new runtime scopes each
tool call to ``<run>/artifacts/<action-id>`` so a retry cannot overwrite an
earlier artifact and an evaluation run cannot contaminate another run.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator


_OUTPUT_DIRECTORY: ContextVar[Path | None] = ContextVar("expertsrs_output_directory", default=None)


def current_output_directory(default: str | Path) -> str:
    directory = _OUTPUT_DIRECTORY.get() or Path(default)
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory)


@contextmanager
def use_output_directory(directory: str | Path) -> Iterator[Path]:
    path = Path(directory).resolve()
    path.mkdir(parents=True, exist_ok=True)
    token = _OUTPUT_DIRECTORY.set(path)
    try:
        yield path
    finally:
        _OUTPUT_DIRECTORY.reset(token)
