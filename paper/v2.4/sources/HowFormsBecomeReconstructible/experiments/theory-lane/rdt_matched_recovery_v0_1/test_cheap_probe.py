"""Leakage, integrity and unequal-stratum checks for the new forecasting reduction."""
from copy import deepcopy
import math
import numpy as np
import pytest
from it_common import ROOT, C, read, specification
import cp_models
import cp_analysis
import it_evidence
from test_injury_transfer import panel, saved_forecasts


def test_frozen_training_excludes_every_target_founder_and_injury():
    rows = read(ROOT / "context/TRAINING_ROWS.json")["rows"]
    models = read(ROOT / "FROZEN_CANDIDATES.json")
    assert len(rows) == models["training_rows"] == 768
    assert {r["block"] for r in rows} == set(range(8))
    assert {r["injury"] for r in rows} == {12, 24, 36}
    assert set(C["blocks"]).isdisjoint(r["block"] for r in rows)
    assert set(C["injury_levels"]).isdisjoint(r["injury"] for r in rows)
    assert set(models["models"]) == set(cp_models.BASE_NAMES)
    assert all(m["gradient_max"] <= 1e-8 and m["ridge"] == .01 for m in models["models"].values())


@pytest.mark.parametrize("injury,noise,curve", [(18, "matched", [.25, 0.]),
                                              (30, "independent", [.25, .25])])
def test_shift_feature_contract_and_shared_signed_transfer(injury, noise, curve):
    row = dict(injury=injury, regime=noise, boundary=list(range(11)),
               fractions=dict(direct8=.25, direct64=.5, successor32=.75))
    d, n = (injury-24)/12, int(noise == "independent")
    for family, q in (("direct8", .25), ("direct64", .5), ("successor64", .75)):
        assert cp_models.feature(row, "linear_"+family) == [*range(11), d, n, d*n, q, d*q, n*q]
        assert cp_models.feature(row, "quadratic_"+family)[-2:] == curve
    assert cp_models.feature(row, "quadratic_boundary0")[:11] == row["boundary"]
    assert len(cp_models.feature(row, "quadratic_condition0")) == 5


def test_forecast_cannot_use_future_or_training_label_fields():
    row = deepcopy(read(ROOT / "context/TRAINING_ROWS.json")["rows"][0])
    row.update(injury=18, regime="independent", current_pass=int(row["boundary"][5]))
    before = cp_models.probabilities(row)
    row.update(outcome=1-row["outcome"], target_replicate=999, passed=1,
               margin_last=100000, signed_last=-100000, future=[0, 1, 0, 1])
    assert cp_models.probabilities(row) == before


def test_candidate_probabilities_are_committed_in_the_global_barrier(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    ref = it_evidence.seal_forecasts(root, spec, panel_ref, refs)
    _, seal = it_evidence.check_seal(root, ref, spec)
    assert cp_models.check_sealed(seal["forecasts"], seal["candidate_forecasts"]) == 704
    assert seal["candidate_models_sha256"] == C["candidate_models_sha256"]
    bad = deepcopy(seal["candidate_forecasts"])
    bad[0]["probabilities"]["quadratic_direct8"] += .01
    with pytest.raises(ValueError, match="candidate seal differs"):
        cp_models.check_sealed(seal["forecasts"], bad)
    with pytest.raises(ValueError):
        cp_models.check_sealed(seal["forecasts"], bad[:-1])


def unequal_fixture():
    spec = specification("qualification")
    rows = [dict(key=[b, i], block=b, current_pass=int(i > 0))
            for b in spec["blocks"] for i in range(3)]
    forecasts = [dict(**r, injury=n, regime=g,
                    probabilities={m: .8 if r["current_pass"] else .3 for m in cp_models.NAMES})
                 for r in rows for n in spec["injuries"] for g in spec["regimes"]]
    outcomes = [dict(key=r["key"], injury=n, regime=g, replicate=rep, passed=rep % 2)
                for r in rows for n in spec["injuries"] for g in spec["regimes"] for rep in spec["repeats"]]
    return rows, forecasts, outcomes, spec


def test_individual_brier_losses_have_equal_expression_stratum_weights():
    rows, fs, ys, spec = unequal_fixture()
    result, audit = cp_analysis.analyze(rows, fs, ys, spec)
    assert audit["scalar_block_model_checks"] == 176
    assert result["inferential_verdict"] is None
    for cells in result["injuries"].values():
        for cell in cells.values():
            assert cell["observed_success"] == .5
            for m in cp_models.NAMES:
                assert abs(cell["brier"][m]-.315) < 1e-12
                assert abs(cell["mean_forecast"][m]-.55) < 1e-12
                assert abs(cell["calibration_bias"][m]-.05) < 1e-12
    assert len(result["primary"]) == 6
    assert all(p["fixed_panel_direction"] == "NOT_SCIENTIFIC_QUALIFICATION" for p in result["primary"].values())


@pytest.mark.parametrize("damage", ["missing_future", "duplicate_future", "wrong_injury", "model", "identity"])
def test_no_partial_or_misbound_candidate_analysis(damage):
    rows, fs, ys, spec = unequal_fixture()
    if damage == "missing_future":
        ys.pop()
    elif damage == "duplicate_future":
        ys[-1] = ys[0]
    elif damage == "wrong_injury":
        ys[0]["injury"] = 24
    elif damage == "model":
        fs[0]["probabilities"].pop("linear_direct64")
    else:
        fs[0]["block"] += 100
    with pytest.raises(ValueError):
        cp_analysis.analyze(rows, fs, ys, spec)


def test_nonpositive_gain_counts_against_the_fixed_panel_prediction():
    rows, fs, ys, spec = unequal_fixture()
    spec = dict(spec, scope="development")
    result, _ = cp_analysis.analyze(rows, fs, ys, spec)
    assert result["fixed_panel_all_directions_positive"] is False
    assert all(p["fixed_panel_direction"] == "DIRECTIONAL_PREDICTION_CONTRADICTED"
               for p in result["primary"].values())
    assert result["inferential_verdict"] is None
