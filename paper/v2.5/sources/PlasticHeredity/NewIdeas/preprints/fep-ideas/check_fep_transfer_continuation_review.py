"""Frozen-policy and state-projection checks; no controller optimization."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, log
from pathlib import Path
from time import perf_counter
import json
import os
import platform
import traceback

from check_fep_reader_evidence import Checks, entropy, h, information, kl, marginal, report


SPEC = Path(__file__).with_name("FEP_TRANSFER_CONTINUATION_REVIEW_CHECKS_2026-09-19.md")
SOURCE = Path("/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01")
TOL, L = 1e-12, log(2)
LAWS = ("episode", "stepwise", "late_reset")
POLICIES = ("frozen", "old_anchor", "recent_anchor", "maintain", "reference", "blind", "frozen_audit")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def prices(f, i):
    return (0., f["k"], f["k"]+f[f"d{i}"])


def get_source(checks):
    manifest = json.loads((SOURCE/"MANIFEST.json").read_text())
    checks.require(manifest["passed"], "source run failed")
    for item in manifest["inputs"]+manifest["outputs"]:
        checks.require(digest(Path(item["path"])) == item["sha256"], ("source hash mismatch", item["path"]))
    data = json.loads((SOURCE/"RESULTS.json").read_text())
    out = []
    for name in ("continuation", "transfer_isolated"):
        source = next(f for f in data["fixtures"] if f["name"] == name)
        root = next(b for b in source["bundles"] if b["bundle"] == "anchor")
        objectives = ["bayes", "state", "full_extension", "regime_extension"]
        if name == "continuation":
            objectives.append("task_extension")
        policy = None
        for obj in objectives:
            opt = source["global_optima"][obj]
            checks.require(opt["bundles"] == ["anchor"] and opt["policy_count"] == 1, "saved policy not unique")
            candidate = {}
            for row in root["objectives"][obj]["representative_policy"]:
                checks.require(row["second_bundle"] == "anchor", "saved second access changed")
                h0 = tuple(row["first_history"])
                for terminal in row["terminal"]:
                    h1 = tuple(terminal["second_history"])
                    candidate[h0, h1] = tuple(terminal["choice"])
                    e0, e1 = h0[0] ^ h0[1], h1[0] ^ h1[1]
                    expected = (0, 0, 1 if e0 else 2) if e0 == e1 else ((0, 1, 10) if name == "continuation" else (1, 0, 2))
                    checks.require(candidate[h0, h1] == expected, "saved action differs from review")
            checks.require(len(candidate) == 16, "incomplete saved policy")
            if policy is not None:
                checks.require(candidate == policy, "source objectives differ")
            policy = candidate
        if name == "transfer_isolated":
            task = source["global_optima"]["task_extension"]
            checks.require(task["bundles"] == ["skip"] and task["policy_count"] == 1, "isolated task policy changed")
            checks.close("isolated_task_maintenance", task["representative"]["maintenance_rate"], 1.)
            checks.close("isolated_task_calibration_cost", task["representative"]["calibration_cost"], 0.)
        out.append((name, source, policy, objectives))
    return out


def physical(f, law):
    q = {}
    for w in product((0, 1), repeat=14):
        C, K, F0, F1, F2, X0, R0, Z0, X1, R1, Z1, X2, R2, Z2 = w
        mass = (f["p"] if C else 1-f["p"])*(f["tau"] if K else 1-f["tau"])*.5
        mass *= float(F1 == F0) if K else .5
        if law == "episode":
            mass *= float(F2 == F0) if K else .5
        elif law == "stepwise":
            mass *= f["tau"]*float(F2 == F1)+(1-f["tau"])/2
        else:
            mass *= .5
        mass *= .125*(float(R0 == X0 and R1 == X1 and R2 == X2) if C else .125)
        for X, Z, key in ((X0, Z0, "kappa0"), (X1, Z1, "kappa1"), (X2, Z2, "kappa2")):
            mass *= f[key] if Z == X else 1-f[key]
        if mass:
            q[w] = mass
    return q


def calibration_bits(w):
    return w[6] ^ w[2], w[7], w[9] ^ w[3], w[10]


def decide(name, w, frozen):
    bits = calibration_bits(w)
    h0, h1 = bits[:2], bits[2:]
    if name in ("frozen", "frozen_audit"):
        m, b, code = frozen[h0, h1]
        if name == "frozen_audit" and not b:
            code = 3*(code & 1)+12*((code >> 1) & 1)
            b = 1
        return 2, 2, m, b, code
    if name == "old_anchor":
        return 2, 0, 0, 0, 1 if h0[0] != h0[1] else 2
    if name == "recent_anchor":
        return 0, 2, 0, 0, 1 if h1[0] != h1[1] else 2
    return {"maintain": (0, 0, 1, 0, 2), "reference": (0, 0, 0, 1, 10),
            "blind": (0, 0, 0, 0, 0)}[name]


def trajectory(qw, name, frozen):
    q = {}
    for w, p in qw.items():
        a0, a1, m, b, code = decide(name, w, frozen)
        y0, z0, y1, z1 = calibration_bits(w)
        y2 = w[12] ^ (w[4] if not m else 0)
        bits = (y2, w[13]) if b else (y2,)
        q[w+(y0, y1, y2, a0, a1, m, b, report(code, bits))] = p
    return q


def observed(s):
    a0, a1, m, b, D = s[17:]
    h0 = () if a0 == 0 else (s[14],) if a0 == 1 else (s[14], s[7])
    h1 = () if a1 == 0 else (s[15],) if a1 == 1 else (s[15], s[10])
    final = (s[16], s[13]) if b else (s[16],)
    return a0, h0, a1, h1, m, b, final, D


def projected(s):
    return s[11], observed(s)


def projected_preference(t, f, K0):
    x, (a0, h0, a1, h1, m, b, final, D) = t
    n = len(h0)+len(h1)+len(final)
    utility = f["v"]*(D == x)-prices(f, 0)[a0]-prices(f, 1)[a1]-f["c"]*m-f["d2"]*b
    return 2**(16-n)*exp(f["beta"]*utility-K0)


def preferred_checks(f, K0, checks):
    z = 131072*(1+exp(f["beta"]*f["v"]))
    for i in (0, 1):
        z *= fsum(exp(-f["beta"]*cost) for cost in prices(f, i))
    z *= (1+exp(-f["beta"]*f["c"]))*(1+exp(-f["beta"]*f["d2"]))
    checks.close("source_preference_normalizer", K0, log(z))
    ct = {}
    for x, D, m, b in product((0, 1), repeat=4):
        for a0, a1 in product(range(3), repeat=2):
            for h0 in product((0, 1), repeat=a0):
                for h1 in product((0, 1), repeat=a1):
                    for final in product((0, 1), repeat=1+b):
                        t = (x, (a0, h0, a1, h1, m, b, final, D))
                        ct[t] = projected_preference(t, f, K0)
    checks.close("projected_preference_normalization", fsum(ct.values()), 1.)
    task_marginal = marginal(ct, lambda t: (t[0], t[1][7], t[1][0], t[1][2], t[1][4], t[1][5]))
    for (x, D, a0, a1, m, b), mass in task_marginal.items():
        utility = f["v"]*(D == x)-prices(f, 0)[a0]-prices(f, 1)[a1]-f["c"]*m-f["d2"]*b
        checks.close("same_preferred_task_action_marginal", mass, 65536*exp(f["beta"]*utility-K0))


def summarize(q, f, K0, HW, checks):
    qo, qt = marginal(q, observed), marginal(q, projected)
    accuracy = fsum(p for s, p in q.items() if s[21] == s[11])
    mr = fsum(p for s, p in q.items() if s[19])
    br = fsum(p for s, p in q.items() if s[20])
    cal = fsum(p*(prices(f, 0)[s[17]]+prices(f, 1)[s[18]]) for s, p in q.items())
    U = f["v"]*accuracy-cal-f["c"]*mr-f["d2"]*br
    cs = {s: exp(f["beta"]*(f["v"]*(s[21] == s[11])-prices(f, 0)[s[17]]-prices(f, 1)[s[18]]-f["c"]*s[19]-f["d2"]*s[20])-K0) for s in q}
    ct = {t: projected_preference(t, f, K0) for t in qt}
    full_risk, projected_risk = kl(q, cs), kl(qt, ct)
    conditional = fsum(p*log((p/qt[projected(s)])/(cs[s]/ct[projected(s)])) for s, p in q.items())
    info = dict(full=entropy(qo), task=information(q, lambda s: s[11], observed),
                regime=information(q, lambda s: (s[0], s[1], s[4]), observed))
    expected_n = fsum(p*(len(o[1])+len(o[3])+len(o[6])) for o, p in qo.items())
    signal_entropy_gap = expected_n*L-entropy(qo)
    checks.close("trajectory_normalization", fsum(q.values()), 1.)
    checks.close("policy_invariant_physical_entropy", entropy(q), HW)
    checks.close("full_risk_identity", full_risk, K0-f["beta"]*U-HW)
    checks.close("projected_risk_identity", projected_risk, K0-17*L-f["beta"]*U+signal_entropy_gap+info["task"])
    checks.close("projection_conditional_KL_identity", full_risk, projected_risk+conditional)
    checks.close("projection_entropy_chain", entropy(qt), entropy(qo)+L-info["task"])
    checks.require(conditional >= -TOL, "negative projection conditional KL")
    checks.require(signal_entropy_gap >= -TOL, "negative signal entropy deficit")
    checks.close("content_invariant", fsum(p for s, p in q.items() if s[11] == s[12]), (1+f["p"])/2)
    scores = dict(bayes=-U, state=full_risk,
                  **{target+"_extension": K0-f["beta"]*U-I for target, I in info.items()})
    return dict(utility=U, accuracy=accuracy, maintenance_rate=mr, final_reference_rate=br,
                calibration_cost=cal, physical_entropy=entropy(q), information=info, scores=scores,
                projected_risk=projected_risk, projection_conditional_KL=conditional,
                expected_signal_bits=expected_n, signal_entropy_gap=signal_entropy_gap,
                observable_law=[dict(value=o, probability=p) for o, p in sorted(qo.items())]), qo


def tv(left, right):
    return .5*fsum(abs(left.get(o, 0.)-right.get(o, 0.)) for o in left.keys() | right.keys())


def verify():
    start, checks = perf_counter(), Checks()
    sources = get_source(checks)
    results, visible, past, comparisons = [], {}, {}, []
    frozen_predictions = {"continuation": (.638, .61925, .488),
                          "transfer_isolated": (.86875, .821875, .49375)}
    for name, source, frozen, objectives in sources:
        f, K0 = source["parameters"], source["K0"]
        preferred_checks(f, K0, checks)
        fixture_rows = []
        for index, law in enumerate(LAWS):
            qw = physical(f, law)
            checks.close("physical_normalization", fsum(qw.values()), 1.)
            past[name, law] = marginal(qw, lambda w: w[:4]+w[5:11])
            a = f["tau"]
            b, c = (a, a) if law == "episode" else (a, a*a) if law == "stepwise" else (0., 0.)
            correlations = {}
            for label, i, j, expected in (("adjacent_old", 2, 3, a), ("adjacent_new", 3, 4, b), ("lag_two", 2, 4, c)):
                correlations[label] = fsum(p*(1-2*w[i])*(1-2*w[j]) for w, p in qw.items())
                checks.close("orientation_correlation", correlations[label], expected)
            orientH = (3-2*a)*L if law == "episode" else ((2-a)*L+h((1+a)/2) if law == "stepwise" else (3-a)*L)
            HW = h(f["p"])+h(a)+(6-3*f["p"])*L+fsum(h(f[f"kappa{i}"]) for i in range(3))+orientH
            checks.close("analytic_physical_entropy", entropy(qw), HW)
            r0, r1 = 2*f["kappa0"]-1, 2*f["kappa1"]-1
            agree = (1+f["p"]*a*r0*r1)/2
            mr, br = (0., 1-agree) if name == "continuation" else (1-agree, 0.)
            frozen_accuracy = agree/2+f["p"]*(r0*c+r1*b)/4+(1-agree)*(f["kappa2"] if name == "continuation" else 1.)
            Uf = frozen_accuracy-prices(f, 0)[2]-prices(f, 1)[2]-f["c"]*mr-f["d2"]*br
            checks.close("prospective_frozen_utility", Uf, frozen_predictions[name][index])
            expected = dict(frozen=Uf, old_anchor=.5+.5*f["p"]*r0*c-prices(f, 0)[2],
                            recent_anchor=.5+.5*f["p"]*r1*b-prices(f, 1)[2],
                            maintain=(1+f["p"])/2-f["c"], reference=f["kappa2"]-f["d2"], blind=.5,
                            frozen_audit=Uf-f["d2"]*(1-br))
            rows = {}
            for policy_name in POLICIES:
                q = trajectory(qw, policy_name, frozen)
                row, qo = summarize(q, f, K0, HW, checks)
                checks.close("analytic_fixed_policy_utility", row["utility"], expected[policy_name])
                if policy_name in ("frozen", "frozen_audit"):
                    checks.close("frozen_accuracy", row["accuracy"], frozen_accuracy)
                    checks.close("frozen_maintenance", row["maintenance_rate"], mr)
                    checks.close("frozen_reference", row["final_reference_rate"], br if policy_name == "frozen" else 1.)
                if law == "episode" and policy_name == "frozen":
                    original = source["global_optima"]["bayes"]["representative"]
                    for key in ("utility", "accuracy", "maintenance_rate", "final_reference_rate", "calibration_cost", "physical_entropy"):
                        checks.close("saved_original_"+key, row[key], original[key])
                    for obj, value in row["scores"].items():
                        checks.close("saved_original_objective", value, original["scores"][obj])
                rows[policy_name] = row
                visible[name, law, policy_name] = qo
            for policy_name, row in rows.items():
                checks.close("full_state_task_ranking", row["scores"]["state"]-rows["blind"]["scores"]["state"],
                             -f["beta"]*(row["utility"]-rows["blind"]["utility"]))
            fixture_rows.append(dict(law=law, correlations=correlations, physical_entropy=HW, policies=rows))
        for law in LAWS:
            checks.close("same_complete_calibration_law", tv(past[name, "episode"], past[name, law]), 0.)
        rows = fixture_rows[0]["policies"]
        full_gap = rows["frozen"]["scores"]["state"]-rows["recent_anchor"]["scores"]["state"]
        projected_gap = rows["frozen"]["projected_risk"]-rows["recent_anchor"]["projected_risk"]
        analytic_gap = (-.104+(L-h(.62))+.62*(L-h(23/31))+.38*(L-h(.9))-(L-h(.65))
                        if name == "continuation" else -.15+7/8*(L-h(13/14))+L/8)
        checks.close("projection_ranking_gap", projected_gap, analytic_gap)
        checks.close("full_ranking_gap", full_gap, -.104 if name == "continuation" else -.15)
        checks.require(full_gap < 0 < projected_gap, "projected ranking did not reverse")
        comparisons.append(dict(fixture=name, first="frozen", second="recent_anchor",
                                full_score_difference=full_gap, projected_score_difference=projected_gap,
                                conditional_term_difference=rows["frozen"]["projection_conditional_KL"]-rows["recent_anchor"]["projection_conditional_KL"]))
        results.append(dict(name=name, parameters=f, K0=K0, source_objectives_sharing_policy=objectives,
                            frozen_policy=[dict(first_history=h0, second_history=h1, choice=choice) for (h0, h1), choice in sorted(frozen.items())],
                            laws=fixture_rows))
    distinctions = []
    for name in ("continuation", "transfer_isolated"):
        for policy_name in ("frozen", "frozen_audit"):
            expectations = ({"frozen": (.015, 0.), "frozen_audit": (.03, .12)} if name == "continuation"
                            else {"frozen": (0., 0.), "frozen_audit": (.0375, .3)})[policy_name]
            for law, expected in zip(("stepwise", "late_reset"), expectations):
                distance = tv(visible[name, "episode", policy_name], visible[name, law, policy_name])
                checks.close("prospective_observable_total_variation", distance, expected)
                distinctions.append(dict(fixture=name, policy=policy_name, alternative=law, total_variation=distance))
    return dict(passed=True, fixtures=results, physical_cases=6, fixed_policies=7, distributions=42,
                projection_comparisons=comparisons, observable_distinctions=distinctions,
                numeric_comparisons=checks.numeric, structural_checks=checks.structural,
                max_abs_errors=checks.errors, tolerance=TOL, elapsed_seconds=perf_counter()-start)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    mount = Path("/mnt/bioIce1")
    if not os.path.ismount(mount) or mount/"fep-ideas" not in output.parents:
        raise SystemExit("Require a new directory on mounted /mnt/bioIce1/fep-ideas")
    output.mkdir(parents=True, exist_ok=False)
    original_manifest = json.loads((SOURCE/"MANIFEST.json").read_text())
    sources = [Path(__file__).resolve(), SPEC.resolve(), SOURCE/"MANIFEST.json", SOURCE/"RESULTS.json"]
    sources += [Path(item["path"]) for item in original_manifest["inputs"]]
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size) for p in sources]
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=30)
    manifest, log_path = output/"MANIFEST.json", output/"RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nFrozen-policy review and pushed-forward state preferences; no optimization.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during review")
        result["created_utc"] = receipt["created_utc"]
        (output/"RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['physical_cases']} physical cases; {result['fixed_policies']} fixed policies; {result['distributions']} distributions.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; no refitting, controller optimization or original-study rerun.\n")
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
