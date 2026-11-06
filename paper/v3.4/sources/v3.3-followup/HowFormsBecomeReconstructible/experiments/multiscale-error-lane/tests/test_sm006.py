"""SM006's tests (engineering; no block is drawn; no FIT or TEST value is read)."""
import json
import math
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm001 import design as S1D  # noqa: E402
from sm003 import predict as P3  # noqa: E402
from sm004 import design as D4  # noqa: E402
from sm006 import analyze as A  # noqa: E402
from sm006 import design as D  # noqa: E402
from sm006 import fitread as FR  # noqa: E402
from sm006 import predict as PR  # noqa: E402


def _conds():
    out = []
    for u in D4.FIT_UNITS:
        cfg = S1D.UNIT[u]
        for L in cfg["sizes"]:
            for a in S1D.unit_arms(u):
                if a["never"]:
                    continue
                for g in (1, 2, 4):
                    if g == 4 and cfg["w"] < 8:
                        continue
                    out.append(dict(w=cfg["w"], L=L, lam=a["lam_rest"], m=a["m"], tau=a["tau_c"], g=g, f=1.0, eps=3.0 * g))
                if a["m"] in D.FIT_MS:
                    for g in D.FIT_GRAINS_VAR:
                        for f in D.F_GRID:
                            out.append(dict(w=cfg["w"], L=L, lam=a["lam_rest"], m=a["m"], tau=a["tau_c"], g=g, f=f,
                                            eps=3.0 * g / f ** (2 / 3)))
    return out


def test_stages_and_reads():
    assert len(D.stage_tasks("development")) == 192 and len(D.stage_tasks("probe")) == 24
    for stage in D.STAGES:
        for src, blocks in D.STAGES[stage].items():
            M = json.loads((Path(D.SOURCES[src][0]) / "manifest.json").read_text())
            assert all([u, b] in M["pairs"] for u in D.UNITS for b in blocks)
    assert len(FR.arm_index("W16_x32")) == 18 and D.TEST_FACTORS["refine"] == (0.5, 0.25)


def test_the_named_forms_are_one_column():
    r = dict(w=8, L=4, lam=3.0, m=2, tau=3000.0, g=2, eps=6.0)
    v = A.gvars(r)
    assert math.isclose(math.log2(r["L"] / r["eps"]), v["e"] - v["z"])
    assert math.isclose(math.log2(r["lam"] / r["eps"]), v["e"] - v["z"] - v["b"])
    assert math.isclose(v["E"], v["e"] - v["z"])


def test_the_fit_rows_count_and_identification():
    rows = _conds()
    assert len(rows) == 1836
    for name, terms in D.CANDIDATES.items():
        idf = A.identification(rows, terms)
        assert idf["rank"] == len(terms), name
        json.dumps(idf)  # the model blob carries it (a numpy bool stopped the first selection run at 18:09Z)


def test_fit_recovers_a_known_logistic():
    rng = np.random.default_rng(0)
    rows = [dict(r, E=np.zeros((4, 8)), blocks=[0, 1, 2, 3]) for r in _conds()[::4]]
    terms = D.CANDIDATES["J6"]
    beta = rng.normal(size=len(terms)) * 0.2
    for r in rows:
        r["E"][:] = 1 / (1 + np.exp(-(A.phi(r, terms) @ beta)))
    m = A.fit_form(rows, terms)
    assert np.allclose(m["beta"], beta, atol=1e-6)


def test_narrowest_is_sm003s():
    for v, sd, h, k in ((0.0123, 0.031, (0.004, 0.02), "in"), (0.0456, 0.012, (0.04, 0.05), "ge")):
        assert PR.narrowest(v, sd, h, k) == P3.narrowest(v, sd, h, k)


def test_development_refuses_before_a_freeze(tmp_path):
    import os
    import subprocess
    p = subprocess.run([sys.executable, "-m", "sm006.run", "--stage", "development", "--root", str(tmp_path / "d"), "--cpus", "2"],
                       capture_output=True, text=True, cwd=LANE, env=dict(os.environ, PYTHONPATH=str(LANE)))
    assert p.returncode != 0 and "refusing" in (p.stdout + p.stderr) and not (tmp_path / "d").exists()


def test_the_reread_digest_ignores_eps_only(monkeypatch):
    # the FIT gain rereads never read EPS: their resume key is the design's digest with EPS blanked
    before, full = D.reread_digest(), D.digest()
    monkeypatch.setattr(D, "EPS", dict(D.EPS or {}, **{"32/1/f1": 99}))
    assert D.reread_digest() == before and D.digest() != full
    monkeypatch.setattr(D, "F_GRID", (0.5, 0.25))
    assert D.reread_digest() != before


def test_sensitivity_u_drops_the_censored_fit_readers():
    # the lead's ruling: J4's terms refitted on the 1,458 FIT means whose erasure size is not censored (378 dropped)
    rng = np.random.default_rng(1)
    rows = [dict(r, side=32, eps=D.eps(32, r["g"], r["f"]), E=np.zeros((4, 8)), blocks=[0, 1, 2, 3]) for r in _conds()]
    terms = D.CANDIDATES["J4"]
    beta = rng.normal(size=len(terms)) * 0.2
    for r in rows:
        r["E"][:] = 1 / (1 + np.exp(-(A.phi(r, terms) @ beta)))
    su = A.sensitivity_u(rows, {"model": {"terms": list(terms)}, "model_sha256": "x"})
    assert su["excluded"]["means"] == 378 and su["excluded"]["kept"] == 1458 and su["name"] == "U"
    assert set(su["model"]) == {"terms", "beta"} and np.allclose(su["model"]["beta"], beta, atol=1e-6)
    assert sorted(A.U_CENSORED) == sorted(k for k in D.EPS if k.startswith("32/") and k in ("32/4/f1", "32/2/f4"))
    json.dumps(su)


def test_h1_beside_every_part():
    ids = [p for p, *_ in PR.parts([])]
    rep = [r for r, *_ in PR.reported_parts([])]
    assert sorted(PR.H1_BESIDE) == sorted(ids) and all(v in rep for v in PR.H1_BESIDE.values()) and len(rep) == 20
