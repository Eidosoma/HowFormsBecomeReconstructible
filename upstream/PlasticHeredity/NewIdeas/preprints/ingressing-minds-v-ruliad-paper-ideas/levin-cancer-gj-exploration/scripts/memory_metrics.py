"""Observable definitions for the predeclared memory probe; no simulator imports."""

import numpy as np

REGULATORS = ("miR200_total", "Zeb_mRNA_total", "ZEB_prot")


def opposite(label):
    if label not in ("E", "M"):
        raise ValueError("An E/M label is required")
    return "M" if label == "E" else "E"


def classify(concentrations, ion_indices):
    """Ion axis is penultimate; accepts [ions,cells] or [samples,ions,cells]."""
    values = np.asarray(concentrations)
    delta = values[..., ion_indices["miR200_total"], :] - values[..., ion_indices["Zeb_mRNA_total"], :]
    return np.where(delta > 2, "E", np.where(delta < -2, "M", "X"))


def regulatory_distance(a, b, scales):
    scales = np.asarray(scales)
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("Reference separations must be finite and positive")
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b)) / scales))


def perturb_recipient(state, target, indices, fraction):
    """Pure, mass-concentration interpolation of the three primary regulators."""
    if not 0 < fraction < 1:
        raise ValueError("Perturbation fraction must be strictly between zero and one")
    changed = np.asarray(state).copy()
    changed[indices, 0] = (1 - fraction) * changed[indices, 0] + fraction * np.asarray(target)[indices]
    return changed


def recovery_decision(d0, final_distance, before_label, shadow_label, final_label, config):
    ratio = final_distance / d0 if d0 > 0 else None
    recovered = (
        np.isfinite(d0) and np.isfinite(final_distance)
        and d0 >= config["minimum_challenge_distance"]
        and final_distance <= config["recovery_absolute_tolerance"]
        and ratio <= config["recovery_distance_ratio"]
        and before_label in ("E", "M")
        and before_label == shadow_label == final_label
    )
    return {"initial_distance": d0, "final_distance": final_distance,
            "distance_ratio": ratio, "recovered": bool(recovered)}
