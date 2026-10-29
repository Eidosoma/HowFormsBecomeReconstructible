"""Deterministic artifact, manifest, seeding, and progress helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
        os.replace(name, path)
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(name, path)
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(name, path)
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def environment_manifest() -> dict[str, Any]:
    import scipy

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }


def seed_rng(tag: str, *parts: int) -> np.random.Generator:
    digest = hashlib.sha256((tag + ":" + ":".join(map(str, parts))).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


def hash_fraction(tag: str, value: int) -> float:
    """Deterministic uniform-in-[0,1) hash used for dev/eval splits."""
    digest = hashlib.sha256(f"{tag}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], "little") / 2**64


def progress(path: Path, *, stage: str, completed: int, total: int, started: float) -> None:
    elapsed = time.time() - started
    fraction = completed / total if total else 1.0
    eta = elapsed * (1.0 - fraction) / fraction if fraction > 0 else None
    atomic_json(
        path,
        {
            "stage": stage,
            "completed": completed,
            "total": total,
            "fraction": fraction,
            "elapsed_seconds": elapsed,
            "eta_seconds": eta,
            "updated_unix": time.time(),
        },
    )


def write_checksums(root: Path, output: Path, *, exclude: tuple[str, ...] = ("SHA256SUMS",)) -> None:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name in exclude or path.suffix == ".tmp":
            continue
        rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")


def valid_npz(path: Path, digest: str, required: tuple[str, ...]) -> bool:
    if not path.exists():
        return False
    try:
        with np.load(path, allow_pickle=False) as data:
            if str(data.get("config_digest", "")) != digest:
                return False
            return all(key in data for key in required)
    except Exception:
        return False
