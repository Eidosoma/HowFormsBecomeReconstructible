"""E2E001's tests (engineering; no successor value is read)."""
import inspect
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from e2e001 import design as D  # noqa: E402
from e2e001 import predict as PR  # noqa: E402
from e2e001 import sim  # noqa: E402
from e2e001 import worker as WK  # noqa: E402
from mse.assay import Case  # noqa: E402
from sr001 import sim as SRS  # noqa: E402


def test_stages_and_tasks():
    assert len(D.stage_tasks("probe")) == 32 and len(D.stage_tasks("development")) == 128
    assert len(D.stage_tasks("debug")) == 8 and len(D.stage_tasks("preflight")) == 16
    for stage in D.STAGES:
        for src in D.STAGES[stage]:
            M = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
            for s, b, u, blk in D.stage_tasks(stage):
                if s == src:
                    assert f"{b}/{u}/{blk}" in M["tasks"]


def test_the_clock_is_the_one_substitution():
    src = inspect.getsource(SRS.generation)
    assert src.count("V, P, aval)") == 1
    assert sim.GENERATION.__globals__["_ETA"] == A.CLOCK["eta"] == 3e-4
    assert sim.GENERATION_SR001.__globals__["_ETA"] == 0.01
    assert D.ROUTE.rate == A.CLOCK["rate"] and D.ROUTE.source == "body" and not D.ROUTE.parity and D.NOREAD.gain == 0.0


def test_score_is_orientation_relative():
    rng = np.random.default_rng(0)
    T = np.where(rng.random((2, 32, 32)) < 0.5, 1.2, -1.2)
    r = T * np.where(rng.random((2, 32, 32)) < 0.9, 1.0, -1.0)
    m = np.zeros((2, 32, 32), bool)
    m[:, 4:8, 4:8] = True
    Tf = np.stack([np.roll(T, s, -1) for s in (1, 2, 3)])
    a, b = sim.score(r, r, T, Tf, m), sim.score(-r, -r, T, Tf, m)
    for e in ("u_r", "u_v", "a_r", "q_r"):
        assert np.allclose(a[e], b[e]), e
    assert not np.allclose(a["u_r_raw"], b["u_r_raw"])


def test_perm_index():
    cases = [Case(900799, m, p) for m in range(4) for p in range(2)]
    pi = sim.perm_index(cases)
    for j, c in enumerate(cases):
        t = cases[pi[j]]
        assert (t.block, t.message, t.parent) == (c.block, (c.message + 1) % 4, c.parent)


def test_packets_on_the_debug_record():
    raw, meta, _f = WK.load("ar005/debug", "dw", "S4_t0", 900799)
    cases, V0, ema0, R0, th, T = A1S.prepare("S4", 900799, "engineering")
    rows, labels, aliases = sim.packets(raw, meta, cases, V0, ema0, R0, T, D.MAIN + D.SECOND, meta["tag"])
    for lab in ("protected", "post/memory@0", "vote/memory@0", "vms/memory@0", "vguard/memory@0", "vote/memory@1",
                "vms/memory@1", "vguard/memory@1", "vote/none@0", "foreign/protected", "noread/protected",
                "unint/vguard/memory@0", "Q/vote/memory@0"):
        assert lab in labels, lab
    assert labels["vote/memory@1"] == labels["vote/memory@0"]            # the vote never reads the cue
    assert labels["post/none@0"] == labels["protected"] == labels["post/cue@0"]
    assert labels["post/correlated@0"] == labels["post/memory@0"]
    assert rows[labels["noread/protected"]]["route"] is D.NOREAD and rows[labels["unint/vguard/memory@0"]]["persist"]
    assert all(rows[labels[l]]["stop"] == D.G_MAIN for l in ("protected", "vote/memory@0", "vote/none@0"))
    assert rows[labels["foreign/protected"]]["stop"] == D.G_SIDE


def test_lineage_stops_and_persists():
    cases = [Case(900799, m, p) for m in range(4) for p in range(2)]
    rng = np.random.default_rng(1)
    R0 = np.where(rng.random((8, 32, 32)) < 0.5, 1.2, -1.2)
    H0, W0, r0 = sim.protected(R0)
    Vs = rng.normal(0, 0.1, (8, 32, 32))
    rows = [{"labels": ["a"], "packet": (H0, W0, r0), "stop": 2, "route": D.ROUTE, "persist": False, "V0": None},
            {"labels": ["b"], "packet": (H0, W0, r0), "stop": 1, "route": D.ROUTE, "persist": False, "V0": None},
            {"labels": ["c"], "packet": (H0, W0, r0), "stop": 2, "route": D.ROUTE, "persist": True, "V0": Vs}]
    pk = tuple(np.concatenate([row["packet"][x] for row in rows]) for x in range(3))
    T = R0
    Tf = np.stack([np.roll(T, s, -1) for s in (1, 2, 3)])
    m = np.zeros((8, 32, 32), bool)
    m[:, :4, :4] = True
    reads, alive_at, kept, _ = sim.lineage("dw", rows, cases, pk, np.zeros((8, 32, 32)), T, Tf, m, H0, W0, "mse-e2e-test",
                                           sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), t_gen=20, horizons=(1, 2), keep=(1, 2))
    assert alive_at == {1: [0, 1, 2], 2: [0, 2]}
    assert reads[1]["u_r"].shape == (3, 8) and reads[2]["u_r"].shape == (2, 8)
    v1 = kept[1]["V"].reshape(3, 8, 32, 32)
    assert np.array_equal(v1[0], v1[1]) and not np.array_equal(v1[0], v1[2])      # paired births; the persisting body


def test_parts_and_reported_declared():
    ids = [p for p, *_ in PR.parts()]
    assert ids == [f"E{i}" for i in range(1, 10)]
    kinds = {p: k for p, _w, _f, k in PR.parts()}
    assert kinds["E4"] == kinds["E5"] == "in" and kinds["E8"] == "le"
    assert all(PR.narrowest(0.0123, 0.004, (0.01, 0.015), "ge") <= 0.0123 - D.K_RULE * 0.004 for _ in [0])


def test_development_refuses_before_a_freeze(tmp_path):
    import os
    import subprocess
    p = subprocess.run([sys.executable, "-m", "e2e001.run", "--stage", "development", "--root", str(tmp_path / "d"), "--cpus", "2"],
                       capture_output=True, text=True, cwd=LANE, env=dict(os.environ, PYTHONPATH=str(LANE)))
    assert p.returncode != 0 and "refusing" in (p.stdout + p.stderr) and not (tmp_path / "d").exists()


def test_later_futures_pair_on_the_main_rows():
    # the lead's ruling: the second future runs the main rows only; a contrast pairs within the futures every term ran in
    from e2e001 import checks as CK
    assert CK.row_generations([8, 8, 3], 2) == (8 + 8 + 3) + (8 + 8) and D.SIDE_FUTURES == 1
    k = 8
    ends = {"g0/u_r": np.zeros((3, k)), "f0/g1/rows": np.array([0, 1, 2]), "f0/g1/u_r": np.array([[1.0] * k, [2.0] * k, [5.0] * k]),
            "f1/g1/rows": np.array([0, 1]), "f1/g1/u_r": np.array([[3.0] * k, [6.0] * k])}
    task = {"meta": {"labels": {"a": 0, "b": 1, "side": 2}, "futures": 2}, "ends": ends}
    assert np.allclose(PR.lin((1, "a", "u_r", 1), (-1, "b", "u_r", 1))(task), ((1 - 2) + (3 - 6)) / 2)
    assert np.allclose(PR.lin((1, "a", "u_r", 1), (-1, "side", "u_r", 1))(task), 1 - 5)       # future 0 only
    assert np.allclose(PR.lin((1, "a", "u_r", 1), (-1, "a", "u_r", 0))(task), (1 + 3) / 2)
    assert PR.TH["E8"] == 0.002
