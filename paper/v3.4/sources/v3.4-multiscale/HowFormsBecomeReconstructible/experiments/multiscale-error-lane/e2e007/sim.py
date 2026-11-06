"""E2E007's successors: E2E006's renewal under repeated injury, with the response's sign and the injury's target crossed.

generation  e2e002.sim.generation's own source compiled with E2E006's two substitutions, each asserted to apply once: the
            detector call routed to ar006.sim.detect, the one body call routed through field_body(). With no coupling,
            no body injury and no observer set, field_body is dl001.sim.body itself, so the generation is E2E006's and
            E2E003's bit for bit (P66s, Q3). field_body, in order: (1) at the body injury's update, flips the scheduled
            patch in V and E on the body-injured branches (and checks the flip); (2) the coupling (Coupling below) or
            dl001.sim.body; (3) at the observer's updates, records each branch's agreement with its own record on the
            generation's patch (output only).
Coupling    e2e006.sim.Coupling with a signed response: on a "raise" branch the reading gain x (1 + kappa x), E2E006's
            exactly; on a "relax" branch the reading gain / (1 + kappa x); x the exposure after the previous update's step.
lineage     e2e006.sim.lineage's loop for E2E007's rows: each generation a newborn under the future's names, the second
            record and the cue from the incoming record, then the injury by the row's target (memory: the patch flipped in
            the record at update 0, e2e003.sim.injure; body: the same patch flipped in the body at update t_body), the routed
            generation (the field rows in one shared 2 x 4 medium each, reset at the birth), E2E006's reads, the
            diagnostics (the detectors', the injury's own check, the exposures, the observer), the handoff; after the
            generations in fresh_at, the fresh-successor test (field-free, under the fresh names), its final states saved.
packets     e2e006.sim.packets's rule with the response and the target in a row's identity.
"""
from __future__ import annotations

import inspect

import numpy as np

from ar006 import sim as S6
from dl001 import sim as S
from e2e001 import sim as E1
from e2e002 import sim as E2
from e2e003 import sim as E3
from e2e006 import sim as S6E
from msegrid.core import birth
from sr001 import sim as SRS

from . import design as D

DETECT_CALL, BODY_CALL = S6E.DETECT_CALL, S6E.BODY_CALL
_COUPLING = None                          # the coupling of the generation now running (None: no field)
_BODY = None                              # the body injury of the generation now running: {"t", "M", "ok"} (None: none)
_OBS = None                               # the observer of the generation now running: {"m", "at", "agree"} (None: none)


def field_body(t, V, E, r, thb, z, p, gain, alpha, G):
    """dl001.sim.body, with the generation's body injury, coupling and observer where set."""
    if _BODY is not None and t == _BODY["t"]:
        M = _BODY["M"]
        V0, E0 = V, E
        V, E = np.where(M, -V, V), np.where(M, -E, E)
        _BODY["ok"] = (np.all(np.where(M, V == -V0, V == V0), axis=(-2, -1))
                       & np.all(np.where(M, E == -E0, E == E0), axis=(-2, -1)))
    out = S.body(V, E, r, thb, z, p, gain, alpha, G) if _COUPLING is None else _COUPLING.body(t, V, E, r, thb, z, p,
                                                                                               gain, alpha, G)
    if _OBS is not None and t in _OBS["at"]:
        m = _OBS["m"]
        _OBS["agree"][_OBS["at"][t]] = (((out[0] > 0) == (r > 0)) & m).sum((-2, -1)) / m.sum((-2, -1))
    return out


def _derive(fn, namespace, subs):
    src = inspect.getsource(fn)
    for old, new in subs:
        if src.count(old) != 1:
            raise RuntimeError(f"{fn.__module__}.{fn.__name__}: '{old}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    exec(compile(src, f"<{fn.__module__}.{fn.__name__}, routed by e2e007>", "exec"), namespace)
    return namespace[fn.__name__]


_NS = dict(vars(E2), detect_vt=S6.detect, field_body=lambda *a: field_body(*a))
generation = _derive(E2.generation, _NS, ((DETECT_CALL, "detect_vt(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])"),
                                          (BODY_CALL, "V, E, Vt, drift, d = field_body(t, V, E, r, thb, buf[i][idx], p, gain, alpha, G)")))
DIAG = E2.DIAG
BIRTH_NAMES, GEN_NAMES = E2.BIRTH_NAMES, E2.GEN_NAMES
FRESH_BIRTH = lambda f, names=D.FRESH["names"]: (lambda g: (*names, "fut", f, "gen", g, "birth"))
FRESH_GEN = lambda f, names=D.FRESH["names"]: (lambda g: tuple((*names, "fut", f, "gen", g, *s) for s in
                                                                (("future",), ("record-noise",), ("bond-noise",),
                                                                 ("record-noise", "B"), ("bond-noise", "B"))))
score, post_damage, birth_cue, groups_of = E1.score, E2.post_damage, E2.birth_cue, E2.groups_of
schedule, injure, injury_ok, packet_of = E3.schedule, E3.injure, E3.injury_ok, E2.packet_of
READS, UNION_READS = E3.READS, E3.UNION_READS
FieldAdapter, field_adapter = S6E.FieldAdapter, S6E.field_adapter


class Coupling(S6E.Coupling):
    """e2e006.sim.Coupling with each group's sign: +1 raise (gain x (1 + kappa x)), -1 relax (gain / (1 + kappa x))."""

    def __init__(self, adapter, groups, n):
        super().__init__(adapter, groups, n)
        self.sign = np.zeros((n, 1, 1))
        for g in groups:
            self.sign[g["branches"]] = g["sign"]

    def body(self, t, V, E, r, thb, z, p, gain, alpha, G):
        x = self.c[:, 0, 0]
        self.sums["full"] += x
        self.sums["early" if t <= self.half else "late"] += x
        active = ((self.lo <= t) & (t <= self.hi))[:, None, None]
        if active.any():
            up = gain * (1.0 + self.kappa * self.c)                    # e2e006.sim.FieldAdapter.respond's, exactly
            down = gain / (1.0 + self.kappa * self.c)
            gain = np.where(active, np.where(self.sign > 0, up, down), gain)
            self.kc += np.where(active, self.kappa * self.c, 0.0)[:, 0, 0]
        out = S.body(V, E, r, thb, z, p, gain, alpha, G)
        emissions = self.adapter.emission(self.adapter.stress(V=out[0], Vt=out[2], drift=out[3], d=out[4], r=r))
        c = np.zeros(V.shape[0])
        for g in self.groups:
            ix = g["branches"]
            c[ix] = g["medium"].step(emissions[ix])
        self.c = c[:, None, None]
        return out


def row_kappa(row):
    """A field row's kappa (Amendment 1): an explicit value (P66k's trials), the matched kappa' (KAPPA_MATCHED, from P66k)
    for kappa_key "matched", else FIELD's kappa."""
    if row.get("kappa") is not None:
        return float(row["kappa"])
    if row.get("kappa_key") == "matched":
        if D.KAPPA_MATCHED is None:
            raise RuntimeError("relax-matched/memory needs KAPPA_MATCHED, fixed by P66k")
        return D.KAPPA_MATCHED
    if row.get("kappa_key") is not None:
        raise ValueError(f"unknown kappa_key {row['kappa_key']!r}")
    return D.FIELD["kappa"]


def coupling_for(adapter, rows, alive, k, kappa=None):
    """The generation's coupling: None when no alive row meets the field; else one fresh shared Medium per field row (the
    eight sheets in rectangle(2, 4)), the row's sign and its kappa (row_kappa; or kappa, an override for every row)."""
    if adapter is None or all(rows[i]["field"] == "none" for i in alive):
        return None
    groups = []
    for j, i in enumerate(alive):
        row = rows[i]
        if row["field"] == "none":
            continue
        groups.append({"branches": np.arange(j * k, (j + 1) * k), "window": (1, D.T_GEN), "medium": adapter.medium(k),
                       "kappa": row_kappa(row) if kappa is None else kappa, "sign": D.SIGN[row["response"]], "row": i})
    return Coupling(adapter, groups, len(alive) * k)


def lineage(body, rows, cases, thf, T, Tf, m0, am, normals, tag, gen_names, birth_names, sched=None, t_gen=D.T_GEN,
            keep=(), configs=None, field=None, fresh_names=None, fresh_birth=None, fresh_at=(), kappa=None,
            save_fresh=False, observe=True, body_masks=None, scored=True, obs_at=None):
    """rows: dicts {"packet", "policy", "sigma", "stop", "injured", "target", "response", "field"[, "kappa_key",
    "kappa"]}. field: a FieldAdapter (None: every row field-free). Under sched, an injured row is injured each generation
    by its target: "memory" (the patch flipped in the record at update 0), "body" (the patch flipped in V and E at update
    t_gen // BODY_FRAC). kappa: an override for every field row (the bridge's 0); else each row's (row_kappa). observe: the
    observer on (output only), at obs_at ({update: name}; default D.obs_updates). body_masks: {g: (n, side, side)}
    replacing the body injury's masks (the bridge's empty patch). scored False: no read and no fresh test is computed
    (P66k, P66h). Returns the reads of every generation, the rows alive at each, the diagnostics, the states kept and the
    fresh successors' reads; with save_fresh, kept["x<g>"] holds their final states."""
    global _COUPLING, _BODY, _OBS
    configs = D.POLICIES if configs is None else configs
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, diags, kept, fresh = {}, {}, {}, {}, {}
    union = m0.copy()
    tb = D.t_body(t_gen)
    at = {u: name for name, u in D.obs_updates(t_gen).items()} if obs_at is None else dict(obs_at)
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
            aval[sl] = birth_cue(A_[4][sl], normals, rows[i]["sigma"])
        P = {"am": am[idx], "aval": aval}
        exact = np.where(A_[4] > 0, 1.0, -1.0)
        cue_dis = ((aval != exact) & P["am"]).sum((-2, -1)).reshape(len(alive), k)
        mg = m0 if sched is None else sched[g]
        inj, Mb = None, None
        if sched is not None:
            union = union | mg
            mem = np.repeat(np.array([bool(rows[i]["injured"]) and rows[i]["target"] == "memory" for i in alive]), k)
            bod = np.repeat(np.array([bool(rows[i]["injured"]) and rows[i]["target"] == "body" for i in alive]), k)
            M = mg[idx] & mem[:, None, None]
            before = A_
            A_ = injure(A_, M)
            inj = injury_ok(before, A_, M) & (M.sum((-2, -1)) == np.where(mem, D.SIZE * D.SIZE, 0))
            Mb = (mg[idx] if body_masks is None else body_masks[g]) & bod[:, None, None]
            if bod.any():
                _BODY = {"t": tb, "M": Mb, "ok": np.zeros(len(idx), bool)}
        _COUPLING = coupling_for(field, rows, alive, k, kappa)
        _OBS = {"m": mg[idx], "at": at, "agree": {}} if observe else None
        coupling, body_inj, obs = _COUPLING, _BODY, _OBS
        try:
            V, E, A_, B_, dg = generation(body, groups_of([rows[i]["policy"] for i in alive], k, configs), cases, V, E, A_,
                                          B_, P, mg[idx], thf[idx], tag, gen_names(g), t_gen)
        finally:
            _COUPLING, _BODY, _OBS = None, None, None
        diags[g] = {key: dg[key].reshape(len(alive), k) for key in DIAG}
        diags[g]["cue_dis_birth"] = cue_dis
        if inj is not None:
            bok = np.ones(len(idx), bool)
            if body_inj is not None:
                n_body = np.where(bod, D.SIZE * D.SIZE, 0) if body_masks is None else Mb.sum((-2, -1))
                bok = np.where(bod, body_inj["ok"] & (Mb.sum((-2, -1)) == n_body), True)
            diags[g]["injury_ok"] = np.where(mem, inj, np.where(bod, bok, inj)).reshape(len(alive), k)
            diags[g]["body_injury_ok"] = bok.reshape(len(alive), k)
        if coupling is not None:
            diags[g].update({key: v.reshape(len(alive), k) for key, v in coupling.summary(t_gen).items()})
        if obs is not None:
            for name, v in obs["agree"].items():                  # in the order the updates came
                diags[g][f"agree_{name}"] = v.reshape(len(alive), k)
        if scored:
            Tb, Tfb = T[idx], Tf[:, idx]
            so = score(V, A_[4], Tb, Tfb, mg[idx])
            su = score(V, A_[4], Tb, Tfb, union[idx])
            reads[g] = {key: so[e].reshape(len(alive), k) for key, e in READS.items()}
            reads[g].update({key: su[e].reshape(len(alive), k) for key, e in UNION_READS.items()})
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        A_, _ = SRS.handoff(A_, None)
        if scored and g in fresh_at:
            fresh[g], fst = fresh_test(body, A_, cases, alive, k, thf, T, Tf, union, normals, am, tag, fresh_names(g),
                                       fresh_birth(g), t_gen, configs)
            if save_fresh:
                kept[f"x{g}"] = dict(fst, rows=list(alive))
    return reads, alive_at, diags, kept, fresh


def fresh_test(body, A_out, cases, alive, k, thf, T, Tf, union, normals, am, tag, names, birth_names, t_gen, configs):
    """e2e006.sim.fresh_test with E2E007's generation (no coupling, no body injury, no observer: E2E006's bit for bit): a
    field-free newborn reading each alive row's outgoing record for one generation (the vote, no injury, no medium), scored
    on the union and whole-sheet; its final state (V, r, H, W after the last update)."""
    idx = np.tile(np.arange(k), len(alive))
    V = birth(tag, cases, *birth_names, side=D.SIDE)[idx].copy()
    E = V.copy()
    A_ = tuple(x.copy() for x in A_out)
    B_ = tuple(x.copy() for x in A_)
    P = {"am": am[idx], "aval": birth_cue(A_[4], normals, 0.0)}
    V, E, A_, B_, _dg = generation(body, groups_of([D.FRESH["policy"]] * len(alive), k, configs), cases, V, E, A_, B_, P,
                                   union[idx], thf[idx], tag, names, t_gen)
    su = score(V, A_[4], T[idx], Tf[:, idx], union[idx])
    out = {key: su[e].reshape(len(alive), k) for key, e in UNION_READS.items()}
    out.update({"a_v": su["a_v"].reshape(len(alive), k), "q_v": su["q_v"].reshape(len(alive), k),
                "a_r": su["a_r"].reshape(len(alive), k), "q_r": su["q_r"].reshape(len(alive), k)})
    return out, {"V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8), "W": A_[1].astype(np.int8)}


def packets(raw, meta, cases, V0, ema0, R0, T, lineages):
    """The task's distinct rows and, for each label, the row it runs on; the alias table; the packets' sources. As
    e2e006.sim.packets, a row's identity being its packet, policy, injury, target, response and kappa (its kappa_key and
    any explicit value: Amendment 1)."""
    rows, labels, aliases, sources, sig = [], {}, {}, {}, {}
    for ln in lineages:
        pk, src = packet_of(ln["packet"], raw, meta, cases, V0, ema0, R0, T)
        if pk is None:
            continue
        pk = tuple(np.asarray(x, dtype=float) for x in pk)
        h = (E2._digest(*pk), ln["policy"], bool(ln["injured"]), ln["target"], ln["response"], ln.get("kappa_key"),
             ln.get("kappa"))
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], ln["stop"])
            aliases.setdefault(rows[i]["labels"][0], []).append(ln["label"])
            rows[i]["labels"].append(ln["label"])
        else:
            sig[h] = len(rows)
            rows.append({"labels": [ln["label"]], "packet": pk, "policy": ln["policy"], "sigma": ln["sigma"],
                         "stop": ln["stop"], "injured": bool(ln["injured"]), "target": ln["target"],
                         "response": ln["response"], "field": ln["field"], "medium": ln["medium"], "window": ln["window"],
                         "kappa_key": ln.get("kappa_key"), "kappa": ln.get("kappa"), "source": src})
        labels[ln["label"]] = sig[h]
        sources[ln["label"]] = src
    return rows, labels, aliases, sources
