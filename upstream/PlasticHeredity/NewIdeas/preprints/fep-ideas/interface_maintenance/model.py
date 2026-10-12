"""Production dynamics. Calibrators receive only pilot labels and responses."""
import hashlib

import numpy as np

from .spec import ARMS, SPEC


def field_rng(phase, block, field):
    key = f"IM1-v1/{phase}/{SPEC['seeds'][phase]}/{block}/{field}"
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def record_hash(records):
    return hashlib.sha256(records.tobytes(order="C")).hexdigest()


def sensor(signals, noises, permutation):
    """One independent hard reset for each signal; steps are the penultimate axis."""
    state = np.zeros_like(signals)
    mapped = signals[..., permutation]
    for step in range(SPEC["sensor_steps"]):
        state = (SPEC["retention"] * state
                 + (1 - SPEC["retention"]) * mapped
                 + SPEC["noise_sd"] * noises[..., step, :])
    return state


def initial_reader():
    gain = 1 - SPEC["retention"] ** SPEC["sensor_steps"]
    return np.eye(SPEC["channels"]) / gain


def learn_reader(labels, observations):
    """No record, fault, evaluation target, RNG or score argument is accepted."""
    reader = initial_reader()
    history = [reader.copy()]
    for label, response in zip(labels, observations):
        residual = label - reader @ response
        reader += (SPEC["learning_rate"] * np.outer(residual, response)
                   / (SPEC["denominator_floor"] + response @ response))
        history.append(reader.copy())
    return np.asarray(history)


def batch_reader(labels, observations):
    return np.linalg.lstsq(observations, labels,
                           rcond=SPEC["lstsq_rcond"])[0].T


def oracle_reader(permutation):
    gain = 1 - SPEC["retention"] ** SPEC["sensor_steps"]
    return np.eye(SPEC["channels"])[permutation].T / gain


def generate_block(phase, block):
    c, d, t, m, s = (SPEC[k] for k in
                      ("cases", "channels", "pilots", "records", "sensor_steps"))
    permutations = np.tile(np.arange(d), (c, 1))
    rng = field_rng(phase, block, "fault")
    for case in range(c):
        chosen = rng.permutation(d)[:SPEC["damaged_channels"]]
        for left, right in chosen.reshape(-1, 2):
            permutations[case, left], permutations[case, right] = right, left
    records = field_rng(phase, block, "records").uniform(-1, 1, (c, m, d))
    pilots = (2 * field_rng(phase, block, "pilots").integers(0, 2, (c, t, d)) - 1).astype(float)
    sham = (2 * field_rng(phase, block, "sham").integers(0, 2, (c, t, d)) - 1).astype(float)
    cal_noise = field_rng(phase, block, "calibration_noise").standard_normal((c, t, s, d))
    eval_noise = field_rng(phase, block, "assessment_noise").standard_normal((c, 2, m, s, d))
    before = record_hash(records)
    for data in (records, pilots, sham, cal_noise, eval_noise, permutations):
        data.setflags(write=False)

    observations = np.empty((c, 2, t, d))
    assessment = np.empty((c, 2, 2, m, d))
    active = np.empty((c, 2, t + 1, d, d))
    sham_history = np.empty_like(active)
    readers = np.empty((c, 2, len(ARMS), d, d))
    for case in range(c):
        for condition in range(2):
            route = np.arange(d) if condition == 0 else permutations[case]
            z = sensor(pilots[case], cal_noise[case], route)
            z.setflags(write=False)
            observations[case, condition] = z
            active[case, condition] = learn_reader(pilots[case], z)
            sham_history[case, condition] = learn_reader(sham[case], z)
            readers[case, condition, 0] = active[case, condition, -1]
            readers[case, condition, 1] = initial_reader()
            readers[case, condition, 3] = sham_history[case, condition, -1]
            readers[case, condition, 4] = batch_reader(pilots[case], z)
            readers[case, condition, 5] = oracle_reader(route)

    increments = np.empty((c, 2, t, d, d))
    for case in range(c):
        donor = (case + 1) % c
        increments[case] = np.diff(active[donor], axis=1)
        for condition in range(2):
            reader = initial_reader()
            for increment in increments[case, condition]:
                reader += increment
            readers[case, condition, 2] = reader

    # Evaluation responses are generated only after every reader is finalized.
    predictions = np.empty((c, 2, 2, len(ARMS), m, d))
    for case in range(c):
        for condition in range(2):
            route = np.arange(d) if condition == 0 else permutations[case]
            for recipient in range(2):
                z = sensor(records[case], eval_noise[case, recipient], route)
                assessment[case, condition, recipient] = z
                for arm in range(len(ARMS)):
                    predictions[case, condition, recipient, arm] = z @ readers[case, condition, arm].T
    errors = np.mean((predictions - records[:, None, None, None, :, :]) ** 2,
                     axis=(-2, -1))
    after = record_hash(records)
    if before != after:
        raise RuntimeError("Assessment record bytes changed")
    arrays = {
        "permutations": permutations, "records": records, "pilots": pilots,
        "sham_labels": sham, "calibration_noise": cal_noise,
        "assessment_noise": eval_noise, "calibration_observations": observations,
        "assessment_observations": assessment, "active_history": active,
        "sham_history": sham_history, "yoked_increments": increments,
        "readers": readers, "predictions": predictions, "errors": errors,
    }
    metadata = {"phase": phase, "block": block, "record_sha256_before": before,
                "record_sha256_after": after,
                "identical_damaged_yoke_mappings": sum(
                    int(np.array_equal(permutations[i], permutations[(i + 1) % c]))
                    for i in range(c))}
    return arrays, metadata
