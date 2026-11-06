"""SM007's package: its layout, the lead's ruled functions against E2E006's, the isolated control, the kappa bridge and
refusal, and the reader's code paths on a synthetic stage (random endpoints, no tissue outcome)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from msefield.core import Medium  # noqa: E402
from sm007 import design as D  # noqa: E402
from sm007 import predict as P  # noqa: E402
from sm007 import sim  # noqa: E402


def test_layout_counts_and_coverage():
    for aset, nb, ng in ((D.PILOT_SET, 240, 45), (D.STAGE_SETS["development"], 509, 97)):
        br_case, br_arr, groups = sim.layout(aset, 8, D.PROBE_TAG)
        assert len(br_case) == nb and len(groups) == ng
        for ai in range(len(aset)):
            assert set(br_case[br_arr == ai]) == set(range(8))
    labels = [a[0] for a in D.STAGE_SETS["development"]]
    assert len(labels) == len(set(labels)) and D.REFERENCE in labels
    assert sim.groups_of(3, 8) == [[0, 1, 2], [3, 4, 5], [6, 7, 0]]


def test_derangement_fixed_and_without_fixed_points():
    for n in (2, 4, 8):
        p = sim.derangement(D.PROBE_TAG, n, "x", 0)
        assert np.array_equal(p, sim.derangement(D.PROBE_TAG, n, "x", 0))
        assert sorted(p) == list(range(n)) and not np.any(p == np.arange(n))


def test_functions_equal_e2e006():
    import msefield
    from e2e006 import sim as E6
    ad = E6.FieldAdapter(msefield.core)
    rng = np.random.default_rng(3)
    V, Vt, drift, d, r = (rng.standard_normal((5, 8, 8)) for _ in range(5))
    assert np.array_equal(sim.stress(V, Vt, drift, d, r), ad.stress(V=V, Vt=Vt, drift=drift, d=d, r=r))
    c = rng.uniform(0, 20, (5, 1, 1))
    g, _t, _p = ad.respond(c, np.ones((5, 1, 1), bool), np.full((5, 1, 1), D.KAPPA), gain=D.G_DIST, thb=None, p=None)
    assert np.array_equal(sim.respond(c, D.KAPPA, D.G_DIST), g)
    shared = sim.medium("2x4", "absorbing", D.LAMBDA_SHARED)
    theirs = ad.medium(8)
    assert (shared.D, shared.gamma, shared.leak, shared.m, shared.nsub) == (theirs.D, theirs.gamma, theirs.leak, theirs.m, theirs.nsub)


@pytest.mark.parametrize("lam", [D.LAMBDA, D.LAMBDA2, D.LAMBDA_SHARED])
def test_isolated_blocks_equal_one_sheet_media(lam):
    rng = np.random.default_rng(int(lam * 10))
    Mi = sim.medium("iso8", "absorbing", lam)
    Ms = [Medium([(0, 0)], D.d_field(lam), D.GAMMA, 1.0, dt=1.0, m=D.SITES[lam], margin=0) for _ in range(8)]
    for _t in range(40):
        e = rng.uniform(0, 2, 8)
        assert np.array_equal(Mi.step(e), np.array([Ms[j].step(e[j:j + 1])[0] for j in range(8)]))


def test_response_and_kappa():
    assert D.KAPPA is not None and abs(D.KAPPA * 0.658918 - 1) < 1e-6
    assert sim.respond(0.0, D.KAPPA, D.G_DIST) == D.G_DIST
    x = np.linspace(0, 10, 11)
    assert np.all(np.diff(sim.respond(x, D.KAPPA, D.G_DIST)) > 0)


def test_kappa_unset_refuses(monkeypatch):
    monkeypatch.setattr(D, "KAPPA", None)
    with pytest.raises(RuntimeError):
        sim.run("dw", D.PILOT_SET[:1], [], np.zeros((0, 4, 4)), np.zeros((0, 4, 4)), np.zeros((0, 4, 4)), D.PROBE_TAG,
                window=1)


def test_paper_stress():
    for S in (D.PAPER_SSTAR, D.PAPER_SHIGH):
        assert abs(float(sim.paper_rate(np.array([S]))[0])) < 1e-15
    assert abs(D.PAPER_SSTAR - 0.134) < 5e-4 and abs(D.PAPER_SHIGH - 1.866) < 5e-4
    cases = [type("C", (), {"key": (lambda self, j=j: (900799, j, 0))})() for j in range(8)]
    S0 = sim.paper_init(D.PROBE_TAG, cases, 0)
    assert np.all(S0 >= D.PAPER_SSTAR) and not np.array_equal(S0, sim.paper_init(D.PROBE_TAG, cases, 1))
    tr = sim.paper_trajectory(D.PROBE_TAG, cases, 0, 300)
    assert np.all(np.diff(np.vstack([S0, tr]), axis=0) >= 0) and np.abs(tr[-1] - D.PAPER_SHIGH).max() < 1e-12
    assert np.array_equal(tr, sim.paper_trajectory(D.PROBE_TAG, cases, 0, 300))
    assert D.KAPPA_PAPER is not None and abs(D.KAPPA_PAPER * 2.24024 - 1) < 1e-5


def test_worker_futures_layout():
    from sm007 import worker as WK
    arrs = (D.PAPER_SET[1], ("2x4/absorbing", "2x4", "absorbing", "field", D.LAMBDA))
    ends, states, meta, bridge = WK.task("ar005/p53", "dw", "S4_t1", 900729, "debug", futures=2, arrangements=arrs,
                                         window=30, reads=(30,))
    n = 16
    assert all(bridge.values()) and meta["futures"] == 2 and meta["branches_a_future"] == n
    assert ends["a_v"].shape == (1, 2 * n) and np.array_equal(ends["br_future"], np.repeat([0, 1], n))
    assert states["V"].shape == (2 * n, D.SIDE, D.SIDE) and not np.array_equal(states["V"][:n], states["V"][n:])
    one, s1, _m, _b = WK.task("ar005/p53", "dw", "S4_t1", 900729, "debug", futures=1, arrangements=arrs, window=30,
                              reads=(30,))
    assert np.array_equal(one["a_v"], ends["a_v"][:, :n]) and np.array_equal(s1["V"], states["V"][:n])


def test_isotonic_and_curve():
    assert np.allclose(P.isotonic([1, 3, 2, 4]), [1, 2.5, 2.5, 4])
    assert np.allclose(P.isotonic([3, 2, 1]), [2, 2, 2])
    kn = P.fit_curve([0.5, 0.6, 0.6, 1.0], [0.5, 0.7, 0.5, 0.9])
    assert kn["x"] == [0.5, 0.6, 1.0] and np.allclose(kn["y"], [0.5, 0.6, 0.9])
    assert P.curve(kn, 0.1) == 0.5 and P.curve(kn, 2.0) == 0.9 and abs(P.curve(kn, 0.8) - 0.75) < 1e-12


def _synthetic_stage(root, stage, aset, blocks, seed, futures=1):
    """A stage of random endpoints in the run's layout and manifest format (no tissue simulated), futures laid out
    future-major as the worker's."""
    rng = np.random.default_rng(seed)
    br_case, br_arr, _g = sim.layout(aset, 8, D.PROBE_TAG)
    br_case, br_arr = np.tile(br_case, futures), np.tile(br_arr, futures)
    n = len(br_case)
    M = {"stage": stage, "tasks": {}}
    for blk in blocks:
        for body, unit in D.PAIRS:
            a = 0.5 + 0.5 * rng.uniform(size=(4, n))
            meta = {"study": D.STUDY, "stage": stage, "source": "synthetic", "body": body, "unit": unit, "block": blk,
                    "arrangements": [list(x) for x in aset], "cases": [[blk, j, 0] for j in range(8)]}
            path = root / "shards" / body / unit / f"{blk}.npz"
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(path, __meta__=np.array(json.dumps(meta)), reads=np.array(D.READS), a_v=a, sign=a,
                     gain_mean=rng.uniform(0.05, 0.4, n), expo_mean=rng.uniform(0, 9, n), stress_mean=rng.uniform(0.2, 0.6, n),
                     br_case=br_case, br_arr=br_arr)
            M["tasks"][f"{body}/{unit}/{blk}"] = {"files": {"shards": {
                "path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}}
    (root / "manifest.json").write_text(json.dumps(M))


def test_reader_on_synthetic_stages(tmp_path):
    probe = tmp_path / "probe"
    _synthetic_stage(probe, "probe", D.PILOT_SET, [b for h in D.HALVES["probe"] for b in h], 1)
    rec = P.margins(probe)
    by = {p["id"]: p for p in rec["parts"]}
    assert set(by) == {f"M{i}" for i in range(1, 10)}
    for pid, p in by.items():
        assert p["available"], pid
        assert np.isfinite(p["value"]) and np.isfinite(p["sd"]) and all(np.isfinite(p["halves"])), pid
        assert p["narrowest"] is not None, pid
    assert len(rec["G"]["x"]) == 6 and np.all(np.diff(rec["G"]["y"]) >= 0)
    lv = rec["levels"]
    assert set(lv) == {a[0] for a in D.PILOT_SET} and all(lv[k]["a_8000"] is not None for k in lv)
    dev = tmp_path / "development"
    _synthetic_stage(dev, "development", D.STAGE_SETS["development"], list(D.AR005_DEV), 2, futures=2)
    tasks, _M = P.load(dev)
    sc = {p["id"]: p for p in P.score(tasks, th={}, stage="development", knots=rec["G"])}
    assert all(sc[f"M{i}"]["available"] for i in range(1, 10))
    assert sc["M7"]["n_cases_a_block"] == 1 and sc["M7"]["n_blocks"] == 16
    rep = {r["id"]: r for r in P.score_reported(tasks, "development")} if P.frozen_G()[0] else {}
    for r in rep.values():
        assert r["available"] is True or r["available"] is False
    probe_tasks, _M = P.load(probe)
    prep = {r["id"]: r for r in P.score_reported(probe_tasks, "probe")}
    for k in ("C7/x", "C7/N", "C7/f", "C7/x-N", "C7/x-f", "C8/x", "C8/N", "C8/f", "C8/x-N", "C8/x-f"):
        assert prep[k]["available"] and np.isfinite(prep[k]["value"]), k
    assert abs(prep["C8/x-N"]["value"] - (prep["C8/x"]["value"] - prep["C8/N"]["value"])) < 1e-12
    assert not prep["RP2/2x4/absorbing"]["available"]          # the paper arm is not in the pilot set
    sc_dev = {r["id"]: r for r in P.score_reported(tasks, "development", knots=rec["G"])}
    assert sc_dev["RP2/2x4/absorbing"]["available"] and sc_dev["RP3/2x4/sealed"]["available"]
    lv = P.levels(tasks)
    assert sum(lv["2x4/sealed/paper"]["hist"]) == 16 * 4 * 2 * 8
