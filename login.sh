#!/usr/bin/env bash
set -euo pipefail
astra_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
astra_python="${ASTRA_HARNESS_PYTHON:-${astra_root}/.venv/bin/python}"
if [[ ! -x "$astra_python" ]]; then
  echo "Run ./setup.sh --core-only first." >&2
  exit 2
fi
export PYTHONPATH="${astra_root}/src"
export PYTHONDONTWRITEBYTECODE=1
exec "$astra_python" "${astra_root}/scripts/chatgpt_plan_login.py" "$@"
