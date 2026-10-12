"""Scientific constants fixed before qualification; no parameter selection."""
SPEC = {
    "study": "IM2-v1", "blocks": 64, "cases": 4, "channels": 8,
    "reference_reads": 1024, "proposal_reads": 512, "validation_reads": 512,
    "validation_batches": 8, "assessment_reads": 64, "sensor_steps": 8,
    "retention": 0.6, "noise_sd": 0.05, "gram_ridge": 0.5,
    "damaged_channels": 4, "tie_tolerance": 1e-12,
    "gate_se_multiplier": 2.0, "gate_floor": 1e-12,
    "seeds": {"main": 2026091721, "qualification": 2026091722, "benchmark": 2026091723},
    "bootstrap_seed": 2026091729, "bootstrap_draws": 10000,
    "workers": 4, "artifact_limit_bytes": 1073741824,
    "free_reserve_bytes": 4294967296, "wall_limit_seconds": 3600,
}
ARMS = ("gated", "frozen", "always", "wrong_reference", "erased_reference", "oracle")
CONDITIONS = ("structured_intact", "structured_damage", "environment_shift",
              "exchangeable_intact", "exchangeable_damage")
STAGES = ("reference", "proposal", "validation", "assessment")
SIZES = {stage: SPEC[stage + "_reads"] for stage in STAGES}
