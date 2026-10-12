"""Local experiment plumbing; importing this module never writes elsewhere."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
os.environ["XDG_CACHE_HOME"] = str(ROOT / ".cache")
sys.dont_write_bytecode = True


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rng(tag, *parts):
    import numpy as np
    key = json.dumps([tag, *parts], separators=(",", ":")).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16], "little")))


def cap_cpus(count=12):
    if not 1 <= count <= 12:
        raise ValueError("CPU ceiling is 12")
    if hasattr(os, "sched_getaffinity"):
        cpus = sorted(os.sched_getaffinity(0))[:count]
        os.sched_setaffinity(0, cpus)
        return cpus
    return []


def new_run(path, inputs, contract):
    import numpy as np
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("All output must be inside this experiments tree")
    path.mkdir(parents=True, exist_ok=False)
    snapshots = path / "inputs"
    snapshots.mkdir()
    hashes = {}
    for item in inputs:
        item = Path(item).resolve()
        rel = item.relative_to(ROOT)
        dest = snapshots / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, dest)
        hashes[str(rel)] = sha(item)
    info = dict(started_utc=utc(), status="RUNNING", contract=contract,
                inputs_sha256=hashes, python=sys.version, executable=sys.executable,
                numpy=np.__version__, platform=platform.platform(),
                cpu_affinity=cap_cpus(), numerical_threads=1,
                random_generator="NumPy PCG64, SHA256 semantic stream seeds")
    dump(path / "manifest.json", info)
    return path


def check_inputs(run):
    run = Path(run)
    manifest = json.loads((run / "manifest.json").read_text())
    for rel, digest in manifest["inputs_sha256"].items():
        if sha(ROOT / rel) != digest or sha(run / "inputs" / rel) != digest:
            raise ValueError(f"Frozen input changed: {rel}")


def finish(run, started, details=None):
    import time
    check_inputs(run)
    files = {str(p.relative_to(run)): sha(p) for p in sorted(Path(run).rglob("*"))
             if p.is_file() and p.name not in ("COMPLETE.json", "FAILED.json")}
    dump(Path(run) / "COMPLETE.json", dict(status="COMPLETE", finished_utc=utc(),
         seconds=time.monotonic()-started, outputs_sha256=files, **(details or {})))


def bootstrap(values, tag):
    import numpy as np
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("Finite independent block means required")
    draws = rng(tag, "bootstrap").integers(0, len(values), (10000, len(values)))
    bounds = np.quantile(values[draws].mean(axis=1), [.025, .975])
    return dict(mean=float(values.mean()), ci95=bounds.tolist(),
                block_means=values.tolist(), positive_blocks=int((values > 0).sum()))
