"""D150 single-use saved-trajectory development; no dynamics or automatic next run."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import recovery_features as features,recovery_models as models,recovery_check as check
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json,external_root

io=features.io;ROOT=features.ROOT;WS=features.WS
RUN='l20_extension1_recovery_prediction_dev_v1_attempt1'
COMPLETE='a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72'
PREDECESSORS={features.DEV:'e4eb6955a54c27392d31f0c7fef804c6b16e488556ca0db9c4f3767c2357c295',
 features.HELD:'818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918'}
SCIENCE=('recovery-prediction/PROTOCOL_V1.md','src/l20_extension1/recovery_features.py',
 'src/l20_extension1/recovery_models.py','src/l20_extension1/recovery_check.py',
 'src/l20_extension1/recovery_run.py','tests/test_recovery_prediction.py','scripts/run_recovery_prediction.sh')
ENV='L20_RECOVERY_PREDICTION_DETACHED';READY='D150_READY_FD'
ALLOWANCE=256*1024**2;RESERVE=4*1024**3
DISPOSABLE=('disposable_dev',514240)
IDS=np.array([s[1] for s in features.SPECS],dtype=np.int64)


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    assert not sys.flags.optimize and external_root(ROOT)==ROOT.resolve()
    cpus=sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus)>6 or not set(cpus)<=set(range(6)):raise RuntimeError('at most CPUs0-5')
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONDONTWRITEBYTECODE'):
        if os.environ.get(k)!='1':raise RuntimeError(k+'=1 required')
    for k in ('TMPDIR','XDG_CACHE_HOME'):
        p=Path(os.environ.get(k,'/')).resolve()
        if ROOT not in p.parents or not p.is_dir():raise RuntimeError('external '+k+' required')
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')
    return cpus


def contract():
    return dict(run=RUN,source_complete=COMPLETE,specs=[list(s) for s in features.SPECS],
        cases=[list(s) for s in features.CASES],lives=4,blocks=32,case_count=512,
        initial=list(features.INITIAL),endpoint=list(features.ENDPOINT),recovery=list(features.RECOVERY),
        models=list(models.MODELS),dimensions=[7,19,19,31,31],alphas=list(models.ALPHAS),
        central_comparison=['challenge_recovery','passive_recovery'],nested_validation=True,
        prospective_evidence=False,former_test_is_development=True,repeated_futures_training=False,
        workers=1,maximum_cpus=6,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        new_dynamics=0,new_founders=0,new_challenges=0,confidence_intervals=False,
        main_forecast='32*checked_feature_block_seconds+2*checked_full_model_seconds+2*hash_seconds+120',
        benchmark_forecast='1600*qualification_small_model_seconds+4*qualification_feature_seconds+120',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    run,out=ROOT/'runs'/features.REPEATED,ROOT/'outputs'/features.REPEATED
    assert sha256_file(run/'COMPLETE.json')==COMPLETE
    c,m=io.read_json(run/'COMPLETE.json'),io.read_json(run/'MANIFEST.json')
    assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c and not (run/'FAILED.json').exists()
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==1265 and len(c['output_sha256'])==36
    assert m['input_sha256']==io.hashes([Path(p) for p in m['input_sha256']])
    assert c['output_sha256']==io.hashes([Path(p) for p in c['output_sha256']])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    files={Path(p) for p in (*m['input_sha256'],*c['output_sha256'])}
    for name,digest in PREDECESSORS.items():
        p=ROOT/'runs'/name/'COMPLETE.json';assert p in files and sha256_file(p)==digest
    for spec in features.SPECS:
        assert all(p in files for p in features.paths(spec))
    for spec in (DISPOSABLE,('disposable_test',514240)):
        assert all(p in files for p in features.paths(spec,True))
    files.update((run/'COMPLETE.json',run/'MANIFEST.json',run/'STATUS.json',out/'output_hashes.sha256'))
    files.update(WS/name for name in SCIENCE)
    return sorted(files)


def qualification(report):
    io.require_beneath(report,ROOT/'logs');tree=ET.parse(report).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=40 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_recovery_prediction')]
    names={c.get('name').split('[',1)[0] for c in ours}
    required={'test_feature_block','test_small_models','test_outer_isolation','test_inner_isolation',
        'test_two_copy_boundary','test_source_closure','test_summary','test_independent_checker',
        'test_future_not_training','test_resource_guards','test_detach_guard','test_no_automatic_successor',
        'test_feature_corruption','test_model_corruption','test_roundtrip','test_no_dynamics','test_startup_handshake'}
    assert required<=names
    elapsed=lambda name:max(float(c.get('time')) for c in ours if c.get('name')==name)
    small,feature=elapsed('test_small_models'),elapsed('test_feature_block')
    return dict(report=str(report),tests=len(cases),failures=0,skipped=0,
        small_model_seconds=small,feature_seconds=feature,benchmark_forecast=1600*small+4*feature+120)


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use stage already exists')
    proof=qualification(report);tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    f=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_hash_seconds=seconds,main_extracted=False)
    io.write_json(freeze_path(),f,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_hash_seconds=seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report]) and f['main_extracted'] is False
    return f


def detached_guard(required,stage):
    if required and os.environ.get(ENV)!='1':raise RuntimeError('forecast above ten minutes requires detached stage')
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


def checked_feature(spec,disposable=False):
    raw,_=features.diagnostic(spec,disposable);value=features.extract(raw)
    proof=check.check_features(value,raw);y=features.labels(spec,disposable)
    assert check.check_labels(spec,y,disposable)
    return value,y,proof


def synthetic_panel():
    data,y=models.fixture();futures=np.clip(y[16:,...,None]+np.random.default_rng(150142).normal(scale=.07,size=(16,4,4,4)),-1,1)
    return dict(**data,labels=y,futures=futures,block_ids=IDS.copy())


def fit_dataset(data):
    p,m=models.fit_all(features.assemble(data),data['labels'],data['block_ids'])
    s=models.summarize(p,m,data['labels'],data['futures'],features.SPECS)
    return p,m,s


def verify_models(data,p,m,s):
    a=check.check_fits(p,m,data,data['labels'],data['block_ids'])
    b=check.check_summary(s,p,m,data['labels'],data['futures'],features.SPECS)
    return dict(models=a,summary=b)


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();data,y,proof=checked_feature(DISPOSABLE,True)
        io.write_npz(directory/'features.npz',dict(**data,labels=y),ROOT)
        loaded=io.load_npz(directory/'features.npz');labels=loaded.pop('labels')
        raw,_=features.diagnostic(DISPOSABLE,True);check.check_features(loaded,raw);check.check_labels(DISPOSABLE,labels,True)
        feature_seconds=time.monotonic()-tick;tick=time.monotonic()
        data=synthetic_panel();p,m,s=fit_dataset(data)
        io.write_npz(directory/'synthetic.npz',data,ROOT);io.write_npz(directory/'predictions.npz',p,ROOT)
        io.write_json(directory/'fits.json',m,ROOT);io.write_json(directory/'summary.json',s,ROOT)
        verified=verify_models(io.load_npz(directory/'synthetic.npz'),io.load_npz(directory/'predictions.npz'),
            io.read_json(directory/'fits.json'),io.read_json(directory/'summary.json'))
        model_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir())
        budget=size*4+32*sum(v.nbytes for v in loaded.values())+16*4*4*4*8+64*1024**2
        assert budget<=ALLOWANCE
        forecast=32*feature_seconds+2*model_seconds+2*hash_seconds+120
        t=dict(status='COMPLETE',completed_utc=utc_now(),feature_proof=proof,verification=verified,
            checked_feature_block_seconds=feature_seconds,checked_full_model_seconds=model_seconds,hash_seconds=hash_seconds,
            projected_seconds=forecast,must_detach=forecast>600,benchmark_bytes=size,projected_bytes=budget,
            raw_feature_bytes=sum(v.nbytes for v in loaded.values()),freeze_sha256=sha256_file(freeze_path()),
            output_sha256=io.hashes(list(directory.iterdir())),scientific_evidence=False,main_extracted=False)
        io.write_json(timing_path(),t,ROOT);print(json.dumps(t,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def timing_checked():
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['main_extracted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path())
    assert {p.name for p in benchmark_dir().iterdir()}=={'features.npz','synthetic.npz','predictions.npz','fits.json','summary.json'}
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==32*t['checked_feature_block_seconds']+2*t['checked_full_model_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==4*t['benchmark_bytes']+32*t['raw_feature_bytes']+16*4*4*4*8+64*1024**2<=ALLOWANCE
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def output_names():return ['dataset.npz','predictions.npz','fits.json','summary.json','verification.json','input_hashes.sha256']


def verify_saved():
    _,out=paths();data=io.load_npz(out/'dataset.npz')
    assert set(data)=={'start','endpoint','recovery','stages','labels','futures','block_ids'}
    np.testing.assert_array_equal(data['block_ids'],IDS);proofs=[]
    for i,spec in enumerate(features.SPECS):
        raw,_=features.diagnostic(spec)
        value={k:data[k][i] for k in ('start','endpoint','recovery','stages')}
        proofs.append(check.check_features(value,raw));check.check_labels(spec,data['labels'][i])
        if i>=16:check.check_futures(spec[1],data['futures'][i-16])
    p=io.load_npz(out/'predictions.npz');m=io.read_json(out/'fits.json');s=io.read_json(out/'summary.json')
    return dict(blocks=proofs,**verify_models(data,p,m,s))


def saved_audit():
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc'] and m['main_extracted'] is False
    assert {p.name for p in out.iterdir()}==set(output_names())|{'output_hashes.sha256'}
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(m['input_sha256'])
    proof=verify_saved();assert io.read_json(out/'verification.json')==proof
    c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['source_complete']==COMPLETE
    assert c['output_sha256']==io.hashes([out/name for name in output_names()])
    assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert c['verification']==proof and c['output_bytes']==sum(p.stat().st_size for p in out.iterdir())<=ALLOWANCE
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=6,blocks=32,cases=512,models=5,
        repeated_outcomes=1024,new_dynamics=0,prospective_evidence=False,original_result_unchanged=True)


def execute():
    resources();manifest_inputs=inputs();timing=timing_checked();detached_guard(timing['must_detach'],'execute')
    run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        m=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=manifest_inputs,timing=timing,
            environment=environment_manifest(),affinity=sorted(os.sched_getaffinity(0)),main_extracted=False)
        io.write_json(run/'MANIFEST.json',m,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(manifest_inputs))
        (run/'EXECUTION.lock').mkdir();atomic_json(run/'STATUS.json',dict(status='EXTRACTING',completed_blocks=[]),ROOT)
        ready('execute');rows=[];labels=[];futures=[]
        for spec in features.SPECS:
            raw,_=features.diagnostic(spec);rows.append(features.extract(raw));labels.append(features.labels(spec))
            if spec[0]=='former_test':futures.append(features.futures(spec[1]))
            atomic_json(run/'STATUS.json',dict(status='EXTRACTING',completed_blocks=IDS[:len(rows)].tolist(),updated_utc=utc_now()),ROOT)
        data={k:np.stack([r[k] for r in rows]) for k in rows[0]}
        data.update(labels=np.stack(labels),futures=np.stack(futures),block_ids=IDS)
        io.write_npz(out/'dataset.npz',data,ROOT)
        atomic_json(run/'STATUS.json',dict(status='FITTING',updated_utc=utc_now()),ROOT)
        p,m,s=fit_dataset(data);io.write_npz(out/'predictions.npz',p,ROOT)
        io.write_json(out/'fits.json',m,ROOT);io.write_json(out/'summary.json',s,ROOT)
        atomic_json(run/'STATUS.json',dict(status='INDEPENDENT_SAVED_CHECK',updated_utc=utc_now()),ROOT)
        proof=verify_saved();io.write_json(out/'verification.json',proof,ROOT);assert manifest_inputs==inputs()
        hashes=io.hashes([out/name for name in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            source_complete=COMPLETE,manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,
            hash_index_sha256=sha256_file(out/'output_hashes.sha256'),verification=proof,new_dynamics=0,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def detach(stage):
    resources();frozen()
    if stage=='execute':
        timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    else:raise ValueError('declared stage required')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir()
    env=os.environ.copy();env[ENV]='1';reader,writer=os.pipe();env[READY]=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.recovery_run','--'+stage],
                cwd=WS.parent,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
                start_new_session=True,pass_fds=(writer,))
    finally:os.close(writer)
    readable,_,_=select.select([reader],[],[],55);data=os.read(reader,4096) if readable else b'';os.close(reader)
    ack=json.loads(data) if data else None
    if ack is not None:assert ack==dict(stage=stage,pid=child.pid,status='STARTED')
    receipt=dict(status='DETACHED',stage=stage,pid=child.pid,launched_utc=utc_now(),startup_acknowledged=ack is not None,
        log=str(logfile(stage)),automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(lock/'LAUNCH.json',receipt,ROOT);print(json.dumps(receipt,indent=2),flush=True)


def main():
    if sys.flags.optimize:raise RuntimeError('assertions must remain enabled')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--test-report',type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','execute','audit','detach','detach-benchmark'):group.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze!=(args.test_report is not None):parser.error('test report only with freeze')
    if args.freeze:freeze(args.test_report)
    elif args.benchmark:benchmark()
    elif args.execute:execute()
    elif args.audit:print(json.dumps(saved_audit(),indent=2))
    else:detach('benchmark' if args.detach_benchmark else 'execute')


if __name__=='__main__':main()
