"""Portable installation paths for the standalone astra_tools_r1 distribution."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def project_root() -> Path:
    """Locate a source checkout or installed shared runtime without using cwd."""
    configured = os.environ.get("ASTRA_HARNESS_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "scripts/evaluate_foundation_vision_harness_V3.py").is_file():
            return parent
    installed = Path(sys.prefix) / "share/astra_harness_v3_r1"
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = project_root()
DEFAULT_SIM_PYTHON = str(Path(os.environ.get(
    "ASTRA_HARNESS_SIM_PYTHON", str(PROJECT_ROOT / ".venv-sim/bin/python"))).expanduser())
DEFAULT_LIBERO_ROOT = str(Path(os.environ.get(
    "ASTRA_HARNESS_LIBERO_ROOT", str(PROJECT_ROOT / "third_party/LIBERO"))).expanduser())
DEFAULT_AUTH_STORE = Path(os.environ.get(
    "ASTRA_HARNESS_AUTH_STORE", str(PROJECT_ROOT / ".private/chatgpt_plan"))).expanduser()
