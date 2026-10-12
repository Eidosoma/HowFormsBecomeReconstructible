"""Forensically qualified, immutable recovery of a final JSON reporting failure."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from laws_confirmation.io import (atomic_text, canonical_digest, external_root,
    sha256_file, utc_now, write_hash_manifest)
from laws_confirmation.l17_r_channel import verify_hashes

_spec=importlib.util.spec_from_file_location("frozen_l22_independent",Path(__file__).with_name("audit_l22_source_recovery_outputs.py"))
audit=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)
SOURCE_ID=audit.RUN_ID
RUN_ID=SOURCE_ID+"_publication_recovery_v1"


def strict_json(path,value,root):
    atomic_text(path,json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n",root)


def source(root):
    run,output=root/"runs"/SOURCE_ID,root/"outputs"/SOURCE_ID
    failure=json.loads((run/"STATUS.json").read_text())
    assert failure["status"]=="FAILED" and failure["error"]=="Object of type bool is not JSON serializable"
    assert 'print(json.dumps(status,indent=2),flush=True)' in failure["traceback"]
    assert (run/"COMPLETE").is_file() and (run/"FAILED").is_file()
    assert (run/"COMPLETE").read_text().strip() < (run/"FAILED").read_text().strip()
    counts=[audit.manifest_check(output/f"{kind}_hashes.sha256") for kind in ("input","output")]
    assert counts==[133,370]
    study=json.loads((output/"source_recovery.json").read_text())
    assert study["completed_cleanly"] is True and study["calibration_qualified"]=="True"
    assert [r["tissue"] for r in study["results"]]==[r["tissue"] for r in study["calibrations"]]==list(range(30000,30008))
    assert all(r["passes"] is True and all(v is True for v in r["gates"].values()) for r in study["results"]+study["calibrations"])
    m=json.loads((run/"MANIFEST.json").read_text())
    cfg={"replicates":4,"settle":120,"imprint":1000,"sweeps":1000,"times":[0,50,250,500,1000],"norm":.3,"lam":.001,"damage":.3}
    audit.close(m["config"],cfg)
    audit.close(m["modes"],audit.modes())
    assert m["tissues"]==list(range(30000,30008)) and m["workers"]==4
    return study,cfg,failure,counts


def input_paths(root):
    ws=Path(__file__).resolve().parents[1]
    paths=[Path(__file__).resolve(),Path(audit.__file__).resolve(),ws/"protocols/L22_SOURCE_RECOVERY_PUBLICATION_V1.md",
        ws/"tests/test_l22_publication_recovery.py"]
    for kind in ("input","output"):
        manifest=root/"outputs"/SOURCE_ID/f"{kind}_hashes.sha256"
        paths.append(manifest)
        paths.extend(Path(line.split("  ",1)[1]) for line in manifest.read_text().splitlines())
    paths.extend(root/"runs"/SOURCE_ID/name for name in ("MANIFEST.json","STATUS.json","COMPLETE","FAILED"))
    return sorted(set(paths))


def runtime(root):
    import shutil
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
    assert all(os.environ.get(k)=="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"))
    assert shutil.disk_usage(root).free >= (1024+128)*1024**2
    return sorted(os.sched_getaffinity(0))


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root):
    assert not (root/"runs"/RUN_ID).exists() and not (root/"outputs"/RUN_ID).exists()
    cpus=runtime(root)
    study,cfg,_,counts=source(root)
    start=time.monotonic()
    directory=root/"outputs"/SOURCE_ID/"tissue_30000"
    audit.check_calibration(directory,study["calibrations"][0],cfg)
    audit.check_tissue(directory,study["results"][0],cfg)
    elapsed=time.monotonic()-start
    estimate=elapsed*8*1.5+60
    record={"run_id":RUN_ID,"measured_utc":utc_now(),"tissue_seconds":elapsed,"projected_seconds":estimate,
        "must_detach":bool(estimate>600),"passes":True,"new_simulations":0,"effects_not_reported":True,
        "cpu_affinity":cpus,"source_manifest_counts":counts,"input_sha256":{str(p):sha256_file(p) for p in input_paths(root)}}
    strict_json(timing_path(root),record,root)
    print(json.dumps({k:v for k,v in record.items() if k!="input_sha256"},indent=2),flush=True)
    return record


def prepare(root):
    run,output=root/"runs"/RUN_ID,root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable publication recovery already exists")
    timing=json.loads(timing_path(root).read_text())
    cpus=runtime(root)
    _,_,failure,counts=source(root)
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    assert timing["passes"] and hashes==timing["input_sha256"]
    hashes[str(timing_path(root))]=sha256_file(timing_path(root))
    manifest={"run_id":RUN_ID,"source_run":SOURCE_ID,"prepared_utc":utc_now(),"new_simulations":0,
        "benchmark":timing,"cpu_affinity":cpus,"source_failure":failure,"source_manifest_counts":counts,
        "input_sha256":hashes,"hash_contract":canonical_digest(hashes)}
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    strict_json(run/"MANIFEST.json",manifest,root)
    write_hash_manifest([Path(p) for p in hashes],output/"input_hashes.sha256",root)
    strict_json(run/"STATUS.json",{"status":"PREPARED","run_id":RUN_ID},root)
    print(json.dumps({"status":"PREPARED","input_hashes":len(hashes),"estimated_seconds":timing["projected_seconds"]}),flush=True)
    return manifest


def verify(root):
    run=root/"runs"/RUN_ID
    m=json.loads((run/"MANIFEST.json").read_text())
    assert json.loads((run/"STATUS.json").read_text())["status"]=="PREPARED"
    assert not (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    assert m["run_id"]==RUN_ID and m["source_run"]==SOURCE_ID and m["new_simulations"]==0
    assert verify_hashes(m["input_sha256"]) and canonical_digest(m["input_sha256"])==m["hash_contract"]
    assert set(m["input_sha256"])=={str(p) for p in input_paths(root)+[timing_path(root)]}
    return m


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    m,run=verify(root),root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    stdout,stderr=[root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout","stderr")]
    cmd=[sys.executable,str(Path(__file__).resolve()),"--run"]
    with stdout.open("xb") as out,stderr.open("xb") as err:
        process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    result={"run_id":RUN_ID,"pid":process.pid,"launched_utc":utc_now(),"estimated_seconds":m["benchmark"]["projected_seconds"],
        "stdout_log":str(stdout),"stderr_log":str(stderr),"status":str(run/"STATUS.json"),"complete":str(run/"COMPLETE"),
        "failed":str(run/"FAILED"),"polling_owner":"user"}
    strict_json(run/"LAUNCH.json",result,root)
    atomic_text(run/"RUN.pid",f"{process.pid}\n",root)
    print(json.dumps(result,indent=2),flush=True)
    return result


def run_recovery(root):
    manifest=verify(root)
    run,output=root/"runs"/RUN_ID,root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached run required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start=time.monotonic()
    try:
        runtime(root)
        study,cfg,failure,counts=source(root)
        strict_json(run/"STATUS.json",{"status":"RUNNING","checked_tissues":0,"updated_utc":utc_now()},root)
        checked,positive=[],[]
        for i in range(8):
            saved=study["results"][i]
            directory=root/"outputs"/SOURCE_ID/f"tissue_{saved['tissue']}"
            audit.close(json.loads((directory/"experiment.json").read_text()),saved)
            audit.close(json.loads((directory/"calibration.json").read_text()),study["calibrations"][i])
            positive.append(audit.check_calibration(directory,study["calibrations"][i],cfg))
            checked.append(audit.check_tissue(directory,saved,cfg))
            strict_json(run/"STATUS.json",{"status":"RUNNING","checked_tissues":len(checked),"updated_utc":utc_now()},root)
            print(f"publication recovery: tissue {saved['tissue']} independently verified",flush=True)
        qualified=bool(min(positive)>.25 and sum(positive)/8>=.75)
        assert qualified and study["calibration_qualified"]==str(qualified)
        classification=audit.adjudicate(checked)
        audit.close(study["classification"],classification)
        assert verify_hashes(manifest["input_sha256"])
        correction={"field":"calibration_qualified","original":"True","normalized":True,"reason":"NumPy boolean was stringified in the original metadata"}
        normalized=study|{"calibration_qualified":qualified,"source_process_clean":False,"original_run_status":"FAILED",
            "publication_recovery_id":RUN_ID,"metadata_corrections":[correction],
            "completion_scope":"scientific data independently verified; original process failed during final status printing"}
        record={"run_id":RUN_ID,"source_run":SOURCE_ID,"passes":True,"checked_utc":utc_now(),"new_simulations":0,
            "source_process_clean":False,"source_failure":failure,"source_manifest_counts":counts,"calibration_scores":positive,
            "classification":classification,"recovery_batches_checked":144,"assay_batches_checked":168,
            "batch_writer_updates_checked":144000,"metadata_corrections":[correction],"checked":checked}
        strict_json(output/"normalized_source_recovery.json",normalized,root)
        strict_json(output/"rescore.json",record,root)
        write_hash_manifest([output/"input_hashes.sha256",output/"normalized_source_recovery.json",output/"rescore.json"],output/"output_hashes.sha256",root)
        audit.manifest_check(output/"output_hashes.sha256")
        status={"status":"COMPLETE","run_id":RUN_ID,"completed_utc":utc_now(),"elapsed_seconds":time.monotonic()-start,
            "source_process_clean":False,"verified_scientific_data":True,"new_simulations":0,"classification":classification["label"]}
        strict_json(run/"STATUS.json",status,root)
        atomic_text(run/"COMPLETE",status["completed_utc"]+"\n",root)
        print(json.dumps(status,indent=2),flush=True)
        return 0
    except Exception as error:
        failure={"status":"FAILED","run_id":RUN_ID,"failed_utc":utc_now(),"error":str(error),"traceback":traceback.format_exc()}
        strict_json(run/"STATUS.json",failure,root)
        atomic_text(run/"FAILED",failure["failed_utc"]+"\n",root)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    for name in ("benchmark","prepare","run","detach"):
        group.add_argument(f"--{name}",action="store_true")
    args=parser.parse_args()
    root=external_root()
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_recovery(root)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
