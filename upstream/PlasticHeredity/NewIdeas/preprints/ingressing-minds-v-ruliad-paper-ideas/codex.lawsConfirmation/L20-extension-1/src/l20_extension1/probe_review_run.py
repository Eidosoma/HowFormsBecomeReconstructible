"""Qualified, frozen D151 saved-case review; explicit single-use stages only."""
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
from . import probe_run as source,probe_review as review,probe_review_check as checker
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_targeted_prediction_review_v1_attempt1'
COMPLETE='68742ebaa28c3594dcd72123e481561f7e51a6549a6c752f6e56196764e9a13f'
SCIENCE=('targeted-prediction/SAVED_CASE_REVIEW_PLAN_V1.md','targeted-prediction/RESULTS.md',
 'src/l20_extension1/probe_review.py','src/l20_extension1/probe_review_check.py','src/l20_extension1/probe_review_run.py',
 'src/l20_extension1/placement_review.py','src/l20_extension1/placement_review_check.py',
 'tests/test_probe_review.py','scripts/run_targeted_prediction_review.sh')
ENV='L20_PROBE_REVIEW_DETACHED';READY='D151_REVIEW_READY_FD';ALLOWANCE=256*1024**2;RESERVE=4*1024**3


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    source.previous.resources(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')


def contract():
    return dict(run=RUN,source_complete=COMPLETE,specs=[list(s) for s in source.system.SPECS],
        blocks=32,cases=512,models=list(review.MODELS),branches=list(review.BRANCHES),stages=list(review.STAGES),
        fields=list(review.field.FIELDS),comparisons=[list(c) for c in review.CONTRASTS],new_dynamics=0,new_models=0,
        posthoc=True,prospective_evidence=False,all_cases_retained=True,workers=1,maximum_cpus=6,numerical_threads=1,
        allowance=ALLOWANCE,reserve=RESERVE,benchmark_forecast='4*qualified_block_seconds+4*qualified_summary_seconds+120',
        main_forecast='32*checked_block_seconds+2*summary_seconds+2*hash_seconds+120',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    run,out=source.paths();c=io.read_json(run/'COMPLETE.json');m=io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json')==COMPLETE and c['status']=='COMPLETE'
    assert not (run/'FAILED.json').exists() and io.read_json(run/'STATUS.json')==c
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==1834 and len(c['output_sha256'])==71
    expected={**m['input_sha256'],**c['output_sha256']}
    assert expected==io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    files={Path(p) for p in expected};files.update((run/'COMPLETE.json',run/'STATUS.json',run/'MANIFEST.json',out/'output_hashes.sha256'))
    files.update(WS/p for p in SCIENCE);return sorted(files)


def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=30 and not any(tree.findall('.//'+n) for n in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    required={'test_full_block','test_summary','test_independent_check','test_threshold','test_roles','test_constant',
        'test_error_identity','test_future_identity','test_derived_corruption','test_summary_corruption','test_source_closure',
        'test_no_dynamics','test_resource_guard','test_detach_guard','test_startup_handshake','test_no_automatic_successor'}
    assert required<={c.get('name').split('[',1)[0] for c in cases}
    seconds=lambda name:max(float(c.get('time')) for c in cases if c.get('name')==name)
    block,summary=seconds('test_full_block'),seconds('test_summary')
    return dict(report=str(path),tests=len(cases),failures=0,skipped=0,qualified_block_seconds=block,
        qualified_summary_seconds=summary,benchmark_forecast=4*block+4*summary+120)


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use review stage already exists')
    proof=qualification(report);tick=time.monotonic();audit=source.saved_audit();audit_seconds=time.monotonic()-tick
    assert audit['passes'] and audit['new_dynamics']==0 and audit['input_hashes']==1834 and audit['outputs']==71
    tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_audit=audit,source_audit_seconds=audit_seconds,
        source_hash_seconds=seconds,main_extracted=False)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_audit=audit,source_audit_seconds=audit_seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    path=Path(f['test_proof']['report']);assert f['test_proof']==qualification(path)
    assert f['input_sha256']==io.hashes(source_files()+[path]) and f['main_extracted'] is False
    assert f['source_audit']['passes'] and f['source_audit']['new_dynamics']==0
    return f


def raw_block(spec):
    assert spec in source.system.SPECS+(source.system.DISPOSABLE,)
    directory=source.benchmark_dir() if spec==source.system.DISPOSABLE else source.paths()[1]
    raw=io.load_npz(directory/(source.stem(spec)+'.npz'));meta=io.read_json(directory/(source.stem(spec)+'.json'))
    assert meta['spec']==list(spec) and len(meta['lives'])==4
    original,_=source.system.load_source(spec)
    return raw,original


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


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();raw,original=raw_block(source.system.DISPOSABLE)
        value=review.extract(raw,original);proof=checker.check_block(value,raw,original)
        io.write_npz(directory/'block.npz',value,ROOT);checker.check_block(io.load_npz(directory/'block.npz'),raw,original)
        block_seconds=time.monotonic()-tick;tick=time.monotonic();panel,arch=review.fixture(value)
        summary=review.summarize(panel,arch,True);io.write_npz(directory/'panel.npz',panel,ROOT)
        io.write_json(directory/'summary.json',summary,ROOT)
        checked=checker.check_summary(io.read_json(directory/'summary.json'),io.load_npz(directory/'panel.npz'),arch,True)
        summary_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());raw_bytes=sum(v.nbytes for v in value.values())
        budget=32*raw_bytes+size+64*1024**2;assert budget<=ALLOWANCE
        forecast=32*block_seconds+2*summary_seconds+2*hash_seconds+120
        t=dict(status='COMPLETE',completed_utc=utc_now(),proof=proof,summary_check=checked,
            checked_block_seconds=block_seconds,summary_seconds=summary_seconds,hash_seconds=hash_seconds,
            block_uncompressed_bytes=raw_bytes,projected_seconds=forecast,must_detach=forecast>600,
            benchmark_bytes=size,projected_bytes=budget,freeze_sha256=sha256_file(freeze_path()),
            output_sha256=io.hashes(list(directory.iterdir())),scientific_evidence=False,new_dynamics=0)
        io.write_json(timing_path(),t,ROOT);print(json.dumps(t,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and not t['scientific_evidence'] and t['new_dynamics']==0
    assert t['freeze_sha256']==sha256_file(freeze_path())
    assert {p.name for p in benchmark_dir().iterdir()}=={'block.npz','panel.npz','summary.json'}
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==32*t['checked_block_seconds']+2*t['summary_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==32*t['block_uncompressed_bytes']+t['benchmark_bytes']+64*1024**2<=ALLOWANCE
    if audit:
        raw,original=raw_block(source.system.DISPOSABLE)
        assert checker.check_block(io.load_npz(benchmark_dir()/'block.npz'),raw,original)==t['proof']
        s=io.read_json(benchmark_dir()/'summary.json');p=io.load_npz(benchmark_dir()/'panel.npz')
        assert checker.check_summary(s,p,s['architecture'],True)==t['summary_check']
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def output_names():
    return [source.stem(s)+'.npz' for s in source.system.SPECS]+['panel.npz','summary.json','verification.json','input_hashes.sha256']


def assemble(blocks):
    out=source.paths()[1];data=io.load_npz(out/'dataset.npz');predictions=io.load_npz(out/'predictions.npz')
    np.testing.assert_array_equal(data['block_ids'],np.array([s[1] for s in source.system.SPECS],np.int64))
    return review.assemble(blocks,data,predictions),review.architecture(io.read_json(out/'fits.json'))


def saved_values():
    _,out=paths();blocks=[];proofs=[]
    for spec in source.system.SPECS:
        raw,original=raw_block(spec);value=io.load_npz(out/(source.stem(spec)+'.npz'))
        proofs.append(checker.check_block(value,raw,original));blocks.append(value)
    panel,arch=assemble(blocks);stored=io.load_npz(out/'panel.npz');assert set(stored)==set(panel)
    for k in panel:np.testing.assert_array_equal(stored[k],panel[k])
    summary=io.read_json(out/'summary.json');checked=checker.check_summary(summary,stored,arch)
    bridge=checker.source_scores(summary,io.read_json(source.paths()[1]/'summary.json'))
    return dict(blocks=proofs,summary=checked,source_scores=bridge,new_dynamics=0,new_models=0)


def saved_audit():
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert {p.name for p in out.iterdir()}==set(output_names())|{'output_hashes.sha256'}
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(m['input_sha256'])
    proof=saved_values();assert io.read_json(out/'verification.json')==proof
    c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['verification']==proof
    assert c['output_sha256']==io.hashes([out/n for n in output_names()])
    assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert c['output_bytes']==sum(p.stat().st_size for p in out.iterdir())<=ALLOWANCE
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=len(output_names()),cases=512,blocks=32,
        new_dynamics=0,new_models=0,prospective_evidence=False,source_primary_unchanged=True)


def execute():
    resources();pin=inputs();t=timing_checked(True);detached_guard(t['must_detach'],'execute');run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use review paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        m=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,timing=t,environment=environment_manifest(),
            affinity=sorted(os.sched_getaffinity(0)),main_extracted=False)
        io.write_json(run/'MANIFEST.json',m,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(pin))
        (run/'EXECUTION.lock').mkdir();ready('execute');blocks=[]
        for spec in source.system.SPECS:
            raw,original=raw_block(spec);value=review.extract(raw,original);checker.check_block(value,raw,original)
            io.write_npz(out/(source.stem(spec)+'.npz'),value,ROOT);blocks.append(value)
            atomic_json(run/'STATUS.json',dict(status='EXTRACTING',completed_blocks=len(blocks),updated_utc=utc_now()),ROOT)
        panel,arch=assemble(blocks);s=review.summarize(panel,arch)
        io.write_npz(out/'panel.npz',panel,ROOT);io.write_json(out/'summary.json',s,ROOT)
        proof=saved_values();io.write_json(out/'verification.json',proof,ROOT);assert pin==inputs()
        hashes=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_dynamics=0,new_models=0,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def detach(stage):
    resources();frozen()
    if stage=='execute':timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    else:raise ValueError('declared stage')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir();env=os.environ.copy();env[ENV]='1'
    reader,writer=os.pipe();env[READY]=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.probe_review_run','--'+stage],cwd=WS.parent,env=env,
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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--test-report',type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','benchmark-audit','execute','audit','detach','detach-benchmark'):group.add_argument('--'+name,action='store_true')
    a=parser.parse_args()
    if a.freeze!=(a.test_report is not None):parser.error('test report only with freeze')
    if a.freeze:freeze(a.test_report)
    elif a.benchmark:benchmark()
    elif a.benchmark_audit:
        resources(False);frozen();t=timing_checked(True);print(json.dumps(dict(passes=True,projected_seconds=t['projected_seconds'],new_dynamics=0)))
    elif a.execute:execute()
    elif a.audit:print(json.dumps(saved_audit(),indent=2))
    else:detach('benchmark' if a.detach_benchmark else 'execute')


if __name__=='__main__':main()
