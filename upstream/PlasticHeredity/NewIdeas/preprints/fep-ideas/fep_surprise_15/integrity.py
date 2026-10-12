from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_checksums(directory: Path) -> None:
    target = directory / "SHA256SUMS"
    paths = sorted(path for path in directory.rglob("*") if path.is_file() and path != target)
    target.write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(directory)}\n" for path in paths),
        encoding="ascii",
    )


def verify_checksums(directory: Path) -> dict[str, bool]:
    target = directory / "SHA256SUMS"
    if not target.is_file():
        raise FileNotFoundError(target)
    results: dict[str, bool] = {}
    for line in target.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        path = directory / relative
        results[relative] = path.is_file() and sha256_file(path) == expected
    if not results or not all(results.values()):
        invalid = [name for name, valid in results.items() if not valid]
        raise ValueError(f"checksum verification failed: {invalid}")
    return results


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
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

