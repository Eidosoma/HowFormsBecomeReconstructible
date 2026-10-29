"""D101 write-once source control, freeze, benchmark, guarded launch and audit."""
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

from . import l19_broadcast_withdrawal as p
from . import l15_repair_speed_run as u
from .io import atomic_json,environment_manifest,external_root,git_head,sha256_file,utc_now

SOURCE_UNITS=tuple(range(4))
OLD_HASHES={
 'architecture_inventory.csv':'c9e985c0ecc0cafc0a0ea3c3f3ea1c2c05352f2e80c72222073bdc33e4d6562f',
 'audit.json':'204fb704ef4cdbac10d67e4187ca73912aa076dca7dcc67f6a41089ee31e22e7',
 'audit.md':'600b19be2592d9c592ff2a73ba400064bc79fa45e63e08181d05ef258ff8dfc3',
 'e64_corner_rows.csv':'caf3133f16633f7e3867bb8180a6b5d9809d8461b2ba754ef76fb3bd48307f9c',
 'e64_regime_repeats.csv':'5d1196b2303949ecf6b86ceb80d957b1ac786b10a6f185908e9de4fa18fe2f3a',
 'e65_arm_rows.csv':'a23be39979e4ca8dea3dffb4f5ba9498391c925265e1c8b2146402463104a740',
 'input_hashes.sha256':'0704522a6c64d78d8934907a22a8aca26576bd03cb051f79bd1ab8b702e1f5a4'}
LEGACY_CASE=dict(path=str(p.WS/'laws/L19_incorruptible_reference.md'),
 historical_sha256='8f7e729eff39a68aec87b114f01c715a5e862d3d51b4369c2a124477c08c9b0b',
 current_sha256='9b6c2d0cc3fd2f3d5cfd9ffe1a2c2af7b266a140372d592b7b6fd37f9b054695',
 reason='explicit documentation-only exception; exact earlier text/revision unverified; old audit preserved')


def source_cache_paths():
    return [p.ORIGIN/f'teaching/results/full/work/teach_shard_{s:02d}_of_06.json' for s in range(6)]


def source_expected():
    rows={}
    for path in source_cache_paths():
        data=u.read_json(path); assert data['config_digest']==p.SOURCE_DIGEST
        for row in data['entries']:
            if (row['arm']=='broadcast' and row['T']==500 and row['r_mode']=='free'
                    and row['sigma_r']==0 and row['barcode'] is None):
                assert row['tissue'] not in rows
                rows[row['tissue']]=row
    assert set(rows)==set(SOURCE_UNITS)
    return rows


def check_legacy_row(digest,name):
    if name==LEGACY_CASE['path']:
        assert digest==LEGACY_CASE['historical_sha256']
        assert sha256_file(Path(name))==LEGACY_CASE['current_sha256'],'unrecognized case revision'
    else:
        assert sha256_file(Path(name))==digest,'old L19 input drift: '+name


def science_paths(root):
    old=root/'outputs/l19_incorruptible_reference_audit_v1'
    for name,digest in OLD_HASHES.items():
        assert sha256_file(old/name)==digest,'old L19 output drift: '+name
    rows=[line.split('  ',1) for line in (old/'input_hashes.sha256').read_text().splitlines()]
    assert len(rows)==143 and len({x[1] for x in rows})==143
    assert sum(name==LEGACY_CASE['path'] for _,name in rows)==1
    for digest,name in rows: check_legacy_row(digest,name)
    paths=[Path(name) for _,name in rows]+[old/name for name in OLD_HASHES]
    paths+=[p.WS/name for name in (*p.SCIENCE,'src/laws_confirmation/io.py',
        'src/laws_confirmation/__init__.py','src/laws_confirmation/l15_repair_speed.py',
        'src/laws_confirmation/l15_repair_speed_run.py','scripts/audit_l15_repair_speed_outputs.py',
        'tests/test_l15_repair_speed.py','tests/test_l19_audit.py',
        'reviews/L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md',
        'reviews/L19_NEXT_STEP_2026-09-12.md','reviews/L15_CLOSEOUT_2026-09-12.md')]
    paths+=[*source_cache_paths(),p.ORIGIN/'LAWS.md',p.WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md']
    assert sha256_file(p.ORIGIN/'LAWS.md')=='d4205acf612f7eb7f4d63022ee9bc9a66d0c35c114b5a3930bab982788e011db'
    assert sha256_file(p.WS.parents[3]/'PRE_PRINT_PAPER_DRAFT_V2.3.md')=='c0a80cdcda6373708639a25bfb535a8df979a8b7b820a09f3ff37b78aea686d0'
    for package in p.PACKAGES:
        found=sorted((p.ORIGIN/package/'src').rglob('*.py')); assert found
        paths+=found
    return sorted(set(paths))


def test_proof(path,root):
    path=u.require_beneath(path,root/'logs')
    assert not path.is_symlink() and path.name.startswith('d101_') and path.suffix=='.xml'
    report=ET.parse(path).getroot(); cases=report.findall('.//testcase')
    assert len(cases)>=70 and not any(report.findall('.//'+x) for x in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    assert {'test_full_disposable_replay','test_order_and_duplicate_aliases',
        'test_free_window_has_no_target_argument','test_hand_built_primary',
        'test_short_source_replay','test_documentation_exception_is_exact',
        'test_saved_roundtrip_and_external_guard'} <= {c.get('name') for c in cases}
    return dict(path=str(path),tests=len(cases),failed=0,skipped=0)


def output_names():
    return tuple(f'block_{t}.{ext}' for t in p.TISSUES for ext in ('npz','json'))+(
        'summary.json','verification.json','input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=4,reserve_bytes=u.RESERVE,allowance_bytes=u.ALLOWANCE,
        old_matching_inputs=142,documentation_exception=LEGACY_CASE,detach_above_seconds=600,
        output_files=list(output_names()),output_hash_count=19,
        forecast='8*checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*uncompressed_block_bytes+source_bytes+benchmark_bytes+32MiB')


def source_worker(root,index):
    u.preflight(root,starting=False); start=time.monotonic()
    raw,meta=p.source_control(index)
    assert meta['result']==source_expected()[index],'retained source outcome mismatch'
    u.save_pair(root/'outputs'/p.CONTROL_ID,f'tissue_{index}',raw,meta,root)
    return dict(index=index,seconds=time.monotonic()-start,max_abs=meta['replay']['max_abs'])


def source_summary(directory):
    expected=source_expected(); results=[]
    for index in SOURCE_UNITS:
        meta=u.read_json(directory/f'tissue_{index}.json')
        assert type(meta['index']) is int and meta['index']==index
        assert meta['result']==expected[index]
        p.checker().nested(meta['config'],p.api()['TeachConfig']().as_dict())
        assert meta['replay']['full_source_replay'] and 0<=meta['replay']['max_abs']<=1e-10
        results.append(meta['result'])
    return dict(source_jobs=4,lineages_per_job=8,cycles=12,exact_retained_scalars=True,
        independent_full_replays=4,mean_fidelity=float(np.mean([x['fidelity'] for x in results])),
        results=results,known_outcomes=True,main_pool=False)


def source_controls(root,report):
    u.preflight(root); proof=test_proof(report,root)
    forecast=3*max(u.read_json(x)['elapsed_seconds'] for x in source_cache_paths())+180
    assert forecast<=600,'source controls require detached preparation before reservation'
    inputs=u.hashes(science_paths(root)+[report])
    directory=root/'outputs'/p.CONTROL_ID; directory.mkdir(); start=time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json',dict(input_sha256=inputs,test_proof=proof,
            contract=contract(),environment=environment_manifest(),started_utc=utc_now(),
            git_head=git_head(p.WS),projected_seconds=forecast),root)
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
            records=list(pool.map(source_worker,[root]*4,SOURCE_UNITS))
        summary=source_summary(directory); u.write_json(directory/'summary.json',summary,root)
        assert inputs==u.hashes(science_paths(root)+[report])
        u.preflight(root,starting=False)
        complete=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            rows=records,output_sha256=u.hashes(list(directory.iterdir())))
        u.write_json(directory/'COMPLETE.json',complete,root)
        print(json.dumps(summary | dict(seconds=complete['elapsed_seconds']),indent=2),flush=True)
    except Exception as error:
        u.failure(directory,error,root); raise


def source_artifacts(root,report):
    directory=root/'outputs'/p.CONTROL_ID
    names={f'tissue_{i}.{e}' for i in SOURCE_UNITS for e in ('npz','json')}|{'INPUTS.json','summary.json','COMPLETE.json'}
    assert {x.name for x in directory.iterdir()}==names
    inputs=u.read_json(directory/'INPUTS.json'); complete=u.read_json(directory/'COMPLETE.json')
    assert inputs['input_sha256']==u.hashes(science_paths(root)+[report])
    p.checker().nested(inputs['contract'],contract())
    assert inputs['environment']==environment_manifest() and inputs['test_proof']==test_proof(report,root)
    assert complete['status']=='COMPLETE'
    assert complete['output_sha256']==u.hashes([directory/n for n in names if n!='COMPLETE.json'])
    assert u.read_json(directory/'summary.json')==source_summary(directory)
    return [directory/n for n in sorted(names)]


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root,report):
    u.preflight(root); proof=test_proof(report,root)
    for path in (freeze_path(root),timing_path(root),benchmark_dir(root),root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID):
        if path.exists(): raise FileExistsError(path)
    inputs=u.hashes(science_paths(root)+[report]+source_artifacts(root,report))
    u.write_json(freeze_path(root),dict(frozen_utc=utc_now(),contract=contract(),input_sha256=inputs,
        test_proof=proof,environment=environment_manifest(),git_head=git_head(p.WS),main_futures_seen=0),root)
    print(f'D101 frozen: {len(inputs)} inputs, zero main futures',flush=True)


def frozen(root):
    record=u.read_json(freeze_path(root)); report=Path(record['test_proof']['path'])
    p.checker().nested(record['contract'],contract())
    assert record['main_futures_seen']==0 and record['environment']==environment_manifest()
    assert record['test_proof']==test_proof(report,root)
    assert record['input_sha256']==u.hashes(science_paths(root)+[report]+source_artifacts(root,report))
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
    source=u.read_json(root/'outputs'/p.CONTROL_ID/'COMPLETE.json')
    assert 6*max(x['seconds'] for x in source['rows'])+30<=600,'benchmark itself needs detached design'
    directory=benchmark_dir(root); directory.mkdir(); start=time.monotonic()
    try:
        block=checked_block(root,directory,p.DISPOSABLE)
        raw=u.load_npz(directory/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8),[raw]*8,p.CONFIG)
        seconds=time.monotonic()-start
        hstart=time.monotonic(); frozen(root); hash_seconds=time.monotonic()-hstart
        source_bytes=sum(x.stat().st_size for x in (root/'outputs'/p.CONTROL_ID).iterdir())
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
        print(f'D101 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s',flush=True)
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
    command=[sys.executable,'-m','laws_confirmation.l19_broadcast_withdrawal_run','--external-root',str(root),'--run']
    env=os.environ.copy(); env['L19_WITHDRAWAL_DETACHED_LOG']=str(log)
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
    return dict(passes=True,checked_blocks=8,checked_lives=16,fresh_branches=64,
        exact_alias_branches=16,full_dynamics_replayed_now=replay,input_hashes=len(manifest['input_sha256']),
        output_hashes=19 if complete else 0,label=summary['label'],primary=summary['primary'])


def run_experiment(root):
    u.preflight(root); manifest=prepared(root); run,out=root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID
    if 'L19_WITHDRAWAL_DETACHED_LOG' in os.environ:
        u.write_json(run/'LAUNCH.json',dict(pid=os.getpid(),launched_utc=utc_now(),
            log=os.environ['L19_WITHDRAWAL_DETACHED_LOG'],manifest_sha256=sha256_file(run/'MANIFEST.json')),root)
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
                print(f'D101 tissue {index}: two full independent replays and two aliases pass',flush=True)
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
    commands=('source_controls','freeze','benchmark','prepare','run','detach','audit')
    for name in commands: group.add_argument('--'+name.replace('_','-'),action='store_true')
    args=parser.parse_args(); root=external_root(args.external_root)
    selected=[name for name in commands if getattr(args,name)]; command=selected[0] if selected else default_command
    if (command in ('source_controls','freeze')) != (args.test_report is not None):
        parser.error('--test-report required only for source-controls/freeze')
    if args.replay and command!='audit': parser.error('--replay is audit-only')
    if command=='audit': print(json.dumps(audit(root,replay=args.replay),indent=2)); return
    if command in ('source_controls','freeze'): globals()[command](root,args.test_report)
    else: (run_experiment if command=='run' else globals()[command])(root)


if __name__=='__main__': main()
