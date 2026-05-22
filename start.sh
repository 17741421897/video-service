#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

if [[ ! -f "${ROOT}/ComfyUI/main.py" ]]; then
  echo "缺少 ${ROOT}/ComfyUI/main.py"
  exit 1
fi

PY="${VIDEO_SERVICE_PYTHON:-python3}"

ARGS=()
if [[ -n "${1:-}" ]]; then
  ARGS+=(-m "$1")
fi
exec "${PY}" "${ROOT}/run.py" "${ARGS[@]}"
