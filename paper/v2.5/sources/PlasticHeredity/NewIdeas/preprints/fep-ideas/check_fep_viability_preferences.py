"""Exact support, preference and projection checks for the energy-budget assay."""
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, isfinite, isinf, log
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback


ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "FEP_VIABILITY_PREFERENCES_V1.md"
STORE = Path("/mnt/bioIce1/fep-ideas/formal-checks/fep-viability-preferences-v1")
TOL = 1e-12
MODES = ("economy", "precision")
FIXTURES = (
    ("hard", {"epsilon": 0.}, ["economy"]),
    ("task_only", {"epsilon": 1.}, ["precision"]),
    ("soft_tie", {"epsilon": exp(-4.)}, ["economy", "precision"]),
    ("soft_strict", {"epsilon": exp(-8.)}, ["economy"]),
    ("hard_certain_recharge", {"epsilon": 0., "p": 1.}, ["precision"]),
    ("hard_no_recharge", {"epsilon": 0., "p": 0.}, ["economy"]),
    ("biased_reference", {"epsilon": 1., "rho": .25}, ["economy"]),
    ("hard_unavoidable_outage", {"epsilon": 0., "ell": .1}, []),
)


class Checks:
    def __init__(self):
        self.numeric = 0
        self.structural = 0
        self.max_error = 0.

    def require(self, condition, context):
        self.structural += 1
        if not condition:
            raise AssertionError(context)

    def close(self, actual, expected, context):
        self.numeric += 1
        error = abs(actual - expected)
        self.max_error = max(self.max_error, error)
        if not (isfinite(actual) and isfinite(expected) and error <= TOL):
            raise AssertionError((context, actual, expected, error))

    def risk(self, actual, expected, context):
        if isinf(actual) or isinf(expected):
            self.require(actual == expected == float("inf"), context)
        else:
            self.close(actual, expected, context)


def marginal(q, projection):
    out = defaultdict(float)
    for s, mass in q.items():
        out[projection(s)] += mass
    return dict(out)


def kl(q, c):
    if any(mass > 0 and c.get(s, 0.) == 0 for s, mass in q.items()):
        return float("inf")
    return fsum(mass * log(mass / c[s]) for s, mass in q.items() if mass > 0)


def binary_kl(p, q):
    return kl({0: 1-p, 1: p}, {0: 1-q, 1: q})


def reduced(s):
    return s[0], s[1], s[5], s[8], s[10]


def task(s):
    return s[0], s[1], s[9], s[5], s[11], s[7]


def reduced_task(t):
    a, x1, x2, y1, y2 = t
    return a, x1, y1, x2, y2, int(y2 != -1)


def utility(s, f):
    return float(s[1] == s[9]) + f["w"] * (s[5] == s[11])


def physical(f, a):
    q = f["alpha"] if a == 0 else f["gamma"]
    out = {}
    for x1, noise, recharge, outage, x2 in product((0, 1), repeat=5):
        mass = (.25 * (q if noise == 0 else 1-q)
                * (f["p"] if recharge else 1-f["p"])
                * (f["ell"] if outage else 1-f["ell"]))
        if mass == 0:
            continue
        energy = (1-outage) * (1-a+recharge)
        viable = int(energy >= 1)
        y1 = x1 ^ noise
        y2 = x2 if viable else -1
        out[(a, x1, noise, recharge, outage, x2, energy, viable,
             y1, y1, y2, y2)] = mass
    return out


def mixture(laws, r):
    return {s: weight * mass for law, weight in zip(laws, (1-r, r))
            for s, mass in law.items() if weight * mass > 0}


def finite_minima(scores):
    available = [v for v in scores.values() if isfinite(v)]
    if not available:
        return []
    best = min(available)
    return [name for name, score in scores.items() if isfinite(score)
            and abs(score-best) <= TOL]


def optimum(f, v, U):
    if f["epsilon"] == 0:
        safe = [a for a in (0, 1) if v[a] == 1.]
        if not safe:
            return None
        if len(safe) == 1:
            return float(safe[0])
        viability_term = 0.
    else:
        viability_term = (v[0]-v[1]) * log(f["epsilon"])
    odds = log(f["rho"]/(1-f["rho"])) + f["beta"]*(U[1]-U[0]) + viability_term
    return 1 / (1+exp(-odds))


def verify(emit):
    checks = Checks()
    fixtures = []
    policy_count = 0
    infinity_count = 0
    for name, overrides, expected_minima in FIXTURES:
        f = dict(alpha=.75, gamma=.9, p=.9, ell=0., w=.5, beta=4., rho=.5)
        f.update(overrides)
        laws = [physical(f, a) for a in (0, 1)]
        mu = mixture(laws, f["rho"])
        v = [1-f["ell"], (1-f["ell"])*f["p"]]
        U = [q+f["w"]*live for q, live in zip((f["alpha"], f["gamma"]), v)]
        for a, law in enumerate(laws):
            checks.close(fsum(law.values()), 1., (name, a, "physical mass"))
            joint_targets = marginal(law, lambda s: (s[1], s[5]))
            for mass in joint_targets.values():
                checks.close(mass, .25, (name, a, "independent fair targets"))
            for s in law:
                checks.require(s[0] == a and s[9] == s[8] and s[11] == s[10],
                               (name, "mode and fixed reports"))
                checks.require(s[6] == (1-s[4])*(1-a+s[3]) and s[7] == (s[6] >= 1),
                               (name, "energy and continuation"))
                checks.require(s[10] == (s[5] if s[7] else -1), (name, "future access"))
                checks.require(task(s) == reduced_task(reduced(s)), (name, "task retained"))

        weights = {s: mass*exp(f["beta"]*utility(s, f))
                   * (1. if s[7] else f["epsilon"]) for s, mass in mu.items()}
        Z = fsum(weights.values())
        c = {s: mass/Z for s, mass in weights.items()}
        h = lambda q: 1-q+q*exp(f["beta"])
        z_terms = [prior*h(q)*(live*exp(f["beta"]*f["w"])+(1-live)*f["epsilon"])
                   for prior, q, live in zip((1-f["rho"], f["rho"]),
                                             (f["alpha"], f["gamma"]), v)]
        checks.close(Z, fsum(z_terms), (name, "independent normalizer"))
        checks.close(fsum(mu.values()), 1., (name, "reference mass"))
        checks.close(fsum(c.values()), 1., (name, "preference mass"))
        ct = marginal(c, reduced)
        cb = marginal(c, task)
        cb_reduced = marginal(ct, reduced_task)
        for b, mass in cb.items():
            checks.close(cb_reduced[b], mass, (name, "preferred task joint"))
        for t, mass in ct.items():
            a, x1, x2, y1, y2 = t
            prior = (1-f["rho"], f["rho"])[a]
            q = (f["alpha"], f["gamma"])[a]
            read_probability = q if x1 == y1 else 1-q
            live = y2 != -1
            mu_t = prior * .25 * read_probability * (v[a] if live else 1-v[a])
            u_t = float(x1 == y1) + f["w"]*(x2 == y2)
            expected = mu_t * exp(f["beta"]*u_t) * (1. if live else f["epsilon"]) / Z
            checks.close(mass, expected, (name, "independent projected preference"))

        r_star = optimum(f, v, U)
        checkpoints = [0., .25, .5, .75, 1.]
        if r_star is not None and r_star not in checkpoints:
            checkpoints.append(r_star)
        j_star = kl(mixture(laws, r_star), c) if r_star is not None else None
        rows = []
        scores = {}
        matched_scores = {}
        for r in checkpoints:
            q = mixture(laws, r)
            qt = marginal(q, reduced)
            actual_u = fsum(mass*utility(s, f) for s, mass in q.items())
            actual_v = fsum(mass*s[7] for s, mass in q.items())
            expected_u = (1-r)*U[0]+r*U[1]
            fail = (1-r)*(1-v[0])+r*(1-v[1])
            full_risk = kl(q, c)
            projected_risk = kl(qt, ct)
            feasible = f["epsilon"] > 0 or fail == 0
            predicted = float("inf")
            if feasible:
                predicted = log(Z)+binary_kl(r, f["rho"])-f["beta"]*expected_u
                if f["epsilon"] > 0:
                    predicted -= fail*log(f["epsilon"])
            checks.close(fsum(q.values()), 1., (name, r, "policy mass"))
            checks.close(actual_u, expected_u, (name, r, "utility"))
            checks.close(actual_v, 1-fail, (name, r, "continuation"))
            checks.risk(full_risk, predicted, (name, r, "risk identity"))
            checks.risk(projected_risk, full_risk, (name, r, "projection invariance"))
            if isfinite(full_risk):
                conditional = 0.
                for s, mass in q.items():
                    t = reduced(s)
                    conditional += mass*log((mass/qt[t])/(c[s]/ct[t]))
                    checks.close(mass/qt[t], c[s]/ct[t], (name, r, "common conditional"))
                checks.close(conditional, 0., (name, r, "removed conditional KL"))
                checks.require(r_star is not None, (name, "finite policy requires optimum"))
                checks.close(full_risk-j_star, binary_kl(r, r_star),
                             (name, r, "global optimum certificate"))
            else:
                infinity_count += 1
                checks.require(any(mass > 0 and c[s] == 0 and s[7] == 0
                                   for s, mass in q.items()), (name, r, "failure support witness"))
            if r in (0., 1.):
                a = int(r)
                scores[MODES[a]] = full_risk
                cost = -log((1-f["rho"], f["rho"])[a])/f["beta"]
                value = U[a]-cost
                if f["epsilon"] > 0:
                    value += (1-v[a])*log(f["epsilon"])/f["beta"]
                matched_scores[MODES[a]] = -value if feasible else float("inf")
            rows.append(dict(precision_probability=r, utility=actual_u,
                             continuation_probability=actual_v, full_risk=full_risk,
                             projected_risk=projected_risk, finite=feasible))
            policy_count += 1
        selected = finite_minima(scores)
        checks.require(selected == expected_minima, (name, "frozen deterministic prediction", selected))
        checks.require(selected == finite_minima(matched_scores), (name, "matched Bayesian optima"))
        ca = marginal(c, lambda s: s[0])
        for a in (0, 1):
            checks.close(ca[a], z_terms[a]/Z, (name, "preferred action marginal"))
        shortcut = finite_minima({MODES[a]: -log(ca[a]) if ca[a] > 0 else float("inf")
                                 for a in (0, 1)})
        if name == "hard":
            checks.require(shortcut == ["precision"] and isinf(scores["precision"]),
                           "survivor marginal conceals hard failure")
        fixtures.append(dict(name=name, parameters=f, normalizer=Z,
                             physical_state_count=len(mu), policy_checks=rows,
                             deterministic_optima=selected,
                             matched_Bayesian_optima=finite_minima(matched_scores),
                             raw_utility_optima=finite_minima(dict(zip(MODES, (-U[0], -U[1])))),
                             analytic_random_optimum=r_star, preferred_action_mass=ca,
                             invalid_action_only_shortcut=shortcut,
                             reference_and_preference=[dict(state=list(s), reference=mass,
                                                            preferred=c[s]) for s, mass in mu.items()]))
        emit(f"{name}: deterministic={selected}; random optimum={r_star}; support checked")
    return dict(passed=True, fixtures=fixtures, fixture_count=len(fixtures),
                policy_distribution_checks=policy_count, infinite_policy_scores=infinity_count,
                numeric_comparisons=checks.numeric, structural_checks=checks.structural,
                max_abs_error=checks.max_error, tolerance=TOL)


def clean(value):
    if isinstance(value, float) and isinf(value):
        return "infinite"
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


def file_record(path):
    content = path.read_bytes()
    return dict(path=str(path), bytes=len(content), sha256=sha256(content).hexdigest())


def main():
    parser = ArgumentParser()
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--expected-spec-sha256", required=True)
    parser.add_argument("--expected-checker-sha256", required=True)
    args = parser.parse_args()
    if not os.path.ismount("/mnt/bioIce1"):
        raise SystemExit("External mount absent; refusing workspace fallback")
    out = args.outdir.resolve()
    if STORE.resolve() not in out.parents:
        raise SystemExit("Output must be an attempt below the FEP viability store")
    inputs = [file_record(SPEC), file_record(Path(__file__).resolve())]
    if [item["sha256"] for item in inputs] != [args.expected_spec_sha256, args.expected_checker_sha256]:
        raise SystemExit("Frozen source identity mismatch; no attempt started")
    out.mkdir(parents=True, exist_ok=False)
    created = datetime.now(timezone.utc).isoformat()
    start = perf_counter()
    passed = False
    outputs = []
    with (out/"RUN_LOG.txt").open("x") as stream:
        def emit(line):
            print(line, file=stream, flush=True)
        emit(f"Started {created}; Python {platform.python_version()}; one process; forecast under 30 seconds")
        for item in inputs:
            emit(json.dumps(item, sort_keys=True))
        try:
            result = verify(emit)
            result.update(created_utc=created, elapsed_seconds=perf_counter()-start)
            with (out/"RESULTS.json").open("x") as handle:
                json.dump(clean(result), handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
            outputs.append(out/"RESULTS.json")
            passed = True
            emit(f"PASS: {result['fixture_count']} fixtures; {result['policy_distribution_checks']} policy distributions; "
                 f"{result['numeric_comparisons']} numeric and {result['structural_checks']} structural checks; "
                 f"max error {result['max_abs_error']:.12g}; {result['elapsed_seconds']:.9f} seconds")
        except Exception:
            traceback.print_exc(file=stream)
            emit("FAIL: attempt preserved; no source retuning or overwrite")
    outputs.append(out/"RUN_LOG.txt")
    manifest = dict(created_utc=created, passed=passed, python=platform.python_version(),
                    process_count=1, forecast_seconds_under=30, inputs=inputs,
                    outputs=[file_record(path) for path in outputs])
    with (out/"MANIFEST.json").open("x") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    if not passed:
        raise SystemExit(f"Verification failed; retained record: {out}")
    print(json.dumps({key: value for key, value in result.items() if key != "fixtures"}, sort_keys=True))
    print(f"Record: {out}")


if __name__ == "__main__":
    main()
