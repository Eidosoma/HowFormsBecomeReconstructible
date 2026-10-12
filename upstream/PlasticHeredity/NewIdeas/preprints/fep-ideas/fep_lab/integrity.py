from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(value) + b"\n")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifest(root: Path, paths: Iterable[Path]) -> dict[str, str]:
    output: dict[str, str] = {}
    for path in sorted(paths):
        resolved = path.resolve()
        output[str(resolved.relative_to(root.resolve()))] = sha256_file(resolved)
    return output


def runtime_manifest() -> dict[str, str]:
    return {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def seal_directory(directory: Path, filenames: Iterable[str]) -> dict[str, Any]:
    files = {name: sha256_file(directory / name) for name in sorted(filenames)}
    payload = {"files": files, "seal_id": sha256_bytes(canonical_json_bytes(files))}
    write_json(directory / "seal.json", payload)
    return payload


def verify_seal(directory: Path) -> bool:
    seal_path = directory / "seal.json"
    if not seal_path.is_file():
        return False
    seal = read_json(seal_path)
    files = seal.get("files", {})
    if not files:
        return False
    if any(not (directory / name).is_file() for name in files):
        return False
    actual = {name: sha256_file(directory / name) for name in sorted(files)}
    expected_id = sha256_bytes(canonical_json_bytes(actual))
    return actual == files and expected_id == seal.get("seal_id")
