"""Selection: python -m or001.select --root RUN_ROOT --cpus LIST [--envs a,b] [--generations K] [--debug]

One antithetic evolution-strategies run per (environment, seed), from the near-zero genome X0.
Generation k evaluates POP genomes (x +- SIGMA_ES eps, eps addressed by (env, seed, k)) on one
batch of founders, noise and injuries drawn through tag mse-or001-s{seed}-sel{k} on engineering
blocks (common random numbers within a generation, fresh ones across generations). Fitness:
or001.sim.fitness. Update: centred-rank utilities, antithetic gradient estimate, step ALPHA_k
decaying linearly from ALPHA to ALPHA / 4. The evolved genome is the mean of x over the last 10
generations. Writes RUN_ROOT/selection/{env}_s{seed}.json (history and evolved genome).
--debug uses tag mse-or001-debug and is for plumbing only.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from mse.native import address  # noqa: E402
from or001 import design as O  # noqa: E402
from or001 import sim  # noqa: E402


def evolve(job):
    env_name, seed, K, root, debug = job
    env = O.ENV[env_name]
    t0 = time.time()
    x = np.array(O.X0, float)
    half = O.POP // 2
    lo, hi = O.IDENTITIES["selection"]
    hist, xs = [], []
    for k in range(K):
        tag = f"{O.TAG}-debug-s{seed}-sel{k}" if debug else f"{O.TAG}-s{seed}-sel{k}"
        cases, s0, th, p, T = sim.founders(tag, env.family, env.sigma, list(range(lo, hi)), "engineering", O.SEL_PARENTS)
        eps = address(O.TAG, "es", env.name, seed, k).standard_normal((half, len(O.GENES)))
        X = np.concatenate([x + O.SIGMA_ES * eps, x - O.SIGMA_ES * eps])
        res = sim.chain(tag, O.decode(X), cases, s0, th, p, T, env.injuries, O.G_SEL)
        F = sim.fitness(res, env.cost)
        u = np.argsort(np.argsort(F)) / (O.POP - 1) - 0.5
        grad = ((u[:half] - u[half:])[:, None] * eps).sum(0) / (half * O.SIGMA_ES)
        alpha = O.ALPHA * (1 - 0.75 * k / max(K - 1, 1))
        hist.append({"k": k, "x": [round(float(v), 5) for v in x], "genes": {g: round(float(v), 6) for g, v in O.decode(x).items()},
                     "fitness_mean": round(float(F.mean()), 5), "fitness_max": round(float(F.max()), 5),
                     "v_qual_mean": round(float(res["v_qual"][1:].mean()), 5), "dose_mean": round(float(res["dose"].mean()), 1)})
        xs.append(x.copy())
        x = x + alpha * grad
    final = np.mean(xs[-10:], axis=0)
    out = {"env": env_name, "seed": seed, "generations": K, "debug": debug, "design_digest": O.digest(),
           "evolved_x": [float(v) for v in final], "evolved_genes": {g: float(v) for g, v in O.decode(final).items()},
           "history": hist, "wall_s": round(time.time() - t0, 1)}
    path = Path(root) / "selection" / f"{env_name}_s{seed}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(out) + "\n")
    os.replace(tmp, path)
    return env_name, seed, out["wall_s"]


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--envs", default="all")
    ap.add_argument("--generations", type=int, default=O.K_GEN)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    if not a.debug:
        frozen = json.loads((LANE / "or001" / "frozen" / "design.json").read_text())
        now = O.sources(LANE)
        changed = sorted(k for k in set(frozen["sources"]) | set(now) if frozen["sources"].get(k) != now.get(k))
        if frozen["digest"] != O.digest() or changed or a.generations != O.K_GEN:
            sys.exit(f"refusing selection: digest or sources differ from the freeze ({changed}) or generations changed")
    envs = list(O.ENV) if a.envs == "all" else a.envs.split(",")
    jobs = [(e, s, a.generations, str(a.root), a.debug) for e in envs for s in O.SEEDS
            if not (a.root / "selection" / f"{e}_s{s}.json").exists()]
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), f"{len(jobs)} selection runs on {len(cpus)} cpus", flush=True)
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        for e, s, w in pool.map(evolve, jobs):
            print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "done", e, s, w, "s", flush=True)


if __name__ == "__main__":
    main()
