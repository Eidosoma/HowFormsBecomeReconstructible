"""E2E002's successors: the AR tissue's vote-default arms in every generation, started from restored generation-0 packets.

generation  ar003.sim.run_vd's update arithmetic for branches that start from their own states. Every branch (rows x
            cases, row-major) has its own first record A = (H, W, Hb, Wb, r), second record B = (HB, WB, HbB, WbB, rB),
            body, cue and detector configuration (ar005.sim.detect: ar002.sim.detect for every configuration without a
            guard). The branches sharing one configuration form a group, and each group's detector and targets run on
            all its branches at once (run_vd runs them per arm; the arithmetic is per branch). The streams are named by
            the caller: run_vd's own names under the record's tag reproduce generation 0 (replay0, the bridge), and a
            future's names under E2E002's tag give a successor.
birth_cue   the successor's cue (the lead's ruling 3): the anchors are the case's own cells (lr005.sim.anchor_mask under
            the record's tag, generation 0's); each holds its incoming record's sign, read at the lineage's sigma at the
            case's quenched displaced site (gc001.sim.read_at with unit_normals under the record's tag). This is the rule
            ar001.sim.event applies to R0 at generation 0, applied to the incoming record. A "lineage" row carries
            generation 0's cue instead (a second heritable channel, reported).
lineage     rows run from their packets for generations of T_GEN updates: a newborn body (V = E = a birth under the
            future's names, as E2E001); the first record from the packet with the strengths at STRENGTH0 x sign
            (sr001.sim.handoff, as at every handoff); the second record a copy of the incoming record (the vote's own
            rule when no event hits the first record: ar003.sim.second_record); the cue at birth; the row's policy.
            Nothing else crosses: no body, no second record, no cue, no detector state or commitment.
packets     a task's rows from its restored raw file (e2e001.sim's protected and post_damage, unchanged); identical rows
            (packet, policy, and for a detector the cue it reads) run once, every label they stand for named.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np

from ar001 import design as A
from ar001 import sim as A1S
from ar002 import sim as A2S
from ar003 import sim as S3
from ar005 import sim as A5S
from be002 import sim as B2S
from dl001 import design as DL
from dl001 import sim as S
from e2e001 import sim as E1
from gc001 import sim as GCS
from lr001.sim import cut_for, halves
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream, birth, record_step
from sr001 import sim as SRS

from . import design as D

RUN_VD_NAMES = (("future",), ("record-noise",), ("bond-noise",), ("record-noise", "B"), ("bond-noise", "B"))
BIRTH_NAMES = E1.BIRTH_NAMES            # ("e2e", "fut", f, "gen", g, "birth"), under E2E002's tag
GEN_NAMES = E1.GEN_NAMES                # the future's five streams, under E2E002's tag
DIAG = ("fired", "det_on", "det_fp", "det_fp_in", "det_zone", "det_zone_in", "opened", "opened_out", "signal",
        "committed_end")
score, protected, post_damage, perm_index = E1.score, E1.protected, E1.post_damage, E1.perm_index


def generation(body, groups, cases, V, E, A_, B_, P, m, thb, tag, names, window=D.T_GEN, gain=D.GAIN, clock=None):
    """One generation. groups: [(cfg, branch indices)] partitioning the branches; P {"am", "aval"} per branch; m the
    case's patch per branch (the detector's onset diagnostic only). Returns V, E, A, B and the detectors' diagnostics."""
    clock = D.CLOCK if clock is None else clock
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    G = S.ghat(A.SIDE, L) if alpha else None
    k = len(cases)
    n = V.shape[0]
    idx = np.tile(np.arange(k), n // k)
    H, W, Hb, Wb, r = (x.copy() for x in A_)
    HB, WB, HbB, WbB, rB = (x.copy() for x in B_)
    fp2 = B2S.footprint(m, A.SIG["d"])
    cut = cut_for(clock["rate"])
    p = replace(NATIVE, sigma=A.SIGMA)
    st, xs, zs, xsB, zsB = (Stream(tag, cases, *nm, side=A.SIDE) for nm in names)
    states = [A2S.new_det(len(ix)) for _cfg, ix in groups]
    Pg = [{"am": P["am"][ix], "aval": P["aval"][ix]} for _cfg, ix in groups]
    mg = [m[ix] for _cfg, ix in groups]
    prm = {"tau_c": clock["tau_c"]}
    opened, opened_out, signal = np.zeros(n), np.zeros(n), np.zeros(n)
    for t in range(1, window + 1):
        i = (t - 1) % A.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(A.CHUNK), xs.take(A.CHUNK), zs.take(A.CHUNK)
            xbB, zbB = xsB.take(A.CHUNK), zsB.take(A.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(H, W))
        zB = zbB[i][idx]
        h2, w2 = zB > cut, zB < -cut
        HB, WB, HbB, WbB = np.where(h2, -HB, HB), np.where(w2, -WB, WB), np.where(h2, -HbB, HbB), np.where(w2, -WbB, WbB)
        rB = record_step(rB, xbB[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(HB, WB))
        for gi, (cfg, ix) in enumerate(groups):
            sta = states[gi]
            Vs, rs, rBs = V[ix], r[ix], rB[ix]
            A5S.detect(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])
            t_on = sta["t_on"]
            on = (t_on > 0) & (t >= t_on) & (t < t_on + A.SIG["duration"])
            onset = (t_on > 0) & (t == t_on)
            signal[ix] += on
            xh, xw, extra = S3.vd_targets(prm, Vs, rs, rBs, Pg[gi], sta, on, onset, mg[gi])
            zone, tt = extra
            if tt is not None:
                opened[ix] += zone.mean((-2, -1))
                opened_out[ix] += (zone & ~fp2[ix]).mean((-2, -1))
                r[ix] = np.where(zone, rs + A.EPS * A.PULL * (tt * R_STAR - rs), rs)
            lh, lw = xh != 0, xw != 0
            Hbs, Wbs = Hb[ix], Wb[ix]
            Hn, Wn = Hbs + eta * (xh - Hbs), Wbs + eta * (xw - Wbs)
            Hbs, Wbs = np.where(lh, Hn, Hbs), np.where(lw, Wn, Wbs)
            Hb[ix], Wb[ix] = Hbs, Wbs
            H[ix] = np.where(lh & (Hbs != 0), np.sign(Hbs), H[ix])
            W[ix] = np.where(lw & (Wbs != 0), np.sign(Wbs), W[ix])
            HbBs, WbBs = HbB[ix], WbB[ix]
            HbBs, WbBs = np.where(lh, HbBs + eta * (xh - HbBs), HbBs), np.where(lw, WbBs + eta * (xw - WbBs), WbBs)
            HbB[ix], WbB[ix] = HbBs, WbBs
            HB[ix] = np.where(lh & (HbBs != 0), np.sign(HbBs), HB[ix])
            WB[ix] = np.where(lw & (WbBs != 0), np.sign(WbBs), WB[ix])
    diag = {key: np.zeros(n) for key in DIAG}
    diag["zone_map"], diag["fp_map"] = np.zeros((n, A.SIDE, A.SIDE), bool), np.zeros((n, A.SIDE, A.SIDE), bool)
    msum = m.sum((-2, -1))
    for (_cfg, ix), sta in zip(groups, states):
        diag["fired"][ix] = sta["t_on"] > 0
        diag["det_on"][ix] = np.where(sta["t_on"] > 0, sta["t_on"], -1)
        diag["det_fp"][ix] = sta["fp"].sum((-2, -1))
        diag["det_fp_in"][ix] = (sta["fp"] & m[ix]).sum((-2, -1)) / msum[ix]
        diag["det_zone"][ix] = sta["zone"].sum((-2, -1))
        diag["det_zone_in"][ix] = (sta["zone"] & m[ix]).sum((-2, -1)) / msum[ix]
        diag["committed_end"][ix] = (sta["s"] >= A.S_MIN).sum((-2, -1))
        diag["zone_map"][ix], diag["fp_map"][ix] = sta["zone"], sta["fp"]
    diag["opened"], diag["opened_out"], diag["signal"] = opened / window, opened_out / window, signal
    return V, E, (H, W, Hb, Wb, r), (HB, WB, HbB, WbB, rB), diag


def groups_of(policies, k, configs=None):
    """[(cfg, branch indices)] for rows' policy names (row-major branches), in the configurations' order (default
    POLICIES; the bridge passes AR005's VD_DETECTORS, which add vpool)."""
    configs = D.POLICIES if configs is None else configs
    out = []
    for name in configs:
        rows = [j for j, p in enumerate(policies) if p == name]
        if rows:
            out.append((configs[name], np.concatenate([np.arange(j * k, (j + 1) * k) for j in rows])))
    if sum(len(ix) for _c, ix in out) != len(policies) * k:
        raise ValueError(f"a policy without a configuration: {sorted(set(policies) - set(configs))}")
    return out


def birth_cue(r_in, normals, sigma):
    """The successor's anchors' values: the incoming record's signs, read at sigma at the quenched displaced sites."""
    exact = np.where(r_in > 0, 1.0, -1.0)
    return GCS.read_at(exact, normals, sigma) if sigma else exact


def replay0(body, situation, policies, cases, V0, ema0, R0, th, T, theta, tag, window=D.T_GEN, size=D.SIZE, configs=None):
    """Generation 0 re-run by generation() from the event's state (ar001.sim.event under the record's tag; the second
    record by ar003.sim.second_record; the event's cue; run_vd's stream names): the bridge to the restored raw file."""
    base, sig = situation.split("@")
    sigma = float(sig)
    ev = A1S.event(base, size, sigma, cases, V0, ema0, R0, T, tag)
    k = len(cases)
    idx = np.tile(np.arange(k), len(policies))
    A_ = tuple(ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb", "r"))
    rB, HB, WB, HbB, WbB = S3.second_record(base, ev, R0, idx)
    P = {"am": ev["am"][idx], "aval": ev["aval"][idx]}
    return generation(body, groups_of(policies, k, configs), cases, ev["V"][idx].copy(), ev["E"][idx].copy(), A_,
                      (HB, WB, HbB, WbB, rB), P, ev["m"][idx], (th * theta)[idx], tag, RUN_VD_NAMES, window)


def lineage(body, rows, cases, thf, T, Tf, m, am, normals, cue0, tag, gen_names, birth_names, t_gen=D.T_GEN,
            horizons=D.HORIZONS, keep=()):
    """rows: dicts {"packet": (H, W, r) each (cases, side, side), "policy", "cue", "sigma", "stop"}. cue0: {sigma:
    generation 0's anchors' values} for "lineage" rows. Returns the reads at the horizons ({g: {endpoint: (rows alive,
    cases)}}), the rows alive at each, the diagnostics of every generation ({g: {key: (rows alive, cases)}}) and the
    states kept at the generations in `keep`."""
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, diags, kept = {}, {}, {}, {}
    for g in range(1, max(row["stop"] for row in rows) + 1):
        still = [i for i in alive if rows[i]["stop"] >= g]
        if still != alive:
            sel = np.concatenate([np.arange(alive.index(i) * k, (alive.index(i) + 1) * k) for i in still])
            A_ = tuple(x[sel] for x in A_)
            alive = still
        idx = np.tile(np.arange(k), len(alive))
        V = birth(tag, cases, *birth_names(g), side=D.SIDE)[idx].copy()
        E = V.copy()
        B_ = tuple(x.copy() for x in A_)
        aval = np.empty_like(A_[4])
        for j, i in enumerate(alive):
            sl = slice(j * k, (j + 1) * k)
            row = rows[i]
            aval[sl] = cue0[row["sigma"]] if row["cue"] == "lineage" else birth_cue(A_[4][sl], normals, row["sigma"])
        P = {"am": am[idx], "aval": aval}
        # the cue's state at birth: anchors misread (birth cues at sigma > 0) and anchors already disagreeing with the
        # incoming record (a lineage cue's carried template where the packet has moved away from it)
        exact = np.where(A_[4] > 0, 1.0, -1.0)
        cue_dis = ((aval != exact) & P["am"]).sum((-2, -1)).reshape(len(alive), k)
        Tb, Tfb, mb = T[idx], Tf[:, idx], m[idx]
        V, E, A_, B_, dg = generation(body, groups_of([rows[i]["policy"] for i in alive], k), cases, V, E, A_, B_, P, mb,
                                      thf[idx], tag, gen_names(g), t_gen)
        diags[g] = {key: dg[key].reshape(len(alive), k) for key in DIAG}
        diags[g]["cue_dis_birth"] = cue_dis
        if g in horizons:
            sc = score(V, A_[4], Tb, Tfb, mb)
            reads[g] = {key: v.reshape(len(alive), k) for key, v in sc.items()}
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        A_, _ = SRS.handoff(A_, None)
    return reads, alive_at, diags, kept


def _digest(*xs):
    h = hashlib.sha256()
    for x in xs:
        h.update(np.ascontiguousarray(np.asarray(x, dtype=float)).tobytes())
    return h.hexdigest()


def packet_of(name, raw, meta, cases, V0, ema0, R0, T):
    """The generation-0 packet (H, W, r) named "<arm>/<situation>", "protected" or "post/<situation>", and the source it
    was taken from (P53 ran no vms under none@0: there the vote's none@0 record stands in, named)."""
    if name == "protected":
        return protected(R0), "protected"
    arm, sit = name.split("/")
    if arm == "post":
        base = sit.split("@")[0]
        if D.RECORD_HIT[base]:
            pk, _m = post_damage(sit, cases, V0, ema0, R0, T, meta["tag"])
            return pk, name
        return protected(R0), "protected"
    arms_of = {nm: list(a) for nm, a in meta["runs"]}
    src_arm = arm if arm in arms_of.get(sit, []) else ("vote" if "vote" in arms_of.get(sit, []) else None)
    if src_arm is None:
        return None, None
    j = arms_of[sit].index(src_arm)
    return (raw[f"{sit}/H"][j], raw[f"{sit}/W"][j], raw[f"{sit}/r"][j]), f"{src_arm}/{sit}"


def packets(raw, meta, cases, V0, ema0, R0, T, lineages):
    """The task's distinct rows and, for each lineage label, the row it runs on; the alias table; the packets' sources."""
    entries = []
    for ln in lineages:
        pk, src = packet_of(ln["packet"], raw, meta, cases, V0, ema0, R0, T)
        if pk is None:
            continue
        entries.append((ln, tuple(np.asarray(x, dtype=float) for x in pk), src))
    rows, labels, aliases, sources, sig = [], {}, {}, {}, {}
    for ln, pk, src in entries:
        reads_cue = ln["policy"] != "vote"           # the vote never reads its cue: its lineage is the packet's alone
        h = (_digest(*pk), ln["policy"], ln["cue"] if reads_cue else "-", ln["sigma"] if reads_cue else "-")
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], ln["stop"])
            aliases.setdefault(rows[i]["labels"][0], []).append(ln["label"])
            rows[i]["labels"].append(ln["label"])
        else:
            sig[h] = len(rows)
            rows.append({"labels": [ln["label"]], "packet": pk, "policy": ln["policy"], "cue": ln["cue"],
                         "sigma": ln["sigma"], "stop": ln["stop"], "source": src})
        labels[ln["label"]] = sig[h]
        sources[ln["label"]] = src
    return rows, labels, aliases, sources
