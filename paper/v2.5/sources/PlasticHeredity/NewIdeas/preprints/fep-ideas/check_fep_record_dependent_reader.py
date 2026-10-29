"""Finite verification of a record-dependent reader; standard library only."""
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
SPEC = Path(__file__).with_name("FEP_RECORD_DEPENDENT_READER_V1.md")
POLICIES = tuple(product((0, 1), repeat=3))
TARGETS = ("bayes", "state", "exact_decomposition", "outcome_dropped",
           "full_state_extension", "task_extension", "record_extension")


def entropy(q):
    return -fsum(p * log(p) for p in q.values() if p)


def h(p):
    return entropy({0: 1 - p, 1: p})


def kl(q, p):
    return fsum(v * log(v / p[s]) for s, v in q.items() if v)


def normalize(weights):
    z = fsum(weights.values())
    return {s: w / z for s, w in weights.items()}


def marginal(q, fn):
    result = {}
    for s, p in q.items():
        key = fn(s)
        result[key] = result.get(key, 0.) + p
    return result


def information(q, fn1, fn2):
    joint = marginal(q, lambda s: (fn1(s), fn2(s)))
    first, second = marginal(q, fn1), marginal(q, fn2)
    return fsum(p * log(p / (first[x] * second[y])) for (x, y), p in joint.items())


def observe(s):
    x, record, error, a, report = s
    return a, record ^ error, report


def report_from_observation(policy, observation):
    # The target, raw record and realized errors are deliberately not arguments.
    return policy[1 + observation]


def physical(policy, eta, rho):
    a = policy[0]
    states = {}
    for x, damage, error in product((0, 1), repeat=3):
        p_damage = eta if damage else 1 - eta
        p_error = 1 - rho[a] if error else rho[a]
        mass = .5 * p_damage * p_error
        if not mass:
            continue
        record = x ^ damage
        observed = record ^ error
        report = report_from_observation(policy, observed)
        state = x, record, error, a, report
        states[state] = states.get(state, 0.) + mass
    return states


def fixtures():
    # name, eta, cost, rho0, rho1, task value; beta is fixed at 4.
    return [
        ("intact_useful", 0., .1, .5, 1., 1.),
        ("intact_state_disagreement", 0., .4, .5, 1., 1.),
        ("intact_information_overpayment", 0., .6, .5, 1., 1.),
        ("content_replaced", .5, .1, .5, 1., 1.),
        ("partial_state_disagreement", .25, .1, .5, 1., 1.),
        ("partial_record_overpayment", .25, .3, .5, 1., 1.),
        ("maintenance_disabled", 0., .1, .5, .5, 1.),
        ("reader_intact", 0., .1, 1., 1., 1.),
        ("known_reversal", 0., .1, 0., 1., 1.),
        ("no_task_value", 0., .1, .5, 1., 0.),
        ("interior", .1, .1, .7, .9, 1.),
        ("state_threshold", 0., .5 - log(2) / 4, .5, 1., 1.),
        ("task_threshold", 0., .5, .5, 1., 1.),
        ("information_threshold", 0., .5 + log(2) / 4, .5, 1., 1.),
    ]


def verify():
    started = perf_counter()
    residuals = {}
    numeric_checks = structural_checks = 0

    def check(name, actual, expected):
        nonlocal numeric_checks
        numeric_checks += 1
        error = abs(actual - expected)
        residuals[name] = max(residuals.get(name, 0.), error)
        if not error <= TOL:
            raise AssertionError((name, actual, expected, error))

    def require(condition, message):
        nonlocal structural_checks
        structural_checks += 1
        if not condition:
            raise AssertionError(message)

    require(len(POLICIES) == len(set(POLICIES)) == 8, "policy enumeration")
    beta, ell = 4., log(2)
    cases = []
    for name, eta, cost, rho0, rho1, value in fixtures():
        rho = rho0, rho1
        require(0 <= eta <= .5 and all(0 <= r <= 1 for r in rho)
                and cost >= 0 and value >= 0, "physical parameter bounds")
        cs = normalize({s: exp(beta * (value * int(s[4] == s[0]) - cost * s[3]))
                        for s in product((0, 1), repeat=5)})
        co = marginal(cs, observe)
        check("state_preference_normalization", fsum(cs.values()), 1.)
        check("outcome_preference_normalization", fsum(co.values()), 1.)
        require(len(cs) == 32 and len(co) == 8, "fixed alphabets")
        for (a, y, d), p in co.items():
            check("induced_outcome_preference", p, exp(-beta * cost * a) /
                  (4 * (1 + exp(-beta * cost))))
        constant = 3 * ell + log1p(exp(beta * value)) + log1p(exp(-beta * cost))
        q = tuple(eta + (1 - 2 * eta) * r for r in rho)
        best_success = tuple(max(p, 1 - p) for p in q)
        delta = best_success[1] - best_success[0]
        loss_e, loss_x = h(rho0) - h(rho1), h(q[0]) - h(q[1])
        thresholds = {"bayes": value * delta,
                      "state": value * delta - loss_e / beta,
                      "exact_decomposition": value * delta - loss_e / beta,
                      "outcome_dropped": 0.,
                      "full_state_extension": value * delta,
                      "task_extension": value * delta + loss_x / beta,
                      "record_extension": value * delta + loss_e / beta}
        rows, content_marginals = [], {}
        for policy in POLICIES:
            a, d0, d1 = policy
            qs = physical(policy, eta, rho)
            qo = marginal(qs, observe)
            qxr = marginal(qs, lambda s: s[:2])
            content_marginals[policy] = qxr
            check("physical_normalization", fsum(qs.values()), 1.)
            check("observation_normalization", fsum(qo.values()), 1.)
            require(len(qo) == 2, "one fair binary read, no extra observations")
            require(all(s[3] == a and s[4] == report_from_observation(policy, observe(s)[1])
                        for s in qs), "report uses only its admitted observation")
            for x, r in product((0, 1), repeat=2):
                expected = .5 * (1 - eta if x == r else eta)
                check("retained_content_law", qxr.get((x, r), 0.), expected)
            for o, p in qo.items():
                check("fair_reader_output", p, .5)
                conditional_match = fsum(mass for s, mass in qs.items()
                                         if observe(s) == o and s[0] == o[1]) / p
                check("target_posterior", conditional_match, q[a])
            success = fsum(p * int(s[4] == s[0]) for s, p in qs.items())
            expected_success = (q[a] if (d0, d1) == (0, 1) else
                                1 - q[a] if (d0, d1) == (1, 0) else .5)
            utility = fsum(p * (value * int(s[4] == s[0]) - cost * s[3])
                           for s, p in qs.items())
            info_full = information(qs, lambda s: s, observe)
            info_task = information(qs, lambda s: s[0], observe)
            info_record = information(qs, lambda s: s[1], observe)
            retained = information(qs, lambda s: s[0], lambda s: s[1])
            ce = -fsum(p * log(cs[s]) for s, p in qs.items())
            gap = fsum(p * log((p / qo[observe(s)]) / (cs[s] / co[observe(s)]))
                       for s, p in qs.items())
            scores = {"bayes": -utility, "state": kl(qs, cs),
                      "exact_decomposition": kl(qo, co) + gap,
                      "outcome_dropped": kl(qo, co),
                      "full_state_extension": ce - info_full,
                      "task_extension": ce - info_task,
                      "record_extension": ce - info_record}
            check("success_probability", success, expected_success)
            check("utility", utility, value * expected_success - cost * a)
            check("state_entropy", entropy(qs), ell + h(eta) + h(rho[a]))
            check("observation_entropy", entropy(qo), ell)
            check("retained_target_information", retained, ell - h(eta))
            check("available_target_information", info_task, ell - h(q[a]))
            check("available_record_information", info_record, ell - h(rho[a]))
            check("full_state_information", info_full, ell)
            check("no_information_from_maintenance_itself",
                  information(qs, lambda s: (s[0], s[1], s[2]), lambda s: s[3]), 0.)
            check("cross_entropy", ce, constant - beta * utility)
            check("state_closed_form", scores["state"],
                  constant - beta * utility - ell - h(eta) - h(rho[a]))
            check("exact_kl_decomposition", scores["exact_decomposition"], scores["state"])
            check("outcome_closed_form", scores["outcome_dropped"],
                  log1p(exp(-beta * cost)) + ell + beta * cost * a)
            check("full_extension_closed_form", scores["full_state_extension"],
                  constant - beta * utility - ell)
            check("task_extension_closed_form", scores["task_extension"],
                  constant - beta * utility - ell + h(q[a]))
            check("record_extension_closed_form", scores["record_extension"],
                  constant - beta * utility - ell + h(rho[a]))
            check("conditional_kl_closed_form", gap,
                  ell + log1p(exp(beta * value)) - beta * value * success - h(eta) - h(rho[a]))
            require(gap >= -TOL, "nonnegative conditional KL")
            if eta == .5:
                check("erased_content_chance_bound", success, .5)
                check("erased_content_no_target_information", info_task, 0.)
            rows.append({"policy": policy, "success_probability": success,
                         "utility": utility, "state_entropy": entropy(qs),
                         "retained_target_information": retained,
                         "available_target_information": info_task,
                         "available_record_information": info_record,
                         "full_state_information": info_full,
                         "conditional_kl": gap, "scores": scores})

        # The content distribution is unchanged by either maintenance or report selection.
        reference = content_marginals[0, 0, 0]
        for qxr in content_marginals.values():
            for key in set(reference) | set(qxr):
                check("maintenance_does_not_change_content", qxr.get(key, 0.), reference.get(key, 0.))
        by_policy = {tuple(row["policy"]): row for row in rows}

        def best_maps(a, target):
            if target == "outcome_dropped" or value == 0 or abs(q[a] - .5) <= TOL:
                return tuple(product((0, 1), repeat=2))
            return ((0, 1),) if q[a] > .5 else ((1, 0),)

        optima, score_deltas = {}, {}
        for target in TARGETS:
            threshold = thresholds[target]
            actions = ((0, 1) if abs(cost - threshold) <= TOL
                       else (1,) if cost < threshold else (0,))
            expected = {(a, *bits) for a in actions for bits in best_maps(a, target)}
            best = min(row["scores"][target] for row in rows)
            winners = [row for row in rows if row["scores"][target] <= best + TOL]
            require({tuple(row["policy"]) for row in winners} == expected,
                    (name, target, [row["policy"] for row in winners], expected))
            optima[target] = {"policies": [row["policy"] for row in winners],
                              "representative": winners[0]["policy"],
                              "representative_utility": winners[0]["utility"],
                              "utility_range": [min(row["utility"] for row in winners),
                                                max(row["utility"] for row in winners)]}
            skipped = by_policy[(0, *best_maps(0, target)[0])]["scores"][target]
            maintained = by_policy[(1, *best_maps(1, target)[0])]["scores"][target]
            score_deltas[target] = maintained - skipped
            scale = 1. if target == "bayes" else beta
            check("maintenance_delta_" + target, score_deltas[target], scale * (cost - threshold))
        if name == "known_reversal":
            require(optima["bayes"]["policies"] == [(0, 1, 0)],
                    "known reversed reader requires no maintenance")
            check("known_reversal_perfect_success", by_policy[0, 1, 0]["success_probability"], 1.)
        cases.append({"name": name, "beta": beta, "task_value": value,
                      "content_flip_probability": eta, "reader_alignment": rho,
                      "maintenance_price": cost, "raw_target_match": q,
                      "best_success_by_action": best_success,
                      "maintenance_thresholds": thresholds,
                      "maintenance_minus_skip": score_deltas,
                      "baselines": {"never_maintain_best_report": value * best_success[0],
                                    "always_maintain_best_report": value * best_success[1] - cost,
                                    "no_observation_no_maintenance": value / 2},
                      "policy_scores": rows, "optima": optima})
    return {"passed": True, "kind": "finite arithmetic verification, not sampled evidence",
            "settings": len(cases), "policies_per_setting": len(POLICIES),
            "policy_distributions": len(cases) * len(POLICIES), "objectives": len(TARGETS),
            "objective_scores": len(cases) * len(POLICIES) * len(TARGETS),
            "optimum_sets": len(cases) * len(TARGETS), "numeric_comparisons": numeric_checks,
            "structural_checks": structural_checks, "max_abs_errors": residuals,
            "cases": cases, "elapsed_seconds": perf_counter() - started}


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
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
               "python": platform.python_version(), "passed": False,
               "execution": "one process, standard library, no random draws",
               "forecast_seconds_less_than": 10, "forecast_bytes_less_than": 200000}
    manifest, log_path = output / "MANIFEST.json", output / "RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs recorded before verification.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output / "RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
        with log_path.open("a") as log_file:
            log_file.write(f"PASS: {result['settings']} fixtures, {result['policy_distributions']} "
                           f"policy distributions, {result['objective_scores']} objective scores.\n"
                           f"All {result['optimum_sets']} optimum sets passed.\n"
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
