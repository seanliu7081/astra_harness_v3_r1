"""Clone-local task/configuration checks; no model or simulator is launched."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher():
    spec = importlib.util.spec_from_file_location("standalone_launcher", ROOT / "scripts/launch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_is_inspection_and_launch_requires_explicit_approval(launcher):
    parser = launcher.build_parser()
    args = parser.parse_args([])
    assert args.command == "inspect"
    assert not args.approved
    command = launcher.build_command(args)
    assert "inspect" in command
    assert "--approved" not in command
    assert "--output" not in command
    with pytest.raises(ValueError, match="requires --approved"):
        launcher.build_command(parser.parse_args(["run"]))
    with pytest.raises(ValueError, match="only with run"):
        launcher.build_command(parser.parse_args(["inspect", "--approved"]))


@pytest.mark.parametrize("alias,canonical,official", [
    ("t04", "t04_can_obstacle", "libero_10_t4"),
    ("t08", "t08_bottle_obstacle", "libero_10_t8"),
])
def test_bundled_task_inputs_survive_checkout_relocation(launcher, tmp_path, monkeypatch,
                                                        alias, canonical, official):
    relocated = tmp_path / "a clone with spaces"
    shutil.copytree(ROOT / "tasks", relocated / "tasks")
    monkeypatch.setattr(launcher, "ROOT", relocated)
    task, options = launcher.task_options(alias, 0)
    assert task == official
    values = dict(zip(options[::2], options[1::2]))
    data = relocated / "tasks" / canonical
    manifest = json.loads((data / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert sha256((data / name).read_bytes()).hexdigest() == digest
    assert values["--task-bddl-override"] == str(data / "custom_task.bddl")
    assert values["--initial-state-override"] == str(data / "initial_state.npy")
    assert values["--expected-initial-observation-sha256"] == (
        data / "initial_observation.sha256").read_text().strip()
    with pytest.raises(ValueError, match="initial state 0"):
        launcher.task_options(alias, 1)
    with pytest.raises(ValueError, match="cannot be overridden"):
        launcher.task_options(alias, 0, "0" * 64)


def test_custom_task_overrides_require_an_official_task_name(launcher, tmp_path):
    parser = launcher.build_parser()
    args = parser.parse_args(["inspect", "--task", "t04", "--initial-state-override", "state.npy"])
    with pytest.raises(ValueError, match="official task name"):
        launcher.build_command(args)
    args = parser.parse_args(["run", "--approved", "--task", "libero_10_t7",
                             "--expected-initial-observation-sha256", "a" * 64,
                             "--output", str(tmp_path / "fresh run")])
    command = launcher.build_command(args)
    assert "--approved" in command
    assert command[command.index("--task") + 1] == "libero_10_t7"
    assert command[command.index("--expected-initial-observation-sha256") + 1] == "a" * 64
    assert command[command.index("--output") + 1] == str(tmp_path / "fresh run")


def test_list_tasks_and_inspect_do_not_require_installed_simulator_or_auth(tmp_path):
    script = ROOT / "scripts/launch.py"
    listed = subprocess.run([sys.executable, str(script), "--list-tasks"], cwd=tmp_path,
                            check=True, capture_output=True, text=True)
    assert "t04_can_obstacle" in listed.stdout
    assert "t08_bottle_obstacle" in listed.stdout
    assert "libero_10_t7" in listed.stdout
    for task in ("libero_10_t4", "t04_can_obstacle"):
        result = subprocess.run([
            sys.executable, str(script), "inspect", "--task", task, "--vision", "off",
            "--sim-python", str(tmp_path / "missing-python"),
            "--libero-root", str(tmp_path / "missing-libero"),
            "--store-dir", str(tmp_path / "missing-credentials"),
        ], cwd=tmp_path, check=True, capture_output=True, text=True)
        report = json.loads(result.stdout)
        assert report["inspection_only"] is True
        assert report["network_calls"] == report["model_loads"] == report["simulator_resets"] == 0
        config = report["configuration"]
        assert config["revision"] == "astra_tools_r1"
        assert config["billing"] == "chatgpt_subscription"
        assert config["api_key_fallback"] is False
        assert config["automatic_episode_retry"] is False
        assert config["vision"]["preloaded"] is False
        assert config["episode_action_cap"] is config["episode_time_cap_s"] is None
        assert config["transit_command_cap_m"] == config["osc_translation_scale_m"] == .1
    assert not (tmp_path / "missing-credentials").exists()
