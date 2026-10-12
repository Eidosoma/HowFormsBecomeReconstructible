"""Qualified and frozen D152 saved-fit audit; no model training or dynamics."""
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
from . import group_run as source,group_review as review,group_review_check as checker
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_group_fit_review_v1_attempt1'
COMPLETE='5188ad1597fb086ce653fc10cf1c80e7f388b2a8adb384f2551857360a73026d'
AUDIT=ROOT/'logs/l20_extension1_group_prediction_dev_v1_attempt1_saved_audit_v1.json'
AUDIT_HASH='d6e8a3ea7305869ccab16af8897de828793ab3f628446907a82e21bd5a4a1a36'
SCIENCE=('group-sensitive-prediction/SAVED_FIT_REVIEW_PLAN_V1.md','group-sensitive-prediction/RESULTS.md',
 'src/l20_extension1/group_review.py','src/l20_extension1/group_review_check.py','src/l20_extension1/group_review_run.py',
 'tests/test_group_review.py','scripts/run_group_review.sh')
ENV='L20_GROUP_REVIEW_DETACHED';READY='D152_REVIEW_READY_FD';ALLOWANCE=256*1024**2;RESERVE=4*1024**3


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    source.resources(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')


def contract():
    return dict(run=RUN,source_complete=COMPLETE,source_audit=AUDIT_HASH,blocks=source.IDS.tolist(),cases=512,
        architectures=list(review.ARCH),observers=list(review.MODELS),comparisons=review.specs(),alphas=list(review.ALPHAS),
        parts=list(review.PARTS),new_fits=0,new_predictions=0,new_dynamics=0,posthoc=True,prospective_evidence=False,
        all_cases_retained=True,deleted_score_rows_are_not_retrained_folds=True,
        workers=1,maximum_cpus=6,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        benchmark_forecast='4*qualified_full_review_seconds+120',
        main_forecast='2*checked_full_review_seconds+2*hash_seconds+120',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    run,out=source.paths();c=io.read_json(run/'COMPLETE.json');m=io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json')==COMPLETE and c['status']=='COMPLETE'
    assert not (run/'FAILED.json').exists() and io.read_json(run/'STATUS.json')==c
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==1976 and len(c['output_sha256'])==9
    expected={**m['input_sha256'],**c['output_sha256']}
    assert expected==io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert sha256_file(AUDIT)==AUDIT_HASH;proof=io.read_json(AUDIT)
    assert proof['passes'] and proof['complete_sha256']==COMPLETE and proof['source_primary_unchanged']
    assert proof['input_hashes']==1976 and proof['outputs']==9 and proof['new_dynamics']==0
    files={Path(p) for p in expected};files.update((run/'COMPLETE.json',run/'STATUS.json',run/'MANIFEST.json',out/'output_hashes.sha256',AUDIT))
    files.update(WS/p for p in SCIENCE);return sorted(files)


def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=35 and not any(tree.findall('.//'+n) for n in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_group_review')]
    required={'test_full_review','test_forward','test_clipping','test_ties','test_empty_partition','test_error_identity',
        'test_mean_sham','test_future_identity','test_score_deletion','test_source_bridge','test_panel_corruption',
        'test_summary_corruption','test_source_closure','test_roundtrip','test_no_fits_or_dynamics',
        'test_resource_guard','test_detach_guard','test_startup_handshake','test_no_automatic_successor'}
    assert required<={c.get('name').split('[',1)[0] for c in ours}
    seconds=max(float(c.get('time')) for c in ours if c.get('name')=='test_full_review')
    return dict(report=str(path),tests=len(cases),failures=0,skipped=0,qualified_full_review_seconds=seconds,
        benchmark_forecast=4*seconds+120)


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use stage already exists')
    proof=qualification(report);tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_audit=io.read_json(AUDIT),source_hash_seconds=seconds,main_extracted=False)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_hash_seconds=seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report]) and f['main_extracted'] is False
    assert f['source_audit']==io.read_json(AUDIT);return f


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


def prediction_arrays(p):return {a+'__'+k:p[a][k] for a in review.ARCH for k in review.MODELS}
def prediction_dict(p):return {a:{k:p[a+'__'+k] for k in review.MODELS} for a in review.ARCH}


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();data,p,m=review.fixture();panel=review.extract(data,p,m);summary=review.summarize(panel)
        old=source.models.summarize(p['group_sensitive'],m['group_sensitive'],p['shared'],m['shared'],data)
        io.write_npz(directory/'synthetic.npz',data,ROOT);io.write_npz(directory/'predictions.npz',prediction_arrays(p),ROOT)
        io.write_json(directory/'fits.json',m,ROOT);io.write_npz(directory/'panel.npz',panel,ROOT)
        io.write_json(directory/'summary.json',summary,ROOT);io.write_json(directory/'source_summary.json',old,ROOT)
        checked=verify_benchmark();review_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());budget=4*size+64*1024**2;assert budget<=ALLOWANCE
        forecast=2*review_seconds+2*hash_seconds+120
        value=dict(status='COMPLETE',completed_utc=utc_now(),verification=checked,checked_full_review_seconds=review_seconds,
            hash_seconds=hash_seconds,projected_seconds=forecast,must_detach=forecast>600,benchmark_bytes=size,projected_bytes=budget,
            freeze_sha256=sha256_file(freeze_path()),output_sha256=io.hashes(list(directory.iterdir())),
            scientific_evidence=False,new_fits=0,new_dynamics=0,main_extracted=False)
        io.write_json(timing_path(),value,ROOT);print(json.dumps(value,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def verify_benchmark():
    d=benchmark_dir();data=io.load_npz(d/'synthetic.npz');p=prediction_dict(io.load_npz(d/'predictions.npz'));m=io.read_json(d/'fits.json')
    panel=io.load_npz(d/'panel.npz');s=io.read_json(d/'summary.json')
    return dict(panel=checker.check_panel(panel,data,p,m),summary=checker.check_summary(s,panel),
        source_bridge=checker.source_bridge(s,io.read_json(d/'source_summary.json')))


def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['main_extracted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path()) and t['new_dynamics']==t['new_fits']==0
    assert {p.name for p in benchmark_dir().iterdir()}=={'synthetic.npz','predictions.npz','fits.json','panel.npz','summary.json','source_summary.json'}
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==2*t['checked_full_review_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==4*t['benchmark_bytes']+64*1024**2<=ALLOWANCE
    if audit:assert verify_benchmark()==t['verification']
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def source_data():
    out=source.paths()[1];data=io.load_npz(out/'dataset.npz');np.testing.assert_array_equal(data['block_ids'],source.IDS)
    p={'shared':io.load_npz(out/'shared_predictions.npz'),'group_sensitive':io.load_npz(out/'predictions.npz')}
    m={'shared':io.read_json(out/'shared_fits.json'),'group_sensitive':io.read_json(out/'fits.json')}
    return data,p,m


def output_names():return ['panel.npz','summary.json','verification.json','input_hashes.sha256']


def verify_saved():
    out=paths()[1];data,p,m=source_data();panel=io.load_npz(out/'panel.npz');s=io.read_json(out/'summary.json')
    return dict(panel=checker.check_panel(panel,data,p,m),summary=checker.check_summary(s,panel),
        source_bridge=checker.source_bridge(s,io.read_json(source.paths()[1]/'summary.json')))


def saved_audit():
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert m['main_extracted'] is False and m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc']
    assert {p.name for p in out.iterdir()}==set(output_names())|{'output_hashes.sha256'}
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(m['input_sha256'])
    proof=verify_saved();assert io.read_json(out/'verification.json')==proof
    c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['verification']==proof
    assert c['output_sha256']==io.hashes([out/n for n in output_names()])
    assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert c['output_bytes']==sum(p.stat().st_size for p in out.iterdir())<=ALLOWANCE
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=len(output_names()),blocks=32,cases=512,
        models=12,contrasts=42,new_fits=0,new_predictions=0,new_dynamics=0,prospective_evidence=False,source_primary_unchanged=True)


def execute():
    resources();pin=inputs();t=timing_checked(True);detached_guard(t['must_detach'],'execute');run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use review paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,timing=t,environment=environment_manifest(),
            affinity=sorted(os.sched_getaffinity(0)),main_extracted=False)
        io.write_json(run/'MANIFEST.json',manifest,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(pin))
        (run/'EXECUTION.lock').mkdir();ready('execute')
        atomic_json(run/'STATUS.json',dict(status='REVIEWING_SAVED_FITS',updated_utc=utc_now()),ROOT)
        data,p,m=source_data();panel=review.extract(data,p,m);summary=review.summarize(panel)
        io.write_npz(out/'panel.npz',panel,ROOT);io.write_json(out/'summary.json',summary,ROOT)
        proof=verify_saved();io.write_json(out/'verification.json',proof,ROOT);assert pin==inputs()
        hashes=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        value=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_fits=0,new_dynamics=0,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',value,ROOT);atomic_json(run/'STATUS.json',value,ROOT)
        print(json.dumps({k:v for k,v in value.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def audit(seal=False):
    t=timing_checked();detached_guard(t['must_detach'],'audit');ready('audit');tick=time.monotonic();proof=saved_audit()
    proof.update(checked_utc=utc_now(),elapsed_seconds=time.monotonic()-tick,complete_sha256=sha256_file(paths()[0]/'COMPLETE.json'),
        runner_sha256=sha256_file(Path(__file__)),checker_sha256=sha256_file(Path(checker.__file__)))
    if seal:io.write_json(ROOT/'logs'/f'{RUN}_saved_audit_v1.json',proof,ROOT)
    print(json.dumps(proof,indent=2),flush=True)


def detach(stage):
    resources();frozen()
    if stage=='execute':timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    elif stage=='audit':timing_checked();assert (paths()[0]/'COMPLETE.json').exists()
    else:raise ValueError('declared stage')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir();env=os.environ.copy();env[ENV]='1'
    reader,writer=os.pipe();env[READY]=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.group_review_run','--'+('seal-audit' if stage=='audit' else stage)],
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
    for name in ('freeze','benchmark','benchmark-audit','execute','audit','seal-audit','detach','detach-benchmark','detach-audit'):
        group.add_argument('--'+name,action='store_true')
    a=parser.parse_args()
    if a.freeze!=(a.test_report is not None):parser.error('test report only with freeze')
    if a.freeze:freeze(a.test_report)
    elif a.benchmark:benchmark()
    elif a.benchmark_audit:
        resources(False);frozen();t=timing_checked(True);print(json.dumps(dict(passes=True,projected_seconds=t['projected_seconds'],new_fits=0,new_dynamics=0)))
    elif a.execute:execute()
    elif a.audit or a.seal_audit:audit(a.seal_audit)
    else:detach('benchmark' if a.detach_benchmark else 'audit' if a.detach_audit else 'execute')


if __name__=='__main__':main()
