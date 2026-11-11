#!/usr/bin/env python3
"""Check bundled task inputs and original r1 policy hashes without inference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
R1_PACKAGE = "src/gpt_field/foundation_vision_harness_V3"
R1_MODULES = {
    f"{R1_PACKAGE}/{name}.py"
    for name in (
        "__init__", "client", "executor", "protocol", "recording", "robot_guard",
        "runner", "telemetry", "vision_tools",
    )
}
TASKS = ("t04_can_obstacle", "t08_bottle_obstacle")


def verify_file(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: {path.relative_to(ROOT)}")


def main() -> int:
    try:
        source = json.loads((ROOT / "provenance/source_manifest.json").read_text())
        if source["revision"] != "astra_tools_r1":
            raise ValueError("Source provenance must identify astra_tools_r1")
        if set(source["preserved_r1_modules"]) != R1_MODULES:
            raise ValueError("Source provenance must contain the nine original r1 modules")
        for name in sorted(R1_MODULES):
            verify_file(ROOT / name, source["upstream_sha256"][name])

        asset_count = 0
        for name, metadata in source["additional_assets"].items():
            verify_file(ROOT / name, metadata["sha256"])
            asset_count += 1
        if asset_count != 6:
            raise ValueError("Expected six bundled custom task assets")

        task_count = 0
        for task in TASKS:
            directory = ROOT / "tasks" / task
            manifest = json.loads((directory / "manifest.json").read_text())
            for name, expected in manifest["files"].items():
                verify_file(directory / name, expected)
                task_count += 1
        if task_count != 6:
            raise ValueError("Expected six recorded T04/T08 input files")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Repository verification failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "revision": source["revision"],
        "frozen_r1_modules_verified": len(R1_MODULES),
        "bundled_layout_assets_verified": asset_count,
        "task_files_verified": task_count,
        "network_calls": 0,
        "model_calls": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
