"""D131 fit-once guide with split-isolated founders; external-only and detached long jobs."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

from . import l20_learned_guide as p
from . import l16_body_content_run as previous
from . import l15_repair_speed_run as u
from .io import atomic_json, environment_manifest, external_root, git_head, sha256_file, utc_now

WORKERS, RESERVE, ALLOWANCE = previous.WORKERS, previous.RESERVE, previous.ALLOWANCE
preflight = previous.preflight
DETACHED_ENV = 'L20_LEARNED_GUIDE_DETACHED_LOG'


def science_paths(root):
    run=root/'runs'/'l20_blind_alignment_v1_attempt1';out=root/'outputs'/'l20_blind_alignment_v1_attempt1'
    assert sha256_file(run/'COMPLETE.json')=='0cc4c95ed626357dbd192c3e57cba98582d2db49f1bd57914b5b65406cda120e'
    manifest,complete=u.read_json(run/'MANIFEST.json'),u.read_json(run/'COMPLETE.json')
    assert complete['status']=='COMPLETE' and u.read_json(run/'STATUS.json')==complete
    assert complete['manifest_sha256']==sha256_file(run/'MANIFEST.json')
    assert complete['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
    assert manifest['environment']==environment_manifest()
    inputs=manifest['input_sha256'];outputs=complete['output_sha256']
    assert len(inputs)==752 and len(outputs)==19
    assert inputs==u.hashes([Path(x) for x in inputs]) and outputs==u.hashes([Path(x) for x in outputs])
    assert {str(x) for x in out.iterdir()}==set(outputs)|{str(out/'output_hashes.sha256')}
    assert (out/'output_hashes.sha256').read_text()==u.hash_text(outputs)
    files=[Path(x) for x in (*inputs,*outputs)]
    files += [run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]+[out/'output_hashes.sha256']
    files += [p.WS/'reviews/L20_BLIND_ALIGNMENT_2026-09-15.md',*[p.WS/n for n in p.SCIENCE]]
    return sorted(set(files))


def source_expected():
    return dict(known_founder_acquisitions=2,known_pre_readers=2,known_source_writers=4,known_reader_paths=10,
        full_replay=True,max_abs=0.,new_futures=0,whole_renewal_replayed=False,qualification_pool=False)


def test_proof(report, root):
    report = u.require_beneath(report, root/'logs')
    assert not report.is_symlink() and report.name.startswith('d131_') and report.suffix == '.xml'
    tree = ET.parse(report).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 50 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    current = [c for c in cases if c.get('classname','').endswith('test_l20_learned_guide')]
    assert len(current) >= 50
    names = {c.get('name','').split('[',1)[0] for c in current}
    assert {'test_source_bridge_full_replay','test_full_disposable_life','test_full_training_life',
        'test_fit_packet_only','test_split_isolation','test_fresh_founders','test_shared_shuffle',
        'test_fresh_process_reader','test_no_source_state','test_births_and_noise','test_independent_dynamics',
        'test_independent_observer','test_observer_denominator','test_independent_summary',
        'test_raw_corruption','test_metadata_corruption','test_summary_corruption','test_external_roundtrip',
        'test_cpu_and_external_guards','test_reservation_guards','test_freeze_reservation_guard',
        'test_detachment_guard','test_provenance_closure','test_progress_counts','test_selector_all_offsets',
        'test_selector_packet_only','test_calibration_exact','test_pre_shuffle_control',
        'test_packet_transform_no_normalization','test_independent_selector','test_fresh_process_selector',
        'test_selector_ties','test_matched_gate','test_training_stage_order'} <= names
    offsets={c.get('name') for c in current if c.get('name','').startswith('test_selector_all_offsets[')}
    assert offsets=={f'test_selector_all_offsets[{i}]' for i in range(256)}
    duration = lambda name: max(float(c.get('time','0')) for c in current if c.get('name') == name)
    return dict(path=str(report), tests=len(cases), new_tests=len(current), failed=0, skipped=0,
        source_test_seconds=duration('test_source_bridge_full_replay'),
        training_life_seconds=duration('test_full_training_life'),
        block_test_seconds=p.CONFIG.lives*duration('test_full_disposable_life'))


def source_bridge(root, report):
    preflight(root); proof = test_proof(report, root)
    forecast = 4*proof['source_test_seconds']+60
    assert forecast <= 600, 'long bridge needs a separately detached stage'
    inputs = u.hashes(science_paths(root)+[report])
    directory = root/'outputs'/p.CONTROL_ID; directory.mkdir(); start = time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json', dict(input_sha256=inputs,test_proof=proof,
            environment=environment_manifest(),contract=contract(),projected_seconds=forecast),root)
        raw, meta = p.source_bridge(root); p.checker().nested(meta['replay'],source_expected())
        u.save_pair(directory,'bridge',raw,meta,root)
        u.write_json(directory/'summary.json',meta['replay'],root)
        assert inputs == u.hashes(science_paths(root)+[report]); preflight(root,False)
        complete = dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            output_sha256=u.hashes(list(directory.iterdir())))
        u.write_json(directory/'COMPLETE.json',complete,root)
        print(json.dumps(dict(status='SOURCE_COMPLETE',**meta['replay']),indent=2),flush=True)
    except Exception as error:
        u.failure(directory,error,root); raise


def source_artifacts(root, report):
    directory = root/'outputs'/p.CONTROL_ID
    names = {'INPUTS.json','bridge.npz','bridge.json','summary.json','COMPLETE.json'}
    assert {x.name for x in directory.iterdir()} == names
    inputs, complete = u.read_json(directory/'INPUTS.json'), u.read_json(directory/'COMPLETE.json')
    assert inputs['input_sha256'] == u.hashes(science_paths(root)+[report])
    assert inputs['test_proof'] == test_proof(report,root) and inputs['environment'] == environment_manifest()
    p.checker().nested(inputs['contract'],contract())
    assert complete['status'] == 'COMPLETE'
    assert complete['output_sha256'] == u.hashes([directory/n for n in names if n != 'COMPLETE.json'])
    meta = u.read_json(directory/'bridge.json')
    assert meta['known_outcomes'] is True and meta['new_futures'] == 0 and meta['index'] == 514217
    p.checker().nested(meta['replay'],source_expected())
    assert u.read_json(directory/'summary.json') == meta['replay']
    return [directory/n for n in sorted(names)]


def output_names():
    return tuple(f'block_{i}.{ext}' for i in p.TISSUES for ext in ('npz', 'json')) + (
        'summary.json', 'verification.json', 'input_hashes.sha256')


def contract():
    return p.contract() | dict(workers=WORKERS, cpu_affinity_max=list(range(WORKERS)),
        reserve_bytes=RESERVE, allowance_bytes=ALLOWANCE, detach_above_seconds=600,
        output_files=list(output_names()), output_hash_count=19,
        forecast='8*checked_block_seconds+2*hash_seconds+180',
        storage_forecast='8*raw_block_bytes+bridge_bytes+training_bytes+benchmark_bytes+32MiB',
        successor='none; report one fit-once guide comparison')


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root, report):
    preflight(root); proof = test_proof(report, root)
    for target in (freeze_path(root), timing_path(root), benchmark_dir(root), root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID, root/'outputs'/p.TRAIN_ID):
        if target.exists(): raise FileExistsError(target)
    inputs = u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    u.write_json(freeze_path(root), dict(frozen_utc=utc_now(), contract=contract(), input_sha256=inputs,
        environment=environment_manifest(), git_head=git_head(p.WS), test_proof=proof, training_futures_seen=0, main_futures_seen=0), root)
    print(f'D131 frozen: {len(inputs)} inputs, zero main futures', flush=True)


def frozen(root):
    saved = u.read_json(freeze_path(root)); report = Path(saved['test_proof']['path'])
    p.checker().nested(saved['contract'], contract())
    assert saved['main_futures_seen'] == saved['training_futures_seen'] == 0 and saved['environment'] == environment_manifest()
    assert saved['test_proof'] == test_proof(report, root)
    assert saved['input_sha256'] == u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    return saved


def train(root):
    preflight(root);saved=frozen(root)
    forecast=4*8*saved['test_proof']['training_life_seconds']+60
    assert forecast<=600,'long training requires a separately detached stage'
    assert not timing_path(root).exists() and not benchmark_dir(root).exists()
    for path in (root/'runs'/p.RUN_ID,root/'outputs'/p.RUN_ID):assert not path.exists()
    directory=root/'outputs'/p.TRAIN_ID;directory.mkdir();start=time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json',dict(core_freeze_sha256=sha256_file(freeze_path(root)),
            input_sha256=saved['input_sha256'],environment=environment_manifest(),contract=contract(),
            training_blocks=list(p.TRAINING),test_blocks=list(p.TISSUES),main_futures_seen=0,projected_seconds=forecast),root)
        blocks=[]
        for index in p.TRAINING:
            raw,meta=p.training_block(index)
            stored=u.save_pair(directory,f'block_{index}',raw,meta,root)
            assert p.checker().check_training_block(stored,u.read_json(directory/f'block_{index}.json'),p.CONFIG,False)
            blocks.append(raw)
        examples=np.stack([np.frombuffer(p.encode(b['written_fields'][life,r,0]),np.uint8)
            for b in blocks for life in range(4) for r in (0,1)])
        labels=np.tile(np.arange(2,dtype=np.int64),8)
        guide=p.fit_guide(examples,labels)
        error=p.checker().check_fit(examples,labels,guide)
        raw=dict(examples=examples,labels=labels,guide=guide,
            training_indices=np.repeat(np.asarray(p.TRAINING,dtype=np.int64),8),
            training_lives=np.tile(np.repeat(np.arange(4,dtype=np.int64),2),2))
        meta=dict(fit_rule=p.FIT_RULE,fit_count=1,records=16,records_per_family=8,
            guide_sha256=__import__('hashlib').sha256(p.guide_bytes(guide)).hexdigest(),
            fit_max_abs=error,training_blocks=list(p.TRAINING),test_blocks=list(p.TISSUES),
            supplied_family_groups=True,supplied_coordinate_frame=True,perfect_template_pixels_in_fit=False,
            test_outcome_access=False,main_futures_seen=0,guide_bytes=4096,carrier_bytes=2048,
            guide_is_public_host_prior=True,guide_inherited=False,training_parent_acquisitions=16,
            training_pre_readers=16,training_source_writers=16)
        u.save_pair(directory,'guide',raw,meta,root)
        assert frozen(root)==saved;preflight(root,False)
        u.write_json(directory/'COMPLETE.json',dict(status='COMPLETE',completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start,main_futures_seen=0,fit_count=1,
            output_sha256=u.hashes(list(directory.iterdir()))),root)
        training_artifacts(root)
        print(json.dumps(dict(status='GUIDE_FROZEN',guide_sha256=meta['guide_sha256'],
            training_records=16,fit_count=1,main_futures_seen=0),indent=2),flush=True)
    except Exception as error:
        u.failure(directory,error,root);raise


def training_artifacts(root):
    directory=root/'outputs'/p.TRAIN_ID
    names={'INPUTS.json','guide.npz','guide.json','COMPLETE.json'}|{f'block_{i}.{ext}' for i in p.TRAINING for ext in ('npz','json')}
    assert {x.name for x in directory.iterdir()}==names
    inputs,complete=u.read_json(directory/'INPUTS.json'),u.read_json(directory/'COMPLETE.json')
    saved=u.read_json(freeze_path(root))
    assert inputs['core_freeze_sha256']==sha256_file(freeze_path(root))
    assert inputs['input_sha256']==saved['input_sha256'] and inputs['environment']==environment_manifest()
    p.checker().nested(inputs['contract'],contract())
    assert inputs['training_blocks']==list(p.TRAINING) and inputs['test_blocks']==list(p.TISSUES)
    assert inputs['main_futures_seen']==complete['main_futures_seen']==0 and complete['fit_count']==1
    assert complete['status']=='COMPLETE'
    assert complete['output_sha256']==u.hashes([directory/n for n in names if n!='COMPLETE.json'])
    blocks=[]
    for index in p.TRAINING:
        raw=u.load_npz(directory/f'block_{index}.npz');meta=u.read_json(directory/f'block_{index}.json')
        assert meta['index']==index
        assert p.checker().check_training_block(raw,meta,p.CONFIG,False);blocks.append(raw)
    raw=u.load_npz(directory/'guide.npz');meta=u.read_json(directory/'guide.json')
    assert set(raw)=={'examples','labels','guide','training_indices','training_lives'}
    examples=np.stack([np.frombuffer(p.encode(b['written_fields'][life,r,0]),np.uint8)
        for b in blocks for life in range(4) for r in (0,1)])
    np.testing.assert_array_equal(raw['examples'],examples)
    np.testing.assert_array_equal(raw['labels'],np.tile(np.arange(2,dtype=np.int64),8))
    np.testing.assert_array_equal(raw['training_indices'],np.repeat(np.asarray(p.TRAINING,dtype=np.int64),8))
    np.testing.assert_array_equal(raw['training_lives'],np.tile(np.repeat(np.arange(4,dtype=np.int64),2),2))
    error=p.checker().check_fit(raw['examples'],raw['labels'],raw['guide'])
    expected=dict(fit_rule=p.FIT_RULE,fit_count=1,records=16,records_per_family=8,
        guide_sha256=__import__('hashlib').sha256(p.guide_bytes(raw['guide'])).hexdigest(),fit_max_abs=error,
        training_blocks=list(p.TRAINING),test_blocks=list(p.TISSUES),supplied_family_groups=True,
        supplied_coordinate_frame=True,perfect_template_pixels_in_fit=False,test_outcome_access=False,
        main_futures_seen=0,guide_bytes=4096,carrier_bytes=2048,guide_is_public_host_prior=True,guide_inherited=False,
        training_parent_acquisitions=16,training_pre_readers=16,training_source_writers=16)
    p.checker().nested(meta,expected)
    return [directory/n for n in sorted(names)]


def checked_block(root, directory, index):
    preflight(root,False); assert index in p.TISSUES or index == p.DISPOSABLE
    raw, meta = p.execute_block(index,root=root)
    saved = u.save_pair(directory,f'block_{index}',raw,meta,root)
    assert p.checker().check_block(saved,u.read_json(directory/f'block_{index}.json'),p.CONFIG,p.load_guide(root),replay=False)
    return dict(index=index,full_life_replays=4,exact_path_aliases=36,reader_paths=192,parent_acquisitions=8,
        pre_readers=8,source_writers=16,selector_decisions=144,primary_packets=48,
        max_abs=max(max(m['replay'][k] for k in ('dynamics_max_abs','founder_max_abs','pre_reader_max_abs','source_max_abs')) for m in meta['lives']),
        uncompressed_bytes=sum(a.nbytes for a in raw.values()))



def benchmark(root):
    preflight(root); saved = frozen(root); training_files=training_artifacts(root)
    assert 4*saved['test_proof']['block_test_seconds']+60 <= 600, 'long benchmark needs detached design'
    directory = benchmark_dir(root); directory.mkdir(); start = time.monotonic()
    try:
        block = checked_block(root, directory, p.DISPOSABLE)
        raw = u.load_npz(directory/f'block_{p.DISPOSABLE}.npz')
        assert p.checker().check_summary(p.summarize([raw]*8), [raw]*8, p.CONFIG)
        seconds = time.monotonic()-start
        hstart = time.monotonic(); frozen(root); hseconds = time.monotonic()-hstart
        paths = list(directory.iterdir()); size = sum(x.stat().st_size for x in paths)
        source_bytes = sum(x.stat().st_size for x in (root/'outputs'/p.CONTROL_ID).iterdir())
        forecast = 8*seconds+2*hseconds+180
        training_bytes=sum(x.stat().st_size for x in training_files)
        budget = 8*block['uncompressed_bytes']+source_bytes+training_bytes+size+32*1024**2
        assert budget <= ALLOWANCE; preflight(root)
        timing = dict(benchmark_utc=utc_now(), disposable=p.DISPOSABLE, qualification_pool=False,
            block=block, checked_block_seconds=seconds, hash_seconds=hseconds,
            projected_seconds=forecast, must_detach=forecast > 600, projected_total_bytes=budget,
            source_bytes=source_bytes, training_bytes=training_bytes, training_sha256=u.hashes(training_files), benchmark_bytes=size, artifact_sha256=u.hashes(paths),
            freeze_sha256=sha256_file(freeze_path(root)))
        u.write_json(timing_path(root), timing, root)
        print(json.dumps({k: timing[k] for k in ('checked_block_seconds', 'projected_seconds', 'must_detach', 'projected_total_bytes')}, indent=2), flush=True)
    except Exception as error:
        u.failure(directory, error, root); raise


def timing_checked(root):
    t = u.read_json(timing_path(root))
    assert t['freeze_sha256'] == sha256_file(freeze_path(root))
    assert t['training_sha256']==u.hashes(training_artifacts(root))
    assert t['disposable'] == p.DISPOSABLE and t['qualification_pool'] is False
    assert t['artifact_sha256'] == u.hashes(list(benchmark_dir(root).iterdir()))
    forecast = 8*t['checked_block_seconds']+2*t['hash_seconds']+180
    assert np.isfinite(forecast) and forecast > 0 and t['projected_seconds'] == forecast
    assert t['must_detach'] == (forecast > 600)
    assert t['projected_total_bytes'] == 8*t['block']['uncompressed_bytes']+t['source_bytes']+t['training_bytes']+t['benchmark_bytes']+32*1024**2
    assert 0 < t['projected_total_bytes'] <= ALLOWANCE
    return t


def main_inputs(root):
    saved = frozen(root); timing_checked(root)
    return u.hashes([Path(x) for x in saved['input_sha256']] + [freeze_path(root), timing_path(root), *training_artifacts(root), *benchmark_dir(root).iterdir()])


def prepare(root):
    preflight(root); inputs = main_inputs(root); timing = timing_checked(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('single-use identity already reserved')
    run.mkdir(); out.mkdir()
    try:
        u.write_json(run/'MANIFEST.json', dict(contract=contract(), input_sha256=inputs,
            environment=environment_manifest(), timing=timing, prepared_utc=utc_now(), git_head=git_head(p.WS)), root)
        with (out/'input_hashes.sha256').open('x') as handle: handle.write(u.hash_text(inputs))
        atomic_json(run/'STATUS.json', dict(status='PREPARED', run_id=p.RUN_ID, timing=timing), root)
        print(f'D131 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s', flush=True)
    except Exception as error:
        u.failure(run, error, root); raise


def prepared(root):
    manifest = u.read_json(root/'runs'/p.RUN_ID/'MANIFEST.json')
    p.checker().nested(manifest['contract'], contract())
    assert manifest['input_sha256'] == main_inputs(root)
    assert manifest['environment'] == environment_manifest() and manifest['timing'] == timing_checked(root)
    assert (root/'outputs'/p.RUN_ID/'input_hashes.sha256').read_text() == u.hash_text(manifest['input_sha256'])
    return manifest


def detached_guard(root, required):
    run = root/'runs'/p.RUN_ID
    if required or (run/'LAUNCH.json').exists():
        launch = u.read_json(run/'LAUNCH.json')
        assert launch['pid'] == os.getpid() == os.getsid(0)
        assert launch['log'] == str(root/'logs'/f'{p.RUN_ID}.log')
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd)) == launch['log'] for fd in (1, 2))
        assert launch['manifest_sha256'] == sha256_file(run/'MANIFEST.json')


def detach(root):
    preflight(root); prepared(root); run = root/'runs'/p.RUN_ID
    for name in ('EXECUTION.lock', 'COMPLETE.json', 'FAILED.json'):
        if (run/name).exists(): raise FileExistsError('execution already attempted')
    (run/'LAUNCH.lock').mkdir(); log = root/'logs'/f'{p.RUN_ID}.log'
    env = os.environ.copy(); env[DETACHED_ENV] = str(log)
    command = [sys.executable, '-m', 'laws_confirmation.l20_learned_guide_run', '--external-root', str(root), '--run']
    with log.open('xb') as handle:
        child = subprocess.Popen(command, cwd=p.WS, env=env, stdin=subprocess.DEVNULL,
            stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    print(json.dumps(dict(status='DETACHED', pid=child.pid, log=str(log), user_polls=True, automatic_polling=False)), flush=True)


def audit(root, complete=True, replay=False):
    preflight(root,False); manifest = prepared(root)
    out, run = root/'outputs'/p.RUN_ID, root/'runs'/p.RUN_ID
    assert {x.name for x in out.iterdir()} == set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    assert (run/'EXECUTION.lock').is_dir() and not (run/'FAILED.json').exists()
    if replay: assert manifest['timing']['projected_seconds'] <= 600, 'long replay needs detached design'
    p.api(); blocks = []
    for index in p.TISSUES:
        raw, meta = u.load_npz(out/f'block_{index}.npz'), u.read_json(out/f'block_{index}.json')
        assert type(meta['index']) is int and meta['index'] == index
        assert p.checker().check_block(raw,meta,p.CONFIG,p.load_guide(root),replay)
        blocks.append(raw)
    summary = u.read_json(out/'summary.json'); assert p.checker().check_summary(summary,blocks,p.CONFIG)
    v = u.read_json(out/'verification.json')
    assert set(v) == {'independent_life_replays','exact_path_aliases','rows','checked_utc'}
    assert v['independent_life_replays'] == 32 and v['exact_path_aliases'] == 288
    assert [r['index'] for r in v['rows']] == list(p.TISSUES)
    assert all(set(r)=={'index','full_life_replays','exact_path_aliases','reader_paths','parent_acquisitions',
        'pre_readers','source_writers','selector_decisions','primary_packets','max_abs','uncompressed_bytes'}
        and r['full_life_replays']==4 and r['exact_path_aliases']==36 and r['reader_paths']==192
        and r['parent_acquisitions']==8 and r['pre_readers']==8 and r['source_writers']==16
        and r['selector_decisions']==144 and r['primary_packets']==48 and 0<=r['max_abs']<=1e-10 for r in v['rows'])
    if complete:
        status = u.read_json(run/'COMPLETE.json')
        assert status['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == status
        actual = u.hashes([out/n for n in output_names()])
        assert status['output_sha256'] == actual and (out/'output_hashes.sha256').read_text() == u.hash_text(actual)
        assert status['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert status['output_bytes'] == sum(x.stat().st_size for x in out.iterdir()) <= manifest['timing']['projected_total_bytes']
    return dict(passes=True,checked_blocks=8,checked_lives=32,reader_paths=1536,parent_acquisitions=64,pre_readers=64,
        exact_path_aliases=288,new_source_writes=128,selector_decisions=1152,full_dynamics_replayed_now=replay,
        input_hashes=len(manifest['input_sha256']),output_hashes=19 if complete else 0,
        label=summary['label'],primary=summary['primary'],content_qualified=summary['content_qualified'],
        calibration_qualified=summary['calibration_qualified'],readout_qualified=summary['readout_qualified'])


def progress_message(row):
    return (f'D131 block{row["index"]}: {row["full_life_replays"]} full reader-life replays, '
            f'{row["source_writers"]} source writers, {row["reader_paths"]} readers, '
            f'{row["selector_decisions"]} selections and {row["exact_path_aliases"]} path aliases pass')


def run_experiment(root):
    preflight(root); manifest = prepared(root)
    run, out = root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID
    if DETACHED_ENV in os.environ:
        u.write_json(run/'LAUNCH.json', dict(pid=os.getpid(), launched_utc=utc_now(),
            log=os.environ[DETACHED_ENV], manifest_sha256=sha256_file(run/'MANIFEST.json')), root)
    detached_guard(root, manifest['timing']['must_detach'])
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checked = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = {pool.submit(checked_block, root, out, index): index for index in p.TISSUES}
            for job in as_completed(jobs):
                index = jobs[job]; checked[index] = job.result(); preflight(root, False)
                atomic_json(run/'STATUS.json', dict(status='RUNNING', run_id=p.RUN_ID,
                    checked_blocks=len(checked), updated_utc=utc_now()), root)
                print(progress_message(checked[index]), flush=True)
        blocks = [u.load_npz(out/f'block_{i}.npz') for i in p.TISSUES]
        u.write_json(out/'summary.json', p.summarize(blocks), root)
        u.write_json(out/'verification.json', dict(independent_life_replays=32, exact_path_aliases=288,
            rows=[checked[i] for i in p.TISSUES], checked_utc=utc_now()), root)
        saved_audit = audit(root, complete=False)
        actual = u.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as handle: handle.write(u.hash_text(actual))
        size = sum(x.stat().st_size for x in out.iterdir())
        assert size <= manifest['timing']['projected_total_bytes'] <= ALLOWANCE
        preflight(root, False)
        status = dict(status='COMPLETE', run_id=p.RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start, output_bytes=size, output_sha256=actual,
            manifest_sha256=sha256_file(run/'MANIFEST.json'), hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            saved_audit=saved_audit)
        u.write_json(run/'COMPLETE.json', status, root); atomic_json(run/'STATUS.json', status, root)
        print(json.dumps({k: status[k] for k in ('status', 'elapsed_seconds', 'output_bytes', 'saved_audit')}, indent=2), flush=True)
    except Exception as error:
        u.failure(run, error, root)
        atomic_json(run/'STATUS.json', dict(status='FAILED', error=str(error), automatic_retry=False), root)
        raise


def main(default_command=None):
    if sys.flags.optimize: raise RuntimeError('assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path, required=True)
    parser.add_argument('--test-report', type=Path); parser.add_argument('--replay', action='store_true')
    group = parser.add_mutually_exclusive_group(required=default_command is None)
    commands = ('source_bridge', 'freeze', 'train', 'benchmark', 'prepare', 'run', 'detach', 'audit')
    for name in commands: group.add_argument('--'+name.replace('_', '-'), action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    chosen = [name for name in commands if getattr(args, name)]
    command = chosen[0] if chosen else default_command
    if (command in ('source_bridge', 'freeze')) != (args.test_report is not None):
        parser.error('--test-report required only for source-bridge/freeze')
    if args.replay and command != 'audit': parser.error('--replay is audit-only')
    if command == 'audit': print(json.dumps(audit(root, replay=args.replay), indent=2)); return
    if command in ('source_bridge', 'freeze'): globals()[command](root, args.test_report)
    else: (run_experiment if command == 'run' else globals()[command])(root)


if __name__ == '__main__': main()
