#!/usr/bin/env bash
set -euo pipefail
ASTRA_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ASTRA_INTERPRETER="${ASTRA_HARNESS_PYTHON:-${ASTRA_ROOT}/.venv/bin/python}"
if [[ ! -x "$ASTRA_INTERPRETER" ]]; then
  echo "Controller environment missing. Run: ${ASTRA_ROOT}/setup.sh" >&2
  exit 2
fi
export PYTHONPATH="${ASTRA_ROOT}/src"
export PYTHONDONTWRITEBYTECODE=1
export GPT_FIELD_USER_CHECK_TRANSIT_ACTION_M=0.10
exec "$ASTRA_INTERPRETER" "${ASTRA_ROOT}/scripts/launch.py" "$@"
