#!/usr/bin/env bash
set -euo pipefail
forms_public_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
forms_public_python="${FORMS_PYTHON:-${forms_public_root}/.venv/bin/python}"
if [[ ! -x "${forms_public_python}" ]]; then
  forms_public_python="$(command -v python3)"
fi
export FORMS_PYTHON="${forms_public_python}"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-${forms_public_root}/.cache/matplotlib}"
mkdir -p -- "${MPLCONFIGDIR}"
cd "${forms_public_root}"
exec "${forms_public_python}" -B "$@"
