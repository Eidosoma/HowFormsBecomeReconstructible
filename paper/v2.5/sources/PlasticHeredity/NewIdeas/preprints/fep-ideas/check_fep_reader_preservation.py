"""Exact finite check of preserving a reader with zero information acquisition."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, log, log1p
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback


TOL = 1e-12
SPEC = Path(__file__).with_name("FEP_READER_PRESERVATION_V1.md")
POLICIES = tuple(product((0, 1), repeat=2))
TARGETS = ("bayes", "state", "exact_decomposition", "outcome_dropped",
           "latent_extension")


def entropy(q):
    return -fsum(p * log(p) for p in q.values() if p)


def binary_entropy(p):
    return entropy({0: 1 - p, 1: p})


def kl(q, p):
    return fsum(v * log(v / p[s]) for s, v in q.items() if v)


def normalize(weights):
    z = fsum(weights.values())
    return {s: w / z for s, w in weights.items()}


def marginal(q, fn):
    result = {}
    for s, mass in q.items():
        key = fn(s)
        result[key] = result.get(key, 0.0) + mass
    return result


def observe(s):
    return s[1:]


def physical(policy, rho, content):
    """No fault or feedback is passed to the policy; every output crosses F."""
    a, b = policy
    prepared = content ^ b
    states, faults = {}, {}
    for fault, mass in ((0, rho[a]), (1, 1 - rho[a])):
        if not mass:
            continue
        report = prepared ^ fault
        success = int(report == content)
        states[success, a, b] = mass
        faults[fault, a, b] = mass
    return states, faults


def fixtures():
    # Fixed in the analytic specification before this checker was written.
    return [
        ("useful_cheap", 4., 1., .5, 1., .1),
        ("useful_state_disagreement", 4., 1., .5, 1., .4),
        ("excessive_cost", 4., 1., .5, 1., .6),
        ("state_threshold", 4., 1., .5, 1., .5 - log(2) / 4),
        ("task_threshold", 4., 1., .5, 1., .5),
        ("no_damage", 4., 1., 1., 1., .1),
        ("ineffective_maintenance", 4., 1., .5, .5, .1),
        ("no_task_value", 4., 0., .5, 1., .1),
        ("interior_disagreement", 4., 1., .75, .95, .15),
        ("strong_preference", 16., 1., .5, 1., .4),
        ("weak_preference_free", 1., 1., .5, 1., 0.),
    ]


def verify():
    started = perf_counter()
    residuals = {}
    numeric_checks = structural_checks = 0

    def check(name, value, expected):
        nonlocal numeric_checks
        numeric_checks += 1
        error = abs(value - expected)
        residuals[name] = max(residuals.get(name, 0.0), error)
        if not error <= TOL:
            raise AssertionError((name, value, expected, error))

    def require(condition, message):
        nonlocal structural_checks
        structural_checks += 1
        if not condition:
            raise AssertionError(message)

    require(len(POLICIES) == len(set(POLICIES)) == 4, "policy enumeration")
    cases = []
    for name, beta, value, rho0, rho1, cost in fixtures():
        rho = rho0, rho1
        require(.5 <= rho0 <= rho1 <= 1 and cost >= 0 and value >= 0,
                (name, "physical parameter bounds"))
        cs = normalize({s: exp(beta * (value * s[0] - cost * s[1]))
                        for s in product((0, 1), repeat=3)})
        co = marginal(cs, observe)
        cf = {(f, a, b): cs[int(f == b), a, b]
              for f, a, b in product((0, 1), repeat=3)}
        for label, density in (("state", cs), ("outcome", co), ("fault", cf)):
            check(label + "_normalization", fsum(density.values()), 1.)
        require(len(cs) == len(cf) == 8 and len(co) == 4, "fixed alphabets")
        constant = log1p(exp(beta * value)) + log1p(exp(-beta * cost)) + log(2)
        delta = rho1 - rho0
        entropy_loss = binary_entropy(rho0) - binary_entropy(rho1)
        thresholds = {"bayes": value * delta,
                      "state": value * delta - entropy_loss / beta,
                      "exact_decomposition": value * delta - entropy_loss / beta,
                      "outcome_dropped": 0., "latent_extension": value * delta}
        rows = []
        for policy in POLICIES:
            a, b = policy
            qs, qf = physical(policy, rho, content=0)
            other_content, other_faults = physical(policy, rho, content=1)
            require(qs == other_content and qf == other_faults, "content symmetry")
            require(all(s[1:] == policy for s in qs), "causal action commitment")
            # Check the actual success/fault mass mapping, including deterministic endpoints.
            for f, aa, bb in qf:
                check("physical_fault_success_mapping", qf[f, aa, bb],
                      qs[int(f == b), a, b])
            qo = marginal(qs, observe)
            require(qo.keys() == {policy}, "no new observations")
            check("physical_normalization", fsum(qs.values()), 1.)
            success = fsum(mass * s[0] for s, mass in qs.items())
            maintenance = fsum(mass * s[1] for s, mass in qs.items())
            utility = value * success - cost * maintenance
            ce = -fsum(mass * log(cs[s]) for s, mass in qs.items())
            info = fsum(mass * log(1 / qo[observe(s)]) for s, mass in qs.items())
            gap = fsum(mass * log((mass / qo[observe(s)]) /
                                 (cs[s] / co[observe(s)])) for s, mass in qs.items())
            scores = {"bayes": -utility, "state": kl(qs, cs),
                      "exact_decomposition": kl(qo, co) + gap,
                      "outcome_dropped": kl(qo, co),
                      "latent_extension": ce - info}
            expected_success = rho[a] if b == 0 else 1 - rho[a]
            check("success_probability", success, expected_success)
            check("paid_maintenance", maintenance, a)
            check("external_utility", utility, value * expected_success - cost * a)
            check("state_entropy", entropy(qs), binary_entropy(rho[a]))
            check("observation_entropy", entropy(qo), 0.)
            check("zero_information_gain", info, 0.)
            check("preference_cross_entropy", ce, constant - beta * utility)
            check("state_closed_form", scores["state"],
                  constant - beta * utility - binary_entropy(rho[a]))
            check("exact_kl_decomposition", scores["state"], scores["exact_decomposition"])
            check("latent_closed_form", scores["latent_extension"], constant - beta * utility)
            check("outcome_closed_form", scores["outcome_dropped"],
                  log1p(exp(-beta * cost)) + log(2) + beta * cost * a)
            check("conditional_kl_closed_form", gap,
                  log1p(exp(beta * value)) - beta * value * success - binary_entropy(success))
            check("latent_state_entropy_gap", scores["latent_extension"] - scores["state"],
                  entropy(qs))
            check("fault_coordinate_invariance", kl(qf, cf), scores["state"])
            require(gap >= -TOL, "nonnegative conditional KL")
            rows.append({"policy": policy, "success_probability": success,
                         "utility": utility, "state_entropy": entropy(qs),
                         "information": info, "conditional_kl": gap, "scores": scores})

        by_policy = {tuple(row["policy"]): row for row in rows}
        skip, maintain = by_policy[0, 0], by_policy[1, 0]
        score_deltas = {t: maintain["scores"][t] - skip["scores"][t] for t in TARGETS}
        expected_deltas = {"bayes": cost - value * delta,
                           "state": beta * (cost - value * delta) + entropy_loss,
                           "exact_decomposition": beta * (cost - value * delta) + entropy_loss,
                           "outcome_dropped": beta * cost,
                           "latent_extension": beta * (cost - value * delta)}
        for target in TARGETS:
            check("maintenance_difference_" + target, score_deltas[target], expected_deltas[target])
        check("maintenance_utility_difference", maintain["utility"] - skip["utility"],
              value * delta - cost)
        check("maintenance_conditional_kl_difference", maintain["conditional_kl"] -
              skip["conditional_kl"], -beta * value * delta + entropy_loss)
        optima = {}
        for target in TARGETS:
            threshold = thresholds[target]
            actions = ((0, 1) if abs(cost - threshold) <= TOL
                       else (1,) if cost < threshold else (0,))
            expected = {(a, b) for a in actions for b in (0, 1)
                        if target == "outcome_dropped" or value == 0 or rho[a] == .5 or b == 0}
            best = min(row["scores"][target] for row in rows)
            winners = [row for row in rows if row["scores"][target] <= best + TOL]
            actual = {tuple(row["policy"]) for row in winners}
            require(actual == expected, (name, target, actual, expected))
            optima[target] = {"policies": [row["policy"] for row in winners],
                              "representative": winners[0]["policy"],
                              "representative_utility": winners[0]["utility"],
                              "utility_range": [min(row["utility"] for row in winners),
                                                max(row["utility"] for row in winners)]}
        cases.append({"name": name, "beta": beta, "task_value": value,
                      "reader_reliability": rho, "maintenance_price": cost,
                      "entropy_loss": entropy_loss, "maintenance_thresholds": thresholds,
                      "maintenance_minus_skip": score_deltas,
                      "baselines": {"never_maintain": skip["utility"],
                                    "always_maintain": maintain["utility"]},
                      "policy_scores": rows, "optima": optima})
    return {"passed": True, "kind": "finite arithmetic verification, not sampled evidence",
            "settings": len(cases), "policies_per_setting": len(POLICIES),
            "policy_distributions": len(cases) * len(POLICIES),
            "objectives": len(TARGETS), "optimum_sets": len(cases) * len(TARGETS),
            "content_symmetry_comparisons": len(cases) * len(POLICIES),
            "numeric_comparisons": numeric_checks, "structural_checks": structural_checks,
            "max_abs_errors": residuals, "cases": cases,
            "elapsed_seconds": perf_counter() - started}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mount = Path("/mnt/bioIce1")
    namespace = mount / "fep-ideas" / "formal-checks"
    output = args.output.resolve()
    if not os.path.ismount(mount) or namespace not in output.parents:
        raise SystemExit("Output must be inside the mounted FEP formal-checks namespace")
    output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), SPEC.resolve()]
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [{"path": str(p), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
              for p, data in snapshots.items()]
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "inputs": inputs, "passed": False,
               "execution": "one process, standard library, no random draws",
               "forecast_seconds_less_than": 10, "forecast_bytes_less_than": 100000}
    manifest = output / "MANIFEST.json"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log_path = output / "RUN_LOG.txt"
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs recorded before verification.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output / "RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
        with log_path.open("a") as log_file:
            log_file.write(f"PASS: {result['settings']} fixtures, {result['policy_distributions']} "
                           f"policy distributions, {result['objectives']} scores per policy.\n"
                           f"All {result['optimum_sets']} optimum sets and "
                           f"{result['content_symmetry_comparisons']} content comparisons passed.\n"
                           f"Numeric comparisons: {result['numeric_comparisons']}.\n"
                           f"Structural checks: {result['structural_checks']}.\n"
                           f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                           f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                           "One process, standard library, no simulation or random draws.\n")
        receipt["passed"] = True
    except BaseException:
        with log_path.open("a") as log_file:
            log_file.write(traceback.format_exc())
        for p, data in snapshots.items():
            (output / ("FAILED_INPUT_" + p.name)).write_bytes(data)
        raise
    finally:
        receipt["outputs"] = [{"path": str(p), "sha256": digest(p), "bytes": p.stat().st_size}
                              for p in sorted(output.iterdir()) if p.is_file() and p != manifest]
        manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(log_path.read_text(), end="")
    print(f"Record: {output}")


if __name__ == "__main__":
    main()
