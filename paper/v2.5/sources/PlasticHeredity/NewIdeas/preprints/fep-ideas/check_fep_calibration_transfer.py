"""Exact contingent-policy check of FEP_CALIBRATION_TRANSFER_V1.md."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, log, prod
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback

from check_fep_reader_evidence import Checks, entropy, h, information, kl, marginal, physical, report


SPEC = Path(__file__).with_name("FEP_CALIBRATION_TRANSFER_V1.md")
HELPER = Path(__file__).with_name("check_fep_reader_evidence.py")
TOL, L = 1e-12, log(2)
BUNDLES = ("skip", "one", "repeat", "anchor", "both")
INDICES = ((), (4,), (4, 5), (4, 6), (4, 5, 6))
OBJECTIVES = ("bayes", "state", "full_extension", "task_extension", "regime_extension")
CHOICES = tuple((m, b, code) for m in (0, 1) for b in (0, 1)
                for code in range(1 << (2 ** (1+b))))


def fixtures():
    base = dict(pC=.5, pT=.5, kappa0=.75, kappa1=.75, ell=.0025, d0=.1,
                c=.125, d1=.25, beta=8., v=1., reset=False, repair=True)
    changes = (("persistent", {}), ("reset", dict(reset=True)),
               ("weaker_preferences", dict(beta=4.)), ("costly_calibration", dict(ell=.01)),
               ("cheap_final_reference", dict(d1=.01)), ("maintenance_disabled", dict(repair=False)),
               ("content_erased", dict(pC=0.)), ("bayes_price_tie", dict(ell=1/64)),
               ("state_price_tie", dict(ell=(1/32-L/32)/2)))
    return [(name, dict(base, **change)) for name, change in changes]


def prices(f):
    ell, d0 = f["ell"], f["d0"]
    return (0., ell, 2*ell, ell+d0, 2*ell+d0)


def prior(f):
    return {(C, T): (f["pC"] if C else 1-f["pC"])*(f["pT"] if T else 1-f["pT"])
            for C, T in product((0, 1), repeat=2)
            if (f["pC"] if C else 1-f["pC"])*(f["pT"] if T else 1-f["pT"])}


def history(w0, a):
    return tuple(w0[i] for i in INDICES[a])


def final_bits(w1, b):
    return w1[4:6] if b else (w1[4],)


def future(qH, m, f):
    q = {}
    for (C, T), ph in qH.items():
        for x, r, y, z in product((0, 1), repeat=4):
            pr = float(r == x) if C else .5
            py = float(y == r) if T or (m and f["repair"]) else .5
            pz = f["kappa1"] if z == x else 1-f["kappa1"]
            mass = ph * .5 * pr * py * pz
            if mass:
                q[C, T, x, r, y, z] = mass
    return q


def terminal(qH, f, checks):
    pbad = fsum(p for (C, T), p in qH.items() if not T)
    rows, groups, predicted = [], {}, {obj: [] for obj in OBJECTIVES}
    for m in (0, 1):
        q = future(qH, m, f)
        checks.close("future_normalization", fsum(q.values()), 1.)
        for b in (0, 1):
            obs = lambda w: final_bits(w, b)
            qo = marginal(q, obs)
            info = dict(full=entropy(qo), task=information(q, lambda w: w[2], obs),
                        regime=information(q, lambda w: w[:2], obs))
            for target, fn in (("task", lambda w: w[2]), ("regime", lambda w: w[:2])):
                conditional = fsum(mass*entropy(marginal(
                    {w: p/mass for w, p in q.items() if obs(w) == o}, fn)) for o, mass in qo.items())
                checks.close("terminal_information_identity", info[target], entropy(marginal(q, fn))-conditional)
            qread = .5+.5*fsum(p for (C, T), p in qH.items() if C and (T or (m and f["repair"])))
            best_accuracy = max(qread, f["kappa1"]) if b else qread
            choices_by_observation = []
            posterior_accuracy = 0.
            for o in product((0, 1), repeat=1+b):
                mx = [fsum(p for w, p in q.items() if obs(w) == o and w[2] == x) for x in (0, 1)]
                posterior_accuracy += max(mx)
                choices_by_observation.append(tuple(x for x in (0, 1) if max(mx)-mx[x] <= TOL))
            checks.close("optimal_accuracy_formula", posterior_accuracy, best_accuracy)
            good_codes = {sum(bit << i for i, bit in enumerate(bits)) for bits in product(*choices_by_observation)}
            Ubest = f["v"]*best_accuracy-f["c"]*m-f["d1"]*b
            penalty = L*m*pbad if f["repair"] else 0.
            best_scores = (-Ubest, -f["beta"]*Ubest+penalty,
                           -f["beta"]*Ubest-info["full"], -f["beta"]*Ubest-info["task"],
                           -f["beta"]*Ubest-info["regime"])
            for obj, score in zip(OBJECTIVES, best_scores):
                predicted[obj].append((score, {(m, b, code) for code in good_codes}))
            for code in range(1 << (2 ** (1+b))):
                accuracy = fsum(p for w, p in q.items() if report(code, obs(w)) == w[2])
                U = f["v"]*accuracy-f["c"]*m-f["d1"]*b
                scores = dict(zip(OBJECTIVES, (-U, -f["beta"]*U+penalty,
                              -f["beta"]*U-info["full"], -f["beta"]*U-info["task"],
                              -f["beta"]*U-info["regime"])))
                rows.append(dict(choice=(m, b, code), accuracy=accuracy, utility=U, scores=scores))
                if not f["pC"] and not b:
                    checks.close("erased_record_chance_bound", accuracy, .5)
    checks.require(tuple(row["choice"] for row in rows) == CHOICES, "incomplete terminal choices")
    for obj in OBJECTIVES:
        minimum = min(row["scores"][obj] for row in rows)
        opts = [row for row in rows if row["scores"][obj]-minimum <= TOL]
        analytic_min = min(score for score, codes in predicted[obj])
        expected = set().union(*(codes for score, codes in predicted[obj] if score-analytic_min <= TOL))
        checks.close("terminal_optimum_score", minimum, analytic_min)
        checks.require({row["choice"] for row in opts} == expected, "incomplete local optimum set")
        if not f["repair"]:
            checks.require(all(row["choice"][0] == 0 for row in opts), "ineffective maintenance selected")
        groups[obj] = dict(score=minimum, choices=[row["choice"] for row in opts],
                           utility_range=[min(row["utility"] for row in opts), max(row["utility"] for row in opts)],
                           representative_utility=opts[0]["utility"])
    return rows, groups


def trajectory(q0, a, policy, f):
    q = {}
    native = prior(f)
    cache = {}
    for w0, p0 in q0.items():
        m, b, code = policy[history(w0, a)]
        key = (w0[:2], m)
        if key not in cache:
            cache[key] = future(native if f["reset"] else {w0[:2]: 1.}, m, f)
        for w1, p1 in cache[key].items():
            D = report(code, final_bits(w1, b))
            q[w0+w1+(a, m, b, D)] = p0*p1
    return q


def observed(s):
    a, m, b, D = s[13:17]
    return a, history(s, a), m, b, final_bits(s[7:13], b), D


def audit_trajectory(q, f, a, K, Hbase, checks):
    pp, beta = prices(f), f["beta"]
    qout = marginal(q, observed)
    ca = [exp(-beta*p) for p in pp]
    za, zm, zb = fsum(ca), 1+exp(-beta*f["c"]), 1+exp(-beta*f["d1"])
    cs = {s: exp(beta*(f["v"]*(s[16] == s[9])-pp[a]-f["c"]*s[14]-f["d1"]*s[15])-K) for s in q}
    co = {o: ca[a]/za*exp(-beta*f["c"]*o[2])/zm*exp(-beta*f["d1"]*o[3])/zb
          /2**(len(o[1])+len(o[4])+1) for o in qout}
    checks.close("trajectory_normalization", fsum(q.values()), 1.)
    accuracy = fsum(p for s, p in q.items() if s[16] == s[9])
    mr = fsum(p for s, p in q.items() if s[14])
    br = fsum(p for s, p in q.items() if s[15])
    U = f["v"]*accuracy-pp[a]-f["c"]*mr-f["d1"]*br
    removed = L*fsum(p for s, p in q.items() if s[14] and not s[8]) if f["repair"] else 0.
    checks.close("physical_entropy_formula", entropy(q), Hbase-removed)
    state = kl(q, cs)
    conditional = fsum(p*log((p/qout[observed(s)])/(cs[s]/co[observed(s)])) for s, p in q.items())
    checks.close("conditional_KL_decomposition", state, kl(qout, co)+conditional)
    checks.require(conditional >= -TOL, "negative conditional KL")
    ce = -fsum(p*log(cs[s]) for s, p in q.items())
    checks.close("preferred_cross_entropy", ce, K-beta*U)
    info = dict(full=information(q, lambda s: s, observed),
                task=information(q, lambda s: s[9], observed),
                regime=information(q, lambda s: s[7:9], observed))
    checks.close("deterministic_observation_information", info["full"], entropy(qout))
    scores = dict(bayes=-U, state=state, full_extension=ce-info["full"],
                  task_extension=ce-info["task"], regime_extension=ce-info["regime"])
    checks.close("content_causal_invariance", fsum(p for s, p in q.items() if s[9] == s[10]), .5+.5*f["pC"])
    checks.close("future_content_prior", fsum(p for s, p in q.items() if s[7]), f["pC"])
    checks.close("future_reader_prior", fsum(p for s, p in q.items() if s[8]), f["pT"])
    return dict(utility=U, accuracy=accuracy, maintenance_rate=mr, final_reference_rate=br,
                calibration_cost=pp[a], information=info, physical_entropy=entropy(q),
                conditional_KL=conditional, scores=scores)


def verify_fixture(name, f, checks):
    q0 = physical(f["pC"], f["pT"], f["kappa0"], False)
    checks.close("calibration_normalization", fsum(q0.values()), 1.)
    hprior = prior(f)
    pp, beta = prices(f), f["beta"]
    z = 8192*(1+exp(beta*f["v"]))*fsum(exp(-beta*p) for p in pp)
    z *= (1+exp(-beta*f["c"]))*(1+exp(-beta*f["d1"]))
    # Sum preferred masses by the 4096 states with each value of X1.
    preferred_mass = fsum(4096*exp(beta*(f["v"]*(D == x)-pp[a]-f["c"]*m-f["d1"]*b))/z
                          for x, D, m, b in product((0, 1), repeat=4) for a in range(5))
    checks.close("preferred_state_normalization", preferred_mass, 1.)
    Hbase = entropy(q0)+(entropy(hprior) if f["reset"] else 0.)
    Hbase += (3-f["pC"]-f["pT"])*L+h(f["kappa1"])
    K = log(z)
    bundles = []
    for a, label in enumerate(BUNDLES):
        ph = marginal(q0, lambda w: history(w, a))
        prefix_I = 0. if f["reset"] else information(q0, lambda w: w[:2], lambda w: history(w, a))
        histories = []
        for hist in product((0, 1), repeat=len(INDICES[a])):
            mass = ph.get(hist, 0.)
            checks.require(mass > 0., "fixture includes an unreachable calibration history")
            post = {w: p/mass for w, p in q0.items() if history(w, a) == hist}
            qH = hprior if f["reset"] else marginal(post, lambda w: w[:2])
            checks.close("mechanism_posterior_normalization", fsum(qH.values()), 1.)
            if f["reset"]:
                for H in hprior:
                    checks.close("reset_prior_unchanged", qH.get(H, 0.), hprior[H])
            if a == 2 and not f["reset"]:
                checks.close("repeat_content_prior", fsum(p for H, p in qH.items() if H[0]), f["pC"])
                checks.close("repeat_reader_posterior", fsum(p for H, p in qH.items() if H[1]),
                             2/3 if hist[0] == hist[1] else 0.)
            rows, opt = terminal(qH, f, checks)
            histories.append(dict(history=hist, probability=mass,
                                  future_mechanism_posterior=[dict(mechanism=H, probability=p) for H, p in sorted(qH.items())],
                                  terminal_scores=[list(row["choice"])+[row["accuracy"], row["utility"]]
                                                   +[row["scores"][obj] for obj in OBJECTIVES] for row in rows],
                                  optima=opt))
        bundle = dict(bundle=label, calibration_cost=pp[a], prefix_entropy=entropy(ph),
                      prefix_future_regime_information=prefix_I, histories=histories, objectives={})
        for obj in OBJECTIVES:
            offset = pp[a] if obj == "bayes" else beta*pp[a]
            if obj == "full_extension":
                offset -= entropy(ph)
            elif obj == "regime_extension":
                offset -= prefix_I
            score = offset+fsum(row["probability"]*row["optima"][obj]["score"] for row in histories)
            policy = {row["history"]: row["optima"][obj]["choices"][0] for row in histories}
            q = trajectory(q0, a, policy, f)
            # The independent future target carries no calibration information.
            checks.close("no_answer_transfer", information(q, lambda s: s[9], lambda s: history(s, a)), 0.)
            checks.close("prefix_information_chain", information(q, lambda s: s[7:9], lambda s: history(s, a)), prefix_I)
            direct = audit_trajectory(q, f, a, K, Hbase, checks)
            expected = score if obj == "bayes" else K+score-(Hbase if obj == "state" else 0.)
            checks.close("dynamic_vs_whole_trajectory", direct["scores"][obj], expected)
            utility_range = [fsum(row["probability"]*row["optima"][obj]["utility_range"][side]
                                  for row in histories)-pp[a] for side in (0, 1)]
            expected_U = fsum(row["probability"]*row["optima"][obj]["representative_utility"] for row in histories)-pp[a]
            checks.close("representative_utility", direct["utility"], expected_U)
            # Construct policies attaining both utility endpoints of the complete tie product.
            row_by_hist = {row["history"]: row for row in histories}
            for side in (0, 1):
                attained = 0.
                for hist, row in row_by_hist.items():
                    allowed = set(row["optima"][obj]["choices"])
                    utilities = [r[4] for r in row["terminal_scores"] if tuple(r[:3]) in allowed]
                    attained += row["probability"]*(min(utilities) if side == 0 else max(utilities))
                checks.close("attainable_tie_utility", attained-pp[a], utility_range[side])
            bundle["objectives"][obj] = dict(reduced_score=score, policy_count=prod(len(row["optima"][obj]["choices"]) for row in histories),
                                                utility_range=utility_range, representative=direct)
        bundles.append(bundle)
    optima = {}
    for obj in OBJECTIVES:
        minimum = min(bundle["objectives"][obj]["reduced_score"] for bundle in bundles)
        opts = [bundle for bundle in bundles if bundle["objectives"][obj]["reduced_score"]-minimum <= TOL]
        optima[obj] = dict(reduced_score=minimum, bundles=[bundle["bundle"] for bundle in opts],
                           policy_count=sum(bundle["objectives"][obj]["policy_count"] for bundle in opts),
                           utility_range=[min(b["objectives"][obj]["utility_range"][0] for b in opts),
                                          max(b["objectives"][obj]["utility_range"][1] for b in opts)],
                           representative_bundle=opts[0]["bundle"], representative=opts[0]["objectives"][obj]["representative"])
    if name in ("persistent", "weaker_preferences", "costly_calibration", "bayes_price_tie", "state_price_tie"):
        checks.close("analytic_repeat_utility", bundles[2]["objectives"]["bayes"]["representative"]["utility"], 21/32-2*f["ell"])
        checks.close("prior_only_bayesian_utility", bundles[0]["objectives"]["bayes"]["representative"]["utility"], 5/8)
        if beta == 8.:
            delta = bundles[2]["objectives"]["state"]["reduced_score"]-bundles[0]["objectives"]["state"]["reduced_score"]
            checks.close("analytic_state_transfer_difference", delta, beta*(2*f["ell"]-1/32)+L/4)
    expected_bundles = {
        "persistent": {"bayes": ["repeat"], "state": ["repeat"]},
        "reset": {o: ["skip"] for o in ("bayes", "state", "task_extension", "regime_extension")},
        "weaker_preferences": {"bayes": ["repeat"], "state": ["skip"]},
        "costly_calibration": {"bayes": ["repeat"], "state": ["skip"]},
        "cheap_final_reference": {"bayes": ["skip"], "state": ["skip"]},
        "maintenance_disabled": {"bayes": ["skip"], "state": ["skip"]},
        "content_erased": {"bayes": ["skip"], "state": ["skip"]},
        "bayes_price_tie": {"bayes": ["skip", "repeat"], "state": ["skip"]},
        "state_price_tie": {"bayes": ["repeat"], "state": ["skip", "repeat"]}}
    for obj, expected in expected_bundles[name].items():
        checks.require(optima[obj]["bundles"] == expected, (name, obj, "analytic bundle mismatch", optima[obj]["bundles"]))
    if name == "cheap_final_reference":
        for obj in ("bayes", "state"):
            r = optima[obj]["representative"]
            checks.close("direct_reference_utility", r["utility"], .74)
            checks.close("direct_reference_access", r["final_reference_rate"], 1.)
            checks.close("direct_reference_no_maintenance", r["maintenance_rate"], 0.)
    checks.require(sum(len(bundle["histories"])*40 for bundle in bundles) == 760, "incomplete history enumeration")
    return dict(name=name, parameters=f, K=K, Hbase=Hbase, bundles=bundles, global_optima=optima)


def verify():
    start, checks = perf_counter(), Checks()
    results = [verify_fixture(name, fixture, checks) for name, fixture in fixtures()]
    return dict(passed=True, fixtures=results, settings=len(results), local_choices=760*len(results),
                local_objective_scores=760*5*len(results), initial_bundle_scores=25*len(results),
                global_optimum_sets=5*len(results), audited_trajectories=25*len(results),
                terminal_score_columns=["maintenance", "final_reference", "report_code", "accuracy", "utility"]+list(OBJECTIVES),
                numeric_comparisons=checks.numeric, structural_checks=checks.structural,
                max_abs_errors=checks.errors, tolerance=TOL, elapsed_seconds=perf_counter()-start)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    mount = Path("/mnt/bioIce1")
    if not os.path.ismount(mount) or mount/"fep-ideas" not in output.parents:
        raise SystemExit("Require a new output directory on mounted /mnt/bioIce1/fep-ideas")
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__).resolve(), SPEC.resolve(), HELPER.resolve())
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size) for p in sources]
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=60)
    manifest, log_path = output/"MANIFEST.json", output/"RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs and reused frozen helper recorded before verification.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output/"RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['settings']} fixtures; {result['local_choices']} local choices; "
                         f"{result['local_objective_scores']} local scores; {result['initial_bundle_scores']} initial scores.\n"
                         f"Complete global optimum sets: {result['global_optimum_sets']}.\n"
                         f"Whole-trajectory audits: {result['audited_trajectories']}.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; exact finite dynamic programming; no simulation, fitting or random draws.\n")
        receipt["passed"] = True
    except BaseException:
        with log_path.open("a") as stream:
            stream.write(traceback.format_exc())
        for path, data in snapshots.items():
            (output/("FAILED_INPUT_"+path.name)).write_bytes(data)
        raise
    finally:
        receipt["outputs"] = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size)
                              for p in sorted(output.iterdir()) if p.is_file() and p != manifest]
        manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    print(log_path.read_text(), end="")
    print(f"Record: {output}")


if __name__ == "__main__":
    main()
