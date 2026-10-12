"""Prespecified IM2 block inference, control counts and human-readable result."""
import numpy as np

from .spec import ARMS, CONDITIONS, SIZES, SPEC


def summarize(block_metrics):
    values = np.asarray(block_metrics, dtype=float)
    if values.shape != (SPEC["blocks"], len(CONDITIONS), len(ARMS), 4) or not np.isfinite(values).all():
        raise ValueError("A complete fixed collection of blocks is required")
    error = values[..., 0]
    effects = {
        "primary_frozen_minus_gated": error[:, 1, 1] - error[:, 1, 0],
        "wrong_reference_minus_gated": error[:, 1, 3] - error[:, 1, 0],
        "erased_reference_minus_gated": error[:, 1, 4] - error[:, 1, 0],
        "always_minus_gated_damaged": error[:, 1, 2] - error[:, 1, 0],
        "always_minus_gated_intact": error[:, 0, 2] - error[:, 0, 0],
        "intact_frozen_minus_gated": error[:, 0, 1] - error[:, 0, 0],
        "environment_shift_frozen_minus_gated": error[:, 2, 1] - error[:, 2, 0],
        "exchangeable_intact_frozen_minus_gated": error[:, 3, 1] - error[:, 3, 0],
        "exchangeable_damaged_frozen_minus_gated": error[:, 4, 1] - error[:, 4, 0],
        "frozen_damage_cost": error[:, 1, 1] - error[:, 0, 1],
        "oracle_rescue": error[:, 1, 1] - error[:, 1, 5],
        "oracle_minus_gated": error[:, 1, 5] - error[:, 1, 0],
    }
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    sampled = rng.integers(0, SPEC["blocks"], (SPEC["bootstrap_draws"], SPEC["blocks"]))
    contrasts = {}
    for name, vector in effects.items():
        distribution = vector[sampled].mean(axis=1)
        lo, hi = np.percentile(distribution, [2.5, 97.5])
        contrasts[name] = {"mean": float(vector.mean()), "ci95": [float(lo), float(hi)],
                           "block_effects": vector.tolist()}
    low, high = contrasts["primary_frozen_minus_gated"]["ci95"]
    label = "GAIN" if low > 0 else "HARM" if high < 0 else "UNRESOLVED"
    gates = {name: contrasts[name]["ci95"][0] > 0 for name in (
        "primary_frozen_minus_gated", "frozen_damage_cost", "oracle_rescue",
        "wrong_reference_minus_gated", "erased_reference_minus_gated")}
    tables = {}
    for metric, name in enumerate(("absolute_mse", "edit_rates", "mapping_recovery_rates", "proposal_rates")):
        tables[name] = {condition: {arm: float(values[:, cond, a, metric].mean())
                        for a, arm in enumerate(ARMS)} for cond, condition in enumerate(CONDITIONS)}
    counts = {name.replace("_rates", "_counts"): {
        condition: {arm: int(round(rate * SPEC["blocks"] * SPEC["cases"])) for arm, rate in arms.items()}
        for condition, arms in table.items()} for name, table in tables.items() if name.endswith("_rates")}
    return {"study": SPEC["study"], "independent_blocks": SPEC["blocks"],
            "cases_per_block": SPEC["cases"], "primary_label": label,
            "maintenance_gates": gates, "maintenance_gates_all_pass": all(gates.values()),
            "contrasts": contrasts, "block_metrics": values.tolist(), **tables, **counts,
            "reference_bytes_per_case_environment": SPEC["channels"] ** 2 * 8,
            "read_budget_per_arm_condition": SIZES,
            "claim_limit": "Repair from an acquired, protected reference under a stable environment; identical sensor histories cannot distinguish a wiring fault from the paired environment shift. No reference self-maintenance, inheritance or FEP-specific result."}


def report_text(summary, costs):
    effect = summary["contrasts"]["primary_frozen_minus_gated"]
    lo, hi = effect["ci95"]
    lines = ["# IM2 learned-reference result", "",
             f"Primary: **{summary['primary_label']}**. Frozen-minus-gated structured-damage MSE: {effect['mean']:.8f}, 95% block interval [{lo:.8f}, {hi:.8f}].", "",
             f"{SPEC['blocks']} independent blocks × {SPEC['cases']} cases; all retained, reloaded and independently replayed.", "",
             "| Condition | " + " | ".join(ARMS) + " |",
             "| --- | " + " | ".join(["---:"] * len(ARMS)) + " |"]
    for condition in CONDITIONS:
        lines.append("| " + condition + " | " + " | ".join(f"{summary['absolute_mse'][condition][arm]:.8f}" for arm in ARMS) + " |")
    lines += ["", "| Contrast | Mean | Pointwise 95% interval |", "| --- | ---: | ---: |"]
    for name, result in summary["contrasts"].items():
        lo, hi = result["ci95"]
        lines.append(f"| {name} | {result['mean']:.8f} | [{lo:.8f}, {hi:.8f}] |")
    for key, label in (("edit_counts", "Applied edits"), ("proposal_counts", "Nonidentity search proposals"),
                       ("mapping_recovery_counts", "Exact physical-mapping recovery")):
        lines += ["", f"{label}, out of {SPEC['blocks'] * SPEC['cases']} cases per condition:", "",
                  "| Condition | " + " | ".join(ARMS) + " |", "| --- | " + " | ".join(["---:"] * len(ARMS)) + " |"]
        for condition in CONDITIONS:
            lines.append("| " + condition + " | " + " | ".join(str(summary[key][condition][arm]) for arm in ARMS) + " |")
    lines += ["", "For gated/wrong/erased arms, applied edit counts also equal accepted nonidentity proposals. Frozen and oracle make no search proposals.",
              "", "Interpretation gates:", ""]
    lines += [f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in summary["maintenance_gates"].items()]
    lines += ["", f"All {costs['ambiguity_pairs_verified']} matched histories have bitwise-identical visible readings and identical non-oracle actions/predictions. Different target records expose the causal ambiguity.",
              f"Four workers restricted to CPUs {costs['cpus']}; numerical-library thread variables fixed to one. Per-block worker CPU total: {costs['worker_cpu_seconds']:.3f} s.",
              f"Wall time through report assembly: {costs['wall_seconds']:.3f} s; COMPLETE.json records full time including final sealing. Block artifacts: {costs['block_artifact_bytes']} bytes.",
              "", f"Each arm/condition is charged {SIZES['reference']} reference, {SIZES['proposal']} proposal and {SIZES['validation']} validation reads, plus {SIZES['assessment']} assessment reads. Each read has eight sensor steps. A learned reference uses 512 bytes, plus count/configuration and working memory. Shared simulation is executed once per available history; observation equality is not equality of compute or energy costs.",
              "", summary["claim_limit"], ""]
    return "\n".join(lines)
