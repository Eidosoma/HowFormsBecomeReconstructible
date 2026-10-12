from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_read_write_split as study
from laws_confirmation import l17_r_channel as base
from laws_confirmation import l17_r_channel_twelve as chain


@pytest.fixture(scope="module")
def context():
    cfg = replace(study.CONFIG, replicates=2, settle_sweeps=4, imprint_sweeps=8,
                  render_sweeps=4, child_sweeps=12, sample_times=(0,1,12))
    return base.make_context(30042,cfg)


@pytest.fixture(scope="module")
def data(context):
    return study.disposable(context)


@pytest.fixture(scope="module")
def small(context,data):
    return study.experiment(context,data,2)


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1]/"scripts/audit_l17_read_write_split_outputs.py"
    spec = importlib.util.spec_from_file_location("split_independent_tests",path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_and_exact_native_parameters(context):
    assert study.CHECKPOINTS == (1,2,3) and study.TISSUES == tuple(range(10000,10008))
    assert len(study.ARMS) == 7 and len(study.PROBES) == 11
    assert study.REGISTERED_LIVES == 13824 and study.REPLAY_LIVES == 1536
    assert study.WORKERS == 4 and study.CONFIG.sample_times == (0,50,1000)
    assert context["bp"].rho == .002 and context["bp"].c_m == .2


def test_common_bodies_reset_wrong_and_reference_inputs_are_distinct(data):
    states = study.branches(data,2)
    for a,s in states.items():
        for k in ("V","ema"):
            np.testing.assert_array_equal(s[k],data["initial"][k])
            assert not np.shares_memory(s[k],data["initial"][k])
        expected = (data["newborn"]["R"] if a.endswith("reset") else chain.permute_message(data["initial"]["R"],2)
                    if a.endswith("wrong") else data["initial"]["R"])
        np.testing.assert_array_equal(s["R"],expected)
        assert not np.shares_memory(s["R"],expected)


def test_every_reader_exactly_matches_native_engine_without_candidate(context,data,small):
    states = study.branches(data,2)
    for a,tr in small[1].items():
        native = base.simulate(context,states[a],chain.phase(2,"child_development"),12,
            sample_times=(0,1,12),rho=0. if a.startswith("held") else None,c_m=0. if a.startswith("off") else None)
        for t in (0,1,12):
            for k in ("V","ema","R"):
                np.testing.assert_array_equal(tr["snapshots"][t][k],native["snapshots"][t][k])
        assert tr["rng_final_sha256"] == native["rng_final_sha256"]


def test_zero_initialized_candidate_uses_post_step_body_not_working_R(context,data,small):
    for a,tr in small[1].items():
        assert np.all(tr["snapshots"][0]["Q"] == 0.)
        np.testing.assert_array_equal(tr["snapshots"][1]["Q"], .002*tr["snapshots"][1]["V"])
        assert not np.array_equal(tr["final"]["Q"],data["initial"]["R"])
        assert all(tr["gates"].values())
        if a.startswith("held"):
            np.testing.assert_array_equal(tr["snapshots"][0]["R"],tr["final"]["R"])
        else:
            np.testing.assert_allclose(tr["final"]["R"]-tr["final"]["Q"], .998**12*tr["snapshots"][0]["R"],atol=1e-12,rtol=0.)


def test_all_candidate_updates_match_independent_full_body_reconstruction(context,data,small):
    states = study.branches(data,2)
    for a,tr in small[1].items():
        native = base.simulate(context,states[a],chain.phase(2,"child_development"),12,
            sample_times=tuple(range(13)),rho=0. if a.startswith("held") else None,c_m=0. if a.startswith("off") else None)
        q = np.zeros_like(data["initial"]["V"])
        for t in range(1,13):
            q = .998*q + .002*native["snapshots"][t]["V"]
        np.testing.assert_allclose(tr["final"]["Q"],q,atol=1e-14,rtol=0.)


def test_off_development_aliases_V_ema_Q_but_different_R(small):
    left,right = (small[1][a] for a in ("off_correct","off_reset"))
    for t in (0,1,12):
        for k in ("V","ema","Q"):
            np.testing.assert_array_equal(left["snapshots"][t][k],right["snapshots"][t][k])
    np.testing.assert_array_equal(left["body_scores"],right["body_scores"])
    assert not np.array_equal(left["final"]["R"],right["final"]["R"])


def test_only_candidate_enters_matched_fresh_probe_bodies(context,data,small):
    assert set(inspect.signature(study.probe_birth).parameters) == {"newborn","reference"}
    for a,tr in small[2].items():
        for k in ("V","ema"):
            np.testing.assert_array_equal(tr["snapshots"][0][k],data["newborn"][k])
        for state in tr["snapshots"].values():
            np.testing.assert_array_equal(state["R"],tr["snapshots"][0]["R"])
        if a in tuple(f"q_{arm}" for arm in study.ARMS):
            np.testing.assert_array_equal(tr["final"]["R"],small[1][a[2:]]["final"]["Q"])
    for t in (0,1,12):
        for k in ("V","ema"):
            np.testing.assert_array_equal(small[2]["q_held_correct_off"]["snapshots"][t][k],small[2]["zero_off"]["snapshots"][t][k])


def test_complete_gates_and_two_replays(small):
    assert small[0]["passes"] and all(small[0]["structural_gates"].values())
    assert small[0]["structural_gates"]["full_new_development_replay"]
    assert small[0]["structural_gates"]["full_new_candidate_probe_replay"]


def test_historical_anchor_rejects_changed_source_array(context,data,small):
    data = deepcopy(data)
    data["anchor"] = {f"s{t}_{k}":v.copy() for t,s in small[1]["live_correct"]["snapshots"].items() for k,v in s.items() if k != "Q"}
    assert study.experiment(context,data,2)[0]["passes"]
    data["anchor"]["s12_V"][0,0,0] += 1e-7
    with pytest.raises(RuntimeError,match="historical_live_anchor_exact"):
        study.experiment(context,data,2)


def test_generation_streams_change_without_global_rng_mutation(context,data):
    old = deepcopy(np.random.get_state())
    one = study.develop(context,data["initial"],1,"held_correct")
    three = study.develop(context,data["initial"],3,"held_correct")
    assert one["rng_initial_sha256"] != three["rng_initial_sha256"]
    new = np.random.get_state()
    assert old[0] == new[0] and old[2:] == new[2:]
    np.testing.assert_array_equal(old[1],new[1])


def endpoint_records(flags):
    records = []
    for tissue in study.TISSUES:
        for generation in study.CHECKPOINTS:
            f = flags if generation == 2 else (True,True,True)
            summaries = {"candidate": {"held_correct":{"1000":{"reference_true_margin":.5}},
                                      "live_correct":{"1000":{"reference_true_margin":.1 if f[0] else .5}}},
                         "probe":{"q_held_correct":{"1000":{"body_accuracy":1.}},
                                  "q_live_correct":{"1000":{"body_accuracy":.25 if f[1] else 1.}},
                                  "q_held_reset":{"1000":{"body_accuracy":.25 if f[2] else 1.}}}}
            records.append({"tissue":tissue,"generation":generation,"passes":True,"summaries":summaries})
    return records


@pytest.mark.parametrize("flags",[(True,True,True),(False,True,True),(True,False,True),(True,True,False),(False,False,False)])
def test_G2_fixed_three_endpoint_adjudication(flags,independent):
    records = endpoint_records(flags)
    classified = study.classify(records)
    assert classified["label"] == ("READ_WRITE_SEPARATION_IMPROVES_NEW_RECORD" if all(flags) else "NO_QUALIFIED_SPLIT_READER_LEAD")
    cells = [{"tissue":r["tissue"],"generation":r["generation"],"final":{kind:{a:s["1000"] for a,s in group.items()} for kind,group in r["summaries"].items()}} for r in records]
    assert independent.adjudicate(cells,classified)["label"] == classified["label"]
    for n,c in enumerate(classified["co_primary_G2"].values()):
        assert c["quantiles"] == [1/120,119/120] and c["seed"] == 20260907170501+n


def test_classifier_rejects_missing_duplicate_and_failed_cells():
    records = endpoint_records((True,True,True))
    for invalid in ([],records[:-1],records+[records[0]]):
        assert study.classify(invalid)["label"] == "INVALID_STRUCTURAL_FAILURE"
    records[0]["passes"] = False
    assert study.classify(records)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert study.classify(endpoint_records((True,True,True)),False)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_independent_raw_arrays_projection_recurrence_and_tamper_detection(tmp_path,independent):
    cfg = replace(study.CONFIG,settle_sweeps=4,imprint_sweeps=8,render_sweeps=4,child_sweeps=12,sample_times=(0,1,12))
    context = base.make_context(30043,cfg)
    data = study.disposable(context)
    result,developed,probes = study.experiment(context,data,2)
    study.atomic_json(tmp_path/"cell.json",result,tmp_path)
    dev_maps = {a:base.trajectory_arrays(tr)|{"body_scores":tr["body_scores"]} for a,tr in developed.items()}
    probe_maps = {a:base.trajectory_arrays(tr) for a,tr in probes.items()}
    for a,raw in dev_maps.items():
        base.atomic_npz(tmp_path/f"development_{a}.npz",raw,tmp_path)
    for a,raw in probe_maps.items():
        base.atomic_npz(tmp_path/f"probe_{a}.npz",raw,tmp_path)
    dev_maps = {a:chain.load_arrays(tmp_path/f"development_{a}.npz") for a in dev_maps}
    probe_maps = {a:chain.load_arrays(tmp_path/f"probe_{a}.npz") for a in probe_maps}
    saved = json.loads((tmp_path/"cell.json").read_text())
    args = (data,saved,dev_maps,probe_maps,cfg.sample_times)
    assert len(independent.check_cell(*args)) == 75
    # Corrupt an unsaved-step writer input: endpoint-map checks alone miss it.
    dev_maps["held_correct"]["body_scores"][2,0,0] += .01
    with pytest.raises(AssertionError):
        independent.check_cell(*args)
    dev_maps["held_correct"] = chain.load_arrays(tmp_path/"development_held_correct.npz")
    # Detect direct old-R carry into the supposedly empty candidate.
    dev_maps["held_correct"]["s0_Q"][0,0,0] = .01
    with pytest.raises(AssertionError):
        independent.check_cell(*args)
    dev_maps["held_correct"] = chain.load_arrays(tmp_path/"development_held_correct.npz")
    probe_maps["q_held_correct"]["s0_V"][0,0,0] += .01
    with pytest.raises(AssertionError):
        independent.check_cell(*args)


def test_all_real_common_births_match_saved_inputs():
    context = base.make_context(10000,study.CONFIG)
    for generation in study.CHECKPOINTS:
        data = study.load_common(study.external_root(),context,generation)
        for key in ("V","ema","R"):
            np.testing.assert_array_equal(data["initial"][key],data["anchor"][f"s0_{key}"])
        assert base.message_independent(data["newborn"]["V"],8)
    with pytest.raises(ValueError):
        study.load_common(study.external_root(),context,12)


def test_existing_target_blocks_prepare_and_benchmark(tmp_path):
    (tmp_path/"outputs"/study.RUN_ID).mkdir(parents=True)
    for method in (study.prepare,study.benchmark):
        with pytest.raises(FileExistsError):
            method(tmp_path)


def test_prepared_contract_and_tamper_detection(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    path,bench = tmp_path/"contract.txt",study.benchmark_path(tmp_path)
    study.atomic_text(path,"fixed",tmp_path)
    study.atomic_json(bench,{"must_detach":True},tmp_path)
    monkeypatch.setattr(study,"input_paths",lambda root:[path])
    hashes = {str(p):study.sha256_file(p) for p in (path,bench)}
    manifest = {"run_id":study.RUN_ID,"input_sha256":hashes,"contract_digest":study.canonical_digest(hashes),
                "config":asdict(study.CONFIG),"tissues":list(study.TISSUES),"checkpoints":list(study.CHECKPOINTS),
                "arms":list(study.ARMS),"probes":list(study.PROBES),"workers":4}
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_json(run/"STATUS.json",{"status":"PREPARED"},tmp_path)
    assert study.verify_prepared(tmp_path)["workers"] == 4
    for key,value in (("workers",5),("probes",list(study.PROBES)[:-1]),("checkpoints",[1,3])):
        study.atomic_json(run/"MANIFEST.json",manifest|{key:value},tmp_path)
        with pytest.raises(RuntimeError,match="contract changed"):
            study.verify_prepared(tmp_path)
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_text(path,"changed",tmp_path)
    with pytest.raises(RuntimeError,match="contract changed"):
        study.verify_prepared(tmp_path)


def test_long_run_requires_detached_launch(tmp_path,monkeypatch):
    (tmp_path/"runs"/study.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":True}})
    with pytest.raises(RuntimeError,match="detached launch required"):
        study.run_study(tmp_path)
    assert not (tmp_path/"runs"/study.RUN_ID/"EXECUTION.lock").exists()


def test_detach_is_no_poll_and_unique(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    (tmp_path/"logs").mkdir()
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"projected_seconds_four_workers":901}})
    calls = []
    def launch(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(pid=9876)
    monkeypatch.setattr(study.subprocess,"Popen",launch)
    result = study.launch_detached(tmp_path)
    assert result["polling_owner"] == "user" and result["pid"] == 9876
    assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"] == study.subprocess.DEVNULL
    assert (run/"RUN.pid").read_text().strip() == "9876"
    with pytest.raises(FileExistsError):
        study.launch_detached(tmp_path)


def test_runtime_failure_records_sentinel_without_scientific_work(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":False}})
    monkeypatch.setattr(study.base,"runtime",lambda:{"passes":False})
    monkeypatch.setattr(study,"qualify_source",lambda root:{"passes":True})
    monkeypatch.setattr(study,"worker",lambda *args:pytest.fail("must not simulate"))
    with pytest.raises(RuntimeError,match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run/"FAILED").is_file() and not (run/"COMPLETE").exists()
