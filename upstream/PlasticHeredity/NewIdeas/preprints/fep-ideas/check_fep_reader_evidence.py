"""Exact verification of FEP_READER_EVIDENCE_V1.md; standard library only."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, log, sqrt
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback


SPEC = Path(__file__).with_name("FEP_READER_EVIDENCE_V1.md")
TOL = 1e-12
BUNDLES = ("one", "repeat", "anchor", "both")
INDICES = ((4,), (4, 5), (4, 6), (4, 5, 6))
OBJECTIVES = ("bayes", "state", "exact", "full_extension", "task_extension", "regime_extension")
WORLDS = tuple(product((0, 1), repeat=7))


def entropy(q):
    return -fsum(p * log(p) for p in q.values() if p)


def h(p):
    return entropy({0: 1 - p, 1: p})


def marginal(q, fn):
    out = {}
    for s, p in q.items():
        key = fn(s)
        out[key] = out.get(key, 0.) + p
    return out


def information(q, fn, obs):
    joint = marginal(q, lambda s: (fn(s), obs(s)))
    left, right = marginal(q, fn), marginal(q, obs)
    return fsum(p * log(p / (left[x] * right[y])) for (x, y), p in joint.items() if p)


def kl(q, p):
    return fsum(v * log(v / p[s]) for s, v in q.items() if v)


def evidence(w, a):
    return tuple(w[i] for i in INDICES[a])


def observe(s):
    return s[7], evidence(s, s[7]), s[8]


def report(code, obs):
    # This function has access only to the selected, observable bits.
    index = 0
    for bit in obs:
        index = 2 * index + bit
    return (code >> index) & 1


def physical(pC, pT, kappa, shared):
    out = {}
    for w in WORLDS:
        C, T, x, r, y1, y2, z = w
        pr = float(r == x) if C else .5
        py = float(y1 == r and y2 == r) if T else .25
        pz = float(z == r) if shared else (kappa if z == x else 1 - kappa)
        mass = (pC if C else 1-pC) * (pT if T else 1-pT) * .5 * pr * py * pz
        if mass:
            out[w] = mass
    return out


def fixtures():
    base = dict(pC=.5, pT=.5, kappa=.75, shared=False, k=.05, d=.1, beta=4., v=1.)
    changes = (
        ("independent", {}), ("expensive", dict(k=1., d=1.)),
        ("chance_anchor", dict(kappa=.5, d=.05)), ("shared_fault", dict(shared=True)),
        ("erased_independent", dict(pC=0.)), ("erased_shared", dict(pC=0., shared=True)),
        ("task_price_tie", dict(d=.125)),
    )
    return [(name, dict(base, **change)) for name, change in changes]


class Checks:
    def __init__(self):
        self.numeric = 0
        self.structural = 0
        self.errors = {}

    def close(self, name, actual, expected):
        self.numeric += 1
        error = abs(actual - expected)
        self.errors[name] = max(error, self.errors.get(name, 0.))
        if not error <= TOL:
            raise AssertionError((name, actual, expected, error))

    def require(self, condition, message):
        self.structural += 1
        if not condition:
            raise AssertionError(message)


def channel(eta, rho, kappa, shared=False):
    out = {}
    for x, r, y1, y2, z in product((0, 1), repeat=5):
        mass = .5 * (1-eta if r == x else eta)
        mass *= (rho if y1 == r else 1-rho) * (rho if y2 == r else 1-rho)
        mass *= float(z == r) if shared else (kappa if z == x else 1-kappa)
        if mass:
            out[(x, r, y1, y2, z)] = mass
    return out


def check_identification(check):
    rows = []
    settings = ((.1, .8, .75), (.4, .65, .9), (0., 1., 1.),
                (.5, .8, .75), (.2, .5, .75), (.2, .8, .5))
    for eta, rho, kappa in settings:
        q = channel(eta, rho, kappa)
        qo = marginal(q, lambda w: w[2:])
        check.close("channel_normalization", fsum(q.values()), 1.)
        s, t, r = 1-2*eta, 2*rho-1, 2*kappa-1
        for o in product((0, 1), repeat=3):
            u1, u2, z = (1-2*b for b in o)
            expected = (1+t*t*u1*u2+s*t*r*(u1*z+u2*z))/8
            check.close("three_bit_law", qo.get(o, 0.), expected)
        m12 = fsum(p * (1-2*w[2]) * (1-2*w[3]) for w, p in q.items())
        m1z = fsum(p * (1-2*w[2]) * (1-2*w[4]) for w, p in q.items())
        check.close("reader_moment", m12, t*t)
        check.close("grounded_moment", m1z, s*t*r)
        identified = rho > .5 and kappa > .5
        recovered = None
        if identified:
            t_hat = sqrt(m12)
            recovered = dict(rho=(1+t_hat)/2, eta=(1-m1z/(t_hat*r))/2)
            check.close("recovered_rho", recovered["rho"], rho)
            check.close("recovered_eta", recovered["eta"], eta)
        else:
            check.close("degenerate_grounded_moment", m1z, 0.)
        rows.append(dict(eta=eta, rho=rho, kappa=kappa, m12=m12, m1z=m1z,
                         identifiable=identified, recovered=recovered))
    for rho in (.5, .8, 1.):
        for shared in (False, True):
            baseline = None
            for eta in (0., .2, .5):
                q = channel(eta, rho, .75, shared)
                qo = marginal(q, (lambda w: w[2:]) if shared else (lambda w: w[2:4]))
                if baseline is None:
                    baseline = qo
                for o in baseline.keys() | qo.keys():
                    check.close("content_observational_equivalence", qo.get(o, 0.), baseline.get(o, 0.))
    return rows


def verify_fixture(name, f, check):
    q = physical(f["pC"], f["pT"], f["kappa"], f["shared"])
    beta, v, k, d = (f[key] for key in ("beta", "v", "k", "d"))
    prices = (0., k, d, k+d)
    Z = 128*(1+exp(beta*v))*(1+exp(-beta*k))*(1+exp(-beta*d))
    K, HW = log(Z), entropy(q)
    cs = {w+(a, D): exp(beta*(v*(D == w[2])-prices[a]))/Z
          for w in WORLDS for a in range(4) for D in (0, 1)}
    co = marginal(cs, observe)
    check.close("physical_normalization", fsum(q.values()), 1.)
    check.close("preference_normalization", fsum(cs.values()), 1.)
    check.close("preferred_outcome_normalization", fsum(co.values()), 1.)
    hw_analytic = h(f["pC"])+h(f["pT"])+(4-f["pC"]-2*f["pT"])*log(2)
    if not f["shared"]:
        hw_analytic += h(f["kappa"])
    check.close("physical_entropy", HW, hw_analytic)
    anchor_accuracy = fsum(p for w, p in q.items() if w[6] == w[2])
    check.close("reference_accuracy", anchor_accuracy,
                .5+.5*f["pC"] if f["shared"] else f["kappa"])
    actions, records, predictions = [], [], []
    for a, label in enumerate(BUNDLES):
        obs_fn = lambda w: evidence(w, a)
        qo = marginal(q, obs_fn)
        obs_space = tuple(product((0, 1), repeat=len(INDICES[a])))
        targets = dict(full=lambda w: w, task=lambda w: w[2], regime=lambda w: w[:2],
                       content=lambda w: w[0], reader=lambda w: w[1], record=lambda w: w[3])
        info = {target: information(q, fn, obs_fn) for target, fn in targets.items()}
        for target, fn in targets.items():
            conditional_entropy = fsum(
                mass * entropy(marginal({w: p/mass for w, p in q.items() if obs_fn(w) == o}, fn))
                for o, mass in qo.items())
            check.close("information_entropy_identity", info[target],
                        entropy(marginal(q, fn))-conditional_entropy)
        check.close("full_information", info["full"], entropy(qo))
        if a < 2 or f["shared"] or f["kappa"] == .5:
            check.close("no_content_evidence", info["content"], 0.)
        posterior_rows, allowed = [], []
        best_accuracy = 0.
        for o in obs_space:
            mass = qo.get(o, 0.)
            sub = {w: p for w, p in q.items() if obs_fn(w) == o}
            mx = [fsum(p for w, p in sub.items() if w[2] == x) for x in (0, 1)]
            best_accuracy += max(mx)
            allowed.append(tuple(x for x in (0, 1) if max(mx)-mx[x] <= TOL))
            if not mass:
                continue
            post = {w: p/mass for w, p in sub.items()}
            check.close("posterior_normalization", fsum(post.values()), 1.)
            pc = fsum(p for w, p in post.items() if w[0])
            pt = fsum(p for w, p in post.items() if w[1])
            match = fsum(p for w, p in post.items() if w[3] == w[2])
            if a < 2 or f["shared"] or f["kappa"] == .5:
                check.close("unchanged_content_prior", pc, f["pC"])
            if name == "independent" and a == 3:
                expected = ((4/7, 5/7) if o[0] == o[1] == o[2] else
                            (2/5, 3/5) if o[0] == o[1] else (.5, 0.))
                check.close("content_posterior_example", pc, expected[0])
                check.close("reader_posterior_example", pt, expected[1])
            posterior_rows.append(dict(observed=o, probability=mass, p_content_intact=pc,
                                       p_reader_intact=pt, p_record_matches_target=match,
                                       p_target_one=mx[1]/mass))
        good_codes = {sum(bit << i for i, bit in enumerate(bits)) for bits in product(*allowed)}
        bestU = v*best_accuracy-prices[a]
        predicted = dict(zip(OBJECTIVES, (-bestU, K-beta*bestU-HW, K-beta*bestU-HW,
                         K-beta*bestU-info["full"], K-beta*bestU-info["task"],
                         K-beta*bestU-info["regime"])))
        predictions.append((good_codes, predicted))
        actions.append(dict(bundle=label, cost=prices[a], best_accuracy=best_accuracy,
                            best_utility=bestU, information=info, observations=posterior_rows))
        if name in ("independent", "expensive", "task_price_tie"):
            check.close("analytic_accuracy", best_accuracy, .625 if a < 2 else .75)
        if name == "independent":
            ih = (0., h(.75)-log(2)/2, h(9/16)-3*log(2)/4-h(.75)/4,
                  entropy(dict(enumerate((7/16, 5/16, 1/8, 1/8))))-5*log(2)/4-h(.75)/4)
            check.close("analytic_regime_information", info["regime"], ih[a])
        for code in range(1 << len(obs_space)):
            qs = {w+(a, report(code, obs_fn(w))): p for w, p in q.items()}
            qout = marginal(qs, observe)
            check.close("policy_normalization", fsum(qs.values()), 1.)
            for o, mass in qo.items():
                check.close("allowed_observation_law", qout[(a, o, report(code, o))], mass)
            check.close("constant_state_entropy", entropy(qs), HW)
            check.close("observation_entropy", entropy(qout), entropy(qo))
            check.require(all(s[8] == report(code, evidence(s, a)) for s in qs), "hidden report access")
            accuracy = fsum(p for s, p in qs.items() if s[8] == s[2])
            U = v*accuracy-prices[a]
            state = kl(qs, cs)
            outcome = kl(qout, co)
            conditional = fsum(p*log((p/qout[observe(s)])/(cs[s]/co[observe(s)]))
                               for s, p in qs.items())
            ce = -fsum(p*log(cs[s]) for s, p in qs.items())
            scores = dict(zip(OBJECTIVES, (-U, state, outcome+conditional,
                          ce-info["full"], ce-info["task"], ce-info["regime"])))
            check.close("cross_entropy", ce, K-beta*U)
            check.close("state_formula", state, K-beta*U-HW)
            check.close("exact_conditional_decomposition", state, scores["exact"])
            check.require(conditional >= -TOL, "negative conditional KL")
            if name == "erased_shared":
                check.close("erased_shared_chance_bound", accuracy, .5)
            records.append(dict(bundle=label, code=code, accuracy=accuracy, utility=U, scores=scores))
    optima = {}
    for obj in OBJECTIVES:
        low = min(row["scores"][obj] for row in records)
        actual = [row for row in records if row["scores"][obj]-low <= TOL]
        predicted_low = min(p[obj] for codes, p in predictions)
        expected = {(BUNDLES[a], code) for a, (codes, p) in enumerate(predictions)
                    if p[obj]-predicted_low <= TOL for code in codes}
        check.close("optimum_score", low, predicted_low)
        check.require({(r["bundle"], r["code"]) for r in actual} == expected,
                      (name, obj, "optimum set mismatch"))
        optima[obj] = dict(score=low, count=len(actual),
                           policies=[[r["bundle"], r["code"]] for r in actual],
                           utility_range=[min(r["utility"] for r in actual), max(r["utility"] for r in actual)],
                           representative=[actual[0]["bundle"], actual[0]["code"]],
                           representative_utility=actual[0]["utility"])
        if name == "expensive":
            check.require(all(r["bundle"] == "one" for r in actual), "overpriced evidence selected")
    check.require(optima["bayes"]["policies"] == optima["state"]["policies"] == optima["exact"]["policies"],
                  "state/Bayesian ordering differs")
    if name == "task_price_tie":
        check.require({p[0] for p in optima["bayes"]["policies"]} == {"one", "anchor"}, "missing price tie")
    check.require(len(records) == 292, "incomplete policy enumeration")
    return dict(name=name, parameters=f, physical_entropy=HW, reference_accuracy=anchor_accuracy,
                actions=actions, policy_scores=records, optima=optima)


def verify():
    start, check = perf_counter(), Checks()
    identification = check_identification(check)
    results = [verify_fixture(name, fixture, check) for name, fixture in fixtures()]
    return dict(passed=True, settings=len(results), policy_distributions=292*len(results),
                objective_scores=292*len(results)*len(OBJECTIVES), optimum_sets=len(results)*len(OBJECTIVES),
                identification_fixtures=identification, fixtures=results,
                numeric_comparisons=check.numeric, structural_checks=check.structural,
                max_abs_errors=check.errors, tolerance=TOL, elapsed_seconds=perf_counter()-start)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    mount = Path("/mnt/bioIce1")
    namespace = mount / "fep-ideas"
    if not os.path.ismount(mount) or namespace not in output.parents:
        raise SystemExit("Require mounted /mnt/bioIce1 and a new output directory in its FEP namespace")
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__).resolve(), SPEC.resolve())
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size) for p in sources]
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=10)
    manifest, log_path = output / "MANIFEST.json", output / "RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs recorded before verification.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output / "RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as log_file:
            log_file.write(f"PASS: {result['settings']} fixtures; {result['policy_distributions']} policies; "
                           f"{result['objective_scores']} scores; {result['optimum_sets']} optimum sets.\n"
                           f"Numeric comparisons: {result['numeric_comparisons']}.\n"
                           f"Structural checks: {result['structural_checks']}.\n"
                           f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                           f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                           "One process; standard library; no simulation, fitting or random draws.\n")
        receipt["passed"] = True
    except BaseException:
        with log_path.open("a") as log_file:
            log_file.write(traceback.format_exc())
        for path, data in snapshots.items():
            (output / ("FAILED_INPUT_"+path.name)).write_bytes(data)
        raise
    finally:
        receipt["outputs"] = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size)
                              for p in sorted(output.iterdir()) if p.is_file() and p != manifest]
        manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    print(log_path.read_text(), end="")
    print(f"Record: {output}")


if __name__ == "__main__":
    main()
