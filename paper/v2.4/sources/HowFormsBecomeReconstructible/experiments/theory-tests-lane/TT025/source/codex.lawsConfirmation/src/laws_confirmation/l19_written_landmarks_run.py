"""D106 staged write-once qualification and, only if qualified, main assay."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from . import l19_written_landmarks as p
from . import l15_repair_speed_run as io
from . import l19_internal_repair_run as previous
from .io import atomic_json,environment_manifest,external_root,git_head,require_beneath,sha256_file,utc_now

PHASES = ('qualification','main')
PRIOR_COMPLETE = '8d1c5d4f2bdc34332baf90695d393f541297b74c4bfd6d3f5262bef11c1cb9b4'


def run_id(phase):
    if phase not in PHASES:
        raise ValueError('undeclared phase')
    return p.QUAL_ID if phase=='qualification' else p.RUN_ID


def tissues(phase):
    run_id(phase)
    return p.QUAL_TISSUES if phase=='qualification' else p.TISSUES


def output_names(phase):
    return tuple(f'block_{i}.{ext}' for i in tissues(phase) for ext in ('npz','json'))+(
        'summary.json','verification.json','input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=4,reserve_bytes=io.RESERVE,allowance_bytes=io.ALLOWANCE,
        documentation_exception=previous.contract()['documentation_exception'],
        detach_above_seconds=600,phase_outputs={phase:list(output_names(phase)) for phase in PHASES},
        forecast='8*phase_checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*(main_uncompressed+qualification_uncompressed)+benchmark_bytes+32MiB',
        main_requires_qualified=True,prior_complete_sha256=PRIOR_COMPLETE)


def prior_artifacts(root):
    manifest=previous.prepared(root)
    out,run = root/'outputs'/p.base.RUN_ID,root/'runs'/p.base.RUN_ID
    assert sha256_file(run/'COMPLETE.json')==PRIOR_COMPLETE
    assert sha256_file(out/'summary.json')=='ba4ccac15c6df77f68e74c4e7e5412eba3acf6bc3728e56507b528a452fc299e'
    complete=io.read_json(run/'COMPLETE.json')
    assert complete['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==complete
    names=set(previous.output_names())|{'output_hashes.sha256'}
    assert {x.name for x in out.iterdir()}==names
    assert complete['output_sha256']==io.hashes([out/n for n in previous.output_names()])
    assert complete['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
    assert complete['manifest_sha256']==sha256_file(run/'MANIFEST.json')
    return [Path(x) for x in manifest['input_sha256']]+[out/n for n in names]+[
        run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]+[p.WS/'reviews/L19_INTERNAL_REPAIR_2026-09-12.md']


def science_paths(root):
    return sorted(set(prior_artifacts(root)+[p.WS/x for x in p.SCIENCE]))


def test_proof(path,root):
    path = require_beneath(path,root/'logs')
    if path.is_symlink() or not path.name.startswith('d106_') or path.suffix!='.xml':
        raise ValueError('retained external D106 XML proof required')
    report = ET.parse(path).getroot(); cases = report.findall('.//testcase')
    assert len(cases)>=100 and not any(report.findall('.//'+x) for x in ('failure','error','skipped'))
    assert len(cases)==len({(c.get('classname'),c.get('name')) for c in cases})
    names = {c.get('name','') for c in cases}
    base_names={name.split('[',1)[0] for name in names}
    assert {'test_d106_fresh_process_import','test_d105_saved_baseline_anchor','test_d106_targets',
            'test_d106_target_exclusion','test_d106_hand_built_pooling','test_d106_qualification_gates',
            'test_d106_failed_qualification_blocks_main','test_d106_common_untrained_recipient',
            'test_d106_wrong_content_identity','test_d106_native_writing_not_injection'}<=base_names
    assert any(c.get('classname','').endswith('test_l19_written_landmarks') for c in cases)
    assert sum(n.startswith('test_d106_full_block_replay[') for n in names)==2
    return dict(path=str(path),tests=len(cases),failed=0,skipped=0)


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root,report):
    io.preflight(root); proof = test_proof(report,root)
    assert previous.audit(root)['passes'], 'prior saved audit failed'
    targets = [freeze_path(root),timing_path(root),benchmark_dir(root)]
    targets += [root/folder/run_id(phase) for folder in ('runs','outputs') for phase in PHASES]
    if any(x.exists() for x in targets):
        raise FileExistsError('D106 single-use identity already reserved')
    inputs = io.hashes(science_paths(root)+[report])
    io.write_json(freeze_path(root),dict(contract=contract(),input_sha256=inputs,test_proof=proof,
        environment=environment_manifest(),git_head_at_freeze=git_head(p.WS),frozen_utc=utc_now(),
        qualification_futures_seen=0,main_futures_seen=0),root)
    print(f'D106 frozen: {len(inputs)} inputs; no qualification or main future yet',flush=True)


def frozen(root):
    record = io.read_json(freeze_path(root)); report = Path(record['test_proof']['path'])
    assert record['contract']==json.loads(json.dumps(contract()))
    assert record['qualification_futures_seen']==record['main_futures_seen']==0
    assert record['environment']==environment_manifest() and record['test_proof']==test_proof(report,root)
    assert record['input_sha256']==io.hashes(science_paths(root)+[report])
    return record


def checked_block(root,directory,index,phase,prefix=None):
    io.preflight(root,starting=False)
    qual = phase=='qualification'; run_id(phase)
    raw,meta = p.execute_block(index,qual)
    name = prefix or f'block_{index}'
    saved = io.save_pair(directory,name,raw,meta,root)
    assert p.checker().check_block(saved,io.read_json(directory/(name+'.json')),p.CONFIG,replay=False)
    return dict(index=index,qualification=qual,lives=2,independent_life_replays=2,
        readout_futures=8 if qual else 24,teaching_histories=4,exact_alias_branches=2,
        max_abs=max(m['replay']['max_abs'] for m in meta['lives']),
        uncompressed_bytes=sum(x.nbytes for x in raw.values()))


def benchmark(root):
    io.preflight(root); frozen(root)
    assert 8*previous.timing_checked(root)['checked_block_seconds']+60<=600, 'benchmark itself needs detached design'
    directory = benchmark_dir(root); directory.mkdir()
    try:
        timings = {}
        for phase in PHASES:
            start = time.monotonic()
            block = checked_block(root,directory,p.DISPOSABLE,phase,prefix=phase)
            raw = io.load_npz(directory/(phase+'.npz'))
            summary = p.summarize([raw]*8,phase=='qualification')
            assert p.checker().check_summary(summary,[raw]*8,phase=='qualification',p.CONFIG)
            timings[phase] = dict(checked_block_seconds=time.monotonic()-start,block=block)
            print(f'D106 disposable {phase} block: replay/aliases/save/summary pass',flush=True)
        start = time.monotonic(); frozen(root); hashing = time.monotonic()-start
        for value in timings.values():
            value['projected_seconds'] = 8*value['checked_block_seconds']+2*hashing+180
            value['must_detach'] = value['projected_seconds']>600
        artifacts = list(directory.iterdir()); bench_bytes = sum(x.stat().st_size for x in artifacts)
        size = 8*sum(t['block']['uncompressed_bytes'] for t in timings.values())+bench_bytes+32*1024**2
        assert size<=io.ALLOWANCE, 'no automatic budget change'
        io.preflight(root)
        result = dict(benchmark_utc=utc_now(),disposable=p.DISPOSABLE,cohort_pool=False,
            phases=timings,hash_seconds=hashing,benchmark_bytes=bench_bytes,projected_total_bytes=size,
            artifact_sha256=io.hashes(artifacts),freeze_sha256=sha256_file(freeze_path(root)))
        io.write_json(timing_path(root),result,root)
        print(json.dumps(result,indent=2),flush=True)
    except Exception as error:
        io.failure(directory,error,root); raise


def timing_checked(root):
    result = io.read_json(timing_path(root)); phases = result['phases']
    assert result['freeze_sha256']==sha256_file(freeze_path(root)) and set(phases)==set(PHASES)
    assert result['disposable']==p.DISPOSABLE and result['cohort_pool'] is False
    assert result['artifact_sha256']==io.hashes(list(benchmark_dir(root).iterdir()))
    for phase in PHASES:
        row = phases[phase]
        assert row['block']['qualification']==(phase=='qualification')
        assert row['projected_seconds']==8*row['checked_block_seconds']+2*result['hash_seconds']+180
        assert row['must_detach']==(row['projected_seconds']>600)
    assert result['projected_total_bytes']==(8*sum(v['block']['uncompressed_bytes'] for v in phases.values())+
        result['benchmark_bytes']+32*1024**2)
    assert 0<result['projected_total_bytes']<=io.ALLOWANCE
    return result


def require_qualified(summary):
    if summary.get('qualification') is not True or summary.get('qualified') is not True:
        raise RuntimeError('qualification failed: main remains unlaunched; no automatic redesign/retry')
    return True


def qualification_artifacts(root):
    assert audit(root,'qualification')['passes']
    out,run = root/'outputs'/p.QUAL_ID,root/'runs'/p.QUAL_ID
    require_qualified(io.read_json(out/'summary.json'))
    return list(out.iterdir())+[run/'MANIFEST.json',run/'COMPLETE.json',run/'STATUS.json']


def input_hashes(root,phase):
    run_id(phase); record = frozen(root); timing_checked(root)
    paths = [Path(x) for x in record['input_sha256']]+[freeze_path(root),timing_path(root),*benchmark_dir(root).iterdir()]
    if phase=='main':
        paths.extend(qualification_artifacts(root))
    return io.hashes(sorted(set(paths)))


def prepare(root,phase):
    io.preflight(root); inputs = input_hashes(root,phase); timing = timing_checked(root)
    name = run_id(phase); run,out = root/'runs'/name,root/'outputs'/name
    if run.exists() or out.exists():
        raise FileExistsError('phase identity already reserved')
    run.mkdir(); out.mkdir()
    try:
        io.write_json(run/'MANIFEST.json',dict(contract=contract(),phase=phase,input_sha256=inputs,
            environment=environment_manifest(),timing=timing,prepared_utc=utc_now()),root)
        with (out/'input_hashes.sha256').open('x') as handle:
            handle.write(io.hash_text(inputs))
        atomic_json(run/'STATUS.json',dict(status='PREPARED',phase=phase,run_id=name,
            forecast=timing['phases'][phase]),root)
        print(f'D106 {phase} prepared: {len(inputs)} inputs',flush=True)
    except Exception as error:
        io.failure(run,error,root); raise


def prepared(root,phase):
    run,out = root/'runs'/run_id(phase),root/'outputs'/run_id(phase)
    manifest = io.read_json(run/'MANIFEST.json')
    assert manifest['contract']==json.loads(json.dumps(contract())) and manifest['phase']==phase
    assert manifest['input_sha256']==input_hashes(root,phase)
    assert manifest['environment']==environment_manifest() and manifest['timing']==timing_checked(root)
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(manifest['input_sha256'])
    return manifest


def detached_guard(root,phase,required):
    run = root/'runs'/run_id(phase)
    if required or (run/'LAUNCH.json').exists():
        launch = io.read_json(run/'LAUNCH.json')
        assert launch['phase']==phase and launch['pid']==os.getpid()==os.getsid(0)
        assert os.readlink('/proc/self/fd/0')=='/dev/null'
        assert all(os.readlink(f'/proc/self/fd/{i}')==launch['log'] for i in (1,2))
        assert launch['manifest_sha256']==sha256_file(run/'MANIFEST.json')


def detach(root,phase):
    io.preflight(root); prepared(root,phase); name = run_id(phase); run = root/'runs'/name
    if any((run/x).exists() for x in ('EXECUTION.lock','COMPLETE.json','FAILED.json')):
        raise FileExistsError('execution already attempted')
    (run/'LAUNCH.lock').mkdir(); log = root/'logs'/f'{name}.log'
    env = os.environ.copy(); env['D106_DETACHED_LOG'] = str(log)
    command = [sys.executable,'-m','laws_confirmation.l19_written_landmarks_run',
        '--external-root',str(root),'--phase',phase,'--run']
    with log.open('xb') as handle:
        child = subprocess.Popen(command,cwd=p.WS,env=env,stdin=subprocess.DEVNULL,
            stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',phase=phase,pid=child.pid,log=str(log),
        user_polls=True,automatic_polling=False)),flush=True)


def audit(root,phase,complete=True,replay=False):
    io.preflight(root,starting=False); manifest = prepared(root,phase)
    if replay:
        assert manifest['timing']['phases'][phase]['projected_seconds']<=600, 'long replay must be detached separately'
    name = run_id(phase); out,run = root/'outputs'/name,root/'runs'/name
    expected = set(output_names(phase)) | ({'output_hashes.sha256'} if complete else set())
    assert {x.name for x in out.iterdir()}==expected
    assert (run/'EXECUTION.lock').is_dir() and not (run/'FAILED.json').exists()
    p.base.api(); blocks = []
    for index in tissues(phase):
        raw,meta = io.load_npz(out/f'block_{index}.npz'),io.read_json(out/f'block_{index}.json')
        assert type(meta['index']) is int and meta['index']==index and meta['qualification']==(phase=='qualification')
        assert p.checker().check_block(raw,meta,p.CONFIG,replay)
        blocks.append(raw)
    summary = io.read_json(out/'summary.json')
    assert p.checker().check_summary(summary,blocks,phase=='qualification',p.CONFIG)
    proof = io.read_json(out/'verification.json')
    assert proof['phase']==phase and proof['checked_blocks']==8 and proof['independent_life_replays']==16
    assert proof['exact_alias_branches']==16 and [r['index'] for r in proof['rows']]==list(tissues(phase))
    assert all(r['independent_life_replays']==2 and r['exact_alias_branches']==2 and 0<=r['max_abs']<=1e-10 for r in proof['rows'])
    if complete:
        status = io.read_json(run/'COMPLETE.json'); assert status['status']=='COMPLETE' and status['phase']==phase
        assert io.read_json(run/'STATUS.json')==status
        actual = io.hashes([out/n for n in output_names(phase)])
        assert status['output_sha256']==actual and (out/'output_hashes.sha256').read_text()==io.hash_text(actual)
        assert status['manifest_sha256']==sha256_file(run/'MANIFEST.json')
        assert status['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
        assert status['output_bytes']==sum(x.stat().st_size for x in out.iterdir())
        assert status['output_bytes']<=manifest['timing']['projected_total_bytes']
        assert status['qualified']==(summary['qualified'] if phase=='qualification' else None)
    return dict(passes=True,phase=phase,checked_blocks=8,independent_lives=16,
        full_dynamics_replayed_now=replay,exact_alias_branches=16,input_hashes=len(manifest['input_sha256']),
        output_hashes=19 if complete else 0,qualified=summary.get('qualified'),
        label=summary['label'],primary=summary['primary'])


def run_experiment(root,phase):
    io.preflight(root); manifest = prepared(root,phase); name = run_id(phase)
    run,out = root/'runs'/name,root/'outputs'/name
    if 'D106_DETACHED_LOG' in os.environ:
        io.write_json(run/'LAUNCH.json',dict(phase=phase,pid=os.getpid(),launched_utc=utc_now(),
            log=os.environ['D106_DETACHED_LOG'],manifest_sha256=sha256_file(run/'MANIFEST.json')),root)
    detached_guard(root,phase,manifest['timing']['phases'][phase]['must_detach'])
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checks = {}
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending = {pool.submit(checked_block,root,out,index,phase):index for index in tissues(phase)}
            for future in as_completed(pending):
                index = pending[future]; checks[index] = future.result(); io.preflight(root,starting=False)
                atomic_json(run/'STATUS.json',dict(status='RUNNING',run_id=name,phase=phase,
                    checked_blocks=len(checks),updated_utc=utc_now()),root)
                print(f'D106 {phase} tissue {index}: full independent replay and common-body alias checks pass',flush=True)
        blocks = [io.load_npz(out/f'block_{i}.npz') for i in tissues(phase)]
        summary = p.summarize(blocks,phase=='qualification')
        io.write_json(out/'summary.json',summary,root)
        io.write_json(out/'verification.json',dict(phase=phase,checked_blocks=8,independent_life_replays=16,
            exact_alias_branches=16,rows=[checks[i] for i in tissues(phase)],checked_utc=utc_now()),root)
        result = audit(root,phase,complete=False)
        current = io.hashes([out/n for n in output_names(phase)])
        with (out/'output_hashes.sha256').open('x') as handle:
            handle.write(io.hash_text(current))
        size = sum(x.stat().st_size for x in out.iterdir())
        assert size<=manifest['timing']['projected_total_bytes']<=io.ALLOWANCE
        io.preflight(root,starting=False)
        status = dict(status='COMPLETE',phase=phase,run_id=name,completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start,qualified=summary.get('qualified'),output_bytes=size,
            output_sha256=current,manifest_sha256=sha256_file(run/'MANIFEST.json'),
            hash_file_sha256=sha256_file(out/'output_hashes.sha256'),saved_audit=result)
        io.write_json(run/'COMPLETE.json',status,root); atomic_json(run/'STATUS.json',status,root)
        print(json.dumps({k:status[k] for k in ('status','phase','qualified','elapsed_seconds','output_bytes','saved_audit')},indent=2),flush=True)
        if phase=='main': print(json.dumps(summary['primary'],indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,root)
        atomic_json(run/'STATUS.json',dict(status='FAILED',phase=phase,run_id=name,error=str(error),automatic_retry=False),root)
        raise


def main(default_command=None):
    if sys.flags.optimize:
        raise RuntimeError('audit assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root',type=Path,required=True)
    parser.add_argument('--phase',choices=PHASES)
    parser.add_argument('--test-report',type=Path)
    parser.add_argument('--replay',action='store_true')
    group = parser.add_mutually_exclusive_group(required=default_command is None)
    for name in ('freeze','benchmark','prepare','run','detach','audit'):
        group.add_argument('--'+name,action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    command = next((n for n in ('freeze','benchmark','prepare','run','detach','audit') if getattr(args,n)),default_command)
    if (command=='freeze')!=(args.test_report is not None):
        parser.error('--test-report is required only for freeze')
    if (command in ('prepare','run','detach','audit'))!=(args.phase is not None):
        parser.error('--phase required only for prepare/run/detach/audit')
    if args.replay and command!='audit': parser.error('--replay is audit-only')
    if command=='freeze': freeze(root,args.test_report)
    elif command=='benchmark': benchmark(root)
    elif command=='audit': print(json.dumps(audit(root,args.phase,replay=args.replay),indent=2))
    else: (run_experiment if command=='run' else globals()[command])(root,args.phase)


if __name__=='__main__': main()
