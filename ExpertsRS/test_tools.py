"""Compatibility entry point for the legacy tool smoke command.

It is intentionally import-safe: pytest/unittest discovery can import the
module without executing tools or terminating the Python process.
"""

from __future__ import annotations

from tools_smoke import main


if __name__ == "__main__":
    raise SystemExit(main())
