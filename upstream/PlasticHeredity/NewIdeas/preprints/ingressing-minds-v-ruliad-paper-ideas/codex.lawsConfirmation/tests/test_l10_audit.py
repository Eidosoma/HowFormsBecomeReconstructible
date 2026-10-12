from pathlib import Path

import pytest

from laws_confirmation.l10_audit import (
    EXPECTED_CONFIG_DIGESTS,
    ema_response,
    run_l10_audit,
    source_config_digests,
    summarize_replay_rows,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l10_source_config_digests_match_final_summaries():
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l10_exact_ema_is_a_decay_scale_not_expiration():
    result = ema_response(0.002)
    assert result["exact_discrete_e_folding_sweeps"] == pytest.approx(499.4998331664548)
    assert result["residual_after_one_over_rho"] == pytest.approx(0.3675112548571586)
    assert result["first_integer_sweep_at_or_below"]["20_percent"] == 804
    assert result["first_integer_sweep_at_or_below"]["1_percent"] == 2301
    assert result["one_time_constant_is_expiration"] is False


def test_l10_row_summary_discloses_censoring_and_long_zap_weighting():
    rows = [
        {"tissue": 0, "zap_sweeps": 4, "replica": 0,
         "recovery_rate": 1.0, "median_arrival": 10.0, "settle": 12},
        {"tissue": 0, "zap_sweeps": 8, "replica": 0,
         "recovery_rate": 0.5, "median_arrival": 20.0, "settle": None},
        {"tissue": 0, "zap_sweeps": 16, "replica": 0,
         "recovery_rate": 0.0, "median_arrival": None, "settle": 30},
        {"tissue": 0, "zap_sweeps": 16, "replica": 1,
         "recovery_rate": 1.0, "median_arrival": 22.0, "settle": 31},
        {"tissue": 1, "zap_sweeps": 4, "replica": 0,
         "recovery_rate": 1.0, "median_arrival": 11.0, "settle": 12},
        {"tissue": 1, "zap_sweeps": 8, "replica": 0,
         "recovery_rate": 1.0, "median_arrival": 21.0, "settle": 24},
        {"tissue": 1, "zap_sweeps": 16, "replica": 0,
         "recovery_rate": 1.0, "median_arrival": 25.0, "settle": 31},
        {"tissue": 1, "zap_sweeps": 16, "replica": 1,
         "recovery_rate": 1.0, "median_arrival": 26.0, "settle": 31},
    ]
    result = summarize_replay_rows(
        rows,
        settle_key="settle",
        futures_per_row=2,
        horizon=40,
        bootstrap_seed=1,
    )
    assert result["overall"]["rows"] == 8
    assert result["overall"]["lock_eligible_rows"] == 6
    assert result["overall"]["excluded_from_lock_rows"] == 2
    assert result["overall"]["cessation_chronology"] == {
        "before_arrival": 0, "at_arrival": 0, "after_arrival": 6,
    }
    assert result["weighting"]["rows_by_zap"] == {"4": 2, "8": 2, "16": 4}
    assert result["weighting"]["longest_zap_is_replica_overweighted"] is True
    assert result["weighting"]["replica_zero_median_by_zap"] == {
        "4": 1.5, "8": 3.0, "16": 6.0,
    }
    assert result["registered"]["arrival_by_zap"] == {
        "4": 10.5, "8": 20.5, "16": 25.0,
    }


def test_l10_static_audit_keeps_claim_boundaries():
    audit, paths = run_l10_audit(PLASTIC_ROOT, replay=False)
    assert audit["all_final_source_config_digests_match"] is True
    assert audit["E46_round1"]["current_source_is_round1_source"] is False
    assert audit["source_comparability_audit"]["causal_monotone_currency_trend_identified"] is False
    assert audit["signal_and_clock_inventory"][0]["retained_lock"] == 2
    assert audit["signal_and_clock_inventory"][1]["retained_lock"] == 30
    assert audit["EMA_fixed_V_analysis"]["residual_after_one_over_rho"] > 0.36
    assert audit["E50_clock_claim_audit"]["expiration_observed"] is False
    assert audit["claim_assessment"]["reported_30_15_6_5_values_are_comparable"]["status"] == (
        "REFUTED_BY_SOURCE_TRACE"
    )
    assert audit["overall_verdict"] == "NOT_CONFIRMED"
    assert len(paths) >= 40
