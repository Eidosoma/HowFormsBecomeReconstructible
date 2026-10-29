"""D137 write-once external runner; benchmark/main detach above ten minutes."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import l20_reference_handoff as p
from . import l16_body_content_run as resource
from . import l15_repair_speed_run as u
from .io import DEFAULT_EXTERNAL_ROOT,atomic_json,environment_manifest,external_root,git_head,sha256_file,utc_now

WORKERS=6;ALLOWANCE=resource.ALLOWANCE;RESERVE=resource.RESERVE
DETACHED_ENV='L20_REFERENCE_HANDOFF_DETACHED_STAGE'
SOURCE_AUDIT='l20_serial_fidelity_audit_v1_attempt1'
SOURCE_SHA='2937fced5069861a7f07016b34ed4aa0f4cbabbcbdfda0e81b8d22d6e810f55e'

def preflight(root,starting=True):
    affinity=resource.preflight(root,starting);p.api();return affinity

def science_paths(root):
    d=root/'outputs'/SOURCE_AUDIT
    assert sha256_file(d/'COMPLETE.json')==SOURCE_SHA and not (d/'FAILED.json').exists()
    complete=u.read_json(d/'COMPLETE.json');inputs=u.read_json(d/'INPUTS.json')
    assert complete['status']=='COMPLETE' and complete['new_trajectories']==0
    assert inputs['environment']==environment_manifest()
    assert len(inputs['input_sha256'])==950 and len(complete['output_sha256'])==4
    assert inputs['input_sha256']==u.hashes([Path(x) for x in inputs['input_sha256']])
    assert complete['output_sha256']==u.hashes([Path(x) for x in complete['output_sha256']])
    assert {str(x) for x in d.iterdir()}==set(complete['output_sha256'])|{str(d/'COMPLETE.json')}
    return sorted(set([Path(x) for x in (*inputs['input_sha256'],*complete['output_sha256'])]+
        [d/'COMPLETE.json',p.WS/'reviews/L20_SERIAL_FIDELITY_2026-09-16.md',*[p.WS/n for n in p.SCIENCE]]))

def test_proof(report,root):
    report=u.require_beneath(report,root/'logs')
    assert not report.is_symlink() and report.name.startswith('d137_') and report.suffix=='.xml'
    tree=ET.parse(report).getroot();cases=tree.findall('.//testcase')
    assert not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    current=[c for c in cases if c.get('classname','').endswith('test_l20_reference_handoff')]
    assert len(current)>=40
    names={c.get('name','').split('[',1)[0] for c in current}
    assert {'test_full_disposable_life','test_source_bridge_exact','test_independent_dynamics',
        'test_packet_lineage','test_source_pairing','test_writer_no_other_state','test_reader_no_other_state',
        'test_condition_order','test_independent_observer','test_independent_summary',
        'test_gate_failure','test_raw_corruption','test_metadata_corruption','test_summary_corruption',
        'test_external_roundtrip','test_resource_guards','test_detachment_guard','test_reservation_guard',
        'test_long_stage_guard','test_long_main_guard','test_synthetic_decision_rules',
        'test_provenance','test_fresh_process_reader','test_fresh_process_saved_check',
        'test_reference_decomposition','test_handoff_factorial','test_birth_zero_causal_read',
        'test_unchanged_start_handling','test_synthetic_recurrence'}<=names
    seconds=max(float(c.get('time','0')) for c in current if c.get('name')=='test_full_disposable_life')
    assert seconds>0
    return dict(path=str(report),tests=len(cases),new_tests=len(current),failed=0,skipped=0,
        full_life_seconds=seconds,block_test_seconds=4*seconds,benchmark_forecast=16*seconds+60)

def freeze_path(root):return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def benchmark_dir(root):return root/'tmp'/f'{p.RUN_ID}_benchmark'
def timing_path(root):return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def log_path(root,stage):return root/'logs'/f'{p.RUN_ID}_{stage}.log'
def lock_path(root,stage):return root/'tmp'/f'{p.RUN_ID}_{stage}_launch.lock'
def output_names():return tuple(f'block_{i}.{e}' for i in p.TISSUES for e in ('npz','json'))+('summary.json','verification.json','input_hashes.sha256')
def contract():return p.contract()|dict(workers=6,reserve_bytes=RESERVE,allowance_bytes=ALLOWANCE,
    detach_above_seconds=600,output_files=list(output_names()),source_audit_sha256=SOURCE_SHA,
    benchmark_forecast='16*full_disposable_life_test_seconds+60',
    main_forecast='8*checked_block_seconds+2*hash_seconds+180')

def freeze(root,report):
    preflight(root);proof=test_proof(report,root)
    for path in (freeze_path(root),benchmark_dir(root),timing_path(root),root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID,
        log_path(root,'benchmark'),log_path(root,'main'),lock_path(root,'benchmark'),lock_path(root,'main')):
        if path.exists():raise FileExistsError(path)
    inputs=u.hashes(science_paths(root)+[report])
    u.write_json(freeze_path(root),dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,
        input_sha256=inputs,environment=environment_manifest(),git_head=git_head(p.WS),main_futures_seen=0),root)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),main_futures_seen=0,test_proof=proof)),flush=True)

def frozen(root):
    f=u.read_json(freeze_path(root));report=Path(f['test_proof']['path'])
    p.checker().nested(f['contract'],contract());assert f['environment']==environment_manifest() and f['main_futures_seen']==0
    assert f['test_proof']==test_proof(report,root) and f['input_sha256']==u.hashes(science_paths(root)+[report])
    return f

def detached_guard(root,stage,required):
    if required and os.environ.get(DETACHED_ENV)!=stage:raise AssertionError('long stage requires detached execution')
    if DETACHED_ENV in os.environ:
        assert os.environ[DETACHED_ENV]==stage and os.getpid()==os.getsid(0)
        assert os.readlink('/proc/self/fd/0')=='/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd))==str(log_path(root,stage)) for fd in (1,2))

def block_proof(meta,raw):
    rows=[x['replay'] for x in meta['lives']]
    return dict(index=meta['index'],full_life_replays=len(rows),
        **{k:sum(x[k] for x in rows) for k in ('known_source_writers','new_handoff_writers','reader_paths','selector_decisions','exact_path_aliases','matched_body_ema_starts')},
        max_abs=max(x[k] for x in rows for k in x if k.endswith('_max_abs')),
        uncompressed_bytes=sum(x.nbytes for x in raw.values()))

def checked_block(root,directory,index):
    preflight(root,False);raw,meta=p.execute_block(index,root=root)
    saved=u.save_pair(directory,f'block_{index}',raw,meta,root);source,_=p.load_source(index,root)
    assert p.checker().check_block(saved,u.read_json(directory/f'block_{index}.json'),p.CONFIG,source,p.source_paths(index,root))
    return block_proof(meta,raw)

def benchmark(root):
    preflight(root);f=frozen(root);detached_guard(root,'benchmark',f['test_proof']['benchmark_forecast']>600)
    d=benchmark_dir(root);d.mkdir();start=time.monotonic()
    try:
        proof=checked_block(root,d,p.DISPOSABLE);raw=u.load_npz(d/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8),[raw]*8,p.CONFIG)
        seconds=time.monotonic()-start;tick=time.monotonic();frozen(root);hseconds=time.monotonic()-tick
        size=sum(x.stat().st_size for x in d.iterdir());forecast=8*seconds+2*hseconds+180
        budget=8*proof['uncompressed_bytes']+size+32*1024**2;assert 0<budget<=ALLOWANCE;preflight(root)
        result=dict(status='COMPLETE',completed_utc=utc_now(),qualification_pool=False,block=proof,
            checked_block_seconds=seconds,hash_seconds=hseconds,projected_seconds=forecast,must_detach=forecast>600,
            projected_total_bytes=budget,benchmark_bytes=size,artifact_sha256=u.hashes(list(d.iterdir())),
            freeze_sha256=sha256_file(freeze_path(root)))
        u.write_json(timing_path(root),result,root)
        print(json.dumps(result,indent=2),flush=True)
    except Exception as error:u.failure(d,error,root);raise

def timing_checked(root):
    t=u.read_json(timing_path(root));d=benchmark_dir(root)
    assert t['status']=='COMPLETE' and t['qualification_pool'] is False and t['freeze_sha256']==sha256_file(freeze_path(root))
    assert {x.name for x in d.iterdir()}=={f'block_{p.DISPOSABLE}.npz',f'block_{p.DISPOSABLE}.json'}
    assert t['artifact_sha256']==u.hashes(list(d.iterdir()))
    assert t['projected_seconds']==8*t['checked_block_seconds']+2*t['hash_seconds']+180
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['benchmark_bytes']==sum(x.stat().st_size for x in d.iterdir())
    assert t['projected_total_bytes']==8*t['block']['uncompressed_bytes']+t['benchmark_bytes']+32*1024**2<=ALLOWANCE
    return t

def benchmark_audit(root):
    preflight(root,False);frozen(root);t=timing_checked(root);d=benchmark_dir(root)
    raw=u.load_npz(d/f'block_{p.DISPOSABLE}.npz');meta=u.read_json(d/f'block_{p.DISPOSABLE}.json');source,_=p.load_source(p.DISPOSABLE,root)
    assert p.checker().check_block(raw,meta,p.CONFIG,source,p.source_paths(p.DISPOSABLE,root))
    assert t['block']==block_proof(meta,raw)
    return dict(passes=True,new_dynamics=0,projected_seconds=t['projected_seconds'],projected_total_bytes=t['projected_total_bytes'])

def main_inputs(root):
    f=frozen(root);timing_checked(root)
    return u.hashes([Path(x) for x in f['input_sha256']]+[freeze_path(root),timing_path(root),*benchmark_dir(root).iterdir()])

def prepare(root):
    preflight(root);inputs=main_inputs(root);timing=timing_checked(root)
    run=root/'runs'/p.RUN_ID;out=root/'outputs'/p.RUN_ID
    if run.exists() or out.exists():raise FileExistsError('single-use identity already reserved')
    run.mkdir();out.mkdir()
    manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=inputs,environment=environment_manifest(),timing=timing,git_head=git_head(p.WS))
    u.write_json(run/'MANIFEST.json',manifest,root)
    with (out/'input_hashes.sha256').open('x') as f:f.write(u.hash_text(inputs))
    atomic_json(run/'STATUS.json',dict(status='PREPARED',run_id=p.RUN_ID),root)
    print(json.dumps(dict(status='PREPARED',inputs=len(inputs),forecast=timing['projected_seconds'])),flush=True)

def prepared(root):
    run=root/'runs'/p.RUN_ID;out=root/'outputs'/p.RUN_ID;m=u.read_json(run/'MANIFEST.json')
    p.checker().nested(m['contract'],contract());assert m['environment']==environment_manifest()
    assert m['input_sha256']==main_inputs(root) and m['timing']==timing_checked(root)
    assert (out/'input_hashes.sha256').read_text()==u.hash_text(m['input_sha256'])
    return m

def saved_audit(root,complete=True):
    preflight(root,False);manifest=prepared(root);run=root/'runs'/p.RUN_ID;out=root/'outputs'/p.RUN_ID
    assert {x.name for x in out.iterdir()}==set(output_names())|({'output_hashes.sha256'} if complete else set())
    blocks=[];proofs=[];audit=p.checker()
    for i in p.TISSUES:
        raw=u.load_npz(out/f'block_{i}.npz');meta=u.read_json(out/f'block_{i}.json');source,_=p.load_source(i,root)
        assert audit.check_block(raw,meta,p.CONFIG,source,p.source_paths(i,root));blocks.append(raw);proofs.append(block_proof(meta,raw))
    assert u.read_json(out/'verification.json')==proofs
    assert audit.check_summary(u.read_json(out/'summary.json'),blocks,p.CONFIG)
    if complete:
        c=u.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and u.read_json(run/'STATUS.json')==c
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json')
        assert c['output_sha256']==u.hashes([out/n for n in output_names()])
        assert (out/'output_hashes.sha256').read_text()==u.hash_text(c['output_sha256'])
        assert c['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
    return dict(passes=True,input_hashes=len(manifest['input_sha256']),output_hashes=19 if complete else 0,
        known_source_writers=192,new_handoff_writers=576,reader_paths=4224,selectors=3840,new_dynamics_at_audit=0)

def execute(root):
    preflight(root);m=prepared(root);detached_guard(root,'main',m['timing']['must_detach'])
    run=root/'runs'/p.RUN_ID;out=root/'outputs'/p.RUN_ID
    assert u.read_json(run/'STATUS.json')['status']=='PREPARED' and not (run/'FAILED.json').exists()
    (run/'EXECUTION.lock').mkdir();start=time.monotonic()
    try:
        atomic_json(run/'STATUS.json',dict(status='RUNNING',run_id=p.RUN_ID,started_utc=utc_now()),root)
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs=[pool.submit(checked_block,root,out,i) for i in p.TISSUES]
            proofs=[]
            for job in as_completed(jobs):
                proof=job.result();proofs.append(proof);print(json.dumps(dict(block_complete=proof['index'])),flush=True)
        proofs.sort(key=lambda x:x['index']);blocks=[u.load_npz(out/f'block_{i}.npz') for i in p.TISSUES]
        summary=p.summarize(blocks);assert p.checker().check_summary(summary,blocks,p.CONFIG)
        u.write_json(out/'summary.json',summary,root);u.write_json(out/'verification.json',proofs,root)
        saved_audit(root,False);inputs=main_inputs(root);assert inputs==m['input_sha256'];preflight(root,False)
        outputs=u.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as f:f.write(u.hash_text(outputs))
        size=sum(x.stat().st_size for x in out.iterdir());assert size<=ALLOWANCE
        result=dict(status='COMPLETE',run_id=p.RUN_ID,completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=outputs,hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            output_bytes=size,automatic_successor=False,label=summary['label'])
        u.write_json(run/'COMPLETE.json',result,root);atomic_json(run/'STATUS.json',result,root)
        print(json.dumps(dict(status='COMPLETE',seconds=result['elapsed_seconds'],bytes=size,label=summary['label'])),flush=True)
    except Exception as error:u.failure(run,error,root);raise

def detach(root,stage):
    preflight(root)
    if stage=='benchmark':
        frozen(root)
        if benchmark_dir(root).exists() or timing_path(root).exists():raise FileExistsError('benchmark reserved')
    elif stage=='main':
        prepared(root);run=root/'runs'/p.RUN_ID
        assert u.read_json(run/'STATUS.json')['status']=='PREPARED' and not (run/'EXECUTION.lock').exists() and not (run/'FAILED.json').exists()
    else:raise ValueError('declared detached stage required')
    lock_path(root,stage).mkdir();log=log_path(root,stage);env=os.environ.copy();env[DETACHED_ENV]=stage
    cmd=[sys.executable,'-m','laws_confirmation.l20_reference_handoff_run','--external-root',str(root),'--benchmark' if stage=='benchmark' else '--execute']
    with log.open('xb') as f:
        child=subprocess.Popen(cmd,cwd=p.WS,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',stage=stage,pid=child.pid,log=str(log),automatic_polling=False,user_polls=True,automatic_successor=False)),flush=True)

def main():
    if sys.flags.optimize:raise RuntimeError('assertions must be enabled')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--external-root',type=Path,default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument('--test-report',type=Path);mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','benchmark-audit','prepare','execute','audit','detach-benchmark','detach-main'):mode.add_argument('--'+name,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    if args.freeze!=(args.test_report is not None):parser.error('--test-report only required for --freeze')
    if args.freeze:freeze(root,args.test_report)
    elif args.benchmark:benchmark(root)
    elif args.benchmark_audit:print(json.dumps(benchmark_audit(root),indent=2))
    elif args.prepare:prepare(root)
    elif args.execute:execute(root)
    elif args.audit:print(json.dumps(saved_audit(root),indent=2))
    elif args.detach_benchmark:detach(root,'benchmark')
    else:detach(root,'main')

if __name__=='__main__':main()

