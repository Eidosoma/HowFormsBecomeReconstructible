"""One bounded continuation pilot from sealed, previously measured records."""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import traceback

from bridge import ROOT,P,ev,read,verify_inputs
import audit_pilot
import futures
import ledger
import scoring_pilot as scoring
import verify_science


class Guard:
    def __init__(self,folder,seconds):
        self.folder=folder;self.end=time.monotonic()+seconds;self.next_check=0.

    def check(self):
        now=time.monotonic()
        if now>=self.end:raise TimeoutError('One-hour pilot deadline reached; no extension or automatic retry')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>P['resources']['maximum_resident_bytes']:
            raise MemoryError('Frozen memory ceiling exceeded')
        if now>=self.next_check:
            if shutil.disk_usage(self.folder).free<P['resources']['minimum_free_disk_bytes']:
                raise OSError('Insufficient free disk')
            if sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file())>P['resources']['maximum_saved_bytes']:
                raise OSError('Saved-evidence ceiling exceeded')
            self.next_check=now+20.


def check_cache():
    rows=read(ROOT/'cohort/ROWS.json');forecasts=read(ROOT/'cohort/FORECASTS.json')
    blocks,_,_=scoring.validate(rows,forecasts)
    if blocks!=P['cohort']['blocks'] or len(rows)!=P['cohort']['records'] or len(forecasts)!=P['cohort']['case_regimes']:
        raise ValueError('Declared cached panel changed')
    if read(ROOT/'CACHE_VERIFICATION.json')['status']!='PASS' or ev.sha(ROOT/'FROZEN_MODELS.json')!=P['models_sha256']:
        raise ValueError('Validated cache and fixed models required')
    packets=ev.load(ROOT/'cohort/PACKETS.npz',ev.sha(ROOT/'cohort/PACKETS.npz'))['packets']
    if packets.shape!=(len(rows),2,16,16):raise ValueError('Wrong packet panel shape')
    by_key={tuple(r['key']):r for r in rows}
    predictions={(tuple(r['key']),r['regime']):r for r in forecasts}
    historical={(tuple(r['key']),r['regime']):r for r in read(ROOT/'context/source_FORECASTS.json')}
    refs=read(ROOT/'cohort/REFERENCES.json')
    if len(refs)!=len(forecasts) or len({(tuple(r['key']),r['regime']) for r in refs})!=len(forecasts):
        raise ValueError('Incomplete cache measurement references')
    models=read(ROOT/'FROZEN_MODELS.json')
    for row,packet in zip(rows,packets,strict=True):
        if hashlib.sha256(packet.tobytes()).hexdigest()!=row['packet_sha256']:
            raise ValueError('Cached packet identity changed')
    for ref in refs:
        key=(tuple(ref['key']),ref['regime']);row=by_key[key[0]];prediction=predictions[key]
        expected=historical[key]
        if (prediction['q_rewrite']!=expected['q_rewrite'][0] or prediction['q_direct']!=expected['q_direct'][0]
            or prediction['probabilities']!={m:v[0] for m,v in expected['probabilities'].items()}):
            raise ValueError('Forecast is not the predeclared first measurement repeat')
        folder=ledger.child(ROOT,ref['folder'])
        if read(folder/'FORECAST.json')!=prediction:raise ValueError('Cached forecast reference differs')
        verify_science.measurement(folder,row,prediction,P['reader'],models)
    for block in blocks:
        verify_science.boundary(ROOT,ROOT/f'cohort/boundaries/block_{block:06d}',[r for r in rows if r['block']==block])
    return rows,forecasts,packets


def work(folder,rows,forecasts,packets,guard,binding,event=lambda *_:None):
    """All forecast checks precede the seal and every continuation call."""
    blocks,_,_=scoring.validate(rows,forecasts)
    if len(packets)!=len(rows):raise ValueError('Incomplete packet panel')
    seal=folder/'FORECAST_SEAL.json'
    ledger.atomic_json(seal,dict(utc=ev.utc(),input_binding=binding,records=len(rows),case_regimes=len(forecasts),
        rows=rows,forecasts=forecasts,complete_cohort_checked_before_any_future=True))
    seal_sha=ev.sha(seal)
    references=[]
    for block in blocks:
        indices=[i for i,row in enumerate(rows) if row['block']==block]
        selected=[rows[i] for i in indices];selected_packets=[packets[i] for i in indices]
        if not 1<=len(selected)<=4:raise ValueError('Declared batches contain at most four selected records')
        audit_key=min(selected,key=lambda r:r['selection_hash'])['key']
        for regime in scoring.REGIMES:
            guard.check()
            target=folder/'futures'/f'block_{block:06d}_{regime}';target.mkdir(parents=True)
            receipt,outcomes=futures.batch(selected,selected_packets,audit_key,regime,'pilot',target/'future',guard,seal,seal_sha)
            ev.write(target/'OUTCOMES.json',outcomes)
            audit=verify_science.continuation(target,selected,outcomes,P['reader'],seal_sha,audit_key)
            ev.write(target/'VERIFICATION.json',audit)
            identity=dict(binding=binding,block=block,regime=regime,keys=[r['key'] for r in selected],seal_sha256=seal_sha)
            ledger.commit(target,identity,dict(outcomes=outcomes,native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads']))
            references.append(dict(reference=ledger.reference(folder,target),rows=selected,audit_key=audit_key))
            event('continuation_batch_committed',dict(block=block,regime=regime,completed_batches=len(references),total_batches=2*len(blocks)))
    labels=[]
    for item in references:
        path,committed=ledger.referenced(folder,item['reference'])
        outcomes=read(path/'OUTCOMES.json')
        if outcomes!=committed['payload']['outcomes']:raise ValueError('Committed outcome content changed')
        verify_science.continuation(path,item['rows'],outcomes,P['reader'],seal_sha,item['audit_key'])
        labels.extend(outcomes)
    result=scoring.analyze(rows,forecasts,labels)
    independent=audit_pilot.evaluate(rows,forecasts,labels,result)
    ev.write(folder/'ANALYSIS.json',result);ev.write(folder/'VERIFICATION.json',independent)
    ev.write(folder/'FUTURE_REFERENCES.json',[r['reference'] for r in references])
    with (folder/'REPORT.md').open('x') as stream:stream.write(scoring.report(result))
    return dict(decision=result['decision'],records=len(rows),acquisition_blocks=len(blocks),
        case_regimes=len(labels),primary_native_reads=19*len(labels),flat_native_reads=38*len(blocks),
        new_measurement_reads=0,new_acquisition_reads=0,new_model_fits=0,
        first_repeat_only=True,forecast_seal_sha256=seal_sha,independent_final_analysis=True)


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    start,cpu=time.monotonic(),time.process_time()
    ceiling=P['resources']['pilot_wall_ceiling_seconds']
    def timeout(*_):raise TimeoutError('One-hour pilot deadline reached; no extension')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(ceiling)
    ev.write(output/'START.json',dict(utc=ev.utc(),pid=os.getpid(),wall_ceiling_seconds=ceiling,
        input_manifest_sha256=ev.sha(ROOT/'INPUTS.json')))
    ev.status(output,status='RUNNING',stage='input_verification_and_admission')
    try:
        count=verify_inputs()
        for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
            if os.environ.get(name)!='1':raise ValueError('One numerical thread required')
        if read(ROOT/'QUALIFICATION.json')['status']!='PASS':raise ValueError('Pilot wrapper qualification required')
        sys.path.insert(0,str(ROOT/'inherited/reference'))
        import cpu_preflight
        admission=cpu_preflight.collect();ev.write(output/'CPU_ADMISSION.json',admission)
        if not admission['within_limit']:raise RuntimeError('No shared CPU slot; no retry')
        guard=Guard(output,max(0.,ceiling-(time.monotonic()-start)));guard.check()
        rows,forecasts,packets=check_cache()
        def event(stage,details):
            guard.check();ev.status(output,status='RUNNING',stage=stage,details=details)
        event('all_cached_forecasts_verified',dict(records=len(rows),case_regimes=len(forecasts)))
        result=work(output,rows,forecasts,packets,guard,ev.sha(ROOT/'INPUTS.json'),event)
        verify_inputs();guard.check()
        hashes={str(p.relative_to(output)):ev.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
        ev.write(output/'OUTPUTS.json',dict(sha256=hashes))
        complete=dict(utc=ev.utc(),status='COMPLETE',**result,wall_seconds=time.monotonic()-start,
            cpu_seconds=time.process_time()-cpu,peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            output_manifest_sha256=ev.sha(output/'OUTPUTS.json'),input_files_verified=count,automatic_successor=False)
        ledger.atomic_json(output/'COMPLETE.json',complete)
        ev.status(output,status='COMPLETE',stage='complete')
        print(dict(status='COMPLETE',wall_seconds=complete['wall_seconds'],decision=result['decision']),flush=True)
    except BaseException as error:
        ledger.atomic_json(output/'FAILED.json',dict(utc=ev.utc(),type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        ev.status(output,status='FAILED',stage='failed');raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.output)
