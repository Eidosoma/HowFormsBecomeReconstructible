"""IM4 production model: three fallible actuator routes and fixed reader decisions."""
import hashlib

import numpy as np

from causal_probe.model import pulse_gate, selected_channel, sensor_drive, uniform_calibration
from learned_reference.model import covariance, repair
from .spec import APPARATUS, ARMS, CONDITIONS, HISTORY, SCHEMES, SIZES, SPEC, TARGET


def field_rng(phase, block, field):
    key = f"IM4-v1/{phase}/{SPEC['seeds'][phase]}/{block}/{field}"
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def byte_hash(a):
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def observed_pair(records, reader, actuator, commands, off_noise, on_noise):
    """Apparatus composition: reader sees both the input and actuated command."""
    drive = records[:, reader]
    increment = commands[:, actuator][:, reader]
    return np.stack((sensor_drive(drive, off_noise), sensor_drive(drive + increment, on_noise)), axis=1)


def mapping_consensus(candidates):
    for candidate in candidates:
        if np.count_nonzero(np.all(candidates == candidate, axis=1)) >= 2:
            return candidate.copy(), True
    return np.arange(candidates.shape[1]), False


def reader_decisions(proposed, command_index, separate_reads, shared_reads, uniform_reads):
    """Only proposed q, command index and observed responses enter this policy."""
    d = len(proposed)
    votes = np.zeros((2, 3), dtype=bool)
    evidence = np.zeros((2, 3, 8))
    stats = np.zeros((2, 3, 2))
    for scheme, readings in enumerate((separate_reads, shared_reads)):
        for path in range(3):
            gate = pulse_gate(proposed, command_index, readings[path])
            votes[scheme, path] = gate["accepted"]
            evidence[scheme, path], stats[scheme, path] = gate["evidence"], gate["statistics"]
    pooled = pulse_gate(proposed, command_index, shared_reads.reshape(24, 2, d))
    uniform = [uniform_calibration(readings) for readings in uniform_reads]
    candidates = np.asarray([row["selected"] for row in uniform], dtype=np.int64)
    consensus, agreement = mapping_consensus(candidates)
    selected = np.tile(np.arange(d), (5, 1))
    for arm, accept in enumerate((votes[0].sum() >= 2, votes[1].sum() >= 2,
                                  pooled["accepted"], votes[0].all())):
        if accept:
            selected[arm] = proposed
    selected[4] = consensus
    return {"selected": selected, "path_votes": votes, "path_evidence": evidence, "path_statistics": stats,
            "pooled_accepted": pooled["accepted"], "pooled_evidence": pooled["evidence"],
            "pooled_statistics": pooled["statistics"], "uniform_mappings": candidates,
            "uniform_search": np.asarray([row["search"] for row in uniform]),
            "uniform_ties": np.asarray([row["ties"] for row in uniform], dtype=np.int64),
            "uniform_consensus": agreement}


def generate_block(phase, block):
    c, d, steps, paths, pairs = SPEC["cases"], SPEC["channels"], SPEC["sensor_steps"], SPEC["paths"], SPEC["pairs_per_path"]
    nc, na, ns = len(CONDITIONS), len(ARMS), len(SCHEMES)
    identity = np.arange(d)
    a = {"geometry": field_rng(phase, block, "geometry").standard_normal((c, d, d)),
         "fault": np.tile(identity, (c, 1)),
         "failed_location": field_rng(phase, block, "failed_location").integers(0, paths, size=c, dtype=np.int64)}
    rng = field_rng(phase, block, "fault")
    for case in range(c):
        sites = rng.permutation(d)[:SPEC["damaged_channels"]]
        for k in range(0, len(sites), 2):
            a["fault"][case, sites[k]], a["fault"][case, sites[k + 1]] = sites[k + 1], sites[k]
    bases = {stage: field_rng(phase, block, stage + "_base").standard_normal((c, n, d)) for stage, n in SIZES.items()}
    noise = {stage: field_rng(phase, block, stage + "_noise").standard_normal((c, n, steps, d)) for stage, n in SIZES.items()}
    diagnostic = field_rng(phase, block, "diagnostic_base").standard_normal((c, paths, pairs, d))
    off = field_rng(phase, block, "diagnostic_off_noise").standard_normal((c, paths, pairs, steps, d))
    on = field_rng(phase, block, "diagnostic_on_noise").standard_normal((c, paths, pairs, steps, d))
    shapes = {"population_covariance": (c, d, d), "factors": (c, d, d),
              "reference_readings": (c, SIZES["reference"], d), "learned_references": (c, d, d),
              "assessment_records": (c, 2, SIZES["assessment"], d), "diagnostic_records": (c, 2, paths, pairs, d),
              "reference_candidates": (c, 2, d), "reference_selected": (c, 2, d),
              "reference_accepted": (c, 2), "reference_improvements": (c, 2, 8),
              "reference_gate": (c, 2, 2), "reference_search": (c, 2, 3),
              "reference_ties": (c, 2), "proposal_covariances": (c, 2, d, d),
              "actuator_routes": (c, nc, paths, d),
              "command_indices": (c, 2, ns, paths, pairs), "commands": (c, 2, ns, paths, pairs, d),
              "probe_readings": (c, nc, ns, paths, pairs, 2, d),
              "path_votes": (c, nc, 2, paths), "path_evidence": (c, nc, 2, paths, pairs),
              "path_statistics": (c, nc, 2, paths, 2), "pooled_accepted": (c, nc),
              "pooled_evidence": (c, nc, paths * pairs), "pooled_statistics": (c, nc, 2),
              "uniform_mappings": (c, nc, paths, d), "uniform_search": (c, nc, paths, 3),
              "uniform_ties": (c, nc, paths), "uniform_consensus": (c, nc),
              "selected": (c, nc, na, d), "errors": (c, nc, na),
              "edited": (c, nc, na), "mapping_recovered": (c, nc, na)}
    for stage in ("proposal", "validation", "assessment"):
        shapes[stage + "_readings"] = (c, 2, SIZES[stage], d)
    integer = {"reference_candidates", "reference_selected", "reference_ties", "actuator_routes", "command_indices", "uniform_mappings", "uniform_ties", "selected"}
    boolean = {"reference_accepted", "path_votes", "pooled_accepted", "uniform_consensus", "edited", "mapping_recovered"}
    for key, shape in shapes.items():
        a[key] = np.zeros(shape, dtype=np.int64 if key in integer else bool if key in boolean else float)
    for case in range(c):
        gram = a["geometry"][case] @ a["geometry"][case].T / d + SPEC["gram_ridge"] * np.eye(d)
        scale = np.sqrt(np.diag(gram))
        population = gram / scale[:, None] / scale[None, :]
        factor = np.linalg.cholesky(population)
        a["population_covariance"][case], a["factors"][case] = population, factor
        signals = {stage: bases[stage][case] @ factor.T for stage in SIZES}
        ref_read = sensor_drive(signals["reference"], noise["reference"][case])
        a["reference_readings"][case], a["learned_references"][case] = ref_read, covariance(ref_read)
        raw_diagnostic = diagnostic[case] @ factor.T
        for history, order in enumerate((identity, a["fault"][case])):
            a["assessment_records"][case, history] = signals["assessment"][:, order]
            a["diagnostic_records"][case, history] = raw_diagnostic[:, :, order]
            for stage in ("proposal", "validation", "assessment"):
                a[stage + "_readings"][case, history] = sensor_drive(signals[stage][:, order], noise[stage][case])
    for field in ("learned_references", "assessment_records", "diagnostic_records"):
        a[field].setflags(write=False)
    metadata = {"phase": phase, "block": block, "ambiguity_pairs_verified": 2 * c}
    for field, label in (("learned_references", "reference"), ("assessment_records", "record"), ("diagnostic_records", "diagnostic")):
        metadata[label + "_sha256_before"] = byte_hash(a[field])
    for case in range(c):
        for history in range(2):
            prior = repair(a["learned_references"][case], a["proposal_readings"][case, history], a["validation_readings"][case, history])
            for target, source in (("reference_candidates", "candidate"), ("reference_selected", "selected"),
                                   ("reference_accepted", "accepted"), ("reference_improvements", "improvements"),
                                   ("reference_gate", "gate"), ("reference_search", "search"),
                                   ("reference_ties", "ties"), ("proposal_covariances", "proposal_covariance")):
                a[target][case, history] = prior[source]
            j = selected_channel(prior["selected"])
            for scheme in range(ns):
                indices = np.tile(np.arange(d), (paths, 1)) if scheme == 2 else np.full((paths, pairs), j, dtype=np.int64)
                a["command_indices"][case, history, scheme] = indices
                a["commands"][case, history, scheme] = SPEC["pulse_amplitude"] * np.eye(d)[indices]
        for cond, (reader_failed, environment_changed, failures) in enumerate(APPARATUS):
            history, target = HISTORY[cond], TARGET[cond]
            reader = a["fault"][case] if reader_failed else identity
            actuators = np.tile(identity, (paths, 1))
            location = int(a["failed_location"][case])
            failed = [] if failures == 0 else [location] if failures == 1 else [p for p in range(paths) if p != location] if failures == 2 else list(range(paths))
            actuators[failed] = a["fault"][case]
            a["actuator_routes"][case, cond] = actuators
            for scheme in range(ns):
                for path in range(paths):
                    actuator = actuators[0 if scheme == 1 else path]
                    a["probe_readings"][case, cond, scheme, path] = observed_pair(
                        a["diagnostic_records"][case, target, path], reader, actuator,
                        a["commands"][case, history, scheme, path], off[case, path], on[case, path])
            proposed = a["reference_selected"][case, history]
            j = selected_channel(proposed)
            decisions = reader_decisions(proposed, j, *a["probe_readings"][case, cond])
            selected = np.tile(identity, (na, 1))
            selected[:5], selected[5], selected[7] = decisions["selected"], proposed, np.argsort(reader)
            a["selected"][case, cond] = selected
            for field, value in decisions.items():
                if field != "selected":
                    a[field][case, cond] = value
            for arm in range(na):
                prediction = a["assessment_readings"][case, history][:, selected[arm]]
                a["errors"][case, cond, arm] = np.mean((prediction - a["assessment_records"][case, target]) ** 2)
                a["edited"][case, cond, arm] = np.any(selected[arm] != identity)
                a["mapping_recovered"][case, cond, arm] = np.array_equal(selected[arm], np.argsort(reader))
    for field, label in (("learned_references", "reference"), ("assessment_records", "record"), ("diagnostic_records", "diagnostic")):
        metadata[label + "_sha256_after"] = byte_hash(a[field])
    return a, metadata


def block_metrics(a):
    return np.stack((a["errors"], a["edited"], a["mapping_recovered"]), axis=-1).mean(axis=0)


def block_diagnostics(a):
    votes = a["path_votes"].sum(axis=-1)
    return {"reference_proposal_counts": np.any(a["reference_candidates"][:, HISTORY] != np.arange(8), axis=-1).sum(axis=0).tolist(),
            "reference_accept_counts": a["reference_accepted"][:, HISTORY].sum(axis=0).tolist(),
            "path_vote_counts": a["path_votes"].sum(axis=0).tolist(),
            "disagreement_counts": ((votes > 0) & (votes < 3)).sum(axis=0).tolist(),
            "pooled_accept_counts": a["pooled_accepted"].sum(axis=0).tolist(),
            "uniform_consensus_counts": a["uniform_consensus"].sum(axis=0).tolist(),
            "failed_location_counts": np.bincount(a["failed_location"], minlength=3).tolist(),
            "command_pair_counts": [[np.bincount(a["command_indices"][:, HISTORY[cond], scheme].ravel(), minlength=8).tolist()
                                     for scheme in range(len(SCHEMES))] for cond in range(len(CONDITIONS))]}
