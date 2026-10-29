"""Reading: python -m or001.read --stage {preflight,development} --root RUN_ROOT --selection SEL_ROOT --cpus LIST

For every environment, the two evolved genomes (seeds 0 and 1) and the four reference genomes run
6-generation chains from the same founders on the stage's blocks (tag mse-or001; development: 16
fresh blocks x 4 messages x 2 parents). Writes RUN_ROOT/read/{env}.npz with arrays
(blocks, generations + 1, genomes, cases) and a completion record. Development reading is
refused unless the design and sources equal the frozen ones and every selection output exists
under the frozen digest and is not a debug run.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from or001 import design as O  # noqa: E402
from or001 import sim  # noqa: E402

GENOMES = ("evolved_s0", "evolved_s1", *O.REFERENCES)


def genome_table(env_name, sel_root):
    rows = []
    for s in O.SEEDS:
        sel = json.loads((Path(sel_root) / "selection" / f"{env_name}_s{s}.json").read_text())
        rows.append(sel["evolved_genes"])
    rows += [O.REFERENCES[r] for r in O.REFERENCES]
    return {g: np.array([r[g] for r in rows]) for g in O.GENES}


def read_env(job):
    env_name, blocks, purpose, sel_root, root = job
    env = O.ENV[env_name]
    t0 = time.time()
    genes = genome_table(env_name, sel_root)
    acc = {}
    for b in blocks:
        cases, s0, th, p, T = sim.founders(O.TAG, env.family, env.sigma, [b], purpose, O.PARENTS)
        res = sim.chain(O.TAG, genes, cases, s0, th, p, T, env.injuries, O.G_READ)
        for k, v in res.items():
            acc.setdefault(k, []).append(v)
    arrays = {k: np.stack(v) for k, v in acc.items()}
    folder = Path(root) / "read"
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{env_name}.npz"
    tmp = folder / f".{env_name}.{os.getpid()}.tmp.npz"
    np.savez(tmp, genomes=np.array(GENOMES), genes=np.stack([genes[g] for g in O.GENES]), **arrays)
    os.replace(tmp, final)
    rec = {"env": env_name, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": O.digest(),
           "sha256": hashlib.sha256(final.read_bytes()).hexdigest(), "wall_s": round(time.time() - t0, 1),
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (folder / f"{env_name}.json").write_text(json.dumps(rec) + "\n")
    return env_name, rec["wall_s"]


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    if a.stage == "development":
        frozen = json.loads((LANE / "or001" / "frozen" / "design.json").read_text())
        now = O.sources(LANE)
        changed = sorted(k for k in set(frozen["sources"]) | set(now) if frozen["sources"].get(k) != now.get(k))
        if frozen["digest"] != O.digest() or changed:
            sys.exit(f"refusing development reading: digest or sources differ from the freeze ({changed})")
        for e in O.ENV:
            for s in O.SEEDS:
                sel = json.loads((a.selection / "selection" / f"{e}_s{s}.json").read_text())
                if sel["design_digest"] != O.digest() or sel["debug"] or sel["generations"] != O.K_GEN:
                    sys.exit(f"refusing development reading: selection output {e} s{s} is not from the frozen design")
    blocks = list(range(*O.IDENTITIES[a.stage]))
    jobs = [(e, blocks, O.PURPOSE[a.stage], str(a.selection), str(a.root)) for e in O.ENV]
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), f"{len(jobs)} environments on {len(cpus)} cpus", flush=True)
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        for e, w in pool.map(read_env, jobs):
            print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "done", e, w, "s", flush=True)


if __name__ == "__main__":
    main()
