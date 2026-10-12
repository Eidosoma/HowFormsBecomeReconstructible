"""Independent IM3 replay: regenerated randomness, closed-form drives, trace scores."""
import hashlib
import math

import numpy as np

from learned_reference.audit import choices, replay_repair, second_moment_covariance
from .spec import ARMS, CONDITIONS, PROBES, SIZES, SPEC, STAGES


class AuditError(ValueError):
    pass


def replay_pulse(proposed, j, readings):
    evidence = [float(row[1, proposed[j]]) - float(row[0, proposed[j]])
                - float(row[1, j]) + float(row[0, j]) for row in readings]
    mean = math.fsum(evidence) / len(evidence)
    se = math.sqrt(math.fsum((v - mean) ** 2 for v in evidence) / ((len(evidence) - 1) * len(evidence)))
    accepted = int(proposed[j]) != j and mean > 2 * se + SPEC["gate_floor"]
    return proposed if accepted else np.arange(len(proposed)), accepted, evidence, [mean, se]


def replay_uniform(readings):
    response = readings[:, 1] - readings[:, 0]
    candidates = choices(len(response))
    alignment = np.zeros(len(candidates))
    for j in range(len(response)):
        alignment += response[j, candidates[:, j]]
    constant = math.fsum(float(v) ** 2 for v in response.flat) + len(response) * SPEC["pulse_amplitude"] ** 2
    loss = constant - 2 * SPEC["pulse_amplitude"] * alignment
    ties = np.flatnonzero(loss <= float(min(loss)) + SPEC["tie_tolerance"])
    return candidates[ties[0]], len(ties), [float(min(loss)), float(loss[0]), float(loss[ties[0]])]


def audit_block(a, metadata):
    c, d, s, pairs = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"], SPEC["probe_pairs"]
    nc, na, npb = len(CONDITIONS), len(ARMS), len(PROBES)
    shapes = {
        "geometry": (c, d, d), "fault": (c, d), "random_channel": (c,),
        "population_covariance": (c, d, d), "factors": (c, d, d),
        "reference_readings": (c, SIZES["reference"], d), "learned_references": (c, d, d),
        "assessment_records": (c, nc, SIZES["assessment"], d), "diagnostic_records": (c, nc, pairs, d),
        "reference_candidates": (c, nc, d), "reference_selected": (c, nc, d),
        "reference_accepted": (c, nc), "reference_improvements": (c, nc, 8),
        "reference_gate": (c, nc, 2), "reference_search": (c, nc, 3),
        "reference_ties": (c, nc), "proposal_covariances": (c, nc, d, d),
        "command_indices": (c, nc, npb, pairs), "commands": (c, nc, npb, pairs, d),
        "probe_readings": (c, nc, npb, pairs, 2, d), "probe_evidence": (c, nc, npb, pairs),
        "probe_statistics": (c, nc, npb, 2), "probe_accepted": (c, nc, npb),
        "uniform_search": (c, nc, 3), "uniform_ties": (c, nc),
        "selected": (c, nc, na, d), "predictions": (c, nc, na, SIZES["assessment"], d),
        "errors": (c, nc, na), "edited": (c, nc, na), "mapping_recovered": (c, nc, na)}
    for stage in ("proposal", "validation", "assessment"):
        shapes[stage + "_readings"] = (c, nc, SIZES[stage], d)
    if set(shapes) != set(a):
        raise AuditError("Missing or unexpected arrays")
    integers = {"fault", "random_channel", "reference_candidates", "reference_selected", "reference_ties", "command_indices", "uniform_ties", "selected"}
    booleans = {"reference_accepted", "probe_accepted", "edited", "mapping_recovered"}
    for key, shape in shapes.items():
        dtype = np.dtype("int64" if key in integers else "bool" if key in booleans else "float64")
        if a[key].shape != shape or a[key].dtype != dtype or not np.isfinite(a[key]).all():
            raise AuditError("Invalid shape, dtype or finite values: " + key)
    phase, block = metadata["phase"], metadata["block"]
    if phase not in SPEC["seeds"] or type(block) is not int or block < 0:
        raise AuditError("Invalid block namespace")
    maximum = 0.0

    def check(name, actual, expected, exact=False):
        nonlocal maximum
        x, y = np.asarray(actual), np.asarray(expected)
        if x.shape != y.shape:
            raise AuditError("Replay shape mismatch: " + name)
        difference = float(np.max(np.abs(x.astype(float) - y.astype(float))))
        okay = np.array_equal(x, y) if exact else np.allclose(x, y, rtol=1e-10, atol=1e-10)
        if not okay:
            raise AuditError(f"Replay mismatch {name}: {difference:.6g}")
        maximum = max(maximum, difference)

    def rng(field):
        key = "/".join(("IM3-v1", phase, str(SPEC["seeds"][phase]), str(block), field))
        seed = int.from_bytes(hashlib.sha256(key.encode("utf8")).digest()[:16], byteorder="little")
        return np.random.Generator(np.random.PCG64(seed))

    geometry = rng("geometry").standard_normal((c, d, d))
    check("geometry RNG", a["geometry"], geometry, exact=True)
    bases = {stage: rng(stage + "_base").standard_normal((c, SIZES[stage], d)) for stage in STAGES}
    noises = {stage: rng(stage + "_noise").standard_normal((c, SIZES[stage], s, d)) for stage in STAGES if stage != "diagnostic"}
    off = rng("diagnostic_off_noise").standard_normal((c, pairs, s, d))
    on = rng("diagnostic_on_noise").standard_normal((c, pairs, s, d))
    routes = np.tile(np.arange(d), (c, 1))
    source = rng("fault")
    for case in range(c):
        sites = source.permutation(d)[:SPEC["damaged_channels"]]
        for k in range(0, len(sites), 2):
            routes[case, sites[k]] = sites[k + 1]
            routes[case, sites[k + 1]] = sites[k]
    check("route RNG", a["fault"], routes, exact=True)
    random_j = rng("random_channel").integers(0, d, size=c, dtype=np.int64)
    check("random command RNG", a["random_channel"], random_j, exact=True)
    for field, label in (("assessment_records", "record"), ("learned_references", "reference"), ("diagnostic_records", "diagnostic")):
        digest = hashlib.sha256(a[field].tobytes(order="C")).hexdigest()
        if digest != metadata[label + "_sha256_before"] or digest != metadata[label + "_sha256_after"]:
            raise AuditError("Changed protected bytes: " + field)
    rho, sigma = SPEC["retention"], SPEC["noise_sd"]
    weights = [sigma * rho ** (s - step - 1) / (1 - rho ** s) for step in range(s)]

    def observed(drive, noise):
        return drive + np.einsum("nsd,s->nd", noise, weights)

    metrics = np.empty((c, nc, na, 3))
    diag = {"reference_proposal_counts": np.zeros(nc, dtype=np.int64),
            "reference_accept_counts": np.zeros(nc, dtype=np.int64),
            "probe_accept_counts": np.zeros((nc, npb), dtype=np.int64),
            "command_pair_counts": np.zeros((nc, npb, d), dtype=np.int64)}
    identity = np.arange(d)
    for case in range(c):
        g = geometry[case]
        gram = np.asarray([[math.fsum(float(g[i, k]) * float(g[j, k]) for k in range(d)) / d
                            + (SPEC["gram_ridge"] if i == j else 0) for j in range(d)] for i in range(d)])
        scale = np.sqrt(np.diag(gram))
        population = gram / scale[:, None] / scale[None, :]
        factor = np.linalg.cholesky(population)
        check("population", a["population_covariance"][case], population)
        check("factor", a["factors"][case], factor)
        signals = {stage: np.einsum("ij,nj->ni", factor, bases[stage][case]) for stage in STAGES}
        reference_readings = observed(signals["reference"], noises["reference"][case])
        reference = second_moment_covariance(reference_readings)
        check("reference readings", a["reference_readings"][case], reference_readings)
        check("reference covariance", a["learned_references"][case], reference)
        for cond in range(nc):
            route = routes[case] if cond == 1 else identity
            records = {stage: np.take(signals[stage], routes[case], axis=1) if cond == 2 else signals[stage]
                       for stage in ("proposal", "validation", "assessment", "diagnostic")}
            reads = {}
            for stage in ("proposal", "validation", "assessment"):
                reads[stage] = observed(np.take(records[stage], route, axis=1), noises[stage][case])
                check(stage + " readings", a[stage + "_readings"][case, cond], reads[stage])
            for stage in ("assessment", "diagnostic"):
                check(stage + " records", a[stage + "_records"][case, cond], records[stage])
            prior = replay_repair(reference, reads["proposal"], reads["validation"])
            for field, key, exact in (("reference_candidates", "candidate", True), ("reference_selected", "selected", True),
                                      ("reference_accepted", "accepted", True), ("reference_improvements", "improvements", False),
                                      ("reference_gate", "gate", False), ("reference_search", "search", False),
                                      ("reference_ties", "ties", True), ("proposal_covariances", "proposal_covariance", False)):
                check(field, a[field][case, cond], prior[key], exact)
            proposed = prior["selected"]
            changed = [j for j in range(d) if int(proposed[j]) != j]
            target = changed[0] if changed else 0
            diag["reference_proposal_counts"][cond] += int(any(int(prior["candidate"][j]) != j for j in range(d)))
            diag["reference_accept_counts"][cond] += int(prior["accepted"])
            selected = np.tile(identity, (na, 1))
            selected[2] = proposed
            inverse = np.empty(d, dtype=np.int64)
            for measured, original in enumerate(route):
                inverse[original] = measured
            selected[7] = inverse
            for pidx, name in enumerate(PROBES):
                indices = list(range(d)) if name == "uniform_calibration" else [int(random_j[case]) if name == "random_channel" else target] * pairs
                commands = np.zeros((pairs, d))
                for r, j in enumerate(indices):
                    commands[r, j] = SPEC["pulse_amplitude"]
                    diag["command_pair_counts"][cond, pidx, j] += 1
                check("command indices", a["command_indices"][case, cond, pidx], indices, True)
                check("command vectors", a["commands"][case, cond, pidx], commands, True)
                drive = np.take(records["diagnostic"], route, axis=1)
                increment = (np.zeros_like(commands) if name == "sham" else commands if name == "downstream"
                             else np.take(commands, route, axis=1))
                paired = np.stack((observed(drive, off[case]), observed(drive + increment, on[case])), axis=1)
                check("paired pulse responses", a["probe_readings"][case, cond, pidx], paired)
                if name == "uniform_calibration":
                    correction, ties, stats = replay_uniform(paired)
                    check("uniform ties", a["uniform_ties"][case, cond], ties, True)
                    check("uniform score", a["uniform_search"][case, cond], stats)
                    accepted, evidence, statistics = False, np.zeros(pairs), np.zeros(2)
                else:
                    correction, accepted, evidence, statistics = replay_pulse(proposed, indices[0], paired)
                check("pulse acceptance", a["probe_accepted"][case, cond, pidx], accepted, True)
                check("pulse evidence", a["probe_evidence"][case, cond, pidx], evidence)
                check("pulse statistics", a["probe_statistics"][case, cond, pidx], statistics)
                diag["probe_accept_counts"][cond, pidx] += int(accepted)
                selected[ARMS.index(name)] = correction
            check("selected readers", a["selected"][case, cond], selected, True)
            for arm in range(na):
                predicted = np.take(reads["assessment"], selected[arm], axis=1)
                residual = predicted - records["assessment"]
                error = math.fsum(float(v) ** 2 for v in residual.flat) / residual.size
                edited = any(int(selected[arm, j]) != j for j in range(d))
                recovered = all(int(route[selected[arm, j]]) == j for j in range(d))
                check("assessment prediction", a["predictions"][case, cond, arm], predicted)
                for field, value in (("errors", error), ("edited", edited), ("mapping_recovered", recovered)):
                    check(field, a[field][case, cond, arm], value, field != "errors")
                metrics[case, cond, arm] = [error, edited, recovered]
    for field in ("proposal_readings", "validation_readings", "assessment_readings", "reference_candidates", "reference_selected", "reference_accepted", "commands", "command_indices"):
        check("indistinguishable prior: " + field, a[field][:, 1], a[field][:, 2], True)
    for probe in (1, 4):
        check("downstream/sham ambiguity", a["probe_readings"][:, 1, probe], a["probe_readings"][:, 2, probe], True)
    for arm in (1, 2, 5, 6):
        check("matched non-discriminating actions", a["selected"][:, 1, arm], a["selected"][:, 2, arm], True)
    if metadata["ambiguity_pairs_verified"] != c:
        raise AuditError("Ambiguity pair count mismatch")
    return {"passed": True, "max_abs_replay_error": maximum, "ambiguity_pairs_verified": c,
            "independent_block_metrics": metrics.mean(axis=0).tolist(),
            "independent_block_diagnostics": {key: value.tolist() for key, value in diag.items()}}


def audit_summary(summary, checked_block_metrics, checked_block_diagnostics):
    values = np.asarray(checked_block_metrics, dtype=float)
    n = SPEC["blocks"]
    if values.shape != (n, 3, 8, 3) or not np.isfinite(values).all() or len(checked_block_diagnostics) != n:
        raise AuditError("Incomplete block collection")

    def same(actual, expected, name):
        if np.asarray(actual).shape != np.asarray(expected).shape or not np.allclose(actual, expected, rtol=1e-10, atol=1e-10):
            raise AuditError("Summary mismatch: " + name)

    same(summary["block_metrics"], values, "block metrics")
    definitions = {"primary_downstream_minus_upstream": ((0.5, 1, 1), (0.5, 2, 1), (-0.5, 1, 0), (-0.5, 2, 0))}
    for arm in (2, 3, 4, 5, 6, 7):
        definitions["balanced_" + ARMS[arm] + "_minus_upstream"] = ((0.5, 1, arm), (0.5, 2, arm), (-0.5, 1, 0), (-0.5, 2, 0))
    for cond in (1, 2):
        for arm in (1, 2, 6):
            definitions[CONDITIONS[cond] + "_" + ARMS[arm] + "_minus_upstream"] = ((1, cond, arm), (-1, cond, 0))
    definitions["intact_frozen_minus_upstream"] = ((1, 0, 6), (-1, 0, 0))
    if set(summary["contrasts"]) != set(definitions):
        raise AuditError("Contrast set mismatch")
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    draws = rng.integers(0, n, size=(SPEC["bootstrap_draws"], n))
    weights = np.asarray([np.bincount(row, minlength=n) for row in draws], dtype=float) / n
    for name, terms in definitions.items():
        vector = [math.fsum(sign * values[b, cond, arm, 0] for sign, cond, arm in terms) for b in range(n)]
        distribution = np.sort(weights @ vector)
        limits = []
        for fraction in (0.025, 0.975):
            position = (len(distribution) - 1) * fraction
            low, high = math.floor(position), math.ceil(position)
            limits.append(float(distribution[low] + (position - low) * (distribution[high] - distribution[low])))
        row = summary["contrasts"][name]
        same(row["mean"], math.fsum(vector) / n, name)
        same(row["ci95"], limits, name)
        same(row["block_effects"], vector, name)
    for metric, name in enumerate(("absolute_mse", "edit_rates", "mapping_recovery_rates")):
        for cond, condition in enumerate(CONDITIONS):
            for arm, arm_name in enumerate(ARMS):
                mean = math.fsum(values[:, cond, arm, metric]) / n
                same(summary[name][condition][arm_name], mean, name)
                if metric > 0:
                    same(summary[name.replace("_rates", "_counts")][condition][arm_name], round(mean * n * SPEC["cases"]), name + " counts")
    diag_shapes = {"reference_proposal_counts": (3,), "reference_accept_counts": (3,),
                   "probe_accept_counts": (3, 5), "command_pair_counts": (3, 5, 8)}
    if set(summary["diagnostics"]) != set(diag_shapes):
        raise AuditError("Diagnostic fields changed")
    for key, shape in diag_shapes.items():
        expected = np.zeros(shape, dtype=np.int64)
        for block in checked_block_diagnostics:
            raw = np.asarray(block[key])
            if raw.shape != shape or raw.dtype.kind not in "iu" or np.any(raw < 0):
                raise AuditError("Invalid diagnostic counts")
            for index in np.ndindex(shape):
                expected[index] += int(raw[index])
        same(summary["diagnostics"][key], expected, key)
    lo, hi = summary["contrasts"]["primary_downstream_minus_upstream"]["ci95"]
    label = "GAIN" if lo > 0 else "HARM" if hi < 0 else "UNRESOLVED"
    gates = {key: summary["contrasts"][key]["ci95"][0] > 0 for key in (
        "primary_downstream_minus_upstream", "damage_frozen_minus_upstream", "environment_change_passive_minus_upstream")}
    if (summary["study"] != SPEC["study"] or summary["independent_blocks"] != n
            or summary["cases_per_block"] != SPEC["cases"] or summary["primary_label"] != label
            or summary["discrimination_gates"] != gates or summary["discrimination_gates_all_pass"] != all(gates.values())
            or summary["read_budget_per_arm_condition"] != {"reference": 1024, "proposal": 512, "validation": 512, "diagnostic": 16, "assessment": 64}
            or summary["pulse_squared_norm_per_functioning_arm_condition"] != 0.5):
        raise AuditError("Verdict or budget mismatch")
    return {"passed": True, "blocks": n, "contrasts": len(definitions),
            "bootstrap_replay": "independent block multiplicities and interpolated order statistics"}
