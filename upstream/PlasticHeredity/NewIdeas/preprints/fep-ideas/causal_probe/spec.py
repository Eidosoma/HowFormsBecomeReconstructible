SPEC = {
    "study": "IM3-v1", "blocks": 64, "cases": 4, "channels": 8,
    "reference_reads": 1024, "proposal_reads": 512, "validation_reads": 512,
    "assessment_reads": 64, "probe_pairs": 8, "pulse_amplitude": 0.25,
    "sensor_steps": 8, "retention": 0.6, "noise_sd": 0.05,
    "gram_ridge": 0.5, "damaged_channels": 4,
    "tie_tolerance": 1e-12, "gate_se_multiplier": 2.0, "gate_floor": 1e-12,
    "seeds": {"main": 2026091731, "qualification": 2026091732, "benchmark": 2026091733},
    "bootstrap_seed": 2026091739, "bootstrap_draws": 10000,
    "workers": 4, "artifact_limit_bytes": 268435456,
    "free_reserve_bytes": 4294967296, "wall_limit_seconds": 3600,
}
ARMS = ("upstream", "downstream", "passive", "random_channel", "uniform_calibration", "sham", "frozen", "oracle")
CONDITIONS = ("intact", "damage", "environment_change")
PROBES = ("upstream", "downstream", "random_channel", "uniform_calibration", "sham")
STAGES = ("reference", "proposal", "validation", "assessment", "diagnostic")
SIZES = {stage: SPEC[stage + "_reads"] for stage in STAGES if stage != "diagnostic"}
SIZES["diagnostic"] = SPEC["probe_pairs"]
