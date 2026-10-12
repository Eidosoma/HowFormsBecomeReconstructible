"""D151 qualified/frozen targeted diagnostic development, explicit single-use stages."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import deepcopy
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import probe_system as system,probe_audit as audit,probe_models as models,probe_model_check as checker
from . import recovery_run as previous
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=previous.io;ROOT=system.ROOT;WS=system.WS
RUN='l20_extension1_targeted_prediction_dev_v1_attempt1'
SOURCE='l20_extension1_recovery_prediction_dev_v1_attempt1'
SOURCES={SOURCE:('4ab1e508b8249ffc28f339ccc4f1ceb2bd5a8ebb51efc892017ceb815ae33b6e',1320,6,'hash_index_sha256'),
 'l20_extension1_competing_component_v1_attempt1':('fa42358f1848eea93a3290cd78d1fa4fda872e458b93f9f0fdaace3b772805bc',1745,37,'hash_file_sha256')}
SCIENCE=('targeted-prediction/PROTOCOL_V1.md','src/l20_extension1/probe_system.py','src/l20_extension1/probe_audit.py',
 'src/l20_extension1/probe_models.py','src/l20_extension1/probe_model_check.py','src/l20_extension1/probe_run.py',
 'tests/test_probe.py','scripts/run_targeted_prediction.sh')
ALLOWANCE=2*1024**3;RESERVE=4*1024**3;WORKERS=6
ENV='L20_TARGETED_PREDICTION_DETACHED';READY='D151_READY_FD'


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def plan_path():return ROOT/'tmp'/f'{RUN}_cell_plan.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'
def stem(spec):return f'{spec[0]}_{spec[1]}'


def resources(starting=True):
    cpus=previous.resources(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external two-GiB allowance and reserve required')
    system.old.api()
    return cpus


def contract():
    return dict(run=RUN,specs=[list(s) for s in system.SPECS],cases=[list(c) for c in system.CASES],
        edits=list(system.EDITS),models=list(models.MODELS),comparisons=[list(c) for c in models.CONTRASTS],
        central=['attenuate','passive'],config=asdict(system.CONFIG),guide_sha256=system.old.GUIDE_SHA256,
        carrier_bytes=2048,blocks=32,cases_count=512,new_cycles=1536,new_readers=3072,new_writers=1536,
        new_main_lineages=0,new_founders=0,prospective_evidence=False,confidence_intervals=False,
        observer_cycles=2,dimensions=[7,19,19,19,19,19],alphas=list(models.ridge.ALPHAS),
        baseline_predictions_reused=True,baseline_run=SOURCE,matched_U1_noise=True,rerouted_after_edit=False,
        dose='0.5*min(competing_RMS,residual_RMS)',degeneracy='D149 unchanged',cell_plan_before_new_outcomes=True,
        full_physics_replay=True,workers=6,maximum_cpus=6,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        benchmark_forecast='4*full_life_seconds+1600*small_model_seconds+120',
        main_forecast='32*checked_block_seconds+2*checked_model_seconds+2*hash_seconds+180',
        byte_budget='32*uncompressed_block_bytes+benchmark_bytes+128MiB',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    files=set()
    for name,(digest,ni,no,index_key) in SOURCES.items():
        run,out=ROOT/'runs'/name,ROOT/'outputs'/name
        assert sha256_file(run/'COMPLETE.json')==digest
        c,m=io.read_json(run/'COMPLETE.json'),io.read_json(run/'MANIFEST.json')
        assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c and not (run/'FAILED.json').exists()
        assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
        assert len(m['input_sha256'])==ni and len(c['output_sha256'])==no
        assert m['input_sha256']==io.hashes([Path(p) for p in m['input_sha256']])
        assert c['output_sha256']==io.hashes([Path(p) for p in c['output_sha256']])
        assert sha256_file(out/'output_hashes.sha256')==c[index_key]
        assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
        files.update(Path(p) for p in (*m['input_sha256'],*c['output_sha256']))
        files.update((run/'COMPLETE.json',run/'MANIFEST.json',run/'STATUS.json',out/'output_hashes.sha256'))
    receipt=ROOT/'logs/d150_saved_audit_v1.json'
    assert sha256_file(receipt)=='9d6b8161d54923ec4a1b2e0213078baa1eca3d0c32092811fcf32da51576f8a5'
    a=io.read_json(receipt);assert a['passes'] and a['new_dynamics']==0 and a['complete_sha256']==SOURCES[SOURCE][0]
    files.add(receipt)
    files.update(WS/p for p in (*SCIENCE,'recovery-prediction/RESULTS.md','competing-component/RESULTS.md'))
    return sorted(files)


def qualification(report):
    io.require_beneath(report,ROOT/'logs');tree=ET.parse(report).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=45 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_probe')]
    required={'test_full_disposable_life','test_small_models','test_independent_replay','test_source_parity',
        'test_algebra','test_degenerate','test_two_copy_boundary','test_baseline_identity','test_outer_isolation',
        'test_future_not_training','test_mean_sham_is_loss','test_summary','test_source_closure','test_raw_corruption',
        'test_metadata_corruption','test_saved_no_dynamics','test_no_reroute','test_resource_guards',
        'test_detach_guard','test_no_automatic_successor','test_startup_handshake','test_model_corruption','test_roundtrip'}
    assert required<={c.get('name').split('[',1)[0] for c in ours}
    elapsed=lambda name:max(float(c.get('time')) for c in ours if c.get('name')==name)
    life,small=elapsed('test_full_disposable_life'),elapsed('test_small_models')
    return dict(report=str(report),tests=len(cases),failures=0,skipped=0,full_life_seconds=life,small_model_seconds=small,
        benchmark_forecast=4*life+1600*small+120)


def cell_plan():
    p=io.read_json(plan_path())
    assert p['specs']==[list(s) for s in system.SPECS] and p['new_cycles']==1536 and len(p['blocks'])==32
    assert [b['spec'] for b in p['blocks']]==p['specs']
    return p


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),plan_path(),timing_path(),benchmark_dir(),*paths(),logfile('benchmark'),logfile('execute'))):
        raise FileExistsError('single-use D151 stages already exist')
    proof=qualification(report);tick=time.monotonic();files=source_files()
    plans=[system.block_plan(s) for s in system.SPECS]
    plan=dict(specs=[list(s) for s in system.SPECS],blocks=plans,new_cycles=1536,new_outcomes_generated=False,
        identity_cycles=sum(p['identity_cycles'] for p in plans))
    io.write_json(plan_path(),plan,ROOT);inputs=io.hashes(files+[report,plan_path()]);seconds=time.monotonic()-tick
    f=dict(frozen_utc=utc_now(),contract=contract(),input_sha256=inputs,test_proof=proof,environment=environment_manifest(),
        source_hash_and_plan_seconds=seconds,new_main_diagnostics=False,plan_sha256=sha256_file(plan_path()))
    io.write_json(freeze_path(),f,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),proof=proof,identity_cycles=plan['identity_cycles'],new_main_diagnostics=False)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report,plan_path()])
    assert f['plan_sha256']==sha256_file(plan_path()) and f['new_main_diagnostics'] is False
    cell_plan();return f


def detached_guard(required,stage):
    if required and os.environ.get(ENV)!='1':raise RuntimeError('forecast above ten minutes requires detachment')
    if os.environ.get(ENV)=='1':
        assert os.getpid()==os.getsid(0) and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==logfile(stage)
        assert os.readlink('/proc/self/fd/2')==os.readlink('/proc/self/fd/1')


def ready(stage):
    descriptor=os.environ.pop(READY,None)
    if descriptor is not None:
        fd=int(descriptor)
        try:os.write(fd,json.dumps(dict(stage=stage,pid=os.getpid(),status='STARTED')).encode())
        except BrokenPipeError:pass
        finally:os.close(fd)


def check_block(raw,meta,plan):
    spec=tuple(meta['spec']);assert list(spec)==plan['spec'] and meta['config']==asdict(system.CONFIG)
    source,sm=system.load_source(spec);assert len(meta['lives'])==4
    proofs=[]
    for life in range(4):
        assert meta['lives'][life]['life']==life
        src={k:v[life] for k,v in source.items()};value={k:v[life] for k,v in raw.items()}
        p=audit.check_life(value,meta['lives'][life],src,sm['lives'][life],False)
        stored=meta['lives'][life]['replay']
        assert set(stored)==set(p) and stored['passes'] and stored['replayed_cycles']==12
        assert stored['cycles']==12 and stored['readers']==24 and stored['writers']==12 and stored['new_actual_lineages']==0
        assert stored['prospective_evidence'] is False and set(stored['maxima'])==set(p['maxima'])
        assert all(0<=v<=1e-10 for v in stored['maxima'].values()) and stored['max_abs']==max(stored['maxima'].values())
        for ci in range(4):
            for ei in range(3):assert meta['lives'][life]['cells'][ci][ei]['plan']==plan['lives'][life][ci][ei]
        proofs.append(p)
    assert meta['new_cycles']==48
    return dict(passes=True,spec=list(spec),new_cycles=48,saved_checks=proofs,
        full_replayed_cycles=48,uncompressed_bytes=sum(v.nbytes for v in raw.values()))


def checked_block(directory,spec,plan):
    resources(False);source,sm=system.load_source(spec);rows=[];entries=[]
    for life in range(4):
        row,meta=system.simulate_life(spec,life,source['founder_packets'][life],source['guide'][life],plan['lives'][life])
        meta['replay']=audit.check_life(row,meta,{k:v[life] for k,v in source.items()},sm['lives'][life],True)
        rows.append(row);entries.append(meta)
    raw={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    meta=dict(spec=list(spec),config=asdict(system.CONFIG),lives=entries,new_cycles=48)
    io.write_npz(directory/(stem(spec)+'.npz'),raw,ROOT);io.write_json(directory/(stem(spec)+'.json'),meta,ROOT)
    return check_block(io.load_npz(directory/(stem(spec)+'.npz')),io.read_json(directory/(stem(spec)+'.json')),plan)


def baseline():
    out=ROOT/'outputs'/SOURCE
    raw=io.load_npz(out/'dataset.npz');data={k:raw[k] for k in ('start','endpoint','labels','futures','block_ids')}
    np.testing.assert_array_equal(data['block_ids'],np.array([s[1] for s in system.SPECS],np.int64))
    return data,io.load_npz(out/'predictions.npz'),io.read_json(out/'fits.json')


def verify_models(data,p,m,s,bp,bm):
    return dict(models=checker.check_fits(p,m,data,bp,bm),summary=checker.check_summary(s,p,m,data))


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();plan=system.block_plan(system.DISPOSABLE)
        proof=checked_block(directory,system.DISPOSABLE,plan);block_seconds=time.monotonic()-tick
        tick=time.monotonic();data,bp,bm=models.fixture();p,m=models.fit_new(data,bp,bm);s=models.summarize(p,m,data)
        for name,value in (('synthetic',data),('predictions',p),('baseline_predictions',bp)):io.write_npz(directory/(name+'.npz'),value,ROOT)
        for name,value in (('fits',m),('baseline_fits',bm)):io.write_json(directory/(name+'.json'),value,ROOT)
        verified=verify_models(io.load_npz(directory/'synthetic.npz'),io.load_npz(directory/'predictions.npz'),io.read_json(directory/'fits.json'),s,
            io.load_npz(directory/'baseline_predictions.npz'),io.read_json(directory/'baseline_fits.json'))
        raw=io.load_npz(directory/(stem(system.DISPOSABLE)+'.npz'));source,_=system.load_source(system.DISPOSABLE)
        diagnostics=models.diagnostic_summary([raw]*32,np.stack([source['diagnostic_features']]*32),[plan]*32)
        dp=checker.check_diagnostic_summary(diagnostics,[raw]*32,np.stack([source['diagnostic_features']]*32),[plan]*32)
        io.write_json(directory/'fixture.json',dict(scientific_evidence=False,summary=s,verification=verified,
            diagnostic_summary=diagnostics,diagnostic_check=dp),ROOT)
        model_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());budget=32*proof['uncompressed_bytes']+size+128*1024**2
        assert budget<=ALLOWANCE
        forecast=32*block_seconds+2*model_seconds+2*hash_seconds+180
        t=dict(status='COMPLETE',completed_utc=utc_now(),block_proof=proof,verification=verified,
            checked_block_seconds=block_seconds,checked_model_seconds=model_seconds,hash_seconds=hash_seconds,
            projected_seconds=forecast,must_detach=forecast>600,benchmark_bytes=size,projected_bytes=budget,
            freeze_sha256=sha256_file(freeze_path()),output_sha256=io.hashes(list(directory.iterdir())),
            scientific_evidence=False,new_main_diagnostics=False)
        io.write_json(timing_path(),t,ROOT);print(json.dumps(t,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def timing_checked():
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['new_main_diagnostics'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path())
    expected={stem(system.DISPOSABLE)+'.npz',stem(system.DISPOSABLE)+'.json','synthetic.npz','predictions.npz','baseline_predictions.npz','fits.json','baseline_fits.json','fixture.json'}
    assert {p.name for p in benchmark_dir().iterdir()}==expected
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==32*t['checked_block_seconds']+2*t['checked_model_seconds']+2*t['hash_seconds']+180
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==32*t['block_proof']['uncompressed_bytes']+t['benchmark_bytes']+128*1024**2<=ALLOWANCE
    return t


def benchmark_audit():
    resources(False);frozen();t=timing_checked();d=benchmark_dir();spec=system.DISPOSABLE
    raw=io.load_npz(d/(stem(spec)+'.npz'));plan=system.block_plan(spec)
    assert check_block(raw,io.read_json(d/(stem(spec)+'.json')),plan)==t['block_proof']
    fixture=io.read_json(d/'fixture.json');assert fixture['scientific_evidence'] is False
    verified=verify_models(io.load_npz(d/'synthetic.npz'),io.load_npz(d/'predictions.npz'),io.read_json(d/'fits.json'),fixture['summary'],
        io.load_npz(d/'baseline_predictions.npz'),io.read_json(d/'baseline_fits.json'))
    assert verified==t['verification']==fixture['verification']
    source,_=system.load_source(spec)
    assert checker.check_diagnostic_summary(fixture['diagnostic_summary'],[raw]*32,np.stack([source['diagnostic_features']]*32),[plan]*32)==fixture['diagnostic_check']
    return dict(passes=True,new_dynamics=0,projected_seconds=t['projected_seconds'],projected_bytes=t['projected_bytes'])


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def output_names():
    return [stem(s)+'.'+ext for s in system.SPECS for ext in ('npz','json')]+[
        'dataset.npz','predictions.npz','fits.json','summary.json','diagnostics.json','verification.json','input_hashes.sha256']


def assemble_saved():
    _,out=paths();data,bp,bm=baseline();blocks=[io.load_npz(out/(stem(s)+'.npz')) for s in system.SPECS]
    data['targeted']=np.stack([b['diagnostic_features'] for b in blocks])
    return data,bp,bm,blocks


def saved_values():
    _,out=paths();plans=cell_plan()['blocks'];data,bp,bm,blocks=assemble_saved();proofs=[]
    for spec,raw,plan in zip(system.SPECS,blocks,plans):proofs.append(check_block(raw,io.read_json(out/(stem(spec)+'.json')),plan))
    saved=io.load_npz(out/'dataset.npz');assert set(saved)==set(data)
    for k in data:np.testing.assert_array_equal(data[k],saved[k])
    p,m,s=io.load_npz(out/'predictions.npz'),io.read_json(out/'fits.json'),io.read_json(out/'summary.json')
    proof=verify_models(saved,p,m,s,bp,bm)
    diagnostic=checker.check_diagnostic_summary(io.read_json(out/'diagnostics.json'),blocks,data['endpoint'],plans)
    return dict(blocks=proofs,**proof,diagnostics=diagnostic)


def saved_audit():
    resources(False);run,out=paths();manifest=io.read_json(run/'MANIFEST.json')
    assert manifest['input_sha256']==inputs() and manifest['contract']==contract() and manifest['environment']==environment_manifest()
    assert {p.name for p in out.iterdir()}==set(output_names())|{'output_hashes.sha256'}
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(manifest['input_sha256'])
    proof=saved_values();assert io.read_json(out/'verification.json')==proof
    c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['verification']==proof
    assert c['output_sha256']==io.hashes([out/name for name in output_names()])
    assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert c['output_bytes']==sum(p.stat().st_size for p in out.iterdir())<=ALLOWANCE
    return dict(passes=True,input_hashes=len(manifest['input_sha256']),outputs=len(output_names()),blocks=32,cases=512,
        new_dynamics=0,completed_new_diagnostic_cycles=1536,all_new_cycles_independently_replayed=True,
        models=6,baseline_models_unchanged=3,prospective_evidence=False,new_actual_lineages=0)


def execute():
    resources();manifest_inputs=inputs();timing=timing_checked();detached_guard(timing['must_detach'],'execute')
    run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use D151 paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=manifest_inputs,timing=timing,
            environment=environment_manifest(),affinity=sorted(os.sched_getaffinity(0)),new_main_diagnostics=False)
        io.write_json(run/'MANIFEST.json',manifest,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(manifest_inputs))
        (run/'EXECUTION.lock').mkdir();atomic_json(run/'STATUS.json',dict(status='DIAGNOSTICS',completed_blocks=[]),ROOT)
        ready('execute');plans=cell_plan()['blocks'];done=[]
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs={pool.submit(checked_block,out,s,p):s for s,p in zip(system.SPECS,plans)}
            for job in as_completed(jobs):
                spec=jobs[job];job.result();done.append(list(spec))
                atomic_json(run/'STATUS.json',dict(status='DIAGNOSTICS',completed_blocks=sorted(done),updated_utc=utc_now()),ROOT)
                print(json.dumps(dict(completed_block=spec,completed_blocks=len(done),new_cycles=48*len(done))),flush=True)
        atomic_json(run/'STATUS.json',dict(status='FITTING',updated_utc=utc_now()),ROOT)
        data,bp,bm,blocks=assemble_saved();p,m=models.fit_new(data,bp,bm);s=models.summarize(p,m,data)
        io.write_npz(out/'dataset.npz',data,ROOT);io.write_npz(out/'predictions.npz',p,ROOT)
        io.write_json(out/'fits.json',m,ROOT);io.write_json(out/'summary.json',s,ROOT)
        io.write_json(out/'diagnostics.json',models.diagnostic_summary(blocks,data['endpoint'],plans),ROOT)
        atomic_json(run/'STATUS.json',dict(status='INDEPENDENT_SAVED_CHECK',updated_utc=utc_now()),ROOT)
        proof=saved_values();io.write_json(out/'verification.json',proof,ROOT);assert manifest_inputs==inputs()
        hashes=io.hashes([out/name for name in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_actual_lineages=0,prospective_evidence=False,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def detach(stage):
    resources();frozen()
    if stage=='execute':timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    else:raise ValueError('declared stage required')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir();env=os.environ.copy();env[ENV]='1'
    reader,writer=os.pipe();env[READY]=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.probe_run','--'+stage],cwd=WS.parent,env=env,
                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(writer,))
    finally:os.close(writer)
    readable,_,_=select.select([reader],[],[],55);data=os.read(reader,4096) if readable else b'';os.close(reader)
    ack=json.loads(data) if data else None
    if ack is not None:assert ack==dict(stage=stage,pid=child.pid,status='STARTED')
    receipt=dict(status='DETACHED',stage=stage,pid=child.pid,launched_utc=utc_now(),startup_acknowledged=ack is not None,
        log=str(logfile(stage)),automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(lock/'LAUNCH.json',receipt,ROOT);print(json.dumps(receipt,indent=2),flush=True)


def main():
    if sys.flags.optimize:raise RuntimeError('assertions must remain enabled')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--test-report',type=Path)
    group=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','benchmark-audit','execute','audit','detach','detach-benchmark'):group.add_argument('--'+name,action='store_true')
    args=p.parse_args()
    if args.freeze!=(args.test_report is not None):p.error('test report only with freeze')
    if args.freeze:freeze(args.test_report)
    elif args.benchmark:benchmark()
    elif args.benchmark_audit:print(json.dumps(benchmark_audit(),indent=2))
    elif args.execute:execute()
    elif args.audit:print(json.dumps(saved_audit(),indent=2))
    else:detach('benchmark' if args.detach_benchmark else 'execute')


if __name__=='__main__':main()
