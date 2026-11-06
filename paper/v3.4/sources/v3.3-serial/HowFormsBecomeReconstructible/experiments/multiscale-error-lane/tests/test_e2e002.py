"""E2E002's tests (engineering; no successor value is read)."""
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from e2e002 import design as D  # noqa: E402
from e2e002 import predict as PR  # noqa: E402
from e2e002 import sim  # noqa: E402
from e2e002 import worker as WK  # noqa: E402
from gc001 import sim as GCS  # noqa: E402


def _prep(block=900729, unit="F0_t1"):
    pattern, theta = A.parse_unit(unit)
    return A1S.prepare(pattern, block, "engineering"), theta


def test_stages_and_tasks():
    assert len(D.stage_tasks("probe")) == 32 and len(D.stage_tasks("development")) == 128
    assert len(D.stage_tasks("debug")) == 8 and len(D.stage_tasks("preflight")) == 16
    for stage in D.STAGES:
        for src in D.STAGES[stage]:
            M = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
            for s, b, u, blk in D.stage_tasks(stage):
                if s == src:
                    assert f"{b}/{u}/{blk}" in M["tasks"]
    assert D.digest() == D.digest() and len(D.digest()) == 64


def test_lineages_declared():
    labels = [x["label"] for x in D.ALL]
    assert len(labels) == len(set(labels))
    for x in D.ALL:
        assert x["policy"] in D.POLICIES and x["cue"] in ("birth", "lineage") and x["stop"] in (D.G_SIDE, D.G_MAIN)
    core = {x["label"] for x in D.CORE}
    for pid, _w, _fn, _k in PR.parts():
        assert pid in ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
    assert {PR.EVERY, PR.ONCE, PR.PROT, PR.PROT_E, PR.N_E, PR.N_O} <= core


def test_groups_partition_the_branches():
    g = sim.groups_of(["vms", "vote", "vms", "vote", "vote"], 4)
    names = [cfg for cfg, _ix in g]
    assert names == [D.POLICIES["vote"], D.POLICIES["vms"]]
    ix = np.sort(np.concatenate([i for _c, i in g]))
    assert np.array_equal(ix, np.arange(20))
    assert list(g[1][1]) == list(range(0, 4)) + list(range(8, 12))


def test_birth_cue_rule():
    (cases, V0, ema0, R0, th, T), _ = _prep()
    normals = GCS.unit_normals(cases, "mse-p53")
    exact = np.where(R0 > 0, 1.0, -1.0)
    assert np.array_equal(sim.birth_cue(R0, normals, 0.0), exact)
    assert np.array_equal(sim.birth_cue(R0, normals, 1.0), GCS.read_at(exact, normals, 1.0))
    ev = A1S.event("memory", D.SIZE, 1.0, cases, V0, ema0, R0, T, "mse-p53")
    assert np.array_equal(sim.birth_cue(R0, normals, 1.0), ev["aval"])          # generation 0's rule, applied to R0


def test_generation_is_run_vd_at_a_short_window():
    (cases, V0, ema0, R0, th, T), theta = _prep()
    V, E, A_, B_, dg = sim.replay0("li4", "memory@0", ["vote", "vms"], cases, V0, ema0, R0, th, T, theta, "mse-p53",
                                   window=40)
    res = S3.run_vd("li4", "memory", 0.0, ["vote", "vms"], cases, V0, ema0, R0, th, T, theta, {40}, tag="mse-p53", window=40)
    for x, mine in (("V", V), ("r", A_[4]), ("H", A_[0]), ("W", A_[1]), ("rB", B_[4]), ("HB", B_[0]), ("WB", B_[1])):
        assert np.array_equal(res[x], mine), x


def test_packets_alias_by_policy_and_cue():
    raw, meta, _ = WK.load("ar005/debug", "dw", "S4_t0", 900799)
    pattern, _theta = A.parse_unit("S4_t0")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, 900799, "engineering")
    L = D.L
    lins = (L("a", "protected", "vote", "birth", 0.0, 8), L("b", "protected", "vote", "lineage", 1.0, 3),
            L("c", "protected", "vms", "birth", 0.0, 8), L("d", "protected", "vms", "lineage", 0.0, 3),
            L("e", "vms/memory@0", "vote", "birth", 0.0, 8))
    rows, labels, aliases, sources = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    assert labels["a"] == labels["b"] and len({labels[x] for x in "acde"}) == 4
    assert rows[labels["a"]]["stop"] == 8 and aliases == {"a": ["b"]}
    assert sources["e"] == "vms/memory@0" and sources["a"] == "protected"


def test_p53_none_stands_in_with_the_vote():
    raw, meta, _ = WK.load("ar005/p53", "li4", "F0_t1", 900729)
    pattern, _theta = A.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, 900729, "engineering")
    pk, src = sim.packet_of("vms/none@0", raw, meta, cases, V0, ema0, R0, T)
    assert src == "vote/none@0"
    j = [a for nm, a in meta["runs"] if nm == "none@0"][0].index("vote")
    assert np.array_equal(pk[2], raw["none@0/r"][j])


def test_rule_helpers():
    assert PR.narrowest(0.30, 0.05, [0.28, 0.31], "ge") == 0.21
    assert PR.registers("ge", 0.0) is False and PR.registers("ge", 0.01) is True
    assert PR.registers("le", 0.05) is True and PR.registers("le", 0.06) is False
    x = np.ones((4, 4))
    blocks = [900729, 900739, 900749, 900759]
    v = PR.value(x, blocks, "probe")
    assert v["sd"] == 0 and v["halves"] == [1.0, 1.0] and v["n_cases_a_block"] == 4


def test_thresholds_are_p58s_narrowest():
    """Amendment 1: F1-F4 as equivalence bands, F5 a band, F6 an upper bound, each the rule's narrowest on P58."""
    d = json.loads((LANE / "probes" / "results" / "p58b_e2e002_margins.json").read_text())
    kinds = {pid: k for pid, _w, _fn, k in PR.parts()}
    for p in d["parts"]:
        if p["id"] in PR.TH:
            assert PR.narrowest(p["value"], p["sd"], p["halves"], kinds[p["id"]]) == PR.TH[p["id"]], p["id"]
    assert set(PR.TH) == {"F1", "F2", "F3", "F4", "F5", "F6"} and kinds["F7"] == "ge"
    assert all(kinds[f] == "in" for f in ("F1", "F2", "F3", "F4", "F5")) and kinds["F6"] == "le"


def test_phase_b_rows():
    labels = [x["label"] for x in D.lineages("development")]
    assert labels == [x["label"] for x in D.CORE + D.CONTEXT] + ["vms-every+lineage-cue/memory@0"]
    lc = D.lineages("development")[-1]
    assert lc["cue"] == "lineage" and lc["stop"] == D.G_MAIN and lc["policy"] == "vms"
    assert D.lineages("preflight") == D.lineages("development") and D.FUTURES["development"] == 1
    assert not D.SECOND_FUTURE
