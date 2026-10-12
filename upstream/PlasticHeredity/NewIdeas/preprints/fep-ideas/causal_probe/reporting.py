"""Frozen IM3 block inference and complete comparator readout."""
import numpy as np

from .spec import ARMS, CONDITIONS, PROBES, SPEC


def summarize(block_metrics, block_diagnostics):
    values = np.asarray(block_metrics, dtype=float)
    n = SPEC["blocks"]
    if values.shape != (n, len(CONDITIONS), len(ARMS), 3) or not np.isfinite(values).all() or len(block_diagnostics) != n:
        raise ValueError("Complete fixed block collection required")
    error = values[..., 0]
    balanced = (error[:, 1] + error[:, 2]) / 2
    effects = {"primary_downstream_minus_upstream": balanced[:, 1] - balanced[:, 0]}
    for arm in ("passive", "random_channel", "uniform_calibration", "sham", "frozen", "oracle"):
        effects["balanced_" + arm + "_minus_upstream"] = balanced[:, ARMS.index(arm)] - balanced[:, 0]
    for condition in ("damage", "environment_change"):
        cond = CONDITIONS.index(condition)
        for arm in ("downstream", "passive", "frozen"):
            effects[condition + "_" + arm + "_minus_upstream"] = error[:, cond, ARMS.index(arm)] - error[:, cond, 0]
    effects["intact_frozen_minus_upstream"] = error[:, 0, 6] - error[:, 0, 0]
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    draws = rng.integers(0, n, (SPEC["bootstrap_draws"], n))
    contrasts = {}
    for name, vector in effects.items():
        limits = np.percentile(vector[draws].mean(axis=1), [2.5, 97.5])
        contrasts[name] = {"mean": float(vector.mean()), "ci95": limits.tolist(), "block_effects": vector.tolist()}
    low, high = contrasts["primary_downstream_minus_upstream"]["ci95"]
    label = "GAIN" if low > 0 else "HARM" if high < 0 else "UNRESOLVED"
    gates = {key: contrasts[key]["ci95"][0] > 0 for key in (
        "primary_downstream_minus_upstream", "damage_frozen_minus_upstream", "environment_change_passive_minus_upstream")}
    tables = {}
    for metric, name in enumerate(("absolute_mse", "edit_rates", "mapping_recovery_rates")):
        tables[name] = {condition: {arm: float(values[:, cond, a, metric].mean()) for a, arm in enumerate(ARMS)}
                        for cond, condition in enumerate(CONDITIONS)}
    counts = {key.replace("_rates", "_counts"): {condition: {arm: int(round(rate * n * SPEC["cases"]))
              for arm, rate in row.items()} for condition, row in table.items()} for key, table in tables.items() if key.endswith("_rates")}
    diagnostics = {key: np.sum([block[key] for block in block_diagnostics], axis=0).tolist() for key in (
        "reference_proposal_counts", "reference_accept_counts", "probe_accept_counts", "command_pair_counts")}
    return {"study": SPEC["study"], "independent_blocks": n, "cases_per_block": SPEC["cases"],
            "primary_label": label, "discrimination_gates": gates, "discrimination_gates_all_pass": all(gates.values()),
            "contrasts": contrasts, "block_metrics": values.tolist(), **tables, **counts, "diagnostics": diagnostics,
            "read_budget_per_arm_condition": {"reference": 1024, "proposal": 512, "validation": 512, "diagnostic": 16, "assessment": 64},
            "pulse_squared_norm_per_functioning_arm_condition": SPEC["probe_pairs"] * SPEC["pulse_amplitude"] ** 2,
            "claim_limit": "Discrimination through a supplied, trusted actuator in a linear apparatus. One tested link does not certify a full reader; full calibration needs no reference history. No autonomous actuator/reference maintenance, simultaneous-fault diagnosis, inheritance or FEP-specific result."}


def report_text(summary, costs):
    effect = summary["contrasts"]["primary_downstream_minus_upstream"]
    low, high = effect["ci95"]
    lines = ["# IM3 causal-probe result", "",
             f"Primary: **{summary['primary_label']}**. Balanced downstream-minus-upstream MSE: {effect['mean']:.8f}, 95% whole-block interval [{low:.8f}, {high:.8f}].", "",
             "The score weights reader damage and environment change equally (50:50); this is a declared decision setting, not an estimated prevalence.", "",
             f"{SPEC['blocks']} independent blocks × {SPEC['cases']} cases; all retained, reloaded and independently replayed."]
    for key, label in (("absolute_mse", "Mean squared error"), ("edit_counts", "Applied edits out of 256"),
                       ("mapping_recovery_counts", "Exact physical-mapping recovery out of 256")):
        lines += ["", label + ":", "", "| Condition | " + " | ".join(ARMS) + " |",
                  "| --- | " + " | ".join(["---:"] * len(ARMS)) + " |"]
        for condition in CONDITIONS:
            cells = [f"{summary[key][condition][arm]:.8f}" if key == "absolute_mse" else str(summary[key][condition][arm]) for arm in ARMS]
            lines.append("| " + condition + " | " + " | ".join(cells) + " |")
    lines += ["", "| Contrast | Mean | Pointwise 95% interval |", "| --- | ---: | ---: |"]
    for name, row in summary["contrasts"].items():
        low, high = row["ci95"]
        lines.append(f"| {name} | {row['mean']:.8f} | [{low:.8f}, {high:.8f}] |")
    diag = summary["diagnostics"]
    lines += ["", "Reference and pulse decisions, out of 256 per condition:", "",
              "| Condition | Reference raw proposals | Reference accepted | Upstream accepted | Downstream accepted | Random accepted | Sham accepted |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for cond, condition in enumerate(CONDITIONS):
        counts = [diag["reference_proposal_counts"][cond], diag["reference_accept_counts"][cond]]
        counts += [diag["probe_accept_counts"][cond][p] for p in (0, 1, 2, 4)]
        lines.append("| " + condition + " | " + " | ".join(map(str, counts)) + " |")
    lines += ["", "Reference counts describe the shared historical procedure; uniform calibration, frozen and oracle do not use it. Uniform calibration has no pulse gate and always applies its selected mapping.",
              "", "Diagnostic pair counts by commanded input coordinate (0 through 7):", "",
              "| Condition | Probe | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for cond, condition in enumerate(CONDITIONS):
        for probe, name in enumerate(PROBES):
            lines.append("| " + condition + " | " + name + " | " + " | ".join(map(str, diag["command_pair_counts"][cond][probe])) + " |")
    lines += ["", "Interpretation gates (integrity additionally required):", ""]
    lines += [f"- {key}: {'PASS' if passed else 'FAIL'}" for key, passed in summary["discrimination_gates"].items()]
    lines += ["", f"All {costs['ambiguity_pairs_verified']} damage/environment pairs have bitwise-identical historical observations, downstream/sham probe readings and their respective decisions. Upstream access changes the observation contract.",
              "", "Each arm has an allowance of 1,024 reference, 512 proposal, 512 validation, 16 diagnostic and 64 assessment reads, each with eight sensor steps. Each functioning pulse arm emits eight amplitude-0.25 commands, total squared norm 0.5 per case and condition. Sham has command labels but failed actuation; passive/frozen/oracle emit no pulse. Uniform calibration uses the same diagnostic budget and needs no historical reference at all; equal allowances do not imply equal information requirements, compute or energy.",
              "", "The capsule retains observations and outcomes. Frozen field streams regenerate per-step simulation noise and Gaussian inputs. It is a replayable simulation archive, not a raw experimental recording.",
              "", f"Four workers, CPUs {costs['cpus']}, one thread per numerical library. Worker CPU total {costs['worker_cpu_seconds']:.3f} s; wall time through report assembly {costs['wall_seconds']:.3f} s. COMPLETE.json includes final sealing time. Block artifacts: {costs['block_artifact_bytes']} bytes.",
              "", summary["claim_limit"], ""]
    return "\n".join(lines)
