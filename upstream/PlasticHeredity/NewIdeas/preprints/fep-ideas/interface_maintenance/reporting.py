"""Prespecified block-level contrasts and reporting."""
import numpy as np

from .spec import ARMS, CONDITIONS, RECIPIENTS, SPEC


def summarize(block_errors):
    values = np.asarray(block_errors, dtype=float)
    if values.shape != (SPEC["blocks"], 2, 2, len(ARMS)) or not np.isfinite(values).all():
        raise ValueError("A complete fixed set of independent blocks is required")
    damaged = values[:, 1, 0]
    intact = values[:, 0, 0]
    effects = {
        "primary_frozen_minus_active": damaged[:, 1] - damaged[:, 0],
        "yoked_minus_active": damaged[:, 2] - damaged[:, 0],
        "sham_minus_active": damaged[:, 3] - damaged[:, 0],
        "batch_ls_minus_active": damaged[:, 4] - damaged[:, 0],
        "oracle_minus_active": damaged[:, 5] - damaged[:, 0],
        "intact_frozen_minus_active": intact[:, 1] - intact[:, 0],
        "damage_interaction": (damaged[:, 1] - damaged[:, 0]) - (intact[:, 1] - intact[:, 0]),
        "fresh_frozen_minus_active": values[:, 1, 1, 1] - values[:, 1, 1, 0],
        "frozen_damage_cost": damaged[:, 1] - intact[:, 1],
        "oracle_rescue": damaged[:, 1] - damaged[:, 5],
    }
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    indices = rng.integers(0, SPEC["blocks"], (SPEC["bootstrap_draws"], SPEC["blocks"]))
    contrasts = {}
    for name, effect in effects.items():
        bootstrap = np.mean(effect[indices], axis=1)
        lo, hi = np.percentile(bootstrap, [2.5, 97.5])
        contrasts[name] = {"mean": float(np.mean(effect)), "ci95": [float(lo), float(hi)],
                           "block_effects": effect.tolist()}
    interval = contrasts["primary_frozen_minus_active"]["ci95"]
    label = "GAIN" if interval[0] > 0 else "HARM" if interval[1] < 0 else "UNRESOLVED"
    gates = {name: contrasts[name]["ci95"][0] > 0 for name in (
        "primary_frozen_minus_active", "frozen_damage_cost", "oracle_rescue",
        "yoked_minus_active", "sham_minus_active", "fresh_frozen_minus_active")}
    absolute = {}
    for condition, condition_name in enumerate(CONDITIONS):
        absolute[condition_name] = {}
        for recipient, recipient_name in enumerate(RECIPIENTS):
            absolute[condition_name][recipient_name] = {
                arm: float(values[:, condition, recipient, a].mean()) for a, arm in enumerate(ARMS)}
    return {"study": SPEC["study"], "independent_blocks": SPEC["blocks"],
            "cases_per_block": SPEC["cases"], "primary_label": label,
            "maintenance_gates": gates, "maintenance_gates_all_pass": all(gates.values()),
            "contrasts": contrasts, "absolute_mse": absolute,
            "block_errors": values.tolist(),
            "interval_method": "10000 paired whole-block percentile bootstrap draws; secondary intervals pointwise",
            "claim_limit": "Engineered calibration with supplied pilot labels and coordinate frame; no FEP-specific, biological or autonomous-inheritance claim."}


def report_text(summary, costs):
    primary = summary["contrasts"]["primary_frozen_minus_active"]
    lo, hi = primary["ci95"]
    lines = ["# IM1 reader-calibration result", "",
             f"Primary result: **{summary['primary_label']}**. Frozen-minus-active damaged-read MSE: "
             f"{primary['mean']:.8f}, 95% block-bootstrap interval [{lo:.8f}, {hi:.8f}].", "",
             f"{SPEC['blocks']} independent blocks × {SPEC['cases']} cases. All block artifacts reloaded and independently replayed; aggregate statistics independently checked.", "",
             "| Arm | Intact original MSE | Damaged original MSE | Damaged fresh-recipient MSE |",
             "| --- | ---: | ---: | ---: |"]
    for arm in ARMS:
        a = summary["absolute_mse"]
        lines.append(f"| {arm} | {a['intact']['original'][arm]:.8f} | {a['damaged']['original'][arm]:.8f} | {a['damaged']['fresh'][arm]:.8f} |")
    lines += ["", "| Contrast (positive favors active, except damage cost/oracle rescue) | Mean | Pointwise 95% interval |",
              "| --- | ---: | ---: |"]
    for name, contrast in summary["contrasts"].items():
        lo, hi = contrast["ci95"]
        lines.append(f"| {name} | {contrast['mean']:.8f} | [{lo:.8f}, {hi:.8f}] |")
    lines += ["", "Prespecified maintenance gates:", ""]
    lines += [f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in summary["maintenance_gates"].items()]
    lines += ["", f"Main wall time: {costs['wall_seconds']:.3f} s. Worker process CPU total: {costs['worker_cpu_seconds']:.3f} s. Parent CPU: {costs['parent_cpu_seconds']:.3f} s.",
              f"Four workers; all processes restricted to CPUs {costs['cpus']}; numerical-library thread variables fixed to one.",
              f"Block artifacts: {costs['block_artifact_bytes']} bytes. Identical damaged yoke mappings retained: {costs['identical_damaged_yoke_mappings']}.",
              "", "Every arm is charged 96 calibration pilots, each with eight sensor steps. Actual shared sensor trajectories per case and condition: 96 calibration reads plus 64 assessment reads. Reader arithmetic differs among arms; equal observation counts are not equal energy or compute costs.",
              "", summary["claim_limit"], "",
              "The fresh recipient has the same fault and original record bytes, new assessment noise, and no calibration. A positive transplant contrast establishes sufficiency of the supplied reader parameters in that matched recipient, not inheritance or generalization to a new fault.",
              "", "This is one bounded study with fixed constants; no automatic successor or parameter search follows.", ""]
    return "\n".join(lines)
