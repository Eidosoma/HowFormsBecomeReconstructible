"""Independent packet-link, raw-map and writer-projection audit; no new futures."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

from laws_confirmation.io import atomic_json, canonical_digest, external_root, utc_now, write_hash_manifest


_spec = importlib.util.spec_from_file_location("frozen_split_audit", Path(__file__).with_name("audit_l17_read_write_split_outputs.py"))
prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)
independent, helpers = prior.independent, prior.prior
RUN_ID = "l17_replacement_chain_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
NAIVE_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
PARENT_ID = "l17_r_channel_one_boundary_v1_attempt1"
ARMS = ("split_replace", "split_reset", "split_wrong", "split_off", "reset_off", "coupled_replace", "native_carry", "native_reset", "protected_copy")
HELD = ("split_replace", "split_reset", "split_wrong", "protected_copy")
RESET = ("split_reset", "reset_off", "native_reset")
COPY = ("native_carry", "protected_copy")
PROBES = ("q_split", "q_reset", "q_coupled", "q_reader_off", "q_wrong", "q_split_off", "zero_off")


def packet_hash(reference):
    assert reference.dtype == np.dtype("float64") and reference.shape == (32, 16, 16) and np.isfinite(reference).all()
    return hashlib.sha256(reference.tobytes(order="C")).hexdigest()


def donor(reference):
    return np.concatenate((reference[8:], reference[:8]))


def message_independent(reference):
    grouped = reference.reshape(4, 8, 16, 16)
    return all(np.array_equal(grouped[0], grouped[m]) for m in range(1, 4))


def development_hash(raw, saved, arm, times):
    snapshots = {str(t): helpers.state_hash({k: raw[f"s{t}_{k}"] for k in ("V", "ema", "R", "Q")}) for t in times}
    metadata = saved["development_checks"][arm]
    return canonical_digest({"snapshots": snapshots, "body_scores": independent.digest(raw["body_scores"]),
        "initial_sha256": helpers.state_hash({k: raw[f"s0_{k}"] for k in ("V", "ema", "R")}),
        "rng_initial_sha256": saved["rng_initial_sha256"], "rng_final_sha256": saved["rng_final_sha256"], **metadata})


def check_generation(newborn, previous, saved, development, times=(0, 50, 1000)):
    assert saved["passes"] and all(saved["structural_gates"].values())
    assert set(development) == set(previous) == set(ARMS)
    assert helpers.state_hash(newborn) == saved["newborn_sha256"]
    assert all(message_independent(v) for v in newborn.values())
    stages, outgoing, codes = [], {}, helpers.templates()
    for arm, raw in development.items():
        assert set(raw) == {f"s{t}_{k}" for t in times for k in ("V", "ema", "R", "Q")} | {"body_scores"}
        expected = newborn["R"] if arm in RESET else previous[arm]
        assert saved["upstream_packet_sha256"][arm] == packet_hash(previous[arm])
        assert saved["received_packet_sha256"][arm] == packet_hash(expected)
        for k in ("V", "ema"):
            np.testing.assert_array_equal(raw[f"s0_{k}"], newborn[k])
        np.testing.assert_array_equal(raw["s0_R"], expected)
        assert helpers.state_hash({k: raw[f"s0_{k}"] for k in ("V", "ema", "R")}) == saved["birth_sha256"][arm]
        assert np.all(raw["s0_Q"] == 0.)
        assert not np.array_equal(raw[f"s{times[-1]}_Q"], raw["s0_Q"])
        trace = raw["body_scores"]
        assert trace.shape == (times[-1]+1, 32, 4) and np.isfinite(trace).all()
        # Evaluator projections, independently integrated with no R0 carry term.
        q_scores, written = np.zeros((32, 4)), {0: np.zeros((32, 4))}
        for sweep in range(1, times[-1]+1):
            q_scores = .998*q_scores + .002*trace[sweep]
            if sweep in times:
                written[sweep] = q_scores.copy()
        for sweep in times:
            body_scores, _ = independent.probabilities(raw[f"s{sweep}_V"], codes)
            candidate_scores, _ = independent.probabilities(raw[f"s{sweep}_Q"], codes)
            np.testing.assert_allclose(body_scores, trace[sweep], rtol=0., atol=1e-12)
            np.testing.assert_allclose(candidate_scores, written[sweep], rtol=0., atol=1e-12)
            if arm in HELD:
                np.testing.assert_array_equal(raw[f"s{sweep}_R"], expected)
            else:
                np.testing.assert_allclose(raw[f"s{sweep}_R"]-raw[f"s{sweep}_Q"], .998**sweep*expected, rtol=0., atol=1e-12)
            if arm == "split_off":
                for k in ("V", "ema", "Q"):
                    np.testing.assert_array_equal(raw[f"s{sweep}_{k}"], development["reset_off"][f"s{sweep}_{k}"])
            if arm == "split_wrong":
                for k in ("V", "ema", "R", "Q"):
                    np.testing.assert_array_equal(raw[f"s{sweep}_{k}"], donor(development["split_replace"][f"s{sweep}_{k}"]))
            for kind, field in (("working", "R"), ("candidate", "Q")):
                state = {"V": raw[f"s{sweep}_V"], "ema": raw[f"s{sweep}_ema"], "R": raw[f"s{sweep}_{field}"]}
                rows = [r for r in saved["rows"][kind][arm] if r["sweep"] == sweep]
                result = prior.checked_state(state, rows, saved["summaries"][kind][arm][str(sweep)], codes)
                if arm in (*RESET, "split_off"):
                    assert result["body_accuracy"] == .25 and message_independent(state["V"])
                stages.append({"kind": kind, "arm": arm, "sweep": sweep, **result})
        field = "R" if arm in COPY else "Q"
        assert saved["outgoing_field"][arm] == field
        outgoing[arm] = raw[f"s{times[-1]}_{field}"].copy()
        assert packet_hash(outgoing[arm]) == saved["outgoing_packet_sha256"][arm]
        checks = saved["development_checks"][arm]
        assert all(checks["gates"].values()) and all(v < 1e-12 for v in checks["accumulator_errors"].values())
        assert all(v < 1e-12 for v in checks["carry_errors"].values())
        assert development_hash(raw, saved, arm, times) == saved["development_sha256"][arm]
    np.testing.assert_array_equal(development["split_off"]["body_scores"], development["reset_off"]["body_scores"])
    np.testing.assert_array_equal(outgoing["protected_copy"], previous["protected_copy"])
    assert saved["replay_received_packet_sha256"] == packet_hash(previous["split_replace"])
    assert saved["replay_outgoing_packet_sha256"] == packet_hash(outgoing["split_replace"])
    assert saved["replay_development_sha256"] == saved["development_sha256"]["split_replace"]
    return stages, outgoing


def check_terminal(newborn, outgoing, saved, probes, times=(0, 50, 1000)):
    assert saved["passes"] and all(saved["structural_gates"].values()) and set(probes) == set(PROBES)
    assert saved["newborn_sha256"] == helpers.state_hash(newborn)
    donors = {"q_split": "split_replace", "q_reset": "split_reset", "q_coupled": "coupled_replace",
              "q_reader_off": "split_off", "q_wrong": "split_wrong", "q_split_off": "split_replace"}
    stages, codes = [], helpers.templates()
    for arm, raw in probes.items():
        assert set(raw) == {f"s{t}_{k}" for t in times for k in ("V", "ema", "R")}
        expected = np.zeros_like(newborn["R"]) if arm == "zero_off" else outgoing[donors[arm]]
        assert packet_hash(expected) == saved["received_packet_sha256"][arm]
        for k in ("V", "ema"):
            np.testing.assert_array_equal(raw[f"s0_{k}"], newborn[k])
        for sweep in times:
            state = {k: raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
            np.testing.assert_array_equal(state["R"], expected)
            rows = [r for r in saved["rows"][arm] if r["sweep"] == sweep]
            result = prior.checked_state(state, rows, saved["summaries"][arm][str(sweep)], codes)
            if arm in ("q_split_off", "zero_off", "q_reset", "q_reader_off"):
                assert result["body_accuracy"] == .25 and message_independent(state["V"])
            if arm == "q_split_off":
                for k in ("V", "ema"):
                    np.testing.assert_array_equal(state[k], probes["zero_off"][f"s{sweep}_{k}"])
            if arm == "q_wrong":
                for k in ("V", "ema", "R"):
                    np.testing.assert_array_equal(state[k], donor(probes["q_split"][f"s{sweep}_{k}"]))
            stages.append({"kind": "terminal", "arm": arm, "sweep": sweep, **result})
    assert saved["replay_received_packet_sha256"] == packet_hash(outgoing["split_replace"])
    assert saved["replay_probe_sha256"] == saved["probe_sha256"]["q_split"]
    return stages


def adjudicate(cells, saved):
    assert [r["tissue"] for r in cells] == list(range(10000, 10008))
    assert all([r["generation"] for r in cell["generations"]] == list(range(1, 13)) for cell in cells)
    endpoints = (("body_vs_reset", "generation", "split_replace", "split_reset"),
                 ("new_record_readout_vs_reset", "terminal", "q_split", "q_reset"),
                 ("new_record_readout_vs_reader_off", "terminal", "q_split", "q_split_off"))
    contrasts = {}
    for n, (name, kind, left, right) in enumerate(endpoints):
        groups = [r["generations"][-1]["final"]["working"] if kind == "generation" else r["terminal"] for r in cells]
        values = np.asarray([s[left]["body_accuracy"]-s[right]["body_accuracy"] for s in groups])
        seed = 20260907183001+n
        draws = np.random.default_rng(seed).integers(0, 8, (10000, 8))
        interval = np.quantile(values[draws].mean(axis=1), [1/120, 119/120]).tolist()
        positive = int((values > 0).sum())
        supported = interval[0] > 0 and positive >= 6
        recorded = saved["co_primary_G12"][name]
        for key, value in (("mean", float(values.mean())), ("tissue_differences", values.tolist()), ("paired_tissue_interval", interval)):
            np.testing.assert_allclose(recorded[key], value, rtol=0., atol=1e-12)
        assert recorded["supported"] == supported and recorded["positive_tissues"] == positive
        assert recorded["seed"] == seed and recorded["resamples"] == 10000 and recorded["quantiles"] == [1/120, 119/120]
        contrasts[name] = {"mean": float(values.mean()), "tissue_differences": values.tolist(), "interval": interval, "positive_tissues": positive, "supported": supported}
    protected = np.asarray([[g["final"]["working"]["protected_copy"]["body_accuracy"] for g in r["generations"]] for r in cells])
    qualified = bool((protected > .25).all() and (protected.mean(axis=0) >= .75).all())
    np.testing.assert_array_equal(protected, saved["protected_control_per_tissue_generation"])
    assert qualified == saved["protected_control_qualified"]
    label = ("NO_QUALIFIED_PROTECTED_REFERENCE_CONTROL" if not qualified else
             "QUALIFIED_TWELVE_GENERATION_REPLACEMENT" if all(c["supported"] for c in contrasts.values()) else "NO_QUALIFIED_REPLACEMENT_LEAD")
    assert label == saved["label"]
    return {"label": label, "co_primary_G12": contrasts, "protected_control_qualified": qualified}


def main():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k) == "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"))
    root = external_root()
    source, output, run = root/"outputs"/RUN_ID, root/"outputs"/AUDIT_ID, root/"runs"/RUN_ID
    if output.exists():
        raise FileExistsError("immutable audit already exists")
    status = json.loads((run/"STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"] and (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    inputs, outputs = independent.manifest_check(source/"input_hashes.sha256"), independent.manifest_check(source/"output_hashes.sha256")
    study = json.loads((source/"replacement_chain.json").read_text())
    assert study["completed_cleanly"] and all(study["completion_gates"].values())
    assert study["scientific_lives"] == 29440 and study["replay_lives"] == 3328
    assert [r["tissue"] for r in study["results"]] == list(range(10000, 10008))
    stages, cells, calibration = [], [], []
    for tissue in range(10000, 10008):
        directory = source/f"tissue_{tissue}"
        lineage = json.loads((directory/"lineage.json").read_text())
        assert lineage == study["results"][tissue-10000] and lineage["passes"]
        original = independent.arrays(root/"outputs"/PARENT_ID/f"tissue_{tissue}"/"parent_states.npz")["after_render_R"]
        assert lineage["seed_packet_sha256"] == packet_hash(original)
        previous = {a: donor(original) if a == "split_wrong" else original.copy() for a in ARMS}
        generations, positive = [], []
        for g in range(1, 13):
            gd, old = directory/f"g{g:02d}", root/"outputs"/NAIVE_ID/f"tissue_{tissue}"/f"g{g:02d}"
            newborn = independent.arrays(gd/"newborn.npz")
            naive = independent.arrays(old/"newborn.npz")
            assert set(newborn) == set(naive) == {"V", "ema", "R"}
            for k in naive:
                np.testing.assert_array_equal(newborn[k], naive[k])
            cal = json.loads((old/"calibration.json").read_text())
            assert cal["newborn_sha256"] == helpers.state_hash(newborn)
            positive.append(cal["positive_accuracy"])
            saved = json.loads((gd/"generation.json").read_text())
            assert saved["tissue"] == tissue and saved["generation"] == g
            assert {k: v for k, v in saved.items() if k != "rows"} == lineage["generations"][g-1]
            development = {a: independent.arrays(gd/f"development_{a}.npz") for a in ARMS}
            for arm, name in (("native_carry", "fresh_renew"), ("native_reset", "fresh_reset")):
                anchor = independent.arrays(old/f"{name}_states.npz")
                assert set(anchor) == {f"s{t}_{k}" for t in (0, 50, 1000) for k in ("V", "ema", "R")}
                for k, value in anchor.items():
                    np.testing.assert_array_equal(development[arm][k], value)
            checked, previous = check_generation(newborn, previous, saved, development)
            stages.extend({"tissue": tissue, "generation": g, **r} for r in checked)
            final = {kind: {r["arm"]: r for r in checked if r["kind"] == kind and r["sweep"] == 1000} for kind in ("working", "candidate")}
            generations.append({"generation": g, "final": final})
        readout = json.loads((directory/"terminal"/"readout.json").read_text())
        assert {k: v for k, v in readout.items() if k != "rows"} == lineage["terminal"]
        probes = {a: independent.arrays(directory/"terminal"/f"probe_{a}.npz") for a in PROBES}
        checked = check_terminal(newborn, previous, readout, probes)
        stages.extend({"tissue": tissue, "generation": "terminal_nonrenewing", **r} for r in checked)
        cells.append({"tissue": tissue, "generations": generations, "terminal": {r["arm"]: r for r in checked if r["sweep"] == 1000}})
        calibration.append(positive)
        print(f"independent replacement audit: tissue {tissue} verified", flush=True)
    scores = np.asarray(calibration)
    assert (scores > .25).all() and (scores.mean(axis=0) >= .75).all()
    classification = adjudicate(cells, study["classification"])
    assert len(stages) == 5352
    assert independent.manifest_check(source/"input_hashes.sha256") == inputs
    assert independent.manifest_check(source/"output_hashes.sha256") == outputs
    record = {"run_id": AUDIT_ID, "source_run": RUN_ID, "checked_utc": utc_now(), "passes": True,
              "source_input_hashes_verified": inputs, "source_output_hashes_verified": outputs,
              "raw_state_snapshots_rescored": 2760, "field_views_rescored": len(stages), "world_rows_rescored": len(stages)*32,
              "serial_arm_boundary_links": 864, "terminal_packet_links": 56,
              "candidate_projection_updates_reconstructed": 864000, "classification": classification,
              "stages": stages, "cells": cells, "new_simulations": 0}
    output.mkdir(parents=True)
    atomic_json(output/"rescore.json", record, root)
    write_hash_manifest([Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(helpers.__file__).resolve(), Path(independent.__file__).resolve(),
                         source/"input_hashes.sha256", source/"output_hashes.sha256", run/"MANIFEST.json", run/"STATUS.json", run/"COMPLETE"], output/"input_hashes.sha256", root)
    write_hash_manifest([output/"rescore.json", output/"input_hashes.sha256"], output/"output_hashes.sha256", root)
    print(json.dumps({k: v for k, v in record.items() if k not in ("stages", "cells")}, indent=2))


if __name__ == "__main__":
    main()
