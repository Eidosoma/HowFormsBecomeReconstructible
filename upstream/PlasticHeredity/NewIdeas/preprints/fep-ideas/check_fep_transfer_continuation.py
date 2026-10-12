"""Exact three-record check of FEP_TRANSFER_CONTINUATION_V1.md."""
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


SPEC = Path(__file__).with_name("FEP_TRANSFER_CONTINUATION_V1.md")
HELPER = Path(__file__).with_name("check_fep_reader_evidence.py")
TOL, L = 1e-12, log(2)
BUNDLES = ("skip", "read", "anchor")
OBJECTIVES = ("bayes", "state", "full_extension", "task_extension", "regime_extension")
CHOICES = tuple((m, b, code) for m in (0, 1) for b in (0, 1)
                for code in range(1 << (2 ** (1+b))))


def fixtures():
    base = dict(p=.5, tau=.75, kappa0=.9, kappa1=.9, kappa2=.9, k=.005,
                d0=.02, d1=.02, c=.15, d2=.30, beta=8., v=1.)
    changes = (("continuation", {}, .638), ("reset", dict(tau=0.), .6),
               ("stable", dict(tau=1.), .684),
               ("transfer_isolated", dict(p=1., kappa0=1., kappa1=1.), .86875),
               ("erased_content", dict(p=0.), .6),
               ("chance_calibration", dict(kappa0=.5, kappa1=.5), .6),
               ("cheap_final_reference", dict(d2=.01), .89),
               ("cheap_maintenance", dict(c=.025), .725),
               ("costly_recheck", dict(d1=.05), .625),
               ("recheck_price_tie", dict(d1=.033), .625),
               ("weak_preferences", dict(beta=2.), .638),
               ("no_future_reward", dict(v=0.), 0.))
    return [(name, dict(base, **change), expected) for name, change, expected in changes]


def prices(f, i):
    return (0., f["k"], f["k"]+f[f"d{i}"])


def calibration(f):
    q = {}
    for w in product((0, 1), repeat=11):
        C, K, F0, F1, F2, X0, R0, Z0, X1, R1, Z1 = w
        mass = (f["p"] if C else 1-f["p"])*(f["tau"] if K else 1-f["tau"])*.5
        mass *= float(F1 == F0 and F2 == F0) if K else .25
        mass *= .25*(float(R0 == X0 and R1 == X1) if C else .25)
        mass *= f["kappa0"] if Z0 == X0 else 1-f["kappa0"]
        mass *= f["kappa1"] if Z1 == X1 else 1-f["kappa1"]
        if mass:
            q[w] = mass
    return q


def hist(w, i, a):
    y, z = (w[6] ^ w[2], w[7]) if i == 0 else (w[9] ^ w[3], w[10])
    return () if a == 0 else (y,) if a == 1 else (y, z)


def regime(w):
    return w[0], w[1], w[4]


def future(qH, f):
    q = {}
    for (C, K, F), ph in qH.items():
        for X, R, Z in product((0, 1), repeat=3):
            mass = ph*.5*(float(R == X) if C else .5)
            mass *= f["kappa2"] if Z == X else 1-f["kappa2"]
            if mass:
                q[C, K, F, X, R, Z] = mass
    return q


def final_bits(w, m, b):
    y = w[4] ^ (w[2] if not m else 0)
    return (y, w[5]) if b else (y,)


def vfe_check(q, obs, checks):
    rows = []
    for o, mass in marginal(q, obs).items():
        joint = {w: p for w, p in q.items() if obs(w) == o}
        post = {w: p/mass for w, p in joint.items()}
        exact = fsum(p*log(p/joint[w]) for w, p in post.items())
        checks.close("VFE_exact", exact, -log(mass))
        first = next(iter(post))
        tilt = {w: p*(2 if w == first else 1) for w, p in post.items()}
        norm = fsum(tilt.values())
        tilt = {w: p/norm for w, p in tilt.items()}
        gap = kl(tilt, post)
        value = fsum(p*log(p/joint[w]) for w, p in tilt.items())
        checks.close("VFE_perturbed_identity", value, -log(mass)+gap)
        checks.require(gap > 0 if len(post) > 1 else abs(gap) <= TOL, "VFE perturbation")
        rows.append(dict(history=o, probability=mass, exact_vfe=exact, perturbed_gap=gap))
    return rows


def analytic_posterior(f, anchors):
    p, tau = f["p"], f["tau"]
    signs = [(2*f[f"kappa{i}"]-1, sign) for i, sign in anchors]
    if not signs:
        return p, tau, 0.
    if len(signs) == 1:
        r, sign = signs[0]
        return p, tau, p*tau*r*sign
    (r0, s0), (r1, s1) = signs
    t = r0*r1*s0*s1
    denominator = 1+p*tau*t
    return p*(1+tau*t)/denominator, tau*(1+p*t)/denominator, p*tau*(r0*s0+r1*s1)/denominator


def check_posterior(qH, f, anchors, checks):
    pC, pK, t = analytic_posterior(f, anchors)
    checks.close("posterior_C", fsum(p for H, p in qH.items() if H[0]), pC)
    checks.close("posterior_K", fsum(p for H, p in qH.items() if H[1]), pK)
    checks.close("posterior_oriented_content", fsum(p*H[0]*(1-2*H[2]) for H, p in qH.items()), t)
    expected = {}
    for C, K, F in product((0, 1), repeat=3):
        mass = (f["p"] if C else 1-f["p"])*(f["tau"] if K else 1-f["tau"])*.5
        if C and K:
            for i, sign in anchors:
                mass *= 1+(2*f[f"kappa{i}"]-1)*sign*(1-2*F)
        expected[C, K, F] = mass
    norm = fsum(expected.values())
    for H, p in expected.items():
        checks.close("joint_regime_posterior", qH.get(H, 0.), p/norm)
    return dict(content=pC, transfer=pK, oriented_content=t)


def terminal(qH, f, checks):
    q = future(qH, f)
    checks.close("terminal_physical_normalization", fsum(q.values()), 1.)
    pC = fsum(p for H, p in qH.items() if H[0])
    t = fsum(p*H[0]*(1-2*H[2]) for H, p in qH.items())
    rows, optima, predictions = [], {}, {o: [] for o in OBJECTIVES}
    for m, b in product((0, 1), repeat=2):
        obs = lambda w: final_bits(w, m, b)
        info = (entropy(marginal(q, obs)), information(q, lambda w: w[3], obs),
                information(q, lambda w: w[:3], obs))
        A = (1+pC)/2 if m else (1+abs(t))/2
        expected_accuracy = max(A, f["kappa2"]) if b else A
        good_bits, best_accuracy = [], 0.
        for o in product((0, 1), repeat=1+b):
            weights = [fsum(p for w, p in q.items() if obs(w) == o and w[3] == x) for x in (0, 1)]
            best_accuracy += max(weights)
            good_bits.append([x for x in (0, 1) if max(weights)-weights[x] <= TOL])
        checks.close("best_report_accuracy", best_accuracy, expected_accuracy)
        codes = {sum(bit << i for i, bit in enumerate(bits)) for bits in product(*good_bits)}
        if not f["v"]:
            codes = set(range(1 << (2 ** (1+b))))
        bestU = f["v"]*expected_accuracy-f["c"]*m-f["d2"]*b
        bestscores = (-bestU, -f["beta"]*bestU, *(-f["beta"]*bestU-I for I in info))
        for obj, score in zip(OBJECTIVES, bestscores):
            predictions[obj].append((score, {(m, b, code) for code in codes}))
        for code in range(1 << (2 ** (1+b))):
            accuracy = fsum(p for w, p in q.items() if report(code, obs(w)) == w[3])
            U = f["v"]*accuracy-f["c"]*m-f["d2"]*b
            scores = dict(zip(OBJECTIVES, (-U, -f["beta"]*U, *(-f["beta"]*U-I for I in info))))
            rows.append(dict(choice=(m, b, code), accuracy=accuracy, utility=U, scores=scores))
            if not f["p"] and not b:
                checks.close("erased_record_bound", accuracy, .5)
    checks.require(tuple(r["choice"] for r in rows) == CHOICES, "incomplete terminal menu")
    for obj in OBJECTIVES:
        minimum = min(r["scores"][obj] for r in rows)
        selected = [r for r in rows if r["scores"][obj]-minimum <= TOL]
        best = min(score for score, choices in predictions[obj])
        expected = set().union(*(choices for score, choices in predictions[obj] if score-best <= TOL))
        checks.close("local_optimum_score", minimum, best)
        checks.require({r["choice"] for r in selected} == expected, "incomplete terminal optima")
        optima[obj] = dict(score=minimum, choices=[r["choice"] for r in selected],
                           policy_count=len(selected), representative_utility=selected[0]["utility"],
                           utility_range=[min(r["utility"] for r in selected), max(r["utility"] for r in selected)])
    checks.require(optima["bayes"]["choices"] == optima["state"]["choices"], "terminal state/Bayesian mismatch")
    return rows, optima


def prefixes(q, i, a, f):
    obs = lambda w: hist(w, i, a)
    return marginal(q, obs), entropy(marginal(q, obs)), information(q, regime, obs)


def combine(histories, a, i, prefixH, prefixI, f, checks):
    # Rows contain child optima; each selected history can choose independently.
    out = {}
    for obj in OBJECTIVES:
        offset = prices(f, i)[a]*(1 if obj == "bayes" else f["beta"])
        if obj == "full_extension":
            offset -= prefixH
        elif obj == "regime_extension":
            offset -= prefixI
        score = offset+fsum(row["probability"]*row["optima"][obj]["score"] for row in histories)
        urange = [fsum(row["probability"]*row["optima"][obj]["utility_range"][side] for row in histories)-prices(f, i)[a] for side in (0, 1)]
        representative_U = fsum(row["probability"]*row["optima"][obj]["representative_utility"] for row in histories)-prices(f, i)[a]
        out[obj] = dict(score=score, utility_range=urange, representative_utility=representative_U,
                        policy_count=prod(row["optima"][obj]["policy_count"] for row in histories))
        checks.require(urange[0]-TOL <= representative_U <= urange[1]+TOL, "representative outside tie range")
    return out


def select(bundles, checks):
    out = {}
    for obj in OBJECTIVES:
        minimum = min(b["objectives"][obj]["score"] for b in bundles)
        selected = [b for b in bundles if b["objectives"][obj]["score"]-minimum <= TOL]
        out[obj] = dict(score=minimum, bundles=[b["bundle"] for b in selected],
                        policy_count=sum(b["objectives"][obj]["policy_count"] for b in selected),
                        representative_utility=selected[0]["objectives"][obj]["representative_utility"],
                        utility_range=[min(b["objectives"][obj]["utility_range"][0] for b in selected),
                                       max(b["objectives"][obj]["utility_range"][1] for b in selected)])
    for key in ("bundles", "policy_count", "utility_range"):
        checks.require(out["state"][key] == out["bayes"][key], "state/Bayesian branch or range mismatch")
    return out


def second_stage(q0, h0, a0, f, checks):
    bundles = []
    anchors0 = [(0, 1-2*(h0[0] ^ h0[1]))] if a0 == 2 else []
    for a1, label in enumerate(BUNDLES):
        ph1, prefixH, prefixI = prefixes(q0, 1, a1, f)
        vfe = vfe_check(q0, lambda w: hist(w, 1, a1), checks)
        histories = []
        for h1, mass in sorted(ph1.items()):
            post = {w: p/mass for w, p in q0.items() if hist(w, 1, a1) == h1}
            qH = marginal(post, regime)
            anchors = anchors0+([(1, 1-2*(h1[0] ^ h1[1]))] if a1 == 2 else [])
            posterior = check_posterior(qH, f, anchors, checks)
            if a0 == a1 == 2:
                sign = (1-2*(h0[0] ^ h0[1]))*(1-2*(h1[0] ^ h1[1]))
                expected = (1+f["p"]*f["tau"]*(2*f["kappa0"]-1)*(2*f["kappa1"]-1)*sign)/4
                checks.close("second_anchor_conditional_law", mass, expected)
            rows, opts = terminal(qH, f, checks)
            for obj in OBJECTIVES:
                selected = [r for r in rows if r["choice"] in opts[obj]["choices"]]
                for side in (0, 1):
                    attained = (min if side == 0 else max)(r["utility"] for r in selected)
                    checks.close("terminal_tie_endpoint", attained, opts[obj]["utility_range"][side])
            histories.append(dict(history=h1, probability=mass, posterior=posterior, optima=opts,
                                  terminal_scores=[list(r["choice"])+[r["accuracy"], r["utility"]]+[r["scores"][obj] for obj in OBJECTIVES] for r in rows]))
        bundles.append(dict(bundle=label, prefix_entropy=prefixH, prefix_regime_information=prefixI,
                            vfe=vfe, histories=histories,
                            objectives=combine(histories, a1, 1, prefixH, prefixI, f, checks)))
    return bundles, select(bundles, checks)


def choose_policy(bundle, obj, side=None):
    policy = {}
    for row0 in bundle["histories"]:
        allowed = row0["optima"][obj]["bundles"]
        candidates = [b for b in row0["second_bundles"] if b["bundle"] in allowed]
        if side is None:
            chosen = candidates[0]
        else:
            chosen = (min if side == 0 else max)(candidates, key=lambda b: b["objectives"][obj]["utility_range"][side])
        terminal_policy = {}
        for row1 in chosen["histories"]:
            choices = row1["optima"][obj]["choices"]
            if side is None:
                choice = choices[0]
            else:
                allowed_rows = [r for r in row1["terminal_scores"] if tuple(r[:3]) in choices]
                choice = tuple((min if side == 0 else max)(allowed_rows, key=lambda r: r[4])[:3])
            terminal_policy[row1["history"]] = choice
        policy[row0["history"]] = (BUNDLES.index(chosen["bundle"]), terminal_policy)
    return policy


def policy_value(q, a0, policy, f):
    # Independent expected-utility calculation for attainable tie endpoints.
    total = 0.
    for w, p in q.items():
        a1, terminal_policy = policy[hist(w, 0, a0)]
        m, b, code = terminal_policy[hist(w, 1, a1)]
        conditional = 0.
        for X, R, Z in product((0, 1), repeat=3):
            mass = .5*(float(R == X) if w[0] else .5)*(f["kappa2"] if Z == X else 1-f["kappa2"])
            bits = (R ^ (w[4] if not m else 0), Z) if b else (R ^ (w[4] if not m else 0),)
            conditional += mass*f["v"]*(report(code, bits) == X)
        total += p*(conditional-prices(f, 0)[a0]-prices(f, 1)[a1]-f["c"]*m-f["d2"]*b)
    return total


def trajectory(qcal, a0, policy, f):
    q = {}
    for w, p in qcal.items():
        a1, terminal_policy = policy[hist(w, 0, a0)]
        m, b, code = terminal_policy[hist(w, 1, a1)]
        for X, R, Z in product((0, 1), repeat=3):
            mass = p*.5*(float(R == X) if w[0] else .5)*(f["kappa2"] if Z == X else 1-f["kappa2"])
            if mass:
                y2 = R ^ (w[4] if not m else 0)
                bits = (y2, Z) if b else (y2,)
                q[w+(X, R, Z, w[6] ^ w[2], w[9] ^ w[3], y2, a0, a1, m, b, report(code, bits))] = mass
    return q


def observed(s):
    a0, a1, m, b, D = s[17:]
    h0 = () if a0 == 0 else (s[14],) if a0 == 1 else (s[14], s[7])
    h1 = () if a1 == 0 else (s[15],) if a1 == 1 else (s[15], s[10])
    bits = (s[16], s[13]) if b else (s[16],)
    return a0, h0, a1, h1, m, b, bits, D


def preferred_observation(o, f):
    a0, h0, a1, h1, m, b, bits, D = o
    costs = prices(f, 0)[a0]+prices(f, 1)[a1]+f["c"]*m+f["d2"]*b
    norm = prod(fsum(exp(-f["beta"]*cost) for cost in prices(f, i)) for i in (0, 1))
    norm *= (1+exp(-f["beta"]*f["c"]))*(1+exp(-f["beta"]*f["d2"]))
    return exp(-f["beta"]*costs)/norm/2**(len(h0)+len(h1)+len(bits)+1)


def audit(q, f, K0, HW, checks):
    qo = marginal(q, observed)
    accuracy = fsum(p for s, p in q.items() if s[21] == s[11])
    mr = fsum(p for s, p in q.items() if s[19])
    br = fsum(p for s, p in q.items() if s[20])
    cal_cost = fsum(p*(prices(f, 0)[s[17]]+prices(f, 1)[s[18]]) for s, p in q.items())
    U = f["v"]*accuracy-cal_cost-f["c"]*mr-f["d2"]*br
    cs = {s: exp(f["beta"]*(f["v"]*(s[21] == s[11])-prices(f, 0)[s[17]]-prices(f, 1)[s[18]]-f["c"]*s[19]-f["d2"]*s[20])-K0) for s in q}
    co = {o: preferred_observation(o, f) for o in qo}
    state = kl(q, cs)
    conditional = fsum(p*log((p/qo[observed(s)])/(cs[s]/co[observed(s)])) for s, p in q.items())
    checks.close("trajectory_normalization", fsum(q.values()), 1.)
    checks.close("constant_physical_entropy", entropy(q), HW)
    checks.close("state_score_identity", state, K0-f["beta"]*U-HW)
    checks.close("state_outcome_conditional_KL", state, kl(qo, co)+conditional)
    checks.require(conditional >= -TOL, "negative conditional KL")
    info = dict(full=information(q, lambda s: s, observed), task=information(q, lambda s: s[11], observed),
                regime=information(q, regime, observed))
    checks.close("full_information_entropy", info["full"], entropy(qo))
    checks.close("no_answer_in_calibration", information(q, lambda s: s[11], lambda s: observed(s)[:4]), 0.)
    checks.close("content_causal_invariance", fsum(p for s, p in q.items() if s[11] == s[12]), (1+f["p"])/2)
    scores = dict(bayes=-U, state=state, **{target+"_extension": K0-f["beta"]*U-I for target, I in info.items()})
    return dict(utility=U, accuracy=accuracy, calibration_cost=cal_cost, maintenance_rate=mr,
                final_reference_rate=br, second_anchor_rate=fsum(p for s, p in q.items() if s[18] == 2),
                information=info, physical_entropy=entropy(q), conditional_KL=conditional, scores=scores)


def parity_cases(f, subset):
    for signs in product((-1, 1), repeat=len(subset)):
        anchors = list(zip(subset, signs))
        probability = 2.**(-len(subset))
        if len(subset) == 2:
            probability *= 1+f["p"]*f["tau"]*(2*f["kappa0"]-1)*(2*f["kappa1"]-1)*signs[0]*signs[1]
        if probability:
            pC, pK, t = analytic_posterior(f, anchors)
            yield probability, (1+abs(t))/2, (1+pC)/2


def analytic_controls(f, bundle0, checks):
    subsets = []
    for subset in ((), (0,), (1,), (0, 1)):
        cost = fsum(prices(f, i)[2] for i in subset)
        value = fsum(prob*max(f["v"]*A, f["v"]*M-f["c"], f["v"]*f["kappa2"]-f["d2"])
                     for prob, A, M in parity_cases(f, subset))-cost
        subsets.append(dict(anchors=subset, utility=value))
    committed = []
    for m, b in product((0, 1), repeat=2):
        analytic_accuracy = fsum(prob*(max(M if m else A, f["kappa2"]) if b else (M if m else A))
                                 for prob, A, M in parity_cases(f, (0, 1)))
        analytic_U = f["v"]*analytic_accuracy-prices(f, 0)[2]-prices(f, 1)[2]-f["c"]*m-f["d2"]*b
        enum_U = 0.
        for row0 in bundle0["histories"]:
            second = row0["second_bundles"][2]
            conditional = 0.
            for row1 in second["histories"]:
                candidate_U = [r[4] for r in row1["terminal_scores"] if r[0] == m and r[1] == b]
                conditional += row1["probability"]*max(candidate_U)
            enum_U += row0["probability"]*(conditional-prices(f, 1)[2])
        enum_U -= prices(f, 0)[2]
        checks.close("committed_action_control", enum_U, analytic_U)
        committed.append(dict(maintenance=m, final_reference=b, accuracy=analytic_accuracy, utility=analytic_U))
    return dict(anchor_subsets=subsets, committed_actions=committed,
                best_committed_both=max(row["utility"] for row in committed),
                best_at_most_one=max(row["utility"] for row in subsets if len(row["anchors"]) <= 1))


def verify_fixture(name, f, expected_U, checks):
    q = calibration(f)
    checks.close("calibration_normalization", fsum(q.values()), 1.)
    HW = h(f["p"])+h(f["tau"])+(9-2*f["tau"]-3*f["p"])*L+fsum(h(f[f"kappa{i}"]) for i in range(3))
    checks.close("physical_entropy_formula", entropy(q)+(2-f["p"])*L+h(f["kappa2"]), HW)
    z = 131072*(1+exp(f["beta"]*f["v"]))*prod(fsum(exp(-f["beta"]*c) for c in prices(f, i)) for i in (0, 1))
    z *= (1+exp(-f["beta"]*f["c"]))*(1+exp(-f["beta"]*f["d2"]))
    K0 = log(z)
    state_mass = fsum(65536*exp(f["beta"]*(f["v"]*(D == x)-prices(f, 0)[a0]-prices(f, 1)[a1]-f["c"]*m-f["d2"]*b))/z
                      for x, D, m, b in product((0, 1), repeat=4) for a0, a1 in product(range(3), repeat=2))
    checks.close("preferred_state_normalization", state_mass, 1.)
    co = {}
    for a0, a1, m, b, D in product(range(3), range(3), (0, 1), (0, 1), (0, 1)):
        for h0 in product((0, 1), repeat=a0):
            for h1 in product((0, 1), repeat=a1):
                for bits in product((0, 1), repeat=1+b):
                    o = (a0, h0, a1, h1, m, b, bits, D)
                    co[o] = preferred_observation(o, f)
                    summed = 2**(16-a0-a1-len(bits))*(1+exp(f["beta"]*f["v"]))
                    summed *= exp(-f["beta"]*(prices(f, 0)[a0]+prices(f, 1)[a1]+f["c"]*m+f["d2"]*b))/z
                    checks.close("preferred_observation_marginal", co[o], summed)
    checks.close("preferred_observation_normalization", fsum(co.values()), 1.)
    bundles = []
    for a0, label in enumerate(BUNDLES):
        ph0, prefixH, prefixI = prefixes(q, 0, a0, f)
        vfe = vfe_check(q, lambda w: hist(w, 0, a0), checks)
        histories = []
        for h0, mass in sorted(ph0.items()):
            checks.close("uniform_first_history", mass, 2.**(-a0))
            post = {w: p/mass for w, p in q.items() if hist(w, 0, a0) == h0}
            second_bundles, optima = second_stage(post, h0, a0, f, checks)
            histories.append(dict(history=h0, probability=mass, second_bundles=second_bundles, optima=optima))
        bundle = dict(bundle=label, prefix_entropy=prefixH, prefix_regime_information=prefixI,
                      vfe=vfe, histories=histories,
                      objectives=combine(histories, a0, 0, prefixH, prefixI, f, checks))
        for obj in OBJECTIVES:
            policy = choose_policy(bundle, obj)
            direct = audit(trajectory(q, a0, policy, f), f, K0, HW, checks)
            entry = bundle["objectives"][obj]
            expected_score = entry["score"] if obj == "bayes" else K0+entry["score"]-(HW if obj == "state" else 0.)
            checks.close("dynamic_vs_whole_trajectory", direct["scores"][obj], expected_score)
            checks.close("representative_utility", direct["utility"], entry["representative_utility"])
            for side in (0, 1):
                checks.close("attainable_global_tie_endpoint", policy_value(q, a0, choose_policy(bundle, obj, side), f), entry["utility_range"][side])
            entry["representative"] = direct
            entry["representative_policy"] = [dict(first_history=h0, second_bundle=BUNDLES[a1],
                                                    terminal=[dict(second_history=h1, choice=choice) for h1, choice in sorted(tp.items())])
                                                for h0, (a1, tp) in sorted(policy.items())]
        bundles.append(bundle)
    optima = select(bundles, checks)
    for obj in OBJECTIVES:
        chosen = next(b for b in bundles if b["bundle"] == optima[obj]["bundles"][0])
        optima[obj]["representative"] = chosen["objectives"][obj]["representative"]
    controls = analytic_controls(f, bundles[2], checks)
    closed_value = max(row["utility"] for row in controls["anchor_subsets"])
    checks.close("closed_Bayesian_value", -optima["bayes"]["score"], closed_value)
    checks.close("prospective_Bayesian_value", closed_value, expected_U)
    if name in ("continuation", "transfer_isolated"):
        checks.require(optima["bayes"]["bundles"] == ["anchor"] and optima["bayes"]["policy_count"] == 1, "main/control optimum not unique")
        for row0 in bundles[2]["histories"]:
            checks.require(row0["optima"]["bayes"]["bundles"] == ["anchor"], "second anchor absent")
            e0 = row0["history"][0] ^ row0["history"][1]
            for row1 in row0["second_bundles"][2]["histories"]:
                e1 = row1["history"][0] ^ row1["history"][1]
                expected = (0, 0, 1 if e0 else 2) if e0 == e1 else ((1, 0, 2) if name == "transfer_isolated" else (0, 1, 10))
                checks.require(row1["optima"]["bayes"]["choices"] == [expected], "prospective contingent action")
        expected_one = .625 if name == "continuation" else .85
        checks.close("best_one_anchor_prediction", controls["best_at_most_one"], expected_one)
    if name == "continuation":
        checks.close("committed_both_prediction", controls["best_committed_both"], .6)
        checks.close("gross_recheck_value", closed_value-controls["best_at_most_one"]+prices(f, 1)[2], .038)
        checks.close("main_accuracy", optima["bayes"]["representative"]["accuracy"], .802)
        checks.close("main_reference_rate", optima["bayes"]["representative"]["final_reference_rate"], .38)
    if name == "recheck_price_tie":
        checks.require(optima["bayes"]["bundles"] == ["anchor"] and optima["bayes"]["policy_count"] == 16, "missing boundary policies")
    choices = sum(len(b1["histories"])*40 for b0 in bundles for r0 in b0["histories"] for b1 in r0["second_bundles"])
    checks.require(choices == 1960, "incomplete history enumeration")
    return dict(name=name, parameters=f, K0=K0, physical_entropy=HW, bundles=bundles,
                global_optima=optima, analytic_controls=controls)


def verify():
    start, checks = perf_counter(), Checks()
    results = [verify_fixture(name, f, expected, checks) for name, f, expected in fixtures()]
    return dict(passed=True, fixtures=results, settings=len(results), local_choices=1960*len(results),
                local_objective_scores=9800*len(results), second_access_scores=105*len(results),
                initial_bundle_scores=15*len(results), global_optimum_sets=5*len(results),
                audited_trajectories=15*len(results), tie_endpoint_policy_checks=30*len(results),
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
        raise SystemExit("Require a new directory on mounted /mnt/bioIce1/fep-ideas")
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__).resolve(), SPEC.resolve(), HELPER.resolve())
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size) for p in sources]
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=120)
    manifest, log_path = output/"MANIFEST.json", output/"RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs frozen before verification; exact three-record policies.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output/"RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['settings']} fixtures; {result['local_choices']} terminal choices; {result['local_objective_scores']} local scores.\n"
                         f"Complete optimum sets: {result['global_optimum_sets']}; trajectory audits: {result['audited_trajectories']}.\n"
                         f"Tie endpoint policies checked: {result['tie_endpoint_policy_checks']}.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; no simulation, fitting, main-outcome tuning or successor launch.\n")
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
