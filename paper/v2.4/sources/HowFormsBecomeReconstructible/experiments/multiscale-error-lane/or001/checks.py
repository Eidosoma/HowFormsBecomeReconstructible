"""Qualification of OR001; criteria fixed in advance.

python -m or001.checks --root PREFLIGHT_ROOT --cpus LIST   (writes or001/frozen/qualification_receipt.json)

The preflight root holds a debug selection (or001.select --debug, 3 generations, every
environment) and its preflight reading on engineering blocks 900972-900973.
O1  unit checks pass (tests/test_or001.py: the native genome is the engine's hold route bit for bit;
    the developmental gene acts only on newborns; gene ranges)
O2  determinism: one selection run repeated in-process gives an identical history and genome
O3  the preflight reading is complete and finite for every environment and genome
O4  the reader completes on the preflight reading, scores every statement and keeps every git
    file at 256 KB or less
O5  resources: forecast selection plus development reading <= 12 h on 16 workers
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from or001 import design as O  # noqa: E402
from or001.select import evolve  # noqa: E402

FROZEN = LANE / "or001" / "frozen"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0, checks = a.root.resolve(), time.time(), {}
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--rootdir=.", "-q", "tests/test_or001.py"],
                          cwd=LANE, capture_output=True, text=True, env=env)
    checks["O1_unit_checks"] = {"pass": proc.returncode == 0, "tail": proc.stdout[-300:]}
    rep = root / "determinism"
    shutil.rmtree(rep, ignore_errors=True)
    outs = []
    for i in range(2):
        evolve((O.PRIMARY, 0, 2, str(rep / str(i)), True))
        outs.append(json.loads((rep / str(i) / "selection" / f"{O.PRIMARY}_s0.json").read_text()))
    same = outs[0]["history"] == outs[1]["history"] and outs[0]["evolved_x"] == outs[1]["evolved_x"]
    checks["O2_determinism"] = {"pass": bool(same)}
    bad = []
    for e in O.ENV:
        path = root / "read" / f"{e}.npz"
        if not path.exists():
            bad.append(e)
            continue
        arr = dict(np.load(path))
        nb = O.IDENTITIES["preflight"][1] - O.IDENTITIES["preflight"][0]
        shape = (nb, O.G_READ + 1, 6, len(O.MESSAGES) * len(O.PARENTS))
        if any(arr[k].shape != shape or not np.isfinite(arr[k]).all() for k in ("v_qual", "v_sign", "p_sign", "dose")):
            bad.append(e)
    checks["O3_reading_complete"] = {"pass": not bad, "bad": bad[:10]}
    out = root / "analysis_dry_run"
    proc = subprocess.run([sys.executable, "-m", "or001.analyze", "--root", str(root), "--selection", str(root),
                           "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / n for n in ("genes.csv", "contrasts.csv", "summary.json", "statements_scored.json")]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "statements_scored.json").read_text()) if expected[3].exists() else {}
    sizes = {p.name: p.stat().st_size for p in expected if p.exists()}
    checks["O4_reader_dry_run"] = {"pass": proc.returncode == 0 and all(p.exists() for p in expected) and set(got) == set(stmts)
                                   and max(sizes.values(), default=0) <= 262144, "sizes": sizes, "stderr": proc.stderr[-600:]}
    per_gen = np.mean([h["wall_s"] / h["generations"] for h in outs]) if outs else 10.0
    walls = [json.loads((root / "read" / f"{e}.json").read_text())["wall_s"] for e in O.ENV if (root / "read" / f"{e}.json").exists()]
    sel_h = per_gen * O.K_GEN * len(O.ENVS) * len(O.SEEDS) / 16 / 3600
    nb_dev = O.IDENTITIES["development"][1] - O.IDENTITIES["development"][0]
    read_h = (np.mean(walls) if walls else 60.0) * nb_dev / 2 * len(O.ENVS) / 16 / 3600
    checks["O5_resources"] = {"pass": bool(sel_h + read_h <= 12), "selection_h_16": round(float(sel_h), 2), "reading_h_16": round(float(read_h), 2)}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": O.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    (FROZEN / "qualification_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
