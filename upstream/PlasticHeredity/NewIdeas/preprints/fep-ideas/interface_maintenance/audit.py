"""Independent numerical replay; deliberately does not import model.py."""
import hashlib
import math

import numpy as np

from .spec import ARMS, SPEC


class AuditError(ValueError):
    pass


def audit_block(arrays, metadata):
    c, d, t, m, s = (SPEC[k] for k in
                      ("cases", "channels", "pilots", "records", "sensor_steps"))
    shapes = {
        "permutations": (c, d), "records": (c, m, d),
        "pilots": (c, t, d), "sham_labels": (c, t, d),
        "calibration_noise": (c, t, s, d), "assessment_noise": (c, 2, m, s, d),
        "calibration_observations": (c, 2, t, d),
        "assessment_observations": (c, 2, 2, m, d),
        "active_history": (c, 2, t + 1, d, d), "sham_history": (c, 2, t + 1, d, d),
        "yoked_increments": (c, 2, t, d, d), "readers": (c, 2, len(ARMS), d, d),
        "predictions": (c, 2, 2, len(ARMS), m, d), "errors": (c, 2, 2, len(ARMS)),
    }
    if set(arrays) != set(shapes):
        raise AuditError("Unexpected/missing array fields")
    for name, shape in shapes.items():
        a = arrays[name]
        dtype = np.dtype("int64") if name == "permutations" else np.dtype("float64")
        if a.shape != shape or a.dtype != dtype or not np.isfinite(a).all():
            raise AuditError(f"Invalid shape, dtype or finite values: {name}")
    phase, block = metadata["phase"], metadata["block"]
    if phase not in SPEC["seeds"] or type(block) is not int or block < 0:
        raise AuditError("Invalid namespace/block")

    def stream(field):
        label = "/".join(("IM1-v1", phase, str(SPEC["seeds"][phase]), str(block), field))
        entropy = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:16], byteorder="little")
        return np.random.Generator(np.random.PCG64(entropy))

    max_error = 0.0

    def close(name, actual, expected, exact=False):
        nonlocal max_error
        difference = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
        if exact:
            good = np.array_equal(actual, expected)
        else:
            good = np.allclose(actual, expected, rtol=1e-10, atol=1e-11)
        if not good:
            raise AuditError(f"Replay mismatch {name}: max difference {difference:.6g}")
        max_error = max(max_error, difference)

    expected_routes = np.tile(np.arange(d, dtype=np.int64), (c, 1))
    faults = stream("fault")
    for case in range(c):
        sites = faults.permutation(d)[:SPEC["damaged_channels"]]
        for j in range(0, len(sites), 2):
            expected_routes[case, sites[j]] = sites[j + 1]
            expected_routes[case, sites[j + 1]] = sites[j]
    close("fault RNG", arrays["permutations"], expected_routes, exact=True)
    expected_inputs = {
        "records": stream("records").uniform(low=-1, high=1, size=(c, m, d)),
        "pilots": stream("pilots").integers(low=0, high=2, size=(c, t, d)) * 2.0 - 1.0,
        "sham_labels": stream("sham").integers(low=0, high=2, size=(c, t, d)) * 2.0 - 1.0,
        "calibration_noise": stream("calibration_noise").standard_normal(size=(c, t, s, d)),
        "assessment_noise": stream("assessment_noise").standard_normal(size=(c, 2, m, s, d)),
    }
    for name, expected in expected_inputs.items():
        close(name + " RNG", arrays[name], expected, exact=True)
    digest = hashlib.sha256(arrays["records"].tobytes(order="C")).hexdigest()
    if not (digest == metadata["record_sha256_before"] == metadata["record_sha256_after"]):
        raise AuditError("Record seal mismatch")
    identical = sum(int(np.array_equal(expected_routes[i], expected_routes[(i + 1) % c]))
                    for i in range(c))
    if identical != metadata["identical_damaged_yoke_mappings"]:
        raise AuditError("Yoke coincidence count mismatch")

    rho, sigma = SPEC["retention"], SPEC["noise_sd"]
    gain = 1.0 - rho ** s
    weights = np.asarray([rho ** (s - j - 1) for j in range(s)])
    start = np.identity(d) / gain

    def closed_sensor(signal, noise, route):
        deterministic = gain * np.take(signal, route, axis=-1)
        stochastic = sigma * np.einsum("...sd,s->...d", noise, weights)
        return deterministic + stochastic

    replay_active = np.empty_like(arrays["active_history"])
    replay_sham = np.empty_like(replay_active)
    checked_readers = np.empty_like(arrays["readers"])
    for case in range(c):
        for condition in range(2):
            route = np.arange(d) if condition == 0 else expected_routes[case]
            z = closed_sensor(arrays["pilots"][case], arrays["calibration_noise"][case], route)
            close("calibration sensor", arrays["calibration_observations"][case, condition], z)
            for label_name, history_name, history in (
                ("pilots", "active_history", replay_active),
                ("sham_labels", "sham_history", replay_sham),
            ):
                reader = start.copy()
                history[case, condition, 0] = reader
                for trial in range(t):
                    response = z[trial]
                    scale = SPEC["learning_rate"] / (SPEC["denominator_floor"]
                             + math.fsum(float(v) ** 2 for v in response))
                    for row in range(d):
                        predicted = float(np.dot(reader[row], response))
                        residual = float(arrays[label_name][case, trial, row]) - predicted
                        reader[row] = reader[row] + (scale * residual) * response
                    history[case, condition, trial + 1] = reader
                close(history_name, arrays[history_name][case, condition], history[case, condition])
            checked_readers[case, condition, 0] = replay_active[case, condition, -1]
            checked_readers[case, condition, 1] = start
            checked_readers[case, condition, 3] = replay_sham[case, condition, -1]
            if np.linalg.matrix_rank(z) != d:
                raise AuditError("Pilot responses do not span the channel space")
            checked_readers[case, condition, 4] = np.linalg.solve(
                z.T @ z, z.T @ arrays["pilots"][case]).T
            inverse = np.zeros((d, d))
            for measured_channel, input_channel in enumerate(route):
                inverse[input_channel, measured_channel] = 1 / gain
            checked_readers[case, condition, 5] = inverse

    for case in range(c):
        donor = (case + 1) % c
        donor_deltas = replay_active[donor, :, 1:] - replay_active[donor, :, :-1]
        close("yoked actions", arrays["yoked_increments"][case], donor_deltas)
        for condition in range(2):
            result = start.copy()
            for delta in donor_deltas[condition]:
                result = result + delta
            checked_readers[case, condition, 2] = result
    close("final readers", arrays["readers"], checked_readers)
    checked_errors = np.empty_like(arrays["errors"])
    for case in range(c):
        for condition in range(2):
            route = np.arange(d) if condition == 0 else expected_routes[case]
            for recipient in range(2):
                z = closed_sensor(arrays["records"][case], arrays["assessment_noise"][case, recipient], route)
                close("assessment sensor", arrays["assessment_observations"][case, condition, recipient], z)
                for arm in range(len(ARMS)):
                    output = np.einsum("ij,nj->ni", checked_readers[case, condition, arm], z)
                    close("assessment prediction", arrays["predictions"][case, condition, recipient, arm], output)
                    residual = output - arrays["records"][case]
                    checked_errors[case, condition, recipient, arm] = math.fsum(
                        float(value) ** 2 for value in residual.flat) / (m * d)
    close("assessment MSE", arrays["errors"], checked_errors)
    return {"passed": True, "record_sha256": digest,
            "max_abs_replay_error": max_error,
            "independent_block_errors": checked_errors.mean(axis=0).tolist()}


def audit_summary(summary, checked_block_errors):
    """Rebuild contrasts and bootstrap via multiplicity weights, not sampled means."""
    errors = np.asarray(checked_block_errors, dtype=float)
    n = SPEC["blocks"]
    if errors.shape != (n, 2, 2, len(ARMS)) or not np.isfinite(errors).all():
        raise AuditError("Incomplete block collection")
    if not np.allclose(summary["block_errors"], errors, rtol=1e-10, atol=1e-11):
        raise AuditError("Summary block scores mismatch")
    rng = np.random.Generator(np.random.PCG64(SPEC["bootstrap_seed"]))
    sampled = rng.integers(0, n, size=(SPEC["bootstrap_draws"], n))
    weights = np.asarray([np.bincount(row, minlength=n) for row in sampled], dtype=float) / n
    # Each tuple is (coefficient, condition, recipient, arm).
    definitions = {
        "primary_frozen_minus_active": ((1, 1, 0, 1), (-1, 1, 0, 0)),
        "yoked_minus_active": ((1, 1, 0, 2), (-1, 1, 0, 0)),
        "sham_minus_active": ((1, 1, 0, 3), (-1, 1, 0, 0)),
        "batch_ls_minus_active": ((1, 1, 0, 4), (-1, 1, 0, 0)),
        "oracle_minus_active": ((1, 1, 0, 5), (-1, 1, 0, 0)),
        "intact_frozen_minus_active": ((1, 0, 0, 1), (-1, 0, 0, 0)),
        "damage_interaction": ((1, 1, 0, 1), (-1, 1, 0, 0), (-1, 0, 0, 1), (1, 0, 0, 0)),
        "fresh_frozen_minus_active": ((1, 1, 1, 1), (-1, 1, 1, 0)),
        "frozen_damage_cost": ((1, 1, 0, 1), (-1, 0, 0, 1)),
        "oracle_rescue": ((1, 1, 0, 1), (-1, 1, 0, 5)),
    }
    if set(summary["contrasts"]) != set(definitions):
        raise AuditError("Wrong contrast collection")

    def same(actual, expected, name):
        if not np.allclose(actual, expected, rtol=1e-10, atol=1e-11):
            raise AuditError("Summary mismatch: " + name)

    for name, terms in definitions.items():
        vector = np.asarray([math.fsum(coef * errors[b, cond, rec, arm]
                           for coef, cond, rec, arm in terms) for b in range(n)])
        bootstrap = np.sort(weights @ vector)
        limits = []
        for quantile in (0.025, 0.975):
            position = quantile * (len(bootstrap) - 1)
            lower = math.floor(position)
            upper = math.ceil(position)
            limits.append(float(bootstrap[lower] + (position - lower) * (bootstrap[upper] - bootstrap[lower])))
        same(summary["contrasts"][name]["mean"], math.fsum(vector) / n, name)
        same(summary["contrasts"][name]["ci95"], limits, name)
        same(summary["contrasts"][name]["block_effects"], vector, name)
    for cond, cname in enumerate(("intact", "damaged")):
        for rec, rname in enumerate(("original", "fresh")):
            for arm, aname in enumerate(ARMS):
                same(summary["absolute_mse"][cname][rname][aname],
                     math.fsum(errors[:, cond, rec, arm]) / n, "absolute MSE")
    lo, hi = summary["contrasts"]["primary_frozen_minus_active"]["ci95"]
    label = "GAIN" if lo > 0 else "HARM" if hi < 0 else "UNRESOLVED"
    gates = {key: summary["contrasts"][key]["ci95"][0] > 0 for key in (
        "primary_frozen_minus_active", "frozen_damage_cost", "oracle_rescue",
        "yoked_minus_active", "sham_minus_active", "fresh_frozen_minus_active")}
    if (summary["primary_label"] != label or summary["maintenance_gates"] != gates
            or summary["maintenance_gates_all_pass"] != all(gates.values())
            or summary["independent_blocks"] != n or summary["cases_per_block"] != SPEC["cases"]):
        raise AuditError("Verdict or sampling-unit mismatch")
    return {"passed": True, "blocks": n, "contrasts": len(definitions),
            "bootstrap_replay": "independent multiplicity weights and interpolated order statistics"}
