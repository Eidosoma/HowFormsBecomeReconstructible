"""D181 wrapper qualification: saved disposable data and synthetic panels only."""
import copy
import inspect
import os
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_repeats_population_run as r


def forbidden(*args, **kwargs):
    raise AssertionError("no new dynamics, population outputs or pending-audit reads")


def synthetic_proof():
    return dict(passes=True, full_physics_replayed=True, paths=144,
                generation_paths=432, terminal_paths=288, exact_alias_checks=728,
                reader_max_abs=0., writer_max_abs=0., terminal_max_abs=0.,
                selector_max_abs=0., feature_max_abs=0., metric_max_abs=0.)


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
    """Empty labelled placeholders are synthetic fixtures, never simulation output."""
    rows = synthetic_rows()
    for index in r.model.BLOCKS:
        block = directory/f"block_{index}"
        block.mkdir()
        for life in range(4):
            r.write_npz(block/f"life_{life}.npz", {})
            r.write_json(block/f"life_{life}.json", dict(synthetic_fixture=True, index=index, life=life))
    monkeypatch.setattr(r.model, "load_source", lambda index: dict(synthetic_source=index))
    seen = []
    def read(directory_, index, life, source):
        assert directory_ == directory/f"block_{index}"
        assert source == dict(synthetic_source=index)
        selected = [x for x in rows if x["index"] == index and x["life"] == life]
        assert len(selected) == 288
        seen.append((index, life))
        return {}, synthetic_proof(), selected
    monkeypatch.setattr(r, "read_life", read)
    monkeypatch.setattr(r.model, "simulate_life", forbidden)
    monkeypatch.setattr(r.check.physics, "step", forbidden)
    return rows, seen


def test_frozen_science_identity():
    assert r.model is r.previous.model and r.check is r.previous.check
    assert r.analysis is r.previous.analysis and r.stats_check is r.previous.stats_check
    assert r.save_life is r.previous.save_life
    assert r.seal_records is r.previous.previous.seal_records
    assert r.model.REPLICAS == (2, 3, 4, 5)
    assert len(r.model.CELLS) == 144 and r.WORKERS == 4


def test_benchmark_hashes():
    pins = r.benchmark_inputs()
    assert len(pins) == 212
    assert str(r.previous.audit_path()) not in pins
    assert len(r.seal_records()) == 32
    assert not r.run_dir().exists() and not r.output_dir().exists()


@pytest.fixture(scope="module")
def saved_benchmark(tmp_path_factory):
    tick = time.monotonic()
    source = r.model.load_source(514240)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(r.model, "simulate_life", forbidden)
        patch.setattr(r.check.physics, "step", forbidden)
        proof = r.previous.saved_block(r.previous.output_dir(), source)
        _, single_proof, rows = r.read_life(r.previous.output_dir(), 514240, 0, source)
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    r.check.prior.nested(proof, done["verification"])
    receipt = dict(benchmark_complete_sha256=r.PINS[r.previous.run_dir()/"COMPLETE.json"],
                   verification=proof, seconds=time.monotonic()-tick, new_dynamics=0)
    r.write_json(tmp_path_factory.getbasetemp()/"saved_benchmark_check.json", receipt)
    return proof, single_proof, rows


def test_saved_disposable_block(saved_benchmark):
    proof, single, rows = saved_benchmark
    assert proof["paths"] == 576 and proof["lives"] == 4
    assert proof["exact_alias_checks"] == 2912 and proof["new_audit_dynamics"] == 0
    assert single["full_physics_replayed"] and len(rows) == 288
    assert proof["reader_max_abs"] == proof["writer_max_abs"] == proof["terminal_max_abs"] == 0


def test_population_saved_panel(tmp_path, monkeypatch):
    rows, seen = fake_panel(tmp_path, monkeypatch)
    got, report, proof = r.saved_population(tmp_path, False)
    assert got == rows
    assert seen == [(index, life) for index in r.model.BLOCKS for life in range(4)]
    assert (proof["source_records"], proof["lives"], proof["paths"], proof["generation_paths"],
            proof["terminal_paths"], proof["exact_alias_checks"]) == (32, 16, 2304, 6912, 4608, 11648)
    stats = proof["saved_statistics"]
    assert stats["groups"] == 8 and stats["rows"] == 4608
    assert stats["pair_components"] == 48 and stats["future_omissions"] == 32
    assert stats["control_cells"] == 1152 and stats["control_contrasts"] == 960
    r.write_json(tmp_path/"records.json", got)
    r.write_json(tmp_path/"summary.json", report)
    monkeypatch.setattr(r.analysis, "summarize", forbidden)
    _, _, reread = r.saved_population(tmp_path, True)
    assert reread == proof


@pytest.mark.parametrize("case", ["missing_block", "extra_block", "missing_life", "extra_life", "missing_report"])
def test_missing_or_extra_outputs(tmp_path, monkeypatch, case):
    # Build only the names needed to reach the intended guard. No real state files.
    blocks = r.model.BLOCKS[:-1] if case == "missing_block" else r.model.BLOCKS
    if case == "extra_block":
        blocks += (99999,)
    for index in blocks:
        block = tmp_path/f"block_{index}"
        block.mkdir()
        if case in ("missing_life", "extra_life"):
            lives = range(3) if case == "missing_life" else range(5)
            for life in lives:
                r.write_npz(block/f"life_{life}.npz", {})
                r.write_json(block/f"life_{life}.json", dict(synthetic_fixture=True))
    monkeypatch.setattr(r, "read_life", forbidden)
    monkeypatch.setattr(r.model, "load_source", forbidden)
    with pytest.raises(AssertionError):
        r.saved_population(tmp_path, case == "missing_report")


@pytest.mark.parametrize("field", ["component", "future", "pair", "control", "row", "old_futures"])
def test_corrupt_report(tmp_path, monkeypatch, field):
    fake_panel(tmp_path, monkeypatch)
    rows, report, _ = r.saved_population(tmp_path, False)
    if field == "component": report["groups"][0]["cross_replica"]["interaction"] += .1
    elif field == "future": report["groups"][0]["leave_one_future_out"][0]["mean"] += .1
    elif field == "pair": report["groups"][0]["pair_components"][0]["components"]["record"] += .1
    elif field == "control": report["control_cells"][0]["preference"] += .1
    elif field == "row": rows = copy.deepcopy(rows); rows[0]["preference"] += .1
    else: report["old_futures_pooled"] = True
    r.write_json(tmp_path/"records.json", rows)
    r.write_json(tmp_path/"summary.json", report)
    monkeypatch.setattr(r.analysis, "summarize", forbidden)
    with pytest.raises(AssertionError):
        r.saved_population(tmp_path, True)


def test_worker_schedule(tmp_path, monkeypatch):
    events = []
    monkeypatch.setenv(r.ENV, "execute")
    monkeypatch.delenv(r.READY, raising=False)
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r, "frozen", lambda: {})
    monkeypatch.setattr(r, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(r.model, "load_source", lambda index: dict(index=index))
    def simulate(source, index, life):
        assert source == dict(index=index) and index == 90000
        events.append(("simulate", life))
        return {}, dict(index=index, life=life)
    def replay(raw, meta, source, full):
        assert full is True and source == dict(index=meta["index"])
        events.append(("replay", meta["life"]))
        return synthetic_proof()
    def save(directory, life, raw, meta, proof):
        assert directory == tmp_path/"block_90000" and meta["life"] == life
        assert proof["full_physics_replayed"]
        events.append(("save", life))
    def read(directory, index, life, source):
        assert directory == tmp_path/"block_90000" and index == 90000
        events.append(("read", life))
        return {}, synthetic_proof(), []
    monkeypatch.setattr(r.model, "simulate_life", simulate)
    monkeypatch.setattr(r.check, "check_life", replay)
    monkeypatch.setattr(r, "save_life", save)
    monkeypatch.setattr(r, "read_life", read)
    result = r.worker(90000)
    assert result["paths"] == 576 and result["lives"] == 4
    assert events == [(action, life) for life in range(4) for action in ("simulate", "replay", "save", "read")]


@pytest.mark.parametrize("index", [True, 514240, 90001, -1])
def test_bad_worker_address(index):
    with pytest.raises(AssertionError): r.worker(index)


@pytest.mark.parametrize("field,value", [("passes", False), ("full_physics_replayed", False),
                                       ("paths", 72), ("terminal_paths", 144), ("exact_alias_checks", 364)])
def test_bad_replay_proof(field, value):
    proof = synthetic_proof()
    proof[field] = value
    with pytest.raises(AssertionError): r.aggregate_proofs([proof])


def test_wrong_source_metadata(monkeypatch):
    monkeypatch.setattr(r.previous, "read_life", forbidden)
    # Metadata belongs to disposable 514240, not the supplied donor/life.
    with pytest.raises(AssertionError): r.read_life(r.previous.output_dir(), 90000, 0, {})


def test_qualification_no_audit_read(monkeypatch):
    original = r.files.read_json
    def read(path):
        assert Path(path) != r.previous.audit_path()
        return original(path)
    monkeypatch.setattr(r.files, "read_json", read)
    assert len(r.benchmark_inputs()) == 212


@pytest.mark.parametrize("bad", [None, "passes", "new_dynamics", "complete_sha256", "freeze_sha256", "verification"])
def test_audit_linkage(monkeypatch, bad):
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    audit = dict(passes=True, new_dynamics=0, automatic_successor=False,
                 complete_sha256=r.PINS[r.previous.run_dir()/"COMPLETE.json"],
                 freeze_sha256=done["freeze_sha256"], verification=copy.deepcopy(done["verification"]))
    if bad == "passes": audit[bad] = False
    elif bad == "new_dynamics": audit[bad] = 1
    elif bad in ("complete_sha256", "freeze_sha256"): audit[bad] = "0"*64
    elif bad == "verification": audit[bad]["paths"] -= 1
    monkeypatch.setattr(r, "benchmark_inputs", lambda: {"synthetic_input": "bound"})
    def read(path):
        if Path(path) == r.previous.audit_path(): return audit
        assert Path(path) == r.previous.run_dir()/"COMPLETE.json"
        return done
    monkeypatch.setattr(r.files, "read_json", read)
    monkeypatch.setattr(r, "sha256_file", lambda path: "synthetic-audit-digest")
    if bad is not None:
        with pytest.raises(AssertionError): r.source_inputs()
    else:
        assert r.source_inputs()[str(r.previous.audit_path())] == "synthetic-audit-digest"


def test_missing_audit(monkeypatch):
    original = r.files.read_json
    monkeypatch.setattr(r, "benchmark_inputs", lambda: {})
    def read(path):
        if Path(path) == r.previous.audit_path(): raise FileNotFoundError("synthetic absent audit")
        return original(path)
    monkeypatch.setattr(r.files, "read_json", read)
    with pytest.raises(FileNotFoundError): r.source_inputs()


def test_budget_cap():
    done = r.files.read_json(r.previous.run_dir()/"COMPLETE.json")
    result = r.budget(done, 162324280, 1.)
    assert result["conservative_seconds"] == 4*done["seconds"]+182
    assert result["storage_bound_bytes"] == 4*179686742+162324280+64*1024**2
    assert result["parallel_speedup_credit"] is False
    with pytest.raises(AssertionError): r.budget(done, r.previous.CAP, 1.)
    with pytest.raises(AssertionError): r.budget(done, 0, float("nan"))


def test_live_budget_gate(monkeypatch):
    f = dict(uncompressed_benchmark_block_bytes=179686742)
    monkeypatch.setattr(r, "resources", lambda: dict(bytes=162324280))
    assert r.live_budget(f) < r.previous.CAP
    monkeypatch.setattr(r, "resources", lambda: dict(bytes=r.previous.CAP))
    with pytest.raises(AssertionError): r.live_budget(f)


def test_foreground_gate(monkeypatch):
    monkeypatch.delenv(r.ENV, raising=False)
    monkeypatch.setattr(r, "resources", lambda: {})
    monkeypatch.setattr(r, "frozen", lambda: dict(conservative_seconds=4709.))
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
    assert len(rows) == 4 and all(x["new_dynamics"] == 0 and not x["reads_pending_audit"] for x in rows)
    assert all(x["pid"] != os.getpid() and x["source_hashes"] == 212 for x in rows)
    r.write_json(tmp_path/"cold_workers.json", rows)


def test_cold_detached(tmp_path):
    result = r.spawn_detached("startup-check", tmp_path/"startup.log", 30)
    assert result["status"] == "DETACHED_STARTED"
    assert not result["automatic_polling"] and not result["automatic_successor"]
    assert ".poll(" not in inspect.getsource(r.spawn_detached)
    assert "start_new_session=True" in inspect.getsource(r.spawn_detached)
    r.write_json(tmp_path/"startup_receipt.json", result)
