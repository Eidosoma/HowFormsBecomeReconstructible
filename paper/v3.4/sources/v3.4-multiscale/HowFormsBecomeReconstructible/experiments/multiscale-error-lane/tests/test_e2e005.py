"""E2E005's tests (engineering; no successor value is read)."""
import inspect
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from e2e004 import sim as E4  # noqa: E402
from e2e005 import design as D  # noqa: E402
from e2e005 import sim  # noqa: E402
from msegrid.core import birth  # noqa: E402

RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"


def _task(source="ar005/p53", body="li4", unit="F0_t1", block=900729):
    root = Path(D.SOURCES[source]["root"])
    M = json.loads((root / "manifest.json").read_text())
    z = np.load(root / M["tasks"][f"{body}/{unit}/{block}"]["files"]["raw"]["path"])
    raw = {k: z[k] for k in z.files if k != "__meta__"}
    meta = json.loads(str(z["__meta__"]))
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    return raw, meta, cases, V0, ema0, R0, th, T, theta


def _first(rows):
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    return (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())


def test_stages_sources_and_lineages():
    assert len(D.stage_tasks("tuning")) == 8 and len(D.stage_tasks("probe")) == 32
    assert len(D.stage_tasks("debug")) == 8 and len(D.stage_tasks("preflight")) == 16
    assert len(D.stage_tasks("development")) == 128
    for stage in D.STAGES:
        for src in D.STAGES[stage]:
            M = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
            for s, b, u, blk in D.stage_tasks(stage):
                if s == src:
                    assert f"{b}/{u}/{blk}" in M["tasks"]
    labels = [x["label"] for x in D.ALL]
    assert len(labels) == len(set(labels)) and len(D.CORE) == 9
    assert {x["route"] for x in D.CORE} == set(D.ROUTES)
    assert not any(x["route"] == "oracle" and x["packet"] == "protected" for x in D.ALL + D.TUNING)
    assert len(D.CANDIDATES) == 16 and list(D.CANDIDATES)[0] == "n3-c0.2-w1-t250"
    assert all(dict(c, n=3, c=0.2, dwell=1, read_from=250) == D.CANDIDATES["n3-c0.2-w1-t250"] for c in D.CANDIDATES.values())
    assert D.GEOMETRY == {"boxes": tuple(range(2, 13)), "q": 1.0, "ring": 2, "ring_max": 0}
    assert D.digest() == D.digest() and len(D.digest()) == 64


def test_substitutions_apply_once():
    src = inspect.getsource(E4.generation)
    for old, _new in sim.SUBSTITUTIONS:
        assert src.count(old) == 1
    assert sim.generation.__code__.co_filename == "<e2e004.sim.generation, routed by e2e005>"


def test_groups_partition_the_branches():
    g = sim.groups_of(["oracle", "record", "ctl", "vote", "body", "ctl"], 4)
    assert [r for r, _ix in g] == ["body", "vote", "record", "ctl", "oracle"]
    assert np.array_equal(np.sort(np.concatenate([i for _r, i in g])), np.arange(24))
    assert list(dict(g)["ctl"]) == list(range(8, 12)) + list(range(20, 24))


def test_fixed_routes_are_e2e004s_generation():
    raw, meta, cases, V0, ema0, R0, th, T, theta = _task()
    k = len(cases)
    lins = (D.L("a", "protected", "record", 1), D.L("b", "protected", "body", 1), D.L("c", D.POST, "vote", 1))
    rows, _l, _a, _s = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    routes = [r["route"] for r in rows]
    idx = np.tile(np.arange(k), len(rows))
    nb = birth("mse-test", cases, *sim.BIRTH_NAMES(0)(1), side=D.SIDE)[idx]
    outs = []
    for mine in (False, True):
        A_ = _first(rows)
        groups = (sim.groups_of if mine else E4.groups_of)(routes, k)
        B_ = tuple(x[dict(groups)["vote"]].copy() for x in A_)
        if mine:
            (V, E, A2, B2), _sw = sim.run_generation("li4", groups, cases, nb.copy(), nb.copy(), A_, B_, (th * theta)[idx],
                                                     "mse-test", sim.GEN_NAMES(0)(1), window=60)
        else:
            V, E, A2, B2 = E4.generation("li4", groups, cases, nb.copy(), nb.copy(), A_, B_, (th * theta)[idx], "mse-test",
                                         sim.GEN_NAMES(0)(1), 60)
        outs.append((V, E) + tuple(A2) + tuple(B2))
    assert all(np.array_equal(x, y) for x, y in zip(*outs))


def test_closed_switch_is_record_and_open_sheet_is_body():
    raw, meta, cases, V0, ema0, R0, th, T, theta = _task("ar005/p53", "dw", "S4_t0", 900739)
    k = len(cases)
    rows, _l, _a, _s = sim.packets(raw, meta, cases, V0, ema0, R0, T, (D.L("x", D.POST, "record", 1),))
    mrows = [dict(packet=rows[0]["packet"], route=x) for x in ("record", "ctl", "body", "oracle")]
    idx = np.tile(np.arange(k), 4)
    groups = sim.groups_of([x["route"] for x in mrows], k)
    nb = birth("mse-test", cases, *sim.BIRTH_NAMES(0)(1), side=D.SIDE)[idx]
    cfgs = {"ctl": {"never": True}, "oracle": {"full": True, "d": 0, "duration": None}}
    (V, E, A2, _B), sw = sim.run_generation("dw", groups, cases, nb.copy(), nb.copy(), _first(mrows), None,
                                            (th * theta)[idx], "mse-test", sim.GEN_NAMES(0)(1), window=60, cfgs=cfgs)
    part = lambda x, j: x[j * k:(j + 1) * k]
    for x in (V, E) + tuple(A2):
        assert np.array_equal(part(x, 0), part(x, 1)) and np.array_equal(part(x, 2), part(x, 3))
    assert (sw["ctl"].t_on == 0).all() and (sw["oracle"].t_on == 1).all() and sw["oracle"].fp.all()


def _cfg(**kw):
    return dict(D.candidate(3, 0.2, 1, 250), **kw)


def test_windows_find_a_compact_disagreement_and_reject_a_stripe():
    n = D.SIDE
    r = np.ones((3, n, n)) * 1.2
    V = np.ones((3, n, n))
    V[0, 10:14, 6:10] = -1.0                        # a 4 x 4 block where the body disagrees with the record
    V[1, :, 6:10] = -1.0                            # a stripe across the sheet
    V[2, 10:14, 6:10] = -1.0
    V[2, 10, 9] = 1.0                               # one confident agreeing cell inside the block: q 1 fails at box 4
    f = sim.windows(V, r, _cfg())
    assert f[4][0, 10, 6] and f[4][0].sum() == 1 and not any(f[b][0].any() for b in f if b != 4)
    assert not any(f[b][1].any() for b in f)
    assert not f[4][2, 10, 6]
    V[0, 10:14, 6:10] = 0.1                         # not confident: no disagreement counted
    assert not any(sim.windows(V, r, _cfg())[b][0].any() for b in f)


def test_ring_must_be_clean():
    n = D.SIDE
    r = np.ones((1, n, n)) * 1.2
    V = np.ones((1, n, n))
    V[0, 10:13, 10:13] = -1.0
    assert sim.windows(V, r, _cfg())[3][0, 10, 10]
    V[0, 14, 11] = -1.0                             # a disagreeing cell 2 rows below: inside the ring of width 2
    assert not sim.windows(V, r, _cfg())[3][0, 10, 10]


def test_switch_fires_once_with_footprint_and_touching_bonds():
    n = D.SIDE
    m = np.zeros((2, n, n), bool)
    m[:, 4:8, 4:8] = True
    sw = sim.Switch("ctl", _cfg(read_from=5, read_every=10), m)
    r = np.ones((2, n, n)) * 1.2
    V = np.ones((2, n, n))
    V[1, 20:24, 20:24] = -1.0
    for t in range(1, 40):
        sw.read(t, V, r)
    assert sw.t_on[0] == 0 and sw.t_on[1] == 5 and sw.reads == 4
    assert sw.zone[1].sum() == 16 and sw.fp[1].sum() == 64 and np.array_equal(sw.fp[1], B2S.footprint(sw.zone[1:2], 2)[0])
    assert sw.masks(4) is None
    mh, mw = sw.masks(5)
    fp = sw.fp & np.array([False, True])[:, None, None]
    assert np.array_equal(mh, fp | np.roll(fp, -1, -1)) and np.array_equal(mw, fp | np.roll(fp, -1, -2))
    V[1] = 1.0                                       # it fired once: nothing re-reads it
    for t in range(40, 80):
        sw.read(t, V, r)
    assert sw.t_on[1] == 5 and sw.masks(7999) is not None


def test_dwell_counts_consecutive_reads():
    n = D.SIDE
    m = np.zeros((1, n, n), bool)
    sw = sim.Switch("ctl", _cfg(read_from=1, read_every=1, dwell=3), m)
    r = np.ones((1, n, n)) * 1.2
    V = np.ones((1, n, n))
    V[0, 2:5, 2:5] = -1.0
    sw.read(1, V, r)
    sw.read(2, V, r)
    V[0, 2:5, 2:5] = 1.0
    sw.read(3, V, r)                                 # the run of holds is broken
    V[0, 2:5, 2:5] = -1.0
    sw.read(4, V, r)
    sw.read(5, V, r)
    assert sw.t_on[0] == 0
    sw.read(6, V, r)
    assert sw.t_on[0] == 6


def test_oracle_opens_over_the_patch_at_its_read():
    n = D.SIDE
    m = np.zeros((2, n, n), bool)
    m[0, 4:8, 4:8] = True
    m[1, 20:24, 1:5] = True
    sw = sim.Switch("oracle", D.ORACLE, m)
    V = r = np.zeros((2, n, n))
    for t in range(1, D.ORACLE["read_from"] + 2):
        sw.read(t, V, r)
    assert (sw.t_on == D.ORACLE["read_from"]).all() and np.array_equal(sw.zone, m)
    assert np.array_equal(sw.fp, B2S.footprint(m, 2))


def test_detector_reads_only_body_and_record():
    params = list(inspect.signature(sim.windows).parameters)
    assert params == ["V", "r", "cfg"]
    src = inspect.getsource(sim.Switch.read)
    assert "self.m" in src and src.count("self.m[j]") == 1      # the patch is read only by the oracle's opening


def test_the_fixed_rules_line():
    from e2e005 import predict as PR
    R, V, B = (1.0, 0.0), (0.75, 0.15), (0.5, 0.5)
    assert abs(PR.hull_heal(0.75, [R, V, B]) - 0.25) < 1e-12          # the vote below the chord: the chord binds
    assert PR.hull_heal(1.0, [R, V, B]) == 0.0 and PR.hull_heal(1.1, [R, V, B]) == 0.0
    assert PR.hull_heal(0.4, [R, V, B]) == 0.5                        # free disposal below the body's keeping
    V2 = (0.75, 0.4)                                                  # the vote beyond the chord: the hull bends at it
    assert abs(PR.hull_heal(0.75, [R, V2, B]) - 0.4) < 1e-12
    assert abs(PR.hull_heal(0.9, [R, V2, B]) - 0.16) < 1e-12
    P = {"record": (np.array([1.0]), np.array([0.0])), "vote": (np.array([0.75]), np.array([0.15])),
         "body": (np.array([0.5]), np.array([0.5])), "ctl": (np.array([0.9]), np.array([0.2]))}
    assert abs(PR.frontier_blocks(P)[0] - (0.2 - 0.1)) < 1e-12 and abs(PR.frontier_blocks(P, chord=True)[0] - 0.1) < 1e-12


def test_rule_helpers():
    from e2e005 import predict as PR
    assert PR.narrowest(0.30, 0.05, [0.28, 0.31], "ge") == 0.21
    assert PR.registers("ge", 0.0) is False and PR.registers("in", [-0.01, 0.01]) is True
    v = PR.value(np.ones((4, 4)), [900729, 900739, 900749, 900759], "probe")
    assert v["sd"] == 0 and v["halves"] == [1.0, 1.0]
    assert [p[0] for p in PR.parts()] == ["C1", "C2", "C3", "C4"] and [p[3] for p in PR.parts()] == ["ge", "in", "ge", "ge"]


def test_the_open_mask_size_is_the_touching_bonds():
    n = D.SIDE
    m = np.zeros((2, n, n), bool)
    sw = sim.Switch("ctl", _cfg(read_from=1, read_every=1), m)
    r = np.ones((2, n, n)) * 1.2
    V = np.ones((2, n, n))
    V[0, 10:13, 10:13] = -1.0                       # a 3 x 3 block: zone 9 cells, footprint 7 x 7 = 49 cells
    sw.read(1, V, r)
    d = sw.diagnostics()
    mh, mw = sw.masks(1)
    assert d["fp"][0] == 49 and d["bonds"][0] == mh[0].sum() + mw[0].sum() == 2 * 49 + 2 * 7 and d["bonds"][1] == 0
    assert set(sim.DIAGS) == set(d)
