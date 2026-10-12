SPEC = {
    "study": "IM4-v1", "blocks": 64, "cases": 4, "channels": 8,
    "reference_reads": 1024, "proposal_reads": 512, "validation_reads": 512,
    "assessment_reads": 64, "paths": 3, "pairs_per_path": 8,
    "pulse_amplitude": 0.25, "sensor_steps": 8, "retention": 0.6,
    "noise_sd": 0.05, "gram_ridge": 0.5, "damaged_channels": 4,
    "tie_tolerance": 1e-12, "gate_se_multiplier": 2.0, "gate_floor": 1e-12,
    "seeds": {"main": 2026091741, "qualification": 2026091742, "benchmark": 2026091743},
    "bootstrap_seed": 2026091749, "bootstrap_draws": 10000,
    "workers": 4, "artifact_limit_bytes": 268435456,
    "free_reserve_bytes": 4294967296, "wall_limit_seconds": 3600,
}
ARMS = ("redundant_majority", "shared_majority", "single_pooled", "unanimous",
        "uniform_majority", "passive", "frozen", "oracle")
CONDITIONS = ("intact", "reader_damage", "environment_change", "actuator_only",
              "reader_one", "environment_one", "reader_two", "environment_two",
              "reader_common", "environment_common")
SCHEMES = ("separate_targeted", "shared_targeted", "separate_uniform")
# Reader fault, environment change, actuator-fault count; no controller sees these.
APPARATUS = ((False, False, 0), (True, False, 0), (False, True, 0),
             (False, False, 1), (True, False, 1), (False, True, 1),
             (True, False, 2), (False, True, 2), (True, False, 3), (False, True, 3))
HISTORY = (0, 1, 1, 0, 1, 1, 1, 1, 1, 1)
TARGET = (0, 0, 1, 0, 0, 1, 0, 1, 0, 1)
SIZES = {"reference": 1024, "proposal": 512, "validation": 512, "assessment": 64}
