"""Counterfactual arithmetic for the frozen calibration policy; no optimization."""
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

from check_fep_reader_evidence import Checks, entropy, h, information, kl, marginal, physical, report


SPEC = Path(__file__).with_name("FEP_CALIBRATION_TRANSFER_REVIEW_CHECKS_2026-09-18.md")
SOURCE = Path("/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01")
TOL, L = 1e-12, log(2)
OBJECTIVES = ("bayes", "state", "full_extension", "task_extension", "regime_extension")
POLICIES = ("frozen", "copy", "invert", "maintain", "blind", "reference", "frozen_plus_reference")
TRUTHS = (("iid_reset", "iid", 0.), ("iid_break_even", "iid", 4/25),
          ("iid_half_transfer", "iid", .5), ("iid_persistent", "iid", 1.),
          ("shared_flip", "shared", None), ("native", "native", None),
          ("reversal", "reversal", None))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def get_source(checks):
    manifest = json.loads((SOURCE/"MANIFEST.json").read_text())
    checks.require(manifest["passed"], "source run did not pass")
    for item in manifest["inputs"]+manifest["outputs"]:
        checks.require(digest(Path(item["path"])) == item["sha256"], ("source hash mismatch", item["path"]))
    result = json.loads((SOURCE/"RESULTS.json").read_text())
    main = next(f for f in result["fixtures"] if f["name"] == "persistent")
    repeated = next(b for b in main["bundles"] if b["bundle"] == "repeat")
    policy = {}
    for obj in OBJECTIVES:
        opt = main["global_optima"][obj]
        checks.require(opt["policy_count"] == 1 and opt["bundles"] == ["repeat"], "source optimum not unique")
        checks.close("source_planned_utility", opt["representative"]["utility"], .65125)
        candidate = {}
        for row in repeated["histories"]:
            hist = tuple(row["history"])
            choices = row["optima"][obj]["choices"]
            checks.require(len(choices) == 1, "source branch has a tie")
            candidate[hist] = tuple(choices[0])
            checks.require(candidate[hist] == (int(hist[0] != hist[1]), 0, 2), "source policy differs from review")
        if policy:
            checks.require(candidate == policy, "source objectives select different policies")
        policy = candidate
    return main, policy


def calibration(kind, f):
    if kind == "iid":
        return [(w, None, p) for w, p in physical(f["pC"], f["pT"], f["kappa0"], False).items()]
    out = []
    for C, T, x, r, flip, z in product((0, 1), repeat=6):
        pc = f["pC"] if C else 1-f["pC"]
        pt = (f["pT"] if T else 1-f["pT"]) if kind == "shared" else float(T == (kind == "native"))
        if kind == "shared":
            pf = float(flip == 0) if T else .5
        else:
            pf = float(flip == (kind == "reversal"))
        pr = float(r == x) if C else .5
        pz = f["kappa0"] if z == x else 1-f["kappa0"]
        p = pc*pt*.5*pr*pf*pz
        if p:
            out.append(((C, T, x, r, r ^ flip, r ^ flip, z), flip, p))
    return out


def decide(policy_name, w0, frozen):
    if policy_name in ("frozen", "frozen_plus_reference"):
        m, b, code = frozen[w0[4:6]]
        return (2, m, 1, 10) if policy_name == "frozen_plus_reference" else (2, m, b, code)
    choice = {"copy": (0, 0, 2), "invert": (0, 0, 1), "maintain": (1, 0, 2),
              "blind": (0, 0, 0), "reference": (0, 1, 10)}[policy_name]
    return (0,)+choice


def physical_trajectory(kind, tau, policy_name, f, frozen):
    q = {}
    prior = {(C, T): (f["pC"] if C else 1-f["pC"])*(f["pT"] if T else 1-f["pT"])
             for C, T in product((0, 1), repeat=2)}
    for w0, flip, p0 in calibration(kind, f):
        a, m, b, code = decide(policy_name, w0, frozen)
        if kind == "iid":
            qH = {H: (1-tau)*p+tau*float(H == w0[:2]) for H, p in prior.items()}
        else:
            qH = {w0[:2]: 1.}
        for (C, T), ph in qH.items():
            for x, r, y, z in product((0, 1), repeat=4):
                pr = float(r == x) if C else .5
                if m:
                    py = float(y == r)
                elif kind == "iid":
                    py = float(y == r) if T else .5
                else:
                    py = float(y == (r ^ flip))
                pz = f["kappa1"] if z == x else 1-f["kappa1"]
                p = p0*ph*.5*pr*py*pz
                if not p:
                    continue
                obs = (y, z) if b else (y,)
                D = report(code, obs)
                s = w0+(C, T, x, r, y, z, a, m, b, D)
                q[s] = q.get(s, 0.)+p
    return q


def observed(s):
    a, m, b, D = s[13:17]
    hist = s[4:6] if a == 2 else ()
    future_obs = s[11:13] if b else (s[11],)
    return a, hist, m, b, future_obs, D


def summarize(q, f, K, checks):
    pp = (0., f["ell"], 2*f["ell"], f["ell"]+f["d0"], 2*f["ell"]+f["d0"])
    accuracy = fsum(p for s, p in q.items() if s[16] == s[9])
    mr = fsum(p for s, p in q.items() if s[14])
    br = fsum(p for s, p in q.items() if s[15])
    access = fsum(p*pp[s[13]] for s, p in q.items())
    U = f["v"]*accuracy-access-f["c"]*mr-f["d1"]*br
    cs = {s: exp(f["beta"]*(f["v"]*(s[16] == s[9])-pp[s[13]]-f["c"]*s[14]-f["d1"]*s[15])-K) for s in q}
    state = kl(q, cs)
    checks.close("trajectory_normalization", fsum(q.values()), 1.)
    checks.close("true_state_score_identity", state, K-f["beta"]*U-entropy(q))
    checks.close("retained_content_accuracy", fsum(p for s, p in q.items() if s[9] == s[10]), .75)
    retained = information(q, lambda s: s[9], lambda s: s[10])
    checks.close("retained_target_information", retained, L-h(.25))
    qo = marginal(q, observed)
    return dict(accuracy=accuracy, utility=U, maintenance_rate=mr, reference_rate=br,
                calibration_cost=access, state_entropy=entropy(q), true_state_risk=state,
                maintenance_in_random_class=fsum(p for s, p in q.items() if s[14] and not s[8]),
                buffered_calibration_agreement=fsum(p for s, p in q.items() if s[4] == s[5]),
                retained_target_information=retained,
                target_read_information=information(q, lambda s: s[9], lambda s: s[11]),
                record_read_information=information(q, lambda s: s[10], lambda s: s[11]),
                observables=[dict(value=o, probability=p) for o, p in sorted(qo.items())]), qo


def tv(left, right):
    return .5*fsum(abs(left.get(o, 0.)-right.get(o, 0.)) for o in left.keys() | right.keys())


def verify():
    start, checks = perf_counter(), Checks()
    source, frozen = get_source(checks)
    f, K = source["parameters"], source["K"]
    results, laws, read_laws = [], {}, {}
    for name, kind, tau in TRUTHS:
        rows = {}
        for policy_name in POLICIES:
            q = physical_trajectory(kind, tau, policy_name, f, frozen)
            row, qo = summarize(q, f, K, checks)
            rows[policy_name] = row
            laws[name, policy_name] = qo
            if policy_name == "copy":
                read_laws[name, "calibration"] = marginal(q, lambda s: s[:5])
                read_laws[name, "final"] = marginal(q, lambda s: s[7:12])
            expected_copy = .75 if kind == "native" else .25 if kind == "reversal" else .625
            expected = dict(copy=expected_copy, invert=1-expected_copy, maintain=.625, blind=.5, reference=.5)
            expected["frozen"] = .620+tau/32 if kind == "iid" else expected_copy-.005
            expected["frozen_plus_reference"] = .46375 if kind == "iid" else .495
            checks.close("analytic_fixed_policy_utility", row["utility"], expected[policy_name])
            if policy_name == "frozen":
                checks.close("analytic_frozen_maintenance", row["maintenance_rate"], .25 if kind == "iid" else 0.)
                if name == "iid_persistent":
                    original = source["global_optima"]["state"]["representative"]
                    checks.close("original_physical_entropy", row["state_entropy"], original["physical_entropy"])
                    checks.close("original_state_score", row["true_state_risk"], original["scores"]["state"])
                    checks.close("original_accuracy", row["accuracy"], original["accuracy"])
                if kind == "iid":
                    checks.close("analytic_frozen_accuracy", row["accuracy"], 21/32+tau/32)
                if kind in ("native", "reversal"):
                    checks.close("invertible_record_channel", row["record_read_information"], L)
                    checks.close("native_reversed_target_information", row["target_read_information"], L-h(.25))
            if policy_name == "frozen_plus_reference":
                probabilities = {}
                for agree in (True, False):
                    mass = fsum(p for s, p in q.items() if (s[4] == s[5]) == agree)
                    if not mass:
                        continue
                    observed_agreement = fsum(p for s, p in q.items() if (s[4] == s[5]) == agree and s[11] == s[12])/mass
                    probabilities[str(agree)] = observed_agreement
                    if kind == "iid":
                        checks.close("reference_identifies_transfer", observed_agreement, 9/16+tau/48 if agree else 5/8)
                    elif kind in ("native", "reversal"):
                        checks.close("reference_identifies_orientation", observed_agreement, 5/8 if kind == "native" else 3/8)
                row["reference_agreement_by_calibration_agreement"] = probabilities
        baseline = rows["copy"]
        for policy_name, row in rows.items():
            expected_drop = L*row["maintenance_in_random_class"] if kind == "iid" else 0.
            checks.close("maintenance_entropy_difference", baseline["state_entropy"]-row["state_entropy"], expected_drop)
            checks.close("state_score_difference", row["true_state_risk"]-baseline["true_state_risk"],
                         -f["beta"]*(row["utility"]-baseline["utility"])+expected_drop)
        results.append(dict(name=name, kind=kind, tau=tau, policies=rows))
    for name, kind, tau in TRUTHS:
        if kind == "iid":
            checks.close("transfer_observational_equivalence", tv(laws[name, "frozen"], laws["iid_persistent", "frozen"]), 0.)
    checks.close("orientation_observational_equivalence", tv(laws["native", "frozen"], laws["reversal", "frozen"]), 0.)
    checks.close("shared_flip_native_observational_equivalence", tv(laws["shared_flip", "frozen"], laws["native", "frozen"]), 0.)
    for read in ("calibration", "final"):
        checks.close("shared_flip_preserves_single_read_law",
                     tv(read_laws["shared_flip", read], read_laws["iid_persistent", read]), 0.)
    transfer_tv = tv(laws["iid_reset", "frozen_plus_reference"], laws["iid_persistent", "frozen_plus_reference"])
    orientation_tv = tv(laws["native", "frozen_plus_reference"], laws["reversal", "frozen_plus_reference"])
    checks.close("queried_transfer_distinction", transfer_tv, 1/64)
    checks.close("queried_orientation_distinction", orientation_tv, 1/4)
    return dict(passed=True, parameters=f, source_main_objectives=list(OBJECTIVES),
                frozen_policy=[dict(history=hist, choice=choice) for hist, choice in sorted(frozen.items())],
                physical_laws=len(TRUTHS), fixed_policies=len(POLICIES), distributions=len(TRUTHS)*len(POLICIES),
                truth_results=results, queried_transfer_total_variation=transfer_tv,
                queried_orientation_total_variation=orientation_tv, tolerance=TOL,
                numeric_comparisons=checks.numeric, structural_checks=checks.structural,
                max_abs_errors=checks.errors, elapsed_seconds=perf_counter()-start)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    mount = Path("/mnt/bioIce1")
    if not os.path.ismount(mount) or mount/"fep-ideas" not in output.parents:
        raise SystemExit("Require a new output directory on mounted /mnt/bioIce1/fep-ideas")
    output.mkdir(parents=True, exist_ok=False)
    old_manifest = json.loads((SOURCE/"MANIFEST.json").read_text())
    sources = [Path(__file__).resolve(), SPEC.resolve(), SOURCE/"MANIFEST.json", SOURCE/"RESULTS.json"]
    sources += [Path(item["path"]) for item in old_manifest["inputs"]]
    snapshots = {p: p.read_bytes() for p in sources}
    inputs = [dict(path=str(p), sha256=digest(p), bytes=p.stat().st_size) for p in sources]
    receipt = dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                   inputs=inputs, passed=False, process_count=1, forecast_seconds_under=10)
    manifest, log_path = output/"MANIFEST.json", output/"RUN_LOG.txt"
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    log_path.write_text(f"Started {receipt['created_utc']}\nInputs recorded before the review checks; no controller optimization.\n")
    try:
        result = verify()
        if any(digest(p) != item["sha256"] for p, item in zip(sources, inputs)):
            raise AssertionError("Source changed during review verification")
        result["created_utc"] = receipt["created_utc"]
        (output/"RESULTS.json").write_text(json.dumps(result, indent=1, sort_keys=True)+"\n")
        with log_path.open("a") as stream:
            stream.write(f"PASS: {result['physical_laws']} physical laws; {result['fixed_policies']} fixed policies; "
                         f"{result['distributions']} distributions.\n"
                         f"Numeric comparisons: {result['numeric_comparisons']}; structural checks: {result['structural_checks']}.\n"
                         f"Maximum residual: {max(result['max_abs_errors'].values()):.12g}.\n"
                         f"Calculation seconds: {result['elapsed_seconds']:.9f}.\n"
                         "One process; exact arithmetic check of a frozen policy and fixed controls; no refitting or new optimum search.\n")
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
