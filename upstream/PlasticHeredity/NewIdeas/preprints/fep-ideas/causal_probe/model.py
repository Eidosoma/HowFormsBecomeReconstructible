"""IM3 production: protected history, observation-only pulse gates, fresh assay."""
import hashlib

import numpy as np

from learned_reference.model import covariance, mappings, repair
from .spec import ARMS, CONDITIONS, PROBES, SIZES, SPEC, STAGES


def field_rng(phase, block, field):
    key = f"IM3-v1/{phase}/{SPEC['seeds'][phase]}/{block}/{field}"
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def byte_hash(values):
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def sensor_drive(drive, noise):
    state = np.zeros_like(drive)
    for step in range(SPEC["sensor_steps"]):
        state = (SPEC["retention"] * state + (1 - SPEC["retention"]) * drive
                 + SPEC["noise_sd"] * noise[:, step])
    return state / (1 - SPEC["retention"] ** SPEC["sensor_steps"])


def pulse_readings(records, route, commands, off_noise, on_noise, placement):
    """Apparatus only: routing/placement/records are never controller arguments."""
    off_drive = records[:, route]
    if placement == "upstream":
        on_drive = off_drive + commands[:, route]
    elif placement == "downstream":
        on_drive = off_drive + commands
    elif placement == "sham":
        on_drive = off_drive
    else:
        raise ValueError("Unknown actuator placement")
    return np.stack((sensor_drive(off_drive, off_noise), sensor_drive(on_drive, on_noise)), axis=1)


def selected_channel(proposed):
    changed = np.flatnonzero(proposed != np.arange(len(proposed)))
    return int(changed[0]) if len(changed) else 0


def pulse_gate(proposed, command_index, paired_readings):
    """No fault, placement, condition, population or outcome is accessible here."""
    delta = paired_readings[:, 1] - paired_readings[:, 0]
    evidence = delta[:, proposed[command_index]] - delta[:, command_index]
    mean = float(evidence.mean())
    se = float(evidence.std(ddof=1) / np.sqrt(len(evidence)))
    accepted = (proposed[command_index] != command_index
                and mean > SPEC["gate_se_multiplier"] * se + SPEC["gate_floor"])
    return {"selected": proposed.copy() if accepted else np.arange(len(proposed)),
            "accepted": bool(accepted), "evidence": evidence, "statistics": np.asarray([mean, se])}


def uniform_calibration(paired_readings):
    """Known input order 0..7; no acquired reference or proposed map is used."""
    delta = paired_readings[:, 1] - paired_readings[:, 0]
    q = mappings(len(delta))
    losses = np.empty(len(q))
    basis = SPEC["pulse_amplitude"] * np.eye(len(delta))
    for start in range(0, len(q), 2048):
        expected = basis[q[start:start + 2048]]
        residual = delta[None, :, :] - expected
        losses[start:start + len(expected)] = np.sum(residual * residual, axis=(1, 2))
    tied = np.flatnonzero(losses <= losses.min() + SPEC["tie_tolerance"])
    return {"selected": q[tied[0]].copy(), "ties": len(tied),
            "search": np.asarray([losses.min(), losses[0], losses[tied[0]]])}


def generate_block(phase, block):
    c, d, s = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"]
    nc, na, npb, pairs = len(CONDITIONS), len(ARMS), len(PROBES), SPEC["probe_pairs"]
    identity = np.arange(d)
    a = {"geometry": field_rng(phase, block, "geometry").standard_normal((c, d, d)),
         "fault": np.tile(identity, (c, 1)),
         "random_channel": field_rng(phase, block, "random_channel").integers(0, d, size=c, dtype=np.int64)}
    rng = field_rng(phase, block, "fault")
    for case in range(c):
        sites = rng.permutation(d)[:SPEC["damaged_channels"]]
        for index in range(0, len(sites), 2):
            a["fault"][case, sites[index]], a["fault"][case, sites[index + 1]] = sites[index + 1], sites[index]
    bases = {stage: field_rng(phase, block, stage + "_base").standard_normal((c, SIZES[stage], d)) for stage in STAGES}
    noises = {stage: field_rng(phase, block, stage + "_noise").standard_normal((c, SIZES[stage], s, d))
              for stage in STAGES if stage != "diagnostic"}
    off = field_rng(phase, block, "diagnostic_off_noise").standard_normal((c, pairs, s, d))
    on = field_rng(phase, block, "diagnostic_on_noise").standard_normal((c, pairs, s, d))
    shapes = {
        "population_covariance": (c, d, d), "factors": (c, d, d),
        "reference_readings": (c, SIZES["reference"], d), "learned_references": (c, d, d),
        "assessment_records": (c, nc, SIZES["assessment"], d),
        "diagnostic_records": (c, nc, pairs, d),
        "reference_candidates": (c, nc, d), "reference_selected": (c, nc, d),
        "reference_accepted": (c, nc), "reference_improvements": (c, nc, 8),
        "reference_gate": (c, nc, 2), "reference_search": (c, nc, 3),
        "reference_ties": (c, nc), "proposal_covariances": (c, nc, d, d),
        "command_indices": (c, nc, npb, pairs), "commands": (c, nc, npb, pairs, d),
        "probe_readings": (c, nc, npb, pairs, 2, d),
        "probe_evidence": (c, nc, npb, pairs), "probe_statistics": (c, nc, npb, 2),
        "probe_accepted": (c, nc, npb), "uniform_search": (c, nc, 3), "uniform_ties": (c, nc),
        "selected": (c, nc, na, d), "predictions": (c, nc, na, SIZES["assessment"], d),
        "errors": (c, nc, na), "edited": (c, nc, na), "mapping_recovered": (c, nc, na)}
    for stage in ("proposal", "validation", "assessment"):
        shapes[stage + "_readings"] = (c, nc, SIZES[stage], d)
    ints = {"reference_candidates", "reference_selected", "reference_ties", "command_indices", "uniform_ties", "selected"}
    bools = {"reference_accepted", "probe_accepted", "edited", "mapping_recovered"}
    for key, shape in shapes.items():
        a[key] = np.zeros(shape, dtype=np.int64 if key in ints else bool if key in bools else float)
    for case in range(c):
        gram = a["geometry"][case] @ a["geometry"][case].T / d + SPEC["gram_ridge"] * np.eye(d)
        normalizer = np.sqrt(np.diag(gram))
        population = gram / normalizer[:, None] / normalizer[None, :]
        factor = np.linalg.cholesky(population)
        a["population_covariance"][case], a["factors"][case] = population, factor
        signals = {stage: bases[stage][case] @ factor.T for stage in STAGES}
        reads = sensor_drive(signals["reference"], noises["reference"][case])
        a["reference_readings"][case], a["learned_references"][case] = reads, covariance(reads)
        for cond in range(nc):
            route = a["fault"][case] if cond == 1 else identity
            for stage in ("proposal", "validation", "assessment", "diagnostic"):
                records = signals[stage][:, a["fault"][case]] if cond == 2 else signals[stage]
                if stage in ("assessment", "diagnostic"):
                    a[stage + "_records"][case, cond] = records
                if stage != "diagnostic":
                    a[stage + "_readings"][case, cond] = sensor_drive(records[:, route], noises[stage][case])
    a["learned_references"].setflags(write=False)
    a["assessment_records"].setflags(write=False)
    a["diagnostic_records"].setflags(write=False)
    metadata = {"phase": phase, "block": block, "ambiguity_pairs_verified": c}
    for field, label in (("assessment_records", "record"), ("learned_references", "reference"), ("diagnostic_records", "diagnostic")):
        metadata[label + "_sha256_before"] = byte_hash(a[field])
    for case in range(c):
        for cond in range(nc):
            route = a["fault"][case] if cond == 1 else identity
            prior = repair(a["learned_references"][case], a["proposal_readings"][case, cond], a["validation_readings"][case, cond])
            for target, source in (("reference_candidates", "candidate"), ("reference_selected", "selected"),
                                   ("reference_accepted", "accepted"), ("reference_improvements", "improvements"),
                                   ("reference_gate", "gate"), ("reference_search", "search"),
                                   ("reference_ties", "ties"), ("proposal_covariances", "proposal_covariance")):
                a[target][case, cond] = prior[source]
            proposed = prior["selected"]
            j = selected_channel(proposed)
            selected = np.tile(identity, (na, 1))
            selected[ARMS.index("passive")] = proposed
            selected[ARMS.index("oracle")] = np.argsort(route)
            for pidx, name in enumerate(PROBES):
                indices = (np.arange(d) if name == "uniform_calibration" else
                           np.full(pairs, a["random_channel"][case] if name == "random_channel" else j, dtype=np.int64))
                commands = SPEC["pulse_amplitude"] * np.eye(d)[indices]
                placement = name if name in ("downstream", "sham") else "upstream"
                paired = pulse_readings(a["diagnostic_records"][case, cond], route, commands, off[case], on[case], placement)
                a["command_indices"][case, cond, pidx], a["commands"][case, cond, pidx] = indices, commands
                a["probe_readings"][case, cond, pidx] = paired
                if name == "uniform_calibration":
                    result = uniform_calibration(paired)
                    a["uniform_search"][case, cond], a["uniform_ties"][case, cond] = result["search"], result["ties"]
                else:
                    result = pulse_gate(proposed, int(indices[0]), paired)
                    a["probe_evidence"][case, cond, pidx] = result["evidence"]
                    a["probe_statistics"][case, cond, pidx] = result["statistics"]
                    a["probe_accepted"][case, cond, pidx] = result["accepted"]
                selected[ARMS.index(name)] = result["selected"]
            a["selected"][case, cond] = selected
            for arm in range(na):
                predictions = a["assessment_readings"][case, cond][:, selected[arm]]
                a["predictions"][case, cond, arm] = predictions
                a["errors"][case, cond, arm] = np.mean((predictions - a["assessment_records"][case, cond]) ** 2)
                a["edited"][case, cond, arm] = np.any(selected[arm] != identity)
                a["mapping_recovered"][case, cond, arm] = np.array_equal(selected[arm], np.argsort(route))
    for field, label in (("assessment_records", "record"), ("learned_references", "reference"), ("diagnostic_records", "diagnostic")):
        metadata[label + "_sha256_after"] = byte_hash(a[field])
    return a, metadata


def block_metrics(a):
    return np.stack((a["errors"], a["edited"], a["mapping_recovered"]), axis=-1).mean(axis=0)


def block_diagnostics(a):
    identity = np.arange(SPEC["channels"])
    return {"reference_proposal_counts": np.any(a["reference_candidates"] != identity, axis=-1).sum(axis=0).tolist(),
            "reference_accept_counts": a["reference_accepted"].sum(axis=0).tolist(),
            "probe_accept_counts": a["probe_accepted"].sum(axis=0).tolist(),
            "command_pair_counts": [[np.bincount(a["command_indices"][:, cond, probe].ravel(), minlength=len(identity)).tolist()
                                     for probe in range(len(PROBES))] for cond in range(len(CONDITIONS))]}
