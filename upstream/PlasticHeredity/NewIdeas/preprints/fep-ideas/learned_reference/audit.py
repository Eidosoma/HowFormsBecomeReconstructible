"""Independent replay: second moments, closed-form sensors and trace search."""
from functools import lru_cache
import hashlib
from itertools import permutations
import math

import numpy as np

from .spec import ARMS, CONDITIONS, SIZES, SPEC, STAGES


class AuditError(ValueError):
    pass


@lru_cache(maxsize=None)
def choices(d):
    out = np.fromiter((v for p in permutations(range(d)) for v in p), dtype=np.int64)
    out = out.reshape(-1, d)
    out.setflags(write=False)
    return out


def second_moment_covariance(x):
    n = len(x)
    sums = np.sum(x, axis=0)
    products = np.einsum("ni,nj->ij", x, x)
    return (products - np.outer(sums, sums) / n) / (n - 1)


def trace_losses(reference, current):
    q = choices(len(reference))
    alignment = np.zeros(len(q))
    for row in range(len(reference)):
        for col in range(len(reference)):
            alignment += reference[row, col] * current[q[:, row], q[:, col]]
    constant = math.fsum(float(v) ** 2 for v in reference.flat) + math.fsum(float(v) ** 2 for v in current.flat)
    return constant - 2 * alignment


def replay_repair(reference, proposal, validation):
    cov = second_moment_covariance(proposal)
    loss = trace_losses(reference, cov)
    tied = np.flatnonzero(loss <= np.min(loss) + SPEC["tie_tolerance"])
    candidate = choices(len(reference))[int(tied[0])]
    d = len(reference)
    batch_size = len(validation) // SPEC["validation_batches"]
    deltas = []
    for start in range(0, len(validation), batch_size):
        batch = second_moment_covariance(validation[start:start + batch_size])
        # Norm terms cancel because Q is a permutation.
        delta = 2 * math.fsum(float(reference[i, j]) *
                             float(batch[candidate[i], candidate[j]] - batch[i, j])
                             for i in range(d) for j in range(d))
        deltas.append(delta)
    mean = math.fsum(deltas) / len(deltas)
    variance = math.fsum((value - mean) ** 2 for value in deltas) / (len(deltas) - 1)
    se = math.sqrt(variance / len(deltas))
    accept = mean > SPEC["gate_se_multiplier"] * se + SPEC["gate_floor"]
    return {"candidate": candidate, "selected": candidate if accept else np.arange(d),
            "accepted": accept, "improvements": deltas, "gate": [mean, se],
            "search": [float(loss.min()), float(loss[0]), float(loss[tied[0]])],
            "ties": len(tied), "proposal_covariance": cov}


def audit_block(a, metadata):
    c, d, s = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"]
    nc, na = len(CONDITIONS), len(ARMS)
    shapes = {"geometry": (c, d, d), "fault": (c, d), "reference_scramble": (c, d),
              "population_covariance": (c, d, d), "factors": (c, d, d),
              "population_symmetry": (c, 2), "reference_readings": (c, 2, SIZES["reference"], d),
              "learned_references": (c, 2, d, d),
              "assessment_records": (c, nc, SIZES["assessment"], d),
              "assessment_readings": (c, nc, SIZES["assessment"], d),
              "candidates": (c, nc, 3, d), "selected": (c, nc, na, d),
              "accepted": (c, nc, 3), "gate_improvements": (c, nc, 3, SPEC["validation_batches"]),
              "gate_statistics": (c, nc, 3, 2), "search_statistics": (c, nc, 3, 3),
              "search_ties": (c, nc, 3), "proposal_covariances": (c, nc, d, d),
              "predictions": (c, nc, na, SIZES["assessment"], d),
              "errors": (c, nc, na), "edited": (c, nc, na),
              "mapping_recovered": (c, nc, na), "proposed": (c, nc, na)}
    for stage in STAGES:
        shapes[stage + "_base"] = (c, SIZES[stage], d)
        shapes[stage + "_noise"] = (c, SIZES[stage], s, d)
    for stage in ("proposal", "validation"):
        shapes[stage + "_readings"] = (c, nc, SIZES[stage], d)
    if set(shapes) != set(a):
        raise AuditError("Missing or unexpected arrays")
    integer_fields = {"fault", "reference_scramble", "candidates", "selected", "search_ties"}
    boolean_fields = {"accepted", "edited", "mapping_recovered", "proposed"}
    for key, shape in shapes.items():
        dtype = np.dtype("int64" if key in integer_fields else "bool" if key in boolean_fields else "float64")
        if a[key].shape != shape or a[key].dtype != dtype or not np.isfinite(a[key]).all():
            raise AuditError("Invalid shape, type or finite values: " + key)
    phase, block = metadata["phase"], metadata["block"]
    if phase not in SPEC["seeds"] or type(block) is not int or block < 0:
        raise AuditError("Invalid block namespace")
    maximum = 0.0

    def check(name, actual, expected, exact=False):
        nonlocal maximum
        x, y = np.asarray(actual), np.asarray(expected)
        difference = float(np.max(np.abs(x.astype(float) - y.astype(float))))
        okay = np.array_equal(x, y) if exact else np.allclose(x, y, rtol=1e-10, atol=1e-10)
        if not okay:
            raise AuditError(f"Replay mismatch {name}: max absolute difference {difference:.6g}")
        maximum = max(maximum, difference)

    def rng(field):
        text = "/".join(("IM2-v1", phase, str(SPEC["seeds"][phase]), str(block), field))
        entropy = int.from_bytes(hashlib.sha256(text.encode("utf8")).digest()[:16], byteorder="little")
        return np.random.Generator(np.random.PCG64(entropy))

    check("geometry RNG", a["geometry"], rng("geometry").standard_normal((c, d, d)), exact=True)
    for stage in STAGES:
        for suffix in ("base", "noise"):
            field = stage + "_" + suffix
            check(field + " RNG", a[field], rng(field).standard_normal(shapes[field]), exact=True)
    route_rng = rng("fault")
    faults = np.tile(np.arange(d), (c, 1))
    for case in range(c):
        sites = route_rng.permutation(d)[:SPEC["damaged_channels"]]
        for index in range(0, len(sites), 2):
            faults[case, sites[index]] = sites[index + 1]
            faults[case, sites[index + 1]] = sites[index]
    check("fault RNG", a["fault"], faults, exact=True)
    scramble_rng = rng("reference_scramble")
    scrambles = np.asarray([scramble_rng.permutation(d) for _ in range(c)])
    check("scramble RNG", a["reference_scramble"], scrambles, exact=True)
    for field, label in (("assessment_records", "record"), ("learned_references", "reference")):
        digest = hashlib.sha256(a[field].tobytes(order="C")).hexdigest()
        if not (digest == metadata[label + "_sha256_before"] == metadata[label + "_sha256_after"]):
            raise AuditError("Changed protected bytes: " + field)
    rho, sigma = SPEC["retention"], SPEC["noise_sd"]
    gain = 1 - rho ** s
    weights = np.asarray([rho ** (s - j - 1) * sigma / gain for j in range(s)])

    def observed(signal, noise, route):
        return np.take(signal, route, axis=1) + np.einsum("nsd,s->nd", noise, weights)

    expected_metrics = np.empty((c, nc, na, 4))
    identity = np.arange(d)
    for case in range(c):
        geometry = a["geometry"][case]
        gram = np.asarray([[math.fsum(float(geometry[i, k]) * float(geometry[j, k])
                            for k in range(d)) / d + (SPEC["gram_ridge"] if i == j else 0)
                            for j in range(d)] for i in range(d)])
        normalizer = np.sqrt(np.diag(gram))
        population = gram / normalizer[:, None] / normalizer[None, :]
        factor = np.linalg.cholesky(population)
        check("population covariance", a["population_covariance"][case], population)
        check("factor", a["factors"][case], factor)
        symmetry_losses = trace_losses(population, population)[1:]
        check("population symmetry", a["population_symmetry"][case],
              [symmetry_losses.min(), np.count_nonzero(symmetry_losses <= SPEC["tie_tolerance"])])
        reference_worlds = []
        for world in range(2):
            raw = np.einsum("ij,nj->ni", factor, a["reference_base"][case]) if world == 0 else a["reference_base"][case]
            read = observed(raw, a["reference_noise"][case], identity)
            check("reference readings", a["reference_readings"][case, world], read)
            reference = second_moment_covariance(read)
            reference_worlds.append(reference)
            check("learned reference", a["learned_references"][case, world], reference)
        for condition in range(nc):
            fault = faults[case] if condition in (1, 4) else identity
            stage_signals, stage_reads = {}, {}
            for stage in ("proposal", "validation", "assessment"):
                raw = np.einsum("ij,nj->ni", factor, a[stage + "_base"][case]) if condition < 3 else a[stage + "_base"][case]
                if condition == 2:
                    raw = np.take(raw, faults[case], axis=1)
                stage_signals[stage] = raw
                stage_reads[stage] = observed(raw, a[stage + "_noise"][case], fault)
                check(stage + " readings", a[stage + "_readings"][case, condition], stage_reads[stage])
            check("immutable assessment records", a["assessment_records"][case, condition], stage_signals["assessment"])
            ref = reference_worlds[0 if condition < 3 else 1]
            wrong = np.take(np.take(ref, scrambles[case], axis=0), scrambles[case], axis=1)
            erased = np.identity(d) * math.fsum(np.diag(ref)) / d
            selected = np.tile(identity, (na, 1))
            proposed = np.zeros(na, dtype=bool)
            for ref_index, reference in enumerate((ref, wrong, erased)):
                replay = replay_repair(reference, stage_reads["proposal"], stage_reads["validation"])
                for target, source in (("candidates", "candidate"), ("accepted", "accepted"),
                                       ("search_ties", "ties")):
                    check(target, a[target][case, condition, ref_index], replay[source], exact=True)
                for target, source in (("gate_improvements", "improvements"), ("gate_statistics", "gate"),
                                       ("search_statistics", "search")):
                    check(target, a[target][case, condition, ref_index], replay[source])
                arm = (0, 3, 4)[ref_index]
                selected[arm] = replay["selected"]
                proposed[arm] = not np.array_equal(replay["candidate"], identity)
                if ref_index == 0:
                    selected[2] = replay["candidate"]
                    proposed[2] = proposed[0]
                    check("proposal covariance", a["proposal_covariances"][case, condition], replay["proposal_covariance"])
            inverse = np.empty(d, dtype=np.int64)
            for measured, original in enumerate(fault):
                inverse[original] = measured
            selected[5] = inverse
            check("selected mappings", a["selected"][case, condition], selected, exact=True)
            for arm in range(na):
                prediction = np.take(stage_reads["assessment"], selected[arm], axis=1)
                check("predictions", a["predictions"][case, condition, arm], prediction)
                residual = prediction - stage_signals["assessment"]
                mse = math.fsum(float(value) ** 2 for value in residual.flat) / residual.size
                edit = not np.array_equal(selected[arm], identity)
                recovered = all(int(fault[selected[arm, i]]) == i for i in range(d))
                for field, value in (("errors", mse), ("edited", edit),
                                      ("mapping_recovered", recovered), ("proposed", proposed[arm])):
                    check(field, a[field][case, condition, arm], value, exact=field != "errors")
                expected_metrics[case, condition, arm] = [mse, edit, recovered, proposed[arm]]
    for field in ("proposal_readings", "validation_readings", "assessment_readings", "candidates", "accepted"):
        check("identical histories: " + field, a[field][:, 1], a[field][:, 2], exact=True)
    check("paired non-oracle actions", a["selected"][:, 1, :5], a["selected"][:, 2, :5], exact=True)
    check("paired non-oracle predictions", a["predictions"][:, 1, :5], a["predictions"][:, 2, :5], exact=True)
    if (metadata["ambiguity_pairs_verified"] != c
            or metadata["wrong_reference_identity"] != int(np.count_nonzero(np.all(scrambles == identity, axis=1)))
            or metadata["wrong_reference_matches_fault"] != int(np.count_nonzero(np.all(scrambles == faults, axis=1)))):
        raise AuditError("Control coincidence or pair count mismatch")
    return {"passed": True, "max_abs_replay_error": maximum,
            "ambiguity_pairs_verified": c,
            "independent_block_metrics": expected_metrics.mean(axis=0).tolist()}


def audit_summary(summary, checked_block_metrics):
    values = np.asarray(checked_block_metrics, dtype=float)
    n = SPEC["blocks"]
    if values.shape != (n, len(CONDITIONS), len(ARMS), 4) or not np.isfinite(values).all():
        raise AuditError("Incomplete block collection")

    def same(actual, expected, name):
        if not np.allclose(actual, expected, rtol=1e-10, atol=1e-10):
            raise AuditError("Summary mismatch: " + name)

    same(summary["block_metrics"], values, "block metrics")
    definitions = {
        "primary_frozen_minus_gated": ((1, 1, 1), (-1, 1, 0)),
        "wrong_reference_minus_gated": ((1, 1, 3), (-1, 1, 0)),
        "erased_reference_minus_gated": ((1, 1, 4), (-1, 1, 0)),
        "always_minus_gated_damaged": ((1, 1, 2), (-1, 1, 0)),
        "always_minus_gated_intact": ((1, 0, 2), (-1, 0, 0)),
        "intact_frozen_minus_gated": ((1, 0, 1), (-1, 0, 0)),
        "environment_shift_frozen_minus_gated": ((1, 2, 1), (-1, 2, 0)),
        "exchangeable_intact_frozen_minus_gated": ((1, 3, 1), (-1, 3, 0)),
        "exchangeable_damaged_frozen_minus_gated": ((1, 4, 1), (-1, 4, 0)),
        "frozen_damage_cost": ((1, 1, 1), (-1, 0, 1)),
        "oracle_rescue": ((1, 1, 1), (-1, 1, 5)),
        "oracle_minus_gated": ((1, 1, 5), (-1, 1, 0)),
    }
    if set(summary["contrasts"]) != set(definitions):
        raise AuditError("Contrast collection changed")
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    draws = rng.integers(0, n, size=(SPEC["bootstrap_draws"], n))
    weights = np.asarray([np.bincount(row, minlength=n) for row in draws], dtype=float) / n
    for name, terms in definitions.items():
        vector = np.asarray([math.fsum(sign * values[b, cond, arm, 0] for sign, cond, arm in terms)
                             for b in range(n)])
        bootstrap = np.sort(weights @ vector)
        intervals = []
        for quantile in (0.025, 0.975):
            position = (len(bootstrap) - 1) * quantile
            floor, ceil = math.floor(position), math.ceil(position)
            intervals.append(float(bootstrap[floor] + (position - floor) * (bootstrap[ceil] - bootstrap[floor])))
        result = summary["contrasts"][name]
        same(result["mean"], math.fsum(vector) / n, name)
        same(result["ci95"], intervals, name)
        same(result["block_effects"], vector, name)
    names = ("absolute_mse", "edit_rates", "mapping_recovery_rates", "proposal_rates")
    for metric, name in enumerate(names):
        for cond, condition in enumerate(CONDITIONS):
            for arm, arm_name in enumerate(ARMS):
                mean = math.fsum(values[:, cond, arm, metric]) / n
                same(summary[name][condition][arm_name], mean, name)
                if metric > 0:
                    same(summary[name.replace("_rates", "_counts")][condition][arm_name],
                         int(round(mean * n * SPEC["cases"])), name + " counts")
    low, high = summary["contrasts"]["primary_frozen_minus_gated"]["ci95"]
    expected_label = "GAIN" if low > 0 else "HARM" if high < 0 else "UNRESOLVED"
    gates = {name: summary["contrasts"][name]["ci95"][0] > 0 for name in (
        "primary_frozen_minus_gated", "frozen_damage_cost", "oracle_rescue",
        "wrong_reference_minus_gated", "erased_reference_minus_gated")}
    if (summary["primary_label"] != expected_label or summary["maintenance_gates"] != gates
            or summary["maintenance_gates_all_pass"] != all(gates.values())
            or summary["independent_blocks"] != n or summary["cases_per_block"] != SPEC["cases"]
            or summary["read_budget_per_arm_condition"] != SIZES
            or summary["reference_bytes_per_case_environment"] != d_reference_bytes()):
        raise AuditError("Verdict, sample unit or budget mismatch")
    return {"passed": True, "blocks": n, "contrasts": len(definitions),
            "bootstrap_replay": "independent multiplicity weights and interpolated order statistics"}


def d_reference_bytes():
    return 8 * SPEC["channels"] * SPEC["channels"]
