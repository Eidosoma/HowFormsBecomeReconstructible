"""D181 fresh-futures disposable benchmark; population execution deliberately absent."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import traceback
import types
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation.io import sha256_file, utc_now
from . import recipient_repeats as model, recipient_repeats_check as check
from . import recipient_coupling_pilot_run as previous
from . import recipient_repeats_analysis as analysis, recipient_repeats_analysis_check as stats_check

ROOT, WS, files = model.ROOT, model.WS, model.files
STEM = "l20_extension1_recipient_repeats"
RUN = STEM + "_benchmark_v1_attempt1"
CAP, RESERVE = 1024**3, 4*1024**3
ENV, READY = "D181_DETACHED_STAGE", "D181_READY_FD"
SCIENCE = ("recipient-repeats/PROTOCOL_V1.md",
           "src/l20_extension1/recipient_repeats.py",
           "src/l20_extension1/recipient_repeats_check.py",
           "src/l20_extension1/recipient_repeats_analysis.py",
           "src/l20_extension1/recipient_repeats_analysis_check.py",
           "src/l20_extension1/recipient_repeats_run.py",
           "tests/test_recipient_repeats.py", "scripts/run_recipient_repeats.sh")
PINS = {
    previous.freeze_path(): "7a7b0beef0c967b0235ab944add0d25bd9ec241960a575cd7b32d81a344a445b",
    previous.run_dir()/"COMPLETE.json": "49b265d13daff99fef5e66570af3e7d55e4143310b497fb4349757930a00b60e",
    previous.audit_path(): "38713e9227a2741d3c6e4aa54d3d65d55591651817fe355a763b1fc47301e2f9",
}
EXECUTION_OWNED = False


def freeze_path(): return ROOT / "tmp" / (RUN + "_freeze.json")
def output_dir(): return ROOT / "outputs" / RUN
def run_dir(): return ROOT / "runs" / RUN
def audit_path(): return ROOT / "logs" / (RUN + "_saved_audit_v1.json")


def external(path):
    path = Path(path)
    assert ROOT.resolve() in path.resolve().parents
    assert not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
    return path


def write_json(path, value):
    external(path).parent.mkdir(parents=True, exist_ok=True)
    files.write_json(path, value, ROOT)


def write_npz(path, value):
    external(path).parent.mkdir(parents=True, exist_ok=True)
    files.write_npz(path, value, ROOT)


def verify(mapping):
    for path, digest in mapping.items():
        p = Path(path)
        assert p.is_file() and not p.is_symlink() and sha256_file(p) == digest, path


def source_inputs():
    verify({str(p):h for p,h in PINS.items()})
    old = previous.frozen()
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    audit = files.read_json(previous.audit_path())
    assert done["status"] == "COMPLETE" and audit["passes"] and audit["new_dynamics"] == audit["new_models"] == 0
    assert audit["complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert audit["freeze_sha256"] == done["freeze_sha256"] == PINS[previous.freeze_path()]
    check.prior.nested(audit["verification"],done["verification"])
    expected = dict(old["inputs"])
    expected.update(old["science_qualification"])
    expected.update({str(p):h for p,h in PINS.items()})
    expected.update(done["output_sha256"])
    expected[str(previous.run_dir()/"MANIFEST.json")] = done["manifest_sha256"]
    allowed = {str((WS/p).resolve()) for p in SCIENCE}
    pending,seen = list(sys.modules.values())+[check.prior,check.physics],set()
    while pending:
        module = pending.pop()
        if not isinstance(module,types.ModuleType) or id(module) in seen:
            continue
        seen.add(id(module))
        name = getattr(module,"__file__",None)
        if not name: continue
        path = Path(name).resolve()
        if model.old.ORIGIN not in path.parents or path.suffix != ".py": continue
        pending.extend(x for x in vars(module).values() if isinstance(x,types.ModuleType))
        assert str(path) in expected or str(path) in allowed, "unbound source: "+str(path)
    assert model.BLOCKS == previous.model.BLOCKS and model.TAG == previous.model.TAG
    assert model.COUPLINGS == previous.model.COUPLINGS and model.CONDITIONS == previous.model.CONDITIONS
    assert model.CONFIG == previous.model.CONFIG and model.REPLICAS == (2,3,4,5)
    verify(expected)
    return expected


def inventory_files():
    result = []
    for area in ("tmp", "logs", "outputs", "runs"):
        for root in (ROOT / area).glob(STEM + "*"):
            assert not root.is_symlink()
            for path in ([root] if root.is_file() else root.rglob("*")):
                if path.is_symlink():
                    target = path.resolve(strict=True)
                    assert "_qualification_v" in root.name
                    assert path.name.endswith("current") and target.parent == path.parent.resolve()
                    stem = path.name[:-7]
                    assert target.name.startswith(stem) and target.name[len(stem):].isdigit() and target.is_dir()
                elif path.is_file():
                    result.append(path)
    return sorted(set(result))


def resources():
    assert not sys.flags.optimize and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    affinity = sorted(os.sched_getaffinity(0))
    assert affinity and set(affinity) <= set(range(6))
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert os.environ.get(key) == "1"
    for key in ("TMPDIR", "XDG_CACHE_HOME"):
        p = Path(os.environ.get(key, "/")).resolve()
        assert ROOT in p.parents and p.is_dir()
    retained = inventory_files()
    size = sum(p.stat().st_size for p in retained)
    assert size < CAP and shutil.disk_usage(ROOT).free >= CAP + RESERVE
    return dict(bytes=size, files=len(retained), cap_bytes=CAP,
                reserve_bytes=RESERVE, affinity=affinity, numerical_threads=1)


def time_gate(seconds, detached=False):
    assert type(seconds) in (float, int) and np.isfinite(seconds) and seconds > 0
    if seconds > 600 and not detached:
        raise RuntimeError("Above ten minutes: use --launch, durable log and no polling")
    return seconds > 600


def compare_proofs(current, original):
    assert current["passes"] and original["passes"] and original["full_physics_replayed"] is True
    assert set(current) == set(original)
    for key in current:
        if key.endswith("_max_abs"):
            limit = 1e-12 if key in ("metric_max_abs", "selector_max_abs", "feature_max_abs") else 1e-10
            assert 0 <= original[key] <= limit
            if key in ("metric_max_abs", "selector_max_abs", "feature_max_abs"):
                assert abs(current[key] - original[key]) <= 1e-12
        elif key != "full_physics_replayed":
            assert current[key] == original[key]


def save_life(directory, life, raw, meta, proof):
    write_npz(directory / f"life_{life}.npz", raw)
    write_json(directory / f"life_{life}.json", dict(metadata=meta, replay=proof))


def read_life(directory, life, source):
    raw = files.load_npz(directory / f"life_{life}.npz")
    entry = files.read_json(directory / f"life_{life}.json")
    assert entry["metadata"]["life"] == life
    proof = check.check_life(raw, entry["metadata"], source, False)
    compare_proofs(proof, entry["replay"])
    rows = analysis.extract_records(raw, entry["metadata"])
    stats_check.check_rows(rows, raw, entry["metadata"])
    return raw, entry["replay"]


def saved_block(directory, source):
    assert {p.name for p in directory.iterdir()} == {
        f"life_{life}.{ext}" for life in range(4) for ext in ("npz", "json")}
    proofs, raw_bytes = [], 0
    for life in range(4):
        raw, proof = read_life(directory, life, source)
        raw_bytes += sum(a.nbytes for a in raw.values())
        raw_bytes += (directory / f"life_{life}.json").stat().st_size
        proofs.append(proof)
    worst = {k: max(p[k] for p in proofs) for k in proofs[0] if k.endswith("_max_abs")}
    return dict(passes=True, lives=4, source_records=8, paths=576, generation_paths=1728,
                terminal_paths=1152, independent_replay_at_generation=True, new_audit_dynamics=0,
                uncompressed_block_bytes=raw_bytes,
                exact_alias_checks=sum(p["exact_alias_checks"] for p in proofs), **worst)


def qualification(xml):
    external(xml)
    assert xml.parent == ROOT / "logs" and xml.name.startswith(RUN + "_qualification_v") and xml.suffix == ".xml"
    tree = ET.parse(xml).getroot()
    cases = tree.findall(".//testcase")
    assert cases and not any(tree.findall(".//" + x) for x in ("failure", "error", "skipped"))
    assert len(cases) == len({(t.get("classname"), t.get("name")) for t in cases})
    names = {t.get("name").split("[", 1)[0] for t in cases}
    assert {"test_complete_disposable_life","test_independent_replay","test_saved_no_dynamics",
            "test_native_bridge","test_physics_ast_unchanged","test_seed_disjointness",
            "test_corruption","test_source_boundary","test_source_hashes",
            "test_time_gate","test_cold_start","test_signed_components","test_analysis_independent",
            "test_missing_life","test_order_guard","test_receipt_write_once",
            "test_bad_summary","test_rows_and_corruption","test_new_only_panel"} <= names
    fixture = ROOT / "tmp" / xml.stem / "life_fixture"
    timing = files.read_json(fixture / "timing.json")
    assert timing["seconds"] > 0 and timing["full_replay_and_io"] is True
    source = model.load_source(514240)
    _, proof = read_life(fixture, 0, source)
    return dict(tests=len(cases), checked_life_seconds=timing["seconds"],
                life_proof=proof, fixture=str(fixture))


def freeze(xml):
    resources()
    assert not any(p.exists() for p in (freeze_path(), run_dir(), output_dir(), audit_path()))
    q = qualification(xml)
    start = time.monotonic()
    inputs = source_inputs()
    hash_seconds = time.monotonic() - start
    fixture_root = ROOT / "tmp" / xml.stem
    artifacts = [WS / p for p in SCIENCE] + [xml]
    artifacts += [p for p in inventory_files() if fixture_root in p.parents]
    value = dict(schema="d181_repeat_benchmark_freeze_v1", frozen_utc=utc_now(),
                 inputs=inputs, science_qualification=files.hashes(artifacts),
                 qualification=q, source_hash_seconds=hash_seconds,
                 conservative_seconds=4*q["checked_life_seconds"] + 2*hash_seconds + 120,
                 python=sys.version, numpy=np.__version__, source_index=514240,
                 lives=[0,1,2,3], replicas=list(model.REPLICAS),
                 source_record_seals=previous.seal_records(), cells=[list(c) for c in model.CELLS],
                 proposed_storage_cap=CAP, main_population_pilot_allowed=False,
                 new_predictors=0, automatic_successor=False)
    raw, _ = read_life(Path(q["fixture"]), 0, model.load_source(514240))
    one_life_bytes = sum(v.nbytes for v in raw.values()) + (Path(q["fixture"]) / "life_0.json").stat().st_size
    value["benchmark_storage_bound"] = resources()["bytes"] + 4*one_life_bytes + 64*1024**2
    assert value["benchmark_storage_bound"] <= CAP
    write_json(freeze_path(), value)
    return {k:v for k,v in value.items() if k not in ("inputs", "science_qualification", "cells", "qualification")}


def frozen():
    f = files.read_json(freeze_path())
    verify(f["inputs"])
    verify(f["science_qualification"])
    assert f["schema"] == "d181_repeat_benchmark_freeze_v1"
    assert f["python"] == sys.version and f["numpy"] == np.__version__
    assert f["source_index"] == 514240 and f["lives"] == [0,1,2,3]
    assert f["cells"] == [list(c) for c in model.CELLS]
    assert f["replicas"] == list(model.REPLICAS) == [2,3,4,5]
    assert f["source_record_seals"] == previous.seal_records()
    assert f["main_population_pilot_allowed"] is False
    return f


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
    run_dir().mkdir(parents=True, exist_ok=False)
    EXECUTION_OWNED = True
    output_dir().mkdir(parents=True, exist_ok=False)
    write_json(run_dir() / "MANIFEST.json", dict(started_utc=utc_now(),
        freeze_sha256=sha256_file(freeze_path()), forecast_seconds=f["conservative_seconds"],
        serial_benchmark=True, main_population_pilot_started=False, automatic_successor=False))
    acknowledge()
    start = time.monotonic()
    source = model.load_source(514240)
    for life in range(4):
        raw, meta = model.simulate_life(source, 514240, life)
        proof = check.check_life(raw, meta, source, True)
        save_life(output_dir(), life, raw, meta, proof)
        read_life(output_dir(), life, source)
        resources()
        print(json.dumps(dict(disposable_life_saved=life, full_replay=True,
                              elapsed_seconds=time.monotonic()-start)), flush=True)
    proof = saved_block(output_dir(), source)
    verify(f["inputs"])
    verify(f["science_qualification"])
    output_hashes = files.hashes(sorted(output_dir().iterdir()))
    elapsed = time.monotonic() - start
    retained = resources()
    main_seconds = 4*elapsed + 2*f["source_hash_seconds"] + 180
    main_bytes = 4*proof["uncompressed_block_bytes"] + retained["bytes"] + 64*1024**2
    result = dict(status="COMPLETE", completed_utc=utc_now(), seconds=elapsed,
        freeze_sha256=sha256_file(freeze_path()), manifest_sha256=sha256_file(run_dir()/"MANIFEST.json"),
        output_sha256=output_hashes, verification=proof, resources=retained,
        main_conservative_seconds=main_seconds, main_storage_bound=main_bytes,
        main_within_storage_cap=main_bytes <= CAP, main_requires_detach=main_seconds > 600,
        main_population_pilot_started=False, automatic_successor=False)
    write_json(run_dir() / "COMPLETE.json", result)
    return {k:v for k,v in result.items() if k != "output_sha256"}


def audit():
    resources()
    f = frozen()
    time_gate(f["conservative_seconds"], os.environ.get(ENV) == "audit")
    assert not audit_path().exists()
    done = files.read_json(run_dir() / "COMPLETE.json")
    assert done["status"] == "COMPLETE" and done["freeze_sha256"] == sha256_file(freeze_path())
    assert done["manifest_sha256"] == sha256_file(run_dir() / "MANIFEST.json")
    verify(done["output_sha256"])
    assert set(done["output_sha256"]) == {str(p) for p in output_dir().iterdir()}
    acknowledge()
    start = time.monotonic()
    source = model.load_source(514240)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved audit must not step tissue dynamics")
    check.physics.step = forbidden
    proof = saved_block(output_dir(), source)
    check.prior.nested(proof, done["verification"])
    verify(f["inputs"])
    verify(f["science_qualification"])
    result = dict(passes=True, completed_utc=utc_now(), seconds=time.monotonic()-start,
        complete_sha256=sha256_file(run_dir()/"COMPLETE.json"), freeze_sha256=sha256_file(freeze_path()),
        verification=proof, resources=resources(), new_dynamics=0, automatic_successor=False)
    write_json(audit_path(), result)
    return result


def spawn_detached(stage, log, timeout=30):
    assert stage in ("execute", "audit", "startup-check") and 0 < timeout <= 55
    external(log)
    readfd, writefd = os.pipe()
    env = dict(os.environ, **{ENV:stage, READY:str(writefd)})
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-u", "-m", "l20_extension1.recipient_repeats_run", "--"+stage],
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
    else:
        assert (run_dir() / "COMPLETE.json").exists() and not audit_path().exists()
    result = spawn_detached(stage, ROOT/"logs"/(RUN+"_"+stage+".log"),
                            min(55., max(10., 2*f["source_hash_seconds"]+10)))
    result["forecast_seconds"] = f["conservative_seconds"]
    result["started_acknowledgement_utc"] = utc_now()
    result["storage_bound_bytes"] = f["benchmark_storage_bound"]
    result["numerical_workers"] = 1
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
            source_inputs()
            acknowledge()
            result = dict(startup_passes=True, new_dynamics=0, population_route=False)
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
