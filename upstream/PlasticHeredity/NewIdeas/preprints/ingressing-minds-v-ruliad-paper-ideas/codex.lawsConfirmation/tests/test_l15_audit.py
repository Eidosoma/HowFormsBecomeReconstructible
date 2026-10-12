from pathlib import Path

import pytest

from laws_confirmation.l15_audit import (
    EXPECTED_CONFIG_DIGESTS,
    comparator_ema_substep,
    e48_surface_csv,
    ema_response,
    run_l15_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l15_source_digest_boundary_is_explicit() -> None:
    observed = source_config_digests()
    assert observed["E49_triangle_final"] == EXPECTED_CONFIG_DIGESTS["E49_triangle_final"]
    assert observed["E50_james_final"] == EXPECTED_CONFIG_DIGESTS["E50_james_final"]
    assert observed["E48_blueprint_web"] == (
        "49c8fda1347f2ae7d930256144e7d0a997ac2cbe8bcca225ce196b86740721ff"
    )
    assert observed["E48_blueprint_web"] != EXPECTED_CONFIG_DIGESTS["E48_blueprint_web"]


def test_fixed_body_ema_separates_asymptotic_identity_from_finite_gate() -> None:
    slow = ema_response(0.002)
    fast = ema_response(0.05)
    assert slow["exact_discrete_e_folding_sweeps"] == pytest.approx(499.4998331664548)
    assert slow["residual_fraction"]["500"] == pytest.approx(0.3675112548571586)
    assert slow["first_integer_sweep_at_or_below"]["5_percent"] == 1497
    assert fast["one_over_rho"] == 20
    assert fast["residual_fraction"]["100"] < 0.006
    assert slow["asymptotically_satisfiable_for_fixed_body"] is True
    assert slow["finite_noise_floor_result_implied"] is False


def test_coupled_substep_exposes_reversion_adoption_ambiguity() -> None:
    result = comparator_ema_substep(0.002, 0.2, dt=0.2)
    assert result["a_dt_times_c_m"] == pytest.approx(0.04)
    assert result["mismatch_decay_q"] == pytest.approx(0.95808)
    assert result["mismatch_e_folding_sweeps"] == pytest.approx(23.351393274699667)
    assert result["limiting_new_body_fraction_after_unit_V_step"] == pytest.approx(
        0.04580152671755725
    )

    # Directly iterate only the isolated linear substep documented by the audit.
    voltage, reference = 1.0, 0.0
    for _ in range(1000):
        voltage_next = 0.96 * voltage + 0.04 * reference
        reference_next = reference + 0.002 * (voltage_next - reference)
        voltage, reference = voltage_next, reference_next
    limit = result["limiting_new_body_fraction_after_unit_V_step"]
    assert voltage == pytest.approx(limit)
    assert reference == pytest.approx(limit)


def test_l15_recalculates_bounded_results_without_inventing_timescale_effect() -> None:
    audit, paths, e48_rows, e49_rows, frozen = run_l15_audit(
        PLASTIC_ROOT,
        WORKSPACE,
        prior_l10_audit=None,
    )
    surface = audit["E48_freedom_surface"]
    assert surface["all_cell_flags_recalculate"] is True
    assert surface["passing_matches_retained"] is True
    assert surface["axis_contrast"]["all_joint_pass_patterns_equal_across_rho"] is True
    assert surface["axis_contrast"]["descriptive_gain_drop_to_rho_range_ratio"] == pytest.approx(
        5.570123658202606
    )
    assert surface["frontier_claim"]["reproducibility_established"] is False
    assert surface["retention"]["satisfiability_0_294_vs_0_351_machine_readable"] is False

    e49 = audit["E49_repair_and_adoption"]
    assert e49["integrity"]["complete_expected_jobs"] is True
    assert e49["all_reported_gates_and_summaries_match"] is True
    assert e49["recalculated_gates"]["gate_p49_1_transport"] is True
    assert e49["distance_8_contrasts"]["profile_T_minus_T_lesion"]["directions"][
        "positive"
    ] == 12
    assert e49["adoption"]["gate_pass"] is False
    assert e49["timescale_identification"]["repair_has_rho_factor"] is False

    category = audit["E50_stress_and_category"]["category_audit"]
    assert category["injury_experience_factorial_present"] is False
    assert category["new_identity_defense_challenge_measured_in_E50"] is False
    assert audit["overall_verdict"] == "MIXED"
    assert len(e48_rows) == 9
    assert len(e49_rows) == 12
    assert len(paths) == len(frozen) >= 100

    csv_text = e48_surface_csv(e48_rows)
    assert len(csv_text.splitlines()) == 10
    assert "isolated_limiting_new_fraction" in csv_text.splitlines()[0]
