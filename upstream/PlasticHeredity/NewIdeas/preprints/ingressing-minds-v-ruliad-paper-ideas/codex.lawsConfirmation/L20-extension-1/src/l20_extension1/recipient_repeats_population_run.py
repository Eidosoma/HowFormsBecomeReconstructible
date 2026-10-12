"""D181 population orchestration only; the benchmark's science stays frozen."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
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
from . import recipient_repeats_run as previous

ROOT, WS, files = previous.ROOT, previous.WS, previous.files
model, check = previous.model, previous.check
analysis, stats_check = previous.analysis, previous.stats_check
RUN = previous.STEM + "_population_v1_attempt1"
WORKERS = 4
ENV, READY = "D181_POPULATION_STAGE", "D181_POPULATION_READY_FD"
SCIENCE = ("recipient-repeats/POPULATION_EXECUTION_V1.md",
           "src/l20_extension1/recipient_repeats_population_run.py",
           "tests/test_recipient_repeats_population.py",
           "scripts/run_recipient_repeats_population.sh")
PINS = {
    previous.freeze_path(): "26637500c7f5a7599606d88f64bd7b9ef24829aca9caf116040d16b69d50278d",
    previous.run_dir()/"COMPLETE.json": "875916f1297d1f6c603bce99d263ff20bcb35336cbc2d135f900d5b76b5c0737",
}
write_json, write_npz, external = previous.write_json, previous.write_npz, previous.external
verify, resources, time_gate = previous.verify, previous.resources, previous.time_gate
sha256_file, utc_now = previous.sha256_file, previous.utc_now
save_life = previous.save_life
seal_records = previous.previous.seal_records
EXECUTION_OWNED = False


def freeze_path(): return ROOT/"tmp"/(RUN+"_freeze.json")
def output_dir(): return ROOT/"outputs"/RUN
def run_dir(): return ROOT/"runs"/RUN
def audit_path(): return ROOT/"logs"/(RUN+"_saved_audit_v1.json")


def benchmark_inputs():
    """Qualification may read the completed benchmark, never the pending audit."""
    verify({str(p): h for p, h in PINS.items()})
    f = previous.frozen()
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    assert done["status"] == "COMPLETE" and done["verification"]["passes"]
    assert done["freeze_sha256"] == PINS[previous.freeze_path()]
    assert done["main_population_pilot_started"] is done["automatic_successor"] is False
    manifest = previous.run_dir()/"MANIFEST.json"
    assert sha256_file(manifest) == done["manifest_sha256"]
    assert len(done["output_sha256"]) == 8
    assert set(done["output_sha256"]) == {str(p) for p in previous.output_dir().iterdir()}
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
    assert model.BLOCKS == (90000, 90005, 90010, 90015)
    assert model.REPLICAS == (2, 3, 4, 5) and len(model.CELLS) == 144
    verify(expected)
    return expected


def source_inputs():
    """Freeze/execution require the completed formal benchmark audit as well."""
    expected = benchmark_inputs()
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    audit = files.read_json(previous.audit_path())
    assert audit["passes"] and audit["new_dynamics"] == 0
    assert audit["automatic_successor"] is False
    assert audit["complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert audit["freeze_sha256"] == done["freeze_sha256"]
    check.prior.nested(audit["verification"], done["verification"])
    expected[str(previous.audit_path())] = sha256_file(previous.audit_path())
    return expected


def read_life(directory, index, life, source):
    entry = files.read_json(directory/f"life_{life}.json")
    assert entry["metadata"]["index"] == index and entry["metadata"]["life"] == life
    raw, proof = previous.read_life(directory, life, source)
    rows = analysis.extract_records(raw, entry["metadata"])
    assert len(rows) == 288
    return raw, proof, rows


def aggregate_proofs(proofs):
    assert proofs
    for p in proofs:
        assert p["passes"] and p["full_physics_replayed"] is True
        assert (p["paths"], p["generation_paths"], p["terminal_paths"], p["exact_alias_checks"]) == (144, 432, 288, 728)
    return dict(passes=True, lives=len(proofs), paths=144*len(proofs),
                generation_paths=432*len(proofs), terminal_paths=288*len(proofs),
                exact_alias_checks=sum(p["exact_alias_checks"] for p in proofs),
                full_dynamics_replayed_at_generation=True,
                **{k: max(p[k] for p in proofs) for k in proofs[0] if k.endswith("_max_abs")})


def saved_population(directory, expect_report=True):
    expected = {f"block_{index}" for index in model.BLOCKS}
    if expect_report:
        expected |= {"records.json", "summary.json"}
    assert {p.name for p in directory.iterdir()} == expected
    records, proofs = [], []
    for index in model.BLOCKS:
        block = directory/f"block_{index}"
        assert {p.name for p in block.iterdir()} == {
            f"life_{life}.{ext}" for life in range(4) for ext in ("npz", "json")}
        source = model.load_source(index)
        for life in range(4):
            _, proof, rows = read_life(block, index, life, source)
            proofs.append(proof)
            records.extend(rows)
    if expect_report:
        check.prior.nested(files.read_json(directory/"records.json"), records)
        report = files.read_json(directory/"summary.json")
    else:
        report = analysis.summarize(records)
    stats = stats_check.check_report(report, records)
    proof = dict(**aggregate_proofs(proofs), source_records=32, blocks=list(model.BLOCKS),
                 replicas=list(model.REPLICAS), saved_statistics=stats,
                 new_audit_dynamics=0, automatic_successor=False)
    assert proof["lives"] == 16 and proof["paths"] == 2304
    assert proof["generation_paths"] == 6912 and proof["terminal_paths"] == 4608
    return records, report, proof


def qualification(xml):
    external(xml)
    assert xml.parent == ROOT/"logs" and xml.name.startswith(RUN+"_qualification_v") and xml.suffix == ".xml"
    tree = ET.parse(xml).getroot()
    cases = tree.findall(".//testcase")
    assert cases and not any(tree.findall(".//"+key) for key in ("failure", "error", "skipped"))
    assert len(cases) == len({(t.get("classname"), t.get("name")) for t in cases})
    names = {t.get("name").split("[", 1)[0] for t in cases}
    assert {"test_frozen_science_identity", "test_benchmark_hashes", "test_saved_disposable_block",
            "test_population_saved_panel", "test_missing_or_extra_outputs", "test_corrupt_report",
            "test_worker_schedule", "test_bad_worker_address", "test_cold_workers",
            "test_cold_detached", "test_foreground_gate", "test_budget_cap", "test_external_write_once",
            "test_audit_linkage", "test_missing_audit", "test_qualification_no_audit_read",
            "test_live_budget_gate", "test_bad_replay_proof", "test_wrong_source_metadata"} <= names
    fixture = ROOT/"tmp"/xml.stem
    receipt = files.read_json(fixture/"saved_benchmark_check.json")
    assert receipt["benchmark_complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert receipt["new_dynamics"] == 0 and receipt["seconds"] > 0
    check.prior.nested(receipt["verification"], files.read_json(previous.run_dir()/"COMPLETE.json")["verification"])
    return dict(tests=len(cases), fixture=str(fixture), new_dynamics=0,
                checked_disposable_block_seconds=receipt["seconds"], verification=receipt["verification"])


def budget(done, retained_bytes, hash_seconds):
    assert type(retained_bytes) is int and retained_bytes >= 0
    assert np.isfinite(hash_seconds) and hash_seconds >= 0
    seconds = 4*done["seconds"] + 2*hash_seconds + 180
    size = 4*done["verification"]["uncompressed_block_bytes"] + retained_bytes + 64*1024**2
    assert np.isfinite(seconds) and seconds > 600
    assert size <= previous.CAP, "full retention exceeds the fixed 1 GiB stage cap"
    return dict(conservative_seconds=seconds, storage_bound_bytes=size,
                storage_cap_bytes=previous.CAP, parallel_speedup_credit=False)


def live_budget(f):
    retained = resources()
    size = 4*f["uncompressed_benchmark_block_bytes"] + retained["bytes"] + 64*1024**2
    assert size <= previous.CAP, "retained artifacts since freeze exceed the stage budget"
    return size


def freeze(xml):
    resources()
    assert not any(p.exists() for p in (freeze_path(), run_dir(), output_dir(), audit_path()))
    q = qualification(xml)
    tick = time.monotonic()
    inputs, records = source_inputs(), seal_records()
    elapsed = time.monotonic()-tick
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    artifacts = [WS/p for p in SCIENCE]+[xml]
    fixture = ROOT/"tmp"/xml.stem
    artifacts += [p for p in previous.inventory_files() if fixture in p.parents]
    costs = budget(done, resources()["bytes"], elapsed)
    value = dict(schema="d181_repeat_population_freeze_v1", frozen_utc=utc_now(),
                 inputs=inputs, science_qualification=files.hashes(artifacts), qualification=q,
                 source_hash_seconds=elapsed, python=sys.version, numpy=np.__version__,
                 blocks=list(model.BLOCKS), workers=WORKERS, replicas=list(model.REPLICAS),
                 cells=[list(c) for c in model.CELLS], source_record_seals=records,
                 benchmark_seconds=done["seconds"],
                 uncompressed_benchmark_block_bytes=done["verification"]["uncompressed_block_bytes"],
                 **costs, new_predictors=0, automatic_successor=False)
    write_json(freeze_path(), value)
    return {k: v for k, v in value.items() if k not in (
        "inputs", "science_qualification", "qualification", "cells", "source_record_seals")}


def frozen():
    f = files.read_json(freeze_path())
    verify(f["inputs"])
    verify(f["science_qualification"])
    assert f["schema"] == "d181_repeat_population_freeze_v1"
    assert f["python"] == sys.version and f["numpy"] == np.__version__
    assert f["blocks"] == list(model.BLOCKS) and f["workers"] == WORKERS == 4
    assert f["replicas"] == list(model.REPLICAS) == [2, 3, 4, 5]
    assert f["cells"] == [list(c) for c in model.CELLS]
    assert f["source_record_seals"] == seal_records()
    assert f["automatic_successor"] is f["parallel_speedup_credit"] is False
    assert str(previous.audit_path()) in f["inputs"]
    return f


def worker(index):
    assert type(index) is int and index in model.BLOCKS
    assert os.environ.get(ENV) == "execute" and os.environ.get(READY) is None
    resources()
    frozen()
    directory = output_dir()/f"block_{index}"
    directory.mkdir(exist_ok=False)
    source, proofs = model.load_source(index), []
    for life in range(4):
        raw, meta = model.simulate_life(source, index, life)
        proof = check.check_life(raw, meta, source, True)
        save_life(directory, life, raw, meta, proof)
        read_life(directory, index, life, source)
        proofs.append(proof)
        resources()
        print(json.dumps(dict(block=index, life_saved=life, full_replay=True)), flush=True)
    return dict(index=index, **aggregate_proofs(proofs))


def cold_worker(number):
    resources()
    pins = benchmark_inputs()
    return dict(number=number, pid=os.getpid(), source_hashes=len(pins),
                new_dynamics=0, reads_pending_audit=False)


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
        freeze_sha256=sha256_file(freeze_path()), blocks=list(model.BLOCKS),
        workers=WORKERS, replicas=list(model.REPLICAS), forecast_seconds=f["conservative_seconds"],
        storage_bound_at_execution=current_bound, source_record_seals=f["source_record_seals"],
        automatic_successor=False))
    acknowledge()
    tick = time.monotonic()
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(worker, index): index for index in model.BLOCKS}
        for future in as_completed(futures):
            proof = future.result()
            assert proof["index"] == futures[future] and proof["passes"] and proof["lives"] == 4
            print(json.dumps(dict(block_finished=proof["index"], elapsed_seconds=time.monotonic()-tick)), flush=True)
    records, report, first = saved_population(output_dir(), False)
    write_json(output_dir()/"records.json", records)
    write_json(output_dir()/"summary.json", report)
    _, _, proof = saved_population(output_dir(), True)
    check.prior.nested(proof, first)
    verify(f["inputs"])
    verify(f["science_qualification"])
    output = files.hashes(sorted(p for p in output_dir().rglob("*") if p.is_file()))
    assert len(output) == 34
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
    assert len(done["output_sha256"]) == 34
    assert set(done["output_sha256"]) == {str(p) for p in output_dir().rglob("*") if p.is_file()}
    acknowledge()
    tick = time.monotonic()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only audit: no dynamics or production summary construction")
    check.physics.step = analysis.summarize = forbidden
    _, _, proof = saved_population(output_dir(), True)
    check.prior.nested(proof, done["verification"])
    verify(f["inputs"])
    verify(f["science_qualification"])
    result = dict(passes=True, completed_utc=utc_now(), seconds=time.monotonic()-tick,
        complete_sha256=sha256_file(run_dir()/"COMPLETE.json"), freeze_sha256=sha256_file(freeze_path()),
        verification=proof, new_dynamics=0, new_models=0, automatic_successor=False)
    write_json(audit_path(), result)
    return result


def spawn_detached(stage, log, timeout=30):
    assert stage in ("execute", "audit", "startup-check") and 0 < timeout <= 55
    external(log)
    readfd, writefd = os.pipe()
    env = dict(os.environ, **{ENV: stage, READY: str(writefd)})
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-u", "-m", "l20_extension1.recipient_repeats_population_run", "--"+stage],
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
                  numerical_workers=WORKERS if stage == "execute" else 1,
                  started_acknowledgement_utc=utc_now())
    write_json(ROOT/"logs"/(RUN+"_"+stage+"_launch.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", type=Path)
    group.add_argument("--execute", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--launch", choices=("execute", "audit"))
    group.add_argument("--startup-check", action="store_true")
    args = parser.parse_args()
    try:
        if args.startup_check:
            resources()
            benchmark_inputs()
            rows = cold_workers()
            acknowledge()
            result = dict(startup_passes=True, workers=len(rows), new_dynamics=0, reads_pending_audit=False)
        else:
            result = freeze(args.freeze) if args.freeze else launch(args.launch) if args.launch else execute() if args.execute else audit()
        print(json.dumps(result, sort_keys=True), flush=True)
    except Exception as exc:
        if args.execute and EXECUTION_OWNED and not (run_dir()/"COMPLETE.json").exists() and not (run_dir()/"FAILED.json").exists():
            write_json(run_dir()/"FAILED.json", dict(failed_utc=utc_now(), error=str(exc),
                traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == "__main__":
    main()
