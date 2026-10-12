"""Independent saved-array and candidate-write projection audit; no new futures."""

import importlib.util
import json
import os
from pathlib import Path

import numpy as np

from laws_confirmation.io import atomic_json, external_root, utc_now, write_hash_manifest


_spec = importlib.util.spec_from_file_location("frozen_centered_audit", Path(__file__).with_name("audit_l17_centered_renewal_outputs.py"))
prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)
independent = prior.independent
RUN_ID = "l17_read_write_split_v1_attempt1"
SOURCE_ID = "l17_centered_renewal_v1_attempt1"
NAIVE_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
PARENT_ID = "l17_r_channel_one_boundary_v1_attempt1"
AUDIT_ID = RUN_ID + "_independent_rescore_v1"
ARMS = ("live_correct", "held_correct", "live_reset", "held_reset", "held_wrong", "off_correct", "off_reset")
PROBES = tuple(f"q_{a}" for a in ARMS) + ("input_held", "zero_held", "q_held_correct_off", "zero_off")


def checked_state(state, rows, summary, codes, data=None):
    args = (data["ancestor"], data["parent"], data) if data else ()
    result = independent.check_snapshot(state, rows, summary, codes, *args)
    for i, row in enumerate(rows):
        v, r = state["V"][i], state["R"][i]
        actual = {"body_mean": float(v.mean()), "body_rms": float(np.sqrt((v*v).mean())), "body_min": float(v.min()),
                  "body_max": float(v.max()), "positive_fraction": float((v > 0).mean()), "active_fraction": float((abs(v) > .2).mean()),
                  "reference_mean": float(r.mean()), "reference_l2_norm": float(np.linalg.norm(r))}
        for key, value in actual.items():
            np.testing.assert_allclose(row[key], value, rtol=0., atol=1e-14)
    for key in ("body_mean", "body_rms", "body_min", "body_max", "positive_fraction", "reference_mean"):
        np.testing.assert_allclose(summary[key], np.mean([r[key] for r in rows]), rtol=0., atol=1e-15)
    scores, _ = independent.probabilities(state["R"], codes)
    labels = np.repeat(np.arange(4), 8)
    result["reference_true_margin"] = float(np.mean([scores[i,m] - max(np.delete(scores[i],m)) for i,m in enumerate(labels)]))
    return result


def check_cell(data, saved, development, probes, times=(0, 50, 1000)):
    assert saved["passes"] and all(saved["structural_gates"].values())
    assert set(development) == set(ARMS) and set(probes) == set(PROBES)
    for name in ("initial", "parent", "ancestor", "newborn"):
        assert prior.state_hash(data[name]) == saved["source_sha256"][name]
    for value in data["newborn"].values():
        grouped = value.reshape(4, 8, 16, 16)
        assert all(np.array_equal(grouped[0], grouped[m]) for m in range(1,4))
    stages, codes = [], prior.templates()
    for arm, raw in development.items():
        assert set(raw) == {f"s{t}_{k}" for t in times for k in ("V", "ema", "R", "Q")} | {"body_scores"}
        expected_r = (data["newborn"]["R"] if arm.endswith("reset") else
                      np.concatenate((data["initial"]["R"][8:], data["initial"]["R"][:8])) if arm.endswith("wrong") else data["initial"]["R"])
        for k in ("V", "ema"):
            np.testing.assert_array_equal(raw[f"s0_{k}"], data["initial"][k])
        np.testing.assert_array_equal(raw["s0_R"], expected_r)
        assert prior.state_hash({k:raw[f"s0_{k}"] for k in ("V", "ema", "R")}) == saved["birth_sha256"][arm]
        assert np.all(raw["s0_Q"] == 0.)
        trace = raw["body_scores"]
        assert trace.shape == (times[-1]+1, 32, 4) and np.isfinite(trace).all()
        # Independently integrate the passive writer's message projections.
        q_scores = np.zeros((32,4))
        written = {0:q_scores.copy()}
        for sweep in range(1, times[-1]+1):
            q_scores = .998 * q_scores + .002 * trace[sweep]
            if sweep in times:
                written[sweep] = q_scores.copy()
        assert not np.array_equal(raw[f"s{times[-1]}_Q"], raw["s0_Q"])
        for sweep in times:
            actual_body_scores, _ = independent.probabilities(raw[f"s{sweep}_V"], codes)
            actual_q_scores, _ = independent.probabilities(raw[f"s{sweep}_Q"], codes)
            np.testing.assert_allclose(actual_body_scores, trace[sweep], rtol=0., atol=1e-12)
            np.testing.assert_allclose(actual_q_scores, written[sweep], rtol=0., atol=1e-12)
            if arm.startswith("held"):
                np.testing.assert_array_equal(raw[f"s{sweep}_R"], expected_r)
            else:
                np.testing.assert_allclose(raw[f"s{sweep}_R"]-raw[f"s{sweep}_Q"], .998**sweep*expected_r, rtol=0., atol=1e-12)
            if arm.startswith("off"):
                for k in ("V", "ema", "Q"):
                    np.testing.assert_array_equal(raw[f"s{sweep}_{k}"], development["off_reset"][f"s{sweep}_{k}"])
            for kind, reference in (("working", "R"), ("candidate", "Q")):
                state = {"V":raw[f"s{sweep}_V"], "ema":raw[f"s{sweep}_ema"], "R":raw[f"s{sweep}_{reference}"]}
                rows = [r for r in saved["rows"][kind][arm] if r["sweep"] == sweep]
                result = checked_state(state, rows, saved["summaries"][kind][arm][str(sweep)], codes, data)
                stages.append({"kind":kind, "arm":arm, "sweep":sweep, **result})
        checks = saved["development_checks"][arm]
        assert all(checks["gates"].values()) and all(v < 1e-12 for v in checks["accumulator_errors"].values())
        assert all(v < 1e-12 for v in checks["carry_errors"].values())
    np.testing.assert_array_equal(development["off_correct"]["body_scores"], development["off_reset"]["body_scores"])
    for arm, raw in probes.items():
        assert set(raw) == {f"s{t}_{k}" for t in times for k in ("V", "ema", "R")}
        if arm in ("zero_held", "zero_off"):
            expected = np.zeros_like(data["initial"]["R"])
        elif arm == "input_held":
            expected = data["initial"]["R"]
        else:
            donor = "held_correct" if arm == "q_held_correct_off" else arm.removeprefix("q_")
            expected = development[donor][f"s{times[-1]}_Q"]
        for key in ("V", "ema"):
            np.testing.assert_array_equal(raw[f"s0_{key}"], data["newborn"][key])
        assert saved["probe_reference_links"][arm] == {"reference_sha256":independent.digest(expected), "birth_sha256":independent.digest(expected)}
        for sweep in times:
            state = {k:raw[f"s{sweep}_{k}"] for k in ("V", "ema", "R")}
            np.testing.assert_array_equal(state["R"], expected)
            rows = [r for r in saved["rows"]["probe"][arm] if r["sweep"] == sweep]
            result = checked_state(state, rows, saved["summaries"]["probe"][arm][str(sweep)], codes)
            if arm in ("q_held_correct_off", "zero_off"):
                assert result["body_accuracy"] == .25
                for key in ("V", "ema"):
                    np.testing.assert_array_equal(state[key], probes["zero_off"][f"s{sweep}_{key}"])
            stages.append({"kind":"probe", "arm":arm, "sweep":sweep, **result})
    return stages


def adjudicate(cells, saved):
    assert [(r["tissue"],r["generation"]) for r in cells] == [(t,g) for t in range(10000,10008) for g in (1,2,3)]
    selected = [r["final"] for r in cells if r["generation"] == 2]
    contrasts = {}
    endpoints = (("candidate_margin", "candidate", "held_correct", "live_correct", "reference_true_margin"),
                 ("candidate_readout", "probe", "q_held_correct", "q_live_correct", "body_accuracy"),
                 ("reference_contribution", "probe", "q_held_correct", "q_held_reset", "body_accuracy"))
    for n, (name,kind,left,right,metric) in enumerate(endpoints):
        values = np.asarray([s[kind][left][metric] - s[kind][right][metric] for s in selected])
        seed = 20260907170501+n
        draws = np.random.default_rng(seed).integers(0,8,(10000,8))
        interval = np.quantile(values[draws].mean(axis=1), [1/120,119/120]).tolist()
        positive = int((values > 0).sum())
        supported = interval[0] > 0 and positive >= 6
        recorded = saved["co_primary_G2"][name]
        for key,value in (("mean",float(values.mean())), ("tissue_differences",values.tolist()), ("paired_tissue_interval",interval)):
            np.testing.assert_allclose(recorded[key], value, rtol=0., atol=1e-12)
        assert recorded["supported"] == supported and recorded["positive_tissues"] == positive
        assert recorded["seed"] == seed and recorded["resamples"] == 10000 and recorded["quantiles"] == [1/120,119/120]
        contrasts[name] = {"mean":float(values.mean()), "tissue_differences":values.tolist(), "interval":interval,
                           "positive_tissues":positive, "supported":supported}
    label = "READ_WRITE_SEPARATION_IMPROVES_NEW_RECORD" if all(c["supported"] for c in contrasts.values()) else "NO_QUALIFIED_SPLIT_READER_LEAD"
    assert label == saved["label"]
    return {"label":label, "co_primary_G2":contrasts}


def main():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k) == "1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"))
    root = external_root()
    source, output, run = root/"outputs"/RUN_ID, root/"outputs"/AUDIT_ID, root/"runs"/RUN_ID
    if output.exists():
        raise FileExistsError("immutable audit already exists")
    status = json.loads((run/"STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["completed_cleanly"]
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    inputs, outputs = independent.manifest_check(source/"input_hashes.sha256"), independent.manifest_check(source/"output_hashes.sha256")
    study = json.loads((source/"read_write_split.json").read_text())
    assert study["completed_cleanly"] and all(study["completion_gates"].values())
    assert [(r["tissue"],r["generation"]) for r in study["results"]] == [(t,g) for t in range(10000,10008) for g in (1,2,3)]
    stages, cells, calibration = [], [], []
    for tissue in range(10000,10008):
        positive = []
        for generation in (1,2,3):
            directory = source/f"tissue_{tissue}"/f"g{generation:02d}"
            raw_common = independent.arrays(directory/"common.npz")
            data = {name:{k:raw_common[f"{name}_{k}"] for k in ("V","ema","R")} for name in ("initial","parent","ancestor","newborn")}
            data.update({k:raw_common[k] for k in ("fresh","counts")})
            saved = json.loads((directory/"cell.json").read_text())
            assert {k:v for k,v in saved.items() if k != "rows"} == study["results"][(tissue-10000)*3+generation-1]
            old = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"/f"g{generation:02d}"
            anchor = independent.arrays(old/"centered_copy_live_states.npz")
            previous = (independent.arrays(old.parent/f"g{generation-1:02d}"/"centered_copy_live_states.npz") if generation > 1 else None)
            ancestor = independent.arrays(root/"outputs"/PARENT_ID/f"tissue_{tissue}"/"parent_states.npz")
            naive_directory = root/"outputs"/NAIVE_ID/f"tissue_{tissue}"/f"g{generation:02d}"
            naive = independent.arrays(naive_directory/"newborn.npz")
            cal = json.loads((naive_directory/"calibration.json").read_text())
            positive.append(cal["positive_accuracy"])
            growth = independent.arrays(old/"births.npz")
            for k in ("V","ema","R"):
                np.testing.assert_array_equal(data["initial"][k],anchor[f"s0_{k}"])
                np.testing.assert_array_equal(data["parent"][k], previous[f"s1000_{k}"] if previous else ancestor[f"after_render_{k}"])
                np.testing.assert_array_equal(data["ancestor"][k],ancestor[f"after_render_{k}"])
                np.testing.assert_array_equal(data["newborn"][k],naive[k])
            for k in ("fresh","counts"):
                np.testing.assert_array_equal(data[k],growth[k])
            dev = {a:independent.arrays(directory/f"development_{a}.npz") for a in ARMS}
            probes = {a:independent.arrays(directory/f"probe_{a}.npz") for a in PROBES}
            for k,value in anchor.items():
                np.testing.assert_array_equal(dev["live_correct"][k],value)
            checked = check_cell(data,saved,dev,probes)
            stages.extend({"tissue":tissue,"generation":generation,**r} for r in checked)
            final = {kind:{r["arm"]:r for r in checked if r["kind"] == kind and r["sweep"] == 1000} for kind in ("working","candidate","probe")}
            cells.append({"tissue":tissue,"generation":generation,"final":final})
        calibration.append(positive)
        print(f"independent read/write split audit: tissue {tissue} verified",flush=True)
    cal = np.asarray(calibration)
    assert (cal > .25).all() and (cal.mean(axis=0) >= .75).all()
    classification = adjudicate(cells,study["classification"])
    assert len(stages) == 1800
    assert independent.manifest_check(source/"input_hashes.sha256") == inputs
    assert independent.manifest_check(source/"output_hashes.sha256") == outputs
    record = {"run_id":AUDIT_ID,"source_run":RUN_ID,"checked_utc":utc_now(),"passes":True,
              "source_input_hashes_verified":inputs,"source_output_hashes_verified":outputs,
              "raw_state_snapshots_rescored":1296,"field_views_rescored":len(stages),"world_rows_rescored":len(stages)*32,
              "candidate_projection_updates_reconstructed":24*7*1000,"classification":classification,
              "stages":stages,"cells":cells,"new_simulations":0}
    output.mkdir(parents=True)
    atomic_json(output/"rescore.json",record,root)
    write_hash_manifest([Path(__file__).resolve(),Path(prior.__file__).resolve(),Path(independent.__file__).resolve(),
                         source/"input_hashes.sha256",source/"output_hashes.sha256",run/"STATUS.json",run/"COMPLETE"],output/"input_hashes.sha256",root)
    write_hash_manifest([output/"rescore.json",output/"input_hashes.sha256"],output/"output_hashes.sha256",root)
    print(json.dumps({k:v for k,v in record.items() if k not in ("stages","cells")},indent=2))


if __name__ == "__main__":
    main()
