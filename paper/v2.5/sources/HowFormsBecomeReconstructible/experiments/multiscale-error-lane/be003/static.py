"""BE003's static map: python -m be003.static  ->  be003/frozen/static_map.json

Computed before the freeze from the design's constants alone, with no tissue dynamics and no development outcome. The
population's history does not depend on any arm: an 8 x 8 wound regrows by cellpop.core.divide at P_REGROW from its rim,
and the contacts age as in be003.sim (age 0 when a newborn touches them, +1 each update). DRAWS regrowth histories from
one seed (the wound's corner fixed: the torus is homogeneous), each with its own anchors (a random quarter of the sites).
  births        each newborn's occupied neighbours at its first update, and the share of newborns whose total junction
                conductance then is below G* = (kappa - theta) / (1 + theta) (THEORY 8.9: a disagreeing anchored cell
                among agreeing cells at v = 1 triggers alone): every newborn under maturing junctions (no conductance at
                age 0), those with fewer than G* / lam^2 neighbours under instant ones (the signal's lam_sig = 1 while it
                is on);
  adoption      at each delay d of the twin runs (the wound refilled), the share of each 4 x 4 patch whose potential is
                below -theta when the cue of both patches disagrees with the record and every other anchor agrees, with
                each arm's conductances at d (the signal arms with the change's signal on: lam_sig^2 m on the contacts
                touching the wound and the twin's 8 x 8);
  false alarms  after updates 250, 750 and 2,000 of a regrowing wound with a quarter of the anchors corrupted
                (scattered), the share of cells below -theta in the wound, its ring and outside, with each arm's
                conductances then (the injury signal on at the next update for 250 and 750: lam_sig^2 m on the contacts
                touching the wound dilated by 2; off for 2,000);
  maturity      the mean maturity of the wound's contacts and of the young patch's at each time.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be002.sim import footprint  # noqa: E402
from be003 import design as D  # noqa: E402
from be003 import sim  # noqa: E402
from cellpop import core as C  # noqa: E402
from sc002 import sim as S2  # noqa: E402
from sc002 import theory as TH  # noqa: E402
from sc002.cable import Cable  # noqa: E402

DRAWS, BATCH, SEED = 1024, 128, 20261029
OUT = LANE / "be003" / "frozen" / "static_map.json"
TIMES_FA = (250, 750, 2000)
N = D.SIDE


def geometry():
    wound = np.zeros((N, N), bool)
    wound[:D.WOUND, :D.WOUND] = True
    young = np.zeros((N, N), bool)
    o = D.YOUNG_OFFSET
    young[o:o + D.PATCH, o:o + D.PATCH] = True
    twin = np.roll(young, D.TWIN_SHIFT, -1)
    fw, ft = footprint(wound[None], D.SIG["d"])[0], footprint(twin[None], D.SIG["d"])[0]
    return {"in": wound, "young": young, "twin": twin, "ring": fw & ~wound, "out": ~(fw | ft),
            "fp_injury": fw, "fp_change": footprint((young | twin)[None], D.SIG["d"])[0]}


def regrow(rng, k, until):
    """k regrowth histories to update `until`: occupancy and contact ages after each update's divisions, newborns'
    neighbour counts at their first update, and each history's fill time."""
    g = geometry()
    occ = np.broadcast_to(~g["in"], (k, N, N)).copy()
    aH, aW = np.full((k, N, N), np.inf), np.full((k, N, N), np.inf)
    zero = np.zeros((k, N, N))
    nbrs, snaps, fill = [], {}, np.full(k, -1)
    for t in range(1, until + 1):
        st = {"occ": occ, "V": zero, "E": zero, "r": zero}
        st, born = C.divide(st, D.P_REGROW, rng.random((k, N, N)), rng.random((k, N, N)), True)
        occ = st["occ"]
        nh, nw = C.touching(born)
        aH, aW = np.where(nh, 0.0, aH + 1.0), np.where(nw, 0.0, aW + 1.0)
        if born.any():
            cnt = sum(C.at(occ, d).astype(int) for d in range(4))
            nbrs.extend(cnt[born].tolist())
        full = occ.all((-2, -1))
        fill = np.where((fill < 0) & full, t, fill)
        if t in snaps_wanted(until):
            snaps[t] = (occ.copy(), aH.copy(), aW.copy())
    return snaps, np.array(nbrs), fill


def snaps_wanted(until):
    return set(TIMES_FA) | set(d for d in D.DELAYS if d > 0) | {until}


def conductances(arm, occ, aH, aW, fp=None):
    return sim.conductance(arm, aH, aW, occ, C.touching(np.broadcast_to(fp, occ.shape)) if fp is not None else None)


def below(cab, I, gH, gW):
    v = cab.solve(I, gH, gW, np.zeros_like(I), tol=1e-12)[0]
    return v < -D.THETA


def main():
    rng = np.random.default_rng(SEED)
    g = geometry()
    arms = [a for a in D.ARMS if a != "cue"]
    gstar = TH.g_star(D.THETA)
    delays = [d for d in D.DELAYS if d > 0]
    until = max(max(delays), max(TIMES_FA))
    adopt = {a: {str(d): {"young": [], "twin": []} for d in delays} for a in arms}
    fa = {a: {str(t): {x: [] for x in ("in", "ring", "out")} for t in TIMES_FA} for a in arms}
    mat = {a: {str(t): {"in": [], "young": []} for t in sorted(set(TIMES_FA) | set(delays))}
           for a in arms if D.JUNCTIONS[a]["tau_m"] > 0}
    nb_all, fills = [], []
    cab = Cable(BATCH)
    for _ in range(DRAWS // BATCH):
        snaps, nbrs, fill = regrow(rng, BATCH, until)
        nb_all.append(nbrs)
        fills.append(fill)
        anch = np.zeros((BATCH, N * N), bool)
        for j in range(BATCH):
            anch[j, rng.permutation(N * N)[: N * N // D.DENSITY]] = True
        anch = anch.reshape(BATCH, N, N)
        bad = np.zeros((BATCH, N * N), bool)
        for j in range(BATCH):
            idx = np.flatnonzero(anch[j].ravel())
            bad[j, idx[rng.permutation(len(idx))[: len(idx) // 4]]] = True
        bad = bad.reshape(BATCH, N, N)
        for t in sorted(snaps):
            occ, aH, aW = snaps[t]
            for a in mat:
                tau = D.JUNCTIONS[a]["tau_m"]
                for x in ("in", "young"):
                    m = np.broadcast_to(g[x], occ.shape)
                    if str(t) in mat[a]:
                        mat[a][str(t)][x].extend(sim.maturity_in(a, aH, aW, occ, m).tolist())
            if t in delays:
                cur = D.KAPPA * (anch & occ) * np.where(g["young"] | g["twin"], -1.0, 1.0)
                for a in arms:
                    fp = g["fp_change"] if D.JUNCTIONS[a]["signal"] else None
                    gH, gW = conductances(a, occ, aH, aW, fp)
                    b = below(cab, cur, gH, gW)
                    for x in ("young", "twin"):
                        adopt[a][str(t)][x].extend((b & g[x]).sum((-2, -1)) / g[x].sum())
            if t in TIMES_FA:
                cur = D.KAPPA * (anch & occ) * np.where(bad, -1.0, 1.0)
                for a in arms:
                    fp = g["fp_injury"] if (D.JUNCTIONS[a]["signal"] and t + 1 <= D.SIG["duration"]) else None
                    gH, gW = conductances(a, occ, aH, aW, fp)
                    b = below(cab, cur, gH, gW) & occ
                    for x in ("in", "ring", "out"):
                        m = g[x] & occ
                        fa[a][str(t)][x].extend((b & m).sum((-2, -1)) / np.maximum(m.sum((-2, -1)), 1))
    nb = np.concatenate(nb_all)
    fill = np.concatenate(fills)
    births = {}
    for a in arms:
        prm = D.JUNCTIONS[a]
        lam2 = (D.SIG["lam_sig"] if prm["signal"] else prm["lam"]) ** 2     # every birth comes while the injury signal is on
        G = np.zeros(len(nb)) if prm["tau_m"] > 0 else nb * lam2
        births[a] = round(float((G < gstar).mean()), 4)
    res = {"note": "static map, no dynamics; computed before the freeze from the design's constants", "draws": DRAWS,
           "seed": SEED, "design_digest": D.digest(), "g_star": gstar, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "fill_time": {"mean": round(float(fill.mean()), 1), "max": int(fill.max()), "share_by_250": round(float((fill <= 250).mean()), 4)},
           "newborn_neighbours": {str(n): round(float((nb == n).mean()), 4) for n in range(1, 5)},
           "self_reading_newborns": births,
           "adoption": {a: {d: {x: round(float(np.mean(v)), 4) for x, v in node.items()} for d, node in adopt[a].items()} for a in arms},
           "false_alarms": {a: {t: {x: round(float(np.mean(v)), 5) for x, v in node.items()} for t, node in fa[a].items()} for a in arms},
           "maturity": {a: {t: {x: round(float(np.mean(v)), 4) for x, v in node.items()} for t, node in mat[a].items()} for a in mat}}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("fill_time", "newborn_neighbours", "self_reading_newborns")}))
    for a in arms:
        print(f"{a:9s} adoption young/twin " + "  ".join(f"d{d}: {res['adoption'][a][d]['young']:.3f}/{res['adoption'][a][d]['twin']:.3f}"
                                                     for d in res["adoption"][a])
              + "   false alarms in/ring/out " + "  ".join(f"t{t}: " + "/".join(f"{res['false_alarms'][a][t][x]:.4f}" for x in ("in", "ring", "out"))
                                                         for t in res["false_alarms"][a]))
    for a in mat:
        print(a, "maturity", res["maturity"][a])


if __name__ == "__main__":
    main()
