from pathlib import Path

from laws_confirmation.l7_audit import (
    EXPECTED_CONFIG_DIGESTS,
    run_l7_retained_audit,
    source_config_digests,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l7_source_config_digests_match_retained_defaults():
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l7_retained_audit_reconstructs_source_and_keeps_adverse_denominator():
    audit, paths = run_l7_retained_audit(PLASTIC_ROOT)
    e33 = audit["E33_training"]
    assert e33["integrity"]["n_shards"] == 8
    assert e33["entry_validation"]["passes"] is True
    assert e33["all_reported_fields_match"] is True
    assert e33["gate_projection"]["gate_sensitization"] is False
    assert e33["gate_projection"]["gate_site_specificity"] is False
    assert e33["gate_projection"]["gate_decay"] is False
    assert e33["detector_opportunities"]["delay_6"]["n_allowed_starts"] == 1
    assert audit["generalization_and_seals"]["E47_training"][
        "original_E33_compound_gate"
    ] is False
    assert audit["appearance_registry"]["counts"]["n_narrative_rows"] == 7
    assert audit["appearance_registry"]["counts"]["n_base_substrate_families"] == 1
    assert [row["experiment"] for row in audit["adverse_and_void_attempts"]] == [
        "E38",
        "E50",
        "E58 Kuramoto",
        "E59 Gray-Scott",
    ]
    assert audit["overall_verdict"] == "MIXED"
    assert len(paths) > 30
