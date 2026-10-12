"""Small, deterministic artifact helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        # ``tolist`` can contain ordinary Python ``nan``/``inf`` leaves.
        # Recurse so invalid numerical trajectories remain representable in
        # strict JSON as nulls instead of aborting the campaign.
        return json_ready(value.tolist())
    if isinstance(value, np.generic):
        return json_ready(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        json_ready(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(json_ready(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
    )


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(canonical_json(record))
            handle.write("\n")
            count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return count


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_checksums(directory: Path) -> None:
    manifest = directory / "SHA256SUMS"
    paths = sorted(
        path for path in directory.rglob("*") if path.is_file() and path != manifest
    )
    atomic_write_text(
        manifest,
        "".join(
            f"{sha256_file(path)}  {path.relative_to(directory)}\n" for path in paths
        ),
    )


def verify_checksums(directory: Path) -> dict[str, bool]:
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        raise FileNotFoundError(f"missing checksum manifest: {manifest}")
    verdicts: dict[str, bool] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        target = directory / relative
        verdicts[relative] = target.is_file() and sha256_file(target) == expected
    if not verdicts or not all(verdicts.values()):
        failed = [name for name, valid in verdicts.items() if not valid]
        raise ValueError(f"checksum verification failed: {failed}")
    return verdicts
