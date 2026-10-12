"""Record exact two-round FEP checks without sampling or editing earlier records."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from math import log
from pathlib import Path
import platform
from time import perf_counter

from .exact import (Model, analytic_choice, analytic_schedules, bayesian_reference,
                    evaluate, forgetting_plan, schedule_plan, solve)

GRID = {
    "delta": (0.0, 0.1, 0.25, 0.5),
    "nu": (0.0, 0.1, 0.25, 0.5),
    "cost": (0.0, 0.05, 0.1, 0.3, 0.6),
    "beta": (1.0, 4.0, 16.0),
    "y1": (0, 1),
}
SHARED_GRID = {
    "rate": (0.0, 0.1, 0.25, 0.5),
    "cost": (0.0, 0.1, 0.3),
    "beta": (1.0, 4.0, 16.0),
    "y1": (0, 1),
}
EXAMPLES = (
    ("both_mappings_persist", Model(0, 0), 0.1, "01", 1.4, "00", 1.5),
    ("future_task_value", Model(0.5, 0), 0.1, "11", 1.3, "11", 1.3),
    ("benefit_below_total_cost", Model(0.25, 0.1), 0.1, "11", 1.2, "00", 1.25),
    ("route_refreshes", Model(0.5, 0.5), 0.1, "11", 0.8, "00", 1.0),
    ("excessive_price", Model(0.5, 0), 0.3, "11", 0.9, "00", 1.0),
    ("prohibitive_price", Model(0.5, 0), 0.6, "00", 1.0, "00", 1.0),
    ("known_shared_flip", Model(0.5, 0.5, shared_flip=True), 0.1, "01", 0.9, "00", 1.0),
)


def grid_checks() -> dict:
    maxima = {key: 0.0 for key in (
        "trajectory_normalization", "efe_direct", "risk_ambiguity",
        "dynamic_utility", "conditional_information_chain",
        "analytic_utility", "analytic_information", "analytic_efe_difference",
        "bayesian_reference", "task_efe_equivalence", "ablation_equivalence",
    )}

    def check(key, a, b):
        residual = abs(a-b)
        maxima[key] = max(maxima[key], residual)
        if residual > 1e-10:
            raise AssertionError(f"{key}: {a} != {b}")

    settings = [(Model(d, n), c, beta, y) for d, n, c, beta, y in product(*GRID.values())]
    settings += [(Model(rate, rate, shared_flip=True), c, beta, y)
                 for rate, c, beta, y in product(*SHARED_GRID.values())]
    rows = []
    for model, cost, beta, y in settings:
        theoretical = analytic_schedules(model, beta, cost)
        schedules = {}
        for k1, k2 in product((False, True), repeat=2):
            name = f"{int(k1)}{int(k2)}"
            evaluated = evaluate(model, y, schedule_plan(model, y, k1, k2), beta, cost)
            schedules[name] = evaluated
            check("trajectory_normalization", evaluated["trajectory_mass"], 1.0)
            check("efe_direct", evaluated["efe_all"], evaluated["efe_direct"])
            check("risk_ambiguity", evaluated["efe_all"], evaluated["risk_plus_ambiguity"])
            check("analytic_utility", evaluated["utility"], theoretical[name]["utility"])
            check("analytic_information", evaluated["state_information"], theoretical[name]["state_information"])
            check("task_efe_equivalence", evaluated["task_information"], 2*log(2))
        for name, evaluated in schedules.items():
            check("analytic_efe_difference", evaluated["efe_all"]-schedules["00"]["efe_all"], theoretical[name]["efe_relative"])

        controllers = {}
        for label, target in (("efe_all", "all"), ("efe_task", "task"), ("epistemic_ablation", "none")):
            solution = solve(model, y, beta, cost, target)
            evaluated = evaluate(model, y, solution.plan, beta, cost)
            check("dynamic_utility", solution.utility, evaluated["utility"])
            expected_information = 0.0 if target == "none" else evaluated["state_information" if target == "all" else "task_information"]
            check("conditional_information_chain", solution.information, expected_information)
            check("efe_direct", evaluated["efe_all"], evaluated["efe_direct"])
            controllers[label] = evaluated
        reference = evaluate(model, y, bayesian_reference(model, y, cost), beta, cost)
        controllers["bayesian"] = reference
        optimum = max(s["utility"] for s in schedules.values())
        check("bayesian_reference", reference["utility"], optimum)
        check("task_efe_equivalence", controllers["efe_task"]["utility"], optimum)
        check("ablation_equivalence", controllers["epistemic_ablation"]["utility"], optimum)
        if controllers["efe_all"]["schedule"] != analytic_choice(model, beta, cost):
            raise AssertionError("Contingent EFE tree disagrees with analytic schedule")
        for label in ("efe_task", "epistemic_ablation"):
            if controllers[label]["schedule"] != reference["schedule"]:
                raise AssertionError("Task-optimal policies disagree, including their tie rule")
        rows.append({"model": asdict(model), "cost": cost, "beta": beta, "y1": y,
                     "controllers": controllers, "all_schedules": schedules})
    return {"independent_grid": GRID, "shared_flip_grid": SHARED_GRID,
            "independent_settings": 480, "shared_flip_settings": 72,
            "decision_settings": len(rows), "schedule_evaluations": 4*len(rows),
            "dynamic_planner_solutions": 3*len(rows), "max_abs_errors": maxima,
            "passed": True, "rows": rows}


def examples() -> list[dict]:
    rows = []
    for name, model, cost, expected_e, ue, expected_b, ub in EXAMPLES:
        y, beta = 0, 4.0
        plans = {
            "efe_all": solve(model, y, beta, cost, "all").plan,
            "efe_task": solve(model, y, beta, cost, "task").plan,
            "epistemic_ablation": solve(model, y, beta, cost, "none").plan,
            "bayesian": bayesian_reference(model, y, cost),
            "memory_only": schedule_plan(model, y, False, False),
            "always_probe": schedule_plan(model, y, True, True),
            "forgetting_resource_ablation": forgetting_plan(model, y),
        }
        results = {label: evaluate(model, y, plan, beta, cost) for label, plan in plans.items()}
        if (results["efe_all"]["schedule"] != expected_e
                or abs(results["efe_all"]["utility"]-ue) > 1e-10
                or results["bayesian"]["schedule"] != expected_b
                or abs(results["bayesian"]["utility"]-ub) > 1e-10):
            raise AssertionError(f"Worked prediction failed: {name}")
        trees = {label: {"first": asdict(plan.first),
                         "second": [{"observed_z1_g1_y2": list(key), "policy": asdict(policy)}
                                    for key, policy in sorted(plan.second.items())]}
                 for label, plan in plans.items()}
        rows.append({"name": name, "model": asdict(model), "beta": beta,
                     "cost": cost, "y1": y, "controllers": results, "policy_trees": trees})
    return rows


def misspecified_transfer() -> dict:
    assumed, truth = Model(0.5, 0), Model(0.5, 0.5)
    plans = {"efe_all": solve(assumed, 0, 4, 0.1, "all").plan,
             "bayesian": bayesian_reference(assumed, 0, 0.1)}
    results = {}
    for name, plan in plans.items():
        predicted = evaluate(assumed, 0, plan, 4, 0.1)
        actual = evaluate(truth, 0, plan, 4, 0.1)
        if abs(predicted["utility"]-1.3) > 1e-10 or abs(actual["utility"]-0.8) > 1e-10:
            raise AssertionError("Misspecified persistence calculation failed")
        keys = ("schedule", "accuracy_round1", "accuracy_round2", "expected_probes", "utility")
        results[name] = {"planned": {k: predicted[k] for k in keys},
                         "true_expected_task_outcomes": {k: actual[k] for k in keys}}
    return {"assumed_model": asdict(assumed), "true_model": asdict(truth),
            "fixed_policies_not_replanned": results,
            "correct_model_bayesian_utility": evaluate(truth, 0, bayesian_reference(truth, 0, 0.1), 4, 0.1)["utility"]}


def report(data: dict) -> str:
    checks = data["verification"]
    lines = ["# FEP persistence v2: exact calculation record", "",
             "Retained knowledge acquires future task value under a specific relation between sensor change, diagnostic-route persistence and cost. The matched Bayesian planner recognizes the same useful exploration.", "",
             "These are exact results of a specified two-round model, not a sampled cohort, biological result or general FEP verdict.", "",
             "## Useful-learning threshold", "",
             "With independent mapping changes, both probes are task-optimal exactly when `max(delta - nu, 0) > 2*c`. Ordinary feedback already reveals the old sensor mapping; extra route knowledge matters when that sensor changes and the diagnostic route stays useful.", "",
             "Full-state trajectory EFE can still buy information outside that task-value region. Task-state EFE and the epistemic ablation agree with the Bayesian optimum in this finite model.", "",
             "## Worked cases", "",
             "Probe schedules are rounds 1 and 2: 00=neither, 01=last only, 11=both. Utility is expected total correct reports minus probe costs, summed across the two rounds. All examples have beta=4.", "",
             "| Case | Full EFE schedule / utility | Bayes schedule / utility | Memory-only utility | Forgetting utility |",
             "| --- | --- | --- | ---: | ---: |"]
    for row in data["examples"]:
        c = row["controllers"]
        e, b = c["efe_all"], c["bayesian"]
        lines.append(f"| {row['name']} | {e['schedule']} / {e['utility']:.3f} | {b['schedule']} / {b['utility']:.3f} | {c['memory_only']['utility']:.3f} | {c['forgetting_resource_ablation']['utility']:.3f} |")
    lines += ["", "The forgetting comparison removes a supplied resource. It does not establish an FEP-specific advantage. All primary objective comparisons retain the same memory.", "",
              "The known shared-flip control has the same individual change rates as the independent refresh case but different joint information. Full-state EFE chooses one late probe instead of two. A reliable marginal is not a substitute for the joint causal model.", "",
              "## Wrong persistence assumption", "",
              "A fixed EFE or Bayesian policy planned for a persistent route expects utility 1.3. If the route actually refreshes completely, both fixed policies obtain 0.8. Correct-model Bayesian control obtains 1.0. This is a shared model-assumption failure, not an inference advantage unique to either framework.", "",
              "## Verification and resources", "",
              f"Passed {checks['independent_settings']} independent-flip settings and {checks['shared_flip_settings']} shared-flip settings, {checks['schedule_evaluations']} fixed-schedule evaluations and {checks['dynamic_planner_solutions']} contingent planner solutions.",
              f"Maximum identity residual: {max(checks['max_abs_errors'].values()):.3g}. Runtime: {data['elapsed_seconds']:.3f} seconds in one Python process, with no numerical libraries or workers.",
              "Full trajectory scoring agrees with the conditional-information dynamic program. The same persistent route bit is not credited twice. JSON retains every grid setting, all four schedule scores, selected-controller scores, worked policy trees, and the misspecified-policy transfer.", "",
              "Protected memory, known rates, feedback access and the preference scale remain supplied. There is no learned persistence model, endogenous communication repair or demonstrated heredity. The existing sister-project lessons were used from the local synthesis; no new fleet or literature search was performed.", "",
              "## Reproduction", "", "From the fep-ideas directory, using Python 3.10 or later:", "",
              "```bash", "python -B -m unittest discover -s tests -p 'test_fep_persistence.py' -v",
              "python -B -m fep_persistence.verify --output formal-checks/fep-persistence-v2-recheck",
              "```", "", "The verifier refuses to overwrite an existing output directory. MANIFEST.json records source and output hashes; prior v1 and IM artifacts are separate and unchanged.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = args.output.resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Output must stay inside fep-ideas")
    if destination.exists():
        raise FileExistsError("Use a fresh output directory")
    started = perf_counter()
    data = {"kind": "exact finite-model verification, not a sampled scientific cohort",
            "created_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "verification": grid_checks(), "examples": examples(),
            "misspecified_transfer": misspecified_transfer()}
    data["elapsed_seconds"] = perf_counter()-started
    destination.mkdir(parents=True)
    outputs = {"RESULTS.json": json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+"\n",
               "RESULTS.md": report(data)}
    for name, text in outputs.items():
        (destination/name).write_text(text)
    inputs = ["FEP_PERSISTENCE_V2.md", "fep_persistence/__init__.py", "fep_persistence/exact.py",
              "fep_persistence/verify.py", "tests/test_fep_persistence.py",
              "fep_formal/__init__.py", "fep_formal/exact.py"]
    manifest = {"kind": data["kind"], "created_utc": data["created_utc"],
                "inputs": {name: sha256((root/name).read_bytes()).hexdigest() for name in inputs},
                "outputs": {name: sha256((destination/name).read_bytes()).hexdigest() for name in outputs}}
    (destination/"MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"output": str(destination.relative_to(root)), "passed": True,
                      "elapsed_seconds": data["elapsed_seconds"],
                      "settings": data["verification"]["decision_settings"],
                      "max_residual": max(data["verification"]["max_abs_errors"].values())}, sort_keys=True))


if __name__ == "__main__":
    main()
