"""Finite verification of the two-report formulation bridge; standard library only."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, isclose, log, log1p
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback


TOL = 1e-12
SPEC = Path(__file__).with_name("FEP_TWO_REPORT_FORMULATION_BRIDGE_V1.md")
N = (0, 0, 0, 0, 0)
E = (1, 1, 0, 0, 0)
L = (0, 0, 0, 1, 1)
B = (1, 1, 0, 1, 1)
TARGETS = ("bayes", "state", "exact_decomposition", "outcome_dropped",
           "latent_extension", "terminal_match_outcome")


def entropy(q):
    return -fsum(p * log(p) for p in q.values() if p)


def kl(q, p):
    return fsum(v * log(v / p[s]) for s, v in q.items() if v)


def normalized(weights):
    z = fsum(weights.values())
    return {s: w / z for s, w in weights.items()}


def observe(s):
    g1, g2, a, b = s
    return a, g1 if a else None, b, g2 if b else None


def marginal(q, fn):
    result = {}
    for s, p in q.items():
        o = fn(s)
        result[o] = result.get(o, 0.0) + p
    return result


def policies():
    no_early = [(0, r, r, b, b) for r, b in product((0, 1), repeat=2)]
    early = [(1, r0, r1, b0, b1)
             for r0, r1, b0, b1 in product((0, 1), repeat=4)]
    return sorted(no_early + early)


def physical(policy):
    a, r0, r1, b0, b1 = policy
    q = {}
    for hidden in (0, 1):
        g1 = 1 - hidden
        # Only purchased first-report feedback chooses a contingent branch.
        branch = g1 if a else 0
        report = (r0, r1)[branch]
        b = (b0, b1)[branch]
        s = g1, int(report == hidden), a, b
        q[s] = q.get(s, 0.0) + 0.5
    return q


def verify():
    started = perf_counter()
    residuals = {}
    checks = 0

    def check(name, value, expected):
        nonlocal checks
        checks += 1
        error = abs(value - expected)
        residuals[name] = max(residuals.get(name, 0.0), error)
        if error > TOL:
            raise AssertionError((name, value, expected, error))

    ps = policies()
    assert len(ps) == len(set(ps)) == 20
    for p in ps:
        if not p[0]:
            assert p[1] == p[2] and p[3] == p[4]
        assert len(physical(p)) == 2
    beta, ell = 4.0, log(2)
    fixtures = [("cheap", 0.1), ("useful_disagreement", 0.25),
                ("overpayment", 0.6), ("outcome_tie", ell / beta),
                ("task_tie", 0.5), ("latent_tie", 0.5 + ell / beta)]
    cases = []
    for name, price in fixtures:
        cs = normalized({s: exp(beta * (s[0] + s[1] - price * (s[2] + s[3])))
                         for s in product((0, 1), repeat=4)})
        co = marginal(cs, observe)
        star = normalized({o: exp(-beta * price * (o[0] + o[2])) for o in co})
        for label, density in (("state", cs), ("outcome", co), ("star", star)):
            check(label + "_normalization", fsum(density.values()), 1.0)
        assert len(cs) == 16 and len(co) == len(star) == 9
        constant = 2 * log1p(exp(beta)) + 2 * log1p(exp(-beta * price))
        star_constant = 2 * log1p(2 * exp(-beta * price))
        cf = log1p(exp(beta)) - beta / 2
        c1 = log1p(exp(beta)) - beta
        df = cf - ell
        rows = []
        for policy in ps:
            qs = physical(policy)
            qo = marginal(qs, observe)
            check("physical_normalization", fsum(qs.values()), 1.0)
            check("fixed_state_entropy", entropy(qs), ell)
            audits = fsum(p * (s[2] + s[3]) for s, p in qs.items())
            utility = fsum(p * (s[0] + s[1]) for s, p in qs.items()) - price * audits
            ce = -fsum(p * log(cs[s]) for s, p in qs.items())
            gap = fsum(p * log((p / qo[observe(s)]) /
                              (cs[s] / co[observe(s)])) for s, p in qs.items())
            info = fsum(p * log(1 / qo[observe(s)]) for s, p in qs.items())
            scores = {"bayes": -utility, "state": kl(qs, cs),
                      "exact_decomposition": kl(qo, co) + gap,
                      "outcome_dropped": kl(qo, co),
                      "latent_extension": ce - info,
                      "terminal_match_outcome": kl(qo, star)}
            check("latent_preference_cost", ce, constant - beta * utility)
            check("deterministic_information", info, entropy(qo))
            check("state_closed_form", scores["state"], constant - beta * utility - ell)
            check("exact_kl_decomposition", scores["state"], scores["exact_decomposition"])
            check("posterior_entropy_gap", scores["latent_extension"] - scores["state"], ell - info)
            check("star_closed_form", scores["terminal_match_outcome"],
                  star_constant + beta * price * audits - info)
            assert gap >= -TOL
            rows.append({"policy": policy, "utility": utility, "expected_audits": audits,
                         "information": info, "conditional_kl": gap, "scores": scores})
        by_policy = {tuple(r["policy"]): r for r in rows}
        for policy, expected_gap in ((N, 2 * cf - ell), (E, c1), (L, cf), (B, 0.0)):
            check("canonical_posterior_gap", by_policy[policy]["conditional_kl"], expected_gap)
        expected_deltas = {
            E: (beta * (price - .5), beta * price + df,
                beta * (price - .5) - ell, beta * price - ell),
            L: (beta * price, beta * price + df, beta * price - ell, beta * price - ell),
            B: (beta * (2 * price - .5), 2 * beta * price + df + c1,
                beta * (2 * price - .5) - ell, 2 * beta * price - ell)}
        for policy, deltas in expected_deltas.items():
            for target, expected in zip(("state", "outcome_dropped", "latent_extension",
                                         "terminal_match_outcome"), deltas):
                check("canonical_" + target, by_policy[policy]["scores"][target] -
                      by_policy[N]["scores"][target], expected)
        no_audit = {p for p in ps if p[0] == 0 and p[3] == 0}
        early_useful = {E}
        single_information = {p for p in ps if
                              (p[0] == 0 and p[3] == 1) or
                              (p[0] == 1 and p[3] == p[4] == 0)}

        def threshold_set(threshold, below):
            if isclose(price, threshold, rel_tol=0, abs_tol=TOL):
                return no_audit | below
            return below if price < threshold else no_audit

        expected_optima = {
            "bayes": threshold_set(.5, early_useful),
            "state": threshold_set(.5, early_useful),
            "exact_decomposition": threshold_set(.5, early_useful),
            "outcome_dropped": no_audit,
            "latent_extension": threshold_set(.5 + ell / beta, early_useful),
            "terminal_match_outcome": threshold_set(ell / beta, single_information)}
        optima = {}
        for target in TARGETS:
            best = min(row["scores"][target] for row in rows)
            winners = [row for row in rows if row["scores"][target] <= best + TOL]
            actual = {tuple(row["policy"]) for row in winners}
            assert actual == expected_optima[target], (name, target, actual, expected_optima[target])
            optima[target] = {"policies": [r["policy"] for r in winners],
                              "representative": winners[0]["policy"],
                              "representative_utility": winners[0]["utility"],
                              "utility_range": [min(r["utility"] for r in winners),
                                                max(r["utility"] for r in winners)]}
        cases.append({"name": name, "beta": beta, "audit_price": price,
                      "policy_scores": rows, "optima": optima})

    # Generic terminal belief checks are separate from the fair-prior trajectory fixtures.
    terminal = []
    for p in (0.0, 0.5, 0.8, 1.0):
        price = .25
        qg = {0: 1 - p, 1: p}
        cg = normalized({g: exp(beta * g) for g in (0, 1)})
        cs = normalized({(g, a): exp(beta * (g - price * a))
                         for g, a in product((0, 1), repeat=2)})
        obs = lambda s: (s[1], s[0] if s[1] else None)
        co = marginal(cs, obs)
        star = normalized({o: exp(-beta * price * o[0]) for o in co})
        scores = []
        for a in (0, 1):
            qs = {(g, a): mass for g, mass in qg.items() if mass}
            qo = marginal(qs, obs)
            ce = -fsum(mass * log(cs[s]) for s, mass in qs.items())
            scores.append({"state": kl(qs, cs), "outcome_dropped": kl(qo, co),
                           "latent_extension": ce - entropy(qo),
                           "terminal_match_outcome": kl(qo, star)})
        expected = {"state": beta * price, "outcome_dropped": beta * price + kl(qg, cg),
                    "latent_extension": beta * price - entropy(qg),
                    "terminal_match_outcome": beta * price - entropy(qg)}
        delta = {t: scores[1][t] - scores[0][t] for t in expected}
        for t in expected:
            check("terminal_" + t, delta[t], expected[t])
        terminal.append({"success_probability": p, "beta": beta,
                         "audit_price": price, "audit_minus_skip": delta})
    return {"passed": True, "kind": "finite arithmetic verification, not sampled evidence",
            "settings": len(cases), "policies_per_setting": len(ps),
            "policy_distributions": len(cases) * len(ps), "objectives": len(TARGETS),
            "terminal_checks": terminal, "numeric_comparisons": checks,
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
    inputs = [{"path": str(p), "sha256": digest(p)} for p in sources]
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "inputs": inputs, "passed": False}
    log_path = output / "RUN_LOG.txt"
    try:
        result = verify()
        assert inputs == [{"path": str(p), "sha256": digest(p)} for p in sources]
        result["created_utc"] = receipt["created_utc"]
        (output / "RESULTS.json").write_text(json.dumps(result, sort_keys=True, indent=1) + "\n")
        log_path.write_text(f"PASS: {result['settings']} fixtures, "
                            f"{result['policy_distributions']} policy distributions, "
                            f"{result['objectives']} scores per policy.\n"
                            f"All 36 optimum sets and 4 terminal belief checks passed.\n"
                            f"Numeric comparisons: {result['numeric_comparisons']}.\n"
                            f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                            f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                            "One process, standard library, no simulation or random draws.\n")
        receipt["passed"] = True
    except Exception:
        log_path.write_text(traceback.format_exc())
        for source in sources:
            (output / ("FAILED_INPUT_" + source.name)).write_bytes(source.read_bytes())
        raise
    finally:
        receipt["outputs"] = [{"path": str(p), "sha256": digest(p), "bytes": p.stat().st_size}
                              for p in sorted(output.iterdir()) if p.is_file()]
        (output / "MANIFEST.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(log_path.read_text(), end="")
    print(f"Record: {output}")


if __name__ == "__main__":
    main()
