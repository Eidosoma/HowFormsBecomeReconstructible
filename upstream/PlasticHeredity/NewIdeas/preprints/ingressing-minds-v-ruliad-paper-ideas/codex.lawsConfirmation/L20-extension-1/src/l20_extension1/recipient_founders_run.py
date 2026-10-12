"""D182 fresh-futures disposable benchmark; population execution deliberately absent."""
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
from . import recipient_founders as model, recipient_founders_check as check
from . import recipient_founders_source as sources, recipient_founders_source_check as source_check
from . import recipient_founders_analysis as analysis, recipient_founders_analysis_check as stats_check

ROOT, WS, files = model.ROOT, model.WS, model.files
STEM = "l20_extension1_recipient_founders"
RUN = STEM + "_benchmark_v1_attempt1"
CAP, RESERVE = 1024**3, 4*1024**3
ENV, READY = "D182_DETACHED_STAGE", "D182_READY_FD"
SCIENCE = ("recipient-founders/PROTOCOL_V1.md",
           "src/l20_extension1/recipient_founders.py",
           "src/l20_extension1/recipient_founders_check.py",
           "src/l20_extension1/recipient_founders_analysis.py",
           "src/l20_extension1/recipient_founders_analysis_check.py",
           "src/l20_extension1/recipient_founders_run.py",
           "tests/test_recipient_founders.py", "scripts/run_recipient_founders.sh",
           "src/l20_extension1/recipient_founders_source.py",
           "src/l20_extension1/recipient_founders_source_check.py",
           "recipient-founders/EXECUTION_CONTRACT.md",
           "recipient-founders/check_design.py")
DESIGN = ROOT/"logs"/(STEM+"_design_v1.json")
DESIGN_SHA = "f7faab67fbae5ebaa71c2eea816ad5163a419181e4ff8ad02333aa137a578cf0"
QUAL_ENV = "D182_QUALIFICATION_FREEZE"
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
    assert sha256_file(DESIGN) == DESIGN_SHA
    design = files.read_json(DESIGN)
    expected = dict(design["scientific_inputs_sha256"])
    assert len(expected) == 765
    expected[str(DESIGN)] = DESIGN_SHA
    verify(expected)
    assert design["protocol_sha256"] == sha256_file(WS/"recipient-founders/PROTOCOL_V1.md")
    assert design["checker_sha256"] == sha256_file(WS/"recipient-founders/check_design.py")
    assert model.BLOCKS == sources.BLOCKS == source_check.BLOCKS == (120000,120005,120010,120015)
    assert model.DISPOSABLE == sources.DISPOSABLE == 514260 and model.CANONICAL_RECIPIENT == 514240
    assert model.CONFIG == sources.CONFIG and model.REPLICAS == (2,3,4,5)
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
    return expected


def inventory_files():
    result = []
    for area in ("tmp", "logs", "outputs", "runs"):
        for root in (ROOT / area).glob(STEM + "*"):
            assert not root.is_symlink()
            for path in ([root] if root.is_file() else root.rglob("*")):
                if path.is_symlink():
                    target = path.resolve(strict=True)
                    assert "_qualification_v" in root.name or "_preflight_v" in root.name
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


def qualify_life(directory, source, index, life):
    assert type(index) is int and index == model.DISPOSABLE
    raw, meta = model.simulate_life(source, index, life)
    try:
        proof = check.check_life(raw, meta, source, True)
    except Exception:
        save_life(directory, life, raw, meta, dict(passes=False))
        raise
    save_life(directory, life, raw, meta, proof)
    loaded, checked = read_life(directory, life, source)
    for key in raw: np.testing.assert_array_equal(loaded[key], raw[key])
    return raw, meta, proof


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


def preparation_path(xml):
    external(xml)
    assert xml.parent == ROOT/"logs" and xml.name.startswith(RUN+"_qualification_v") and xml.suffix == ".xml"
    return ROOT/"tmp"/(xml.stem+"_prefreeze.json")


def prepare(xml):
    resources()
    assert not xml.exists() and not (ROOT/"tmp"/xml.stem).exists()
    assert not any(p.exists() for p in (freeze_path(),run_dir(),output_dir()))
    inputs = source_inputs()
    value = dict(schema="d182_before_acquisition_v1", frozen_utc=utc_now(),
        inputs=inputs, science_sha256=files.hashes(WS/p for p in SCIENCE),
        python=sys.version, numpy=np.__version__, qualification_xml=str(xml),
        main_indices=list(model.BLOCKS), disposable=model.DISPOSABLE,
        founder_namespace=sources.TAG, future_namespace=model.TAG,
        founder_phases=list(sources.PHASES), future_phases=list(model.PHASES),
        replicas=list(model.REPLICAS), new_main_founders_allowed=False,
        new_founders_generated=0, automatic_successor=False)
    write_json(preparation_path(xml),value)
    return dict(status="PRE_ACQUISITION_FROZEN",path=str(preparation_path(xml)),
                sha256=sha256_file(preparation_path(xml)),inputs=len(inputs),science=len(SCIENCE))


def prequalified(path):
    path = external(path)
    f = files.read_json(path)
    assert f["schema"] == "d182_before_acquisition_v1"
    assert path == preparation_path(Path(f["qualification_xml"]))
    verify(f["inputs"]); verify(f["science_sha256"])
    assert f["science_sha256"] == files.hashes(WS/p for p in SCIENCE)
    assert f["inputs"][str(DESIGN)] == DESIGN_SHA
    assert f["python"] == sys.version and f["numpy"] == np.__version__
    assert f["main_indices"] == list(model.BLOCKS) and f["disposable"] == 514260
    assert f["founder_namespace"] == sources.TAG and f["future_namespace"] == model.TAG
    assert f["founder_phases"] == list(sources.PHASES) and f["future_phases"] == list(model.PHASES)
    assert f["replicas"] == [2,3,4,5] and f["new_main_founders_allowed"] is False
    return f


def generate_disposable(directory, lives, preparation):
    """Only disposable acquisition is executable in this stage."""
    assert lives in ((0,), (0,1,2,3))
    prequalified(preparation)
    external(directory).mkdir(parents=True,exist_ok=False)
    index = model.DISPOSABLE
    guide = model.old.load_guide()
    raw_rows, meta_rows, bundles, proofs = [], [], [], []
    for life in lives:
        raw,meta = sources.generate_founders(index,life)
        # Retain raw output before its qualification; failures are never erased.
        write_npz(directory/f"acquisition_{life}.npz",raw)
        write_json(directory/f"acquisition_{life}.json",meta)
        bundle = sources.make_bundle(raw,guide)
        proof = source_check.check_source(raw,meta,bundle,True)
        write_json(directory/f"replay_{life}.json",proof)
        raw_rows.append(raw);meta_rows.append(meta);bundles.append(bundle);proofs.append(proof)
    founders = {key:np.stack([r[key] for r in raw_rows]) for key in sources.FOUNDER_KEYS}
    bundle = {key:np.stack([r[key] for r in bundles]) for key in sources.SOURCE_ARRAYS}
    write_npz(directory/"founders.npz",founders)
    write_json(directory/"founders.json",dict(schema="d182_founder_archive_v1",index=index,
        lives=list(lives),metadata=meta_rows,preparation_sha256=sha256_file(preparation)))
    write_npz(directory/"bundle.npz",bundle)
    write_json(directory/"bundle.json",dict(schema="d182_f0_bundle_v1",index=index,lives=list(lives),
        config=model.asdict(model.CONFIG),guide_sha256=model.old.GUIDE_SHA256,
        founder_artifacts={n:sha256_file(directory/n) for n in ("founders.npz","founders.json")},
        bundle_sha256=sha256_file(directory/"bundle.npz"),record_seals=sources.packet_seals(bundle,index,lives),
        record_definition="encode(written_fields[family,0]); not acquired theta"))
    return read_source(directory,index,lives,sha256_file(preparation))


def source_names(lives):
    return {"founders.npz","founders.json","bundle.npz","bundle.json"} | {
        f"{kind}_{life}.{ext}" for life in lives
        for kind,ext in (("acquisition","npz"),("acquisition","json"),("replay","json"))}


def read_source(directory,index,lives,preparation_sha):
    assert {p.name for p in directory.iterdir()} == source_names(lives)
    source = sources.load_source(directory,index,lives)
    raw = files.load_npz(directory/"founders.npz")
    entry = files.read_json(directory/"founders.json")
    assert set(entry) == {"schema","index","lives","metadata","preparation_sha256"}
    assert entry["schema"] == "d182_founder_archive_v1" and entry["index"] == index
    assert entry["lives"] == list(lives) and entry["preparation_sha256"] == preparation_sha
    assert set(raw) == set(sources.FOUNDER_KEYS) and len(entry["metadata"]) == len(lives)
    assert all(a.shape[0] == len(lives) for a in raw.values())
    for i,life in enumerate(lives):
        individual = files.load_npz(directory/f"acquisition_{life}.npz")
        meta = entry["metadata"][i]
        assert meta["index"] == index and meta["life"] == life
        check.prior.nested(meta,files.read_json(directory/f"acquisition_{life}.json"))
        assert set(individual) == set(raw)
        for key in raw: np.testing.assert_array_equal(raw[key][i],individual[key])
        proof = source_check.check_source(individual,meta,{k:v[i] for k,v in source.items()},False)
        original = files.read_json(directory/f"replay_{life}.json")
        compare_proofs(proof,original)
    return source


def seal_sources(directories,preparation_sha,indices):
    """Pure sealing gate also qualified synthetically for all four main sources."""
    assert indices in (model.BLOCKS,(model.DISPOSABLE,))
    assert len(directories) == len(indices) and set(directories) == set(indices)
    assert len({Path(p).resolve() for p in directories.values()}) == len(indices)
    mappings,records = {},[]
    for index in indices:
        directory = external(directories[index])
        source = read_source(directory,index,(0,1,2,3),preparation_sha)
        mappings[index] = dict(directory=str(directory),sha256=files.hashes(sorted(directory.iterdir())))
        records += sources.packet_seals(source,index,(0,1,2,3))
    assert len(records) == len({(x["index"],x["life"],x["family"]) for x in records}) == 8*len(indices)
    return dict(schema="d182_all_sources_seal_v1",sealed_utc=utc_now(),indices=list(indices),
        preparation_sha256=preparation_sha,sources={str(k):v for k,v in mappings.items()},
        record_seals=records,guide_sha256=model.old.GUIDE_SHA256,descendants_generated=0)


def require_seal(seal,preparation_sha,indices):
    assert set(seal) == {"schema","sealed_utc","indices","preparation_sha256","sources",
                         "record_seals","guide_sha256","descendants_generated"}
    assert seal["schema"] == "d182_all_sources_seal_v1" and seal["indices"] == list(indices)
    assert seal["preparation_sha256"] == preparation_sha and seal["descendants_generated"] == 0
    assert seal["guide_sha256"] == model.old.GUIDE_SHA256
    assert set(seal["sources"]) == {str(i) for i in indices}
    directories = {}
    for index in indices:
        entry = seal["sources"][str(index)]
        assert set(entry) == {"directory","sha256"}
        path = external(entry["directory"])
        verify(entry["sha256"])
        assert set(entry["sha256"]) == {str(p) for p in path.iterdir()}
        directories[index] = path
    expected = seal_sources(directories,preparation_sha,indices)
    expected["sealed_utc"] = seal["sealed_utc"]
    check.prior.nested(seal,expected)
    return True


def uncompressed_bytes(directory):
    count = 0
    for p in directory.rglob("*"):
        if p.is_file():
            count += sum(a.nbytes for a in files.load_npz(p).values()) if p.suffix == ".npz" else p.stat().st_size
    return count


def qualification(xml):
    external(xml)
    prequalified(preparation_path(xml))
    tree = ET.parse(xml).getroot()
    cases = tree.findall(".//testcase")
    assert cases and not any(tree.findall(".//" + x) for x in ("failure","error","skipped"))
    assert len(cases) == len({(t.get("classname"),t.get("name")) for t in cases})
    names = {t.get("name").split("[",1)[0] for t in cases}
    assert {"test_complete_disposable_life","test_independent_replay","test_saved_no_dynamics",
            "test_native_bridge","test_physics_ast_unchanged","test_seed_disjointness",
            "test_corruption","test_source_boundary","test_source_hashes",
            "test_time_gate","test_cold_start","test_signed_components","test_analysis_independent",
            "test_missing_life","test_order_guard","test_receipt_write_once",
            "test_bad_summary","test_rows_and_corruption","test_new_only_panel",
            "test_source_independent","test_source_corruption","test_all_sources_sealing",
            "test_bad_seal","test_pre_acquisition_freeze","test_no_main_route",
            "test_founder_bridge","test_wrong_f0","test_false_freshness"} <= names
    fixture = ROOT/"tmp"/xml.stem/"life_fixture"
    timing = files.read_json(fixture/"timing.json")
    assert timing["seconds"] > 0 and timing["full_replay_and_io"] is timing["includes_source_acquisition"] is True
    source = read_source(fixture/"source",model.DISPOSABLE,(0,),sha256_file(preparation_path(xml)))
    _,proof = read_life(fixture/"descendants",0,source)
    return dict(tests=len(cases),checked_life_seconds=timing["seconds"],life_proof=proof,
                fixture=str(fixture),complete_life_uncompressed_bytes=uncompressed_bytes(fixture))


def freeze(xml):
    resources()
    assert not any(p.exists() for p in (freeze_path(),run_dir(),output_dir(),audit_path()))
    q = qualification(xml)
    start = time.monotonic()
    inputs = source_inputs()
    hash_seconds = time.monotonic()-start
    fixture_root = ROOT/"tmp"/xml.stem
    artifacts = [WS/p for p in SCIENCE] + [xml,preparation_path(xml)]
    artifacts += [p for p in inventory_files() if fixture_root in p.parents]
    value = dict(schema="d182_founder_benchmark_freeze_v1",frozen_utc=utc_now(),
        inputs=inputs,science_qualification=files.hashes(artifacts),qualification=q,
        preparation_path=str(preparation_path(xml)),preparation_sha256=sha256_file(preparation_path(xml)),
        source_hash_seconds=hash_seconds,
        conservative_seconds=4*q["checked_life_seconds"]+2*hash_seconds+120,
        python=sys.version,numpy=np.__version__,source_index=514260,lives=[0,1,2,3],
        replicas=list(model.REPLICAS),cells=[list(c) for c in model.CELLS],
        proposed_storage_cap=CAP,main_population_pilot_allowed=False,new_predictors=0,automatic_successor=False)
    value["benchmark_storage_bound"] = resources()["bytes"]+4*q["complete_life_uncompressed_bytes"]+64*1024**2
    assert value["benchmark_storage_bound"] <= CAP
    write_json(freeze_path(),value)
    return {k:v for k,v in value.items() if k not in ("inputs","science_qualification","cells","qualification")}


def frozen():
    f = files.read_json(freeze_path())
    verify(f["inputs"]); verify(f["science_qualification"])
    assert f["schema"] == "d182_founder_benchmark_freeze_v1"
    assert f["python"] == sys.version and f["numpy"] == np.__version__
    assert f["source_index"] == 514260 and f["lives"] == [0,1,2,3]
    assert f["cells"] == [list(c) for c in model.CELLS] and f["replicas"] == [2,3,4,5]
    assert f["main_population_pilot_allowed"] is False
    assert sha256_file(Path(f["preparation_path"])) == f["preparation_sha256"]
    prequalified(Path(f["preparation_path"]))
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
    source = generate_disposable(output_dir()/"source",(0,1,2,3),Path(f["preparation_path"]))
    seal = seal_sources({model.DISPOSABLE:output_dir()/"source"},f["preparation_sha256"],(model.DISPOSABLE,))
    write_json(output_dir()/"SOURCE_SEAL.json",seal)
    require_seal(files.read_json(output_dir()/"SOURCE_SEAL.json"),f["preparation_sha256"],(model.DISPOSABLE,))
    (output_dir()/"descendants").mkdir(exist_ok=False)
    for life in range(4):
        qualify_life(output_dir()/"descendants", source, model.DISPOSABLE, life)
        resources()
        print(json.dumps(dict(disposable_life_saved=life, full_replay=True,
                              elapsed_seconds=time.monotonic()-start)), flush=True)
    proof = saved_experiment(f)
    verify(f["inputs"])
    verify(f["science_qualification"])
    output_hashes = files.hashes(sorted(p for p in output_dir().rglob("*") if p.is_file()))
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



def saved_experiment(f):
    assert {p.name for p in output_dir().iterdir()} == {"source","descendants","SOURCE_SEAL.json"}
    seal = files.read_json(output_dir()/"SOURCE_SEAL.json")
    require_seal(seal,f["preparation_sha256"],(model.DISPOSABLE,))
    source = read_source(output_dir()/"source",model.DISPOSABLE,(0,1,2,3),f["preparation_sha256"])
    proof = saved_block(output_dir()/"descendants",source)
    proof["uncompressed_block_bytes"] = uncompressed_bytes(output_dir())
    proof["fresh_source_acquisitions"] = 8
    proof["source_writers"] = 16
    proof["source_archive_and_bundle_checked"] = True
    proof["all_f0_sealed_before_descendants"] = True
    return proof


def audit():
    resources()
    f = frozen()
    time_gate(f["conservative_seconds"], os.environ.get(ENV) == "audit")
    assert not audit_path().exists()
    done = files.read_json(run_dir() / "COMPLETE.json")
    assert done["status"] == "COMPLETE" and done["freeze_sha256"] == sha256_file(freeze_path())
    assert done["manifest_sha256"] == sha256_file(run_dir() / "MANIFEST.json")
    verify(done["output_sha256"])
    assert set(done["output_sha256"]) == {str(p) for p in output_dir().rglob("*") if p.is_file()}
    acknowledge()
    start = time.monotonic()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved audit must not step tissue dynamics")
    check.physics.step = forbidden
    proof = saved_experiment(f)
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
            child = subprocess.Popen([sys.executable, "-u", "-m", "l20_extension1.recipient_founders_run", "--"+stage],
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
    assert resources()["bytes"] + 4*f["qualification"]["complete_life_uncompressed_bytes"] + 64*1024**2 <= CAP
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
            source_inputs()
            acknowledge()
            result = dict(startup_passes=True, new_dynamics=0, population_route=False)
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
