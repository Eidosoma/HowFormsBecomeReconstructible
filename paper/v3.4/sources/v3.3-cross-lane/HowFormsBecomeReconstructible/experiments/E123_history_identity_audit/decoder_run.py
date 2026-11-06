"""E123 synthetic full-pipeline checks and explicitly launched retained audit."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from E123_history_identity_audit import decoder_design as design
from E123_history_identity_audit import decoder_data as data
from E123_history_identity_audit import decoder_pipeline as pipeline
from E123_history_identity_audit.decoder_checks import synthetic_fields,test
from E123_history_identity_audit.interface import encode,decode,joint_counts
from E123_history_identity_audit.export import sha,dump


def utc():return datetime.now(timezone.utc).isoformat()


def code_paths():
    return [HERE/n for n in ("decoder_design.py","decoder_features.py","decoder_models.py","decoder_scores.py",
        "decoder_checks.py","decoder_data.py","decoder_pipeline.py","decoder_run.py","DECODER_DESIGN_V1.md","DECODER_AMENDMENT_V2.md",
        "interface.py","export.py","PREDICTION_SCHEMA.json","RESOURCE_ORIGINS.json")]+[
        ROOT/"run_python.sh",ROOT/"common.py",ROOT/"RUN_POLICY.md",ROOT/"E122_specificity_ceiling_and_tail/run.py"]


def frozen(output):
    hashes={}
    for p in code_paths():
        rel=str(p.relative_to(ROOT));target=output/"inputs"/rel
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);hashes[rel]=sha(p)
    dump(output/"CODE_FREEZE.json",dict(utc=utc(),inputs_sha256=hashes))
    return hashes


def check_code(hashes):
    for rel,digest in hashes.items():assert sha(ROOT/rel)==digest,rel


def synthetic_native(block,factor):
    """Native-shaped fixtures, not native read/erase/rewrite simulations."""
    rng=np.random.Generator(np.random.PCG64(123943+block))
    d=rng.normal(0,.3,(4,4,4)).repeat(4,1).repeat(4,2);d-=d.mean(axis=(-2,-1),keepdims=True)
    nbytes=2048//factor**2
    packet=np.empty((8,4,2,4,nbytes),dtype=np.uint8);state=np.empty((8,4,2,4,3,16,16),dtype=np.float64)
    births=rng.normal(0,.02,(4,2,1,16,16))
    for h in range(8):
        for f in range(4):
            for r in range(2):
                for a in range(4):
                    donor=(f+1)%4 if a in (1,3) else f
                    perturb=rng.normal(0,.02+.005*h,(16,16)) if a<2 else np.zeros((16,16))
                    packet[h,f,r,a]=encode(d[donor]+perturb,factor)
                    v=decode(packet[h,f,r,a],factor)+births[f,r,0]
                    state[h,f,r,a]=np.stack((v,.99*v,.98*v))
    incoming=packet[:,:,:,:2].copy();read=state[:,:,:,:2].copy()
    written=np.concatenate((read,decode(packet[:,:,:,:2],factor)[...,None,:,:]),axis=4)
    raw=dict(prototype=d,background=np.zeros((16,16)),checkpoints=np.array(design.CHECKPOINTS,dtype=np.int16),
        checkpoint_packet=packet,checkpoint_state=state,checkpoint_joint=joint_counts(state[...,0,:,:],d),
        checkpoint_birth=np.repeat(births[None],8,axis=0),checkpoint_mask=np.zeros((8,4,2,16,16),dtype=bool),
        protected_packets=packet[0,:,:,2:],checkpoint_writer_incoming=incoming,
        checkpoint_writer_outgoing=packet[:,:,:,:2].copy(),checkpoint_writer_read=read,checkpoint_writer_written=written)
    return raw,dict(block=block,factor=factor,evidence_status="SYNTHETIC_ONLY",native_checkpoint_reader_seconds=0.,
        note="Generated array fixture; no native trajectories, retained arrays or biological results")


def full_test(name):
    output=HERE/"analysis"/name;output.mkdir(parents=True,exist_ok=False);start=time.perf_counter();hashes=frozen(output)
    try:
        engine=output/"engine";engine.mkdir();engine_result=test(engine);dump(engine/"RESULT.json",engine_result)
        blocks=tuple(range(9100100,9100116))
        dataset=output/"synthetic_dataset"
        manifest=data.write_dataset(dataset,synthetic_native,blocks,dict(test="Excluded synthetic native-shaped fields"),"SYNTHETIC_ONLY")
        assert all(v==dict(checkpoint=4096,lifecycle=512) for v in manifest["rows"].values())
        predicted=pipeline.fit_and_seal(dataset,output/"predictions")
        scored=pipeline.score_sealed(dataset,output/"predictions")
        assert scored["status"]=="SYNTHETIC_PIPELINE_ONLY" and scored["source_blocks"]==16
        scores=json.loads((output/"predictions/SCORES.json").read_text())
        assert scores["primary_absolute"]["actual/ridge/record"]["n"]==16*16
        assert predicted["duplicate_probability_checks"]>0
        check_code(hashes)
        result=dict(status="PASS",utc=utc(),seconds=time.perf_counter()-start,engine=engine_result["status"],
            pipeline_prediction=predicted,pipeline_scoring=scored,dataset_rows=manifest["rows"],
            retained_data_fitted=False,new_native_trajectories=0,inputs_sha256=hashes,
            qualification_scope="End-to-end synthetic dataset → grouped tuning → held-out predictions → seal → scores; live E122 source ingestion still awaits completed verified outputs")
        dump(output/"RESULT.json",result)
        dump(output/"COMPLETE.json",dict(status="COMPLETE",outputs_sha256={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}))
        return dict(status=result["status"],seconds=result["seconds"],source_blocks=16,retained_data_fitted=False)
    except BaseException:
        dump(output/"FAILED.json",dict(utc=utc(),error=traceback.format_exc(),seconds=time.perf_counter()-start));raise


def execute(name):
    job=HERE/"jobs"/name;job_manifest=json.loads((job/"LAUNCH.json").read_text());check_code(job_manifest["inputs_sha256"])
    output=HERE/"runs"/name;output.mkdir(parents=True,exist_ok=False);start=time.perf_counter();hashes=frozen(output)
    def status(stage):dump_new=dict(status="RUNNING",utc=utc(),pid=os.getpid(),stage=stage,seconds=time.perf_counter()-start);(output/"STATUS.json").write_text(json.dumps(dump_new,indent=2)+"\n")
    try:
        status("verifying_and_ingesting_completed_E122")
        data.ingest(output/"dataset")
        status("nested_decoder_fitting")
        pipeline.fit_and_seal(output/"dataset",output/"predictions")
        status("scoring_sealed_predictions")
        result=pipeline.score_sealed(output/"dataset",output/"predictions")
        check_code(hashes)
        (output/"STATUS.json").write_text(json.dumps(dict(status="COMPLETE",utc=utc(),stage="finished",seconds=time.perf_counter()-start),indent=2)+"\n")
        dump(output/"COMPLETE.json",dict(status="COMPLETE",utc=utc(),seconds=time.perf_counter()-start,result=result,
            outputs_sha256={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}))
        print(json.dumps(dict(status="COMPLETE",seconds=time.perf_counter()-start,result=result)),flush=True)
    except BaseException:
        failure=dict(status="FAILED",utc=utc(),seconds=time.perf_counter()-start,error=traceback.format_exc(),automatic_restart=False)
        dump(output/"FAILED.json",failure);(output/"STATUS.json").write_text(json.dumps(failure,indent=2)+"\n");raise


def launch(name,qualification):
    qualified=HERE/"analysis"/qualification/"RESULT.json"
    q=json.loads(qualified.read_text());assert q["status"]=="PASS" and not q["retained_data_fitted"]
    check_code(q["inputs_sha256"])
    data.verify_completed_source()  # prerequisite, not a progress-monitoring loop
    from E122_specificity_ceiling_and_tail.run import inventory
    resources=inventory(workers=1)
    assert resources["free_bytes"]>1024**3,"One GiB reserve required for derived audit outputs"
    allowed=resources["preferred_cpus"] or resources["affinity"]
    cpu=5 if 5 in allowed else allowed[0];os.sched_setaffinity(0,{cpu})
    job=HERE/"jobs"/name;job.mkdir(parents=True,exist_ok=False);hashes=frozen(job)
    dump(job/"RESOURCES.json",resources)
    dump(job/"LAUNCH.json",dict(utc=utc(),inputs_sha256=hashes,qualification_sha256=sha(qualified),
        qualification=str(qualified.relative_to(ROOT)),automatic_restart=False,automatic_successor=False,
        numerical_threads=1,cpu_affinity=sorted(os.sched_getaffinity(0))))
    with (job/"stdout.log").open("x") as log:
        p=subprocess.Popen([sys.executable,"-B",str(HERE/"decoder_run.py"),"execute","--name",name],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
    (job/"PID").write_text(str(p.pid)+"\n")
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        marker=HERE/"runs"/name/"STATUS.json"
        if marker.exists():
            state=json.loads(marker.read_text());assert state["status"]=="RUNNING",state
            receipt=dict(status="RUNNING",utc=utc(),pid=p.pid,startup=state,bounded_startup_only=True,automatic_monitoring=False)
            dump(job/"STARTUP.json",receipt);return receipt
        if p.poll() is not None:break
        time.sleep(.1)
    raise RuntimeError("Startup did not pass; inspect saved job log. No automatic restart.")


def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("test","launch","execute"));p.add_argument("--name",required=True);p.add_argument("--qualification")
    a=p.parse_args()
    if not a.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in a.name):raise ValueError("Unique simple name required")
    if a.action!="launch":
        available=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{5 if 5 in available else available[-1]})
    if a.action=="test":result=full_test(a.name)
    elif a.action=="launch":
        if not a.qualification:p.error("A completed exact-code qualification is required")
        result=launch(a.name,a.qualification)
    else:execute(a.name);return
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":main()
