"""Single-use D148 saved-content review, qualified/frozen before extraction."""
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
from . import placement_run as source
from . import placement_review as review,placement_review_check as check
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=source.io;ROOT=source.ROOT;WS=source.system.dev.WS
RUN='l20_extension1_packet_placement_v1_attempt1'
REVIEW=RUN+'_saved_content_review_v1_attempt1'
COMPLETE='22f89ccdf1fedf056d3078fef93b57a490d9941abcec911286911e1d67ca8946'
AUDIT_SHA='4ab4dabf4a08d86617ddbc3aef83bf1ca0991431f1aa1e6fc414e90bc45356a6'
BLOCKS=tuple(range(93000,93016));DISPOSABLE=514246
ALLOWANCE=256*1024**2;RESERVE=4*1024**3
SCIENCE=('packet-placement/SAVED_STATE_REVIEW_PLAN_V1.md','packet-placement/RESULTS.md',
 'src/l20_extension1/placement_review.py','src/l20_extension1/placement_review_check.py',
 'src/l20_extension1/placement_review_run.py','tests/test_placement_review.py','scripts/run_placement_review.sh')
ENV='L20_PLACEMENT_REVIEW_DETACHED'


def paths():return ROOT/'runs'/REVIEW,ROOT/'outputs'/REVIEW
def freeze_path():return ROOT/'tmp'/f'{REVIEW}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{REVIEW}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{REVIEW}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{REVIEW}_{stage}.log'


def resources(starting=True):
    source.preflight(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')


def contract():
    return dict(review=REVIEW,source_complete=COMPLETE,blocks=list(BLOCKS),lives=4,replicas=2,
        cells=12288,groups=96,contrasts=120,times=[0,1,100,300],new_dynamics=0,new_thresholds=0,refits=0,
        workers=1,maximum_cpus=6,allowance=ALLOWANCE,reserve=RESERVE,
        main_forecast='16*checked_block_seconds+2*hash_seconds+120',
        benchmark_forecast='4*qualification_full_block_seconds+120',
        posthoc=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    run,out=ROOT/'runs'/RUN,ROOT/'outputs'/RUN
    assert sha256_file(run/'COMPLETE.json')==COMPLETE
    c,m=io.read_json(run/'COMPLETE.json'),io.read_json(run/'MANIFEST.json')
    assert io.read_json(run/'STATUS.json')==c and c['status']=='COMPLETE' and not (run/'FAILED.json').exists()
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256']
    assert len(m['input_sha256'])==1648 and len(c['output_sha256'])==38 and m['environment']==environment_manifest()
    assert m['input_sha256']==io.hashes([Path(p) for p in m['input_sha256']])
    assert c['output_sha256']==io.hashes([Path(p) for p in c['output_sha256']])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    audit=ROOT/'logs/d148_saved_audit_v1.json';assert sha256_file(audit)==AUDIT_SHA
    proof=io.read_json(audit);assert proof['passes'] and proof['new_dynamics']==0 and proof['complete_sha256']==COMPLETE
    for name,key in (('placement_audit','checker_sha256'),('placement_analysis_check','statistics_checker_sha256'),
        ('placement_history_check','history_checker_sha256'),('placement_run','runner_sha256')):
        assert sha256_file(WS/f'src/l20_extension1/{name}.py')==proof[key]
    files={Path(p) for p in (*m['input_sha256'],*c['output_sha256'])}
    files.update((run/'COMPLETE.json',run/'MANIFEST.json',run/'STATUS.json',out/'output_hashes.sha256',audit))
    files.update(WS/p for p in SCIENCE)
    return sorted(files)


def qualification(report):
    io.require_beneath(report,ROOT/'logs');tree=ET.parse(report).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=25 and not any(tree.findall('.//'+x) for x in ('failure','error','skipped'))
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_block','test_threshold_boundary','test_reverse_role','test_all_transitions','test_energy',
        'test_independent_fields','test_corruption','test_summary','test_normalization','test_source_closure',
        'test_resource_guard','test_detach_guard','test_no_dynamics','test_no_automatic_successor'}<=names
    seconds=max(float(c.get('time')) for c in cases if c.get('name')=='test_full_block')
    return dict(report=str(report),tests=len(cases),failures=0,skipped=0,full_block_seconds=seconds,
        benchmark_forecast=4*seconds+120)


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use stage already exists')
    proof=qualification(report);tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_hash_seconds=seconds,main_extracted=False)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_hash_seconds=seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report]) and f['main_extracted'] is False
    return f


def original():return io.read_json(ROOT/'outputs'/RUN/'summary.json')


def raw_block(index):
    if type(index) is not int or index not in BLOCKS+(DISPOSABLE,):raise ValueError('declared source block required')
    directory=ROOT/('tmp' if index==DISPOSABLE else 'outputs')/(RUN+('_benchmark' if index==DISPOSABLE else ''))
    raw=io.load_npz(directory/f'block_{index}.npz');meta=io.read_json(directory/f'block_{index}.json')
    assert meta['index']==index and len(meta['lives'])==4
    for l in range(4):assert meta['lives'][l]['index']==index and meta['lives'][l]['life']==l
    return raw


def detached_guard(required,stage):
    if required and os.environ.get(ENV)!='1':raise RuntimeError('forecast above ten minutes requires detached stage')
    if os.environ.get(ENV)=='1':
        assert os.getpid()==os.getsid(0) and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==logfile(stage)
        assert os.readlink('/proc/self/fd/2')==os.readlink('/proc/self/fd/1')


def ready(stage):
    descriptor=os.environ.pop('D148_REVIEW_READY_FD',None)
    if descriptor is not None:
        fd=int(descriptor)
        try:os.write(fd,json.dumps(dict(stage=stage,pid=os.getpid(),status='STARTED')).encode())
        except BrokenPipeError:pass
        finally:os.close(fd)


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir();began=time.monotonic()
    try:
        ready('benchmark');raw=raw_block(DISPOSABLE);value=review.extract(raw);proof=check.check_block(value,raw)
        io.write_npz(directory/'features.npz',value,ROOT)
        check.check_block(io.load_npz(directory/'features.npz'),raw)
        summary=review.summarize([value]*16,original(),(DISPOSABLE,)*16,True)
        verified=check.check_summary(summary,[value]*16,original(),(DISPOSABLE,)*16,True)
        io.write_json(directory/'fixture.json',dict(scientific_evidence=False,summary=summary,verification=verified),ROOT)
        seconds=time.monotonic()-began;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());raw_bytes=sum(v.nbytes for v in value.values())
        budget=16*raw_bytes+size+64*1024**2;assert budget<=ALLOWANCE
        forecast=16*seconds+2*hash_seconds+120
        timing=dict(status='COMPLETE',completed_utc=utc_now(),proof=proof,statistics=verified,
            checked_block_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,must_detach=forecast>600,
            raw_block_bytes=raw_bytes,benchmark_bytes=size,projected_bytes=budget,freeze_sha256=sha256_file(freeze_path()),
            output_sha256=io.hashes(list(directory.iterdir())),main_extracted=False,scientific_evidence=False)
        io.write_json(timing_path(),timing,ROOT);print(json.dumps(timing,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['main_extracted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path()) and t['scientific_evidence'] is False
    directory=benchmark_dir();assert {p.name for p in directory.iterdir()}=={'features.npz','fixture.json'}
    assert t['output_sha256']==io.hashes(list(directory.iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in directory.iterdir())
    assert t['projected_seconds']==16*t['checked_block_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==16*t['raw_block_bytes']+t['benchmark_bytes']+64*1024**2<=ALLOWANCE
    if audit:
        value=io.load_npz(directory/'features.npz');assert check.check_block(value,raw_block(DISPOSABLE))==t['proof']
        fixture=io.read_json(directory/'fixture.json');assert fixture['scientific_evidence'] is False
        verified=check.check_summary(fixture['summary'],[value]*16,original(),(DISPOSABLE,)*16,True)
        assert verified==fixture['verification']==t['statistics']
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def output_names():return [f'block_{b}.npz' for b in BLOCKS]+['summary.json','verification.json','input_hashes.sha256']


def saved_audit(complete=True):
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc']
    assert {p.name for p in out.iterdir()}==set(output_names())|({'output_hashes.sha256'} if complete else set())
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(m['input_sha256'])
    blocks=[];proofs=[]
    for b in BLOCKS:
        value=io.load_npz(out/f'block_{b}.npz');proofs.append(check.check_block(value,raw_block(b)));blocks.append(value)
    summary=io.read_json(out/'summary.json');verified=check.check_summary(summary,blocks,original())
    assert io.read_json(out/'verification.json')==dict(blocks=proofs,summary=verified)
    if complete:
        c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['source_complete']==COMPLETE
        assert c['output_sha256']==io.hashes([out/name for name in output_names()])
        assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
        assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=19,labelled_cells=12288,
        field_checkpoints=147456,packet_fields=24576,score_transition_tables=61440,new_dynamics=0,
        original_primary_unchanged=True,summary=verified)


def execute():
    resources();manifest_inputs=inputs();timing=timing_checked(True);detached_guard(timing['must_detach'],'execute')
    run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use review paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        m=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=manifest_inputs,timing=timing,
            environment=environment_manifest(),affinity=sorted(os.sched_getaffinity(0)),main_extracted=False)
        io.write_json(run/'MANIFEST.json',m,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(manifest_inputs))
        (run/'EXECUTION.lock').mkdir();atomic_json(run/'STATUS.json',dict(status='EXTRACTING',completed_blocks=[]),ROOT)
        ready('execute');blocks=[];proofs=[]
        for index in BLOCKS:
            raw=raw_block(index);value=review.extract(raw);proofs.append(check.check_block(value,raw))
            io.write_npz(out/f'block_{index}.npz',value,ROOT);blocks.append(value)
            atomic_json(run/'STATUS.json',dict(status='EXTRACTING',completed_blocks=list(BLOCKS[:len(blocks)]),updated_utc=utc_now()),ROOT)
        summary=review.summarize(blocks,original());verified=check.check_summary(summary,blocks,original())
        io.write_json(out/'summary.json',summary,ROOT);io.write_json(out/'verification.json',dict(blocks=proofs,summary=verified),ROOT)
        del blocks;proof=saved_audit(False);assert manifest_inputs==inputs()
        hashes=io.hashes([out/name for name in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            source_complete=COMPLETE,manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,
            hash_index_sha256=sha256_file(out/'output_hashes.sha256'),verification=proof,new_dynamics=0,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k!='output_sha256'},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def detach(stage):
    resources();frozen()
    if stage=='execute':
        timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    else:raise ValueError('declared stage required')
    lock=ROOT/'tmp'/f'{REVIEW}_{stage}_launch.lock';lock.mkdir()
    env=os.environ.copy();env[ENV]='1';reader,writer=os.pipe();env['D148_REVIEW_READY_FD']=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.placement_review_run','--'+stage],
                cwd=source.system.old.WS,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
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
    for name in ('freeze','benchmark','benchmark-audit','execute','audit','detach','detach-benchmark'):group.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze!=(args.test_report is not None):parser.error('test report only with freeze')
    if args.freeze:freeze(args.test_report)
    elif args.benchmark:benchmark()
    elif args.benchmark_audit:
        resources(False);frozen();timing_checked(True);print(json.dumps(dict(passes=True,new_dynamics=0)))
    elif args.execute:execute()
    elif args.audit:print(json.dumps(saved_audit(),indent=2))
    else:detach('benchmark' if args.detach_benchmark else 'execute')


if __name__=='__main__':main()
