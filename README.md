# Astra Harness V3 R1

A standalone repository for **`foundation_vision_harness_V3 / astra_tools_r1`**.
It contains the frozen r1 policy, its complete local dependency chain, LIBERO
source and assets, recorded T04/T08 obstacle scenes, installation scripts, and
CPU regression tests. It does not require the original `gpt_field` checkout.

This is r1: transit routing uses a **20 mm grid** and **120-action fragment
budget**. It does not include r2 obstacle-map prompt changes or r3/r4 routing
changes. The nine V3 implementation modules are preserved byte for byte;
`provenance/source_manifest.json` records extraction and portability changes.

## Clone and install from scratch

Supported platform: **Linux x86_64**, Python **3.12** for the controller and
Python **3.10** for the simulator. Install Git, Python venv support, FFmpeg,
and EGL/OpenGL runtime libraries first. GPU rendering needs a working driver.
The installer creates both virtual environments inside this repository.

```bash
git clone https://github.com/seanliu7081/astra_harness_v3_r1.git
cd astra_harness_v3_r1
./setup.sh
./run.sh inspect --task t04_can_obstacle
```

For a private repository, authenticate Git with your GitHub account before cloning.
If Python is installed elsewhere:

```bash
./setup.sh --python-controller /path/to/python3.12 --python-sim /path/to/python3.10
```

Only need inspection, library development, or CPU tests?

```bash
./setup.sh --core-only
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Setup downloads Python dependencies, including CPU PyTorch for the simulator.
It does not sign in, start an episode, or download optional vision weights.
The simulator uses the included LIBERO source/assets, MuJoCo 3.2.6, robosuite
1.4.1, and a bundled Pillow encoder that preserves frozen reset hashes. No
training datasets or demonstrations are needed. See `THIRD_PARTY_NOTICES.txt`.

## Inspect and run

Inspection is the default and makes no network calls, model loads, or simulator
resets. It works without a subscription login or the simulator environment.

```bash
./run.sh --list-tasks
./run.sh inspect --task t04_can_obstacle
./run.sh inspect --task t08_bottle_obstacle
./run.sh inspect --task libero_10_t7 --vision off
```

Sign in using the framework's existing ChatGPT subscription flow:

```bash
./login.sh login
```

For a remote server, forward the printed loopback listener port over SSH to
your own machine, then open the printed local URL. Credentials stay in ignored
`.private/chatgpt_plan/`; never add them to Git. An existing compatible store
can be passed with `--store-dir /path/to/store`. The model remains
`gpt-6-astra` with high reasoning effort; account/model access is required.
The runner does not use an API key or fall back to a different billing route.

Explicitly start one episode after reviewing its configuration:

```bash
./run.sh run --approved --task t04_can_obstacle --gpu 0 --vision off \
  --output runs/my_t04
./run.sh run --approved --task t08_bottle_obstacle --gpu 0 --vision off \
  --output runs/my_t08
```

Each command runs one task. Existing output directories are refused. There are
no automatic retries or whole-episode action/time/request caps. Use Ctrl-C to
stop, or create `runs/my_t04/trial/operator_stop.request.json`. The original
runner handles termination and writes its final artifacts.

| Task | Scene |
| --- | --- |
| `t04_can_obstacle` / `t04` | Recorded two-mug scene with the added can |
| `t08_bottle_obstacle` / `t08` | Recorded two-moka-pot scene with the added bottle |
| `libero_10_t4`, `libero_10_t8` | Official scenes without those added obstacles |
| Other names from `--list-tasks` | Packaged official tasks and recorded layouts |

The two obstacle scenes contain only initial state 0. The runner verifies each
reset against its frozen image/state hash. Other initial states require an
independently recorded `--expected-initial-observation-sha256`. For a new scene,
select an official task and supply `--task-bddl-override`,
`--initial-state-override`, and the expected hash explicitly.

`--show-command` prints the resolved command without executing it. Paths passed
on the command line are resolved from your current directory; defaults resolve
from the repository location. `ASTRA_HARNESS_PYTHON`,
`ASTRA_HARNESS_SIM_PYTHON`, and `ASTRA_HARNESS_LIBERO_ROOT` allow explicit overrides.

## Optional SAM 3.1 / DA3 measurements

Ordinary RGB-based control works without these models. `--vision off` disables
tools; `--vision on-demand` retains r1's lazy measurement interface and reports
unavailable tools when weights are not configured. It never substitutes weights
or automatically loads perception on each step.

See [optional vision setup](docs/vision.md) for pinned source installation,
checkpoint download, GPU requirements, and launch commands. These large model
weights are downloaded separately and are not committed to Git.

## Preserved behavior and outputs

Astra owns keyposes and emits `execute`, `measure`, `finish`, or `blocked`
contracts. Execution uses measured robot feedback, known-robot guards, a 100 mm
transit command cap, and a 5 mm contact command cap. The 120-action transit
fragment budget returns control to the model; it is not an episode cap.

Raw LIBERO success does not stop control. The model ends autonomously, after
which the evaluator reports raw and strict physical checks both at termination
and after ten unchanged-gripper hold actions. Collisions are recorded.
Estimated obstacle boxes are not a guarantee of collision-free execution.

Each run saves configuration, source hashes and a launch copy, dependency
versions, the terminal source audit, JSON result, policy/model logs, and (unless
`--no-video`) asynchronously recorded video under `trial/`. Online wall time
includes model/tool waiting and recording overhead.

The `gpt_field` Python namespace and legacy helper filenames are retained to
preserve imports. Use this repository's own environment; do not install another
`gpt-field` distribution into it.

## Validation and provenance

```bash
.venv/bin/python -m pytest
.venv/bin/python scripts/verify_repository.py
```

Tests exercise the frozen r1 contract, routing, public-observation boundaries,
vision-tool failure handling, terminal evaluation, and portable task selection.
Installation and offline validation are not new live task-performance results.
See [validation record](docs/validation.md) for the checks performed on this
extraction, and `provenance/` for upstream hashes and third-party inventories.
