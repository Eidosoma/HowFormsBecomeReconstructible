"""Bounded cached-probe pipeline; no retries or automatic confirmation."""
from pc_common import *
import argparse
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import multiprocessing
import resource
import signal
import time
import traceback
from pc_measure import worker,check


def status(folder,**values):
    tmp=folder/'STATUS.tmp'
    with tmp.open('w') as f:json.dump(dict(utc=utc(),**values),f,indent=2,allow_nan=False)
    tmp.replace(folder/'STATUS.json')


def measurements(cases,folder,workers,deadline,scope='development',n=20):
    folder.mkdir()
    pool=ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'))
    pending={};iterator=iter(cases);result=[]
    def submit():
        case=next(iterator,None)
        if case is None:return False
        future=pool.submit(worker,(case,str(folder/case['case_id']),deadline,scope,n))
        pending[future]=case['case_id'];return True
    try:
        for _ in range(workers):submit()
        while pending:
            check(folder,deadline)
            done,_=wait(pending,timeout=min(30,max(.1,deadline-time.time())),return_when=FIRST_COMPLETED)
            for future in done:
                ident=pending.pop(future);receipt=future.result()
                require(receipt['case_id']==ident and receipt['scope']==scope,'Worker identity')
                result.append(receipt);submit()
            status(folder.parent,status='MEASURING',complete=len(result),expected=len(cases))
        pool.shutdown(wait=True)
    except BaseException:
        for future in pending:future.cancel()
        processes=list(pool._processes.values())
        for process in processes:
            if process.is_alive():process.terminate()
        pool.shutdown(wait=False,cancel_futures=True)
        for process in processes:process.join(timeout=5)
        raise
    require(len(result)==len(cases) and len({r['case_id'] for r in result})==len(cases),'Complete unique measurement cohort')
    return sorted(result,key=lambda r:r['case_id'])


def main(output,workers,seconds):
    wall=time.monotonic();cpu=time.process_time()
    child_start=resource.getrusage(resource.RUSAGE_CHILDREN)
    child_start_cpu=child_start.ru_utime+child_start.ru_stime
    require(1<=workers<=6 and 3600<=seconds<=21600,'Authorized bounded resources')
    output.mkdir(parents=True,exist_ok=False);deadline=time.time()+seconds
    def stop(*_):raise TimeoutError('Fixed development wall deadline or termination; no automatic retry')
    signal.signal(signal.SIGALRM,stop);signal.signal(signal.SIGTERM,stop);signal.alarm(seconds)
    try:
        for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
            require(os.environ.get(v)=='1','One numerical thread per worker')
        freeze=verify_freeze();cases=read(ROOT/'prepared/CASES.json')
        require(read(ROOT/'QUALIFICATION.json')['status']=='PASS','Completed matching qualification')
        write(output/'START.json',dict(utc=utc(),pid=os.getpid(),workers=workers,hard_wall_seconds=seconds,
            freeze_sha256=freeze,cases=len(cases),source_blocks=80,post_hoc=True,automatic_retry=False,automatic_successor=False))
        receipts=measurements(cases,output/'measurements',workers,deadline)
        require(sum(r['new_primary_native_reads'] for r in receipts)==25520 and
                sum(r['new_flat_audit_reads'] for r in receipts)==1276,'Declared new native work')
        write(output/'MEASUREMENT_RECEIPTS.json',receipts)
        compact=[]
        for r in receipts:
            compact.append({k:r[k] for k in ('case_id','block','regime','current_pass','branches','passed','q2',
                'new_primary_native_reads','new_flat_audit_reads','cached_first_writer_reads','raw_sha256')})
        write_csv(output/'probe_outcomes.csv',compact)
        status(output,status='FITTING',complete=638,source_blocks=80)
        from pc_fit import fit_all
        fits=fit_all(output,receipts,deadline)
        status(output,status='SCORING',held_fold_predictions_sealed=True)
        from pc_score import main as score
        summary=score(output,deadline)
        check(output,deadline)
        # Independent saved model/prediction and scoring audit before qualification.
        from pc_audit import audit_run
        audit=audit_run(output)
        feature=read(ROOT/'prepared/FEATURE_COSTS.json')
        cost=dict(new_native_reads=25520,new_flat_audit_reads=1276,new_future_target_reads=0,new_founders=0,
            cached_first_writer_reads_used=12760,standalone_native_reads_per_case=dict(depth0=60,depth1=60,depth2=60,direct8=8),
            features_cpu_seconds=sum(r['cpu_seconds'] for r in feature),fitting=fits,
            parent_cpu_seconds=time.process_time()-cpu,
            child_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime-child_start_cpu,
            wall_seconds=time.monotonic()-wall,workers=workers,hard_wall_seconds=seconds,
            timing_basis='Technical standalone estimates, actual new measurement receipts, preparation feature costs, fitting/calibration and final inference costs are separate.',
            technical_report_sha256=sha(PRICE_REPORT/'VERIFICATION.json'),population_cost_equality_established=False)
        write(output/'COSTS.json',cost)
        entries={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        require(sum((output/name).stat().st_size for name in entries)<=4_000_000_000,'Saved-data ceiling')
        write(output/'OUTPUTS.json',dict(sha256=entries))
        result=dict(status='COMPLETE',utc=utc(),scope='POST_HOC_RETAINED_DEVELOPMENT',freeze_sha256=freeze,
            output_manifest_sha256=sha(output/'OUTPUTS.json'),cases=638,source_blocks=80,new_native_reads=25520,
            flat_audit_reads=1276,final_models=8,saved_prediction_audit=audit['status'],
            wall_seconds=time.monotonic()-wall,automatic_successor=False,fresh_confirmation_launched=False,
            manuscript_changed=False,primary_contrasts=summary['primary_contrasts'])
        write(output/'COMPLETE.json',result);status(output,status='COMPLETE',scope=result['scope'])
        print(json.dumps(result),flush=True)
    except BaseException as error:
        write(output/'FAILURE.json',dict(utc=utc(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False,automatic_successor=False))
        status(output,status='FAILED',error=repr(error));raise
    finally:signal.alarm(0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,required=True);p.add_argument('--seconds',type=int,required=True)
    a=p.parse_args();main(a.output,a.workers,a.seconds)
