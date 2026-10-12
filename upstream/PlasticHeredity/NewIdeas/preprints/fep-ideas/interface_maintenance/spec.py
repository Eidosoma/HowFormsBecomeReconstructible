"""Frozen scientific constants; no data-dependent choices."""

SPEC = {
    "study": "IM1-v1", "blocks": 64, "cases": 4, "channels": 16,
    "pilots": 96, "records": 32, "sensor_steps": 8, "retention": 0.6,
    "noise_sd": 0.05, "learning_rate": 0.5, "denominator_floor": 1e-12,
    "damaged_channels": 8, "lstsq_rcond": 1e-12,
    "seeds": {"main": 2026091701, "qualification": 2026091702,
              "benchmark": 2026091703},
    "bootstrap_seed": 2026091799, "bootstrap_draws": 10000,
    "workers": 4, "artifact_limit_bytes": 1073741824,
    "free_reserve_bytes": 4294967296, "wall_limit_seconds": 3600,
}
ARMS = ("active", "frozen", "yoked", "sham", "batch_ls", "oracle")
CONDITIONS = ("intact", "damaged")
RECIPIENTS = ("original", "fresh")
