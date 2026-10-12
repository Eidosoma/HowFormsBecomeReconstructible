"""D180 frozen four-donor execution and saved-only audit; no automatic successor."""
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
from . import recipient_coupling_run as previous
from . import recipient_coupling_pilot as model, recipient_coupling_pilot_check as check
from . import recipient_coupling_pilot_analysis as analysis, recipient_coupling_pilot_analysis_check as stats_check

ROOT, WS, files = previous.ROOT, previous.WS, previous.files
RUN = "l20_extension1_recipient_coupling_pilot_v1_attempt1"
WORKERS = 4
ENV, READY = "D180_DETACHED_STAGE", "D180_READY_FD"
SCIENCE = ("recipient-variation/PILOT_EXECUTION_V1.md",
    "src/l20_extension1/recipient_coupling_pilot.py",
    "src/l20_extension1/recipient_coupling_pilot_check.py",
    "src/l20_extension1/recipient_coupling_pilot_analysis.py",
    "src/l20_extension1/recipient_coupling_pilot_analysis_check.py",
    "src/l20_extension1/recipient_coupling_pilot_run.py",
    "tests/test_recipient_coupling_pilot.py", "scripts/run_recipient_coupling_pilot.sh")
PINS = {
    previous.freeze_path(): "9fc6aec95c54e536b1cf241629c3ad942ae6b0a706411743fb993d0841bc6b7f",
    previous.run_dir()/"COMPLETE.json": "610fe3a10f3746ed16eee8ccdba5ad4a9205638ced97141774251436b2bbdb6a",
    previous.audit_path(): "72fa6cc6ef3f196cf0b38f2036f75494b3b63fc8c98b2e9fac934833fb8eb6b4",
}
write_json, write_npz, external = previous.write_json, previous.write_npz, previous.external
verify, resources, time_gate = previous.verify, previous.resources, previous.time_gate
sha256_file, utc_now = previous.sha256_file, previous.utc_now
EXECUTION_OWNED = False


def freeze_path(): return ROOT/"tmp"/(RUN+"_freeze.json")
def output_dir(): return ROOT/"outputs"/RUN
def run_dir(): return ROOT/"runs"/RUN
def audit_path(): return ROOT/"logs"/(RUN+"_saved_audit_v1.json")


def source_inputs():
    verify({str(p):h for p,h in PINS.items()})
    old = previous.frozen()
    done = files.read_json(previous.run_dir()/"COMPLETE.json")
    audit = files.read_json(previous.audit_path())
    assert done["status"] == "COMPLETE" and audit["passes"] and audit["new_dynamics"] == 0
    assert audit["complete_sha256"] == PINS[previous.run_dir()/"COMPLETE.json"]
    assert audit["freeze_sha256"] == done["freeze_sha256"] == PINS[previous.freeze_path()]
    check.prior.nested(audit["verification"],done["verification"])
    expected = dict(old["inputs"])
    expected.update(old["science_qualification"])
    expected.update({str(p):h for p,h in PINS.items()})
    expected.update(done["output_sha256"])
    expected[str(previous.run_dir()/"MANIFEST.json")] = done["manifest_sha256"]
    # Source donors already fixed in D178's header-only design receipt.
    source_done = files.read_json(ROOT/"runs"/model.SOURCE/"COMPLETE.json")
    for index in model.BLOCKS:
        for p in model.source_paths(index):
            assert expected[str(p)] == source_done["output_sha256"][str(p)]
    design = previous.design_module()
    assert model.BLOCKS == tuple(design.BLOCKS)
    assert model.COUPLINGS == tuple(design.COUPLINGS) and model.CONDITIONS == tuple(design.CONDITIONS)
    assert model.TAG == design.TAG and model.CONFIG == previous.model.CONFIG
    new = {str((WS/p).resolve()) for p in SCIENCE}
    history = files.read_json(ROOT/"runs"/model.SOURCE/"MANIFEST.json")["input_sha256"]
    pending = list(sys.modules.values())+[check.prior,check.physics]
    seen = set()
    while pending:
        module = pending.pop()
        if not isinstance(module,types.ModuleType) or id(module) in seen:
            continue
        seen.add(id(module))
        name = getattr(module,"__file__",None)
        if not name: continue
        p = Path(name).resolve()
        if model.old.ORIGIN not in p.parents or p.suffix != ".py": continue
        pending.extend(x for x in vars(module).values() if isinstance(x,types.ModuleType))
        if str(p) not in new and str(p) not in expected:
            assert str(p) in history, "unbound inherited code: "+str(p)
            expected[str(p)] = history[str(p)]
    verify(expected)
    return expected


def seal_records():
    seals = []
    for index in model.BLOCKS:
        source = model.load_source(index)
        for life in range(4):
            for role in (0,1):
                seals.append(dict(index=index,life=life,family=role,
                    sha256=check.prior.sha(source["founder_packets"][life,role].tobytes())))
    return seals


def save_life(directory, life, raw, meta, proof):
    write_npz(directory/f"life_{life}.npz",raw)
    write_json(directory/f"life_{life}.json",dict(metadata=meta,replay=proof))


def read_life(directory, index, life, source):
    raw = files.load_npz(directory/f"life_{life}.npz")
    saved = files.read_json(directory/f"life_{life}.json")
    meta = saved["metadata"]
    assert meta["index"] == index and meta["life"] == life
    proof = check.check_life(raw,meta,source,False)
    previous.compare_proofs(proof,saved["replay"])
    rows = analysis.extract_records(raw,meta)
    stats_check.check_rows(rows,raw,meta)
    return raw,saved,rows


def aggregate_proofs(proofs):
    return dict(passes=True,lives=len(proofs),paths=72*len(proofs),
        generation_paths=216*len(proofs),terminal_paths=144*len(proofs),
        exact_alias_checks=sum(p["exact_alias_checks"] for p in proofs),
        full_dynamics_replayed_at_generation=True,
        **{k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith("_max_abs")})


def saved_pilot(directory, expect_report=True):
    names={p.name for p in directory.iterdir()}
    expected={f"block_{index}" for index in model.BLOCKS}
    if expect_report: expected |= {"records.json","summary.json"}
    assert names == expected
    records,proofs = [],[]
    for index in model.BLOCKS:
        block=directory/f"block_{index}"
        assert {p.name for p in block.iterdir()}=={f"life_{life}.{ext}" for life in range(4) for ext in ("npz","json")}
        source=model.load_source(index)
        for life in range(4):
            _,entry,rows=read_life(block,index,life,source)
            proofs.append(entry["replay"])
            records.extend(rows)
    if expect_report:
        check.prior.nested(files.read_json(directory/"records.json"),records)
        report=files.read_json(directory/"summary.json")
    else:
        report=analysis.summarize(records)
    stats=stats_check.check_report(report,records)
    proof=dict(**aggregate_proofs(proofs),source_records=32,blocks=list(model.BLOCKS),
               saved_statistics=stats,new_audit_dynamics=0,automatic_successor=False)
    return records,report,proof


def qualification(xml):
    external(xml)
    assert xml.parent==ROOT/"logs" and xml.name.startswith(RUN+"_qualification_v") and xml.suffix==".xml"
    tree=ET.parse(xml).getroot()
    cases=tree.findall(".//testcase")
    assert cases and not any(tree.findall(".//"+s) for s in ("failure","error","skipped"))
    assert len(cases)==len({(x.get("classname"),x.get("name")) for x in cases})
    names={x.get("name").split("[",1)[0] for x in cases}
    assert {"test_complete_bridge","test_independent_replay","test_saved_no_dynamics",
        "test_physics_ast_unchanged","test_analysis_independent","test_corrupt_summary",
        "test_negative_components","test_block_pooling","test_source_boundary",
        "test_readout_rows","test_cold_workers","test_cold_detached","test_missing_block",
        "test_foreground_gate","test_external_write_once"} <= names
    fixture=ROOT/"tmp"/xml.stem/"life_fixture"
    raw,entry,rows=read_life(fixture,514240,0,model.load_source(514240))
    timing=files.read_json(fixture/"timing.json")
    assert timing["full_replay_io_and_bridge"] and timing["seconds"]>0
    return dict(tests=len(cases),seconds=timing["seconds"],fixture=str(fixture),
                life_proof=entry["replay"],readout_rows=len(rows))


def freeze(xml):
    resources()
    assert not any(p.exists() for p in (freeze_path(),run_dir(),output_dir(),audit_path()))
    q=qualification(xml)
    tick=time.monotonic()
    inputs=source_inputs()
    records=seal_records()
    elapsed=time.monotonic()-tick
    done=files.read_json(previous.run_dir()/"COMPLETE.json")
    assert done["main_within_storage_cap"] and WORKERS==4
    fixture=ROOT/"tmp"/xml.stem
    artifacts=[WS/p for p in SCIENCE]+[xml]
    artifacts += [p for p in previous.inventory_files() if fixture in p.parents]
    remaining=resources()
    storage=4*done["verification"]["uncompressed_block_bytes"]+remaining["bytes"]+64*1024**2
    assert storage<=previous.CAP
    value=dict(schema="d180_pilot_freeze_v1",frozen_utc=utc_now(),inputs=inputs,
        science_qualification=files.hashes(artifacts),qualification=q,source_hash_seconds=elapsed,
        python=sys.version,numpy=np.__version__,blocks=list(model.BLOCKS),workers=WORKERS,
        cells=[list(c) for c in model.CELLS],source_record_seals=records,
        benchmark_seconds=done["seconds"],conservative_seconds=4*done["seconds"]+2*elapsed+180,
        storage_bound_bytes=storage,storage_cap_bytes=previous.CAP,parallel_speedup_credit=False,
        new_predictors=0,automatic_successor=False)
    write_json(freeze_path(),value)
    return {k:v for k,v in value.items() if k not in ("inputs","science_qualification","qualification","source_record_seals","cells")}


def frozen():
    f=files.read_json(freeze_path())
    verify(f["inputs"])
    verify(f["science_qualification"])
    assert f["schema"]=="d180_pilot_freeze_v1" and f["python"]==sys.version and f["numpy"]==np.__version__
    assert f["blocks"]==list(model.BLOCKS) and f["workers"]==WORKERS==4
    assert f["cells"]==[list(c) for c in model.CELLS]
    assert f["source_record_seals"]==seal_records()
    return f


def worker(index):
    assert type(index) is int and index in model.BLOCKS
    assert os.environ.get(ENV)=="execute" and os.environ.get(READY) is None
    resources()
    frozen()
    directory=output_dir()/f"block_{index}"
    directory.mkdir(exist_ok=False)
    source=model.load_source(index)
    proofs=[]
    for life in range(4):
        raw,meta=model.simulate_life(source,index,life)
        proof=check.check_life(raw,meta,source,True)
        save_life(directory,life,raw,meta,proof)
        read_life(directory,index,life,source)
        proofs.append(proof)
        resources()
        print(json.dumps(dict(block=index,life_saved=life,full_replay=True)),flush=True)
    return dict(index=index,**aggregate_proofs(proofs))


def cold_worker(number):
    resources()
    pins=source_inputs()
    return dict(number=number,pid=os.getpid(),source_hashes=len(pins),new_dynamics=0)


def cold_workers():
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn")) as pool:
        rows=list(pool.map(cold_worker,range(WORKERS)))
    assert [x["number"] for x in rows]==list(range(WORKERS))
    assert all(x["pid"]!=os.getpid() and x["new_dynamics"]==0 for x in rows)
    return rows


def acknowledge():
    fd=os.environ.pop(READY,None)
    if fd is not None:
        assert os.environ.get(ENV) in ("execute","audit","startup-check") and os.getsid(0)==os.getpid()
        os.write(int(fd),b"READY\n")
        os.close(int(fd))


def execute():
    global EXECUTION_OWNED
    resources()
    f=frozen()
    time_gate(f["conservative_seconds"],os.environ.get(ENV)=="execute")
    # All complete-pilot work must use the detached entry point, regardless of timing.
    assert os.environ.get(ENV)=="execute" and os.getsid(0)==os.getpid()
    run_dir().mkdir(parents=True,exist_ok=False)
    EXECUTION_OWNED=True
    output_dir().mkdir(parents=True,exist_ok=False)
    write_json(run_dir()/"MANIFEST.json",dict(started_utc=utc_now(),freeze_sha256=sha256_file(freeze_path()),
        blocks=list(model.BLOCKS),workers=WORKERS,forecast_seconds=f["conservative_seconds"],
        source_record_seals=f["source_record_seals"],automatic_successor=False))
    acknowledge()
    tick=time.monotonic()
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn")) as pool:
        futures={pool.submit(worker,index):index for index in model.BLOCKS}
        for future in as_completed(futures):
            proof=future.result()
            assert proof["index"]==futures[future] and proof["passes"]
            print(json.dumps(dict(block_finished=proof["index"],elapsed_seconds=time.monotonic()-tick)),flush=True)
    records,summary,initial_proof=saved_pilot(output_dir(),False)
    write_json(output_dir()/"records.json",records)
    write_json(output_dir()/"summary.json",summary)
    _,_,proof=saved_pilot(output_dir(),True)
    check.prior.nested(proof,initial_proof)
    verify(f["inputs"])
    verify(f["science_qualification"])
    output=files.hashes(sorted(p for p in output_dir().rglob("*") if p.is_file()))
    result=dict(status="COMPLETE",completed_utc=utc_now(),seconds=time.monotonic()-tick,
        freeze_sha256=sha256_file(freeze_path()),manifest_sha256=sha256_file(run_dir()/"MANIFEST.json"),
        output_sha256=output,verification=proof,resources=resources(),
        prospective_prediction=False,new_predictors=0,automatic_successor=False)
    write_json(run_dir()/"COMPLETE.json",result)
    return {k:v for k,v in result.items() if k!="output_sha256"}


def audit():
    resources()
    f=frozen()
    # Independent saved checking is conservatively bounded by four complete benchmark blocks.
    time_gate(f["conservative_seconds"],os.environ.get(ENV)=="audit")
    assert not audit_path().exists()
    done=files.read_json(run_dir()/"COMPLETE.json")
    assert done["status"]=="COMPLETE" and done["freeze_sha256"]==sha256_file(freeze_path())
    assert done["manifest_sha256"]==sha256_file(run_dir()/"MANIFEST.json")
    verify(done["output_sha256"])
    assert set(done["output_sha256"])=={str(p) for p in output_dir().rglob("*") if p.is_file()}
    acknowledge()
    tick=time.monotonic()
    def forbidden(*args,**kwargs): raise AssertionError("saved-only audit: dynamics forbidden")
    check.physics.step=forbidden
    analysis.summarize=forbidden
    _,_,proof=saved_pilot(output_dir(),True)
    check.prior.nested(proof,done["verification"])
    verify(f["inputs"])
    verify(f["science_qualification"])
    result=dict(passes=True,completed_utc=utc_now(),seconds=time.monotonic()-tick,
        complete_sha256=sha256_file(run_dir()/"COMPLETE.json"),freeze_sha256=sha256_file(freeze_path()),
        verification=proof,new_dynamics=0,new_models=0,automatic_successor=False)
    write_json(audit_path(),result)
    return result


def spawn_detached(stage,log,timeout=30):
    assert stage in ("execute","audit","startup-check") and 0<timeout<=55
    external(log)
    readfd,writefd=os.pipe()
    env=dict(os.environ,**{ENV:stage,READY:str(writefd)})
    try:
        with log.open("xb") as handle:
            child=subprocess.Popen([sys.executable,"-u","-m","l20_extension1.recipient_coupling_pilot_run","--"+stage],
                cwd=WS.parent,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,
                env=env,start_new_session=True,pass_fds=(writefd,))
    finally:
        os.close(writefd)
    ready=select.select([readfd],[],[],timeout)[0]
    message=os.read(readfd,64) if ready else b""
    os.close(readfd)
    return dict(status="DETACHED_STARTED" if message==b"READY\n" else "STARTUP_NOT_ACKNOWLEDGED",
        stage=stage,pid=child.pid,log=str(log),automatic_polling=False,automatic_successor=False)


def launch(stage):
    resources()
    f=frozen()
    assert stage in ("execute","audit")
    if stage=="execute":
        assert not run_dir().exists() and not output_dir().exists()
    else:
        assert (run_dir()/"COMPLETE.json").exists() and not audit_path().exists()
    result=spawn_detached(stage,ROOT/"logs"/(RUN+"_"+stage+".log"),
                          min(55.,max(10.,2*f["source_hash_seconds"]+10)))
    result.update(forecast_seconds=f["conservative_seconds"],storage_bound_bytes=f["storage_bound_bytes"],
                  workers=WORKERS,started_acknowledgement_utc=utc_now())
    write_json(ROOT/"logs"/(RUN+"_"+stage+"_launch.json"),result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze",type=Path)
    g.add_argument("--execute",action="store_true")
    g.add_argument("--audit",action="store_true")
    g.add_argument("--launch",choices=("execute","audit"))
    g.add_argument("--startup-check",action="store_true")
    args=p.parse_args()
    try:
        if args.startup_check:
            resources()
            source_inputs()
            rows=cold_workers()
            acknowledge()
            result=dict(startup_passes=True,workers=len(rows),new_dynamics=0)
        else:
            result=freeze(args.freeze) if args.freeze else launch(args.launch) if args.launch else execute() if args.execute else audit()
        print(json.dumps(result,sort_keys=True),flush=True)
    except Exception as exc:
        if args.execute and EXECUTION_OWNED and not (run_dir()/"COMPLETE.json").exists() and not (run_dir()/"FAILED.json").exists():
            write_json(run_dir()/"FAILED.json",dict(failed_utc=utc_now(),error=str(exc),
                traceback=traceback.format_exc(),automatic_retry=False))
        raise


if __name__=="__main__":
    main()
