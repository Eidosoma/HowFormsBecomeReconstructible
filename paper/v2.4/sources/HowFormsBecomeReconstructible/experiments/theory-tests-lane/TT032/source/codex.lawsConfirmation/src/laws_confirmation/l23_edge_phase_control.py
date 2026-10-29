"""D085: compare true checker joins with three matched diagonal edge phases."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import importlib.util
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l23_contact_intervention as old
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 sha256_file, utc_now, write_hash_manifest)

source, strict_json = old.source, old.strict_json
RUN_ID, DISPOSABLE, WORKERS = 'l23_edge_phase_control_v1_attempt1', 402088, 4
ARMS = ('original', 'join_half', 'phase1_half', 'internal_half', 'phase3_half',
        'join_cut', 'phase1_cut', 'internal_cut', 'phase3_cut')
SOURCE_MAP = ((0, 0), (1, 1), (3, 2), (5, 3), (7, 4))
NEW = ((2, 1, .5), (4, 3, .5), (6, 1, 1.), (8, 3, 1.))
ANCHORS = ((0, .5, 1), (2, 1., 4))  # phase, removal, D084 arm
KINDS = ('absolute_join_advantage', 'composition_join_advantage')
SCIENCE = ('src/laws_confirmation/l23_edge_phase_control.py',
           'scripts/audit_l23_edge_phase_control_outputs.py',
           'tests/test_l23_edge_phase_control.py',
           'scripts/run_l23_edge_phase_control.sh',
           'protocols/L23_EDGE_PHASE_CONTROL_V1.md')
RESERVE, ALLOWANCE = 4*1024**3, 1024**3


def checker():
    path = Path(__file__).resolve().parents[2]/SCIENCE[1]
    spec = importlib.util.spec_from_file_location('d085_independent_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_edges(phase):
    if phase not in range(4):
        raise ValueError('undeclared diagonal phase')
    r, c = np.indices((16, 16))
    mask = (r//4+c//4) % 2 == 0
    joins = old.edge_sets(mask, 2)[0]
    return np.roll(joins, (phase, phase), axis=(1, 2))


def simulate(ctx, inst, norm, phase, removal):
    if removal not in (.5, 1.):
        raise ValueError('undeclared removal')
    cfg = ctx['config']
    local = source.layout_instrument(inst, 2)
    theta, offsets, ids = source.old.case_inputs(local, norm, source.CASES)
    generator = source.seeded(ctx['index'], 'expression')
    noise = .2*generator.standard_normal((cfg.draws, 16, 16))
    noise -= noise.mean(axis=(-2, -1), keepdims=True)
    noise = source.transport(noise, inst['layout_maps'][2])
    v = noise[None]+offsets[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    initial_mean = v.mean(axis=(-2, -1))
    max_drift, max_clip = np.zeros_like(initial_mean), np.zeros_like(initial_mean)
    random = source.MappedNoise(generator, cfg.draws, inst['layout_maps'][2])
    edges = selected_edges(phase)
    raw = dict(theta=theta, offsets=offsets, case_ids=ids, birth_noise=noise)
    for t in range(cfg.sweeps+1):
        if t:
            v, ema, ref = old.step(v, ema, ref, theta[:, None], ctx, random, edges, removal)
        max_drift = np.maximum(max_drift, abs(v.mean(axis=(-2, -1))-initial_mean))
        max_clip = np.maximum(max_clip, (abs(v) == 2.).mean(axis=(-2, -1)))
        if t in cfg.times:
            raw.update({f's{t}_{k}': value.copy() for k, value in (('V', v), ('ema', ema), ('R', ref))})
    raw.update(max_mean_drift=max_drift, max_clip_fraction=max_clip)
    return raw, canonical_digest(generator.bit_generator.state)


def execute_panel(ctx, inst, norm, phase, removal, check):
    raw, digest = simulate(ctx, inst, norm, phase, removal)
    discrepancy = check.check_replay(raw, inst, ctx, norm, phase, removal, digest)
    row = old.observe(raw, inst, 2, ctx['config'], check.previous)
    record = dict(norm=norm, phase=phase, removal=removal, rng_final=digest,
        source_arm=None, replay_max_abs=discrepancy, state_sha256={
            f's{t}_{k}': source.base.array_digest(raw[f's{t}_{k}'])
            for t in ctx['config'].times for k in ('V', 'ema', 'R')})
    compact = dict(final_V=raw[f"s{ctx['config'].sweeps}_V"],
        diagnostics=np.stack((raw['max_mean_drift'], raw['max_clip_fraction']), axis=-1))
    return row, compact, record


def read_source(root, index):
    out = root/'outputs'/old.RUN_ID
    with np.load(out/f'block_{index}.npz', allow_pickle=False) as f:
        data = {k: f[k][2].copy() for k in ('values', 'active', 'metrics', 'diagnostics', 'counts', 'distance')}
    return data, json.loads((out/f'block_{index}.json').read_text())


def assemble(previous, fresh):
    result = {}
    for key in ('values', 'active', 'metrics', 'diagnostics'):
        shape = (previous[key].shape[0], 9, *previous[key].shape[2:])
        result[key] = np.empty(shape, dtype=previous[key].dtype)
        for arm, source_arm in SOURCE_MAP:
            result[key][:, arm] = previous[key][:, source_arm]
        for new_index, (arm, _, _) in enumerate(NEW):
            result[key][:, arm] = fresh[key][:, new_index]
    return result


def execute_block(root, index):
    ctx = source.old.context(index)
    inst, check = source.instruments(ctx), checker()
    check.previous.layout_check.check_instruments(inst, index)
    with np.load(root/'outputs'/source.RUN_ID/f'tissue_{index}'/'instruments.npz', allow_pickle=False) as saved:
        assert set(saved.files) == set(inst)
        for key in inst:
            np.testing.assert_array_equal(inst[key], saved[key])
    previous, source_record = read_source(root, index)
    check.check_source_record(source_record, index, asdict(ctx['config']))
    values = np.empty((2, 4, 5, 12, 3, 8, 8, 2, 3, 4))
    active = np.empty(values.shape[:-2]+(2,), dtype=np.uint8)
    metrics = np.empty((2, 4, 12, 3, 8, 8, 6))
    final_v = np.empty((2, 4, 252, 8, 16, 16))
    diagnostics = np.empty((2, 4, 252, 8, 2))
    records, anchors = [], []
    for norm in range(2):
        for phase, removal, source_arm in ANCHORS:
            row, compact, record = execute_panel(ctx, inst, norm, phase, removal, check)
            check.check_anchor(row, compact, record, previous, source_record, source_arm)
            record['source_arm'] = source_arm
            anchors.append(record)
        for new_index, (_, phase, removal) in enumerate(NEW):
            row, compact, record = execute_panel(ctx, inst, norm, phase, removal, check)
            values[norm, new_index], active[norm, new_index] = row['values'], row['active']
            metrics[norm, new_index] = row['metrics']
            final_v[norm, new_index], diagnostics[norm, new_index] = compact['final_V'], compact['diagnostics']
            records.append(record)
    payload = dict(values=values, active=active, metrics=metrics, final_V=final_v, diagnostics=diagnostics,
        edges=np.stack([selected_edges(p) for p in range(4)]), counts=previous['counts'], distance=previous['distance'])
    combined = assemble(previous, payload)
    check.check_block(payload, previous, combined)
    assert len({p['rng_final'] for p in records+anchors}) == 1
    out = root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz', payload, root)
    with np.load(out/f'block_{index}.npz', allow_pickle=False) as saved:
        assert set(saved.files) == set(payload)
        for key in payload:
            np.testing.assert_array_equal(saved[key], payload[key])
    record = dict(tissue=index, passes=True, config=asdict(ctx['config']), panels=records, anchors=anchors,
        independently_replayed_panels=12, source_bridge_panels=4,
        inactive_V=int((active[..., 0] == 0).sum()), inactive_template=int((active[..., 1] == 0).sum()))
    strict_json(out/f'block_{index}.json', record, root)
    check.previous.layout_check.close(record, json.loads((out/f'block_{index}.json').read_text()))
    return record


def summary_of(blocks, metrics):
    # Combined values: norm,arm,time,pair,budget,reader,start,region,band,error.
    return dict(means=sum(x.mean(axis=6) for x in blocks)/len(blocks),
        composition_block_means=np.stack([(x[:, :, :, :, :, 1]-x[:, :, :, :, :, 7]).mean(axis=(5, 6)) for x in blocks]),
        metric_means=sum(x.mean(axis=5) for x in metrics)/len(metrics))


def focal_of(blocks):
    rows = []
    for n, norm in enumerate(source.NORMS):
        x = np.stack([b[n, :, -1, :, 1, :, :, :, 0, 0].mean(axis=-1) for b in blocks])
        for removal, join, internals in ((.5, 1, (2, 3, 4)), (1., 5, (6, 7, 8))):
            for phase, arm in enumerate(internals, start=1):
                absolute = x[:, arm, :, 1]-x[:, join, :, 1]
                composition = absolute-(x[:, arm, :, 7]-x[:, join, :, 7])
                for kind, data in enumerate((absolute, composition)):
                    rows.append(dict(norm=norm, removal=removal, phase=phase, kind=kind, label=KINDS[kind],
                                     source_only=phase == 2, **old.seam.describe(data)))
    return rows


def contract():
    return dict(run_id=RUN_ID, decision='D085', law='L23', source_run=old.RUN_ID,
        tissues=list(source.TISSUES), layout='checker4', phases=[0, 1, 2, 3], diagonal_phases_only=True,
        phase_shifts=[[p, p] for p in range(4)], norms=list(source.NORMS), arms=list(ARMS),
        source_map=[list(p) for p in SOURCE_MAP], new_cases=[list(p) for p in NEW], anchors=[list(p) for p in ANCHORS],
        pairs=list(source.PAIRS), budgets=list(source.BUDGETS), measured=list(source.MEASURED),
        groups={k: list(v) for k, v in source.GROUPS.items()}, times=list(old.seam.TIMES),
        bands=list(old.seam.BANDS[:3]), errors=list(old.seam.ERRORS), metrics=list(source.METRICS),
        draws=8, sweeps=300, workers=WORKERS, source_seed_tag=source.TAG, edge_count=128,
        new_independent_blocks=0, new_intervention_lives=258048, source_anchor_lives=129024,
        independent_replay_lives=387072, new_panels=128, source_anchor_panels=64,
        focal_labels=list(KINDS), focal_endpoints=24, source_only_focal_endpoints=8,
        focal_layout='checker4', focal_time=300, focal_budget='matched', focal_group='all',
        focal_error=old.seam.ERRORS[0], primary_removal=.5, secondary_removal=1.,
        unchanged_d084_step=True, global_mean_constraint_unchanged=True,
        disconnected_regions_are_not_independent=True, outcome_informed=True,
        new_value_axes='norm,new_arm,time,pair,budget,reader,start,region,band,error',
        combined_value_axes='norm,arm,time,pair,budget,reader,start,region,band,error',
        final_V_axes='norm,new_arm,case,start,row,column',
        diagnostics_axes='norm,new_arm,case,start,max_mean_drift_or_max_clip_fraction',
        metric_axes='norm,arm,pair,budget,reader,start,metric',
        means_axes='norm,arm,time,pair,budget,reader,region,band,error',
        composition_block_axes='block,norm,arm,time,pair,budget,band,error',
        source_bridge_exact=True, replay_atol=1e-10, output_hashes=36,
        reserve_bytes=RESERVE, output_allowance_bytes=ALLOWANCE,
        duplicated_source_states=False, duplicated_source_block_statistics=False,
        full_intermediate_states_retained=False, intermediate_state_hashes_retained=True,
        final_new_V_retained=True, all_new_checkpoint_statistics_retained=True,
        full_independent_dynamics_replay=True, hereditary_boundaries=0)


def input_paths(root):
    out = root/'outputs'/old.RUN_ID
    paths = []
    for name in ('input_hashes.sha256', 'output_hashes.sha256'):
        path = out/name
        paths.append(path)
        paths.extend(Path(line.split('  ', 1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/old.RUN_ID/p for p in ('MANIFEST.json', 'STATUS.json', 'COMPLETE')]
    ws = Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENCE, 'reviews/L23_CONTACT_INTERVENTION_2026-09-10.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root, hashes):
    out, run = root/'outputs'/old.RUN_ID, root/'runs'/old.RUN_ID
    for name, count in (('input_hashes.sha256', 495), ('output_hashes.sha256', 36)):
        rows = [line.split('  ', 1) for line in (out/name).read_text().splitlines()]
        assert len(rows) == count and len({p for _, p in rows}) == count
        for digest, path in rows:
            assert hashes[path] == digest, path
    status = json.loads((run/'STATUS.json').read_text())
    assert status['status'] == 'COMPLETE' and status['verified_saved_analysis']
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    analysis = json.loads((out/'analysis.json').read_text())
    for key, value in old.contract().items():
        assert canonical_digest(analysis[key]) == canonical_digest(value), key
    verification = json.loads((out/'verification.json').read_text())
    assert analysis['passes'] and verification['passes'] and verification['saved_pool_verified']
    assert verification['independently_replayed_panels'] == 480 and verification['source_bridge_panels'] == 96
    return True


def preflight(root, starting=True):
    cpus = source.preflight(root)
    if shutil.disk_usage(root).free < RESERVE+(ALLOWANCE if starting else 0):
        raise RuntimeError('four GiB reserve plus one GiB output allowance required at launch')
    return cpus


def timing_path(root):
    return root/'tmp'/f'{RUN_ID}_benchmark.json'


def benchmark(root):
    cpus = preflight(root)
    path = timing_path(root)
    if path.exists():
        raise FileExistsError('immutable benchmark already exists')
    tick = time.monotonic()
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    source_verified(root, hashes)
    hashing = time.monotonic()-tick
    ctx = source.old.context(DISPOSABLE)
    inst, check = source.instruments(ctx), checker()
    check.previous.layout_check.check_instruments(inst, DISPOSABLE)
    directory = root/'tmp'/f'{RUN_ID}_benchmark'
    directory.mkdir()
    panels, records, seconds = [], [], []
    for phase, removal, source_arm in [(p, r, None) for _, p, r in NEW]+list(ANCHORS):
        tick = time.monotonic()
        row, compact, record = execute_panel(ctx, inst, 0, phase, removal, check)
        if source_arm is not None:
            raw, digest = old.simulate(ctx, inst, 2, 0, source_arm)
            assert digest == record['rng_final']
            assert record['state_sha256'] == {f's{t}_{k}': source.base.array_digest(raw[f's{t}_{k}'])
                for t in ctx['config'].times for k in ('V', 'ema', 'R')}
            record['source_arm'] = source_arm
        panels.append(row | compact); records.append(record)
        seconds.append(time.monotonic()-tick)
    tick = time.monotonic()
    payload = {key: np.stack([p[key] for p in panels]) for key in panels[0]}
    source.base.atomic_npz(directory/'panels.npz', payload, root)
    strict_json(directory/'verification.json', dict(passes=True, panels=records), root)
    with np.load(directory/'panels.npz', allow_pickle=False) as saved:
        for key, value in payload.items():
            np.testing.assert_array_equal(saved[key], value)
    writing = time.monotonic()-tick
    elapsed = max(seconds)+writing/6
    forecast = 192*elapsed+2*hashing+180  # no assumed four-worker speedup
    assert hashes == {str(p): sha256_file(p) for p in input_paths(root)}
    record = dict(run_id=RUN_ID, passed=True, completed_utc=utc_now(), effects_not_reported=True,
        disposable=DISPOSABLE, norm=0, config=asdict(ctx['config']), benchmark_panels=6,
        panel_seconds=elapsed, arm_seconds=seconds, write_seconds=writing, hash_seconds=hashing,
        projected_seconds=forecast, must_detach=forecast > 600, cpu_affinity=cpus,
        forecast_does_not_credit_parallel_speedup=True,
        benchmark_files={str(p): sha256_file(p) for p in sorted(directory.iterdir())}, input_sha256=hashes)
    strict_json(path, record, root)
    print(json.dumps({k: v for k, v in record.items() if k not in ('input_sha256', 'benchmark_files')}, indent=2), flush=True)
    return record


def prepare(root):
    run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError('immutable run already exists')
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing['run_id'] == RUN_ID and timing['passed'] and timing['effects_not_reported']
    assert timing['disposable'] == DISPOSABLE and timing['norm'] == 0 and timing['benchmark_panels'] == 6
    assert canonical_digest(timing['config']) == canonical_digest(asdict(source.CONFIG))
    assert len(timing['arm_seconds']) == 6 and all(x > 0 for x in timing['arm_seconds'])
    assert timing['write_seconds'] > 0 and timing['hash_seconds'] > 0
    assert timing['panel_seconds'] == max(timing['arm_seconds'])+timing['write_seconds']/6
    assert timing['projected_seconds'] == 192*timing['panel_seconds']+2*timing['hash_seconds']+180
    assert timing['must_detach'] is (timing['projected_seconds'] > 600)
    assert timing['input_sha256'] == hashes
    source_verified(root, hashes)
    assert set(timing['benchmark_files']) == {str(root/'tmp'/f'{RUN_ID}_benchmark'/p) for p in ('panels.npz', 'verification.json')}
    for path, digest in timing['benchmark_files'].items():
        assert sha256_file(Path(path)) == digest
        hashes[path] = digest
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), input_sha256=hashes,
        hash_contract=canonical_digest(hashes), timing=timing, cpu_affinity=cpus, environment=environment_manifest())
    run.mkdir(parents=True); out.mkdir(parents=True)
    strict_json(run/'MANIFEST.json', manifest, root)
    atomic_text(out/'input_hashes.sha256', ''.join(f'{hashes[p]}  {p}\n' for p in sorted(hashes)), root)
    strict_json(run/'STATUS.json', dict(status='PREPARED', run_id=RUN_ID), root)
    print(json.dumps(dict(status='PREPARED', input_hashes=len(hashes), estimated_seconds=timing['projected_seconds'])), flush=True)
    return manifest


def verify(root):
    run = root/'runs'/RUN_ID
    manifest = json.loads((run/'MANIFEST.json').read_text())
    assert json.loads((run/'STATUS.json').read_text())['status'] == 'PREPARED'
    assert not (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for key, value in contract().items():
        assert canonical_digest(manifest[key]) == canonical_digest(value), key
    hashes, timing = manifest['input_sha256'], manifest['timing']
    assert timing == json.loads(timing_path(root).read_text())
    assert set(hashes) == {str(p) for p in input_paths(root)+[timing_path(root)]} | set(timing['benchmark_files'])
    assert canonical_digest(hashes) == manifest['hash_contract']
    assert all(sha256_file(Path(p)) == digest for p, digest in hashes.items())
    assert (root/'outputs'/RUN_ID/'input_hashes.sha256').read_text() == ''.join(f'{hashes[p]}  {p}\n' for p in sorted(hashes))
    source_verified(root, hashes)
    return manifest


def detach(root):
    if not (root/'runs'/RUN_ID).exists():
        prepare(root)
    manifest = verify(root)
    preflight(root)
    run = root/'runs'/RUN_ID
    (run/'LAUNCH.lock').mkdir()
    logs = [root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout', 'stderr')]
    with logs[0].open('xb') as out, logs[1].open('xb') as err:
        child = subprocess.Popen([sys.executable, '-m', 'laws_confirmation.l23_edge_phase_control',
            '--external-root', str(root), '--run'], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=child.pid, launched_utc=utc_now(), polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'], status=str(run/'STATUS.json'),
        stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    strict_json(run/'LAUNCH.json', record, root)
    atomic_text(run/'RUN.pid', str(child.pid)+'\n', root)
    print(json.dumps(record, indent=2), flush=True)
    return record


def run_experiment(root):
    manifest = verify(root)
    run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    if manifest['timing']['must_detach'] and not (run/'LAUNCH.lock').is_dir():
        raise RuntimeError('detached execution required above ten minutes')
    (run/'EXECUTION.lock').mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        records = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            pending = {pool.submit(execute_block, root, t): t for t in source.TISSUES}
            try:
                for future in as_completed(pending):
                    t = pending[future]
                    records[t] = future.result()
                    preflight(root, starting=False)
                    strict_json(run/'STATUS.json', dict(status='RUNNING', run_id=RUN_ID,
                        checked_blocks=len(records), checked_panels=12*len(records), updated_utc=utc_now()), root)
                    print(f'D085 block {t}: eight new panels and four source anchors independently checked', flush=True)
            except Exception:
                for future in pending:
                    future.cancel()
                raise
        blocks, metrics = [], []
        for t in source.TISSUES:
            previous, _ = read_source(root, t)
            with np.load(out/f'block_{t}.npz', allow_pickle=False) as saved:
                fresh = {k: saved[k] for k in ('values', 'active', 'metrics', 'diagnostics')}
            combined = assemble(previous, fresh)
            blocks.append(combined['values']); metrics.append(combined['metrics'])
        summary, focal, check = summary_of(blocks, metrics), focal_of(blocks), checker()
        assert check.check_summary(blocks, metrics, summary, focal)
        source.base.atomic_npz(out/'summary.npz', summary, root)
        with np.load(out/'summary.npz', allow_pickle=False) as saved:
            assert check.check_summary(blocks, metrics, dict(saved), focal)
        analysis = contract() | dict(completed_utc=utc_now(), passes=True, focal=focal,
            block_records=[records[t] for t in source.TISSUES],
            replay_max_abs=max(p['replay_max_abs'] for r in records.values() for p in r['panels']+r['anchors']))
        strict_json(out/'analysis.json', analysis, root)
        assert check.check_summary(blocks, metrics, summary, json.loads((out/'analysis.json').read_text())['focal'])
        assert all(sha256_file(Path(p)) == digest for p, digest in manifest['input_sha256'].items())
        verification = dict(passes=True, independently_replayed_panels=192, source_bridge_panels=64,
            new_snapshot_batches=640, anchor_snapshot_batches=320, saved_pool_verified=True,
            input_hashes_unchanged=True, input_hashes=len(manifest['input_sha256']), checked_utc=utc_now())
        strict_json(out/'verification.json', verification, root)
        paths = [out/f'block_{t}.{ext}' for t in source.TISSUES for ext in ('npz', 'json')]
        paths += [out/p for p in ('summary.npz', 'analysis.json', 'verification.json', 'input_hashes.sha256')]
        assert len(paths) == 36
        write_hash_manifest(paths, out/'output_hashes.sha256', root)
        assert source.old.checker().check_hashes(out/'output_hashes.sha256') == 36
        total_bytes = sum(p.stat().st_size for p in paths)
        assert total_bytes < ALLOWANCE
        status = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start, checked_blocks=16, independently_replayed_panels=192,
            verified_saved_analysis=True, output_bytes=total_bytes)
        strict_json(run/'STATUS.json', status, root)
        atomic_text(run/'COMPLETE', status['completed_utc']+'\n', root)
        print(json.dumps(status, indent=2), flush=True)
        return 0
    except Exception as error:
        status = dict(status='FAILED', run_id=RUN_ID, failed_utc=utc_now(), error=str(error), traceback=traceback.format_exc())
        strict_json(run/'STATUS.json', status, root)
        atomic_text(run/'FAILED', status['failed_utc']+'\n', root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for op in ('benchmark', 'prepare', 'detach', 'run'):
        group.add_argument('--'+op, action='store_true')
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_experiment(root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
