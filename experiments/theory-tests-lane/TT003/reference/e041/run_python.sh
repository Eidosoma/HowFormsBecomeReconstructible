#!/usr/bin/env bash
set -euo pipefail
forms_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
forms_python="${FORMS_PYTHON:-${forms_root}/../../PlasticHeredity/replicators.13.8.2026.codex/.venv/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR="${forms_root}/.cache/matplotlib"
export XDG_CACHE_HOME="${forms_root}/.cache"
exec "${forms_python}" -B "$@"
