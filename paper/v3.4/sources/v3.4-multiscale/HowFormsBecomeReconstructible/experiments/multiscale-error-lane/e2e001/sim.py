"""E2E001's successors: SR001's lineage machinery at the AR tissue's clock, started from restored generation-0 packets.

generation    sr001.sim.generation's own source, compiled in a copy of sr001.sim's namespace with its one
              lr004.sim.relations call given eta=_ETA (ar005.sim.derive: the substitution is asserted to apply exactly
              once). GENERATION runs at the AR tissue's clock (3e-4); GENERATION_SR001 at SR001's own (1e-2), where it is
              SR001's generation (the bridge, checks Q3).
lineage       SR001's lineage (sr001.sim.lineage) adapted: each row (a packet for every case of the task) starts from its
              own packet (r, H, W; the strengths at STRENGTH0 x sign, as at SR001's G0 and every handoff); the births and
              streams are named by the caller (a future's names, or SR001's own for the bridge); rows marked persist
              ("uninterrupted, approximate") keep their body, moving average and bond strengths and are never handed off;
              rows stop at their own last generation; the handoff is sr001.sim.handoff, unchanged.
packets       a task's rows from its restored raw file: every policy arm's first record at t = 8,000, protected storage
              (R0 with edges_from(bonds(R0, True))), post-damage copying (ar001.sim.event's record under the record's own
              tag), the Q-like capture (R_STAR x sign(V) with its bonds), the foreign rows (the packet of the case PERM
              maps to), disabled reading (the protected packet at gain 0) and the uninterrupted rows (the policy's packet
              with its saved body). Identical rows run once (aliases), every arm they stand for named.
score         the endpoints at a generation's last update (PLAN_E2E001.md): the patch scores relative to the sheet's own
              orientation, the whole-sheet inversion-invariant agreement and SR001's history specificity q.
"""
from __future__ import annotations

import numpy as np

from ar001 import sim as A1S
from ar005.sim import derive
from dl001 import sim as S
from lr001.sim import edges_from
from lr005 import sim as L5S
from msegrid.core import R_STAR, birth, bonds
from sr001 import design as SRD
from sr001 import sim as SRS

from . import design as D


def _derived(eta):
    ns = dict(vars(SRS))
    ns["_ETA"] = eta
    return derive(SRS.generation, ns, old="V, P, aval)", new="V, P, aval, eta=_ETA)")


GENERATION = _derived(D.CLOCK["eta"])
GENERATION_SR001 = _derived(SRD.ETA)

BIRTH_NAMES = lambda f: (lambda g: ("e2e", "fut", f, "gen", g, "birth"))
GEN_NAMES = lambda f: (lambda g: (("e2e", "fut", f, "gen", g, "future"), ("e2e", "fut", f, "gen", g, "record-noise"),
                                  ("e2e", "fut", f, "gen", g, "bond-noise"), ("e2e", "fut", f, "gen", g, "record-noise", "B"),
                                  ("e2e", "fut", f, "gen", g, "bond-noise", "B")))
SR001_BIRTH = lambda g: ("gen", g, "birth")
SR001_NAMES = SRS.GEN_NAMES
ENDPOINTS = ("u_r", "u_v", "u_r_raw", "a_r", "a_v", "q_r", "q_v", "agree_in")


def orient(x, T):
    """+1 where the sheet agrees with T on at least half its cells, else -1 (a record of relations holds a pattern only
    up to its global sign)."""
    return np.where(S.sign(x, T) >= 0.5, 1.0, -1.0)


def inv(a):
    return np.maximum(a, 1 - a)


def score(V, r, T, Tf, m):
    """The endpoints of every branch: (n,) arrays. T, m: (n, side, side); Tf: (nforeign, n, side, side)."""
    sr, sv = orient(r, T)[:, None, None], orient(V, T)[:, None, None]
    a_r, a_v = inv(S.sign(r, T)), inv(S.sign(V, T))
    af_r = np.max([inv(S.sign(r, t)) for t in Tf], axis=0)
    af_v = np.max([inv(S.sign(V, t)) for t in Tf], axis=0)
    return {"u_r": L5S.inside(sr * r, T, m), "u_v": L5S.inside(sv * V, T, m), "u_r_raw": L5S.inside(r, T, m),
            "a_r": a_r, "a_v": a_v, "q_r": (a_r - af_r) / (1 - D.C_Q), "q_v": (a_v - af_v) / (1 - D.C_Q),
            "agree_in": (((V > 0) == (r > 0)) & m).sum((-2, -1)) / m.sum((-2, -1))}


def lineage(body, rows, cases, packet, thf, T, Tf, m, H0, W0, tag, gen_names, birth_names, t_gen=D.T_GEN,
            horizons=D.HORIZONS, gen_fn=None, keep=()):
    """rows: dicts {"route", "stop", "persist", "V0" (cases, side, side) or None}, in the order of `packet`.
    packet: (H, W, r), each (rows x cases, side, side), row-major. thf: (cases, side, side) the environment field (th x
    theta). Returns {g: {endpoint: (rows alive at g, cases)}} at the horizons, the row indices alive at each, and the
    states kept at the generations in `keep` ({g: {"rows", "V", "r", "H", "W"}})."""
    gen_fn = GENERATION if gen_fn is None else gen_fn
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.asarray(x, dtype=float) for x in packet)
    two = [i for i in alive if rows[i]["route"].two]
    A = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    B = None
    if two:
        sel = np.concatenate([np.arange(i * k, (i + 1) * k) for i in two])
        B = tuple(x[sel].copy() for x in A)
    V = E = None
    reads, alive_at, kept = {}, {}, {}
    for g in range(1, max(row["stop"] for row in rows) + 1):
        still = [i for i in alive if rows[i]["stop"] >= g]
        if still != alive:
            if two:
                raise ValueError("rows with a second record must all run to the last generation")
            sel = np.concatenate([np.arange(alive.index(i) * k, (alive.index(i) + 1) * k) for i in still])
            A = tuple(x[sel] for x in A)
            V, E = V[sel], E[sel]
            alive = still
        routes = [rows[i]["route"] for i in alive]
        idx = np.tile(np.arange(k), len(alive))
        pers = np.repeat([bool(rows[i].get("persist")) for i in alive], k)[:, None, None]
        newborn = birth(tag, cases, *birth_names(g), side=D.SIDE)[idx].copy()
        if g == 1:
            V = newborn.copy()
            for j, i in enumerate(alive):
                if rows[i].get("V0") is not None:
                    V[j * k:(j + 1) * k] = rows[i]["V0"]
            E = V.copy()
        else:
            V = np.where(pers, V, newborn)
            E = np.where(pers, E, newborn)
        Tb, Tfb, mb, thb = T[idx], Tf[:, idx], m[idx], thf[idx]
        V, E, A, B, _out = gen_fn(body, routes, cases, V, E, A, B, tag, gen_names(g), t_gen, set(), Tb, Tfb, H0[idx], W0[idx],
                                  thb)
        if g in horizons:
            sc = score(V, A[4], Tb, Tfb, mb)
            reads[g] = {key: v.reshape(len(alive), k) for key, v in sc.items()}
            alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A[4].copy(), "H": A[0].astype(np.int8),
                       "W": A[1].astype(np.int8)}
        A2, B = SRS.handoff(A, B)
        A = (A2[0], A2[1], np.where(pers, A[2], A2[2]), np.where(pers, A[3], A2[3]), A2[4])
    return reads, alive_at, kept, (V, E, A, B)


def q_capture(V):
    """The Q-like capture of a body: R_STAR x sign(V), with its bonds."""
    rq = R_STAR * np.where(V > 0, 1.0, -1.0)
    Hq, Wq = edges_from(bonds(rq, True))
    return Hq, Wq, rq


def protected(R0):
    H0, W0 = edges_from(bonds(R0, True))
    return H0, W0, R0.copy()


def post_damage(situation, cases, V0, ema0, R0, T, tag, size=D.SIZE):
    """ar001.sim.event's record (sigma 0: the record's damage does not depend on the misread)."""
    base, _sigma = situation.split("@")
    ev = A1S.event(base, size, 0.0, cases, V0, ema0, R0, T, tag)
    return (ev["H"], ev["W"], ev["r"]), ev["m"]


def perm_index(cases):
    """For every case, the index of the case PERM maps it to (same block and parent, message PERM(m))."""
    pos = {c.key(): j for j, c in enumerate(cases)}
    return np.array([pos[(c.block, D.PERM(c.message), c.parent)] for c in cases])


def packets(raw, meta, cases, V0, ema0, R0, T, situations, tag, side_stop=D.G_SIDE, main_stop=D.G_MAIN):
    """The task's distinct rows and, for each arm label, the row it runs on. raw: the restored raw file's arrays; meta:
    its __meta__. Returns rows (dicts with the packet), labels {label: row index} and the alias table."""
    k = len(cases)
    arms_of = {name: list(arms) for name, arms in meta["runs"]}
    H0, W0, r0 = protected(R0)
    entries = []                                      # (label, (H, W, r), stop, route, persist, V0)
    entries.append(("protected", (H0, W0, r0), main_stop, D.ROUTE, False, None))
    post = {}
    for sit in situations:
        base = sit.split("@")[0]
        stop = main_stop if sit in D.MAIN else side_stop
        if D.RECORD_HIT[base]:
            pk, _m = post_damage(sit, cases, V0, ema0, R0, T, meta["tag"])
            post[sit] = pk
            entries.append((f"post/{sit}", pk, stop, D.ROUTE, False, None))
        else:
            entries.append((f"post/{sit}", (H0, W0, r0), stop, D.ROUTE, False, None))
        for arm in D.POLICIES:
            src = sit if arm in arms_of.get(sit, []) else (sit.replace("@1", "@0") if arm == "vote" else None)
            if src is None or arm not in arms_of.get(src, []):
                continue
            j = arms_of[src].index(arm)
            pk = (raw[f"{src}/H"][j], raw[f"{src}/W"][j], raw[f"{src}/r"][j])
            entries.append((f"{arm}/{sit}", pk, stop, D.ROUTE, False, None))
    # the controls and the second boundary (memory@0), to the side horizon
    mem = "memory@0"
    pi = perm_index(cases)
    lab = {e[0]: e for e in entries}
    entries.append(("foreign/protected", tuple(x[pi] for x in (H0, W0, r0)), side_stop, D.ROUTE, False, None))
    if f"{D.CONTROLLER}/{mem}" in lab:
        pk = lab[f"{D.CONTROLLER}/{mem}"][1]
        entries.append((f"foreign/{D.CONTROLLER}/{mem}", tuple(x[pi] for x in pk), side_stop, D.ROUTE, False, None))
    entries.append(("noread/protected", (H0, W0, r0), side_stop, D.NOREAD, False, None))
    for arm in D.POLICIES:
        if f"{arm}/{mem}" not in lab or arm not in arms_of.get(mem, []):
            continue
        Vg = raw[f"{mem}/V"][arms_of[mem].index(arm)]
        entries.append((f"unint/{arm}/{mem}", lab[f"{arm}/{mem}"][1], side_stop, D.ROUTE, True, Vg))
        entries.append((f"Q/{arm}/{mem}", q_capture(Vg), side_stop, D.ROUTE, False, None))
    # aliases: identical (packet, route, persist, start body) run once, to the longest stop among them
    rows, labels, aliases = [], {}, {}
    sig = {}
    for label, pk, stop, route, persist, Vg in entries:
        H, W, r = (np.asarray(x, dtype=float) for x in pk)
        h = (route.name, persist,
             _digest(H, W, r, Vg))
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], stop)
            aliases.setdefault(rows[i]["labels"][0], []).append(label)
            rows[i]["labels"].append(label)
        else:
            sig[h] = len(rows)
            rows.append({"labels": [label], "packet": (H, W, r), "stop": stop, "route": route, "persist": persist,
                         "V0": None if Vg is None else np.asarray(Vg, dtype=float)})
        labels[label] = sig[h]
    return rows, labels, aliases


def _digest(H, W, r, Vg):
    import hashlib
    h = hashlib.sha256()
    for x in (H, W, r) + (() if Vg is None else (np.asarray(Vg, dtype=float),)):
        h.update(np.ascontiguousarray(x).tobytes())
    return h.hexdigest()
