"""IM4 independent replay, including composition, voting and impossible pairs."""
import hashlib
import math

import numpy as np

from causal_probe.audit import replay_pulse, replay_uniform
from learned_reference.audit import replay_repair, second_moment_covariance
from .spec import ARMS, CONDITIONS, SCHEMES, SIZES, SPEC


class AuditError(ValueError):
    pass


def audit_block(a, metadata):
    c, d, steps = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"]
    nc, na = len(CONDITIONS), len(ARMS)
    shapes = {"geometry": (c, d, d), "fault": (c, d), "failed_location": (c,),
              "population_covariance": (c, d, d), "factors": (c, d, d),
              "reference_readings": (c, 1024, d), "learned_references": (c, d, d),
              "assessment_records": (c, 2, 64, d), "diagnostic_records": (c, 2, 3, 8, d),
              "reference_candidates": (c, 2, d), "reference_selected": (c, 2, d),
              "reference_accepted": (c, 2), "reference_improvements": (c, 2, 8),
              "reference_gate": (c, 2, 2), "reference_search": (c, 2, 3),
              "reference_ties": (c, 2), "proposal_covariances": (c, 2, d, d),
              "actuator_routes": (c, nc, 3, d), "command_indices": (c, 2, 3, 3, 8),
              "commands": (c, 2, 3, 3, 8, d), "probe_readings": (c, nc, 3, 3, 8, 2, d),
              "path_votes": (c, nc, 2, 3), "path_evidence": (c, nc, 2, 3, 8),
              "path_statistics": (c, nc, 2, 3, 2), "pooled_accepted": (c, nc),
              "pooled_evidence": (c, nc, 24), "pooled_statistics": (c, nc, 2),
              "uniform_mappings": (c, nc, 3, d), "uniform_search": (c, nc, 3, 3),
              "uniform_ties": (c, nc, 3), "uniform_consensus": (c, nc),
              "selected": (c, nc, na, d), "errors": (c, nc, na),
              "edited": (c, nc, na), "mapping_recovered": (c, nc, na)}
    for stage in ("proposal", "validation", "assessment"):
        shapes[stage + "_readings"] = (c, 2, SIZES[stage], d)
    if set(a) != set(shapes):
        raise AuditError("Missing or unexpected arrays")
    ints = {"fault", "failed_location", "reference_candidates", "reference_selected", "reference_ties", "actuator_routes", "command_indices", "uniform_mappings", "uniform_ties", "selected"}
    bools = {"reference_accepted", "path_votes", "pooled_accepted", "uniform_consensus", "edited", "mapping_recovered"}
    for key, shape in shapes.items():
        dtype = np.dtype("int64" if key in ints else "bool" if key in bools else "float64")
        if a[key].shape != shape or a[key].dtype != dtype or not np.isfinite(a[key]).all():
            raise AuditError("Invalid array shape, dtype or finite values: " + key)
    phase, block = metadata["phase"], metadata["block"]
    if phase not in SPEC["seeds"] or type(block) is not int or block < 0:
        raise AuditError("Invalid random namespace")
    maximum = 0.0

    def check(label, actual, expected, exact=False):
        nonlocal maximum
        x, y = np.asarray(actual), np.asarray(expected)
        if x.shape != y.shape:
            raise AuditError("Shape mismatch: " + label)
        error = float(np.max(np.abs(x.astype(float) - y.astype(float))))
        if not (np.array_equal(x, y) if exact else np.allclose(x, y, atol=1e-10, rtol=1e-10)):
            raise AuditError(f"Replay mismatch {label}: {error:.6g}")
        maximum = max(maximum, error)

    def rng(field):
        namespace = "/".join(("IM4-v1", phase, str(SPEC["seeds"][phase]), str(block), field))
        entropy = int.from_bytes(hashlib.sha256(namespace.encode("utf8")).digest()[:16], byteorder="little")
        return np.random.Generator(np.random.PCG64(entropy))

    geometry = rng("geometry").standard_normal((c, d, d))
    check("geometry RNG", a["geometry"], geometry, True)
    base = {stage: rng(stage + "_base").standard_normal((c, count, d)) for stage, count in SIZES.items()}
    noise = {stage: rng(stage + "_noise").standard_normal((c, count, steps, d)) for stage, count in SIZES.items()}
    diagnostic = rng("diagnostic_base").standard_normal((c, 3, 8, d))
    off = rng("diagnostic_off_noise").standard_normal((c, 3, 8, steps, d))
    on = rng("diagnostic_on_noise").standard_normal((c, 3, 8, steps, d))
    identity = np.arange(d)
    faults = np.tile(identity, (c, 1))
    route_rng = rng("fault")
    for case in range(c):
        sites = route_rng.permutation(d)[:4]
        for k in (0, 2):
            faults[case, sites[k]] = sites[k + 1]
            faults[case, sites[k + 1]] = sites[k]
    check("reader RNG", a["fault"], faults, True)
    locations = rng("failed_location").integers(0, 3, size=c, dtype=np.int64)
    check("location RNG", a["failed_location"], locations, True)
    for field, label in (("learned_references", "reference"), ("assessment_records", "record"), ("diagnostic_records", "diagnostic")):
        digest = hashlib.sha256(a[field].tobytes(order="C")).hexdigest()
        if digest != metadata[label + "_sha256_before"] or digest != metadata[label + "_sha256_after"]:
            raise AuditError("Protected bytes changed: " + field)
    weights = [SPEC["noise_sd"] * SPEC["retention"] ** (steps - i - 1)
               / (1 - SPEC["retention"] ** steps) for i in range(steps)]

    def observed(drive, epsilon):
        return drive + np.einsum("nsd,s->nd", epsilon, weights)

    diag = {"reference_proposal_counts": np.zeros(nc, dtype=np.int64),
            "reference_accept_counts": np.zeros(nc, dtype=np.int64),
            "path_vote_counts": np.zeros((nc, 2, 3), dtype=np.int64),
            "disagreement_counts": np.zeros((nc, 2), dtype=np.int64),
            "pooled_accept_counts": np.zeros(nc, dtype=np.int64),
            "uniform_consensus_counts": np.zeros(nc, dtype=np.int64),
            "failed_location_counts": np.zeros(3, dtype=np.int64),
            "command_pair_counts": np.zeros((nc, 3, 8), dtype=np.int64)}
    metrics = np.empty((c, nc, na, 3))
    for case in range(c):
        g = geometry[case]
        gram = np.asarray([[math.fsum(float(g[i, k]) * float(g[j, k]) for k in range(d)) / d
                            + (SPEC["gram_ridge"] if i == j else 0) for j in range(d)] for i in range(d)])
        scale = np.sqrt(np.diag(gram))
        population = gram / scale[:, None] / scale[None, :]
        factor = np.linalg.cholesky(population)
        check("population", a["population_covariance"][case], population)
        check("factor", a["factors"][case], factor)
        signals = {stage: np.einsum("ij,nj->ni", factor, base[stage][case]) for stage in SIZES}
        raw_diagnostic = np.einsum("ij,prj->pri", factor, diagnostic[case])
        ref_read = observed(signals["reference"], noise["reference"][case])
        ref = second_moment_covariance(ref_read)
        check("reference reads", a["reference_readings"][case], ref_read)
        check("protected reference", a["learned_references"][case], ref)
        histories, priors, records, diag_records = [], [], [], []
        for history, route in enumerate((identity, faults[case])):
            reads = {stage: observed(np.take(signals[stage], route, axis=1), noise[stage][case])
                     for stage in ("proposal", "validation", "assessment")}
            for stage, values in reads.items():
                check(stage + " readings", a[stage + "_readings"][case, history], values)
            records.append(np.take(signals["assessment"], route, axis=1))
            diag_records.append(np.take(raw_diagnostic, route, axis=2))
            check("assessment targets", a["assessment_records"][case, history], records[-1])
            check("diagnostic records", a["diagnostic_records"][case, history], diag_records[-1])
            prior = replay_repair(ref, reads["proposal"], reads["validation"])
            for field, key, exact in (("reference_candidates", "candidate", True), ("reference_selected", "selected", True),
                                      ("reference_accepted", "accepted", True), ("reference_improvements", "improvements", False),
                                      ("reference_gate", "gate", False), ("reference_search", "search", False),
                                      ("reference_ties", "ties", True), ("proposal_covariances", "proposal_covariance", False)):
                check(field, a[field][case, history], prior[key], exact)
            histories.append(reads)
            priors.append(prior)
            changed = [j for j in range(d) if int(prior["selected"][j]) != j]
            j = changed[0] if changed else 0
            for scheme in range(3):
                indices = np.asarray([list(range(d)) if scheme == 2 else [j] * 8 for _ in range(3)])
                commands = np.zeros((3, 8, d))
                for path in range(3):
                    for r in range(8):
                        commands[path, r, indices[path, r]] = SPEC["pulse_amplitude"]
                check("command indices", a["command_indices"][case, history, scheme], indices, True)
                check("commands", a["commands"][case, history, scheme], commands, True)
        location = int(locations[case])
        diag["failed_location_counts"][location] += 1
        for cond, name in enumerate(CONDITIONS):
            reader = faults[case] if name.startswith("reader_") else identity
            target = int(name.startswith("environment_"))
            history = int(name not in ("intact", "actuator_only"))
            nfail = 1 if name in ("actuator_only", "reader_one", "environment_one") else 2 if name.endswith("_two") else 3 if name.endswith("_common") else 0
            actuators = np.tile(identity, (3, 1))
            for path in range(3):
                failed = nfail == 3 or (nfail == 1 and path == location) or (nfail == 2 and path != location)
                if failed:
                    actuators[path] = faults[case]
            check("actuator routes", a["actuator_routes"][case, cond], actuators, True)
            q = priors[history]["selected"]
            changed = [j for j in range(d) if int(q[j]) != j]
            j = changed[0] if changed else 0
            diag["reference_proposal_counts"][cond] += int(any(int(priors[history]["candidate"][i]) != i for i in range(d)))
            diag["reference_accept_counts"][cond] += int(priors[history]["accepted"])
            responses = np.zeros((3, 3, 8, 2, d))
            for scheme in range(3):
                for path in range(3):
                    commands = np.zeros((8, d))
                    for r in range(8):
                        index = r if scheme == 2 else j
                        commands[r, index] = SPEC["pulse_amplitude"]
                        diag["command_pair_counts"][cond, scheme, index] += 1
                    actuator = actuators[0 if scheme == 1 else path]
                    increment = np.zeros((8, d))
                    for measured in range(d):
                        increment[:, measured] = commands[:, int(actuator[int(reader[measured])])]
                    drive = np.take(diag_records[target][path], reader, axis=1)
                    responses[scheme, path] = np.stack((observed(drive, off[case, path]), observed(drive + increment, on[case, path])), axis=1)
            check("all diagnostic responses", a["probe_readings"][case, cond], responses)
            votes = [[False] * 3 for _ in range(2)]
            for scheme in range(2):
                for path in range(3):
                    _, accepted, evidence, stats = replay_pulse(q, j, responses[scheme, path])
                    votes[scheme][path] = accepted
                    check("path evidence", a["path_evidence"][case, cond, scheme, path], evidence)
                    check("path gate", a["path_statistics"][case, cond, scheme, path], stats)
                    diag["path_vote_counts"][cond, scheme, path] += int(accepted)
                diag["disagreement_counts"][cond, scheme] += int(0 < sum(votes[scheme]) < 3)
            check("path votes", a["path_votes"][case, cond], votes, True)
            pooled_reads = np.concatenate([responses[1, p] for p in range(3)], axis=0)
            _, pooled, evidence, stats = replay_pulse(q, j, pooled_reads)
            check("pooled decision", a["pooled_accepted"][case, cond], pooled, True)
            check("pooled evidence", a["pooled_evidence"][case, cond], evidence)
            check("pooled stats", a["pooled_statistics"][case, cond], stats)
            diag["pooled_accept_counts"][cond] += int(pooled)
            calibrations = []
            for path in range(3):
                selected, ties, stats = replay_uniform(responses[2, path])
                calibrations.append(tuple(int(v) for v in selected))
                check("uniform map", a["uniform_mappings"][case, cond, path], selected, True)
                check("uniform ties", a["uniform_ties"][case, cond, path], ties, True)
                check("uniform scores", a["uniform_search"][case, cond, path], stats)
            multiplicities = {mapping: calibrations.count(mapping) for mapping in calibrations}
            repeated = [mapping for mapping, count in multiplicities.items() if count >= 2]
            consensus = len(repeated) == 1
            check("calibration consensus", a["uniform_consensus"][case, cond], consensus, True)
            diag["uniform_consensus_counts"][cond] += int(consensus)
            selected = np.tile(identity, (na, 1))
            for arm, accept in enumerate((sum(votes[0]) >= 2, sum(votes[1]) >= 2, pooled, sum(votes[0]) == 3)):
                if accept:
                    selected[arm] = q
            if consensus:
                selected[4] = repeated[0]
            selected[5] = q
            inverse = np.empty(d, dtype=np.int64)
            for measured, original in enumerate(reader):
                inverse[original] = measured
            selected[7] = inverse
            check("reader choices", a["selected"][case, cond], selected, True)
            for arm in range(na):
                prediction = np.take(histories[history]["assessment"], selected[arm], axis=1)
                residual = prediction - records[target]
                mse = math.fsum(float(v) ** 2 for v in residual.flat) / residual.size
                edited = any(int(selected[arm, i]) != i for i in range(d))
                recovered = all(int(reader[selected[arm, i]]) == i for i in range(d))
                for field, value in (("errors", mse), ("edited", edited), ("mapping_recovered", recovered)):
                    check(field, a[field][case, cond, arm], value, field != "errors")
                metrics[case, cond, arm] = [mse, edited, recovered]
    for left, right in ((1, 9), (2, 8)):
        check("shared-failure identical responses", a["probe_readings"][:, left], a["probe_readings"][:, right], True)
        check("shared-failure identical non-oracle decisions", a["selected"][:, left, :7], a["selected"][:, right, :7], True)
    if metadata["ambiguity_pairs_verified"] != 2 * c:
        raise AuditError("Identical-history count mismatch")
    return {"passed": True, "max_abs_replay_error": maximum, "ambiguity_pairs_verified": 2 * c,
            "independent_block_metrics": metrics.mean(axis=0).tolist(),
            "independent_block_diagnostics": {key: value.tolist() for key, value in diag.items()}}


def audit_summary(summary, checked_block_metrics, checked_block_diagnostics):
    n = SPEC["blocks"]
    values = np.asarray(checked_block_metrics, dtype=float)
    if values.shape != (n, 10, 8, 3) or not np.isfinite(values).all() or len(checked_block_diagnostics) != n:
        raise AuditError("Incomplete block collection")

    def same(actual, expected, label):
        if np.asarray(actual).shape != np.asarray(expected).shape or not np.allclose(actual, expected, atol=1e-10, rtol=1e-10):
            raise AuditError("Summary mismatch: " + label)

    same(summary["block_metrics"], values, "block metrics")
    definitions = {"primary_shared_minus_redundant": ((0.5, 4, 1), (0.5, 5, 1), (-0.5, 4, 0), (-0.5, 5, 0))}
    for arm in (2, 3, 4, 5, 6, 7):
        definitions["one_fault_balanced_" + ARMS[arm] + "_minus_redundant"] = ((0.5, 4, arm), (0.5, 5, arm), (-0.5, 4, 0), (-0.5, 5, 0))
    for cond in (4, 5):
        for arm in (1, 2, 5, 6):
            definitions[CONDITIONS[cond] + "_" + ARMS[arm] + "_minus_redundant"] = ((1, cond, arm), (-1, cond, 0))
    for cond in (0, 1, 2, 3, 6, 7, 8, 9):
        definitions[CONDITIONS[cond] + "_frozen_minus_redundant"] = ((1, cond, 6), (-1, cond, 0))
    if set(summary["contrasts"]) != set(definitions):
        raise AuditError("Contrast set changed")
    draws = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"])).integers(0, n, size=(SPEC["bootstrap_draws"], n))
    weights = np.asarray([np.bincount(row, minlength=n) for row in draws], dtype=float) / n
    for name, terms in definitions.items():
        vector = [math.fsum(sign * values[b, cond, arm, 0] for sign, cond, arm in terms) for b in range(n)]
        ordered = np.sort(weights @ vector)
        limits = []
        for quantile in (0.025, 0.975):
            position = (len(ordered) - 1) * quantile
            low, high = math.floor(position), math.ceil(position)
            limits.append(float(ordered[low] + (position - low) * (ordered[high] - ordered[low])))
        same(summary["contrasts"][name]["mean"], math.fsum(vector) / n, name)
        same(summary["contrasts"][name]["ci95"], limits, name)
        same(summary["contrasts"][name]["block_effects"], vector, name)
    for metric, name in enumerate(("absolute_mse", "edit_rates", "mapping_recovery_rates")):
        for cond, condition in enumerate(CONDITIONS):
            for arm, arm_name in enumerate(ARMS):
                mean = math.fsum(values[:, cond, arm, metric]) / n
                same(summary[name][condition][arm_name], mean, name)
                if metric:
                    same(summary[name.replace("_rates", "_counts")][condition][arm_name], round(mean * n * SPEC["cases"]), name + " counts")
    shapes = {"reference_proposal_counts": (10,), "reference_accept_counts": (10,), "path_vote_counts": (10, 2, 3),
              "disagreement_counts": (10, 2), "pooled_accept_counts": (10,), "uniform_consensus_counts": (10,),
              "failed_location_counts": (3,), "command_pair_counts": (10, 3, 8)}
    if set(summary["diagnostics"]) != set(shapes):
        raise AuditError("Diagnostic collection changed")
    for key, shape in shapes.items():
        accumulated = np.zeros(shape, dtype=np.int64)
        for block in checked_block_diagnostics:
            raw = np.asarray(block[key])
            if raw.shape != shape or raw.dtype.kind not in "iu" or np.any(raw < 0):
                raise AuditError("Invalid diagnostic counts")
            for index in np.ndindex(shape):
                accumulated[index] += int(raw[index])
        same(summary["diagnostics"][key], accumulated, key)
    low, high = summary["contrasts"]["primary_shared_minus_redundant"]["ci95"]
    label = "GAIN" if low > 0 else "HARM" if high < 0 else "UNRESOLVED"
    gates = {key: summary["contrasts"][key]["ci95"][0] > 0 for key in (
        "primary_shared_minus_redundant", "reader_one_frozen_minus_redundant", "environment_one_passive_minus_redundant")}
    if (summary["primary_label"] != label or summary["robustness_gates"] != gates
            or summary["robustness_gates_all_pass"] != all(gates.values()) or summary["study"] != SPEC["study"]
            or summary["independent_blocks"] != n or summary["cases_per_block"] != SPEC["cases"]
            or summary["read_budget_per_arm_condition"] != {"reference": 1024, "proposal": 512, "validation": 512, "diagnostic": 48, "assessment": 64}
            or summary["pulse_squared_norm_per_functioning_arm_condition"] != 1.5):
        raise AuditError("Verdict, sample unit or budget changed")
    return {"passed": True, "blocks": n, "contrasts": len(definitions),
            "bootstrap_replay": "independent block multiplicities and interpolated order statistics"}
