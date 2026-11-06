"""NL003's qualification checks, fixed before their results: python -m nl003.checks --root RUN_ROOT --stage
{preflight,debug} [--receipt PATH]. Run on the preflight blocks (900492-900493) at the full shape; on the debug blocks
(900494-900495) in phase A.

Q1  complete and finite at the declared shapes: every endpoint finite except k_spec_reg, where NaN falls exactly on the
    cases whose killed square holds no region in which A and B differ (NL002's Amendment 1, from nl002.sim.masks on the
    case's templates and kill square), and nowhere else.
Q2  serial equals parallel: one task (the store-only unit, the first block) rerun in this process equals its saved
    shards and raw states bit for bit.
Q3  the bridge, bit for bit: with the arbiter off, every branch of both units on the first block (the saved shard's
    float64 endpoints and dose, and the saved final states against nl002's cast to their saved types) equals
    nl002.sim.run's on the same labels and preparation, and the L1-only and coded recipients of those labels equal
    nl002.sim.successor's; nl002's frozen sources unchanged.
Q4  the replay: two gated branches (foreign-k0.75+A under none and copy-k0.75+A under R, dw, one case each) rerun alone
    for 300 updates with the gate computed by explicit per-region, per-cell loops (an independent implementation of the
    declared rule) equal the batched run's states at update 300 within 1e-12, the gate's refusals exactly.
Q5  aliases: (a) a gated branch whose gate never refused (its 'ever' flag 0 at the last read) equals its ungated twin
    bit for bit in every tissue endpoint; (b) the gated coded recipient whose gate never refused equals the coded
    recipient; (c) the coded recipient of 'off' equals its L1-only recipient; (d) the information-limit pair: in every
    gated change branch, spec scored against B (the share at B's sign less the share at A's, from the final record) is
    exactly minus the stored spec.
Q6  reanalysis: the last read's endpoints recomputed from the saved final records and bodies equal the shards'; the
    saved anchors equal the ones regenerated from their addresses (density, values, K's removal, change's respecification).
Q7  efficacy on synthetic states: a region whose live anchors (at least n) all contradict the code is refused; one
    agreeing anchor admits it under q 1; fewer than n contradicting anchors admit it; an anchor on an unconfident record
    cell, or where the code has no target (sigma 0), is not live; the surround admits a contradicted region with a
    disagreeing live anchor within 2 sites outside it; ring_counts equals a brute-force count; the anchors' count is
    the declared density's; the misread at sigma 0 is the identity; K removes exactly the killed square's anchors;
    change respecifies exactly the differing regions' anchors; k2 x G equals k2 bit for bit where G = 1.
Q8  pairing: a label listed twice gives identical branches, and a gated label run alone equals its run in the full
    batch (200 updates, both units).
Q9  resources: the development forecast from this run's CPU per task, within 30 CPU-hours and 12 h of wall on 12
    workers; worker memory within 2 GB; disk headroom.
Q10 the reader dry run (analyze, predict, tables), every part computed, every output file at 256 KB or less.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from nl001 import sim as N1S  # noqa: E402
from nl002 import design as D2  # noqa: E402
from nl002 import sim as S2  # noqa: E402
from nl003 import design as D  # noqa: E402
from nl003 import sim  # noqa: E402
from nl003 import worker  # noqa: E402

K = f"k{D.KSTAR:g}"


def shard(root, unit, block):
    with np.load(root / "shards" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files}


def rawfile(root, unit, block):
    with np.load(root / "raw" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files}


def names_of(s):
    m = json.loads(str(s["__meta__"]))
    return [f"{a}/{e}" for a, e in m["labels"]], m


def q1(root, blocks, stage):
    bad, undefined = [], []
    for u in D.UNITS:
        for b in blocks:
            s = shard(root, u, b)
            names, m = names_of(s)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            P = S2.prepare(cases, D.STAGE_TAG[stage])
            kd_empty = S2.masks(P["TA"], P["TB"], N1S.event_units(cases, D.STAGE_TAG[stage]))["kdreg"].sum((-2, -1)) == 0
            for key, v in s.items():
                if key == "__meta__" or not np.issubdtype(v.dtype, np.floating):
                    continue
                nan = np.isnan(v)
                if np.isinf(v).any():
                    bad.append((u, b, key, "inf"))
                if nan.any():
                    if not key.endswith("k_spec_reg"):
                        bad.append((u, b, key, "NaN outside k_spec_reg"))
                        continue
                    want = np.broadcast_to(kd_empty, v.shape)
                    if not np.array_equal(nan, want):
                        bad.append((u, b, key, "NaN not exactly on the undefined cases"))
            undefined += [(u, b, int(j)) for j in np.flatnonzero(kd_empty)]
            for key in ("t/r/spec_reg", "t/a/ref_all", "s/spec_reg", "c/spec_reg", "g/spec_reg"):
                if key not in s:
                    bad.append((u, b, key, "missing"))
    return {"pass": not bad, "bad": bad[:20], "undefined_cases": sorted(set(undefined))}


def q2(root, blocks, stage):
    u, b = "none", blocks[0]
    with tempfile.TemporaryDirectory(dir=root) as td:
        worker.run_task(u, b, stage, td)
        new_s, new_r = shard(Path(td), u, b), rawfile(Path(td), u, b)
    old_s, old_r = shard(root, u, b), rawfile(root, u, b)
    differ = [k for k in old_s if k != "__meta__" and not np.array_equal(old_s[k], new_s[k], equal_nan=True)]
    differ += [k for k in old_r if k != "__meta__" and not np.array_equal(old_r[k], new_r[k])]
    return {"pass": not differ, "task": [u, b], "differ": differ}


def q3(root, blocks, stage, units=D.UNITS):
    """The bridge on the first block: the saved shard's arbiter-off branches (the tissue's float64 endpoints, the dose,
    the L1-only and coded recipients) against a fresh nl002.sim.run and nl002.sim.successor on the same labels and
    preparation, bit for bit; the saved final states (float32 r and V, int8 bonds) against nl002's cast likewise."""
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])
    P = S2.prepare(cases, tag)
    out = {}
    for unit in units:
        s_, r_ = shard(root, unit, b), rawfile(root, unit, b)
        names, m = names_of(s_)
        labels = [tuple(x) for x in m["labels"]]
        rlabels = [tuple(x) for x in m["rlabels"]]
        arms, _ = sim.use_stage(stage)
        off = [l for l in labels if not arms[l[0]].arb]
        li = [labels.index(l) for l in off]
        o2, d2, f2, _ = S2.run(cases, unit, labels=off, prep=P, tag=tag)
        t_same = all(np.array_equal(s_[f"t/{w}/{e}"][:, li], o2[(w, e)], equal_nan=True) for (w, e) in o2)
        t_same &= bool(np.array_equal(s_["dose"][li], d2))
        f_same = all(np.array_equal(r_[x][li], f2[x].astype(r_[x].dtype)) for x in f2)
        rec2, cod2 = S2.successor(cases, f2, P, labels=off, tag=tag)
        lo = [rlabels.index(l) for l in off]
        nr = len(rlabels)
        s_same = all(np.array_equal(s_[f"s/{e}"][:, lo + [nr, nr + 1, nr + 2]], rec2[e], equal_nan=True) for e in rec2)
        c_same = all(np.array_equal(s_[f"c/{e}"][:, lo], cod2[e], equal_nan=True) for e in cod2)
        out[unit] = {"tissue_and_dose": bool(t_same), "final_states": bool(f_same), "l1_only": bool(s_same),
                     "coded": bool(c_same), "labels_off": len(off)}
    frozen = json.loads((LANE / "nl002" / "frozen" / "design.json").read_text())["sources"]
    now = D2.sources(LANE)
    unchanged = all(now.get(k) == v for k, v in frozen.items())
    return {"pass": all(all(v for k, v in x.items() if k != "labels_off") for x in out.values()) and unchanged,
            "units": out, "nl002_sources_unchanged": unchanged, "block": b}


def gate_loops(r, sig, Bg, am, aval, cfg):
    """The declared rule by explicit loops, one sheet: refused (NR, NR) bool."""
    n_, NR = D.SIDE, D.SIDE // D.REGION
    vs = lambda x: 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)
    live = np.zeros((n_, n_), bool)
    dis = np.zeros((n_, n_), bool)
    for i in range(n_):
        for j in range(n_):
            t = float(np.sign(sig[i, j] * Bg[i, j]))
            if am[i, j] and vs(r[i, j]) != 0 and t != 0:
                live[i, j] = True
                dis[i, j] = aval[i, j] != t
    ref = np.zeros((NR, NR), bool)
    for ri in range(NR):
        for rj in range(NR):
            sl = (slice(ri * D.REGION, (ri + 1) * D.REGION), slice(rj * D.REGION, (rj + 1) * D.REGION))
            nd, nl = int(dis[sl].sum()), int(live[sl].sum())
            ok = nd >= cfg["n"] and nd >= cfg["q"] * nl
            if ok and cfg["ring"]:
                g = cfg["ring"]
                cnt = 0
                for di in range(-g, D.REGION + g):
                    for dj in range(-g, D.REGION + g):
                        if 0 <= di < D.REGION and 0 <= dj < D.REGION:
                            continue
                        cnt += int(dis[(ri * D.REGION + di) % n_, (rj * D.REGION + dj) % n_])
                ok = cnt <= cfg["ring_max"]
            ref[ri, rj] = ok
    return ref


def q4(blocks, stage):
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])
    P = S2.prepare(cases, tag)
    arms, labels = sim.use_stage(stage)
    picks = [(f"foreign-{K}+A", "none"), (f"copy-{K}+A", "R")]
    window = 300
    out = []
    o_full, _, f_full, _, _ = sim.run(cases, "dw", labels, prep=P, tag=tag, window=window, reads=(window,))
    real_gate = sim.gate
    nref = [0, 0]

    def loop_gate(r, sig, Bg, am, aval, n, q, ring, ring_max):
        res = np.stack([gate_loops(r[m], sig[m], Bg[m], am[m], aval[m],
                                   {"n": int(n[m]), "q": float(q[m]), "ring": int(ring[m]), "ring_max": int(ring_max[m])})
                        for m in range(r.shape[0])])
        fast = real_gate(r, sig, Bg, am, aval, n, q, ring, ring_max)
        nref[0] += int(res.sum())
        nref[1] += int((res != fast).sum())
        return res
    sim.gate = loop_gate
    try:
        for lab in picks:
            o1, _, f1, _, _ = sim.run(cases, "dw", [lab], prep=P, tag=tag, window=window, reads=(window,))
            bi = labels.index(lab)
            dr = float(np.abs(f1["r"][0] - f_full["r"][bi]).max())
            dv = float(np.abs(f1["V"][0] - f_full["V"][bi]).max())
            out.append({"label": "/".join(lab), "max_dr": dr, "max_dV": dv})
    finally:
        sim.gate = real_gate
    return {"pass": all(x["max_dr"] <= 1e-12 and x["max_dV"] <= 1e-12 for x in out) and nref[1] == 0,
            "branches": out, "loop_refusals": nref[0], "loop_vs_vectorised_differences": nref[1], "window": window}


def q5(root, blocks, stage):
    bad, n_alias = [], 0
    for u in D.UNITS:
        for b in blocks:
            s = shard(root, u, b)
            names, m = names_of(s)
            gated = m["gated_r"]
            rnames = [f"{a}/{e}" for a, e in m["rlabels"]]
            ever = s["t/a/ever"][-1]                                  # (branches, cases)
            for gi, br in enumerate(names):
                if "+" not in br:
                    continue
                twin = br.split("+")[0] + "/" + br.split("/")[-1]
                if twin not in names or br.endswith("/change"):
                    continue
                ti = names.index(twin)
                for j in np.flatnonzero(ever[gi] == 0):
                    n_alias += 1
                    for key in s:
                        if key.startswith("t/r/") or key.startswith("t/v/"):
                            if not np.array_equal(s[key][:, gi, j], s[key][:, ti, j], equal_nan=True):
                                bad.append((u, b, br, int(j), key))
            if "g/ever" in s:
                gever = s["g/ever"][-1]
                for k_, br in enumerate(gated):
                    ci = rnames.index(br)
                    for j in np.flatnonzero(gever[k_] == 0):
                        for key in [x for x in s if x.startswith("g/") and x != "g/ever"]:
                            if not np.array_equal(s[key][:, k_, j], s["c/" + key[2:]][:, ci, j], equal_nan=True):
                                bad.append((u, b, br, int(j), key, "gated vs coded"))
            oi = rnames.index("off/none")
            for key in [x for x in s if x.startswith("c/")]:
                if not np.array_equal(s[key][:, oi], s["s/" + key[2:]][:, oi], equal_nan=True):
                    bad.append((u, b, "off", key, "coded vs L1-only"))
            r = rawfile(root, u, b)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            mk = S2.masks(r["TA"].astype(float), r["TB"].astype(float), N1S.event_units(cases, D.STAGE_TAG[stage]))
            for br in [x for x in names if x.endswith("/change") and "+" in x]:
                bi = names.index(br)
                reg = N1S.unit_sign(r["r"][bi].astype(float), D.REGION)
                specB = N1S.frac(mk["dreg"], reg == mk["regB"], (-2, -1)) - N1S.frac(mk["dreg"], reg == mk["regA"], (-2, -1))
                if not np.array_equal(specB, -s["t/r/spec_reg"][-1, bi]):
                    bad.append((u, b, br, "the pair's identity"))
    return {"pass": not bad, "bad": bad[:20], "never_refused_case_aliases": n_alias}


def q6(root, blocks, stage):
    bad = []
    tag = D.STAGE_TAG[stage]
    for u in D.UNITS:
        for b in blocks:
            s, r = shard(root, u, b), rawfile(root, u, b)
            names, m = names_of(s)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            mk = {k: np.concatenate([v] * len(names)) for k, v in
                  S2.masks(r["TA"].astype(float), r["TB"].astype(float), N1S.event_units(cases, tag)).items()}
            rr = r["r"].astype(np.float64).reshape(-1, D.SIDE, D.SIDE)
            got = S2.score(rr, mk)
            for e, v in got.items():
                want = s[f"t/r/{e}"][-1].reshape(-1)
                f32 = np.sign(rr) == np.sign(r["r"].reshape(-1, D.SIDE, D.SIDE))
                if not f32.all():
                    bad.append((u, b, "float32 sign"))
                if not np.array_equal(v.reshape(-1), want, equal_nan=True):
                    bad.append((u, b, e))
            arms, labels = sim.use_stage(stage)
            P = S2.prepare(cases, tag)
            units = N1S.event_units(cases, tag)
            gl = [i for i, (a_, _) in enumerate(labels) if arms[a_].arb]
            for k_, i in enumerate(gl):
                a_, ev = labels[i]
                am, aval = sim.anchor_fields(cases, P, arms[a_], ev, units, tag)
                if not (np.array_equal(am.astype(np.int8), r["am"][k_]) and np.array_equal(aval.astype(np.int8), r["aval"][k_])):
                    bad.append((u, b, f"{a_}/{ev}", "anchors"))
    return {"pass": not bad, "bad": bad[:20]}


def q7():
    rule = {"n": 2, "q": 1.0, "ring": 0, "ring_max": 0}
    n_ = D.SIDE
    items = {}
    rng = np.random.default_rng(7)
    r = np.full((1, n_, n_), 1.0)
    sig = np.ones((1, n_, n_))
    Bg = np.full((1, n_, n_), 1.0)
    am = np.zeros((1, n_, n_), bool)
    aval = np.zeros((1, n_, n_))
    am[0, 0:4, 0:4] = True
    aval[0, 0:4, 0:4] = -1.0                                     # region (0, 0): every anchor contradicts the code
    arr = lambda c: tuple(np.array([c[x]]) for x in ("n", "q", "ring", "ring_max"))
    ref = sim.gate(r, sig, Bg, am, aval, *arr(rule))
    items["contradicted_region_refused"] = bool(ref[0, 0, 0]) and int(ref.sum()) == 1
    aval2 = aval.copy()
    aval2[0, 0, 0] = 1.0
    items["one_agreeing_anchor_admits_q1"] = not bool(sim.gate(r, sig, Bg, am, aval2, *arr(rule))[0, 0, 0])
    am3 = np.zeros_like(am)
    am3[0, 0, 0] = True
    items["fewer_than_n_admit"] = not bool(sim.gate(r, sig, Bg, am3, aval, *arr(rule))[0, 0, 0])
    r4 = r.copy()
    r4[0, 0:4, 0:4] = 0.1
    items["unconfident_record_not_live"] = not bool(sim.gate(r4, sig, Bg, am, aval, *arr(rule))[0, 0, 0])
    sig5 = sig.copy()
    sig5[0, 0:4, 0:4] = 0.0
    items["no_target_not_live"] = not bool(sim.gate(r, sig5, Bg, am, aval, *arr(rule))[0, 0, 0])
    sur = dict(rule, **D.SURROUND)
    am6, aval6 = am.copy(), aval.copy()
    am6[0, 5, 1], aval6[0, 5, 1] = True, -1.0                    # a disagreeing live anchor 2 sites below the region
    items["surround_blocks_with_a_disagreeing_neighbour"] = (bool(sim.gate(r, sig, Bg, am, aval, *arr(sur))[0, 0, 0])
                                                             and not bool(sim.gate(r, sig, Bg, am6, aval6, *arr(sur))[0, 0, 0]))
    x = rng.integers(0, 2, (3, n_, n_)).astype(bool)
    for g in (1, 2):
        rc = sim.ring_counts(x, g)
        brute = np.zeros_like(rc)
        for c in range(3):
            for ri in range(n_ // D.REGION):
                for rj in range(n_ // D.REGION):
                    rows = [(ri * D.REGION + d) % n_ for d in range(-g, D.REGION + g)]
                    cols = [(rj * D.REGION + d) % n_ for d in range(-g, D.REGION + g)]
                    brute[c, ri, rj] = x[c][np.ix_(rows, cols)].sum()
        items[f"ring_counts_g{g}"] = bool(np.array_equal(rc, brute))
    cases = sim.cases_for(D.SMOKE_BLOCKS[0], "engineering")
    for dens in (D.DENSITY, D.DENSITY_SIDE):
        a = sim.anchors(cases, dens)
        items[f"anchor_count_density_{dens}"] = bool((a.sum((-2, -1)) == n_ * n_ // dens).all())
    fld = rng.standard_normal((len(cases), n_, n_))
    items["misread_sigma0_identity"] = bool(np.array_equal(sim.read_displaced(fld, cases, 0.0), fld))
    P = S2.prepare(cases, D.TAG)
    units = N1S.event_units(cases, D.TAG)
    sim.use_stage("main") if D.RULE is not None else None
    arm = D.Arm(f"copy-{K}+A", "copy", D.KSTAR, 1.0, "A") if D.RULE is not None else None
    if arm is not None:
        am0, av0 = sim.anchor_fields(cases, P, arm, "none", units)
        amK, avK = sim.anchor_fields(cases, P, arm, "K", units)
        amC, avC = sim.anchor_fields(cases, P, arm, "change", units)
        kill = np.stack([N1S.kill_mask(units[j], P["TA"][j]) for j in range(len(cases))])
        dcell = sim.rep(S2.masks(P["TA"], P["TB"], units)["dreg"])
        items["K_removes_exactly_the_square"] = bool(np.array_equal(amK, am0 & ~kill))
        items["change_respecifies_exactly_the_differing_regions"] = bool(
            np.array_equal(amC, am0) and np.array_equal(avC[~dcell], av0[~dcell])
            and np.array_equal(avC[dcell & am0], np.sign(P["RB"])[dcell & am0]))
        items["anchors_hold_A_acquired_record"] = bool(np.array_equal(av0[am0], np.sign(P["R0"])[am0]))
    k2 = np.array([0.75, 1.0, 0.5])[:, None, None] * D.KC
    g = sim.gated_k2(k2, np.zeros(0, int), np.zeros((0, n_ // D.REGION, n_ // D.REGION), bool), 3)
    items["k2_times_one_exact"] = bool(np.array_equal(g, np.broadcast_to(k2, g.shape)))
    return {"pass": all(items.values()), "items": items}


def q8(blocks, stage):
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])
    P = S2.prepare(cases, tag)
    arms, labels = sim.use_stage(stage)
    lab = (f"foreign-{K}+A", "none")
    out = {}
    for unit in D.UNITS:
        o, _, f, _, _ = sim.run(cases, unit, labels, prep=P, tag=tag, window=200, reads=(200,))
        o2, _, f2, _, _ = sim.run(cases, unit, [lab, lab], prep=P, tag=tag, window=200, reads=(200,))
        bi = labels.index(lab)
        out[unit] = {"twice_identical": bool(np.array_equal(f2["r"][0], f2["r"][1])),
                     "alone_equals_batch": bool(np.array_equal(f2["r"][0], f["r"][bi]))}
    return {"pass": all(all(v.values()) for v in out.values()), "units": out}


def q9(root, blocks):
    M = json.loads((root / "manifest.json").read_text())
    cpu = {u: np.mean([t["cpu_s"] for k, t in M["tasks"].items() if k.startswith(u + "/")]) for u in D.UNITS}
    n_dev = len(D.IDENTITIES["development"])
    total = n_dev * sum(cpu.values()) / 3600
    wall = max(cpu.values()) / 3600 * int(np.ceil(n_dev * len(D.UNITS) / 12))
    rss = M["worker_maxrss_mb_peak"]
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"]
    return {"pass": total <= 30 and wall <= 12 and rss <= 2048 and disk, "forecast_dev_cpu_h": round(total, 2),
            "forecast_dev_wall_h_12": round(wall, 2), "cpu_s_per_task": {u: round(v, 1) for u, v in cpu.items()},
            "worker_rss_mb": rss, "disk_headroom": disk}


def q10(root, stage):
    with tempfile.TemporaryDirectory(dir=root) as td:
        env = dict(os.environ, PYTHONPATH=str(LANE), PYTHONDONTWRITEBYTECODE="1")
        r1 = subprocess.run([sys.executable, "-m", "nl003.analyze", "--root", str(root), "--stage", stage, "--out", td],
                            cwd=LANE, env=env, capture_output=True, text=True)
        r2 = subprocess.run([sys.executable, "-m", "nl003.tables", "--root", str(root), "--stage", stage, "--out", td],
                            cwd=LANE, env=env, capture_output=True, text=True)
        sizes = {p.name: p.stat().st_size for p in Path(td).iterdir()}
        S = json.loads((Path(td) / "predictions_scored.json").read_text()) if (Path(td) / "predictions_scored.json").exists() else {}
    computed = bool(S) and all(np.isfinite(p["value"]) for node in S.values() for p in node["parts"].values())
    return {"pass": r1.returncode == 0 and r2.returncode == 0 and computed and all(v <= 256_000 for v in sizes.values()),
            "stderr": (r1.stderr + r2.stderr)[-400:], "sizes": sizes, "parts": sum(len(n["parts"]) for n in S.values())}


CHECKS = ("Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridge_none", "Q3_bridge_dw", "Q4_replay", "Q5_aliases",
          "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run")


def run_check(name, root, blocks, stage):
    fn = {"Q1_complete_finite": lambda: q1(root, blocks, stage), "Q2_serial_equals_parallel": lambda: q2(root, blocks, stage),
          "Q3_bridge_none": lambda: q3(root, blocks, stage, ("none",)), "Q3_bridge_dw": lambda: q3(root, blocks, stage, ("dw",)),
          "Q4_replay": lambda: q4(blocks, stage), "Q5_aliases": lambda: q5(root, blocks, stage),
          "Q6_reanalysis": lambda: q6(root, blocks, stage), "Q7_efficacy": q7, "Q8_pairing": lambda: q8(blocks, stage),
          "Q9_resources": lambda: q9(root, blocks), "Q10_reader_dry_run": lambda: q10(root, stage)}[name]
    t1 = time.time()
    try:
        res = fn()
    except Exception as exc:                                      # a crash is a failure, recorded
        res = {"pass": False, "error": repr(exc)[:500]}
    res["seconds"] = round(time.time() - t1, 1)
    print(f"{time.strftime('%H:%M:%SZ', time.gmtime())} {name}: {'PASS' if res['pass'] else 'FAIL'} ({res['seconds']} s)", flush=True)
    return res


def main():
    """--only NAME[,NAME] writes the named checks' results to --part; --merge PART [PART ...] writes the receipt from
    parts (every check exactly once); with neither, every check runs here in turn."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "debug"), required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--part", type=Path, default=None)
    ap.add_argument("--merge", type=Path, nargs="*", default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage)
    t0 = time.time()
    if a.only is not None:
        res = {n: run_check(n, root, blocks, a.stage) for n in a.only.split(",")}
        a.part.write_text(json.dumps(res, indent=1, default=str) + "\n")
        return
    if a.merge is not None:
        checks = {}
        for f in a.merge:
            for k, v in json.loads(f.read_text()).items():
                assert k not in checks, k
                checks[k] = v
        assert sorted(checks) == sorted(CHECKS), sorted(set(CHECKS) ^ set(checks))
        wall = round(sum(v["seconds"] for v in checks.values()), 1)
    else:
        checks = {n: run_check(n, root, blocks, a.stage) for n in CHECKS}
        wall = round(time.time() - t0, 1)
    checks = {n: checks[n] for n in CHECKS}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "rule": D.RULE,
               "root": str(root), "stage": a.stage, "blocks": blocks, "tag": D.STAGE_TAG[a.stage],
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "check_seconds_sum": wall,
               "checks": checks}
    out = a.receipt or (root / "qualification_receipt.json")
    out.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}))


if __name__ == "__main__":
    main()
