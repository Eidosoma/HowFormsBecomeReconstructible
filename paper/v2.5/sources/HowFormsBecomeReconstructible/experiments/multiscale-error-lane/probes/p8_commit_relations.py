"""Engineering probe P8 (python probes/p8_commit_relations.py CPUS): commitment and relations.
ENGINEERING_PROBE_NOT_EVIDENCE; a design input for BR002, run after BR001's development read.

Part A, committed writing. BR001's mismatch-gated writers stall short of the bistable record's barrier when
the threshold is high (the stall inequality in THEORY.md: a region commits only if phi > sqrt(theta)/A).
Here a hysteresis gate opens as BR001's does (mismatch above theta and the rule's own condition) and closes
only when the region mismatch falls below 0.05 theta. Does adoption of a lasting change become complete at
sigma 0.3, and what do the rules then do with scars and transients?

Part B, a relational record. Consensus erased BL's fine detail. Bonds J_ij = sign(R0_i) sign(R0_j), the
Mattis gauge of the consensus rule, store the pattern in the relations between neighbours:
    r <- r + eps [ f(r) + kr (sum_j J_ij r_j / 4 - r) ] + sigma_r xi        (+ the coarse code, optional)
With J = 1 this is BR001's consensus rule exactly. Does BL keep its detail and heal small wounds, are newborn
cells re-specified under turnover (bonds survive turnover), and what happens when a lesion kills cells and
the bonds between them (kill: record 0, newborn states, bonds with both ends in the patch lost)?

Engineering blocks 900820-900823 (32 cases) under BR001's tag, with br001/sim.py unchanged for acquisition,
the body step, events and scoring; panel P thresholds from br001/frozen/calibration.json.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from br001 import design as D  # noqa: E402
from br001 import sim  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from mse.ops import block_projection  # noqa: E402

BLOCKS = list(range(900820, 900824))
OFF = 0.05
CAL = json.loads((LANE / "br001" / "frozen" / "calibration.json").read_text())["regimes"]
OUT = LANE / "probes" / "results" / "p8_commit_relations_v1.json"


@dataclass(frozen=True)
class Arm:
    name: str
    eps: float = 0.0
    kc: float = 0.0
    rel: bool = False         # bonds from the taught record's signs (False: J = 1, BR001's consensus)
    clamp: bool = False
    write: str = "none"       # none | always | duration | tags | phase
    hyst: bool = False        # the write gate, once open, stays open until mismatch < OFF x theta


@dataclass(frozen=True)
class Cond:
    name: str
    kind: str = "sham"        # sham | lesion (body and record flipped) | kill | turnover | scar | record | impose
    size: int = 0
    duration: int = 0
    cue: bool = False
    rate: float = 0.0


ARMS_A = (Arm("none", eps=D.EPS),
          *(Arm(f"{w}{'+h' if h else ''}", eps=D.EPS, write=w, hyst=h) for w in ("always", "duration", "tags")
            for h in (False, True)),
          Arm("phase", eps=D.EPS, write="phase"))
COND_A = (Cond("sham"), Cond("scar-6x6", "scar", 6), Cond("record-6x6", "record", 6),
          Cond("impose-inf-cued", "impose", cue=True), Cond("impose-inf", "impose"),
          Cond("impose-300", "impose", duration=300))
REG_A = (D.regime("F0", 0.1), D.regime("F0", 0.3), D.regime("F0", 0.1, "o"), D.regime("F0", 0.3, "o"))

ARMS_B = (Arm("static"), Arm("self", eps=D.EPS), Arm("multi", eps=D.EPS, kc=D.KC), Arm("rel", eps=D.EPS, rel=True),
          Arm("rel+code", eps=D.EPS, kc=D.KC, rel=True), Arm("protected", clamp=True))
COND_B = (Cond("sham"), *(Cond(f"both-{s}x{s}", "lesion", s) for s in (2, 4, 6, 8)),
          Cond("kill-4x4", "kill", 4), Cond("kill-8x8", "kill", 8), Cond("turnover-0.003", "turnover", rate=3e-3))
REG_B = (D.regime("F0", 0.1), D.regime("BL", 0.1), D.regime("BL", 0.3))

SHIFTS = ((1, -2), (-1, -2), (1, -1), (-1, -1))       # the four neighbours, in mse.native.neighbours' order


def bonds(R0, rel):
    if not rel:
        return [np.ones_like(R0) for _ in SHIFTS]
    s = np.where(R0 >= 0, 1.0, -1.0)
    return [s * np.roll(s, sh, ax) for sh, ax in SHIFTS]


def bond_sum(J, r):
    """sum_j J_ij r_j / 4, summed in neighbours' order so that J = 1 reproduces it bit for bit."""
    return (J[0] * np.roll(r, 1, -2) + J[1] * np.roll(r, -1, -2) + J[2] * np.roll(r, 1, -1) + J[3] * np.roll(r, -1, -1)) / 4.0


def simulate8(arm, conds, k, V, ema, R, th, Z, XI, p, conserved, T, Tf, tau, masks, turn, newborn, cal):
    nc = len(conds)
    n = nc * k
    idx = np.tile(np.arange(k), nc)
    thb, Tb, Tfb, taub = th[idx], T[idx], Tf[idx], np.tile(tau, nc)
    mask = np.concatenate([masks[c] if masks[c] is not None else np.zeros((k, 16, 16), bool) for c in range(nc)])
    nb = np.concatenate([newborn[c] if newborn[c] is not None else np.zeros((k, 16, 16)) for c in range(nc)])
    kind = np.repeat([c.kind for c in conds], k)
    dur = np.repeat([c.duration for c in conds], k)
    cue = np.repeat([c.cue for c in conds], k)
    R0b = R[idx]
    B = block_projection(R, 4)[idx]
    J = bonds(R0b, arm.rel)
    v, e, r = V[idx].copy(), ema[idx].copy(), R[idx].copy()
    tag = np.zeros((n, 16, 16))
    latch = np.zeros((n, 16, 16), int)
    opened = np.zeros((n, 16, 16), bool)
    w_l1 = np.zeros(n)
    imp_stop = np.where(dur > 0, taub + dur, D.WINDOW + 1)
    win_stop = taub + D.WINDOW_P
    for t in range(1, D.WINDOW + 1):
        start = taub == t
        if start.any():
            m3 = mask & start[:, None, None]
            both = m3 & (kind == "lesion")[:, None, None]
            v, r = np.where(both, -v, v), np.where(both, -r, r)
            r = np.where(m3 & (kind == "record")[:, None, None], -r, r)
            kill = m3 & (kind == "kill")[:, None, None]
            if kill.any():
                v, e, r = np.where(kill, nb, v), np.where(kill, nb, e), np.where(kill, 0.0, r)
                for d, (sh, ax) in enumerate(SHIFTS):
                    J[d] = np.where(kill & np.roll(kill, sh, ax), 0.0, J[d])
            tag = np.where(m3 & (kind == "scar")[:, None, None], 1.0, tag)
        scar = (kind == "scar") & (t >= taub)
        if scar.any():
            m3 = mask & scar[:, None, None]
            v = np.where(m3, -Tb, v)
            tag = np.where(m3, 1.0, tag)
        imp = (kind == "impose") & (t >= taub) & (t < imp_stop)
        if imp.any():
            v = np.where(imp[:, None, None], Tfb, v)
        v, e, vt = sim.body_step(v, e, r, thb, Z[t - 1][idx], p, conserved, NATIVE.gain)
        gate = None
        if arm.write == "phase":
            gate = np.broadcast_to((cue & (t >= taub) & (t < win_stop))[:, None, None], v.shape)
        elif arm.write != "none":
            mm = sim.region(r - vt)
            mis = mm > cal["mismatch"]
            if arm.write == "duration":
                latch = np.where(sim.region(vt - e) > cal["surprise"], D.LATCH_W, np.maximum(latch - 1, 0))
                ok = latch == 0
            elif arm.write == "tags":
                ok = tag < D.TAG_GATE
            else:
                ok = np.ones_like(mis)
            if arm.hyst:
                opened = (opened & (mm > OFF * cal["mismatch"])) | (mis & ok)
                gate = opened & (tag < D.TAG_GATE) if arm.write == "tags" else opened
            else:
                gate = mis & ok
        tag = tag * (1.0 - D.TAG_DECAY)
        r_old = r
        if arm.eps > 0:
            r = r + arm.eps * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r)) + D.SIGMA_R * XI[t - 1][idx]
        if arm.kc > 0:
            r = r + arm.kc * (B - block_projection(r, 4))
        if gate is not None:
            dw = D.RHO_W * gate * (v - r)
            w_l1 += np.abs(dw).sum(axis=(-2, -1))
            r = r + dw
        r = np.clip(r, -2.0, 2.0) if r is not r_old else r
        if arm.clamp:
            r = R0b.copy()
        if turn is not None:
            for ci in range(nc):
                if turn[ci] is None:
                    continue
                for j in range(k):
                    tt, site, val = turn[ci][j]
                    lo, hi = np.searchsorted(tt, t, "left"), np.searchsorted(tt, t, "right")
                    if hi > lo:
                        b = ci * k + j
                        ii, jj = np.divmod(site[lo:hi], 16)
                        v[b, ii, jj] = val[lo:hi]
                        e[b, ii, jj] = val[lo:hi]
                        r[b, ii, jj] = 0.0
    return v, r, w_l1


def task(args):
    part, name, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    conds, arms = (COND_A, ARMS_A) if part == "A" else (COND_B, ARMS_B)
    cases, s0, th, p, conserved, T, Tf = sim.prepare(name, [block], "engineering")
    k, nc = len(cases), len(conds)
    idx = np.tile(np.arange(k), nc)
    Tb, Tfb = T[idx], Tf[idx]
    tau = sim.onsets(cases, "random" if part == "A" else "start")
    masks = [sim.patch_masks(cases, c.size) if c.size else None for c in conds]
    turn = [sim.turnover_events(cases, c.rate, D.WINDOW) if c.kind == "turnover" else None for c in conds]
    newborn = [np.stack([0.2 * address(D.TAG, *cs.key(), "p8-kill", f"{c.size}").standard_normal((16, 16)) for cs in cases])
               if c.kind == "kill" else None for c in conds]
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    mask = np.concatenate([m if m is not None else np.zeros((k, 16, 16), bool) for m in masks])
    flip = np.sign(Tfb) != np.sign(Tb)
    out = {}
    for arm in arms:
        v, r, w = simulate8(arm, conds, k, s0.V, s0.ema, s0.R, th, Z, XI, p, conserved, T, Tf, tau, masks, turn,
                            newborn, CAL.get(name) if part == "A" else None)
        res = {"v_qual": sim.qual(v, Tb), "r_sign": sim.sign(r, Tb), "les_r": sim.masked_sign(r, Tb, mask), "w_l1": w}
        if part == "A":
            res["rg_sign"] = sim.sign(r, Tfb)
            res["adopt_flip"] = (((r > 0) == (Tfb > 0)) & flip).sum((-2, -1)) / flip.sum((-2, -1))
        out[arm.name] = {kk: np.asarray(vv, float).reshape(nc, k).mean(1).tolist() for kk, vv in res.items()}
    return part, name, block, out, round(time.time() - t0, 1)


def equivalence(block=BLOCKS[0]):
    """With J = 1 and no hysteresis, simulate8 must equal br001.sim.simulate bit for bit."""
    out = {}
    for name, mine, theirs, arms in (
            (D.regime("F0", 0.3), COND_A[:4], D.COND_P[:1] + D.COND_P[2:5], ("none", "always", "duration", "tags")),
            (D.regime("BL", 0.1), COND_B[:3], D.COND_L[:3], ("self", "multi"))):
        cases, s0, th, p, conserved, T, Tf = sim.prepare(name, [block], "engineering")
        k = len(cases)
        part_a = mine[1].kind == "scar"
        tau = sim.onsets(cases, "random" if part_a else "start")
        masks = [sim.patch_masks(cases, c.size) if c.size else None for c in mine]
        Z = sim.draws(cases, "future", updates=D.WINDOW)
        XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
        cal = CAL.get(name) if part_a else None
        for a in arms:
            arm8 = next(x for x in (ARMS_A if part_a else ARMS_B) if x.name == a)
            ref = D.ARM["P"][f"write_{a}"] if part_a else D.ARM["L"][a]
            v, r, _ = simulate8(arm8, mine, k, s0.V, s0.ema, s0.R, th, Z, XI, p, conserved, T, Tf, tau, masks,
                                [None] * len(mine), [None] * len(mine), cal)
            v2, _, r2, _ = sim.simulate(ref, theirs, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf, tau,
                                        masks, [None] * len(theirs), cal)
            out[f"{name}/{a}"] = bool(np.array_equal(v, v2) and np.array_equal(r, r2))
    return out


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    jobs = [("A", r, b) for r in REG_A for b in BLOCKS] + [("B", r, b) for r in REG_B for b in BLOCKS]
    t0 = time.time()
    os.sched_setaffinity(0, cpus[:1])
    eq = equivalence()
    print("equivalence with br001.sim.simulate:", eq)
    if not all(eq.values()):
        raise SystemExit("simulate8 differs from br001.sim.simulate; stopping")
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        results = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    agg = {}
    for part, name, block, out, wall in results:
        for arm, eps in out.items():
            for ep, vals in eps.items():
                agg.setdefault(part, {}).setdefault(name, {}).setdefault(arm, {}).setdefault(ep, []).append(vals)
    summary = {}
    for part, regs in agg.items():
        conds = [c.name for c in (COND_A if part == "A" else COND_B)]
        for name, arms in regs.items():
            for arm, eps in arms.items():
                for ep, blocks in eps.items():
                    x = np.array(blocks)                                # (blocks, conditions)
                    m, h = x.mean(0), 3.182 * x.std(0, ddof=1) / np.sqrt(len(x))
                    summary.setdefault(part, {}).setdefault(name, {}).setdefault(arm, {})[ep] = {
                        c: [round(float(m[i]), 4), round(float(h[i]), 4)] for i, c in enumerate(conds)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"probe": "P8", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "blocks": BLOCKS, "off": OFF,
                               "equivalence_with_br001_sim": eq,
                               "arms": {"A": [asdict(a) for a in ARMS_A], "B": [asdict(a) for a in ARMS_B]},
                               "conditions": {"A": [asdict(c) for c in COND_A], "B": [asdict(c) for c in COND_B]},
                               "values": "block mean over 8 cases each, then mean and t(3) half-width over 4 blocks",
                               "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(r[4] for r in results), 1),
                               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "summary": summary}, indent=1) + "\n")
    for part, eps_show in (("A", ("adopt_flip", "rg_sign", "les_r", "r_sign", "w_l1")), ("B", ("les_r", "r_sign", "v_qual"))):
        conds = [c.name for c in (COND_A if part == "A" else COND_B)]
        for name, arms in summary[part].items():
            for ep in eps_show:
                print(f"\n{part} {name} {ep}: " + " | ".join(conds))
                for arm, d in arms.items():
                    print(f"  {arm:12s} " + " ".join(f"{d[ep][c][0]:7.3f}" for c in conds))
    print(f"\nwrote {OUT} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
