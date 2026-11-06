"""E2E003's unit tests (engineering records only: AR006's debug block 900948 and P57's 900917; no block is drawn)."""
import inspect
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from e2e002 import sim as E2  # noqa: E402
from e2e003 import design as D  # noqa: E402
from e2e003 import predict as PR  # noqa: E402
from e2e003 import sim  # noqa: E402
from e2e003 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from msegrid.core import bonds  # noqa: E402
from sr001 import sim as SRS  # noqa: E402


def test_injury_rule_at_generation0_is_be001s_memory_event():
    cases, V0, ema0, R0, th, T = A1S.prepare("S4", 900948, "engineering")
    ev = B1S.event("memory", D.SIZE, cases, V0, ema0, R0, T, "mse-ar006")
    H0, W0 = edges_from(bonds(R0, True))
    mine = sim.injure((H0, W0, A.STRENGTH0 * H0, A.STRENGTH0 * W0, R0.copy()), ev["m"])
    assert all(np.array_equal(x, ev[y]) for x, y in zip(mine, ("H", "W", "Hb", "Wb", "r")))


def test_schedule_disjoint_and_deterministic():
    cases, V0, ema0, R0, th, T = A1S.prepare("F0", 900948, "engineering")
    m0 = B1S.patch(cases, D.SIZE, "mse-ar006")
    s1, c1, a1 = sim.schedule(cases, m0, D.TAG, D.G_MAIN)
    s2, c2, a2 = sim.schedule(cases, m0, D.TAG, D.G_MAIN)
    s3, c3, a3 = sim.schedule(cases, m0, D.PROBE_TAG, D.G_MAIN)
    stack = np.stack([m0] + [s1[g] for g in range(1, D.G_MAIN + 1)])
    assert (stack.sum((-2, -1)) == D.SIZE * D.SIZE).all() and stack.sum(0).max() == 1
    assert np.array_equal(c1, c2) and np.array_equal(a1, a2) and not np.array_equal(c1, c3)
    s4, c4, _a4 = sim.schedule(cases, m0, D.TAG, 3)                 # a shorter schedule is the longer one's beginning
    assert np.array_equal(c4, c1[:, :3])


def test_injure_flips_exactly_the_patch():
    rng = np.random.default_rng(3)
    n, side = 5, D.SIDE
    A_ = tuple(rng.choice([-1.0, 1.0], (n, side, side)) * s for s in (1, 1, 0.3, 0.3, 1.1))
    M = np.zeros((n, side, side), bool)
    M[:, 0:4, 30:32] = True
    M[:, 0:4, 0:2] = True                                         # a patch across the sheet's edge
    after = sim.injure(A_, M)
    assert sim.injury_ok(A_, after, M).all()
    assert np.array_equal(after[4][~M], A_[4][~M]) and np.array_equal(after[4][M], -A_[4][M])
    assert not sim.injury_ok(A_, A_, M).any()


def test_routed_generation():
    assert inspect.getsource(E2.generation).count(sim.DETECT_CALL) == 1
    assert sim.generation.__globals__["detect_vt"] is S6.detect
    assert sim.replay0.__globals__["generation"] is sim.generation


def test_packets_aliases_and_rows():
    raw, meta, _rf = W.load("ar006/p57", "li4", "F0_t0", 900917)
    cases, V0, ema0, R0, th, T = A1S.prepare("F0", 900917, "engineering")
    rows, labels, aliases, sources = sim.packets(raw, meta, cases, V0, ema0, R0, T, D.CORE)
    assert len(rows) == 7 and labels["vote/memory@1"] == labels["vote/memory@0"]
    assert aliases == {"vote/memory@0": ["vote/memory@1"]}
    assert rows[labels["uninjured"]]["injured"] is False and rows[labels["uninjured"]]["source"] == "vote/none@0"
    assert all(rows[labels[x["label"]]]["injured"] for x in D.CORE if x["label"] != "uninjured")


def test_lineage_without_schedule_is_e2e002s_short():
    raw, meta, _rf = W.load("ar006/debug", "dw", "F0_t1", 900948)
    pattern, theta = A.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, 900948, "engineering")
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am, normals = L5S.anchor_mask(cases, meta["tag"]), GCS.unit_normals(cases, meta["tag"])
    lins = (dict(label="a", packet="vms/memory@0", policy="vms", sigma=0.0, stop=2, injured=False),
            dict(label="b", packet="vote/memory@0", policy="vote", sigma=0.0, stop=2, injured=False))
    rows, *_ = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    cue0 = {0.0: np.where(R0 > 0, 1.0, -1.0)}
    r2, _a2, d2, k2 = E2.lineage("dw", [dict(r, cue="birth") for r in rows], cases, th * theta, T, Tf, m0, am, normals, cue0,
                                 D.TAG, E2.GEN_NAMES(0), E2.BIRTH_NAMES(0), t_gen=300, horizons=(1, 2), keep=(2,))
    r3, _a3, d3, k3 = sim.lineage("dw", rows, cases, th * theta, T, Tf, m0, am, normals, D.TAG, sim.GEN_NAMES(0),
                                  sim.BIRTH_NAMES(0), sched=None, t_gen=300, keep=(2,))
    for g in (1, 2):
        assert all(np.array_equal(r2[g][x], r3[g][x]) for x in r2[g])
        assert all(np.array_equal(d2[g][x], d3[g][x]) for x in d2[g])
    assert all(np.array_equal(k2[2][x], k3[2][x]) for x in ("V", "r", "H", "W"))


def test_reader_parts():
    ps = PR.parts()
    assert [p for p, _w, _f, _k in ps] == ["J1a", "J1b", "J2a", "J2b", "J3a", "J3b", "J3c", "J3d", "J4a", "J4b", "J5a", "J5b"]
    bands = {"J2b", "J3d", "J4a", "J4b", "J5a", "J5b"}            # J5 by the plan; the four nulls by Amendment 1
    assert all(k == ("in" if p in bands else "ge") for p, _w, _f, k in ps)
    assert PR.TH == {"J1a": 0.31, "J1b": 0.05, "J2a": 0.08, "J2b": [-0.04, 0.02], "J3a": 0.28, "J3b": 0.04, "J3c": 0.06,
                     "J3d": [-0.04, 0.03], "J4a": [-0.02, 0.02], "J4b": [-0.03, 0.01], "J5a": [0.09, 0.25], "J5b": [0.06, 0.13]}
    assert set(PR.PAIRS) == set(PR.ENDPOINT) == {p for p, *_ in ps}
    assert PR.narrowest(0.05, 0.01, [0.04, 0.06], "ge") == 0.03 and PR.registers("ge", 0.03) and not PR.registers("ge", 0.0)
