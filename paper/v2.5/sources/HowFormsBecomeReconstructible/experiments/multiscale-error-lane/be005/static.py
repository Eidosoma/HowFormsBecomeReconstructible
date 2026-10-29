"""BE005's static and relaxation maps: python -m be005.static  ->  be005/frozen/static_map.json

Computed before the freeze from the design's constants alone: no tissue dynamics and no development outcome.

Anchors sit at a random quarter of the cells, as the engine draws them; a 4 x 4 patch sits at the corner (the torus is
homogeneous) and the dial's footprint is the patch dilated by 2 (be004.sim.arm_footprint for the dial). Currents are
kappa * (+1 where cue and record agree, -1 where they disagree); the steady potentials solve the cable equation (lam 3
at rest; junctions touching the footprint at lam 1 while the signal is on). 2,000 draws, one seed.

  deadline     T*(eta) = ln(1 + s0) / -ln(1 - eta) for each eta_a, and the registered delays m T*
  evidence     under the dial's conductances, the patch's anchors each repaired (agreeing again) independently with
               probability a in {0, 0.1, ..., 0.7}: the share of the patch below -theta at the signal's onset (BE004's
               static evidence curve, recomputed on this seed)
  relaxation   panel M over a legitimate 4 x 4 change (every anchor in the patch disagrees): potentials relax as
               v <- v + (v* - v) / tau_v from the pre-event steady state (every anchor agreeing), toward the signal's
               steady state while it is on and the resting one while it is off; the share of the patch whose potential
               falls below -theta at some update of the 1,000-update window, for each arm and tau_v. Steady and brief
               signals in closed form (the minimum is at the signal's last update: v*_on + (v_pre - v*_on)(1 - 1/tau)^T);
               flicker simulated with its own on/off draws.
  race         panel M over a 4 x 4 memory damage with the steady signal: the same, but the patch's anchors all repaired
               at round(T*(0.01)) = 58 updates (the arbiter's clock, every sensor at once: a lower bound on the share that
               triggers); the change's share is the upper bound (no repair)
  false alarms the steady sham over scattered corruption of a quarter of the anchors: the share of the sheet and of the
               footprint below -theta at steady state, equal for every tau_v after 1,000 updates (1 - 0.99^1000 > 0.9999)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be001.sim import cable_kernel  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from be005 import design as D  # noqa: E402

DRAWS, SEED, BATCH = 2000, 20261030, 250
EVIDENCE = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
OUT = LANE / "be005" / "frozen" / "static_map.json"


def main():
    n, th, kap = D.SIDE, D.SIG["theta"], D.KAPPA
    rng = np.random.default_rng(SEED)
    m = np.zeros((n, n), bool)
    m[:4, :4] = True
    fp = B2S.footprint(m[None], D.SIG["d"])
    gH, gW = B2S.conductances(fp, D.SIG["lam_rest"], D.SIG["lam_sig"])
    lu = B2S.factor(gH, gW)[0]
    kern = cable_kernel(D.SIG["lam_rest"])
    on_solve = lambda cur: np.stack([lu.solve(c.ravel()).reshape(n, n) for c in cur])
    off_solve = lambda cur: np.real(np.fft.ifft2(np.fft.fft2(cur) / kern))
    arms = ("dial", *(f"t{d}" for d in D.DURS), *(f"f{D.fmt(p)}" for p in D.FLICKS), "never")
    relax = {t: {a: [] for a in arms} for t in D.TAUS}
    race = {t: [] for t in D.TAUS}
    ev = {a_: [] for a_ in EVIDENCE}
    fa_all, fa_fp = [], []
    t_e = int(round(D.t_star(0.01)))
    for b0 in range(0, DRAWS, BATCH):
        nb = min(BATCH, DRAWS - b0)
        anch = np.zeros((nb, n * n), bool)
        for q in range(nb):
            anch[q, rng.permutation(n * n)[: n * n // D.DENSITY]] = True
        anch = anch.reshape(nb, n, n)
        v_pre = off_solve(kap * anch)
        cur_ev = kap * anch * np.where(m, -1.0, 1.0)
        v_on, v_off = on_solve(cur_ev), off_solve(cur_ev)
        mm = np.broadcast_to(m, v_on.shape)
        for tau in D.TAUS:
            f = 1.0 - 1.0 / tau
            for a in arms:
                if a == "never":                     # relaxes from v_pre to the resting steady state over the run
                    vmin = np.minimum(v_pre, v_off)
                elif a.startswith("f"):
                    p_on = float(a[1:])
                    v = v_pre.copy()
                    vmin = v.copy()
                    on_draw = rng.random((D.SIG["duration"], nb)) < p_on
                    for s in range(D.SIG["duration"]):
                        tgt = np.where(on_draw[s][:, None, None], v_on, v_off)
                        v = tgt if tau == 1 else v + (tgt - v) / tau
                        vmin = np.minimum(vmin, v)
                    vmin = np.minimum(vmin, v_off)       # after the window the potentials settle at rest
                else:
                    T = D.SIG["duration"] if a == "dial" else int(a[1:])
                    v_T = v_on + (v_pre - v_on) * f ** T if tau > 1 else v_on
                    vmin = np.minimum(np.minimum(v_T, v_pre), v_off)
                relax[tau][a] += (((vmin < -th) & mm).sum((-2, -1)) / 16.0).tolist()
            # the race against the arbiter: evidence until t_e, every sensor repaired after it (lower bound)
            v_te = v_on + (v_pre - v_on) * f ** t_e if tau > 1 else v_on
            race[tau] += (((np.minimum(v_te, v_pre) < -th) & mm).sum((-2, -1)) / 16.0).tolist()
        u = rng.random((nb, n, n))
        for a_ in EVIDENCE:
            sign = np.where(m, np.where(u < a_, 1.0, -1.0), 1.0)
            ev[a_] += (((on_solve(kap * anch * sign) < -th) & mm).sum((-2, -1)) / 16.0).tolist()
        s = np.ones((nb, n * n))
        for q in range(nb):
            idx = np.flatnonzero(anch[q])
            s[q, rng.permutation(idx)[: len(idx) // 4]] = -1.0
        below = on_solve(kap * anch * s.reshape(nb, n, n)) < -th
        fa_all += below.mean((-2, -1)).tolist()
        fa_fp += ((below & fp).sum((-2, -1)) / float(fp.sum())).tolist()
    res = {"note": "static and relaxation maps, no tissue dynamics; computed before the freeze from the design's constants",
           "draws": DRAWS, "seed": SEED, "design_digest": D.digest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "patch": 4, "theta": th, "t_star": {D.fmt(e): round(D.t_star(e), 3) for e in D.ETAS},
           "delays": {D.fmt(e): [D.delay(e, mm_) for mm_ in D.MULTS] for e in D.ETAS}, "mults": D.MULTS,
           "evidence": {f"{a_:.1f}": round(float(np.mean(ev[a_])), 4) for a_ in EVIDENCE},
           "relaxation": {str(t): {a: round(float(np.mean(relax[t][a])), 4) for a in arms} for t in D.TAUS},
           "race_lower_bound": {str(t): round(float(np.mean(race[t])), 4) for t in D.TAUS}, "race_t_e": t_e,
           "false_alarms": {"all": round(float(np.mean(fa_all)), 5), "footprint": round(float(np.mean(fa_fp)), 5)}}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("t_star", "delays", "evidence", "relaxation", "race_lower_bound", "false_alarms")}, indent=1))


if __name__ == "__main__":
    main()
