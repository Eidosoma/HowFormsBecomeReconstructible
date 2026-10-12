"""D182 population orchestration; fresh acquisition precedes an all-source barrier."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import json
import multiprocessing
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import traceback
import types
import xml.etree.ElementTree as ET
import numpy as np
from . import recipient_founders_run as previous

ROOT, WS, files = previous.ROOT, previous.WS, previous.files
model, check = previous.model, previous.check
sources, source_check = previous.sources, previous.source_check
analysis, stats_check = previous.analysis, previous.stats_check
RUN = previous.STEM + "_population_v1_attempt1"
WORKERS = 4
ENV, READY = "D182_POPULATION_STAGE", "D182_POPULATION_READY_FD"
QUAL_ENV = "D182_POPULATION_QUALIFICATION_FREEZE"
SCIENCE = ("recipient-founders/POPULATION_EXECUTION_V1.md",
           "src/l20_extension1/recipient_founders_population_run.py",
           "tests/test_recipient_founders_population.py",
           "scripts/run_recipient_founders_population.sh")
PINS = {
    previous.freeze_path(): "1e8dc0dd9afb84bd7187ae789e0385d0859ea6d0f6c962227153b53ab551b415",
    previous.run_dir()/"COMPLETE.json": "843324d9c489df63ae1c9d1adabfe9005d8e6022eab81b773c4e9435bf81eda8",
    previous.audit_path(): "fd0e44efc058ad56ee91957e556cb0c3a4644214c5f7f9215a3bf3a7d9015bde",
}
write_json, write_npz, external = previous.write_json, previous.write_npz, previous.external
verify, resources, time_gate = previous.verify, previous.resources, previous.time_gate
sha256_file, utc_now = previous.sha256_file, previous.utc_now
save_life = previous.save_life
EXECUTION_OWNED = False


def freeze_path(): return ROOT/"tmp"/(RUN+"_freeze.json")
def output_dir(): return ROOT/"outputs"/RUN
def run_dir(): return ROOT/"runs"/RUN
def audit_path(): return ROOT/"logs"/(RUN+"_saved_audit_v1.json")


def plan():
    return dict(blocks=list(model.BLOCKS), disposable=model.DISPOSABLE,
        lives=[0, 1, 2, 3], workers=WORKERS, replicas=list(model.REPLICAS),
        cells=[list(c) for c in model.CELLS], founder_namespace=sources.TAG,
        future_namespace=model.TAG, founder_phases=list(sources.PHASES),
        future_phases=list(model.PHASES), canonical_recipient=model.CANONICAL_RECIPIENT,
        config=model.asdict(model.CONFIG), guide_sha256=model.old.GUIDE_SHA256)


def audit_linkage(done, audit):
    assert audit["passes"] is True and audit["new_dynamics"] == 0
    assert audit["automatic_successor"] is False
    assert audit["complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert audit["freeze_sha256"] == done["freeze_sha256"] == PINS[previous.freeze_path()]
    check.prior.nested(audit["verification"], done["verification"])


def source_inputs():
    """Bind the reviewed benchmark, formal audit and every inherited dependency."""
    verify({str(p): h for p, h in PINS.items()})
    f = previous.frozen()
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    assert done["status"] == "COMPLETE" and done["verification"]["passes"] is True
    assert done["main_population_pilot_started"] is done["automatic_successor"] is False
    audit_linkage(done, files.read_json(previous.audit_path()))
    manifest = previous.run_dir()/"MANIFEST.json"
    assert sha256_file(manifest) == done["manifest_sha256"]
    assert len(done["output_sha256"]) == 25
    assert set(done["output_sha256"]) == {str(p) for p in previous.output_dir().rglob("*") if p.is_file()}
    expected = dict(f["inputs"])
    expected.update(f["science_qualification"])
    expected.update({str(p): h for p, h in PINS.items()})
    expected.update(done["output_sha256"])
    expected[str(manifest)] = done["manifest_sha256"]
    allowed = {str((WS/p).resolve()) for p in SCIENCE}
    pending, seen = list(sys.modules.values())+[check.prior, check.physics], set()
    while pending:
        module = pending.pop()
        if not isinstance(module, types.ModuleType) or id(module) in seen:
            continue
        seen.add(id(module))
        name = getattr(module, "__file__", None)
        if not name:
            continue
        path = Path(name).resolve()
        if model.old.ORIGIN not in path.parents or path.suffix != ".py":
            continue
        pending.extend(x for x in vars(module).values() if isinstance(x, types.ModuleType))
        assert str(path) in expected or str(path) in allowed, "unbound source: "+str(path)
    assert model.BLOCKS == sources.BLOCKS == (120000, 120005, 120010, 120015)
    assert model.DISPOSABLE == 514260 and model.CANONICAL_RECIPIENT == 514240
    assert model.REPLICAS == (2, 3, 4, 5) and len(model.CELLS) == 144
    verify(expected)
    return expected


def preparation_path(xml):
    external(xml)
    assert xml.parent == ROOT/"logs" and xml.name.startswith(RUN+"_qualification_v") and xml.suffix == ".xml"
    return ROOT/"tmp"/(xml.stem+"_prefreeze.json")


def prepare(xml):
    resources()
    assert not xml.exists() and not (ROOT/"tmp"/xml.stem).exists()
    assert not any(p.exists() for p in (preparation_path(xml), freeze_path(), run_dir(), output_dir()))
    inputs = source_inputs()
    # One measured checked life, saved block/audit checks, cold startup and tests.
    f = previous.frozen()
    audit = files.read_json(previous.audit_path())
    seconds = 1.2*f["qualification"]["checked_life_seconds"]+2*audit["seconds"]+90
    time_gate(seconds)
    value = dict(schema="d182_population_qualification_freeze_v1", frozen_utc=utc_now(),
        inputs=inputs, science_sha256=files.hashes(WS/p for p in SCIENCE),
        python=sys.version, numpy=np.__version__, qualification_xml=str(xml), plan=plan(),
        qualification_forecast_seconds=seconds, new_main_founders_allowed=False,
        new_main_founders_generated=0, automatic_successor=False)
    write_json(preparation_path(xml), value)
    return dict(status="QUALIFICATION_PRE_ACQUISITION_FROZEN", path=str(preparation_path(xml)),
        sha256=sha256_file(preparation_path(xml)), forecast_seconds=seconds, inputs=len(inputs), science=len(SCIENCE))


def prequalified(path):
    path = external(path)
    f = files.read_json(path)
    assert f["schema"] == "d182_population_qualification_freeze_v1"
    assert path == preparation_path(Path(f["qualification_xml"]))
    verify(f["inputs"]); verify(f["science_sha256"])
    assert f["science_sha256"] == files.hashes(WS/p for p in SCIENCE)
    assert f["inputs"][str(previous.audit_path())] == PINS[previous.audit_path()]
    assert f["python"] == sys.version and f["numpy"] == np.__version__
    assert f["plan"] == plan() and f["new_main_founders_allowed"] is False
    assert f["new_main_founders_generated"] == 0 and f["automatic_successor"] is False
    return f


def generate_source(directory, index, lives, preparation, *, main=False):
    """Gated acquisition; serialization is the benchmark's retained source format."""
    assert type(index) is int and type(main) is bool
    directory, preparation = external(directory), external(preparation)
    if main:
        assert index in model.BLOCKS and lives == (0, 1, 2, 3)
        assert os.environ.get(ENV) == "execute" and os.environ.get(READY) is None
        assert preparation == freeze_path()
        frozen()
        assert directory == output_dir()/"sources"/f"block_{index}"
        assert not (output_dir()/"SOURCE_SEAL.json").exists()
        assert not (output_dir()/"DESCENDANTS_STARTED.json").exists()
        assert not (output_dir()/"descendants").exists()
    else:
        assert index == model.DISPOSABLE and lives == (0,)
        q = prequalified(preparation)
        fixture = ROOT/"tmp"/Path(q["qualification_xml"]).stem
        assert directory == fixture/"life_fixture"/"source"
    directory.mkdir(parents=True, exist_ok=False)
    guide = model.old.load_guide()
    raw_rows, meta_rows, bundles = [], [], []
    for life in lives:
        raw, meta = sources.generate_founders(index, life)
        write_npz(directory/f"acquisition_{life}.npz", raw)
        write_json(directory/f"acquisition_{life}.json", meta)
        bundle = sources.make_bundle(raw, guide)
        proof = source_check.check_source(raw, meta, bundle, True)
        write_json(directory/f"replay_{life}.json", proof)
        raw_rows.append(raw); meta_rows.append(meta); bundles.append(bundle)
    founders = {key: np.stack([r[key] for r in raw_rows]) for key in sources.FOUNDER_KEYS}
    bundle = {key: np.stack([r[key] for r in bundles]) for key in sources.SOURCE_ARRAYS}
    write_npz(directory/"founders.npz", founders)
    write_json(directory/"founders.json", dict(schema="d182_founder_archive_v1", index=index,
        lives=list(lives), metadata=meta_rows, preparation_sha256=sha256_file(preparation)))
    write_npz(directory/"bundle.npz", bundle)
    write_json(directory/"bundle.json", dict(schema="d182_f0_bundle_v1", index=index, lives=list(lives),
        config=model.asdict(model.CONFIG), guide_sha256=model.old.GUIDE_SHA256,
        founder_artifacts={n: sha256_file(directory/n) for n in ("founders.npz", "founders.json")},
        bundle_sha256=sha256_file(directory/"bundle.npz"), record_seals=sources.packet_seals(bundle, index, lives),
        record_definition="encode(written_fields[family,0]); not acquired theta"))
    return previous.read_source(directory, index, lives, sha256_file(preparation))


def read_seal(directory, preparation_sha):
    assert {p.name for p in (directory/"sources").iterdir()} == {f"block_{i}" for i in model.BLOCKS}
    seal = files.read_json(directory/"SOURCE_SEAL.json")
    previous.require_seal(seal, preparation_sha, model.BLOCKS)
    for index in model.BLOCKS:
        assert seal["sources"][str(index)]["directory"] == str(directory/"sources"/f"block_{index}")
    assert len(seal["record_seals"]) == 32
    return seal


def acquire_all_sources(directory, preparation):
    """No descendant directory or task exists until every new source is checked."""
    assert directory == output_dir() and preparation == freeze_path()
    assert not (directory/"descendants").exists()
    (directory/"sources").mkdir(exist_ok=False)
    for index in model.BLOCKS:
        generate_source(directory/"sources"/f"block_{index}", index, (0, 1, 2, 3), preparation, main=True)
        resources()
        print(json.dumps(dict(source_block_saved=index, descendants_generated=0)), flush=True)
    seal = previous.seal_sources({i: directory/"sources"/f"block_{i}" for i in model.BLOCKS},
                                 sha256_file(preparation), model.BLOCKS)
    write_json(directory/"SOURCE_SEAL.json", seal)
    read_seal(directory, sha256_file(preparation))
    return seal


def start_descendants(directory, preparation_sha):
    seal = read_seal(directory, preparation_sha)
    assert not (directory/"descendants").exists()
    value = dict(schema="d182_descendant_barrier_v1", started_utc=utc_now(),
        preparation_sha256=preparation_sha, source_seal_sha256=sha256_file(directory/"SOURCE_SEAL.json"),
        source_records=32, blocks=list(model.BLOCKS), all_sources_checked_before_descendants=True)
    assert datetime.fromisoformat(seal["sealed_utc"]) <= datetime.fromisoformat(value["started_utc"])
    write_json(directory/"DESCENDANTS_STARTED.json", value)
    (directory/"descendants").mkdir(exist_ok=False)


def require_barrier(directory, preparation_sha):
    seal = read_seal(directory, preparation_sha)
    entry = files.read_json(directory/"DESCENDANTS_STARTED.json")
    assert set(entry) == {"schema", "started_utc", "preparation_sha256", "source_seal_sha256",
                          "source_records", "blocks", "all_sources_checked_before_descendants"}
    assert entry["schema"] == "d182_descendant_barrier_v1"
    assert entry["preparation_sha256"] == preparation_sha
    assert entry["source_seal_sha256"] == sha256_file(directory/"SOURCE_SEAL.json")
    assert entry["source_records"] == 32 and entry["blocks"] == list(model.BLOCKS)
    assert entry["all_sources_checked_before_descendants"] is True
    assert datetime.fromisoformat(seal["sealed_utc"]) <= datetime.fromisoformat(entry["started_utc"])
    return seal


def read_life(directory, index, life, source):
    entry = files.read_json(directory/f"life_{life}.json")
    assert entry["metadata"]["index"] == index and entry["metadata"]["life"] == life
    raw, proof = previous.read_life(directory, life, source)
    rows = analysis.extract_records(raw, entry["metadata"])
    assert len(rows) == 288
    return raw, proof, rows


def run_life(directory, source, index, life):
    raw, meta = model.simulate_life(source, index, life)
    try:
        proof = check.check_life(raw, meta, source, True)
    except Exception:
        save_life(directory, life, raw, meta, dict(passes=False))
        raise
    save_life(directory, life, raw, meta, proof)
    loaded, checked, _ = read_life(directory, index, life, source)
    for key in raw:
        np.testing.assert_array_equal(loaded[key], raw[key])
    return checked


def aggregate_proofs(proofs):
    assert proofs
    for p in proofs:
        assert p["passes"] is p["full_physics_replayed"] is True
        assert (p["paths"], p["generation_paths"], p["terminal_paths"], p["exact_alias_checks"]) == (144, 432, 288, 728)
    return dict(passes=True, lives=len(proofs), paths=144*len(proofs), generation_paths=432*len(proofs),
        terminal_paths=288*len(proofs), exact_alias_checks=sum(p["exact_alias_checks"] for p in proofs),
        full_dynamics_replayed_at_generation=True,
        **{k: max(p[k] for p in proofs) for k in proofs[0] if k.endswith("_max_abs")})


def saved_population(directory, preparation_sha, expect_report=True):
    expected = {"sources", "descendants", "SOURCE_SEAL.json", "DESCENDANTS_STARTED.json"}
    if expect_report:
        expected |= {"records.json", "summary.json"}
    assert {p.name for p in directory.iterdir()} == expected
    require_barrier(directory, preparation_sha)
    assert {p.name for p in (directory/"descendants").iterdir()} == {f"block_{i}" for i in model.BLOCKS}
    records, proofs, source_proofs = [], [], []
    for index in model.BLOCKS:
        block = directory/"descendants"/f"block_{index}"
        assert {p.name for p in block.iterdir()} == {f"life_{life}.{ext}" for life in range(4) for ext in ("npz", "json")}
        source_dir = directory/"sources"/f"block_{index}"
        source = sources.load_source(source_dir, index)
        for life in range(4):
            _, proof, rows = read_life(block, index, life, source)
            proofs.append(proof); records.extend(rows)
            p = files.read_json(source_dir/f"replay_{life}.json")
            assert p["passes"] is p["full_physics_replayed"] is True
            assert (p["source_records"], p["acquired_records"], p["source_readers"], p["source_writers"]) == (2, 2, 2, 4)
            source_proofs.append(p)
    if expect_report:
        check.prior.nested(files.read_json(directory/"records.json"), records)
        report = files.read_json(directory/"summary.json")
    else:
        report = analysis.summarize(records)
    stats = stats_check.check_report(report, records)
    proof = dict(**aggregate_proofs(proofs), source_records=32, fresh_source_acquisitions=32,
        source_writers=64, blocks=list(model.BLOCKS), replicas=list(model.REPLICAS), saved_statistics=stats,
        source_max_abs={k: max(p[k] for p in source_proofs) for k in source_proofs[0] if k.endswith("_max_abs")},
        all_f0_sealed_before_descendants=True, source_archive_and_bundle_checked=True,
        new_audit_dynamics=0, automatic_successor=False)
    assert proof["lives"] == 16 and proof["paths"] == 2304
    assert proof["generation_paths"] == 6912 and proof["terminal_paths"] == 4608
    return records, report, proof


def qualification(xml):
    prequalified(preparation_path(xml))
    tree = ET.parse(xml).getroot()
    cases = tree.findall(".//testcase")
    assert cases and not any(tree.findall(".//"+key) for key in ("failure", "error", "skipped"))
    assert len(cases) == len({(t.get("classname"), t.get("name")) for t in cases})
    names = {t.get("name").split("[", 1)[0] for t in cases}
    assert {"test_frozen_science_identity", "test_benchmark_hashes", "test_complete_disposable_life",
        "test_saved_disposable_block", "test_population_saved_panel", "test_missing_or_extra_outputs",
        "test_corrupt_report", "test_worker_schedule", "test_bad_worker_address", "test_cold_workers",
        "test_cold_detached", "test_foreground_gate", "test_budget_cap", "test_external_write_once",
        "test_audit_linkage", "test_live_budget_gate", "test_bad_replay_proof", "test_wrong_source_metadata",
        "test_source_schedule", "test_source_barrier", "test_failed_acquisition_stops_barrier",
        "test_bad_seal", "test_no_main_acquisition", "test_failure_retention", "test_pre_acquisition_freeze",
        "test_source_failure_retention", "test_wrong_barrier", "test_source_address_guard",
        "test_execution_phase_order"} <= names
    fixture = ROOT/"tmp"/xml.stem
    life = fixture/"life_fixture"
    timing = files.read_json(life/"timing.json")
    assert timing["seconds"] > 0 and timing["full_replay_and_io"] is timing["includes_source_acquisition"] is True
    source = previous.read_source(life/"source", model.DISPOSABLE, (0,), sha256_file(preparation_path(xml)))
    _, proof, _ = read_life(life/"descendants", model.DISPOSABLE, 0, source)
    benchmark = files.read_json(fixture/"saved_benchmark_check.json")
    assert benchmark["benchmark_complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert benchmark["new_dynamics"] == 0 and benchmark["seconds"] > 0
    check.prior.nested(benchmark["verification"], files.read_json(previous.run_dir()/"COMPLETE.json")["verification"])
    return dict(tests=len(cases), fixture=str(fixture), checked_life_seconds=timing["seconds"],
        life_proof=proof, new_main_founders_generated=0, checked_disposable_block_seconds=benchmark["seconds"])


def budget(done, retained_bytes, hash_seconds):
    assert type(retained_bytes) is int and retained_bytes >= 0
    assert np.isfinite(hash_seconds) and hash_seconds >= 0
    seconds = 4*done["seconds"]+2*hash_seconds+180
    size = 4*done["verification"]["uncompressed_block_bytes"]+retained_bytes+64*1024**2
    assert np.isfinite(seconds) and seconds > 600
    assert size <= previous.CAP, "full retention exceeds the fixed 1 GiB stage cap"
    return dict(conservative_seconds=seconds, storage_bound_bytes=size,
        storage_cap_bytes=previous.CAP, parallel_speedup_credit=False)


def live_budget(f):
    size = 4*f["uncompressed_benchmark_block_bytes"]+resources()["bytes"]+64*1024**2
    assert size <= previous.CAP, "retained artifacts since freeze exceed the stage budget"
    return size


def freeze(xml):
    resources()
    assert not any(p.exists() for p in (freeze_path(), run_dir(), output_dir(), audit_path()))
    q = qualification(xml)
    tick = time.monotonic()
    inputs = source_inputs()
    elapsed = time.monotonic()-tick
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    fixture = ROOT/"tmp"/xml.stem
    artifacts = [WS/p for p in SCIENCE]+[xml, preparation_path(xml)]
    artifacts += [p for p in previous.inventory_files() if fixture in p.parents]
    costs = budget(done, resources()["bytes"], elapsed)
    value = dict(schema="d182_founder_population_freeze_v1", frozen_utc=utc_now(),
        inputs=inputs, science_qualification=files.hashes(artifacts), qualification=q,
        source_hash_seconds=elapsed, python=sys.version, numpy=np.__version__, plan=plan(),
        preparation_path=str(preparation_path(xml)), preparation_sha256=sha256_file(preparation_path(xml)),
        benchmark_seconds=done["seconds"], uncompressed_benchmark_block_bytes=done["verification"]["uncompressed_block_bytes"],
        **costs, new_main_founders_generated=0, new_predictors=0, automatic_successor=False)
    write_json(freeze_path(), value)
    return {k: v for k, v in value.items() if k not in ("inputs", "science_qualification", "qualification", "plan")}


def frozen():
    f = files.read_json(freeze_path())
    verify(f["inputs"]); verify(f["science_qualification"])
    assert f["schema"] == "d182_founder_population_freeze_v1"
    assert f["python"] == sys.version and f["numpy"] == np.__version__ and f["plan"] == plan()
    assert f["automatic_successor"] is f["parallel_speedup_credit"] is False
    assert f["new_main_founders_generated"] == f["new_predictors"] == 0
    assert f["inputs"][str(previous.audit_path())] == PINS[previous.audit_path()]
    for path, digest in files.hashes(WS/p for p in SCIENCE).items():
        assert f["science_qualification"].get(path) == digest
    assert sha256_file(Path(f["preparation_path"])) == f["preparation_sha256"]
    prequalified(Path(f["preparation_path"]))
    return f


def worker(index):
    assert type(index) is int and index in model.BLOCKS
    assert os.environ.get(ENV) == "execute" and os.environ.get(READY) is None
    resources(); frozen()
    require_barrier(output_dir(), sha256_file(freeze_path()))
    directory = output_dir()/"descendants"/f"block_{index}"
    directory.mkdir(exist_ok=False)
    source = sources.load_source(output_dir()/"sources"/f"block_{index}", index)
    proofs = []
    for life in range(4):
        proofs.append(run_life(directory, source, index, life))
        resources()
        print(json.dumps(dict(block=index, life_saved=life, full_replay=True)), flush=True)
    return dict(index=index, **aggregate_proofs(proofs))


def cold_worker(number):
    resources()
    pins = source_inputs()
    return dict(number=number, pid=os.getpid(), source_hashes=len(pins), new_dynamics=0)


def cold_workers():
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        rows = list(pool.map(cold_worker, range(WORKERS)))
    assert [x["number"] for x in rows] == list(range(WORKERS))
    assert all(x["pid"] != os.getpid() and x["new_dynamics"] == 0 for x in rows)
    return rows


def acknowledge():
    fd = os.environ.pop(READY, None)
    if fd is not None:
        assert os.environ.get(ENV) in ("execute", "audit", "startup-check")
        assert os.getsid(0) == os.getpid()
        os.write(int(fd), b"READY\n")
        os.close(int(fd))


def execute():
    global EXECUTION_OWNED
    resources()
    f = frozen()
    time_gate(f["conservative_seconds"], os.environ.get(ENV) == "execute")
    assert os.environ.get(ENV) == "execute" and os.getsid(0) == os.getpid()
    current_bound = live_budget(f)
    run_dir().mkdir(parents=True, exist_ok=False)
    EXECUTION_OWNED = True
    output_dir().mkdir(parents=True, exist_ok=False)
    write_json(run_dir()/"MANIFEST.json", dict(started_utc=utc_now(),
        freeze_sha256=sha256_file(freeze_path()), plan=plan(), forecast_seconds=f["conservative_seconds"],
        storage_bound_at_execution=current_bound, new_main_founders_generated=0, automatic_successor=False))
    acknowledge()
    tick = time.monotonic()
    acquire_all_sources(output_dir(), freeze_path())
    start_descendants(output_dir(), sha256_file(freeze_path()))
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(worker, index): index for index in model.BLOCKS}
        for future in as_completed(futures):
            proof = future.result()
            assert proof["index"] == futures[future] and proof["passes"] and proof["lives"] == 4
            print(json.dumps(dict(block_finished=proof["index"], elapsed_seconds=time.monotonic()-tick)), flush=True)
    records, report, first = saved_population(output_dir(), sha256_file(freeze_path()), False)
    write_json(output_dir()/"records.json", records)
    write_json(output_dir()/"summary.json", report)
    _, _, proof = saved_population(output_dir(), sha256_file(freeze_path()), True)
    check.prior.nested(proof, first)
    verify(f["inputs"]); verify(f["science_qualification"])
    output = files.hashes(sorted(p for p in output_dir().rglob("*") if p.is_file()))
    assert len(output) == 100
    result = dict(status="COMPLETE", completed_utc=utc_now(), seconds=time.monotonic()-tick,
        freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(run_dir()/"MANIFEST.json"),
        output_sha256=output, verification=proof, resources=resources(),
        prospective_prediction=False, new_predictors=0, automatic_successor=False)
    write_json(run_dir()/"COMPLETE.json", result)
    return {k: v for k, v in result.items() if k != "output_sha256"}


def audit():
    resources()
    f = frozen()
    time_gate(f["conservative_seconds"], os.environ.get(ENV) == "audit")
    assert not audit_path().exists()
    done = files.read_json(run_dir()/"COMPLETE.json")
    assert done["status"] == "COMPLETE" and done["freeze_sha256"] == sha256_file(freeze_path())
    assert done["manifest_sha256"] == sha256_file(run_dir()/"MANIFEST.json")
    verify(done["output_sha256"])
    assert len(done["output_sha256"]) == 100
    assert set(done["output_sha256"]) == {str(p) for p in output_dir().rglob("*") if p.is_file()}
    acknowledge()
    tick = time.monotonic()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only audit: no dynamics, acquisition or production summary construction")
    check.physics.step = model.simulate_life = sources.generate_founders = analysis.summarize = forbidden
    _, _, proof = saved_population(output_dir(), sha256_file(freeze_path()), True)
    check.prior.nested(proof, done["verification"])
    verify(f["inputs"]); verify(f["science_qualification"])
    result = dict(passes=True, completed_utc=utc_now(), seconds=time.monotonic()-tick,
        complete_sha256=sha256_file(run_dir()/"COMPLETE.json"), freeze_sha256=sha256_file(freeze_path()),
        verification=proof, resources=resources(), new_dynamics=0, new_models=0, automatic_successor=False)
    write_json(audit_path(), result)
    return result


def spawn_detached(stage, log, timeout=30):
    assert stage in ("execute", "audit", "startup-check") and 0 < timeout <= 55
    external(log)
    readfd, writefd = os.pipe()
    env = dict(os.environ, **{ENV: stage, READY: str(writefd)})
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-u", "-m", "l20_extension1.recipient_founders_population_run", "--"+stage],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                cwd=WS.parent, env=env, start_new_session=True, pass_fds=(writefd,))
    finally:
        os.close(writefd)
    ready = select.select([readfd], [], [], timeout)[0]
    message = os.read(readfd, 64) if ready else b""
    os.close(readfd)
    return dict(status="DETACHED_STARTED" if message == b"READY\n" else "STARTUP_NOT_ACKNOWLEDGED",
        stage=stage, pid=child.pid, log=str(log), automatic_polling=False, automatic_successor=False)


def launch(stage):
    resources()
    f = frozen()
    assert stage in ("execute", "audit")
    if stage == "execute":
        assert not run_dir().exists() and not output_dir().exists()
        bound = live_budget(f)
    else:
        assert (run_dir()/"COMPLETE.json").exists() and not audit_path().exists()
        bound = f["storage_bound_bytes"]
    result = spawn_detached(stage, ROOT/"logs"/(RUN+"_"+stage+".log"),
                           min(55., max(10., 2*f["source_hash_seconds"]+10)))
    result.update(forecast_seconds=f["conservative_seconds"], storage_bound_bytes=bound,
        numerical_workers=WORKERS if stage == "execute" else 1, started_acknowledgement_utc=utc_now())
    write_json(ROOT/"logs"/(RUN+"_"+stage+"_launch.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", type=Path)
    group.add_argument("--freeze", type=Path)
    group.add_argument("--execute", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--launch", choices=("execute", "audit"))
    group.add_argument("--startup-check", action="store_true")
    args = parser.parse_args()
    try:
        if args.startup_check:
            resources()
            rows = cold_workers()
            acknowledge()
            result = dict(startup_passes=True, workers=len(rows), new_dynamics=0)
        else:
            result = prepare(args.prepare) if args.prepare else freeze(args.freeze) if args.freeze else launch(args.launch) if args.launch else execute() if args.execute else audit()
        print(json.dumps(result, sort_keys=True), flush=True)
    except Exception as exc:
        if args.execute and EXECUTION_OWNED and not (run_dir()/"COMPLETE.json").exists() and not (run_dir()/"FAILED.json").exists():
            write_json(run_dir()/"FAILED.json", dict(failed_utc=utc_now(), error=str(exc),
                traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == "__main__":
    main()
