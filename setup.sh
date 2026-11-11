#!/usr/bin/env bash
set -euo pipefail
package_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
controller_python="python3.12"
simulator_python="python3.10"
install_controller=1
install_simulator=1
require_value() {
  [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo "Missing value for $1" >&2; exit 2; }
}
while (($#)); do
  case "$1" in
    --python-controller) require_value "$@"; controller_python="$2"; shift 2 ;;
    --python-sim) require_value "$@"; simulator_python="$2"; shift 2 ;;
    --sim-only) install_controller=0; shift ;;
    --controller-only|--core-only) install_simulator=0; shift ;;
    -h|--help)
      cat <<'HELP'
Usage: ./setup.sh [--python-controller PATH] [--python-sim PATH]
                  [--sim-only | --core-only]
Creates project-local .venv (Python 3.12) and .venv-sim (Python 3.10).
Installs pinned controller/simulator dependencies; downloads CPU torch from
https://download.pytorch.org/whl/cpu. No credentials, model calls, or simulation.
--core-only installs only the controller; optional vision uses scripts/setup_vision.sh.
System prerequisites: Linux x86_64, Python venv support, FFmpeg, and EGL/OpenGL
runtime libraries. GPU rendering also requires a working NVIDIA driver.
HELP
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
check_python() {
  command -v "$1" >/dev/null || { echo "Python $2 is required; install it or pass an explicit --python-controller/--python-sim path." >&2; exit 2; }
  "$1" -c 'import sys; expected=tuple(map(int,sys.argv[1].split("."))); assert sys.version_info[:2] == expected, f"Expected Python {sys.argv[1]}, got {sys.version}"' "$2"
}
if ((install_controller)); then
  check_python "$controller_python" 3.12
  "$controller_python" -m venv --copies "$package_root/.venv"
  "$package_root/.venv/bin/python" -m pip install --upgrade pip
  "$package_root/.venv/bin/python" -m pip install -r "$package_root/requirements-controller.txt"
  "$package_root/.venv/bin/python" -m pip install --no-deps -e "$package_root"
fi
if ((install_simulator)); then
  check_python "$simulator_python" 3.10
  "$simulator_python" -m venv --copies "$package_root/.venv-sim"
  "$package_root/.venv-sim/bin/python" -m pip install --upgrade pip
  "$package_root/.venv-sim/bin/python" -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.10.0'
  "$package_root/.venv-sim/bin/python" -m pip install -r "$package_root/requirements-simulator.txt" -c "$package_root/provenance/simulator_resolved.lock.txt"
  # The original Pillow 12.3.0 used zlib-ng 2.3.3. The PyPI wheel has a
  # different encoder: identical pixels would fail the frozen PNG-byte hash.
  "$package_root/.venv-sim/bin/python" - "$package_root" <<'PY_CHECK_ENCODER'
import hashlib, json, pathlib, platform, sys
root = pathlib.Path(sys.argv[1])
assert sys.platform == "linux" and platform.machine() == "x86_64", "Frozen encoder requires Linux x86_64"
manifest = json.loads((root / "provenance/encoder_wheel_manifest.json").read_text())
wheel = root / "third_party/wheels/pillow-12.3.0-cp310-cp310-linux_x86_64.whl"
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == manifest["sha256"], "Encoder wheel checksum mismatch"
PY_CHECK_ENCODER
  "$package_root/.venv-sim/bin/python" -m pip install --no-deps --force-reinstall "$package_root/third_party/wheels/pillow-12.3.0-cp310-cp310-linux_x86_64.whl"
  "$package_root/.venv-sim/bin/python" -c 'from PIL import features; assert features.version("zlib") == "2.3.3", "Unexpected PNG encoder"'
fi
printf '%s\n' "Setup complete. Run ./run.sh inspect --task libero_10_t4 with the local environments."
