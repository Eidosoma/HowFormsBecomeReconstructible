"""Exact verification of FEP_INTERPRETATION_TRANSFER_V1.md; no sampling."""
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

from check_fep_reader_evidence import Checks, entropy, h, information, kl, marginal, report


SPEC = Path(__file__).with_name("FEP_INTERPRETATION_TRANSFER_V1.md")
HELPER = Path(__file__).with_name("check_fep_reader_evidence.py")
TOL, L = 1e-12, log(2)
BUNDLES = ("skip", "read", "anchor")
OBJECTIVES = ("bayes", "state", "full_extension", "task_extension", "regime_extension")
CHOICES = tuple((m, b, code) for m in (0, 1) for b in (0, 1)
                for code in range(1 << (2 ** (1+b))))


def fixtures():
    base = dict(p=.5, tau=.75, kappa0=.9, kappa1=.9, k=.005, d0=.02,
                c=.15, d1=.30, beta=8., v=1.)
    changes = (("uncertain_transfer", {}, .625), ("reset", dict(tau=0.), .6),
               ("stable", dict(tau=1.), .675), ("cheap_maintenance", dict(c=.025), .725),
               ("cheap_final_reference", dict(d1=.01), .89), ("erased_content", dict(p=0.), .6),
               ("chance_calibration", dict(kappa0=.5), .6), ("costly_calibration", dict(d0=.10), .6),
               ("intact_content", dict(p=1., c=.25), .775), ("transfer_price_tie", dict(tau=5/8), .6),
               ("weak_preferences", dict(beta=2.), .625))
    return [(name, dict(base, **change), value) for name, change, value in changes]


def prices(f):
    return (0., f["k"], f["k"]+f["d0"])


def physical(f):
    out = {}
    for w in product((0, 1), repeat=10):
        C, K, F0, F1, X0, R0, Z0, X1, R1, Z1 = w
        mass = (f["p"] if C else 1-f["p"])*(f["tau"] if K else 1-f["tau"])*.5
        mass *= float(F1 == F0) if K else .5
        mass *= .25*(float(R0 == X0 and R1 == X1) if C else .25)
        mass *= f["kappa0"] if Z0 == X0 else 1-f["kappa0"]
        mass *= f["kappa1"] if Z1 == X1 else 1-f["kappa1"]
        if mass:
            out[w] = mass
    return out


def history(w, a):
    return () if a == 0 else (w[5] ^ w[2],) if a == 1 else (w[5] ^ w[2], w[6])


def regime(w):
    return w[0], w[1], w[3]


def final_bits(w, m, b):
    y = w[8] ^ (w[3] if not m else 0)
    return (y, w[9]) if b else (y,)


def vfe_check(q, obs, checks):
    records = []
    for o, mass in marginal(q, obs).items():
        joint = {w: p for w, p in q.items() if obs(w) == o}
        posterior = {w: p/mass for w, p in joint.items()}
        exact = fsum(p*log(p/joint[w]) for w, p in posterior.items())
        checks.close("VFE_exact_posterior", exact, -log(mass))
        first = next(iter(posterior))
        tilted = {w: p*(2 if w == first else 1) for w, p in posterior.items()}
        norm = fsum(tilted.values())
        tilted = {w: p/norm for w, p in tilted.items()}
        perturbed = fsum(p*log(p/joint[w]) for w, p in tilted.items())
        gap = kl(tilted, posterior)
        checks.close("VFE_KL_identity", perturbed, -log(mass)+gap)
        checks.require(gap > 0 if len(posterior) > 1 else abs(gap) <= TOL, "VFE perturbation failed")
        records.append(dict(observation=o, probability=mass, exact_vfe=exact, perturbed_gap=gap))
    return records


def identification(q, f, checks):
    p, tau, r0, r1 = f["p"], f["tau"], 2*f["kappa0"]-1, 2*f["kappa1"]-1
    rows = []
    for a in range(3):
        obs = lambda w: history(w, a)
        checks.close("no_answer_in_calibration", information(q, lambda w: w[7], obs), 0.)
        checks.close("no_content_class_in_calibration", information(q, lambda w: w[0], obs), 0.)
        checks.close("no_transition_class_in_calibration", information(q, lambda w: w[1], obs), 0.)
        if a < 2:
            checks.close("unlabeled_read_no_regime_evidence", information(q, regime, obs), 0.)
        for hist, mass in marginal(q, obs).items():
            checks.close("uniform_calibration", mass, 2.**(-a))
            post = {w: v/mass for w, v in q.items() if obs(w) == hist}
            checks.close("content_prior_unchanged", fsum(v for w, v in post.items() if w[0]), p)
            checks.close("transition_prior_unchanged", fsum(v for w, v in post.items() if w[1]), tau)
            if a == 2:
                parity = hist[0] ^ hist[1]
                for C in (0, 1):
                    pc = p if C else 1-p
                    if pc:
                        actual = fsum(v for w, v in post.items() if w[0] == C and w[3] == parity)/pc
                        checks.close("orientation_posterior", actual, (1+tau*r0)/2 if C else .5)
        rows.append(dict(bundle=BUNDLES[a], vfe=vfe_check(q, obs, checks)))
    for m in (0, 1):
        obs = lambda w: history(w, 2)+final_bits(w, m, 1)
        for o, mass in marginal(q, obs).items():
            postK = fsum(v for w, v in q.items() if obs(w) == o and w[1])/mass
            postC = fsum(v for w, v in q.items() if obs(w) == o and w[0])/mass
            sign = 1-2*(o[0] ^ o[1] ^ o[2] ^ o[3])
            if not m:
                expected_mass = (1+p*tau*r0*r1*sign)/16
                expectedK = tau*(1+p*r0*r1*sign)/(1+p*tau*r0*r1*sign)
                expectedC = p*(1+tau*r0*r1*sign)/(1+p*tau*r0*r1*sign)
            else:
                last_sign = 1-2*(o[2] ^ o[3])
                expected_mass = (1+p*r1*last_sign)/16
                expectedK = tau
                expectedC = p*(1+r1*last_sign)/(1+p*r1*last_sign)
            checks.close("four_bit_observation_law", mass, expected_mass)
            checks.close("transition_posterior", postK, expectedK)
            checks.close("content_posterior", postC, expectedC)
        rows.append(dict(maintenance=m, final_anchor_vfe=vfe_check(q, obs, checks),
                         transition_information=information(q, lambda w: w[1], obs)))
        if m:
            checks.close("maintenance_removes_transition_evidence", information(q, lambda w: w[1], obs), 0.)
    laws = [marginal(physical(dict(f, tau=t)), lambda w: history(w, 2)+final_bits(w, 0, 1)) for t in (0., 1.)]
    tv = .5*fsum(abs(laws[0].get(o, 0.)-laws[1].get(o, 0.)) for o in laws[0].keys() | laws[1].keys())
    checks.close("stable_reset_total_variation", tv, p*r0*r1/2)
    return dict(records=rows, stable_reset_total_variation=tv)


def terminal(q, f, a, checks):
    rows, optima, predicted = [], {}, {obj: [] for obj in OBJECTIVES}
    for m, b in product((0, 1), repeat=2):
        obs = lambda w: final_bits(w, m, b)
        qo = marginal(q, obs)
        info = (entropy(qo), information(q, lambda w: w[7], obs), information(q, regime, obs))
        A = (1+f["p"])/2 if m else ((1+f["p"]*f["tau"]*(2*f["kappa0"]-1))/2 if a == 2 else .5)
        expected_accuracy = max(A, f["kappa1"]) if b else A
        decisions, actual_accuracy = [], 0.
        for o in product((0, 1), repeat=1+b):
            weights = [fsum(p for w, p in q.items() if obs(w) == o and w[7] == x) for x in (0, 1)]
            actual_accuracy += max(weights)
            decisions.append([x for x in (0, 1) if max(weights)-weights[x] <= TOL])
        checks.close("best_report_accuracy", actual_accuracy, expected_accuracy)
        codes = {sum(bit << i for i, bit in enumerate(bits)) for bits in product(*decisions)}
        bestU = f["v"]*expected_accuracy-f["c"]*m-f["d1"]*b
        bestscores = (-bestU, -f["beta"]*bestU, *(-f["beta"]*bestU-i for i in info))
        for obj, score in zip(OBJECTIVES, bestscores):
            predicted[obj].append((score, {(m, b, code) for code in codes}))
        for code in range(1 << (2 ** (1+b))):
            accuracy = fsum(p for w, p in q.items() if report(code, obs(w)) == w[7])
            U = f["v"]*accuracy-f["c"]*m-f["d1"]*b
            scores = dict(zip(OBJECTIVES, (-U, -f["beta"]*U, *(-f["beta"]*U-i for i in info))))
            rows.append(dict(choice=(m, b, code), accuracy=accuracy, utility=U, scores=scores))
            if not f["p"] and not b:
                checks.close("erased_record_chance", accuracy, .5)
    checks.require(tuple(row["choice"] for row in rows) == CHOICES, "incomplete terminal menu")
    for obj in OBJECTIVES:
        minimum = min(row["scores"][obj] for row in rows)
        opts = [row for row in rows if row["scores"][obj]-minimum <= TOL]
        best = min(score for score, codes in predicted[obj])
        expected = set().union(*(codes for score, codes in predicted[obj] if score-best <= TOL))
        checks.close("local_optimal_score", minimum, best)
        checks.require({row["choice"] for row in opts} == expected, "incomplete local optimum set")
        optima[obj] = dict(score=minimum, choices=[row["choice"] for row in opts],
                           utility_range=[min(r["utility"] for r in opts), max(r["utility"] for r in opts)],
                           representative_utility=opts[0]["utility"])
    checks.require(optima["state"]["choices"] == optima["bayes"]["choices"], "state/Bayesian branch mismatch")
    return rows, optima


def trajectory(qw, a, policy):
    q = {}
    for w, p in qw.items():
        m, b, code = policy[history(w, a)]
        bits = final_bits(w, m, b)
        q[w+(w[5] ^ w[2], bits[0], a, m, b, report(code, bits))] = p
    return q


def observed(s):
    a, m, b, D = s[12:]
    hist = () if a == 0 else (s[10],) if a == 1 else (s[10], s[6])
    bits = (s[11], s[9]) if b else (s[11],)
    return a, hist, m, b, bits, D


def preferred_observation(o, f):
    a, hist, m, b, bits, D = o
    normalizer = fsum(exp(-f["beta"]*cost) for cost in prices(f))
    normalizer *= (1+exp(-f["beta"]*f["c"]))*(1+exp(-f["beta"]*f["d1"]))
    return exp(-f["beta"]*(prices(f)[a]+f["c"]*m+f["d1"]*b))/normalizer/2**(len(hist)+len(bits)+1)


def audit(q, f, a, K0, HW, checks):
    qo = marginal(q, observed)
    accuracy = fsum(p for s, p in q.items() if s[15] == s[7])
    mr = fsum(p for s, p in q.items() if s[13])
    br = fsum(p for s, p in q.items() if s[14])
    U = f["v"]*accuracy-prices(f)[a]-f["c"]*mr-f["d1"]*br
    cs = {s: exp(f["beta"]*(f["v"]*(s[15] == s[7])-prices(f)[a]-f["c"]*s[13]-f["d1"]*s[14])-K0) for s in q}
    co = {o: preferred_observation(o, f) for o in qo}
    state = kl(q, cs)
    conditional = fsum(p*log((p/qo[observed(s)])/(cs[s]/co[observed(s)])) for s, p in q.items())
    checks.close("trajectory_normalization", fsum(q.values()), 1.)
    checks.close("policy_invariant_state_entropy", entropy(q), HW)
    checks.close("state_score_identity", state, K0-f["beta"]*U-HW)
    checks.close("conditional_KL_decomposition", state, kl(qo, co)+conditional)
    checks.require(conditional >= -TOL, "negative conditional KL")
    info = dict(full=information(q, lambda s: s, observed), task=information(q, lambda s: s[7], observed),
                regime=information(q, regime, observed))
    checks.close("full_information_entropy", info["full"], entropy(qo))
    checks.close("retained_content_invariance", fsum(p for s, p in q.items() if s[8] == s[7]), (1+f["p"])/2)
    scores = dict(bayes=-U, state=state, **{key+"_extension": K0-f["beta"]*U-value for key, value in info.items()})
    return dict(utility=U, accuracy=accuracy, calibration_cost=prices(f)[a], maintenance_rate=mr,
                final_reference_rate=br, information=info, physical_entropy=entropy(q),
                conditional_KL=conditional, scores=scores)


def verify_fixture(name, f, expected_U, checks):
    q = physical(f)
    checks.close("physical_normalization", fsum(q.values()), 1.)
    HW = h(f["p"])+h(f["tau"])+(6-f["tau"]-2*f["p"])*L+h(f["kappa0"])+h(f["kappa1"])
    checks.close("physical_entropy_formula", entropy(q), HW)
    z = 4096*(1+exp(f["beta"]*f["v"]))*fsum(exp(-f["beta"]*cost) for cost in prices(f))
    z *= (1+exp(-f["beta"]*f["c"]))*(1+exp(-f["beta"]*f["d1"]))
    K0 = log(z)
    mass = fsum(2048*exp(f["beta"]*(f["v"]*(D == x)-prices(f)[a]-f["c"]*m-f["d1"]*b))/z
                for x, D, m, b in product((0, 1), repeat=4) for a in range(3))
    checks.close("preferred_state_normalization", mass, 1.)
    preferred_obs = {}
    for a, m, b, D in product(range(3), (0, 1), (0, 1), (0, 1)):
        for hist in product((0, 1), repeat=a):
            for bits in product((0, 1), repeat=1+b):
                o = (a, hist, m, b, bits, D)
                preferred_obs[o] = preferred_observation(o, f)
                summed = 2**(11-a-len(bits))*(1+exp(f["beta"]*f["v"]))
                summed *= exp(-f["beta"]*(prices(f)[a]+f["c"]*m+f["d1"]*b))/z
                checks.close("preferred_observation_marginal", preferred_obs[o], summed)
    checks.close("preferred_observation_normalization", fsum(preferred_obs.values()), 1.)
    identified = identification(q, f, checks)
    bundles = []
    for a, label in enumerate(BUNDLES):
        ph = marginal(q, lambda w: history(w, a))
        prefixI = information(q, regime, lambda w: history(w, a))
        histories = []
        for hist, mass in sorted(ph.items()):
            post = {w: p/mass for w, p in q.items() if history(w, a) == hist}
            rows, opts = terminal(post, f, a, checks)
            histories.append(dict(history=hist, probability=mass, optima=opts,
                                  terminal_scores=[list(r["choice"])+[r["accuracy"], r["utility"]]+[r["scores"][o] for o in OBJECTIVES] for r in rows]))
        bundle = dict(bundle=label, prefix_entropy=entropy(ph), prefix_regime_information=prefixI, histories=histories, objectives={})
        for obj in OBJECTIVES:
            offset = prices(f)[a] if obj == "bayes" else f["beta"]*prices(f)[a]
            if obj == "full_extension":
                offset -= entropy(ph)
            elif obj == "regime_extension":
                offset -= prefixI
            score = offset+fsum(row["probability"]*row["optima"][obj]["score"] for row in histories)
            policy = {row["history"]: row["optima"][obj]["choices"][0] for row in histories}
            direct = audit(trajectory(q, a, policy), f, a, K0, HW, checks)
            expected_score = score if obj == "bayes" else score+K0-(HW if obj == "state" else 0.)
            checks.close("dynamic_whole_trajectory_agreement", direct["scores"][obj], expected_score)
            urange = [fsum(row["probability"]*row["optima"][obj]["utility_range"][side] for row in histories)-prices(f)[a] for side in (0, 1)]
            expected_value = fsum(row["probability"]*row["optima"][obj]["representative_utility"] for row in histories)-prices(f)[a]
            checks.close("representative_utility", direct["utility"], expected_value)
            for side in (0, 1):
                attained = 0.
                for row in histories:
                    allowed = set(row["optima"][obj]["choices"])
                    utilities = [r[4] for r in row["terminal_scores"] if tuple(r[:3]) in allowed]
                    attained += row["probability"]*(min(utilities) if side == 0 else max(utilities))
                checks.close("attainable_tie_utility", attained-prices(f)[a], urange[side])
            bundle["objectives"][obj] = dict(reduced_score=score, utility_range=urange,
                                               policy_count=prod(len(r["optima"][obj]["choices"]) for r in histories),
                                               representative_policy=[dict(history=hist, choice=choice) for hist, choice in sorted(policy.items())],
                                               representative=direct)
        bundles.append(bundle)
    optima = {}
    for obj in OBJECTIVES:
        minimum = min(b["objectives"][obj]["reduced_score"] for b in bundles)
        selected = [b for b in bundles if b["objectives"][obj]["reduced_score"]-minimum <= TOL]
        optima[obj] = dict(reduced_score=minimum, bundles=[b["bundle"] for b in selected],
                           policy_count=sum(b["objectives"][obj]["policy_count"] for b in selected),
                           utility_range=[min(b["objectives"][obj]["utility_range"][0] for b in selected),
                                          max(b["objectives"][obj]["utility_range"][1] for b in selected)],
                           representative=selected[0]["objectives"][obj]["representative"])
    for key in ("bundles", "policy_count", "utility_range"):
        checks.require(optima["state"][key] == optima["bayes"][key], "global state/Bayesian mismatch")
    analytic_value = max(.5, (1+f["p"])/2-f["c"], f["kappa1"]-f["d1"],
                         (1+f["p"]*f["tau"]*(2*f["kappa0"]-1))/2-f["k"]-f["d0"])
    checks.close("analytic_Bayesian_value", -optima["bayes"]["reduced_score"], analytic_value)
    checks.close("prospective_Bayesian_value", analytic_value, expected_U)
    if name == "uncertain_transfer":
        checks.require(optima["bayes"]["bundles"] == ["anchor"] and optima["bayes"]["policy_count"] == 1, "main policy not unique")
        for row in bundles[2]["histories"]:
            parity = row["history"][0] ^ row["history"][1]
            checks.require(row["optima"]["bayes"]["choices"] == [(0, 0, 1 if parity else 2)], "main interpretation prediction")
    if name == "transfer_price_tie":
        checks.require(optima["bayes"]["bundles"] == ["skip", "anchor"] and optima["bayes"]["policy_count"] == 3, "missing boundary ties")
    checks.require(sum(len(b["histories"])*40 for b in bundles) == 280, "incomplete enumeration")
    return dict(name=name, parameters=f, K0=K0, physical_entropy=HW, identification=identified,
                bundles=bundles, global_optima=optima)


def verify():
    start, checks = perf_counter(), Checks()
    results = [verify_fixture(name, f, expected, checks) for name, f, expected in fixtures()]
    return dict(passed=True, fixtures=results, settings=len(results), local_choices=280*len(results),
                local_objective_scores=1400*len(results), initial_bundle_scores=15*len(results),
                global_optimum_sets=5*len(results), audited_trajectories=15*len(results),
                deterministic_policies_per_fixture=2561640,
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
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs frozen before exact verification; no fitting or sampling.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output/"RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['settings']} fixtures; {result['local_choices']} local choices; {result['local_objective_scores']} local scores.\n"
                         f"Complete optimum sets: {result['global_optimum_sets']}; whole-trajectory audits: {result['audited_trajectories']}.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; exact inference and contingent policies; no parameter tuning.\n")
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
