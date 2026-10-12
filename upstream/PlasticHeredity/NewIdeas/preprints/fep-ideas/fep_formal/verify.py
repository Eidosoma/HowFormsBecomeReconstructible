"""Verify the formal predictions by exact enumeration and write a small record."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from math import exp, fsum, log
from pathlib import Path
import platform
from time import perf_counter

from .exact import (Model, OUTCOMES, POLICIES, Policy, bayesian_plan, choose,
                    entropy, log_preference, misspecification_example, score)

GRID = {
    "alpha": (0.0, 0.1, 0.5, 0.9, 1.0),
    "rho": (0.0, 0.1, 0.25, 0.5),
    "epsilon": (0.0, 0.1, 0.5),
    "cost": (0.0, 0.05, 0.1, 0.3, 0.6),
    "beta": (1.0, 4.0, 16.0),
    "y": (0, 1),
}

EXAMPLES = (
    ("reliable_cheap", Model.independent(), 0.1, True, True),
    ("reliable_costly", Model.independent(), 0.6, False, False),
    ("partial_useful", Model.independent(rho=0.25), 0.1, True, True),
    ("partial_beyond_task_value", Model.independent(rho=0.25), 0.3, True, False),
    ("decision_ambiguous", Model.independent(rho=0.5), 0.1, True, False),
    ("decision_ambiguous_noisy", Model.independent(rho=0.5, noise=0.1), 0.05, True, False),
    ("known_sham", Model.independent(rho=0.5, sham=True), 0.1, False, False),
    ("rare_reversal", Model.independent(alpha=0.1), 0.15, False, False),
    ("modeled_common_fault", Model.common_fault(), 0.1, False, False),
)


def check_grid() -> dict:
    maxima = {key: 0.0 for key in (
        "preference_normalization", "efe_direct", "efe_risk_ambiguity",
        "state_information_formula", "task_information_formula",
        "bayesian_optimal_value", "ablation_optimal_value", "task_efe_optimal_value",
        "efe_threshold_difference",
    )}
    cases, policy_checks, threshold_cases = 0, 0, 0
    for alpha, rho, noise, cost, beta, y in product(*GRID.values()):
        model = Model.independent(alpha, rho, noise)
        scores = [score(model, y, p, beta, cost) for p in POLICIES]
        p_total = fsum(exp(log_preference(o, beta, cost)) for o in OUTCOMES)
        maxima["preference_normalization"] = max(
            maxima["preference_normalization"], abs(p_total-1.0))
        t = rho + noise - 2*rho*noise
        extra = entropy((t, 1.0-t)) - entropy((noise, 1.0-noise))
        hx = entropy((alpha, 1.0-alpha))
        for policy, result in zip(POLICIES, scores):
            errors = {
                "efe_direct": abs(result.efe_all-result.efe_direct),
                "efe_risk_ambiguity": abs(result.efe_all-result.risk_plus_ambiguity),
                "state_information_formula": abs(result.state_information-hx-extra*policy.probe),
                "task_information_formula": abs(result.task_information-hx),
            }
            for key, value in errors.items():
                maxima[key] = max(maxima[key], value)
            policy_checks += 1
        optimum = max(s.utility for s in scores)
        policies = {
            "bayesian_optimal_value": bayesian_plan(model, y, cost),
            "ablation_optimal_value": choose(model, y, beta, cost, "preference_cross_entropy"),
            "task_efe_optimal_value": choose(model, y, beta, cost, "efe_task"),
        }
        for key, policy in policies.items():
            value = scores[POLICIES.index(policy)].utility
            maxima[key] = max(maxima[key], abs(value-optimum))
        if alpha == 0.5:
            observed = min(s.efe_all for s in scores[2:])-min(s.efe_all for s in scores[:2])
            predicted = beta*(cost-(0.5-t))-extra
            maxima["efe_threshold_difference"] = max(
                maxima["efe_threshold_difference"], abs(observed-predicted))
            actual = choose(model, y, beta, cost, "efe_all").probe
            if actual != (predicted < -1e-12):
                raise AssertionError("EFE action disagrees with the analytic threshold")
            if policies["bayesian_optimal_value"].probe != (0.5-t-cost > 1e-12):
                raise AssertionError("Bayesian action disagrees with the analytic threshold")
            threshold_cases += 1
        if rho == 0.0:
            efe = choose(model, y, beta, cost, "efe_all")
            if efe != policies["bayesian_optimal_value"]:
                raise AssertionError("Known-route policy equivalence failed")
        cases += 1
    if max(maxima.values()) > 1e-10:
        raise AssertionError(f"Exact identity failed: {maxima}")
    return {"grid": GRID, "decision_cases": cases, "policy_checks": policy_checks,
            "threshold_cases": threshold_cases, "max_abs_errors": maxima,
            "passed": True}


def example_results() -> list[dict]:
    result = []
    for name, model, cost, expected_efe, expected_bayes in EXAMPLES:
        beta, y = 4.0, 0
        policies = {
            "efe_all": choose(model, y, beta, cost, "efe_all"),
            "efe_task": choose(model, y, beta, cost, "efe_task"),
            "epistemic_ablation": choose(model, y, beta, cost, "preference_cross_entropy"),
            "bayesian": bayesian_plan(model, y, cost),
            "reactive": Policy(False, y, y),
            "always_probe": bayesian_plan(model, y, cost, force_probe=True),
        }
        if policies["efe_all"].probe != expected_efe or policies["bayesian"].probe != expected_bayes:
            raise AssertionError(f"Predicted action failed for {name}")
        scored = {key: asdict(score(model, y, policy, beta, cost))
                  for key, policy in policies.items()}
        result.append({"name": name, "beta": beta, "cost": cost, "y": y,
                       "model": asdict(model), "controllers": scored,
                       "all_policy_scores": [asdict(score(model, y, p, beta, cost)) for p in POLICIES]})
    return result


def markdown_report(data: dict) -> str:
    lines = [
        "# FEP model-evidence v1: exact calculation record", "",
        "These are deterministic checks of the specified finite model, not a sampled experiment or biological evidence.", "",
        f"Checked {data['grid_checks']['decision_cases']} decision cases and {data['grid_checks']['policy_checks']} policy scores; all declared identities and thresholds passed.",
        f"Runtime: {data['elapsed_seconds']:.3f} seconds, one Python process, no numerical libraries or parallel workers.", "",
        "All examples have beta=4 and initial reading y=0. U is accuracy minus diagnostic cost.", "",
        "| Case | Full EFE | Bayesian | Full EFE accuracy / U | Bayesian accuracy / U | EFE-task / ablation U |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for case in data["examples"]:
        c = case["controllers"]
        e, b, t, a = (c[key] for key in ("efe_all", "bayesian", "efe_task", "epistemic_ablation"))
        lines.append(f"| {case['name']} | {e['policy']} | {b['policy']} | {e['accuracy']:.3f} / {e['utility']:.3f} | {b['accuracy']:.3f} / {b['utility']:.3f} | {t['utility']:.3f} / {a['utility']:.3f} |")
    miss = data["misspecification"]
    lines += ["", "## Fixed-model misspecification", "",
              f"VFE decreased from {miss['vfe_before']:.9f} to {miss['vfe_after']:.9f} on the same history and assumed model.",
              f"External expected log loss increased from {miss['external_log_loss_before']:.9f} to {miss['external_log_loss_after']:.9f} under the declared true common-fault distribution.",
              "Exact Bayesian inference under the same misspecified model has the same failure. A correct common-fault model retains the ambiguity.", "",
              "## Interpretation", "",
              "Known-route policy equivalence is preserved. With uncertain routes, full-state EFE can reward information whose utility ends before it becomes available. Task-state EFE and the epistemic ablation agree with the Bayesian decision planner in this model.",
              "This identifies assumptions of a specified trajectory objective. It does not test every FEP formulation, establish a new empirical effect, or claim literature novelty.", "",
              "The JSON retains every illustrative policy score, controls, grid settings and maximum residuals. MANIFEST.json identifies the exact source and documentation used.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root):
        raise ValueError("Output must remain inside fep-ideas")
    if output.exists():
        raise FileExistsError("Use a fresh output directory; existing records are not overwritten")
    start = perf_counter()
    data = {
        "kind": "deterministic formal-model verification; not a sampled cohort",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "grid_checks": check_grid(),
        "examples": example_results(),
        "misspecification": misspecification_example(),
    }
    data["elapsed_seconds"] = perf_counter()-start
    output.mkdir(parents=True)
    result_path, report_path = output/"RESULTS.json", output/"RESULTS.md"
    result_path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+"\n")
    report_path.write_text(markdown_report(data))
    inputs = ["FEP_MODEL_EVIDENCE_V1.md", "fep_formal/__init__.py",
              "fep_formal/exact.py", "fep_formal/verify.py", "tests/test_fep_formal.py"]
    manifest = {
        "kind": data["kind"], "created_utc": data["created_utc"],
        "inputs": {name: sha256((root/name).read_bytes()).hexdigest() for name in inputs},
        "outputs": {p.name: sha256(p.read_bytes()).hexdigest() for p in (result_path, report_path)},
    }
    (output/"MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"output": str(output.relative_to(root)),
                      "elapsed_seconds": data["elapsed_seconds"],
                      "decision_cases": data["grid_checks"]["decision_cases"],
                      "policy_checks": data["grid_checks"]["policy_checks"],
                      "max_residual": max(data["grid_checks"]["max_abs_errors"].values()),
                      "passed": True}, sort_keys=True))


if __name__ == "__main__":
    main()
