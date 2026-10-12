"""D105 write-once run; read-only D104 anchor, freeze, benchmark and guarded launch.

Staged launch/audit plumbing is copied from D104, not monkeypatched into it.
"""
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

from . import l19_internal_repair as p
from . import l19_copy_damage_run as previous
from . import l15_repair_speed_run as u
from .io import atomic_json,environment_manifest,external_root,git_head,sha256_file,utc_now


def prior_artifacts(root):
    manifest=previous.prepared(root)
    directory=root/'outputs'/p.base.RUN_ID; run=root/'runs'/p.base.RUN_ID
    assert sha256_file(run/'COMPLETE.json')=='6ff32835d1bdcebe990b152d12cb56b6d9fb718f7617807836dd9571ae34fb16'
    assert sha256_file(directory/'summary.json')=='a380bb652deb54a9f7f030d990b85e7ec7ebf38c9431c03b1276f827852a7f74'
    complete=u.read_json(run/'COMPLETE.json'); assert complete['status']=='COMPLETE'
    assert u.read_json(run/'STATUS.json')==complete
    names=set(previous.output_names())|{'output_hashes.sha256'}
    assert {x.name for x in directory.iterdir()}==names
    assert complete['output_sha256']==u.hashes([directory/n for n in previous.output_names()])
    assert complete['hash_file_sha256']==sha256_file(directory/'output_hashes.sha256')
    assert complete['manifest_sha256']==sha256_file(run/'MANIFEST.json')
    return [Path(x) for x in manifest['input_sha256']]+[directory/n for n in names]+[
        run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]


def science_paths(root):
    return sorted(set(prior_artifacts(root)+[p.WS/n for n in (*p.SCIENCE,
        'reviews/L19_COPY_DAMAGE_2026-09-12.md')]))


def test_proof(path,root):
    path=u.require_beneath(path,root/'logs')
    assert not path.is_symlink() and path.name.startswith('d105_') and path.suffix=='.xml'
    report=ET.parse(path).getroot(); cases=report.findall('.//testcase')
    assert len(cases)>=100 and not any(report.findall('.//'+x) for x in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    assert {'test_d104_saved_baseline_anchor','test_full_disposable_replay',
        'test_target_exclusion','test_between_boundary_record_immutable','test_reader_off_aliases',
        'test_hand_built_primary','test_saved_roundtrip_and_external_guard',
        'test_repair_symmetries','test_hand_built_median_and_no_mutation',
        'test_detail_observer_is_not_generic','test_equal_noise_and_clocks'} <= {c.get('name') for c in cases}
    assert any(c.get('classname','').endswith('test_l19_internal_repair') for c in cases)
    return dict(path=str(path),tests=len(cases),failed=0,skipped=0)


def output_names():
    return tuple(f'block_{t}.{ext}' for t in p.TISSUES for ext in ('npz','json'))+(
        'summary.json','verification.json','input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=4,reserve_bytes=u.RESERVE,allowance_bytes=u.ALLOWANCE,
        previous_run=p.base.RUN_ID,documentation_exception=previous.contract()['documentation_exception'],detach_above_seconds=600,
        output_files=list(output_names()),output_hash_count=19,
        forecast='8*checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*uncompressed_block_bytes+benchmark_bytes+32MiB; no new source artifacts')


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root,report):
    u.preflight(root); proof=test_proof(report,root)
    assert previous.audit(root)["passes"], "prior saved audit failed"
    for path in (freeze_path(root),timing_path(root),benchmark_dir(root),root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID):
        if path.exists(): raise FileExistsError(path)
    inputs=u.hashes(science_paths(root)+[report])
    u.write_json(freeze_path(root),dict(frozen_utc=utc_now(),contract=contract(),input_sha256=inputs,
        test_proof=proof,environment=environment_manifest(),git_head=git_head(p.WS),main_futures_seen=0),root)
    print(f'D105 frozen: {len(inputs)} inputs, zero main futures',flush=True)


def frozen(root):
    record=u.read_json(freeze_path(root)); report=Path(record['test_proof']['path'])
    p.checker().nested(record['contract'],contract())
    assert record['main_futures_seen']==0 and record['environment']==environment_manifest()
    assert record['test_proof']==test_proof(report,root)
    assert record['input_sha256']==u.hashes(science_paths(root)+[report])
    return record


def checked_block(root,directory,index):
    u.preflight(root,starting=False)
    raw,meta=p.execute_block(index)
    loaded=u.save_pair(directory,f'block_{index}',raw,meta,root)
    assert p.checker().check_block(loaded,u.read_json(directory/f'block_{index}.json'),p.CONFIG,replay=False)
    return dict(index=index,full_life_replays=2,exact_alias_branches=2,
        max_abs=max(m['replay']['max_abs'] for m in meta['lives']),
        uncompressed_bytes=sum(v.nbytes for v in raw.values()))


def benchmark(root):
    u.preflight(root); frozen(root)
    old_timing=previous.timing_checked(root)
    assert 8*old_timing['checked_block_seconds']+60<=600,'benchmark itself needs detached design'
    directory=benchmark_dir(root); directory.mkdir(); start=time.monotonic()
    try:
        block=checked_block(root,directory,p.DISPOSABLE)
        raw=u.load_npz(directory/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8),[raw]*8,p.CONFIG)
        seconds=time.monotonic()-start
        hstart=time.monotonic(); frozen(root); hash_seconds=time.monotonic()-hstart
        source_bytes=0  # prior artifacts are reused read-only, not created again
        saved=list(directory.iterdir()); size=sum(x.stat().st_size for x in saved)
        forecast=8*seconds+2*hash_seconds+180
        budget=8*block['uncompressed_bytes']+source_bytes+size+32*1024**2
        assert budget<=u.ALLOWANCE,'budget exceeded; no automatic downsizing'
        u.preflight(root)
        record=dict(benchmark_utc=utc_now(),disposable=p.DISPOSABLE,main_pool=False,block=block,
            checked_block_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,
            must_detach=forecast>600,projected_total_bytes=budget,source_bytes=source_bytes,
            benchmark_bytes=size,artifact_sha256=u.hashes(saved),freeze_sha256=sha256_file(freeze_path(root)))
        u.write_json(timing_path(root),record,root)
        print(json.dumps({k:record[k] for k in ('checked_block_seconds','projected_seconds','must_detach','projected_total_bytes')},indent=2),flush=True)
    except Exception as error:
        u.failure(directory,error,root); raise


def timing_checked(root):
    record=u.read_json(timing_path(root))
    assert record['freeze_sha256']==sha256_file(freeze_path(root))
    assert record['disposable']==p.DISPOSABLE and record['main_pool'] is False
    assert record['artifact_sha256']==u.hashes(list(benchmark_dir(root).iterdir()))
    forecast=8*record['checked_block_seconds']+2*record['hash_seconds']+180
    assert np.isfinite(forecast) and forecast>0 and record['projected_seconds']==forecast
    assert record['must_detach']==(forecast>600)
    assert record['projected_total_bytes']==(8*record['block']['uncompressed_bytes']+
        record['source_bytes']+record['benchmark_bytes']+32*1024**2)<=u.ALLOWANCE
    return record


def main_inputs(root):
    record=frozen(root); timing_checked(root)
    return u.hashes([Path(x) for x in record['input_sha256']]+[freeze_path(root),timing_path(root),*benchmark_dir(root).iterdir()])


def prepare(root):
    u.preflight(root); inputs=main_inputs(root); timing=timing_checked(root)
    run,out=root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('run/output already reserved')
    run.mkdir(); out.mkdir()
    try:
        u.write_json(run/'MANIFEST.json',dict(contract=contract(),input_sha256=inputs,
            environment=environment_manifest(),timing=timing,prepared_utc=utc_now(),git_head=git_head(p.WS)),root)
        with (out/'input_hashes.sha256').open('x') as handle: handle.write(u.hash_text(inputs))
        atomic_json(run/'STATUS.json',dict(status='PREPARED',run_id=p.RUN_ID,
            projected_seconds=timing['projected_seconds'],must_detach=timing['must_detach']),root)
        print(f'D105 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s',flush=True)
    except Exception as error:
        u.failure(run,error,root); raise


def prepared(root):
    manifest=u.read_json(root/'runs'/p.RUN_ID/'MANIFEST.json')
    p.checker().nested(manifest['contract'],contract())
    assert manifest['input_sha256']==main_inputs(root)
    assert manifest['environment']==environment_manifest() and manifest['timing']==timing_checked(root)
    assert (root/'outputs'/p.RUN_ID/'input_hashes.sha256').read_text()==u.hash_text(manifest['input_sha256'])
    return manifest


def detached_guard(root,required):
    run=root/'runs'/p.RUN_ID
    if required or (run/'LAUNCH.json').exists():
        launch=u.read_json(run/'LAUNCH.json')
        assert launch['pid']==os.getpid() and os.getsid(0)==os.getpid()
        assert os.readlink('/proc/self/fd/0')=='/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd))==launch['log'] for fd in (1,2))
        assert launch['manifest_sha256']==sha256_file(run/'MANIFEST.json')


def detach(root):
    u.preflight(root); prepared(root); run=root/'runs'/p.RUN_ID
    for name in ('EXECUTION.lock','COMPLETE.json','FAILED.json'):
        if (run/name).exists(): raise FileExistsError('execution already attempted')
    (run/'LAUNCH.lock').mkdir(); log=root/'logs'/f'{p.RUN_ID}.log'
    command=[sys.executable,'-m','laws_confirmation.l19_internal_repair_run','--external-root',str(root),'--run']
    env=os.environ.copy(); env['L19_REPAIR_DETACHED_LOG']=str(log)
    with log.open('xb') as handle:
        child=subprocess.Popen(command,cwd=p.WS,env=env,stdin=subprocess.DEVNULL,
            stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',pid=child.pid,log=str(log),user_polls=True,automatic_polling=False)),flush=True)


def audit(root,complete=True,replay=False):
    u.preflight(root,starting=False); manifest=prepared(root)
    out,run=root/'outputs'/p.RUN_ID,root/'runs'/p.RUN_ID
    assert {x.name for x in out.iterdir()}==set(output_names())|({'output_hashes.sha256'} if complete else set())
    assert (run/'EXECUTION.lock').is_dir() and not (run/'FAILED.json').exists()
    if replay: assert manifest['timing']['projected_seconds']<=600,'long replay must be detached separately'
    p.api(); blocks=[]
    for index in p.TISSUES:
        raw,meta=u.load_npz(out/f'block_{index}.npz'),u.read_json(out/f'block_{index}.json')
        assert type(meta['index']) is int and meta['index']==index
        assert p.checker().check_block(raw,meta,p.CONFIG,replay)
        blocks.append(raw)
    summary=u.read_json(out/'summary.json'); assert p.checker().check_summary(summary,blocks,p.CONFIG)
    verification=u.read_json(out/'verification.json')
    assert verification['independent_life_replays']==16 and verification['exact_alias_branches']==16
    assert [r['index'] for r in verification['rows']]==list(p.TISSUES)
    assert all(r['full_life_replays']==2 and r['exact_alias_branches']==2 and 0<=r['max_abs']<=1e-10
               for r in verification['rows'])
    if complete:
        status=u.read_json(run/'COMPLETE.json')
        assert status['status']=='COMPLETE' and u.read_json(run/'STATUS.json')==status
        actual=u.hashes([out/n for n in output_names()]); assert status['output_sha256']==actual
        assert (out/'output_hashes.sha256').read_text()==u.hash_text(actual)
        assert status['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256']==sha256_file(run/'MANIFEST.json')
        assert status['output_bytes']==sum(x.stat().st_size for x in out.iterdir())<=manifest['timing']['projected_total_bytes']
    return dict(passes=True,checked_blocks=8,checked_lives=16,fresh_branches=128,
        exact_alias_branches=16,full_dynamics_replayed_now=replay,input_hashes=len(manifest['input_sha256']),
        output_hashes=19 if complete else 0,label=summary['label'],primary=summary['primary'])


def run_experiment(root):
    u.preflight(root); manifest=prepared(root); run,out=root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID
    if 'L19_REPAIR_DETACHED_LOG' in os.environ:
        u.write_json(run/'LAUNCH.json',dict(pid=os.getpid(),launched_utc=utc_now(),
            log=os.environ['L19_REPAIR_DETACHED_LOG'],manifest_sha256=sha256_file(run/'MANIFEST.json')),root)
    detached_guard(root,manifest['timing']['must_detach'])
    (run/'EXECUTION.lock').mkdir(); start=time.monotonic()
    try:
        checks={}
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending={pool.submit(checked_block,root,out,t):t for t in p.TISSUES}
            for future in as_completed(pending):
                index=pending[future]; checks[index]=future.result(); u.preflight(root,starting=False)
                atomic_json(run/'STATUS.json',dict(status='RUNNING',run_id=p.RUN_ID,
                    checked_blocks=len(checks),updated_utc=utc_now()),root)
                print(f'D105 tissue {index}: two full independent replays and two aliases pass',flush=True)
        blocks=[u.load_npz(out/f'block_{t}.npz') for t in p.TISSUES]
        u.write_json(out/'summary.json',p.summarize(blocks),root)
        u.write_json(out/'verification.json',dict(independent_life_replays=16,exact_alias_branches=16,
            rows=[checks[t] for t in p.TISSUES],checked_utc=utc_now()),root)
        checked=audit(root,complete=False)
        actual=u.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as handle: handle.write(u.hash_text(actual))
        size=sum(x.stat().st_size for x in out.iterdir())
        assert size<=manifest['timing']['projected_total_bytes']<=u.ALLOWANCE
        u.preflight(root,starting=False)
        status=dict(status='COMPLETE',run_id=p.RUN_ID,completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            output_bytes=size,output_sha256=actual,manifest_sha256=sha256_file(run/'MANIFEST.json'),
            hash_file_sha256=sha256_file(out/'output_hashes.sha256'),saved_audit=checked)
        u.write_json(run/'COMPLETE.json',status,root); atomic_json(run/'STATUS.json',status,root)
        print(json.dumps({k:status[k] for k in ('status','elapsed_seconds','output_bytes','saved_audit')},indent=2),flush=True)
    except Exception as error:
        u.failure(run,error,root)
        atomic_json(run/'STATUS.json',dict(status='FAILED',run_id=p.RUN_ID,error=str(error),automatic_retry=False),root)
        raise


def main(default_command=None):
    if sys.flags.optimize: raise RuntimeError('assertions must remain enabled')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root',type=Path,required=True)
    parser.add_argument('--test-report',type=Path); parser.add_argument('--replay',action='store_true')
    group=parser.add_mutually_exclusive_group(required=default_command is None)
    commands=('freeze','benchmark','prepare','run','detach','audit')
    for name in commands: group.add_argument('--'+name.replace('_','-'),action='store_true')
    args=parser.parse_args(); root=external_root(args.external_root)
    selected=[name for name in commands if getattr(args,name)]; command=selected[0] if selected else default_command
    if (command in ('freeze',)) != (args.test_report is not None):
        parser.error('--test-report required only for freeze')
    if args.replay and command!='audit': parser.error('--replay is audit-only')
    if command=='audit': print(json.dumps(audit(root,replay=args.replay),indent=2)); return
    if command in ('freeze',): globals()[command](root,args.test_report)
    else: (run_experiment if command=='run' else globals()[command])(root)


if __name__=='__main__': main()


