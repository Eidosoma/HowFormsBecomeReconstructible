from copy import deepcopy
from dataclasses import replace
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_replacement_chain as study
from laws_confirmation import l17_r_channel as base
from laws_confirmation import l17_r_channel_twelve as chain


@pytest.fixture(scope="module")
def context():
    cfg = replace(study.CONFIG, generations=3, replicates=8, settle_sweeps=4,
                  imprint_sweeps=8, render_sweeps=4, child_sweeps=12, sample_times=(0, 1, 12))
    return base.make_context(30044, cfg)


@pytest.fixture(scope="module")
def sources(context):
    seed = study.serialize(base.teach_parent(context)["after_render"]["R"])
    newborns = [base.naive_body(context, chain.phase(g, "fresh_body_birth")) for g in (1, 2, 3)]
    return seed, newborns


@pytest.fixture(scope="module")
def small(context, sources):
    seed, newborns = sources
    packets, replay = study.initial_packets(seed, newborns[0], 8), seed
    generations = []
    for g, newborn in enumerate(newborns, 1):
        incoming = packets.copy()
        record, packets, replay, developed = study.generation(context, packets, newborn, g, replay)
        generations.append((incoming, record, packets.copy(), developed))
    terminal, probes = study.terminal(context, packets, newborns[-1], replay)
    return generations, terminal, probes


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1]/"scripts/audit_l17_replacement_chain_outputs.py"
    spec = importlib.util.spec_from_file_location("replacement_independent_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_horizon_packet_and_native_parameters(context):
    assert study.TISSUES == tuple(range(10000, 10008)) and study.CONFIG.generations == 12
    assert len(study.ARMS) == 9 and len(study.PROBES) == 7
    assert study.REGISTERED_LIVES == 29440 and study.REPLAY_LIVES == 3328
    assert study.WORKERS == 4 and study.CONFIG.sample_times == (0, 50, 1000)
    assert context["bp"].rho == .002 and context["bp"].c_m == .2
    assert study.contract()["packet_bytes_per_world"] == 2048
    assert study.contract()["terminal_nonrenewing_readouts"] == 1


def test_boundary_has_only_public_naive_body_and_exact_byte_packet(sources):
    seed, newborns = sources
    assert set(inspect.signature(study.birth).parameters) == {"newborn", "packet"}
    assert type(seed) is bytes and len(seed) == 32*2048
    state = study.birth(newborns[0], seed)
    assert set(state) == {"V", "ema", "R"}
    for k in ("V", "ema"):
        np.testing.assert_array_equal(state[k], newborns[0][k])
        assert not np.shares_memory(state[k], newborns[0][k])
    assert study.serialize(state["R"]) == seed
    state["R"][:] = 99.
    assert study.serialize(study.birth(newborns[0], seed)["R"]) == seed
    for invalid in (seed[:-8], seed+seed, bytearray(seed), state["R"]):
        with pytest.raises(ValueError):
            study.birth(newborns[0], invalid)
    with pytest.raises(ValueError):
        study.serialize(np.zeros((32, 16, 16), dtype=np.float32))
    with pytest.raises(ValueError):
        study.birth(newborns[0], np.full((32, 16, 16), np.nan).tobytes())


def test_Q_only_serial_replacement_and_no_body_carry(sources, small):
    seed, newborns = sources
    for i, (incoming, record, outgoing, developed) in enumerate(small[0]):
        for arm, tr in developed.items():
            assert all(tr["gates"].values()) and np.all(tr["snapshots"][0]["Q"] == 0.)
            np.testing.assert_array_equal(tr["snapshots"][1]["Q"], .002*tr["snapshots"][1]["V"])
            for k in ("V", "ema"):
                np.testing.assert_array_equal(tr["snapshots"][0][k], newborns[i][k])
            expected = study.serialize(newborns[i]["R"]) if arm in study.RESET_ARMS else incoming[arm]
            assert study.serialize(tr["snapshots"][0]["R"]) == expected
            field = "R" if arm in study.COPY_ARMS else "Q"
            assert outgoing[arm] == study.serialize(tr["final"][field])
            if i:
                assert incoming[arm] == small[0][i-1][2][arm]
        assert outgoing["protected_copy"] == seed
        assert outgoing["split_replace"] != seed
        assert record["replay_outgoing_packet_sha256"] == study.packet_hash(outgoing["split_replace"])


def test_wrong_seed_only_once_off_aliases_and_different_control_storage(small):
    for _, record, outgoing, developed in small[0]:
        assert all(record["structural_gates"].values())
        for t in (0, 1, 12):
            for k in ("V", "ema", "R", "Q"):
                np.testing.assert_array_equal(developed["split_wrong"]["snapshots"][t][k], chain.permute_message(developed["split_replace"]["snapshots"][t][k], 8))
            for k in ("V", "ema", "Q"):
                np.testing.assert_array_equal(developed["split_off"]["snapshots"][t][k], developed["reset_off"]["snapshots"][t][k])
        assert outgoing["native_carry"] != study.serialize(developed["native_carry"]["final"]["Q"])


def test_all_arms_match_native_body_and_full_independent_candidate(context, sources, small):
    newborn = sources[1][0]
    incoming, _, _, developed = small[0][0]
    for a, tr in developed.items():
        packet = study.serialize(newborn["R"]) if a in study.RESET_ARMS else incoming[a]
        mode = study.MODES[a]
        native = base.simulate(context, study.birth(newborn, packet), chain.phase(1, "child_development"), 12,
            sample_times=tuple(range(13)), rho=0. if mode.startswith("held") else None, c_m=0. if mode.startswith("off") else None)
        q = np.zeros_like(newborn["V"])
        for t in range(1, 13):
            q = .998*q + .002*native["snapshots"][t]["V"]
        np.testing.assert_allclose(tr["final"]["Q"], q, atol=1e-14, rtol=0.)
        for t in (0, 1, 12):
            for k in ("V", "ema", "R"):
                np.testing.assert_array_equal(tr["snapshots"][t][k], native["snapshots"][t][k])


def test_terminal_reads_Q12_in_fresh_body_and_really_disables_only_assay_reader(sources, small):
    outgoing = small[0][-1][2]
    newborn = sources[1][-1]
    record, assays = small[1:]
    assert all(record["structural_gates"].values())
    for a, tr in assays.items():
        donor = study.PROBE_DONORS[a]
        expected = study.serialize(np.zeros_like(newborn["R"])) if donor is None else outgoing[donor]
        for k in ("V", "ema"):
            np.testing.assert_array_equal(tr["snapshots"][0][k], newborn[k])
        for state in tr["snapshots"].values():
            assert study.serialize(state["R"]) == expected
    assert record["probe_sha256"]["q_split"] == record["replay_probe_sha256"]


def test_own_replay_corruption_and_historical_anchor_tamper_detected(context, sources, small):
    seed, newborns = sources
    incoming = small[0][1][0]
    with pytest.raises(RuntimeError, match="full_own_packet_replay"):
        study.generation(context, incoming, newborns[1], 2, seed)
    incoming, _, _, developed = small[0][0]
    anchors = {a: {f"s{t}_{k}": tr["snapshots"][t][k].copy() for t in (0, 1, 12) for k in ("V", "ema", "R")}
               for a, tr in developed.items() if a in study.ANCHORS}
    assert study.generation(context, incoming, newborns[0], 1, seed, anchors)[0]["passes"]
    anchors["native_carry"]["s12_R"][0, 0, 0] += .01
    with pytest.raises(RuntimeError, match="historical_native_anchors"):
        study.generation(context, incoming, newborns[0], 1, seed, anchors)


def test_full_lineage_replays_own_serial_outputs_without_mutating_rulebook(context, sources, small, monkeypatch):
    seed, newborns = sources
    calls, original = [], study.generation
    theta_hash = base.array_digest(context["theta"])
    global_rng = deepcopy(np.random.get_state())
    def tracked(ctx, packets, newborn, number, replay_packet, anchors=None):
        calls.append((number, replay_packet))
        return original(ctx, packets, newborn, number, replay_packet, anchors)
    monkeypatch.setattr(study, "generation", tracked)
    result = study.lineage(context, seed, newborns)
    assert result["passes"] and len(calls) == 3
    assert calls[0][1] == seed
    for g in (2, 3):
        assert calls[g-1][1] == small[0][g-2][2]["split_replace"]
    assert base.array_digest(context["theta"]) == theta_hash
    after = np.random.get_state()
    assert global_rng[0] == after[0] and np.array_equal(global_rng[1], after[1]) and global_rng[2:] == after[2:]


def test_independent_raw_rescore_all_three_generations_and_terminal(context, sources, small, independent, tmp_path):
    for g, (incoming, record, outgoing, developed) in enumerate(small[0], 1):
        raw = {a: base.trajectory_arrays(tr) | {"body_scores": tr["body_scores"]} for a, tr in developed.items()}
        # Include actual saved compressed files and JSON, not only in-memory arrays.
        for a, values in raw.items():
            base.atomic_npz(tmp_path/f"g{g}_{a}.npz", values, tmp_path)
        study.atomic_json(tmp_path/f"g{g}.json", record, tmp_path)
        raw = {a: chain.load_arrays(tmp_path/f"g{g}_{a}.npz") for a in raw}
        previous = {a: study.birth(sources[1][g-1], p)["R"] for a, p in incoming.items()}
        stages, checked_out = independent.check_generation(sources[1][g-1], previous, json.loads((tmp_path/f"g{g}.json").read_text()), raw, context["config"].sample_times)
        assert len(stages) == 54
        assert {a: study.serialize(r) for a, r in checked_out.items()} == outgoing
    probes = {a: base.trajectory_arrays(tr) for a, tr in small[2].items()}
    assert len(independent.check_terminal(sources[1][-1], checked_out, small[1], probes, context["config"].sample_times)) == 21


@pytest.mark.parametrize("corruption", ("Q_birth", "trace_unsaved", "fresh_body", "incoming_R", "outgoing_link", "replay_link"))
def test_independent_generation_tamper_detection(corruption, context, sources, small, independent):
    incoming, original, _, developed = small[0][1]
    record = deepcopy(original)
    raw = {a: {k: v.copy() for k, v in (base.trajectory_arrays(tr) | {"body_scores": tr["body_scores"]}).items()} for a, tr in developed.items()}
    if corruption == "Q_birth":
        raw["split_replace"]["s0_Q"][0, 0, 0] = .1
    elif corruption == "trace_unsaved":
        raw["split_replace"]["body_scores"][2, 0, 0] += .01
    elif corruption == "fresh_body":
        raw["split_replace"]["s0_V"][0, 0, 0] += .1
    elif corruption == "incoming_R":
        raw["split_replace"]["s0_R"] = study.birth(sources[1][1], sources[0])["R"]
    elif corruption == "outgoing_link":
        record["outgoing_packet_sha256"]["split_replace"] = "0"*64
    else:
        record["replay_received_packet_sha256"] = study.packet_hash(sources[0])
    previous = {a: study.birth(sources[1][1], p)["R"] for a, p in incoming.items()}
    with pytest.raises(AssertionError):
        independent.check_generation(sources[1][1], previous, record, raw, context["config"].sample_times)


def test_independent_terminal_birth_tamper_detected(context, sources, small, independent):
    outgoing = {a: study.birth(sources[1][-1], p)["R"] for a, p in small[0][-1][2].items()}
    probes = {a: {k: v.copy() for k, v in base.trajectory_arrays(tr).items()} for a, tr in small[2].items()}
    probes["q_split"]["s0_ema"][0, 0, 0] += 1.
    with pytest.raises(AssertionError):
        independent.check_terminal(sources[1][-1], outgoing, small[1], probes, context["config"].sample_times)


def endpoint_records(flags=(True, True, True)):
    records = []
    for tissue in study.TISSUES:
        generations = []
        for g in range(1, 13):
            summaries = {"working": {"split_replace": {"1000": {"body_accuracy": 1.}},
                                     "split_reset": {"1000": {"body_accuracy": .25 if flags[0] or g != 12 else 1.}},
                                     "protected_copy": {"1000": {"body_accuracy": 1.}}}}
            generations.append({"generation": g, "passes": True, "summaries": summaries})
        terminal = {"passes": True, "summaries": {"q_split": {"1000": {"body_accuracy": 1.}},
                    "q_reset": {"1000": {"body_accuracy": .25 if flags[1] else 1.}},
                    "q_split_off": {"1000": {"body_accuracy": .25 if flags[2] else 1.}}}}
        records.append({"tissue": tissue, "passes": True, "generations": generations, "terminal": terminal})
    return records


@pytest.mark.parametrize("flags", ((True, True, True), (False, True, True), (True, False, True), (True, True, False), (False, False, False)))
def test_fixed_G12_three_endpoints_and_independent_intervals(flags, independent):
    records = endpoint_records(flags)
    result = study.classify(records)
    assert result["label"] == ("QUALIFIED_TWELVE_GENERATION_REPLACEMENT" if all(flags) else "NO_QUALIFIED_REPLACEMENT_LEAD")
    cells = [{"tissue": r["tissue"], "generations": [{"generation": g["generation"], "final": {"working": {a: s["1000"] for a, s in g["summaries"]["working"].items()}}} for g in r["generations"]],
              "terminal": {a: s["1000"] for a, s in r["terminal"]["summaries"].items()}} for r in records]
    assert independent.adjudicate(cells, result)["label"] == result["label"]
    for n, contrast in enumerate(result["co_primary_G12"].values()):
        assert contrast["seed"] == 20260907183001+n and contrast["quantiles"] == [1/120, 119/120]


def test_every_protected_control_generation_must_qualify_and_no_endpoint_suppression():
    records = endpoint_records()
    records[0]["generations"][1]["summaries"]["working"]["protected_copy"]["1000"]["body_accuracy"] = .25
    result = study.classify(records)
    assert result["label"] == "NO_QUALIFIED_PROTECTED_REFERENCE_CONTROL"
    assert len(result["co_primary_G12"]) == 3 and not result["protected_control_qualified"]


def test_classifier_invalid_missing_duplicate_failed_and_truncated():
    records = endpoint_records()
    for invalid in ([], records[:-1], records+[records[0]]):
        assert study.classify(invalid)["label"] == "INVALID_STRUCTURAL_FAILURE"
    invalid = deepcopy(records)
    invalid[0]["generations"].pop()
    assert study.classify(invalid)["label"] == "INVALID_STRUCTURAL_FAILURE"
    invalid = deepcopy(records)
    invalid[0]["terminal"]["passes"] = False
    assert study.classify(invalid)["label"] == "INVALID_STRUCTURAL_FAILURE"
    assert study.classify(records, False)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_real_public_newborns_are_reconstructed_without_parent_state():
    context = base.make_context(10000, study.CONFIG)
    for g in (1, 2, 12):
        newborn = study.load_newborn(study.external_root(), context, g)
        replay = base.naive_body(context, chain.phase(g, "fresh_body_birth"))
        assert base.state_digest(newborn) == base.state_digest(replay)
        assert all(base.message_independent(v, 8) for v in newborn.values())


def test_existing_target_blocks_prepare_and_benchmark(tmp_path):
    (tmp_path/"outputs"/study.RUN_ID).mkdir(parents=True)
    for method in (study.prepare, study.benchmark):
        with pytest.raises(FileExistsError):
            method(tmp_path)


def test_prepared_contract_and_tamper_detection(tmp_path, monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    path, bench = tmp_path/"contract.txt", study.benchmark_path(tmp_path)
    study.atomic_text(path, "fixed", tmp_path)
    study.atomic_json(bench, {"must_detach": True}, tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [path])
    hashes = {str(p): study.sha256_file(p) for p in (path, bench)}
    manifest = study.contract() | {"input_sha256": hashes, "contract_digest": study.canonical_digest(hashes)}
    study.atomic_json(run/"MANIFEST.json", manifest, tmp_path)
    study.atomic_json(run/"STATUS.json", {"status": "PREPARED"}, tmp_path)
    assert study.verify_prepared(tmp_path)["workers"] == 4
    for key, value in (("workers", 5), ("probes", list(study.PROBES)[:-1]), ("packet_bytes_per_world", 4096), ("renewing_generations", 3)):
        study.atomic_json(run/"MANIFEST.json", manifest | {key: value}, tmp_path)
        with pytest.raises(RuntimeError, match="contract changed"):
            study.verify_prepared(tmp_path)
    study.atomic_json(run/"MANIFEST.json", manifest, tmp_path)
    study.atomic_text(path, "changed", tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)


def test_long_run_requires_detached_launch(tmp_path, monkeypatch):
    (tmp_path/"runs"/study.RUN_ID).mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": True}})
    with pytest.raises(RuntimeError, match="detached launch required"):
        study.run_study(tmp_path)
    assert not (tmp_path/"runs"/study.RUN_ID/"EXECUTION.lock").exists()


def test_detach_is_no_poll_and_unique(tmp_path, monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    (tmp_path/"logs").mkdir()
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"projected_seconds_four_workers": 901}})
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=9876)
    monkeypatch.setattr(study.subprocess, "Popen", launch)
    result = study.launch_detached(tmp_path)
    assert result["polling_owner"] == "user" and result["pid"] == 9876
    assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"] == study.subprocess.DEVNULL
    assert (run/"RUN.pid").read_text().strip() == "9876"
    with pytest.raises(FileExistsError):
        study.launch_detached(tmp_path)


def test_runtime_failure_records_sentinel_without_scientific_work(tmp_path, monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(study.base, "runtime", lambda: {"passes": False})
    monkeypatch.setattr(study, "qualify_source", lambda root: {"passes": True})
    monkeypatch.setattr(study, "worker", lambda *args: pytest.fail("must not simulate"))
    with pytest.raises(RuntimeError, match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run/"FAILED").is_file() and not (run/"COMPLETE").exists()
