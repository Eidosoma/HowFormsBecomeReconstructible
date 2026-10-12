"""D127 external-only source theta-feedback comparison; long runs detach unpolled."""
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

from . import l20_source_translation as p
from . import l16_body_content_run as previous
from . import l20_source_address_run as prior_run
from . import l15_repair_speed_run as u
from .io import atomic_json, environment_manifest, external_root, git_head, sha256_file, utc_now

WORKERS, RESERVE, ALLOWANCE = previous.WORKERS, previous.RESERVE, previous.ALLOWANCE
preflight = previous.preflight
DETACHED_ENV = 'L20_SOURCE_TRANSLATION_DETACHED_LOG'


def science_paths(root):
    # Validate the already-audited, hash-pinned D126 transitive closure once.
    # No recursive re-execution of every ancestor's preparation validator.
    directory = root/'runs'/prior_run.p.RUN_ID
    out = root/'outputs'/prior_run.p.RUN_ID
    assert sha256_file(directory/'COMPLETE.json') == 'd150d898ca86a2eefd769c502446ea493ff8c17ad82b03eb9f211503d7671267'
    manifest, complete = u.read_json(directory/'MANIFEST.json'), u.read_json(directory/'COMPLETE.json')
    p.checker().nested(manifest['contract'],prior_run.contract())
    assert not (directory/'FAILED.json').exists()
    assert complete['status'] == 'COMPLETE' and u.read_json(directory/'STATUS.json') == complete
    files = [Path(x) for x in manifest['input_sha256']]
    outputs = [Path(x) for x in complete['output_sha256']]
    assert u.hashes(files) == manifest['input_sha256'] and u.hashes(outputs) == complete['output_sha256']
    assert sha256_file(directory/'MANIFEST.json') == complete['manifest_sha256']
    assert sha256_file(out/'output_hashes.sha256') == complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text() == u.hash_text(complete['output_sha256'])
    assert {x.name for x in out.iterdir()} == set(prior_run.output_names()) | {'output_hashes.sha256'}
    files += outputs+[directory/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]
    files += [out/'output_hashes.sha256', p.WS/'reviews/L20_SOURCE_ADDRESS_2026-09-15.md']
    files += [p.WS/n for n in p.SCIENCE]
    return sorted(set(files))


def source_path(): return p.source_paths(p.DISPOSABLE)[0]


def source_expected():
    return dict(known_reader_paths=6, full_reader_replay=True, max_abs=0.,
        known_source_writer_paths=6, full_source_write_replay=True, source_max_abs=0.,
        force_probe_steps=6000, force_metric_max_abs=0.,
        new_source_writer_paths=0, whole_renewal_replayed=False, qualification_pool=False)


def test_proof(report, root):
    report = u.require_beneath(report, root/'logs')
    assert not report.is_symlink() and report.name.startswith('d127_') and report.suffix == '.xml'
    tree = ET.parse(report).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 50 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    current = [c for c in cases if c.get('classname','').endswith('test_l20_source_translation')]
    assert len(current) >= 50
    names = {c.get('name','').split('[',1)[0] for c in current}
    assert {'test_source_bridge_full_replay','test_full_disposable_life','test_exact_source_address',
        'test_shared_shuffle','test_fixed_writer','test_writer_no_other_state','test_source_writer_order',
        'test_writer_floor_and_permutation','test_degenerate_source_fails','test_projection_independent_of_production',
        'test_fresh_process_reader','test_no_source_state','test_births_and_noise',
        'test_independent_dynamics','test_independent_observer','test_observer_denominator',
        'test_independent_summary','test_gate_failure_not_absence','test_raw_corruption',
        'test_metadata_corruption','test_summary_corruption','test_external_roundtrip',
        'test_cpu_and_external_guards','test_reservation_guards','test_freeze_reservation_guard',
        'test_detachment_guard','test_provenance_closure','test_source_feedback_switch',
        'test_source_input_immutability','test_progress_counts','test_latent_theta_not_transmitted',
        'test_source_pairing','test_source_noise_is_new','test_feedback_bridge_equivalence',
        'test_source_independent_dynamics','test_source_bad_inputs','test_source_writer_kept_on',
        'test_source_address_multiset','test_source_address_shared','test_source_sham_exact',
        'test_force_probe_same_noise','test_force_input_strength','test_force_realized_clipping',
        'test_force_summary_independent','test_force_summary_corruption','test_force_does_not_change_path',
        'test_translation_all_offsets_geometry','test_translation_rng_is_target_blind',
        'test_translation_rejects_scattering_and_identity','test_translation_checker_independent',
        'test_symmetric_content_is_not_excluded','test_source_shift_corruption'} <= names
    duration = lambda name: max(float(c.get('time','0')) for c in current if c.get('name') == name)
    return dict(path=str(report), tests=len(cases), new_tests=len(current), failed=0, skipped=0,
        source_test_seconds=duration('test_source_bridge_full_replay'),
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
    assert meta['known_outcomes'] is True and meta['new_source_writer_paths'] == 0 and meta['index'] == 514217
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
        storage_forecast='8*raw_block_bytes+bridge_bytes+benchmark_bytes+32MiB',
        successor='none; report one frozen geometry-preserving source translation comparison and force audit')


def freeze_path(root): return root/'tmp'/f'{p.RUN_ID}_freeze.json'
def timing_path(root): return root/'tmp'/f'{p.RUN_ID}_benchmark.json'
def benchmark_dir(root): return root/'tmp'/f'{p.RUN_ID}_benchmark'


def freeze(root, report):
    preflight(root); proof = test_proof(report, root)
    for target in (freeze_path(root), timing_path(root), benchmark_dir(root), root/'runs'/p.RUN_ID, root/'outputs'/p.RUN_ID):
        if target.exists(): raise FileExistsError(target)
    inputs = u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    u.write_json(freeze_path(root), dict(frozen_utc=utc_now(), contract=contract(), input_sha256=inputs,
        environment=environment_manifest(), git_head=git_head(p.WS), test_proof=proof, main_futures_seen=0), root)
    print(f'D127 frozen: {len(inputs)} inputs, zero main futures', flush=True)


def frozen(root):
    saved = u.read_json(freeze_path(root)); report = Path(saved['test_proof']['path'])
    p.checker().nested(saved['contract'], contract())
    assert saved['main_futures_seen'] == 0 and saved['environment'] == environment_manifest()
    assert saved['test_proof'] == test_proof(report, root)
    assert saved['input_sha256'] == u.hashes(science_paths(root)+[report]+source_artifacts(root, report))
    return saved


def checked_block(root, directory, index):
    preflight(root,False); assert index in p.TISSUES or index == p.DISPOSABLE
    raw, meta = p.execute_block(index,root=root)
    saved = u.save_pair(directory,f'block_{index}',raw,meta,root)
    assert p.checker().check_block(saved,u.read_json(directory/f'block_{index}.json'),p.CONFIG,replay=False,root=root)
    return dict(index=index,full_life_replays=4,exact_path_aliases=156,reader_paths=336,source_pairs=24,source_paths=72,
        force_max_abs=max(m['replay']['force_metric_max_abs'] for m in meta['lives']),force_probe_steps=72000,
        source_max_abs=max(m['replay']['source_dynamics_max_abs'] for m in meta['lives']),
        max_abs=max(m['replay']['dynamics_max_abs'] for m in meta['lives']),
        uncompressed_bytes=sum(a.nbytes for a in raw.values()))


def benchmark(root):
    preflight(root); saved = frozen(root)
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
        budget = 8*block['uncompressed_bytes']+source_bytes+size+32*1024**2
        assert budget <= ALLOWANCE; preflight(root)
        timing = dict(benchmark_utc=utc_now(), disposable=p.DISPOSABLE, qualification_pool=False,
            block=block, checked_block_seconds=seconds, hash_seconds=hseconds,
            projected_seconds=forecast, must_detach=forecast > 600, projected_total_bytes=budget,
            source_bytes=source_bytes, benchmark_bytes=size, artifact_sha256=u.hashes(paths),
            freeze_sha256=sha256_file(freeze_path(root)))
        u.write_json(timing_path(root), timing, root)
        print(json.dumps({k: timing[k] for k in ('checked_block_seconds', 'projected_seconds', 'must_detach', 'projected_total_bytes')}, indent=2), flush=True)
    except Exception as error:
        u.failure(directory, error, root); raise


def timing_checked(root):
    t = u.read_json(timing_path(root))
    assert t['freeze_sha256'] == sha256_file(freeze_path(root))
    assert t['disposable'] == p.DISPOSABLE and t['qualification_pool'] is False
    assert t['artifact_sha256'] == u.hashes(list(benchmark_dir(root).iterdir()))
    forecast = 8*t['checked_block_seconds']+2*t['hash_seconds']+180
    assert np.isfinite(forecast) and forecast > 0 and t['projected_seconds'] == forecast
    assert t['must_detach'] == (forecast > 600)
    assert t['projected_total_bytes'] == 8*t['block']['uncompressed_bytes']+t['source_bytes']+t['benchmark_bytes']+32*1024**2
    assert 0 < t['projected_total_bytes'] <= ALLOWANCE
    return t


def main_inputs(root):
    saved = frozen(root); timing_checked(root)
    return u.hashes([Path(x) for x in saved['input_sha256']] + [freeze_path(root), timing_path(root), *benchmark_dir(root).iterdir()])


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
        print(f'D127 prepared: {len(inputs)} inputs, forecast {timing["projected_seconds"]:.1f}s', flush=True)
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
    command = [sys.executable, '-m', 'laws_confirmation.l20_source_translation_run', '--external-root', str(root), '--run']
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
        assert p.checker().check_block(raw,meta,p.CONFIG,replay,root)
        blocks.append(raw)
    summary = u.read_json(out/'summary.json'); assert p.checker().check_summary(summary,blocks,p.CONFIG)
    v = u.read_json(out/'verification.json')
    assert set(v) == {'independent_life_replays','independent_source_writer_paths','exact_path_aliases','rows','checked_utc'}
    assert v['independent_life_replays'] == 32 and v['independent_source_writer_paths'] == 576 and v['exact_path_aliases'] == 1248
    assert [r['index'] for r in v['rows']] == list(p.TISSUES)
    assert all(set(r) == {'index','full_life_replays','exact_path_aliases','reader_paths','source_pairs','source_paths','source_max_abs','max_abs','uncompressed_bytes','force_max_abs','force_probe_steps'}
        and r['full_life_replays'] == 4 and r['exact_path_aliases'] == 156 and r['reader_paths'] == 336
        and r['source_pairs'] == 24 and r['source_paths'] == 72
        and r['force_probe_steps'] == 72000 and 0 <= r['force_max_abs'] <= 1e-12 and 0 <= r['source_max_abs'] <= r['max_abs'] <= 1e-10 for r in v['rows'])
    if complete:
        status = u.read_json(run/'COMPLETE.json')
        assert status['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == status
        actual = u.hashes([out/n for n in output_names()])
        assert status['output_sha256'] == actual and (out/'output_hashes.sha256').read_text() == u.hash_text(actual)
        assert status['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert status['output_bytes'] == sum(x.stat().st_size for x in out.iterdir()) <= manifest['timing']['projected_total_bytes']
    return dict(passes=True,checked_blocks=8,checked_lives=32,reader_paths=2688,source_pairs=192,
        exact_path_aliases=1248,new_source_writer_paths=576,force_probe_steps=576000,full_dynamics_replayed_now=replay,
        input_hashes=len(manifest['input_sha256']),output_hashes=19 if complete else 0,
        label=summary['label'],primary=summary['primary'],aligned_readable=summary['aligned_readable'],
        translated_readable=summary['translated_readable'],no_feedback_readable=summary['no_feedback_readable'],readout_qualified=summary['readout_qualified'])


def progress_message(row):
    return (f'D127 block{row["index"]}: {row["full_life_replays"]} full reader-life replays, '
            f'{row["source_paths"]} source writers, {row["reader_paths"]} reader paths and {row["exact_path_aliases"]} path aliases pass')


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
        u.write_json(out/'verification.json', dict(independent_life_replays=32, independent_source_writer_paths=576, exact_path_aliases=1248,
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
    commands = ('source_bridge', 'freeze', 'benchmark', 'prepare', 'run', 'detach', 'audit')
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
