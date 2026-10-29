"""Output isolation and reproducibility helpers.

Historical experiment directories are inputs only. Every generated artefact is
forced under the user-designated /mnt/bioIce1 tree.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any, Iterable


DEFAULT_EXTERNAL_ROOT = Path(
    "/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation"
)
ALLOWED_MOUNT = Path("/mnt/bioIce1")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def external_root(value: str | Path | None = None) -> Path:
    root = Path(value) if value is not None else DEFAULT_EXTERNAL_ROOT
    resolved = root.expanduser().resolve()
    allowed = ALLOWED_MOUNT.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError(f"generated artefacts must stay beneath {allowed}: {resolved}")
    if not resolved.is_dir():
        raise FileNotFoundError(f"external output root does not exist: {resolved}")
    return resolved


def require_beneath(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root = root.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing output outside external root {root}: {resolved}")
    return resolved


def atomic_text(path: Path, text: str, root: Path) -> None:
    target = require_beneath(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, value: Any, root: Path) -> None:
    atomic_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        root,
    )


def write_hash_manifest(paths: Iterable[Path], destination: Path, root: Path) -> None:
    unique = sorted({path.resolve() for path in paths})
    rows = [f"{sha256_file(path)}  {path}" for path in unique]
    atomic_text(destination, "\n".join(rows) + "\n", root)


def git_head(path: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def environment_manifest() -> dict[str, Any]:
    try:
        import numpy as np

        numpy_version = np.__version__
    except Exception:
        numpy_version = None
    return {
        "python": sys.version,
        "numpy": numpy_version,
        "platform": platform.platform(),
        "cpu_count_visible": os.cpu_count(),
        "thread_limits": {
            key: os.environ.get(key)
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
        "tmpdir": os.environ.get("TMPDIR"),
        "xdg_cache_home": os.environ.get("XDG_CACHE_HOME"),
        "python_pycache_prefix": os.environ.get("PYTHONPYCACHEPREFIX"),
    }

