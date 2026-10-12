#!/usr/bin/env bash
set -euo pipefail
lane_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lane_python="${FORMS_PYTHON:-${lane_root}/../../../PlasticHeredity/replicators.13.8.2026.codex/.venv/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR="${lane_root}/.cache/matplotlib"
export XDG_CACHE_HOME="${lane_root}/.cache"
exec "${lane_python}" -B "$@"
