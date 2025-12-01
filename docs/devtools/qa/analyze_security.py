#!/usr/bin/env python
"""Helper to run Bandit only on production directories (tests excluded)."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_DIRS = ["src", "adapters", "data", "infra", "security"]
EXCLUDE = ["tests"]


def main() -> int:
    cmd = ["bandit", "-r", *TARGET_DIRS, "-x", ",".join(EXCLUDE)]
    return subprocess.call(cmd, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
