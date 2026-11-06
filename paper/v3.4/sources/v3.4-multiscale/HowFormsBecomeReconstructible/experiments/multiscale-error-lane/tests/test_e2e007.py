"""E2E007's unit tests (engineering records only: AR006's debug block 900948 and P57's 900917, packets only; short
generations of 300 updates; no outcome value is read)."""
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from e2e002 import sim as E2  # noqa: E402
from e2e003 import sim as E3  # noqa: E402
from e2e006 import design as D6  # noqa: E402
from e2e006 import sim as S6E  # noqa: E402
from e2e007 import design as D  # noqa: E402
from e2e007 import sim  # noqa: E402
from e2e007 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

TG = 300                                          # a short generation: the body injury at update 75
LABELS = tuple(x["label"] for x in D.ROWS)


def _task(body="dw", unit="F0_t1", block=900948, source="ar006/debug"):
    raw, meta, _rf = W.load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am, normals = L5S.anchor_mask(cases, meta["tag"]), GCS.unit_normals(cases, meta["tag"])
    return dict(raw=raw, meta=meta, cases=cases, V0=V0, ema0=ema0, R0=R0, thf=th * theta, T=T, Tf=Tf, m0=m0, am=am,
                normals=normals, body=body)


@pytest.fixture(scope="module")
def t():
    return _task()


def _rows(t, labels, stop=2, **over):
    lins = [dict(x, stop=stop, **over) for x in D.ALL if x["label"] in labels]
    rows, lab, _al, _src = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], lins)
    return rows, lab


def _run(t, rows, field, gens=2, T=None, **kw):
    sch = sim.schedule(t["cases"], t["m0"], D.TAG, gens)[0]
    return sim.lineage(t["body"], rows, t["cases"], t["thf"], t["T"] if T is None else T, t["Tf"], t["m0"], t["am"],
                       t["normals"], D.TAG, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sch, t_gen=TG,
                       keep=tuple(range(1, gens + 1)), field=field, **kw)


def _same(k1, i1, k2, i2, g):
    """Row i1's kept state in run 1 equals row i2's in run 2 at generation g (V, r, H, W over the row's eight cases)."""
    a, b = k1[g], k2[g]
    j1, j2 = a["rows"].index(i1), b["rows"].index(i2)
    k = a["V"].shape[0] // len(a["rows"])
    return all(np.array_equal(a[x][j1 * k:(j1 + 1) * k], b[x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))


def _same_reads(o1, i1, o2, i2, g):
    rd1, al1 = o1[0], o1[1]
    rd2, al2 = o2[0], o2[1]
    a, b = al1[g].index(i1), al2[g].index(i2)
    return all(np.array_equal(rd1[g][x][a], rd2[g][x][b]) for x in rd1[g])


def test_rows_as_planned():
    assert LABELS == ("none/memory", "raise/memory", "relax/memory", "none/body", "raise/body", "relax/body")
    for x in D.ROWS:
        assert x["packet"] == "vote/memory@0" and x["policy"] == "vote" and x["sigma"] == 0.0 and x["injured"]
        assert x["stop"] == 8 and (x["field"] == "none") == (x["response"] == "none")
        assert x["field"] in ("none", "shared") and x["medium"] in ("-", "reset")
    assert D.SIGN == {"raise": 1, "relax": -1} and D.FIELD is D6.FIELD and D.FIELD["kappa"] == 1.944
    assert D.STAGES["probe"] == {"ar006/p57": (900917, 900919)} and D.STAGE_TAG["probe"] == "mse-p66"
    assert D.STAGES["preflight"] == {"ar006/preflight": (900929,)} and len(D.stage_tasks("development")) == 128
    assert D.STAGES["debug"] == {"ar006/debug": (900948,)} and D.STAGE_STOP_CAP == {"debug": 3}
    assert D.FRESH_AT == (8,) and D.STAGE_FRESH_AT == {"debug": (3,)} and D.FRESH["names"] == ("e2e007", "fresh")
    assert D.HALVES["probe"] == ((900917,), (900919,))
    # Amendment 1: the matched row, reported only, in phase B and P66x
    assert tuple(x["label"] for x in D.ROWS7) == LABELS + ("relax-matched/memory",) and D.ALL == D.ROWS7
    m = D.MATCHED
    assert (m["response"], m["target"], m["field"], m["medium"], m["kappa_key"]) == ("relax", "memory", "shared",
                                                                                   "reset", "matched")
    assert all(x["kappa_key"] is None for x in D.ROWS)
    assert D.STAGE_LINEAGES["probe"] == D.ROWS and D.STAGE_LINEAGES["probe_x"] == (D.MATCHED,)
    assert all(D.STAGE_LINEAGES[s] == D.ROWS7 for s in ("debug", "preflight", "development"))
    assert D.STAGES["probe_x"] == D.STAGES["probe"] and D.STAGE_TAG["probe_x"] == "mse-p66"
    assert (D.KAPPA_TAG, D.KAPPA_G, D.KAPPA_TRIALS, D.KAPPA_TOL) == ("mse-p66k", 3, (1.0, 1.4, 1.8), 0.002)


def test_body_injury_update_and_observer():
    assert D.t_body() == 2000 and D.obs_updates() == {"pre": 1999, "p80": 2100, "p16": 2500, "p4": 4000, "end": 8000}
    assert D.t_body(TG) == 75 and D.obs_updates(TG) == {"pre": 74, "p80": 78, "p16": 93, "p4": 150, "end": 300}


def test_routed_generation_two_substitutions():
    src = inspect.getsource(E2.generation)
    assert src.count(sim.DETECT_CALL) == 1 and src.count(sim.BODY_CALL) == 1
    assert sim.generation.__globals__["detect_vt"] is S6.detect
    assert sim._COUPLING is None and sim._BODY is None and sim._OBS is None


def test_packets_six_distinct_rows():
    p = _task("li4", "F0_t0", 900917, "ar006/p57")
    rows, lab, al, _s = sim.packets(p["raw"], p["meta"], p["cases"], p["V0"], p["ema0"], p["R0"], p["T"], D.ROWS)
    assert len(rows) == 6 and al == {} and sorted(lab) == sorted(LABELS)
    assert all(np.array_equal(rows[0]["packet"][x], r["packet"][x]) for r in rows for x in range(3))   # one packet


def test_signed_response(monkeypatch):
    """raise: the reading gain x (1 + kappa x), E2E006's FieldAdapter.respond's exactly; relax: gain / (1 + kappa x),
    never below 0, symmetric in log gain; a branch in no group keeps its gain."""
    ad = sim.field_adapter()
    rows = [{"field": "shared", "response": "raise"}, {"field": "shared", "response": "relax"},
            {"field": "none", "response": "none"}]
    c = sim.coupling_for(ad, rows, [0, 1, 2], 8)
    assert [g["sign"] for g in c.groups] == [1, -1] and c.sign[16:].sum() == 0
    x = np.random.default_rng(7).uniform(0.0, 2.0, 24)
    c.c = x[:, None, None]
    seen = {}

    def fake(V, E, r, thb, z, p, gain, alpha, G):
        seen["gain"] = np.broadcast_to(gain, (24, 1, 1)).copy()
        return V, E, V, None, None

    monkeypatch.setattr(sim.S, "body", fake)
    V = np.ones((24, 4, 4))
    c.body(1, V, V.copy(), V.copy(), 0, None, 0, 1.5, 0.1, None)
    kap = D.FIELD["kappa"]
    want_up, _t, _p = S6E.FieldAdapter(None).respond(x[:8, None, None], np.ones((8, 1, 1), bool), kap, gain=1.5, thb=0,
                                                      p=0)
    assert np.array_equal(seen["gain"][:8], want_up)
    assert np.array_equal(seen["gain"][8:16], 1.5 / (1.0 + kap * x[8:16, None, None]))
    assert (seen["gain"][8:16] > 0).all()
    assert np.allclose(np.log(1.5 * (1.0 + kap * x[8:16])) + np.log(seen["gain"][8:16, 0, 0]), 2 * np.log(1.5))
    assert np.array_equal(seen["gain"][16:], np.full((8, 1, 1), 1.5))


def test_body_injury_flips_the_patch_in_V_and_E_only(monkeypatch):
    seen = []

    def fake(V, E, r, thb, z, p, gain, alpha, G):
        seen.append((V.copy(), E.copy(), r.copy()))
        return V, E, V, None, None

    monkeypatch.setattr(sim.S, "body", fake)
    rng = np.random.default_rng(3)
    V, E, r = rng.normal(size=(4, 6, 6)), rng.normal(size=(4, 6, 6)), np.sign(rng.normal(size=(4, 6, 6)))
    M = np.zeros((4, 6, 6), bool)
    M[0, 1:3, 2:4] = True
    M[2, 4:6, 0:2] = True
    sim._BODY = {"t": 5, "M": M, "ok": np.zeros(4, bool)}
    try:
        sim.field_body(4, V, E, r, 0, None, 0, 1.0, 0.1, None)
        sim.field_body(5, V, E, r, 0, None, 0, 1.0, 0.1, None)
        sim.field_body(6, V, E, r, 0, None, 0, 1.0, 0.1, None)
        ok = sim._BODY["ok"].copy()
    finally:
        sim._BODY = None
    (V4, E4, r4), (V5, E5, r5), (V6, E6, _r6) = seen
    assert np.array_equal(V4, V) and np.array_equal(E4, E) and np.array_equal(V6, V) and np.array_equal(E6, E)
    assert np.array_equal(V5, np.where(M, -V, V)) and np.array_equal(E5, np.where(M, -E, E))
    assert np.array_equal(r4, r) and np.array_equal(r5, r) and ok.all()


def test_memory_rows_are_e2e006s(t):
    """none/memory and raise/memory equal e2e006.sim.lineage's vote/none and vote/shared (reads, E2E006's diagnostics,
    states) under repeated injury, two short generations."""
    rows7, lab7 = _rows(t, ("none/memory", "raise/memory"))
    lins6 = [dict(x, stop=2) for x in D6.ALL if x["label"] in ("vote/none", "vote/shared")]
    rows6, lab6, _a, _s = S6E.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], lins6)
    ad = sim.field_adapter()
    o7 = _run(t, rows7, ad)
    sch = sim.schedule(t["cases"], t["m0"], D.TAG, 2)[0]
    o6 = S6E.lineage(t["body"], rows6, t["cases"], t["thf"], t["T"], t["Tf"], t["m0"], t["am"], t["normals"], D.TAG,
                     sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sch, t_gen=TG, keep=(1, 2), field=S6E.field_adapter())
    for mine, theirs in (("none/memory", "vote/none"), ("raise/memory", "vote/shared")):
        i7, i6 = lab7[mine], lab6[theirs]
        for g in (1, 2):
            assert _same(o7[3], i7, o6[3], i6, g) and _same_reads(o7, i7, o6, i6, g)
            a, b = o7[1][g].index(i7), o6[1][g].index(i6)
            assert all(np.array_equal(o7[2][g][x][a], o6[2][g][x][b]) for x in o6[2][g])


def test_field_free_memory_row_is_e2e003s(t):
    rows, lab = _rows(t, ("none/memory",))
    sch = sim.schedule(t["cases"], t["m0"], D.TAG, 2)[0]
    args = (t["body"], rows, t["cases"], t["thf"], t["T"], t["Tf"], t["m0"], t["am"], t["normals"], D.TAG,
            sim.GEN_NAMES(0), sim.BIRTH_NAMES(0))
    r3, _a3, d3, k3 = E3.lineage(*args, sched=sch, t_gen=TG, keep=(2,))
    r7, _a7, d7, k7, _f7 = sim.lineage(*args, sched=sch, t_gen=TG, keep=(2,), field=None)
    for g in (1, 2):
        assert all(np.array_equal(r3[g][x], r7[g][x]) for x in r3[g])
        assert all(np.array_equal(d3[g][x], d7[g][x]) for x in d3[g])
    assert all(np.array_equal(k3[2][x], k7[2][x]) for x in ("V", "r", "H", "W"))


def test_the_injury_by_target(t, monkeypatch):
    """At generation 1: a memory row enters the generation with the patch flipped in its record (e2e003.sim.injure), a
    body row with its record intact; the body rows' patch is flipped in the body at t_body (the check holds), the memory
    rows' never; the injury's check holds on every row."""
    rows, lab = _rows(t, LABELS, stop=1)
    seen = []
    real = sim.generation

    def spy(*a, **kw):
        seen.append((tuple(x.copy() for x in a[5]), None if sim._BODY is None else sim._BODY["M"].copy()))
        return real(*a, **kw)

    monkeypatch.setattr(sim, "generation", spy)
    rd, al, dg, kp, _f = _run(t, rows, sim.field_adapter(), gens=1)
    (A_in, Mb), = seen
    k = 8
    H, Wm, r = (np.asarray(x, dtype=float) for x in rows[0]["packet"])
    clean = (H, Wm, D.STRENGTH0 * H, D.STRENGTH0 * Wm, r)
    m1 = sim.schedule(t["cases"], t["m0"], D.TAG, 1)[0][1]
    hurt = sim.injure(tuple(x.copy() for x in clean), m1)
    for label, i in lab.items():
        sl = slice(i * k, (i + 1) * k)
        want = hurt if label.endswith("/memory") else clean
        assert all(np.array_equal(x[sl], y) for x, y in zip(A_in, want))
        assert np.array_equal(Mb[sl], m1 if label.endswith("/body") else np.zeros_like(m1))
    assert dg[1]["injury_ok"].all() and dg[1]["body_injury_ok"].all()


def test_kappa0_empty_patch_and_observer(t):
    """relax and raise at kappa 0 equal none; a body row with its patch emptied equals the row uninjured; the observer is
    output only (off equals on)."""
    rows, lab = _rows(t, LABELS)
    ad = sim.field_adapter()
    o0 = _run(t, rows, ad, kappa=0.0)
    for a, b in (("relax/memory", "none/memory"), ("relax/body", "none/body"), ("raise/body", "none/body")):
        for g in (1, 2):
            assert _same(o0[3], lab[a], o0[3], lab[b], g) and _same_reads(o0, lab[a], o0, lab[b], g)
    empty = {g: np.zeros((len(rows) * 8, D.SIDE, D.SIDE), bool) for g in (1, 2)}
    oe = _run(t, rows, ad, body_masks=empty)
    ru, lu = _rows(t, ("none/body", "raise/body", "relax/body"), injured=False)
    ou = _run(t, ru, ad)
    for x in ("none/body", "raise/body", "relax/body"):
        for g in (1, 2):
            assert _same(oe[3], lab[x], ou[3], lu[x], g) and _same_reads(oe, lab[x], ou, lu[x], g)
    on = _run(t, rows, ad)
    off = _run(t, rows, ad, observe=False)
    for g in (1, 2):
        assert all(np.array_equal(on[3][g][x], off[3][g][x]) for x in ("V", "r", "H", "W"))
        assert all(np.array_equal(on[0][g][x], off[0][g][x]) for x in on[0][g])
        assert set(off[2][g]) <= set(on[2][g]) and all(np.array_equal(on[2][g][x], off[2][g][x]) for x in off[2][g])
        assert {f"agree_{o}" for o in D.OBS} <= set(on[2][g]) and not any(x.startswith("agree_") for x in off[2][g])
    # the response acted: raise and relax differ from none, and from each other, under each target
    for tg in ("memory", "body"):
        n, u, d = (lab[f"{x}/{tg}"] for x in ("none", "raise", "relax"))
        assert not _same(on[3], u, on[3], n, 1) and not _same(on[3], d, on[3], n, 1) and not _same(on[3], u, on[3], d, 1)


def test_mixed_call_and_pairing(t):
    """A field-free row in a mixed call equals its field-free run; reversing the rows changes no row's output."""
    rows, lab = _rows(t, LABELS)
    ad = sim.field_adapter()
    om = _run(t, rows, ad)
    free = [rows[lab["none/memory"]], rows[lab["none/body"]]]
    of = _run(t, free, None)
    for j, x in enumerate(("none/memory", "none/body")):
        for g in (1, 2):
            assert _same(om[3], lab[x], of[3], j, g) and _same_reads(om, lab[x], of, j, g)
    rev = list(reversed(range(len(rows))))
    orv = _run(t, [rows[i] for i in rev], ad)
    for i in range(len(rows)):
        j = rev.index(i)
        for g in (1, 2):
            assert _same(om[3], i, orv[3], j, g) and _same_reads(om, i, orv, j, g)
            a, b = om[1][g].index(i), orv[1][g].index(j)
            assert all(np.array_equal(om[2][g][x][a], orv[2][g][x][b]) for x in om[2][g])


def test_target_and_mask_never_reach_the_tissue(t, monkeypatch):
    """The information boundary: another target, or another patch mask given to the generation, leaves every state and
    exposure unchanged (the scoring reads the target; the injuries are the schedule's)."""
    rows, _lab = _rows(t, ("raise/memory", "relax/body", "none/body"))
    ad = sim.field_adapter()
    r1, _a1, d1, k1, _f1 = _run(t, rows, ad)
    r2, _a2, d2, k2, _f2 = _run(t, rows, ad, T=np.roll(t["T"], 7, -1))
    assert not np.array_equal(r1[2]["a_v"], r2[2]["a_v"])
    real = sim.generation

    def other_mask(*a, **kw):
        a = list(a)
        a[8] = np.roll(a[8], 9, -1)
        return real(*a, **kw)

    monkeypatch.setattr(sim, "generation", other_mask)
    r3, _a3, d3, k3, _f3 = _run(t, rows, ad)
    fx = ("exp_full", "exp_early", "exp_late", "kexp")
    for g in (1, 2):
        for kk, dd in ((k2, d2), (k3, d3)):
            assert all(np.array_equal(k1[g][x], kk[g][x]) for x in ("V", "r", "H", "W"))
            assert all(np.array_equal(d1[g][x], dd[g][x]) for x in fx)


def test_fresh_successors_saved_and_rescored():
    """A short debug task: the fresh successors after generation 3 are saved (V, r, H, W, rows) and re-score to their
    fresh reads bit for bit; the shards hold the observer and the body injury's check."""
    lins = [x for x in D.ROWS if x["label"] in ("relax/memory", "raise/body")]
    e, s, m, b = W.task("ar006/debug", "dw", "F0_t1", 900948, "debug", lineages=lins, t_gen=TG)
    assert all(b.values()) and m["fresh_at"] == [3] and m["t_body"] == 75
    assert {f"f0/x3/{x}" for x in ("V", "r", "H", "W", "rows")} <= set(s)
    assert {f"f0/d3/agree_{o}" for o in D.OBS} | {"f0/d3/body_injury_ok"} <= set(e)
    p = _task()
    sched = sim.schedule(p["cases"], p["m0"], D.TAG, 3)[0]
    rows = list(s["f0/x3/rows"])
    idx = np.tile(np.arange(8), len(rows))
    union = p["m0"] | sched[1] | sched[2] | sched[3]
    su = sim.score(s["f0/x3/V"], s["f0/x3/r"], p["T"][idx], p["Tf"][:, idx], union[idx])
    assert all(np.array_equal(su[src].reshape(len(rows), 8), e[f"f0/x3/{x}"]) for x, src in sim.UNION_READS.items())
    assert all(np.array_equal(su[x].reshape(len(rows), 8), e[f"f0/x3/{x}"]) for x in ("a_v", "q_v", "a_r", "q_r"))


def test_reader_parts():
    from e2e007 import predict as PR
    ps = PR.parts()
    assert [p for p, _w, _f, _k in ps] == ["Z1", "Z2", "Z3", "Z4", "Z5", "Z1x", "Z3x"]
    assert [k for _p, _w, _f, k in ps] == ["ge", "ge", "le", "ge", "le", "ge", "le"]     # Z3, Z3x reversed (Amendment 1)
    assert PR.TH == {"Z1": 0.17, "Z2": 0.09, "Z3": 0.02, "Z4": 0.07, "Z5": -0.03, "Z1x": 0.19, "Z3x": -0.01}
    assert all(PR.registers(k, PR.TH[p]) for p, _w, _f, k in ps)
    assert PR.registers("ge", 0.01) and not PR.registers("ge", 0.0) and PR.registers("le", 0.05)
    assert not PR.registers("le", 0.06)
    assert PR.narrowest(0.0687, 0.0101, [0.0712, 0.0662], "ge") == 0.05
    ids = [r for r, _w, _f in PR.reported()]
    assert len(ids) == len(set(ids))


def test_row_kappa(monkeypatch):
    """Amendment 1: a field row's kappa is an explicit value, the matched kappa' or FIELD's; the matched row refuses to run
    before P66k fixes kappa'."""
    assert sim.row_kappa(D._A["raise/body"]) == D.FIELD["kappa"] == sim.row_kappa(D._A["relax/memory"])
    assert sim.row_kappa(dict(D.MATCHED, kappa_key=None, kappa=1.4)) == 1.4
    monkeypatch.setattr(D, "KAPPA_MATCHED", None)
    with pytest.raises(RuntimeError):
        sim.row_kappa(D.MATCHED)
    monkeypatch.setattr(D, "KAPPA_MATCHED", 1.234)
    assert sim.row_kappa(D.MATCHED) == 1.234
    with pytest.raises(ValueError):
        sim.row_kappa(dict(D.MATCHED, kappa_key="other"))


def test_matched_row_identity_and_kappa(t, monkeypatch):
    """The matched row is its own row (its kappa in its identity) and meets the field at kappa'; the others keep 1.944."""
    monkeypatch.setattr(D, "KAPPA_MATCHED", 1.3)
    lins = [dict(x, stop=2) for x in D.ROWS7]
    rows, lab, al, _s = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], lins)
    assert len(rows) == 7 and al == {} and lab["relax-matched/memory"] != lab["relax/memory"]
    c = sim.coupling_for(sim.field_adapter(), rows, list(range(7)), 8)
    got = {g["row"]: (g["kappa"], g["sign"]) for g in c.groups}
    assert got[lab["relax-matched/memory"]] == (1.3, -1) and got[lab["relax/memory"]] == (D.FIELD["kappa"], -1)
    assert got[lab["raise/body"]] == (D.FIELD["kappa"], 1) and len(got) == 5
    o = _run(t, [rows[lab["relax/memory"]], rows[lab["relax-matched/memory"]]], sim.field_adapter())
    assert not _same(o[3], 0, o[3], 1, 1)                          # a different kappa, a different lineage
    j = o[1][1].index(1)
    assert np.allclose(o[2][1]["kexp"][j], 1.3 * o[2][1]["exp_full"][j], rtol=1e-12, atol=0)


def test_unscored_and_observer_updates(t):
    """lineage(scored=False) computes no read and no fresh test and leaves every state as the scored run's;
    lineage(obs_at=...) records the observer at those updates only."""
    rows, lab = _rows(t, ("raise/body", "none/memory"))
    ad = sim.field_adapter()
    s1 = _run(t, rows, ad)
    s0 = _run(t, rows, ad, scored=False, fresh_names=sim.FRESH_GEN(0), fresh_birth=sim.FRESH_BIRTH(0), fresh_at=(2,))
    assert s0[0] == {} and s0[4] == {} and s1[0] != {}
    for g in (1, 2):
        assert all(np.array_equal(s1[3][g][x], s0[3][g][x]) for x in ("V", "r", "H", "W"))
    so = _run(t, rows, ad, obs_at={74: "a", 75: "b", 76: "c"})
    assert {x for x in so[2][1] if x.startswith("agree_")} == {"agree_a", "agree_b", "agree_c"}
    assert all(np.array_equal(s1[3][g][x], so[3][g][x]) for g in (1, 2) for x in ("V", "r", "H", "W"))
