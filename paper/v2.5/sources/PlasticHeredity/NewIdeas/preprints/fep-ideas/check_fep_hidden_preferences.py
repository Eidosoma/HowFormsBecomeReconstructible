"""Fixed-policy preference comparison with a common preferred task/cost joint."""
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

from check_fep_reader_evidence import Checks, entropy, kl, marginal
from check_fep_transfer_continuation_review import POLICIES, physical, prices, trajectory


ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "FEP_HIDDEN_PREFERENCES_V1.md"
SOURCE = Path("/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-review-2026-09-19/attempt-01")
FAMILIES = ("content", "literal", "oracle_decoded")
TOL = 1e-12


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def task(s):
    return s[11], s[21], s[17], s[18], s[19], s[20]


def utility(B, f):
    x, D, a0, a1, m, b = B
    return (f["v"] * (D == x) - prices(f, 0)[a0] - prices(f, 1)[a1]
            - f["c"] * m - f["d2"] * b)


def indicator(name, x, r, y, F, m):
    if name == "content":
        return int(r == x)
    if name == "literal":
        return int(y == x)
    return int(y ^ ((1 - m) * F) == x)


def feature(s, name):
    return indicator(name, s[11], s[12], s[16], s[4], s[19])


def relabel(s):
    return s[:16] + (1 - s[16],) + s[17:]


def preferred_cells(f, K0, lambdas, checks):
    cb = {}
    for B in product((0, 1), (0, 1), range(3), range(3), (0, 1), (0, 1)):
        cb[B] = 65536 * exp(f["beta"] * utility(B, f) - K0)
    checks.close("base_preference_normalization", fsum(cb.values()), 1.)
    for family, lam in product(FAMILIES, lambdas):
        mass_sum = []
        z = (1 + exp(lam)) / 2
        for B, expected in cb.items():
            x, D, a0, a1, m, b = B
            values = [indicator(family, x, r, y, F, m)
                      for r, y, F in product((0, 1), repeat=3)]
            checks.require(sum(values) == 4, ("preferred fiber not balanced", B, family))
            base = 8192 * exp(f["beta"] * utility(B, f) - K0)
            actual = fsum(base * exp(lam * value) / z for value in values)
            checks.close("same_preferred_task_cost_cell", actual, expected)
            mass_sum.append(actual)
        checks.close("tilted_preference_normalization", fsum(mass_sum), 1.)
    return cb


def verify():
    started, checks = perf_counter(), Checks()
    manifest = json.loads((SOURCE / "MANIFEST.json").read_text())
    checks.require(manifest["passed"], "source review failed")
    for item in manifest["inputs"] + manifest["outputs"]:
        p = Path(item["path"])
        checks.require(p.stat().st_size == item["bytes"] and digest(p) == item["sha256"],
                       ("source provenance mismatch", str(p)))
    saved = json.loads((SOURCE / "RESULTS.json").read_text())
    checks.require({f["name"] for f in saved["fixtures"]} == {"continuation", "transfer_isolated"},
                   "unexpected source fixtures")
    fixtures, cells, distributions, coding = [], 0, 0, 0
    for source in saved["fixtures"]:
        name, f, K0 = source["name"], source["parameters"], source["K0"]
        checks.close("declared_beta", f["beta"], 8.)
        isolated = name == "transfer_isolated"
        crossing = 12 / 35 if isolated else 152 / 125
        baseline_gap, agreement_gain = (.15, 7 / 16) if isolated else (.304, .25)
        lambdas = (0., crossing, 2.)
        frozen = {(tuple(row["first_history"]), tuple(row["second_history"])): tuple(row["choice"])
                  for row in source["frozen_policy"]}
        checks.require(len(frozen) == 16, "incomplete frozen policy")
        old = next(row for row in source["laws"] if row["law"] == "episode")
        qw = physical(f, "episode")
        checks.close("physical_normalization", fsum(qw.values()), 1.)
        HW = entropy(qw)
        checks.close("saved_physical_entropy", HW, old["physical_entropy"])
        cb = preferred_cells(f, K0, lambdas, checks)
        policy_rows, score_map, naive_map = [], {}, {}
        for policy in POLICIES:
            q = trajectory(qw, policy, frozen)
            qb = marginal(q, task)
            qr = {relabel(s): p for s, p in q.items()}
            U = fsum(p * utility(task(s), f) for s, p in q.items())
            c0 = {s: exp(f["beta"] * utility(task(s), f) - K0) for s in q}
            J0, JB = kl(q, c0), kl(qb, cb)
            checks.close("trajectory_normalization", fsum(q.values()), 1.)
            checks.close("constant_entropy", entropy(q), HW)
            checks.close("saved_policy_utility", U, old["policies"][policy]["utility"])
            checks.close("saved_policy_state_risk", J0, old["policies"][policy]["scores"]["state"])
            checks.close("base_utility_identity", J0, K0 - f["beta"] * U - HW)
            checks.close("relabel_utility", fsum(p * utility(task(s), f) for s, p in qr.items()), U)
            for s in q:
                checks.require(feature(s, "oracle_decoded") == feature(s, "content"),
                               "oracle decoding does not recover retained content")
            expectations = {family: fsum(p * feature(s, family) for s, p in q.items())
                            for family in FAMILIES}
            fidelity = (1 + f["p"]) / 2
            for family in ("content", "oracle_decoded"):
                checks.close("policy_invariant_fidelity", expectations[family], fidelity)
            literal = (fidelity if policy == "maintain" else
                       9 / 16 if isolated and policy in ("frozen", "frozen_audit") else .5)
            checks.close("analytic_literal_agreement", expectations["literal"], literal)
            scores = []
            for family, lam in product(FAMILIES, lambdas):
                z = (1 + exp(lam)) / 2
                cp = {s: c0[s] * exp(lam * feature(s, family)) / z for s in q}
                value = kl(q, cp)
                conditional = fsum(p * log((p / qb[task(s)]) / (cp[s] / cb[task(s)]))
                                   for s, p in q.items())
                checks.close("conditional_tilt_identity", value, J0 - lam * expectations[family] + log(z))
                checks.close("task_conditional_KL_chain", value, JB + conditional)
                checks.require(conditional >= -TOL, "negative conditional risk")
                pushed = {s: exp(f["beta"] * utility(task(s), f) - K0
                                + lam * feature(relabel(s), family)) / z for s in qr}
                transformed = kl(qr, pushed)
                checks.close("bijective_relabel_risk", transformed, value)
                if lam == 0:
                    checks.close("zero_tilt", value, J0)
                score_map[policy, family, lam] = value
                scores.append(dict(family=family, lambda_value=lam, risk=value,
                                   conditional_risk=conditional, relabeled_risk=transformed))
                cells += 1
                coding += 1
            naive_cp = {s: exp(f["beta"] * utility(task(s), f) - K0
                              + 2 * feature(s, "literal")) / ((1 + exp(2)) / 2) for s in qr}
            naive = kl(qr, naive_cp)
            checks.close("reimposed_literal_identity", naive,
                         J0 - 2 * (1 - expectations["literal"]) + log((1 + exp(2)) / 2))
            naive_map[policy] = naive
            policy_rows.append(dict(policy=policy, predictive_support=len(q), utility=U,
                                    original_risk=J0, marginal_task_risk=JB, expectations=expectations,
                                    scores=scores, reimposed_literal_risk=naive))
            distributions += 1
        comparisons, minima = [], []
        for family, lam in product(FAMILIES, lambdas):
            gap = score_map["maintain", family, lam] - score_map["frozen", family, lam]
            expected_gap = baseline_gap - (lam * agreement_gain if family == "literal" else 0)
            checks.close("analytic_maintenance_gap", gap, expected_gap)
            if family == "oracle_decoded":
                for policy in POLICIES:
                    checks.close("oracle_content_risk_equality", score_map[policy, family, lam],
                                 score_map[policy, "content", lam])
            values = {policy: score_map[policy, family, lam] for policy in POLICIES}
            best = min(values.values())
            selected = sorted(policy for policy, value in values.items() if abs(value - best) <= TOL)
            wanted = (["maintain"] if lam == 2 else ["frozen", "maintain"]) if family == "literal" and lam else ["frozen"]
            checks.require(selected == wanted, ("unexpected fixed-set minimum", name, family, lam, selected, wanted))
            comparisons.append(dict(family=family, lambda_value=lam, maintenance_minus_frozen=gap))
            minima.append(dict(family=family, lambda_value=lam, policies=selected,
                               utilities={row["policy"]: row["utility"] for row in policy_rows if row["policy"] in selected}))
        naive_gap = naive_map["maintain"] - naive_map["frozen"]
        checks.close("coding_preference_change_gap", naive_gap, 1.025 if isolated else .804)
        fixtures.append(dict(name=name, parameters=f, K0=K0, physical_entropy=HW,
                             source_frozen_policy=source["frozen_policy"], lambdas=lambdas,
                             preferred_task_cells=[dict(value=B, probability=p) for B, p in sorted(cb.items())],
                             policies=policy_rows, comparisons=comparisons, fixed_set_minima=minima,
                             reimposed_literal_maintenance_gap=naive_gap))
    checks.require(distributions == 14 and cells == 126 and coding == 126, "incomplete declared verification")
    return dict(passed=True, fixtures=fixtures, distributions=distributions, preference_score_cells=cells,
                relabel_score_checks=coding, numeric_comparisons=checks.numeric, structural_checks=checks.structural,
                max_abs_errors=checks.errors, tolerance=TOL, elapsed_seconds=perf_counter() - started)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    mount = Path("/mnt/bioIce1")
    if not os.path.ismount(mount) or mount / "fep-ideas" not in output.parents:
        raise SystemExit("Require a new directory on mounted /mnt/bioIce1/fep-ideas")
    sources = [Path(__file__).resolve(), SPEC, ROOT / "FEP_REPRESENTATION_CONTRACT_V1.md",
               ROOT / "check_fep_transfer_continuation_review.py", ROOT / "check_fep_reader_evidence.py",
               SOURCE / "MANIFEST.json", SOURCE / "RESULTS.json"]
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=sha256(data).hexdigest(), bytes=len(data))
              for p, data in snapshots.items()]
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=30)
    manifest, log_path = output / "MANIFEST.json", output / "RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nFixed-policy hidden preferences; same physical model and preferred task/cost joint.\n")
    try:
        result = verify()
        if any(digest(Path(item["path"])) != item["sha256"] for item in inputs):
            raise AssertionError("Input changed during verification")
        result["created_utc"] = receipt["created_utc"]
        (output / "RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['distributions']} distributions; {result['preference_score_cells']} preference scores; {result['relabel_score_checks']} relabel checks.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; no refitting, new global optimization or new temporal mechanism.\n")
        receipt["passed"] = True
    except BaseException:
        with log_path.open("a") as stream:
            stream.write(traceback.format_exc())
        for p, data in snapshots.items():
            (output / ("FAILED_INPUT_" + p.name)).write_bytes(data)
        raise
    finally:
        receipt["outputs"] = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size)
                              for p in sorted(output.iterdir()) if p.is_file() and p != manifest]
        manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(log_path.read_text(), end="")
    print(f"Record: {output}")


if __name__ == "__main__":
    main()
