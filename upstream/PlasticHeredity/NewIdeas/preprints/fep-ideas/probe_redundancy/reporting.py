"""Fixed IM4 inference; failure panels remain separate from the primary score."""
import numpy as np

from .spec import ARMS, CONDITIONS, SCHEMES, SPEC


def summarize(block_metrics, block_diagnostics):
    n = SPEC["blocks"]
    values = np.asarray(block_metrics, dtype=float)
    if values.shape != (n, len(CONDITIONS), len(ARMS), 3) or not np.isfinite(values).all() or len(block_diagnostics) != n:
        raise ValueError("Complete fixed collection of blocks required")
    error = values[..., 0]
    balanced = (error[:, CONDITIONS.index("reader_one")] + error[:, CONDITIONS.index("environment_one")]) / 2
    effects = {"primary_shared_minus_redundant": balanced[:, 1] - balanced[:, 0]}
    for name in ("single_pooled", "unanimous", "uniform_majority", "passive", "frozen", "oracle"):
        effects["one_fault_balanced_" + name + "_minus_redundant"] = balanced[:, ARMS.index(name)] - balanced[:, 0]
    for cond in ("reader_one", "environment_one"):
        for arm in ("shared_majority", "single_pooled", "passive", "frozen"):
            effects[cond + "_" + arm + "_minus_redundant"] = error[:, CONDITIONS.index(cond), ARMS.index(arm)] - error[:, CONDITIONS.index(cond), 0]
    for cond in CONDITIONS:
        if cond not in ("reader_one", "environment_one"):
            effects[cond + "_frozen_minus_redundant"] = error[:, CONDITIONS.index(cond), 6] - error[:, CONDITIONS.index(cond), 0]
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    sampled = rng.integers(0, n, size=(SPEC["bootstrap_draws"], n))
    contrasts = {name: {"mean": float(vector.mean()), "ci95": np.percentile(vector[sampled].mean(axis=1), [2.5, 97.5]).tolist(),
                       "block_effects": vector.tolist()} for name, vector in effects.items()}
    low, high = contrasts["primary_shared_minus_redundant"]["ci95"]
    label = "GAIN" if low > 0 else "HARM" if high < 0 else "UNRESOLVED"
    gates = {key: contrasts[key]["ci95"][0] > 0 for key in (
        "primary_shared_minus_redundant", "reader_one_frozen_minus_redundant", "environment_one_passive_minus_redundant")}
    tables = {}
    for metric, name in enumerate(("absolute_mse", "edit_rates", "mapping_recovery_rates")):
        tables[name] = {cond: {arm: float(values[:, ci, ai, metric].mean()) for ai, arm in enumerate(ARMS)} for ci, cond in enumerate(CONDITIONS)}
    counts = {key.replace("_rates", "_counts"): {cond: {arm: int(round(rate * n * SPEC["cases"])) for arm, rate in row.items()}
              for cond, row in table.items()} for key, table in tables.items() if key.endswith("_rates")}
    diagnostics = {key: np.sum([block[key] for block in block_diagnostics], axis=0).tolist() for key in (
        "reference_proposal_counts", "reference_accept_counts", "path_vote_counts", "disagreement_counts",
        "pooled_accept_counts", "uniform_consensus_counts", "failed_location_counts", "command_pair_counts")}
    return {"study": SPEC["study"], "independent_blocks": n, "cases_per_block": SPEC["cases"],
            "primary_label": label, "robustness_gates": gates, "robustness_gates_all_pass": all(gates.values()),
            "contrasts": contrasts, "block_metrics": values.tolist(), **tables, **counts, "diagnostics": diagnostics,
            "read_budget_per_arm_condition": {"reference": 1024, "proposal": 512, "validation": 512, "diagnostic": 48, "assessment": 64},
            "pulse_squared_norm_per_functioning_arm_condition": 1.5,
            "claim_limit": "An engineered majority under an at-most-one actuator-fault assumption. Multiple matched corruptions restore identical observations with conflicting required reader actions. No autonomous path/reference maintenance, guaranteed fault diagnosis, inheritance or FEP-specific result."}


def report_text(summary, costs):
    result = summary["contrasts"]["primary_shared_minus_redundant"]
    low, high = result["ci95"]
    lines = ["# IM4 probe-redundancy result", "",
             f"Primary **{summary['primary_label']}**: shared-minus-redundant majority MSE {result['mean']:.8f}, 95% whole-block interval [{low:.8f}, {high:.8f}].", "",
             "The primary score weights reader_one and environment_one equally. Exactly one actuator is faulty, at a randomly sampled location. Two-fault and shared-fault panels are reported separately and violate the candidate's assumed fault bound.", "",
             f"{SPEC['blocks']} independent blocks × {SPEC['cases']} cases; every block saved, reloaded and independently replayed."]
    for key, title in (("absolute_mse", "Mean squared reading error"), ("edit_counts", "Reader edits out of 256"),
                       ("mapping_recovery_counts", "Exact physical reader mapping out of 256")):
        lines += ["", title + ":", "", "| Condition | " + " | ".join(ARMS) + " |",
                  "| --- | " + " | ".join(["---:"] * len(ARMS)) + " |"]
        for cond in CONDITIONS:
            cells = [f"{summary[key][cond][arm]:.8f}" if key == "absolute_mse" else str(summary[key][cond][arm]) for arm in ARMS]
            lines.append("| " + cond + " | " + " | ".join(cells) + " |")
    lines += ["", "| Contrast | Mean | Pointwise 95% interval |", "| --- | ---: | ---: |"]
    for name, row in summary["contrasts"].items():
        low, high = row["ci95"]
        lines.append(f"| {name} | {row['mean']:.8f} | [{low:.8f}, {high:.8f}] |")
    diag = summary["diagnostics"]
    lines += ["", "Reference proposals/acceptance and reader decision diagnostics, out of 256:", "",
              "| Condition | Reference proposals | Reference accepts | Separate-path disagreement | Shared-path disagreement | Pooled accepts | Uniform whole-map consensus |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for ci, cond in enumerate(CONDITIONS):
        counts = [diag["reference_proposal_counts"][ci], diag["reference_accept_counts"][ci], *diag["disagreement_counts"][ci],
                  diag["pooled_accept_counts"][ci], diag["uniform_consensus_counts"][ci]]
        lines.append("| " + cond + " | " + " | ".join(map(str, counts)) + " |")
    lines += ["", "Disagreement means one or two positive votes among three. All-negative votes are abstention, not a healthy-reader certificate. Uniform consensus includes identity; no consensus also retains identity. Uniform/frozen/oracle do not use the shared reference procedure.",
              "", "| Condition | Separate path 0 votes | Path 1 | Path 2 | Shared group 0 votes | Group 1 | Group 2 |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for ci, cond in enumerate(CONDITIONS):
        counts = [*diag["path_vote_counts"][ci][0], *diag["path_vote_counts"][ci][1]]
        lines.append("| " + cond + " | " + " | ".join(map(str, counts)) + " |")
    lines += ["", "Single failed-path location counts (paths 0, 1, 2): " + str(diag["failed_location_counts"]) + ". In the two-fault panel the same sampled path is the only healthy one.",
              "", "Diagnostic pair counts by commanded coordinate:", "",
              "| Condition | Scheme | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for ci, cond in enumerate(CONDITIONS):
        for si, scheme in enumerate(SCHEMES):
            lines.append("| " + cond + " | " + scheme + " | " + " | ".join(map(str, diag["command_pair_counts"][ci][si])) + " |")
    lines += ["", "One-fault interpretation gates (integrity additionally required):", ""]
    lines += [f"- {key}: {'PASS' if passed else 'FAIL'}" for key, passed in summary["robustness_gates"].items()]
    lines += ["", f"All {costs['ambiguity_pairs_verified']} shared-failure pairs passed exact observation/action equality: reader_damage versus environment_common, and environment_change versus reader_common. Each pair requires different physical reader correction.",
              "", "Every arm has 1,024 reference, 512 proposal, 512 validation, 48 diagnostic and 64 assessment read allowances. Functioning pulse arms emit 24 amplitude-0.25 commands (squared norm 1.5); passive/frozen/oracle emit none. Uniform calibration ignores historical data. Three physical paths are extra hardware. This diagnostic budget is three times IM3's, so study-to-study errors are not a matched-budget comparison.",
              "", "Compact archives retain shared histories, target records, commands, all pulse responses, decisions and errors. Gaussian inputs/noises are regenerated from frozen streams; predictions are reconstructed from retained assessment readings and mappings.",
              "", f"Four workers on CPUs {costs['cpus']}, one numerical-library thread each. Worker CPU total {costs['worker_cpu_seconds']:.3f} s; wall through report assembly {costs['wall_seconds']:.3f} s. COMPLETE.json includes final sealing time. Main block artifacts: {costs['block_artifact_bytes']} bytes.",
              "", summary["claim_limit"], ""]
    return "\n".join(lines)
