"""One exclusive acquisition, measurement or repeated-future work unit."""
import argparse
from pathlib import Path
import os
import signal
import time
import traceback
import numpy as np

from ff_common import (ROOT,NATIVE,C,P,REGIMES,e,ev,read,require,ledger,configure,identity,
                       verify_snapshot,binding,Guard,specification)
import acquisition
import pipeline
import measurement
import futures
import verify_science
import ff_selection
import ff_evidence


def synthetic(block,spec):
    histories=P['acquisition']['histories']
    keys=[[block,h,i,0] for i,h in enumerate(histories)]
    offset=block-spec['first_block']
    if offset<2:keys=[k for i,k in enumerate(keys) if i%2==offset]
    if offset==3:keys=keys[:3]
    return pipeline.synthetic_acquisition(block,dict(keys=keys))


def acquire(folder,task,guard):
    spec=task['spec'];b=task['block']
    if spec['scope']=='scientific':
        raw,rows,receipt=acquisition.acquire(b,C['stage'],folder,guard,legacy=False)
    else:
        raw,rows,receipt=synthetic(b,spec)
    ff_selection.check_rows(b,rows,spec['scope']=='scientific')
    ev.save(folder/'boundary.npz',raw)
    ledger.atomic_json(folder/'ENROLLMENT.json',dict(rows=rows,receipt=receipt))
    check=verify_science.boundary(NATIVE,folder,rows,spec['scope']!='scientific')
    ledger.atomic_json(folder/'VERIFICATION.json',check)
    return dict(block=b,rows=rows,native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads'])


def legacy(folder,task,guard):
    raw,_,receipt=acquisition.acquire(C['qualification']['legacy_block'],C['stage'],folder,guard,legacy=True)
    archive=ev.load(NATIVE/'context/legacy_g14.npz',ev.sha(NATIVE/'context/legacy_g14.npz'))
    for name in ('end','outgoing','mean_ports'):
        require(raw[name].dtype==archive[name].dtype and raw[name].shape==archive[name].shape and
                raw[name].tobytes()==archive[name].tobytes(), 'Legacy g14 replay differs: '+name)
    return dict(legacy_block=C['qualification']['legacy_block'],byte_exact=True,
                native_reads=receipt['native_reads'],flat_native_reads=receipt['flat_native_reads'],new_scientific_outcomes=0)


def measure(folder,task,guard):
    root=Path(task['run']);spec=task['spec'];block=task['block']
    plan=ff_evidence.selection(root,task['selection'],spec)
    _,rows,packets=ff_evidence.acquisition_source(root,plan,block,spec)
    forecasts=[];native=flat=0
    for i,(row,packet) in enumerate(zip(rows,packets,strict=True)):
        for regime in REGIMES:
            guard.check();case=folder/f'case_{i:02d}_{regime}';case.mkdir()
            with pipeline.accelerated():
                raw,receipt=measurement.measure(packet,row['rule'],row['key'],regime,C['stage'],case/'probe',guard,indices=list(range(32)))
            prediction=pipeline.forecast(row,regime,raw)
            ledger.atomic_json(case/'FORECAST.json',prediction)
            check=verify_science.measurement(case,row,prediction,P['reader'],read(NATIVE/'FROZEN_MODELS.json'))
            ledger.atomic_json(case/'VERIFICATION.json',check)
            forecasts.append(prediction);native+=receipt['native_reads'];flat+=receipt['flat_native_reads']
    ledger.atomic_json(folder/'FORECASTS.json',forecasts)
    return dict(block=block,forecasts=forecasts,native_reads=native,flat_native_reads=flat)


def future(folder,task,guard):
    root=Path(task['run']);spec=task['spec'];block=task['block'];rep=task['replicate']
    require(rep in spec['repeats'], 'Undeclared future replicate')
    seal_path,seal=ff_evidence.check_seal(root,task['seal'],spec)
    plan=ff_evidence.selection(root,seal['selection'],spec)
    require(block in plan['blocks'], 'Future block not selected')
    _,rows,packets=ff_evidence.acquisition_source(root,plan,block,spec)
    require(rows==[r for r in seal['rows'] if r['block']==block], 'Future cohort differs from global forecasts')
    index=seal['blocks'].index(block)
    forecasts=ff_evidence.verify_measurement(root,seal['measurements'][index],rows,spec)
    require(forecasts==[f for f in seal['forecasts'] if f['block']==block], 'Future forecasts differ from sealed forecasts')
    native=flat=0;outcomes=[];audit_key=min(rows,key=lambda r:r['selection_hash'])['key']
    for regime in REGIMES:
        guard.check();case=folder/regime;case.mkdir()
        receipt,labels=futures.batch(rows,packets,audit_key,regime,C['stage']+f'/replicate_{rep}',
            case/'future',guard,seal_path,task['seal']['sha256'])
        ledger.atomic_json(case/'OUTCOMES.json',labels)
        check=verify_science.continuation(case,rows,labels,P['reader'],task['seal']['sha256'],audit_key)
        ledger.atomic_json(case/'VERIFICATION.json',check)
        outcomes.extend(dict(**y,replicate=rep) for y in labels)
        native+=receipt['native_reads'];flat+=receipt['flat_native_reads']
    return dict(block=block,replicate=rep,outcomes=outcomes,native_reads=native,flat_native_reads=flat)


def run(task_path):
    task=read(task_path);root=Path(task['run']);folder=ledger.child(root,task['output'])
    folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();cpu=time.process_time()
    def expired(*_):raise TimeoutError('Worker deadline or termination; no automatic retry')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,task['deadline']-time.time()))
    try:
        require(task['spec']==specification(task['spec']['scope']), 'Task protocol differs')
        verify_snapshot();require(task['binding']==binding(), 'Task input binding differs')
        configure(task['spec']['scope']);guard=Guard(root,task['deadline']);guard.check()
        kind=task['kind'];require(kind in ('acquire','measure','future','legacy'), 'Wrong work type')
        require(kind!='legacy' or task['spec']['scope']=='qualification', 'Legacy replay is qualification only')
        ledger.atomic_json(folder/'START.json',dict(utc=ev.utc(),pid=os.getpid(),input_manifest_sha256=binding()['input_manifest_sha256'],
            task_sha256=ev.sha(task_path),kind=kind,deadline_epoch=task['deadline']))
        payload={'acquire':acquire,'measure':measure,'future':future,'legacy':legacy}[kind](folder,task,guard)
        guard.check()
        ledger.atomic_json(folder/'RESOURCES.json',dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu))
        fields={} if kind=='legacy' else dict(block=task['block'])
        if kind=='future':fields.update(replicate=task['replicate'],seal_sha256=task['seal']['sha256'])
        ledger.commit(folder,identity(task['spec'],kind,**fields),payload)
        print(dict(status='COMPLETE',kind=kind,**fields),flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        ledger.atomic_json(folder/'FAILED.json',dict(utc=ev.utc(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True)
    run(p.parse_args().task)
