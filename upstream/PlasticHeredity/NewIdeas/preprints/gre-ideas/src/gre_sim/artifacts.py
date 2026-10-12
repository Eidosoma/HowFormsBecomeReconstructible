"""Immutable, checksummed GRE run artifacts."""

from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import shutil
import tempfile
from contextlib import contextmanager
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
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        json_ready(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(json_ready(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl_gz(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                for record in records:
                    text.write(canonical_json(record).decode("utf-8"))
                    text.write("\n")
                    count += 1
    return count


def read_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


@contextmanager
def atomic_destination(destination: Path) -> Iterator[Path]:
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.preparing-", dir=destination.parent)
    )
    try:
        yield temporary
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite {destination}")
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def write_checksums(directory: Path) -> None:
    manifest = directory / "SHA256SUMS"
    files = sorted(
        path for path in directory.rglob("*") if path.is_file() and path != manifest
    )
    manifest.write_text(
        "".join(
            f"{sha256_file(path)}  {path.relative_to(directory)}\n" for path in files
        ),
        encoding="ascii",
    )


def verify_checksums(directory: Path) -> dict[str, bool]:
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        raise FileNotFoundError(f"missing checksum manifest: {manifest}")
    results: dict[str, bool] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        target = directory / relative
        results[relative] = target.is_file() and sha256_file(target) == expected
    if not results or not all(results.values()):
        failed = [name for name, valid in results.items() if not valid]
        raise ValueError(f"checksum verification failed: {failed}")
    return results


def runtime_manifest() -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in ("numpy", "numba", "scipy", "matplotlib", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not-installed"
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": packages,
    }

