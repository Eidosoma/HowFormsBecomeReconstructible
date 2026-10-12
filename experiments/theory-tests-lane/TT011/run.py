"""Freeze unique known-input benchmark/audit jobs; preserve all failures."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import support as s

OWN=['support.py','native.py','arithmetic.py','prepare.py','graph.py','intake.py','scoring.py','symmetry.py','checks.py','report.py','run.py',
     'PROTOCOL.md','DERIVATION.md','DRAFT_PROTOCOL.md','PLANNING_CONTEXT.json','SOURCE_RECEIPT.json','IMPLEMENTATION_REUSE.json']


def hashes():
    names=OWN+list(s.read(s.HERE/'SOURCE_RECEIPT.json')['files_sha256'])
    return {name:s.sha(s.HERE/name) for name in sorted(names)}


def execute(job):
    import checks
    import graph
    import intake
    import scoring
    import report
    meta=s.read(job/'job.json');output=Path(meta['output']);started=time.monotonic()
    def progress(phase,**detail):
        elapsed=time.monotonic()-started
        s.require(elapsed<1800,'First-stage runtime ceiling');s.require(shutil.disk_usage(output).free>=1073741824,'Storage reserve')
        temp=output/'STATUS.tmp';temp.write_text(json.dumps(dict(status='RUNNING',utc=s.utc(),elapsed_seconds=elapsed,phase=phase,pid=os.getpid(),**detail),indent=2)+'\n');temp.replace(output/'STATUS.json')
    try:
        s.require(s.HERE==job/'inputs/TT011' and hashes()==meta['inputs_sha256'],'Frozen input identity')
        affinity=os.sched_getaffinity(0);cpu=7 if 7 in affinity else min(affinity);os.sched_setaffinity(0,{cpu})
        threads={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']}
        s.require(all(v=='1' for v in threads.values()),'One numerical thread')
        s.dump(output/'manifest.json',dict(started_utc=s.utc(),job_sha256=s.sha(job/'job.json'),inputs_sha256=meta['inputs_sha256'],mode=meta['mode'],
               cpu=cpu,threads=threads,pid=os.getpid(),forecast_seconds=meta.get('forecast_seconds'),detached=meta['detached'],new_task_outcomes=False))
        progress('technical_qualification');t=time.monotonic();qualified=checks.run(output);check_seconds=time.monotonic()-t
        synthetic=s.read(output/'synthetic_analysis.json')
        synthetic_text=report.render(synthetic,dict(pairs=128,published_certificates_checked=256,certificates_rejected_with_old_pin_order=1),dict(raw_endpoints=360,dual_task_flags=720))
        s.require('primary same-task minus opposite-task point rule fails' in synthetic_text and 'secondary replacement direction passes' in synthetic_text,'Nontrivial synthetic report decisions')
        with (output/'synthetic_report.md').open('x') as f:
            f.write('SYNTHETIC FIXTURE; NOT COHORT EVIDENCE\n\n'+synthetic_text)
        if meta['mode']=='benchmark':
            t=time.monotonic();_,receipt=intake.run(output,[34006],progress);intake_seconds=time.monotonic()-t
            forecast=2*(4*intake_seconds+check_seconds+60)+30
            result=dict(status='PASS',checks_seconds=check_seconds,intake_seconds=intake_seconds,forecast_seconds=forecast,
                        maximum_seconds=1800,largest_block_cases=16,diagnostic_contexts=receipt['diagnostic_contexts'],new_task_outcomes=False)
            s.dump(output/'benchmark.json',result);s.require(forecast<1800,'Forecast exceeds first-stage ceiling')
        else:
            data,intake_receipt=intake.run(output,progress=progress)
            progress('exact_alignment_certificates');graph.run(data,output)
            progress('dual_task_scoring_and_tables');scoring.run(data,output)
            progress('report');result=report.run(output)
        progress('final_commitment_verification');s.require(hashes()==meta['inputs_sha256'],'Inputs unchanged')
        outputs={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name not in ['STATUS.json']}
        done=dict(status='COMPLETE',audit_status='PASS',utc=s.utc(),seconds=time.monotonic()-started,mode=meta['mode'],outputs_sha256=outputs,
                  full_native_replay_performed=False,new_task_outcomes=False,automatic_polling=False,automatic_successor=False)
        s.dump(output/'COMPLETE.json',done)
        (output/'STATUS.json').write_text(json.dumps({k:v for k,v in done.items() if k!='outputs_sha256'},indent=2)+'\n')
        return done
    except BaseException:
        failure=dict(status='FAILED',utc=s.utc(),seconds=time.monotonic()-started,traceback=traceback.format_exc(),mode=meta['mode'])
        s.dump(output/'FAILED.json',failure);(output/'STATUS.json').write_text(json.dumps(failure,indent=2)+'\n');raise


def prepare(mode,name,benchmark,detach):
    s.require(name and name.replace('_','').isalnum(),'Unique simple run name');inputs=hashes();forecast=None
    if mode=='audit':
        base=s.HERE/'runs'/benchmark;done=s.read(base/'COMPLETE.json');manifest=s.read(base/'manifest.json')
        s.require(done['status']=='COMPLETE' and done['mode']=='benchmark' and manifest['inputs_sha256']==inputs,'Successful identical-input benchmark')
        for rel,digest in done['outputs_sha256'].items():s.require(s.sha(base/rel)==digest,'Benchmark output '+rel)
        forecast=s.read(base/'benchmark.json')['forecast_seconds'];s.require(forecast<1800,'Forecast ceiling')
        s.require(detach or forecast<=600,'Long jobs must run detached')
    s.require(shutil.disk_usage(s.HERE).free>=1073741824+sum((s.HERE/name).stat().st_size for name in inputs),'Storage before freeze')
    job=s.HERE/'jobs'/name;output=s.HERE/'runs'/name;job.mkdir(parents=True,exist_ok=False);output.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        target=job/'inputs/TT011'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,target)
        s.require(s.sha(target)==digest,'Frozen copy')
    command=[sys.executable,'-B',str(job/'inputs/TT011/run.py'),'--execute',str(job)]
    meta=dict(study='TT011',mode=mode,name=name,created_utc=s.utc(),inputs_sha256=inputs,output=str(output),command=command,
              detached=detach,forecast_seconds=forecast,benchmark=benchmark,automatic_polling=False,automatic_successor=False)
    s.dump(job/'job.json',meta)
    with (job/'console.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=detach)
        s.dump(job/'PID.json',dict(pid=child.pid,created_utc=s.utc(),detached=detach))
        if not detach:
            code=child.wait();s.require(code==0,'Worker failed; inspect preserved FAILED.json and log')
    return dict(job=str(job),run=str(output),pid=child.pid,detached=detach,forecast_seconds=forecast)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',type=Path);parser.add_argument('--mode',choices=['benchmark','audit']);parser.add_argument('--name');parser.add_argument('--benchmark',default='benchmark_v1');parser.add_argument('--detach',action='store_true');args=parser.parse_args()
    if args.execute:result=execute(args.execute)
    else:result=prepare(args.mode,args.name,args.benchmark,args.detach)
    print(json.dumps({k:v for k,v in result.items() if k!='outputs_sha256'},indent=2))
