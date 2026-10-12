"""D182 fresh-founder wrapper: one disposable life, no main acquisition."""
import copy
import inspect
import os
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_founders_population_run as r


def forbidden(*args, **kwargs):
    raise AssertionError("forbidden dynamics or premature acquisition/descendant")


def synthetic_proof():
    return dict(passes=True, full_physics_replayed=True, paths=144,
        generation_paths=432, terminal_paths=288, exact_alias_checks=728,
        reader_max_abs=0., writer_max_abs=0., terminal_max_abs=0.,
        selector_max_abs=0., feature_max_abs=0., metric_max_abs=0.)


def synthetic_source_proof():
    return dict(passes=True, full_physics_replayed=True, source_records=2,
        acquired_records=2, source_readers=2, source_writers=4,
        founder_max_abs=0., pre_reader_max_abs=0., founder_source_max_abs=0.)


def synthetic_rows():
    rows = []
    for bi, index in enumerate(r.model.BLOCKS):
        for life in range(4):
            for family, coupling, replica, kind in r.model.CELLS:
                for ai, assay in enumerate(r.analysis.ASSAYS):
                    value = (bi*4+life-7.5)/64+(coupling-1)/8
                    value += (replica-3.5)*(coupling-1)*(life-1)/32
                    value += (r.model.CONDITIONS.index(kind)-2.5)/32+family/64+ai/128
                    rows.append(dict(index=index, life=life, family=family, coupling=coupling,
                        replica=replica, condition=kind, assay=assay, preference=value,
                        body_rms=.7, clip_fraction=0., f0_own_correlation=.8,
                        f0_own_minus_alternative=.4, f3_own_correlation=.65,
                        f3_own_minus_alternative=.25, guide_family=family, guide_shift=[0, 0]))
    return rows


def fake_panel(directory, monkeypatch):
    rows = synthetic_rows()
    for area in ("sources", "descendants"):
        (directory/area).mkdir()
    for name in ("SOURCE_SEAL.json", "DESCENDANTS_STARTED.json"):
        r.write_json(directory/name, dict(synthetic_fixture=True))
    for index in r.model.BLOCKS:
        block = directory/"descendants"/f"block_{index}"
        block.mkdir()
        source = directory/"sources"/f"block_{index}"
        source.mkdir()
        for life in range(4):
            r.write_npz(block/f"life_{life}.npz", {})
            r.write_json(block/f"life_{life}.json", dict(synthetic_fixture=True, index=index, life=life))
            r.write_json(source/f"replay_{life}.json", synthetic_source_proof())
    monkeypatch.setattr(r, "require_barrier", lambda directory, preparation: None)
    monkeypatch.setattr(r.sources, "load_source", lambda directory, index: dict(synthetic_source=index))
    seen = []
    def read(directory_, index, life, source):
        assert directory_ == directory/"descendants"/f"block_{index}"
        assert source == dict(synthetic_source=index)
        selected = [x for x in rows if x["index"] == index and x["life"] == life]
        assert len(selected) == 288
        seen.append((index, life))
        return {}, synthetic_proof(), selected
    monkeypatch.setattr(r, "read_life", read)
    monkeypatch.setattr(r.model, "simulate_life", forbidden)
    monkeypatch.setattr(r.sources, "generate_founders", forbidden)
    monkeypatch.setattr(r.check.physics, "step", forbidden)
    return rows, seen


def test_frozen_science_identity():
    assert r.model is r.previous.model and r.check is r.previous.check
    assert r.analysis is r.previous.analysis and r.stats_check is r.previous.stats_check
    assert r.sources is r.previous.sources and r.source_check is r.previous.source_check
    assert r.save_life is r.previous.save_life
    assert r.model.REPLICAS == (2, 3, 4, 5) and len(r.model.CELLS) == 144 and r.WORKERS == 4
    assert r.plan()["canonical_recipient"] == 514240


def test_benchmark_hashes():
    pins = r.source_inputs()
    assert pins[str(r.previous.audit_path())] == r.PINS[r.previous.audit_path()]
    assert len(pins) > 800
    assert not r.run_dir().exists() and not r.output_dir().exists() and not r.freeze_path().exists()


def test_pre_acquisition_freeze():
    path = Path(os.environ[r.QUAL_ENV])
    f = r.prequalified(path)
    assert f["new_main_founders_allowed"] is False and f["plan"] == r.plan()
    assert len(f["science_sha256"]) == 4
    assert f["qualification_forecast_seconds"] < 600


@pytest.fixture(scope="module")
def checked_life(tmp_path_factory):
    fixture = tmp_path_factory.getbasetemp()/"life_fixture"
    preparation = Path(os.environ[r.QUAL_ENV])
    tick = time.monotonic()
    # A real new disposable acquisition through the new wrapper, not a saved source.
    source = r.generate_source(fixture/"source", r.model.DISPOSABLE, (0,), preparation)
    (fixture/"descendants").mkdir()
    proof = r.run_life(fixture/"descendants", source, r.model.DISPOSABLE, 0)
    r.write_json(fixture/"timing.json", dict(seconds=time.monotonic()-tick,
        full_replay_and_io=True, includes_source_acquisition=True, new_main_founders_generated=0))
    return fixture, source, proof


def test_complete_disposable_life(checked_life, monkeypatch):
    fixture, source, proof = checked_life
    assert proof["full_physics_replayed"] and proof["paths"] == 144 and proof["exact_alias_checks"] == 728
    assert proof["reader_max_abs"] == proof["writer_max_abs"] == proof["terminal_max_abs"] == 0
    benchmark = r.previous.output_dir()
    fresh = r.files.load_npz(fixture/"source"/"acquisition_0.npz")
    prior = r.files.load_npz(benchmark/"source"/"acquisition_0.npz")
    assert set(fresh) == set(prior) == set(r.sources.FOUNDER_KEYS)
    for key in fresh:
        np.testing.assert_array_equal(fresh[key], prior[key])
    r.check.prior.nested(r.files.read_json(fixture/"source"/"acquisition_0.json"),
                         r.files.read_json(benchmark/"source"/"acquisition_0.json"))
    old_source = r.sources.load_source(benchmark/"source", r.model.DISPOSABLE)
    assert set(source) == set(r.sources.SOURCE_ARRAYS)
    for key in source:
        np.testing.assert_array_equal(source[key], old_source[key][:1])
    a = r.files.load_npz(fixture/"descendants"/"life_0.npz")
    b = r.files.load_npz(benchmark/"descendants"/"life_0.npz")
    assert set(a) == set(b)
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])
    monkeypatch.setattr(r.model, "simulate_life", forbidden)
    monkeypatch.setattr(r.sources, "generate_founders", forbidden)
    monkeypatch.setattr(r.check.physics, "step", forbidden)
    _, rechecked, rows = r.read_life(fixture/"descendants", r.model.DISPOSABLE, 0, source)
    assert rechecked == proof and len(rows) == 288


def test_saved_disposable_block(tmp_path_factory, monkeypatch):
    tick = time.monotonic()
    f = r.previous.frozen()
    monkeypatch.setattr(r.model, "simulate_life", forbidden)
    monkeypatch.setattr(r.sources, "generate_founders", forbidden)
    monkeypatch.setattr(r.check.physics, "step", forbidden)
    proof = r.previous.saved_experiment(f)
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    r.check.prior.nested(proof, done["verification"])
    r.write_json(tmp_path_factory.getbasetemp()/"saved_benchmark_check.json", dict(
        benchmark_complete_sha256=r.PINS[r.previous.run_dir()/"COMPLETE.json"],
        verification=proof, seconds=time.monotonic()-tick, new_dynamics=0))
    assert proof["paths"] == 576 and proof["all_f0_sealed_before_descendants"]


def test_population_saved_panel(tmp_path, monkeypatch):
    rows, seen = fake_panel(tmp_path, monkeypatch)
    got, report, proof = r.saved_population(tmp_path, "synthetic", False)
    assert got == rows and seen == [(i, l) for i in r.model.BLOCKS for l in range(4)]
    assert (proof["source_records"], proof["lives"], proof["paths"], proof["generation_paths"],
            proof["terminal_paths"], proof["exact_alias_checks"]) == (32, 16, 2304, 6912, 4608, 11648)
    assert proof["fresh_source_acquisitions"] == 32 and proof["source_writers"] == 64
    stats = proof["saved_statistics"]
    assert stats["groups"] == 8 and stats["rows"] == 4608 and stats["pair_components"] == 48
    assert stats["future_omissions"] == 32 and stats["control_cells"] == 1152 and stats["control_contrasts"] == 960
    r.write_json(tmp_path/"records.json", got)
    r.write_json(tmp_path/"summary.json", report)
    monkeypatch.setattr(r.analysis, "summarize", forbidden)
    _, _, reread = r.saved_population(tmp_path, "synthetic", True)
    assert reread == proof


@pytest.mark.parametrize("case", ["missing_block", "extra_block", "missing_life", "extra_life", "missing_report"])
def test_missing_or_extra_outputs(tmp_path, monkeypatch, case):
    for area in ("sources", "descendants"):
        (tmp_path/area).mkdir()
    for name in ("SOURCE_SEAL.json", "DESCENDANTS_STARTED.json"):
        r.write_json(tmp_path/name, dict(synthetic_fixture=True))
    blocks = r.model.BLOCKS[:-1] if case == "missing_block" else r.model.BLOCKS
    if case == "extra_block": blocks += (99999,)
    for index in blocks:
        block = tmp_path/"descendants"/f"block_{index}"
        block.mkdir()
        lives = range(3) if case == "missing_life" else range(5) if case == "extra_life" else ()
        for life in lives:
            r.write_npz(block/f"life_{life}.npz", {})
            r.write_json(block/f"life_{life}.json", dict(synthetic_fixture=True))
    monkeypatch.setattr(r, "require_barrier", lambda *args: None)
    monkeypatch.setattr(r, "read_life", forbidden)
    monkeypatch.setattr(r.sources, "load_source", forbidden)
    with pytest.raises(AssertionError):
        r.saved_population(tmp_path, "synthetic", case == "missing_report")


@pytest.mark.parametrize("field", ["component", "future", "pair", "control", "row", "old_futures"])
def test_corrupt_report(tmp_path, monkeypatch, field):
    fake_panel(tmp_path, monkeypatch)
    rows, report, _ = r.saved_population(tmp_path, "synthetic", False)
    if field == "component": report["groups"][0]["cross_replica"]["interaction"] += .1
    elif field == "future": report["groups"][0]["leave_one_future_out"][0]["mean"] += .1
    elif field == "pair": report["groups"][0]["pair_components"][0]["components"]["record"] += .1
    elif field == "control": report["control_cells"][0]["preference"] += .1
    elif field == "row": rows = copy.deepcopy(rows); rows[0]["preference"] += .1
    else: report["old_futures_pooled"] = True
    r.write_json(tmp_path/"records.json", rows)
    r.write_json(tmp_path/"summary.json", report)
    monkeypatch.setattr(r.analysis, "summarize", forbidden)
    with pytest.raises(AssertionError): r.saved_population(tmp_path, "synthetic", True)


def synthetic_seal(directory, monkeypatch):
    (directory/"sources").mkdir()
    for i in r.model.BLOCKS:
        r.write_json(directory/"sources"/f"block_{i}"/"fixture.json", dict(synthetic_fixture=True, index=i))
    def source(path, index, lives, preparation):
        assert path == directory/"sources"/f"block_{index}" and lives == (0, 1, 2, 3)
        assert preparation == "synthetic-preparation"
        return dict(founder_packets=np.full((4, 2, 2048), index % 251, np.uint8))
    monkeypatch.setattr(r.previous, "read_source", source)
    seal = r.previous.seal_sources({i: directory/"sources"/f"block_{i}" for i in r.model.BLOCKS},
                                   "synthetic-preparation", r.model.BLOCKS)
    return seal


def test_source_barrier(tmp_path, monkeypatch):
    seal = synthetic_seal(tmp_path, monkeypatch)
    r.write_json(tmp_path/"SOURCE_SEAL.json", seal)
    assert not (tmp_path/"descendants").exists()
    r.start_descendants(tmp_path, "synthetic-preparation")
    assert (tmp_path/"descendants").is_dir()
    assert r.require_barrier(tmp_path, "synthetic-preparation") == seal


@pytest.mark.parametrize("bad", ["missing_source", "extra_source", "duplicate_source", "changed_hash",
                               "changed_record", "wrong_preparation", "wrong_index", "record_count", "already_started"])
def test_bad_seal(tmp_path, monkeypatch, bad):
    seal = synthetic_seal(tmp_path, monkeypatch)
    if bad == "missing_source": del seal["sources"][str(r.model.BLOCKS[-1])]
    elif bad == "extra_source": seal["sources"]["90000"] = seal["sources"][str(r.model.BLOCKS[0])]
    elif bad == "duplicate_source": seal["sources"][str(r.model.BLOCKS[1])] = seal["sources"][str(r.model.BLOCKS[0])]
    elif bad == "changed_hash":
        hashes = seal["sources"][str(r.model.BLOCKS[0])]["sha256"]
        hashes[next(iter(hashes))] = "0"*64
    elif bad == "changed_record": seal["record_seals"][0]["sha256"] = "0"*64
    elif bad == "wrong_preparation": seal["preparation_sha256"] = "old"
    elif bad == "wrong_index": seal["indices"][0] = 90000
    elif bad == "record_count": seal["record_seals"].pop()
    else: seal["descendants_generated"] = 1
    r.write_json(tmp_path/"SOURCE_SEAL.json", seal)
    with pytest.raises(AssertionError): r.start_descendants(tmp_path, "synthetic-preparation")
    assert not (tmp_path/"descendants").exists() and not (tmp_path/"DESCENDANTS_STARTED.json").exists()


@pytest.mark.parametrize("bad", ["hash", "count", "preparation", "time", "flag"])
def test_wrong_barrier(tmp_path, monkeypatch, bad):
    seal = synthetic_seal(tmp_path, monkeypatch)
    r.write_json(tmp_path/"SOURCE_SEAL.json", seal)
    r.start_descendants(tmp_path, "synthetic-preparation")
    entry = r.files.read_json(tmp_path/"DESCENDANTS_STARTED.json")
    if bad == "hash": entry["source_seal_sha256"] = "0"*64
    elif bad == "count": entry["source_records"] = 8
    elif bad == "preparation": entry["preparation_sha256"] = "old"
    elif bad == "time": entry["started_utc"] = "2000-01-01T00:00:00+00:00"
    else: entry["all_sources_checked_before_descendants"] = False
    original = r.files.read_json
    monkeypatch.setattr(r.files, "read_json", lambda p: entry if p == tmp_path/"DESCENDANTS_STARTED.json" else original(p))
    with pytest.raises(AssertionError): r.require_barrier(tmp_path, "synthetic-preparation")


def test_source_schedule(tmp_path, monkeypatch):
    events = []
    preparation = tmp_path/"freeze.json"
    r.write_json(preparation, dict(synthetic_fixture=True))
    output = tmp_path/"output"; output.mkdir()
    monkeypatch.setattr(r, "output_dir", lambda: output)
    monkeypatch.setattr(r, "freeze_path", lambda: preparation)
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r.model, "simulate_life", forbidden)
    def generate(directory, index, lives, prep, *, main):
        assert main is True and lives == (0, 1, 2, 3) and prep == preparation
        assert not (output/"descendants").exists() and not (output/"SOURCE_SEAL.json").exists()
        assert directory == output/"sources"/f"block_{index}"
        directory.mkdir(); events.append(("generate", index))
    def seal(directories, digest, indices):
        assert events == [("generate", i) for i in r.model.BLOCKS]
        assert indices == r.model.BLOCKS and set(directories) == set(indices)
        assert digest == r.sha256_file(preparation)
        events.append(("seal", 32)); return dict(synthetic_fixture=True)
    monkeypatch.setattr(r, "generate_source", generate)
    monkeypatch.setattr(r.previous, "seal_sources", seal)
    monkeypatch.setattr(r, "read_seal", lambda *a: events.append(("check", 32)))
    r.acquire_all_sources(output, preparation)
    assert events == [("generate", i) for i in r.model.BLOCKS]+[("seal", 32), ("check", 32)]
    assert not (output/"descendants").exists()


def test_failed_acquisition_stops_barrier(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(r, "freeze_path", lambda: tmp_path/"freeze")
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r.previous, "seal_sources", forbidden)
    seen = []
    def generate(directory, index, lives, preparation, *, main):
        seen.append(index)
        r.write_json(directory/"partial.json", dict(synthetic_fixture=True, index=index))
        if index == r.model.BLOCKS[1]: raise RuntimeError("synthetic source failure")
    monkeypatch.setattr(r, "generate_source", generate)
    with pytest.raises(RuntimeError, match="synthetic source failure"):
        r.acquire_all_sources(tmp_path, tmp_path/"freeze")
    assert seen == list(r.model.BLOCKS[:2])
    assert len(list((tmp_path/"sources").rglob("partial.json"))) == 2
    assert not (tmp_path/"SOURCE_SEAL.json").exists() and not (tmp_path/"descendants").exists()


@pytest.mark.parametrize("index", [True, 90000, 514240, 120000, 120005, 120010, 120015])
def test_no_main_acquisition(tmp_path, monkeypatch, index):
    monkeypatch.setattr(r.sources, "generate_founders", forbidden)
    with pytest.raises(AssertionError):
        r.generate_source(tmp_path/"source", index, (0,), tmp_path/"not-a-freeze")
    assert not (tmp_path/"source").exists()


@pytest.mark.parametrize("bad", ["stage", "ready", "freeze", "directory", "sealed", "descendants", "disposable", "partial_lives"])
def test_source_address_guard(tmp_path, monkeypatch, bad):
    output = tmp_path/"output"; output.mkdir()
    prep = tmp_path/"freeze.json"
    monkeypatch.setattr(r, "output_dir", lambda: output)
    monkeypatch.setattr(r, "freeze_path", lambda p=prep: p)
    monkeypatch.setattr(r, "frozen", lambda: {})
    monkeypatch.setenv(r.ENV, "execute")
    monkeypatch.delenv(r.READY, raising=False)
    monkeypatch.setattr(r.sources, "generate_founders", forbidden)
    index, lives, directory = 120000, (0, 1, 2, 3), output/"sources"/"block_120000"
    if bad == "stage": monkeypatch.setenv(r.ENV, "qualification")
    elif bad == "ready": monkeypatch.setenv(r.READY, "99")
    elif bad == "freeze": prep = tmp_path/"wrong.json"
    elif bad == "directory": directory = tmp_path/"old-source"
    elif bad == "sealed": r.write_json(output/"SOURCE_SEAL.json", dict(synthetic_fixture=True))
    elif bad == "descendants": (output/"descendants").mkdir()
    elif bad == "disposable": index = 514260
    else: lives = (0,)
    with pytest.raises(AssertionError): r.generate_source(directory, index, lives, prep, main=True)
    assert not directory.exists()


def test_worker_schedule(tmp_path, monkeypatch):
    events = []
    (tmp_path/"descendants").mkdir()
    monkeypatch.setenv(r.ENV, "execute"); monkeypatch.delenv(r.READY, raising=False)
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r, "frozen", lambda: {})
    monkeypatch.setattr(r, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(r, "sha256_file", lambda path: "frozen")
    monkeypatch.setattr(r, "require_barrier", lambda *a: events.append(("barrier", 32)))
    def load(path, index):
        assert events == [("barrier", 32)] and path == tmp_path/"sources"/f"block_{index}"
        return dict(founder_packets="synthetic", guide="synthetic", targets="synthetic")
    monkeypatch.setattr(r.sources, "load_source", load)
    def run(directory, source, index, life):
        assert directory == tmp_path/"descendants"/"block_120000" and index == 120000
        assert set(source) == set(r.sources.SOURCE_ARRAYS)
        events.append(("life", life)); return synthetic_proof()
    monkeypatch.setattr(r, "run_life", run)
    result = r.worker(120000)
    assert result["paths"] == 576 and result["lives"] == 4
    assert events == [("barrier", 32)]+[("life", i) for i in range(4)]


def test_execution_phase_order(tmp_path, monkeypatch):
    """Exercise the real coordinator with labelled synthetic tasks, never main dynamics."""
    events = []
    output, run = tmp_path/"output", tmp_path/"run"
    monkeypatch.setenv(r.ENV, "execute"); monkeypatch.delenv(r.READY, raising=False)
    monkeypatch.setattr(r.os, "getsid", lambda _: os.getpid())
    monkeypatch.setattr(r, "EXECUTION_OWNED", False)
    monkeypatch.setattr(r, "resources", lambda: dict(synthetic_fixture=True))
    monkeypatch.setattr(r, "frozen", lambda: dict(conservative_seconds=5153., inputs={}, science_qualification={}))
    monkeypatch.setattr(r, "live_budget", lambda _: 1000)
    monkeypatch.setattr(r, "output_dir", lambda: output)
    monkeypatch.setattr(r, "run_dir", lambda: run)
    monkeypatch.setattr(r, "sha256_file", lambda p: "synthetic-digest")
    monkeypatch.setattr(r.files, "hashes", lambda paths: {f"synthetic-{i}": "synthetic" for i in range(100)})
    def acquire(directory, preparation):
        assert directory == output and events == []
        assert not (directory/"descendants").exists()
        events.append("all_sources_checked_and_sealed")
    def start(directory, digest):
        assert events == ["all_sources_checked_and_sealed"]
        assert directory == output and digest == "synthetic-digest"
        events.append("barrier_saved")
    class Future:
        def __init__(self, index): self.index = index
        def result(self): return dict(index=self.index, passes=True, lives=4)
    class Pool:
        def __init__(self, *, max_workers, mp_context):
            assert max_workers == 4 and mp_context.get_start_method() == "spawn"
            assert events == ["all_sources_checked_and_sealed", "barrier_saved"]
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def submit(self, function, index):
            assert function is r.worker
            events.append(index); return Future(index)
    def saved(directory, digest, report):
        assert directory == output and digest == "synthetic-digest"
        expected = ["all_sources_checked_and_sealed", "barrier_saved"]+list(r.model.BLOCKS)
        assert events[:6] == expected
        events.append("readback" if report else "aggregate")
        return [], dict(synthetic_fixture=True), dict(passes=True, synthetic_fixture=True)
    monkeypatch.setattr(r, "acquire_all_sources", acquire)
    monkeypatch.setattr(r, "start_descendants", start)
    monkeypatch.setattr(r, "ProcessPoolExecutor", Pool)
    monkeypatch.setattr(r, "as_completed", lambda futures: list(futures))
    monkeypatch.setattr(r, "saved_population", saved)
    result = r.execute()
    assert result["status"] == "COMPLETE" and r.EXECUTION_OWNED
    assert events == ["all_sources_checked_and_sealed", "barrier_saved"]+list(r.model.BLOCKS)+["aggregate", "readback"]
    assert (run/"COMPLETE.json").exists() and not r.audit_path().exists()


@pytest.mark.parametrize("index", [True, 514260, 90000, 120001, -1])
def test_bad_worker_address(index):
    with pytest.raises(AssertionError): r.worker(index)


def test_failure_retention(tmp_path, monkeypatch):
    monkeypatch.setattr(r.model, "simulate_life", lambda *a: (dict(synthetic=np.array([1.])), dict(synthetic_fixture=True)))
    def fail(*a): raise RuntimeError("synthetic replay failure")
    monkeypatch.setattr(r.check, "check_life", fail)
    with pytest.raises(RuntimeError, match="synthetic replay failure"):
        r.run_life(tmp_path, {}, r.model.DISPOSABLE, 0)
    assert r.files.read_json(tmp_path/"life_0.json")["replay"] == dict(passes=False)
    np.testing.assert_array_equal(r.files.load_npz(tmp_path/"life_0.npz")["synthetic"], [1.])


def test_source_failure_retention(tmp_path, monkeypatch):
    preparation = tmp_path/"preparation.json"
    r.write_json(preparation, dict(synthetic_fixture=True))
    xml = r.ROOT/"logs"/(tmp_path.name+".xml")
    # Use the real qualification path guard with a mocked preparation receipt.
    monkeypatch.setattr(r, "prequalified", lambda p: dict(qualification_xml=str(xml)))
    monkeypatch.setattr(r, "ROOT", tmp_path)
    fixture = tmp_path/"tmp"/xml.stem/"life_fixture"/"source"
    monkeypatch.setattr(r.sources, "generate_founders", lambda *a: (dict(synthetic=np.array([2.])), dict(synthetic_fixture=True)))
    monkeypatch.setattr(r.sources, "make_bundle", lambda *a: {})
    def fail(*a): raise RuntimeError("synthetic source replay failure")
    monkeypatch.setattr(r.source_check, "check_source", fail)
    with pytest.raises(RuntimeError, match="synthetic source replay failure"):
        r.generate_source(fixture, r.model.DISPOSABLE, (0,), preparation)
    assert (fixture/"acquisition_0.npz").exists() and (fixture/"acquisition_0.json").exists()
    assert not (fixture/"bundle.npz").exists()


@pytest.mark.parametrize("field,value", [("passes", False), ("full_physics_replayed", False),
    ("paths", 72), ("terminal_paths", 144), ("exact_alias_checks", 364)])
def test_bad_replay_proof(field, value):
    proof = synthetic_proof(); proof[field] = value
    with pytest.raises(AssertionError): r.aggregate_proofs([proof])


def test_wrong_source_metadata(monkeypatch):
    monkeypatch.setattr(r.previous, "read_life", forbidden)
    with pytest.raises(AssertionError):
        r.read_life(r.previous.output_dir()/"descendants", 120000, 0, {})


@pytest.mark.parametrize("bad", [None, "passes", "new_dynamics", "complete_sha256", "freeze_sha256", "verification"])
def test_audit_linkage(bad):
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    audit = r.files.read_json(r.previous.audit_path())
    if bad == "passes": audit[bad] = False
    elif bad == "new_dynamics": audit[bad] = 1
    elif bad in ("complete_sha256", "freeze_sha256"): audit[bad] = "0"*64
    elif bad == "verification": audit[bad]["paths"] -= 1
    if bad is not None:
        with pytest.raises(AssertionError): r.audit_linkage(done, audit)
    else: r.audit_linkage(done, audit)


def test_budget_cap():
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    result = r.budget(done, 199717308, 1.)
    assert result["conservative_seconds"] == 4*done["seconds"]+182
    assert result["storage_bound_bytes"] == 4*182374332+199717308+64*1024**2
    assert result["parallel_speedup_credit"] is False
    with pytest.raises(AssertionError): r.budget(done, r.previous.CAP, 1.)
    with pytest.raises(AssertionError): r.budget(done, 0, float("nan"))


def test_live_budget_gate(monkeypatch):
    f = dict(uncompressed_benchmark_block_bytes=182374332)
    monkeypatch.setattr(r, "resources", lambda: dict(bytes=199717308))
    assert r.live_budget(f) < r.previous.CAP
    monkeypatch.setattr(r, "resources", lambda: dict(bytes=r.previous.CAP))
    with pytest.raises(AssertionError): r.live_budget(f)


def test_foreground_gate(monkeypatch):
    monkeypatch.delenv(r.ENV, raising=False)
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r, "frozen", lambda: dict(conservative_seconds=5153.))
    monkeypatch.setattr(r, "output_dir", forbidden)
    with pytest.raises(RuntimeError): r.execute()
    assert not r.EXECUTION_OWNED
    assert not r.time_gate(600) and r.time_gate(601, True)


def test_external_write_once(tmp_path):
    path = tmp_path/"once.json"
    r.write_json(path, dict(synthetic_fixture=True))
    with pytest.raises(FileExistsError): r.write_json(path, {})
    with pytest.raises(AssertionError): r.external(Path("/tmp/wrong-output-location.json"))
    with pytest.raises(AssertionError): r.verify({str(path): "0"*64})
    r.verify({str(path): r.sha256_file(path)})


def test_cold_workers(tmp_path):
    rows = r.cold_workers()
    assert len(rows) == 4 and all(x["new_dynamics"] == 0 and x["source_hashes"] > 800 for x in rows)
    assert all(x["pid"] != os.getpid() for x in rows)
    r.write_json(tmp_path/"cold_workers.json", rows)


def test_cold_detached(tmp_path):
    result = r.spawn_detached("startup-check", tmp_path/"startup.log", 55)
    assert result["status"] == "DETACHED_STARTED"
    assert not result["automatic_polling"] and not result["automatic_successor"]
    assert ".poll(" not in inspect.getsource(r.spawn_detached)
    assert "start_new_session=True" in inspect.getsource(r.spawn_detached)
    r.write_json(tmp_path/"startup_receipt.json", result)
