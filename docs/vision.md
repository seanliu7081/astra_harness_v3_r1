# Optional SAM 3.1 and Depth Anything 3

The core install supports ordinary RGB-based manipulation without downloading
local vision models. V3 invokes vision only when Astra requests a measurement;
`--vision off` disables those tools. Missing dependencies or checkpoints produce
an unavailable-tool response, never a fabricated measurement.

## Install

On Linux x86_64 with Python 3.12 and an NVIDIA driver supporting CUDA 12:

```bash
./scripts/setup_vision.sh --python python3.12
```

This creates `.venv-vision` independently of `.venv` and `.venv-sim`. It installs
PyTorch 2.10.0 / torchvision 0.25.0 from the CUDA 12.8 wheel index, the controller
dependencies, and a minimal inference stack. It clones these pinned sources into
ignored `artifacts/foundation_vision/vendor/`:

| Package | Upstream | Commit |
| --- | --- | --- |
| SAM3 | https://github.com/facebookresearch/sam3 | `f1647e8d0c1d280991f4d1b7d974c2704537fe66` |
| Depth Anything 3 | https://github.com/ByteDance-Seed/Depth-Anything-3 | `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4` |

Optional training, UI and 3D Gaussian splatting packages are omitted. The selected
SAM and DA3 source packages are installed with `--no-deps` because their broad
upstream metadata includes features this harness never invokes. This optional
environment is not a byte-identical reproduction of the original environment;
model source and checkpoint revisions are pinned. Utility package versions are
constrained to the tested resolution in `provenance/vision_resolved.lock.txt`;
the CUDA PyTorch installation remains a separate explicit stage.

## Obtain checkpoints

Authenticate locally using an approved Hugging Face account if SAM access requires
it, then explicitly request downloads:

```bash
./scripts/setup_vision.sh --download-models
```

No Hugging Face tokens are stored in this repository. Access and licensing depend
on the upstream model repository. The script downloads:

| Model | Revision | Repository-relative path |
| --- | --- | --- |
| `facebook/sam3.1` | `daa63191845a41281374e725f4c9e51c7a824460` | `artifacts/foundation_vision/models/sam3.1/sam3.1_multiplex.pt` |
| `depth-anything/DA3-LARGE-1.1` | `0e109ae307c5982f319a67cf6f9f99ccdc0ec97c` | `artifacts/foundation_vision/models/models--depth-anything--DA3-LARGE-1.1/snapshots/0e109ae307c5982f319a67cf6f9f99ccdc0ec97c` |

The launcher discovers those exact local paths automatically. Alternatively,
pass `--sam-checkpoint /path/to/sam3.1_multiplex.pt` and
`--da3-model /path/to/model-directory`; the DA3 directory needs `config.json`
and `model.safetensors`.

## Use the optional environment

```bash
ASTRA_HARNESS_PYTHON="$PWD/.venv-vision/bin/python" ./run.sh inspect --task libero_10_t4
```

Use the same interpreter override with an explicitly approved `run` command.
`--vision-device cuda:0` is the default. SAM uses the 3.1 detector extracted from
the multiplex checkpoint, not the video tracker. Neither predicted masks nor
depth certify physical clearance. Installation and `inspect` do not load models
or issue inference requests.

The core, simulator and optional vision environments were installed from scratch
for this extraction. SAM's multiplex detector/processor, the builder symbols
used by this harness, and the DA3 inference API imported successfully; see
`provenance/vision_install_validation.json`. No model was instantiated, no
checkpoint was downloaded, and no live model inference was run.

`pip check` in `.venv-vision` reports the deliberately omitted DA3 packages
`fastapi`, `open3d`, `pre-commit`, `typer`, `uvicorn` and `xformers`, plus its
`opencv-python` declaration (this environment uses `opencv-python-headless`).
The upstream package lists these extra features as mandatory metadata. The
actual imports required by this harness pass without them. The core and
simulator environments each pass `pip check` without missing requirements.
