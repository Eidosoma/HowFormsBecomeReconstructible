"""Production simulation and observation-limited exact covariance alignment."""
from functools import lru_cache
import hashlib
from itertools import permutations

import numpy as np

from .spec import ARMS, CONDITIONS, SIZES, SPEC, STAGES


def field_rng(phase, block, field):
    key = f"IM2-v1/{phase}/{SPEC['seeds'][phase]}/{block}/{field}"
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def byte_hash(values):
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


@lru_cache(maxsize=None)
def mappings(dimension):
    values = np.asarray(list(permutations(range(dimension))), dtype=np.int64)
    values.setflags(write=False)
    return values


def covariance(readings):
    centered = readings - readings.mean(axis=0)
    return centered.T @ centered / (len(readings) - 1)


def permutation_losses(reference, current):
    choices = mappings(len(reference))
    losses = np.empty(len(choices))
    for start in range(0, len(choices), 2048):
        q = choices[start:start + 2048]
        delta = reference[None, :, :] - current[q[:, :, None], q[:, None, :]]
        losses[start:start + len(q)] = np.sum(delta * delta, axis=(1, 2))
    return losses


def repair(reference, proposal_readings, validation_readings):
    """Only learned reference and two independent unlabeled batches are visible."""
    current = covariance(proposal_readings)
    choices = mappings(len(reference))
    losses = permutation_losses(reference, current)
    tied = np.flatnonzero(losses <= losses.min() + SPEC["tie_tolerance"])
    candidate = choices[tied[0]].copy()
    improvements = []
    for readings in np.split(validation_readings, SPEC["validation_batches"]):
        batch = covariance(readings)
        loss_identity = np.sum((reference - batch) ** 2)
        loss_candidate = np.sum((reference - batch[np.ix_(candidate, candidate)]) ** 2)
        improvements.append(float(loss_identity - loss_candidate))
    improvements = np.asarray(improvements)
    mean = float(improvements.mean())
    se = float(improvements.std(ddof=1) / np.sqrt(len(improvements)))
    accepted = mean > SPEC["gate_se_multiplier"] * se + SPEC["gate_floor"]
    return {"candidate": candidate, "selected": candidate.copy() if accepted else np.arange(len(reference)),
            "accepted": accepted, "improvements": improvements, "gate": np.asarray([mean, se]),
            "search": np.asarray([losses.min(), losses[0], losses[tied[0]]]),
            "ties": len(tied), "proposal_covariance": current}


def sensor(signals, noises, route):
    state = np.zeros_like(signals)
    mapped = signals[:, route]
    for step in range(SPEC["sensor_steps"]):
        state = (SPEC["retention"] * state + (1 - SPEC["retention"]) * mapped
                 + SPEC["noise_sd"] * noises[:, step])
    return state / (1 - SPEC["retention"] ** SPEC["sensor_steps"])


def generate_block(phase, block):
    c, d, s = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"]
    nc, na = len(CONDITIONS), len(ARMS)
    a = {"geometry": field_rng(phase, block, "geometry").standard_normal((c, d, d))}
    for stage in STAGES:
        a[stage + "_base"] = field_rng(phase, block, stage + "_base").standard_normal((c, SIZES[stage], d))
        a[stage + "_noise"] = field_rng(phase, block, stage + "_noise").standard_normal((c, SIZES[stage], s, d))
    a["fault"] = np.tile(np.arange(d), (c, 1))
    rng = field_rng(phase, block, "fault")
    for case in range(c):
        sites = rng.permutation(d)[:SPEC["damaged_channels"]]
        for left, right in sites.reshape(-1, 2):
            a["fault"][case, left], a["fault"][case, right] = right, left
    rng = field_rng(phase, block, "reference_scramble")
    a["reference_scramble"] = np.asarray([rng.permutation(d) for _ in range(c)])
    a["population_covariance"] = np.empty((c, d, d))
    a["factors"] = np.empty((c, d, d))
    a["population_symmetry"] = np.empty((c, 2))
    a["reference_readings"] = np.empty((c, 2, SIZES["reference"], d))
    a["learned_references"] = np.empty((c, 2, d, d))
    for stage in ("proposal", "validation"):
        a[stage + "_readings"] = np.empty((c, nc, SIZES[stage], d))
    a["assessment_records"] = np.empty((c, nc, SIZES["assessment"], d))
    identity = np.arange(d)
    for case in range(c):
        gram = a["geometry"][case] @ a["geometry"][case].T / d + SPEC["gram_ridge"] * np.eye(d)
        sd = np.sqrt(np.diag(gram))
        cov = gram / np.outer(sd, sd)
        factor = np.linalg.cholesky(cov)
        a["population_covariance"][case] = cov
        a["factors"][case] = factor
        population_losses = permutation_losses(cov, cov)
        a["population_symmetry"][case] = [population_losses[1:].min(),
                                          np.count_nonzero(population_losses[1:] <= SPEC["tie_tolerance"])]
        for world in range(2):
            signal = a["reference_base"][case] @ factor.T if world == 0 else a["reference_base"][case]
            observed = sensor(signal, a["reference_noise"][case], identity)
            a["reference_readings"][case, world] = observed
            a["learned_references"][case, world] = covariance(observed)
        for condition in range(nc):
            route = a["fault"][case] if condition in (1, 4) else identity
            for stage in ("proposal", "validation", "assessment"):
                signal = a[stage + "_base"][case] @ factor.T if condition < 3 else a[stage + "_base"][case]
                if condition == 2:
                    signal = signal[:, a["fault"][case]]
                if stage == "assessment":
                    a["assessment_records"][case, condition] = signal
                else:
                    a[stage + "_readings"][case, condition] = sensor(signal, a[stage + "_noise"][case], route)

    record_before = byte_hash(a["assessment_records"])
    reference_before = byte_hash(a["learned_references"])
    a["assessment_records"].setflags(write=False)
    a["learned_references"].setflags(write=False)
    a["proposal_readings"].setflags(write=False)
    a["validation_readings"].setflags(write=False)
    a["candidates"] = np.empty((c, nc, 3, d), dtype=np.int64)
    a["selected"] = np.empty((c, nc, na, d), dtype=np.int64)
    a["accepted"] = np.empty((c, nc, 3), dtype=bool)
    a["gate_improvements"] = np.empty((c, nc, 3, SPEC["validation_batches"]))
    a["gate_statistics"] = np.empty((c, nc, 3, 2))
    a["search_statistics"] = np.empty((c, nc, 3, 3))
    a["search_ties"] = np.empty((c, nc, 3), dtype=np.int64)
    a["proposal_covariances"] = np.empty((c, nc, d, d))
    for case in range(c):
        for condition in range(nc):
            learned = a["learned_references"][case, 0 if condition < 3 else 1]
            scramble = a["reference_scramble"][case]
            references = (learned, learned[np.ix_(scramble, scramble)], np.eye(d) * np.trace(learned) / d)
            for ref_index, reference in enumerate(references):
                reference.setflags(write=False)
                result = repair(reference, a["proposal_readings"][case, condition], a["validation_readings"][case, condition])
                a["candidates"][case, condition, ref_index] = result["candidate"]
                a["accepted"][case, condition, ref_index] = result["accepted"]
                a["gate_improvements"][case, condition, ref_index] = result["improvements"]
                a["gate_statistics"][case, condition, ref_index] = result["gate"]
                a["search_statistics"][case, condition, ref_index] = result["search"]
                a["search_ties"][case, condition, ref_index] = result["ties"]
                a["selected"][case, condition, (0, 3, 4)[ref_index]] = result["selected"]
                if ref_index == 0:
                    a["selected"][case, condition, 2] = result["candidate"]
                    a["proposal_covariances"][case, condition] = result["proposal_covariance"]
            a["selected"][case, condition, 1] = identity
            a["selected"][case, condition, 5] = np.argsort(a["fault"][case]) if condition in (1, 4) else identity

    # No assessment responses/predictions are calculated until learning has finished.
    a["assessment_readings"] = np.empty((c, nc, SIZES["assessment"], d))
    a["predictions"] = np.empty((c, nc, na, SIZES["assessment"], d))
    a["mapping_recovered"] = np.empty((c, nc, na), dtype=bool)
    for case in range(c):
        for condition in range(nc):
            route = a["fault"][case] if condition in (1, 4) else identity
            observed = sensor(a["assessment_records"][case, condition], a["assessment_noise"][case], route)
            a["assessment_readings"][case, condition] = observed
            for arm in range(na):
                correction = a["selected"][case, condition, arm]
                a["predictions"][case, condition, arm] = observed[:, correction]
                a["mapping_recovered"][case, condition, arm] = np.array_equal(route[correction], identity)
    a["errors"] = np.mean((a["predictions"] - a["assessment_records"][:, :, None]) ** 2, axis=(-2, -1))
    a["edited"] = np.any(a["selected"] != identity, axis=-1)
    a["proposed"] = np.zeros_like(a["edited"])
    for arm, ref_index in ((0, 0), (2, 0), (3, 1), (4, 2)):
        a["proposed"][:, :, arm] = np.any(a["candidates"][:, :, ref_index] != identity, axis=-1)
    for field in ("proposal_readings", "validation_readings", "assessment_readings", "candidates", "accepted"):
        if not np.array_equal(a[field][:, 1], a[field][:, 2]):
            raise RuntimeError("Identical-observation pair diverged: " + field)
    if not np.array_equal(a["selected"][:, 1, :5], a["selected"][:, 2, :5]):
        raise RuntimeError("Paired non-oracle controller decisions differ")
    metadata = {"phase": phase, "block": block,
                "record_sha256_before": record_before, "record_sha256_after": byte_hash(a["assessment_records"]),
                "reference_sha256_before": reference_before, "reference_sha256_after": byte_hash(a["learned_references"]),
                "ambiguity_pairs_verified": c,
                "wrong_reference_identity": int(np.count_nonzero(np.all(a["reference_scramble"] == identity, axis=1))),
                "wrong_reference_matches_fault": int(np.count_nonzero(np.all(a["reference_scramble"] == a["fault"], axis=1)))}
    if record_before != metadata["record_sha256_after"] or reference_before != metadata["reference_sha256_after"]:
        raise RuntimeError("Protected record/reference changed")
    return a, metadata


def block_metrics(arrays):
    return np.stack([arrays[key].astype(float) for key in
                     ("errors", "edited", "mapping_recovered", "proposed")], axis=-1).mean(axis=0)
