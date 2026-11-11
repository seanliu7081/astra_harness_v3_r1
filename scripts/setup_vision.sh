#!/usr/bin/env bash
# Optional GPU vision runtime, isolated from the controller and simulator.
set -euo pipefail
astra_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
astra_vision_python="python3.12"
astra_vision_env="${astra_root}/.venv-vision"
astra_download_models=0
while (($#)); do
  case "$1" in
    --python)
      [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo 'Missing --python value' >&2; exit 2; }
      astra_vision_python="$2"; shift 2 ;;
    --download-models) astra_download_models=1; shift ;;
    -h|--help)
      cat <<'HELP'
Usage: scripts/setup_vision.sh [--python PATH] [--download-models]
Creates .venv-vision with PyTorch 2.10.0/CUDA 12.8 and pinned SAM3/DA3 source.
Default: install libraries only; --download-models explicitly fetches pinned
SAM 3.1 and DA3 checkpoints. SAM access requires approved Hugging Face login.
Requires Python 3.12, Git, Linux x86_64, and an NVIDIA driver supporting CUDA 12.
Run with ASTRA_HARNESS_PYTHON="$PWD/.venv-vision/bin/python" ./run.sh ...
HELP
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
"$astra_vision_python" -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 required"'
"$astra_vision_python" -m venv --copies "$astra_vision_env"
astra_pip=("$astra_vision_env/bin/python" -m pip)
"${astra_pip[@]}" install --upgrade pip 'setuptools<81' wheel
"${astra_pip[@]}" install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
"${astra_pip[@]}" install -r "$astra_root/requirements-controller.txt"
# Minimal inference dependencies; DA3's optional UI/training/3DGS stack is not used.
"${astra_pip[@]}" install -c "$astra_root/requirements-controller.txt" scipy timm 'ftfy==6.1.1' regex iopath typing_extensions \
  huggingface_hub einops omegaconf safetensors imageio trimesh evo e3nn plyfile \
  'moviepy==1.0.3' pillow_heif pycolmap addict pycocotools psutil
astra_vendor="$astra_root/artifacts/foundation_vision/vendor"
mkdir -p "$astra_vendor"
clone_pinned() {
  local source_url="$1" destination="$2" revision="$3"
  if [[ ! -e "$destination" ]]; then
    git clone --filter=blob:none "$source_url" "$destination"
  fi
  [[ -d "$destination/.git" ]] || { echo "Not a Git checkout: $destination" >&2; exit 2; }
  [[ -z "$(git -C "$destination" status --porcelain)" ]] || { echo "Refusing to replace modified vendor source: $destination" >&2; exit 2; }
  git -C "$destination" checkout --detach "$revision"
  [[ "$(git -C "$destination" rev-parse HEAD)" == "$revision" ]]
}
clone_pinned https://github.com/facebookresearch/sam3.git "$astra_vendor/sam3" f1647e8d0c1d280991f4d1b7d974c2704537fe66
clone_pinned https://github.com/ByteDance-Seed/Depth-Anything-3.git "$astra_vendor/depth-anything-3" 3d835ec1a5802d64a8b8b15f817a1ab54809bfe4
"${astra_pip[@]}" install --no-deps -e "$astra_vendor/sam3" -e "$astra_vendor/depth-anything-3"
"${astra_pip[@]}" install --no-deps -e "$astra_root"
if ((astra_download_models)); then
  "$astra_vision_env/bin/python" - "$astra_root" <<'PY_MODELS'
from pathlib import Path
import sys
from huggingface_hub import hf_hub_download, snapshot_download
root = Path(sys.argv[1]) / "artifacts/foundation_vision/models"
hf_hub_download("facebook/sam3.1", "sam3.1_multiplex.pt",
    revision="daa63191845a41281374e725f4c9e51c7a824460", local_dir=root / "sam3.1")
snapshot_download("depth-anything/DA3-LARGE-1.1",
    revision="0e109ae307c5982f319a67cf6f9f99ccdc0ec97c", cache_dir=root,
    allow_patterns=["config.json", "model.safetensors"])
PY_MODELS
fi
printf '%s\n' 'Optional vision environment installed. No models were executed.'
