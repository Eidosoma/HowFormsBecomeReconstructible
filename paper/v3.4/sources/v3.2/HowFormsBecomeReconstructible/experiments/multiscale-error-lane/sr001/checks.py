"""Qualification of SR001 on the preflight (engineering) shards; criteria fixed in advance.

python -m sr001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json;
with --blocks on DEBUG_BLOCKS it writes debug_qualification_receipt.json in the root instead)

Q1  complete and finite: every task's shard holds every endpoint at its declared shape, all finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards (endpoints) and raw states
Q3  engine: a generation from the acquired body with np001's stream names equals np001.sim.stage1 under NP001's six
    conditions (alone, intact, body1, record1, body, body3) bit for bit (V, r, H, W) over 4,000 updates, on S8 and S4s2
    with li4 and dw; with lr004's names it equals lr004.sim.run under vote, body and record+parity at 3e-3 and 1e-2 over
    4,000 updates on F0 with li4; the recipient with np001's names equals np001.sim.successor over 2,000 updates (dw, li4)
Q4  replay: one case of one branch at a time, with no batching and no lr004.sim.relations (bond noise, the record step,
    relearning from the body, the record or the vote, and parity written out here), reproduces five saved G1 states
    (V and r within 1e-12, bonds exactly): li4 body@3e-3 on S8, li16n vote@1e-2 on S4, dw parity@1e-2 on F0, li4 noread
    on S4s2, li16n protected on S8
Q5  aliases: the records no body writes (protected, exposed, parity) give bit-identical record endpoints across the
    three lineage bodies at every generation for every unit; every recipient's no-record control is bit-identical across
    the lineages of its kind; a recipient reading the protected G16 record ends bit-identical across the lineage bodies
Q6  reanalysis: G16's record and body endpoints recomputed from the saved raw states equal the saved ones
Q7  efficacy: every foreign placement's inversion-invariant agreement with T is 0.75, 0.5 and 0.75 (rolls of 1/8, 1/4
    and 3/8 period; C = 0.75) on every case of every unit; the protected route's bonds at G16 equal the acquired bonds
    (bond error 0); the exposed copy's G1 bond error is within 0.02 of (1 - exp(-2 p T_GEN)) / 2; every acquired record
    agrees in sign with its template at every site; each generation's newborn aligns with T within 0.15 of 0.5 (block
    mean); the vote's second record at G16 differs from the first in some bonds (independent noise)
Q8  pairing: a generation with the same route twice gives bit-identical branches; a recipient whose every branch reads
    the same record at the same gain gives bit-identical branches
Q9  resources: forecast development wall <= 12 h on 12 workers, worker RAM <= 2 GB and disk headroom
Q10 reader dry run: sr001.analyze and sr001.tables complete on these shards, every statement is scored, every git
    file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl001 import sim as S  # noqa: E402
from lr001.sim import cut_for, edges_from, halves, parity_repair  # noqa: E402
from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msegrid.core import R_STAR, Stream, birth, bonds, record_step  # noqa: E402
from np001 import design as N1D  # noqa: E402
from np001 import sim as N1S  # noqa: E402
from sr001 import design as D  # noqa: E402
from sr001 import sim  # noqa: E402
from sr001 import worker as WK  # noqa: E402

FROZEN = LANE / "sr001" / "frozen"
Q4_ITEMS = (("li4", "S8", "body@0.003", 1), ("li16n", "S4", "vote@0.01", 4), ("dw", "F0", "parity@0.01", 6),
            ("li4", "S4s2", "noread", 3), ("li16n", "S8", "protected", 7))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def tag_of(root):
    return json.loads((root / "manifest.json").read_text()).get("tag", D.TAG) if (root / "manifest.json").exists() else D.TAG


def meta_tag(root, body, unit, block):
    with np.load(root / "shards" / body / unit / f"{block}.npz") as f:
        return json.loads(str(f["__meta__"]))["tag"]


def shapes():
    k, nr, nb2, g, nv = D.NCASE, len(D.ROUTES), len(WK.BRANCHES2), D.GENS, len(WK.VOTE)
    out = {f"g/{e}": (g, nr, k) for e in sim.ENDS}
    out.update({f"g/{e}": (g, D.NFOREIGN, nr, k) for e in sim.FENDS})
    out["g/rB_a"] = (g, nv, k)
    for RB in D.RECIPIENTS:
        out.update({f"rec/{RB}/{e}": (len(D.READS2), nb2, k) for e in sim.ENDS2})
        out[f"rec/{RB}/v_f"] = (len(D.READS2), D.NFOREIGN, nb2, k)
    return out


def q1(root, blocks):
    want, bad = shapes(), []
    for b, u in D.tasks():
        for blk in blocks:
            z = npz(root / "shards" / b / u / f"{blk}.npz")
            for key, shp in want.items():
                if key not in z or z[key].shape != shp or not np.isfinite(z[key]).all():
                    bad.append((b, u, blk, key))
            if set(z) - set(want):
                bad.append((b, u, blk, "extra", sorted(set(z) - set(want))[:3]))
    return {"pass": not bad, "failed": bad[:10], "tasks": len(D.tasks()) * len(blocks)}


def q2(root, blocks):
    b, u, blk = "li4", "S8", blocks[0]
    tag = meta_tag(root, b, u, blk)
    ends, raw, timing, cases = WK.task(b, u, blk, "engineering", tag)
    z, zr = npz(root / "shards" / b / u / f"{blk}.npz"), npz(root / "raw" / b / u / f"{blk}.npz")
    eq = all(np.array_equal(ends[k], z[k]) for k in ends) and all(np.array_equal(raw[k], zr[k]) for k in raw)
    return {"pass": bool(eq), "task": [b, u, blk]}


def _routes_np1():
    return tuple(D.Route(c.name, c.rate, {"none": "", "body": "body", "record+parity": "record"}[c.repair], c.parity,
                         c.gain) for c in N1D.CONDS)


def _start(R0, idx, two=None):
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    A = (H0.copy(), W0.copy(), D.STRENGTH0 * H0, D.STRENGTH0 * W0, R0[idx].copy())
    B = None if two is None or not len(two) else (H0[two].copy(), W0[two].copy(), D.STRENGTH0 * H0[two],
                                                 D.STRENGTH0 * W0[two], R0[idx][two].copy())
    return A, B, H0, W0


def q3(block, tag):
    items, ok = [], True
    for body, unit in (("li4", "S8"), ("dw", "S4s2"), ("li4", "S4s2"), ("dw", "S8")):
        cases, V0, ema0, R0, th, T = N1S.prepare(unit, block, "engineering")
        k = len(cases)
        o = N1S.stage1(body, N1D.CONDS, cases, V0, ema0, R0, th, T, {N1D.WINDOW}, tag=tag)
        routes = _routes_np1()
        idx = np.tile(np.arange(k), len(routes))
        A, B, H0, W0 = _start(R0, idx)
        Tf = sim.foreign(T, unit, cases)
        V, E, A2, _, _ = sim.generation(body, routes, cases, V0[idx].copy(), ema0[idx].copy(), A, None, tag, sim.NP1_NAMES,
                                        N1D.WINDOW, {N1D.WINDOW}, T[idx], Tf[:, idx], H0, W0, (th * N1D.THETA)[idx])
        e = [np.array_equal(V, o["V"]), np.array_equal(A2[4], o["r"]), np.array_equal(A2[0], o["H"]),
             np.array_equal(A2[1], o["W"])]
        items.append([body, unit, "np001.stage1", e])
        ok &= all(e)
        if body in ("dw", "li4") and unit in ("S8", "S4s2"):
            gains = [N1D.GAIN] * len(N1D.CONDS)
            o2 = N1S.successor(body, o["r"], o["H"], o["W"], cases, th, T, set(N1D.READS2), gains, tag=tag)
            s2 = sim.recipient(body, o["r"], o["H"], o["W"], cases, th, T, Tf, set(N1D.READS2), gains, tag=tag,
                               names=(("successor", body), ("successor-future", body), ("successor-record-noise", body)))
            e = [np.array_equal(s2["V"], o2["V"]), np.array_equal(s2["v_a"], o2["align"])]
            items.append([body, unit, "np001.successor", e])
            ok &= all(e)
    cases, V0, ema0, R0, th, T = N1S.prepare("F0", block, "engineering")
    k = len(cases)
    lconds = tuple(L4D.Cond(p, rep) for p in (0.003, 0.01) for rep in ("vote", "body", "record+parity"))
    o4 = L4S.run("li4", lconds, cases, V0, ema0, R0, th, T, 0.0, {L4D.WINDOW}, tag=tag)
    routes = tuple(D.Route(c.name, c.rate, c.source, c.parity, D.GAIN) for c in lconds)
    idx = np.tile(np.arange(k), len(routes))
    P = sim.params(routes, k)
    A, B, H0, W0 = _start(R0, idx, P["two_idx"])
    Tf = sim.foreign(T, "F0", cases)
    V, E, A2, _, _ = sim.generation("li4", routes, cases, V0[idx].copy(), ema0[idx].copy(), A, B, tag, sim.NP1_NAMES,
                                    L4D.WINDOW, {L4D.WINDOW}, T[idx], Tf[:, idx], H0, W0, (th * 0.0)[idx], P)
    e = [np.array_equal(V, o4["V"]), np.array_equal(A2[4], o4["r"]), np.array_equal(A2[0], o4["H"]),
         np.array_equal(A2[1], o4["W"])]
    items.append(["li4", "F0", "lr004.run", e])
    ok &= all(e)
    return {"pass": bool(ok), "items": items}


def _replay_branch(body, route, j, case_list, R0, th, tag, t_gen):
    """One case, one branch, one generation (G1), unbatched; the relations written out here."""
    alpha, G = sim.kernel(body)
    c = case_list[j]
    V = birth(tag, [c], "gen", 1, "birth", side=D.SIDE)[0].copy()
    E = V.copy()
    s0 = np.where(R0[j] >= 0, 1.0, -1.0)
    H, W = s0 * np.roll(s0, -1, -1), s0 * np.roll(s0, -1, -2)
    r = R0[j].copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    two = route.two
    if two:
        HB, WB, rB = H.copy(), W.copy(), r.copy()
        HbB, WbB = D.STRENGTH0 * HB, D.STRENGTH0 * WB
    cut = cut_for(route.rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    thb = th[j] * D.THETA
    st, xs, zs = (Stream(tag, [c], *nm, side=D.SIDE) for nm in sim.GEN_NAMES(1)[:3])
    if two:
        xsB, zsB = (Stream(tag, [c], *nm, side=D.SIDE) for nm in sim.GEN_NAMES(1)[3:5])
    for t in range(1, t_gen + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK)[:, 0], xs.take(D.CHUNK)[:, 0], zs.take(D.CHUNK)[:, 0]
            if two:
                xbB, zbB = xsB.take(D.CHUNK)[:, 0], zsB.take(D.CHUNK)[:, 0]
        V, E, _, _, _ = S.body(V[None], E[None], r[None], thb[None], buf[i][None], p, route.gain, alpha, G)
        V, E = V[0], E[0]
        z = zbuf[i]
        fh, fw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(fh, -H, H), np.where(fw, -W, W), np.where(fh, -Hb, Hb), np.where(fw, -Wb, Wb)
        r = record_step(r, xbuf[i], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        if two:
            zB = zbB[i]
            fh2, fw2 = zB > cut, zB < -cut
            HB, WB = np.where(fh2, -HB, HB), np.where(fw2, -WB, WB)
            HbB, WbB = np.where(fh2, -HbB, HbB), np.where(fw2, -WbB, WbB)
            rB = record_step(rB, xbB[i], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(HB, WB))
        if route.source:
            if route.source == "body":
                xh, xw = V * np.roll(V, -1, -1), V * np.roll(V, -1, -2)
            elif route.source == "record":
                xh, xw = r * np.roll(r, -1, -1) / R_STAR ** 2, r * np.roll(r, -1, -2) / R_STAR ** 2
            else:                                             # the vote: the majority of three relations, both records
                rel = lambda x: (np.where((x > 0) == (np.roll(x, -1, -1) > 0), 1.0, -1.0),
                                 np.where((x > 0) == (np.roll(x, -1, -2) > 0), 1.0, -1.0))
                (vh, vw), (ah, aw), (bh, bw) = rel(V), rel(r), rel(rB)
                xh, xw = np.sign(vh + ah + bh), np.sign(vw + aw + bw)
                HbB, WbB = HbB + D.ETA * (xh - HbB), WbB + D.ETA * (xw - WbB)
                HB, WB = np.where(HbB != 0, np.sign(HbB), HB), np.where(WbB != 0, np.sign(WbB), WB)
            Hb, Wb = Hb + D.ETA * (np.clip(xh, -1, 1) - Hb), Wb + D.ETA * (np.clip(xw, -1, 1) - Wb)
            H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
        if route.parity:
            H2, W2 = parity_repair(H, W)
            H, W = H2, W2
            Hb, Wb = np.where(np.sign(Hb) * H < 0, -Hb, Hb), np.where(np.sign(Wb) * W < 0, -Wb, Wb)
    return V, r, H, W


def q4(root, block):
    items, ok = [], True
    for body, unit, rname, j in Q4_ITEMS:
        tag = meta_tag(root, body, unit, block)
        cases, V0, ema0, R0, th, T = N1S.prepare(unit, block, "engineering")
        route = D.ROUTES[D.ROUTENAMES.index(rname)]
        V, r, H, W = _replay_branch(body, route, j, cases, R0, th, tag, D.T_GEN)
        zr = npz(root / "raw" / body / unit / f"{block}.npz")
        ri = D.ROUTENAMES.index(rname)
        dV = float(np.abs(V - zr["g1/V"][ri, j]).max())
        dr = float(np.abs(r - zr["g1/r"][ri, j]).max())
        bh = bool(np.array_equal(H.astype(np.int8), zr["g1/H"][ri, j]) and np.array_equal(W.astype(np.int8), zr["g1/W"][ri, j]))
        good = dV <= 1e-12 and dr <= 1e-12 and bh
        items.append([body, unit, rname, j, dV, dr, bh])
        ok &= good
    return {"pass": bool(ok), "items": items}


def q5(root, blocks):
    bad, n = [], 0
    nowrite = [i for i, r in enumerate(D.ROUTES) if r.source in ("", "record")]
    keys = [f"g/{e}" for e in ("r_a", "r_shape", "r_spacing", "bond_err")] + ["g/r_f"]
    for u in D.UNITS:
        for blk in blocks:
            zs = {b: npz(root / "shards" / b / u / f"{blk}.npz") for b in D.BODIES}
            for key in keys:
                ref = zs[D.BODIES[0]][key][..., nowrite, :]
                for b in D.BODIES[1:]:
                    n += 1
                    if not np.array_equal(zs[b][key][..., nowrite, :], ref):
                        bad.append(("nowrite", u, blk, key, b))
    ci, pi = len(WK.BRANCHES2) - 1, 0
    for RB in D.RECIPIENTS:
        for blk in blocks:
            ref = None
            for b, u in D.tasks():
                zr = npz(root / "raw" / b / u / f"{blk}.npz")[f"rec/{RB}/V"]
                n += 1
                if ref is None:
                    ref = zr[ci]
                elif not np.array_equal(zr[ci], ref):
                    bad.append(("control", RB, blk, b, u))
            for u in D.UNITS:
                ref = npz(root / "raw" / D.BODIES[0] / u / f"{blk}.npz")[f"rec/{RB}/V"][pi]
                for b in D.BODIES[1:]:
                    n += 1
                    if not np.array_equal(npz(root / "raw" / b / u / f"{blk}.npz")[f"rec/{RB}/V"][pi], ref):
                        bad.append(("protected recipient", RB, blk, b, u))
    return {"pass": not bad, "checked": n, "failed": bad[:10]}


def q6(root, blocks):
    bad = []
    for b, u in D.tasks():
        for blk in blocks:
            z, zr = npz(root / "shards" / b / u / f"{blk}.npz"), npz(root / "raw" / b / u / f"{blk}.npz")
            T, Tf = zr["T"].astype(float), zr["Tf"].astype(float)
            g = D.GENS
            V, r = zr[f"g{g}/V"], zr[f"g{g}/r"]
            H, W = zr[f"g{g}/H"].astype(float), zr[f"g{g}/W"].astype(float)
            R0 = zr["R0"]
            H0, W0 = edges_from(bonds(R0, True))
            for ri in range(len(D.ROUTES)):
                chk = {"r_a": S.sign(r[ri], T), "v_a": S.sign(V[ri], T), "r_shape": S.best_shift(r[ri], T),
                       "v_shape": S.best_shift(V[ri], T), "r_spacing": S.spacing(r[ri]), "v_spacing": S.spacing(V[ri]),
                       "agree": ((V[ri] > 0) == (r[ri] > 0)).mean((-2, -1)),
                       "bond_err": ((H[ri] != H0).mean((-2, -1)) + (W[ri] != W0).mean((-2, -1))) / 2}
                for key, v in chk.items():
                    if not np.array_equal(v, z[f"g/{key}"][g - 1, ri]):
                        bad.append((b, u, blk, D.ROUTENAMES[ri], key))
                rf = np.stack([S.sign(r[ri], t) for t in Tf])
                if not np.array_equal(rf, z["g/r_f"][g - 1, :, ri]):
                    bad.append((b, u, blk, D.ROUTENAMES[ri], "r_f"))
    return {"pass": not bad, "failed": bad[:10]}


def q7(root, blocks):
    bad = []
    for b, u in D.tasks():
        for blk in blocks:
            z, zr = npz(root / "shards" / b / u / f"{blk}.npz"), npz(root / "raw" / b / u / f"{blk}.npz")
            T, Tf, R0 = zr["T"].astype(float), zr["Tf"].astype(float), zr["R0"]
            ag = np.stack([((t > 0) == (T > 0)).mean((-2, -1)) for t in Tf])
            if not np.allclose(np.maximum(ag, 1 - ag), np.array([0.75, 0.5, 0.75])[:, None], atol=0, rtol=0):
                bad.append(("foreign", b, u, blk))
            if not ((R0 > 0) == (T > 0)).all():
                bad.append(("acquired record", b, u, blk))
            pi = D.ROUTENAMES.index("protected")
            if np.any(z["g/bond_err"][-1, pi] != 0):
                bad.append(("protected bonds", b, u, blk))
            ei = D.ROUTENAMES.index("exposed@0.001")
            expect = (1 - np.exp(-2 * 0.001 * D.T_GEN)) / 2
            if abs(float(z["g/bond_err"][0, ei].mean()) - expect) > 0.02:
                bad.append(("exposed noise", b, u, blk, float(z["g/bond_err"][0, ei].mean())))
            vi = list(WK.VOTE)
            if f"g{D.GENS}/rB" in zr:
                rA = zr[f"g{D.GENS}/r"][[D.ROUTENAMES.index(v) for v in vi]]
                if np.array_equal(np.sign(zr[f"g{D.GENS}/rB"]), np.sign(rA)):
                    bad.append(("vote records identical", b, u, blk))
    tag = meta_tag(root, D.BODIES[0], D.UNITS[0], blocks[0])
    from mse.assay import enrol
    for blk in blocks:
        cases = enrol([blk], D.MESSAGES, D.PARENTS, "engineering")
        T = N1S.prepare("S4", blk, "engineering")[5]
        for g in (1, D.GENS):
            Vn = birth(tag, cases, "gen", g, "birth", side=D.SIDE)
            m = float(S.sign(Vn, T).mean())
            if abs(m - 0.5) > 0.15:
                bad.append(("newborn", blk, g, m))
    return {"pass": not bad, "failed": bad[:10]}


def q8(block, tag):
    cases, V0, ema0, R0, th, T = N1S.prepare("S8", block, "engineering")
    k = len(cases)
    rt = D.ROUTES[D.ROUTENAMES.index("body@0.003")]
    routes = (rt, rt)
    idx = np.tile(np.arange(k), 2)
    A, B, H0, W0 = _start(R0, idx)
    Tf = sim.foreign(T, "S8", cases)
    V = birth(tag, cases, "gen", 1, "birth", side=D.SIDE)[idx].copy()
    V, E, A2, _, _ = sim.generation("li4", routes, cases, V, V.copy(), A, None, tag, sim.GEN_NAMES(1), 500, {500},
                                    T[idx], Tf[:, idx], H0, W0, (th * D.THETA)[idx])
    e1 = np.array_equal(V[:k], V[k:]) and np.array_equal(A2[4][:k], A2[4][k:])
    r = np.concatenate([R0, R0])
    Hs, Ws = edges_from(bonds(R0, True))
    o = sim.recipient("li4", r, np.concatenate([Hs, Hs]), np.concatenate([Ws, Ws]), cases, th, T, Tf, {500}, [D.GAIN] * 2,
                      tag=tag, window=500)
    e2 = np.array_equal(o["V"][:k], o["V"][k:])
    return {"pass": bool(e1 and e2), "generation": bool(e1), "recipient": bool(e2)}


def q9(root):
    m = json.loads((root / "manifest.json").read_text())
    per_task_cpu = m["cpu_s_total"] / len(m["tasks"])
    per_task_wall = max(t["wall_s"] for t in m["tasks"].values())
    ntask = len(D.tasks()) * (D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0])
    wall_h = ntask * np.mean([t["wall_s"] for t in m["tasks"].values()]) / 12 / 3600 * 1.15
    free = shutil.disk_usage(root).free
    need = m["bytes_written"] / len(m["tasks"]) * ntask
    ok = wall_h <= 12 and m["worker_maxrss_mb_peak"] <= 2048 and free > 10 * need
    return {"pass": bool(ok), "forecast_wall_h_12_workers": round(float(wall_h), 2),
            "forecast_cpu_h": round(per_task_cpu * ntask / 3600, 2), "longest_task_wall_s": per_task_wall,
            "peak_rss_mb": m["worker_maxrss_mb_peak"], "disk_need_gb": round(need / 1e9, 2)}


def q10(root, blocks, out):
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "sr001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out),
           "--blocks", f"{blocks[0]},{blocks[-1] + 1}"]
    if blocks[0] not in range(*D.DEBUG_BLOCKS):
        cmd = cmd[:-2]
    p = subprocess.run(cmd, cwd=str(LANE), capture_output=True, text=True)
    if p.returncode == 0:
        p = subprocess.run([sys.executable, "-m", "sr001.tables", "--out", str(out)], cwd=str(LANE), capture_output=True,
                           text=True)
    files = {f.name: f.stat().st_size for f in out.iterdir()}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    ok = p.returncode == 0 and len(scored) == len({q["stmt"] for q in __import__("sr001.predict", fromlist=["PARTS"]).PARTS}) \
        and max(files.values()) <= 256 * 1024
    return {"pass": bool(ok), "returncode": p.returncode, "largest_file_bytes": max(files.values()) if files else None,
            "files": files, "stderr_tail": p.stderr[-400:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus[:1])
    root = a.root.resolve()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    tag = meta_tag(root, D.BODIES[0], D.UNITS[0], blocks[0])
    t0 = time.time()
    res = {}
    import multiprocessing as mp
    pool = ProcessPoolExecutor(2, mp_context=mp.get_context("fork"),
                               initializer=os.sched_setaffinity, initargs=(0, cpus[1:3] or cpus[:1]))
    slow = {"Q2_serial_equals_parallel": pool.submit(q2, root, blocks), "Q3_engine": pool.submit(q3, blocks[0], tag)}
    for name, f in (("Q1_complete_finite", lambda: q1(root, blocks)),
                    ("Q2_serial_equals_parallel", lambda: slow["Q2_serial_equals_parallel"].result()),
                    ("Q3_engine", lambda: slow["Q3_engine"].result()), ("Q4_independent_replay", lambda: q4(root, blocks[0])),
                    ("Q5_aliases_exact", lambda: q5(root, blocks)), ("Q6_reanalysis", lambda: q6(root, blocks)),
                    ("Q7_efficacy", lambda: q7(root, blocks)), ("Q8_pairing", lambda: q8(blocks[0], tag)),
                    ("Q9_resources", lambda: q9(root)),
                    ("Q10_reader_dry_run", lambda: q10(root, blocks, root / "analysis_dry_run"))):
        t1 = time.time()
        try:
            res[name] = f()
        except Exception as exc:                                # a check that cannot run fails
            res[name] = {"pass": False, "error": repr(exc)[:400]}
        res[name]["seconds"] = round(time.time() - t1, 1)
        print(name, res[name]["pass"], res[name].get("seconds"), flush=True)
    pool.shutdown()
    failed = [k for k, v in res.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "blocks": [blocks[0], blocks[-1] + 1], "tag": tag, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": res}
    debug = a.blocks is not None
    path = (root / "debug_qualification_receipt.json") if debug else (FROZEN / "qualification_receipt.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed, path)


if __name__ == "__main__":
    main()
