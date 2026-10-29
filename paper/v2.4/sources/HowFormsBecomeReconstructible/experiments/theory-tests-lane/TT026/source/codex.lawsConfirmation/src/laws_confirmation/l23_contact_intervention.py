"""D084: causal local-diffusion interventions, with translated internal controls."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l23_seam_localization as seam
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

source, strict_json = seam.source, seam.strict_json
RUN_ID = 'l23_contact_intervention_v1_attempt1'
ARMS = ('original', 'join_half', 'internal_half', 'join_cut', 'internal_cut')
REMOVALS = (0., .5, .5, 1., 1.)
SHIFTS = ((0, 4), (4, 0), (2, 2))
KINDS = ('normalized_rescue', 'composition_rescue', 'contact_specificity',
         'record_specificity_off', 'record_specificity_scrambled')
DISPOSABLE = 402087
WORKERS = 4
SCIENCE = ('src/laws_confirmation/l23_contact_intervention.py',
           'scripts/audit_l23_contact_intervention_outputs.py',
           'tests/test_l23_contact_intervention.py',
           'scripts/run_l23_contact_intervention.sh',
           'protocols/L23_CONTACT_INTERVENTION_V1.md')
RESERVE, ALLOWANCE = 4*1024**3, 3*1024**3


def checker():
    path = Path(__file__).resolve().parents[2]/SCIENCE[1]
    spec = importlib.util.spec_from_file_location('d084_independent_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def edge_sets(mask, geometry):
    """Each entry is one undirected edge from (r,c) to its +axis neighbour."""
    cross = np.stack([mask != np.roll(mask, -1, axis=a) for a in (0, 1)])
    internal = np.roll(cross, SHIFTS[geometry], axis=(1, 2))
    assert not (cross & internal).any()
    np.testing.assert_array_equal(cross.sum(axis=(1, 2)), internal.sum(axis=(1, 2)))
    degree = lambda e: sum(e[a].astype(int)+np.roll(e[a], 1, axis=a) for a in (0, 1))
    np.testing.assert_array_equal(np.sort(degree(cross).ravel()), np.sort(degree(internal).ravel()))
    assert cross.sum() == (32, 32, 128)[geometry]
    return np.stack((cross, internal))


def diffusion(v, edges, removal):
    # Preserve the source operation order exactly for the unmodified arm.
    neighbors = (np.roll(v, 1, -2)+np.roll(v, -1, -2)
                 +np.roll(v, 1, -1)+np.roll(v, -1, -1))/4.
    result = neighbors-v
    if removal:
        flux = np.zeros_like(v)
        for a in (0, 1):
            axis = a-2
            flux += edges[a]*(np.roll(v, -1, axis)-v)
            flux += np.roll(edges[a], 1, a)*(np.roll(v, 1, axis)-v)
        result = result-removal*flux/4.
    return result


def step(v, ema, ref, theta, ctx, random, edges, removal):
    """Only the source rung-A diffusion is modified; blueprint rung T, c_m=0."""
    tissue, ladder, bp = ctx['tissue'], ctx['ladder'], ctx['bp']
    drift = v-v**3+tissue.well_asym+theta+tissue.coupling*diffusion(v, edges, removal)+0.
    drift -= drift.mean(axis=(-2, -1), keepdims=True)
    noise = tissue.sigma*random.standard_normal(v.shape)
    noise -= noise.mean(axis=(-2, -1), keepdims=True)
    v = np.clip(v+tissue.dt*drift+noise, -2., 2.)
    ema = (1.-ladder.ema_rate)*ema+ladder.ema_rate*v
    ref = ref+bp.rho*(v-ref)
    return v, ema, ref


def simulate(ctx, inst, g, n, arm):
    cfg = ctx['config']
    assert arm in range(5)
    local = source.layout_instrument(inst, g)
    theta, offsets, ids = source.old.case_inputs(local, n, source.CASES)
    generator = source.seeded(ctx['index'], 'expression')  # unchanged D082 stream
    noise = .2*generator.standard_normal((cfg.draws, 16, 16))
    noise -= noise.mean(axis=(-2, -1), keepdims=True)
    noise = source.transport(noise, inst['layout_maps'][g])
    v = noise[None]+offsets[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    start_mean = v.mean(axis=(-2, -1))
    max_drift, max_clip = np.zeros_like(start_mean), np.zeros_like(start_mean)
    random = source.MappedNoise(generator, cfg.draws, inst['layout_maps'][g])
    edges = edge_sets(local['left'], g)[int(arm in (2, 4))]
    raw = dict(theta=theta, offsets=offsets, case_ids=ids, birth_noise=noise)
    for t in range(cfg.sweeps+1):
        if t:
            v, ema, ref = step(v, ema, ref, theta[:, None], ctx, random, edges, REMOVALS[arm])
        max_drift = np.maximum(max_drift, abs(v.mean(axis=(-2, -1))-start_mean))
        max_clip = np.maximum(max_clip, (abs(v) == 2.).mean(axis=(-2, -1)))
        if t in cfg.times:
            raw.update({f's{t}_{key}': value.copy() for key, value in (('V', v), ('ema', ema), ('R', ref))})
    raw.update(max_mean_drift=max_drift, max_clip_fraction=max_clip)
    return raw, canonical_digest(generator.bit_generator.state)


def observe(raw, inst, g, cfg, check):
    local = source.layout_instrument(inst, g)
    rows = []
    for t in cfg.times:
        v = raw[f's{t}_V'].reshape(12, 3, 7, cfg.draws, 16, 16)
        row = seam.statistics(v, local['forms'], local['left'])
        assert check.seam_check.check_snapshot(v, inst['forms'], g, row)
        rows.append(row)
    v = raw[f's{cfg.sweeps}_V']
    scores = source.old.half_scores(v, local['forms'], local['left'])
    metrics = source.panel_metrics(dict(scores=scores, probabilities=source.old.probabilities(scores),
        alignment=source.centered_alignment(v, local['forms'], local['left'])))
    assert check.check_metrics(v, inst['forms'], g, metrics)
    assert check.seam_check.check_endpoint(rows[-1]['values'], metrics)
    return dict(values=np.stack([r['values'][..., :3, :] for r in rows]),
                active=np.stack([r['active'] for r in rows]), metrics=metrics,
                counts=rows[0]['counts'][:, :3], distance=rows[0]['distance'])


def execute_panel(ctx, inst, g, n, arm, check, bridge=None):
    raw, digest = simulate(ctx, inst, g, n, arm)
    replay = check.check_replay(raw, inst, ctx, g, n, arm, digest)
    observed = observe(raw, inst, g, ctx['config'], check)
    if bridge is not None:
        assert arm == 0
        check.check_source_bridge(raw, observed, bridge, ctx['index'], g, n)
    keys = [f's{t}_{field}' for t in ctx['config'].times for field in ('V', 'ema', 'R')]
    record = dict(geometry=g, norm=n, arm=arm, rng_final=digest, replay_max_abs=replay,
                  state_sha256={key: source.base.array_digest(raw[key]) for key in keys},
                  source_bridge=bridge is not None)
    compact = dict(final_V=raw[f"s{ctx['config'].sweeps}_V"],
        max_mean_drift=raw['max_mean_drift'], max_clip_fraction=raw['max_clip_fraction'])
    return observed, compact, record


def execute_block(root, index):
    ctx = source.old.context(index)
    inst = source.instruments(ctx)
    check = checker()
    check.layout_check.check_instruments(inst, index)
    directory = root/'outputs'/source.RUN_ID/f'tissue_{index}'
    with np.load(directory/'instruments.npz', allow_pickle=False) as saved:
        assert set(saved.files) == set(inst)
        for key in inst:
            np.testing.assert_array_equal(inst[key], saved[key])
    values = np.empty((3, 2, 5, 5, 12, 3, 8, 8, 2, 3, 4))
    active = np.empty(values.shape[:-2]+(2,), dtype=np.uint8)
    metrics = np.empty((3, 2, 5, 12, 3, 8, 8, 6))
    finals = np.empty((3, 2, 4, 252, 8, 16, 16))
    diagnostics = np.empty((3, 2, 5, 252, 8, 2))
    records, counts, distances, edge_masks = [], [], [], []
    for g in range(3):
        edge_masks.append(edge_sets(source.layout_instrument(inst, g)['left'], g))
        for n in range(2):
            for arm in range(5):
                row, raw, record = execute_panel(ctx, inst, g, n, arm, check,
                                                root if arm == 0 else None)
                values[g, n, arm], active[g, n, arm] = row['values'], row['active']
                metrics[g, n, arm] = row['metrics']
                if arm:
                    finals[g, n, arm-1] = raw['final_V']
                diagnostics[g, n, arm] = np.stack((raw['max_mean_drift'], raw['max_clip_fraction']), axis=-1)
                if n == 0 and arm == 0:
                    counts.append(row['counts']); distances.append(row['distance'])
                records.append(record)
    payload = dict(values=values, active=active, metrics=metrics, final_V=finals,
        diagnostics=diagnostics, counts=np.array(counts), distance=np.array(distances), edges=np.array(edge_masks))
    rotation = check.check_block(payload)
    assert len({r['rng_final'] for r in records}) == 1
    out = root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz', payload, root)
    with np.load(out/f'block_{index}.npz', allow_pickle=False) as saved:
        assert set(saved.files) == set(payload)
        for key in payload:
            np.testing.assert_array_equal(saved[key], payload[key])
    record = dict(tissue=index, config=asdict(ctx['config']), passes=True, panels=records,
        rotation_max_abs=rotation, independently_checked_panels=30, source_bridge_panels=6,
        inactive_V=int((active[..., 0] == 0).sum()), inactive_template=int((active[..., 1] == 0).sum()))
    strict_json(out/f'block_{index}.json', record, root)
    check.layout_check.close(record, json.loads((out/f'block_{index}.json').read_text()))
    return record


def summary_of(blocks, metrics):
    # block values: layout,norm,arm,time,pair,budget,reader,start,region,band,error
    return dict(means=sum(x.mean(axis=7) for x in blocks)/len(blocks),
        composition_block_means=np.stack([(x[..., 1, :, :, :, :]-x[..., 7, :, :, :, :]).mean(axis=(6, 7))
                                         for x in blocks]),
        metric_means=sum(x.mean(axis=6) for x in metrics)/len(metrics))


def focal_of(blocks):
    result = []
    for n, norm in enumerate(source.NORMS):
        # block,arm,pair,reader,start after averaging region; fixed all/matched/final/NSE.
        x = np.stack([b[2, n, :, -1, :, 1, :, :, :, 0, 0].mean(axis=-1) for b in blocks])
        cost = x[:, :, :, 1]-x[:, :, :, 7]
        for join, internal, removal in ((1, 2, .5), (3, 4, 1.)):
            rescue = x[:, 0, :, 1]-x[:, join, :, 1]
            draws = (rescue, cost[:, 0]-cost[:, join], cost[:, internal]-cost[:, join],
                     rescue-(x[:, 0, :, 6]-x[:, join, :, 6]),
                     rescue-(x[:, 0, :, 4]-x[:, join, :, 4]))
            for kind, data in enumerate(draws):
                result.append(dict(norm=norm, removal=removal, kind=kind, label=KINDS[kind], **seam.describe(data)))
    return result


def contract():
    return dict(run_id=RUN_ID, decision='D084', law='L23', source_run=source.RUN_ID, diagnostic_run=seam.RUN_ID,
        tissues=list(source.TISSUES), layouts=list(source.LAYOUTS), norms=list(source.NORMS),
        arms=list(ARMS), removals=list(REMOVALS), shifts=[list(x) for x in SHIFTS],
        pairs=list(source.PAIRS), budgets=list(source.BUDGETS), measured=list(source.MEASURED),
        groups={k: list(v) for k, v in source.GROUPS.items()}, times=list(seam.TIMES),
        bands=list(seam.BANDS[:3]), errors=list(seam.ERRORS), metrics=list(source.METRICS),
        draws=8, sweeps=300, workers=WORKERS, source_seed_tag=source.TAG, new_independent_blocks=0,
        new_intervention_lives=774144, original_bridge_lives=193536, independent_replay_lives=967680,
        focal_labels=list(KINDS), focal_endpoints=20, focal_layout='checker4', focal_time=300,
        focal_budget='matched', focal_group='all', focal_error=seam.ERRORS[0],
        primary_removal=.5, secondary_removal=1., local_diffusion_only=True, fixed_denominator=4,
        global_mean_constraint_unchanged=True, disconnected_regions_are_not_independent=True,
        value_axes='layout,norm,arm,time,pair,budget,reader,start,region,band,error',
        final_V_axes='layout,norm,modified_arm,case,start,row,column',
        diagnostics_axes='layout,norm,arm,case,start,max_mean_drift_or_max_clip_fraction',
        metric_axes='layout,norm,arm,pair,budget,reader,start,metric',
        means_axes='layout,norm,arm,time,pair,budget,reader,region,band,error',
        composition_block_axes='block,layout,norm,arm,time,pair,budget,band,error',
        rotation_atol=1e-10, replay_atol=1e-10, source_bridge_exact=True, output_hashes=36,
        reserve_bytes=RESERVE, output_allowance_bytes=ALLOWANCE, outcome_informed=True,
        full_intermediate_states_retained=False, intermediate_state_hashes_retained=True,
        final_modified_V_retained=True, all_checkpoint_statistics_retained=True,
        full_independent_dynamics_replay=True, hereditary_boundaries=0)


def input_paths(root):
    out = root/'outputs'/seam.RUN_ID
    paths = []
    for name in ('input_hashes.sha256', 'output_hashes.sha256'):
        path = out/name
        paths.append(path)
        paths.extend(Path(line.split('  ', 1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/seam.RUN_ID/p for p in ('MANIFEST.json', 'STATUS.json', 'COMPLETE')]
    ws = Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENCE, 'reviews/L23_SEAM_LOCALIZATION_2026-09-09.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root, hashes):
    out = root/'outputs'/seam.RUN_ID
    for name, count in (('input_hashes.sha256', 462), ('output_hashes.sha256', 20)):
        rows = [line.split('  ', 1) for line in (out/name).read_text().splitlines()]
        assert len(rows) == count and len({p for _, p in rows}) == count
        for digest, path in rows:
            assert hashes[path] == digest, path
    run = root/'runs'/seam.RUN_ID
    status = json.loads((run/'STATUS.json').read_text())
    assert status['status'] == 'COMPLETE' and status['verified_saved_analysis']
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    analysis = json.loads((out/'analysis.json').read_text())
    for key, value in seam.contract().items():
        assert canonical_digest(analysis[key]) == canonical_digest(value), key
    assert analysis['passes'] and json.loads((out/'verification.json').read_text())['passes']
    return True


def preflight(root, starting=True):
    cpus = source.preflight(root)
    if shutil.disk_usage(root).free < RESERVE+(ALLOWANCE if starting else 0):
        raise RuntimeError('insufficient external space: four GiB reserve plus three GiB new-output allowance at launch')
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
    # Declared disposable block, checker layout, primary norm, all five arms.
    # Complete 252 cases / 8 starts / 300 steps + independent replay and observers.
    ctx = source.old.context(DISPOSABLE)
    inst, check = source.instruments(ctx), checker()
    check.layout_check.check_instruments(inst, DISPOSABLE)
    directory = root/'tmp'/f'{RUN_ID}_benchmark'
    directory.mkdir()
    panels, records, seconds = [], [], []
    for arm in range(5):
        tick = time.monotonic()
        row, raw, record = execute_panel(ctx, inst, 2, 0, arm, check)
        panels.append(row | raw); records.append(record)
        seconds.append(time.monotonic()-tick)
    tick = time.monotonic()
    payload = {key: np.stack([p[key] for p in panels]) for key in panels[0]}
    source.base.atomic_npz(directory/'panel.npz', payload, root)
    strict_json(directory/'verification.json', dict(passes=True, panels=records), root)
    with np.load(directory/'panel.npz', allow_pickle=False) as saved:
        for key, value in payload.items():
            np.testing.assert_array_equal(saved[key], value)
    write_seconds = time.monotonic()-tick
    elapsed = max(seconds)+write_seconds/5
    # No division by workers: conservative contention-safe upper planning allowance.
    forecast = 480*elapsed+2*hashing+180
    assert hashes == {str(p): sha256_file(p) for p in input_paths(root)}
    record = dict(run_id=RUN_ID, passed=True, completed_utc=utc_now(), effects_not_reported=True,
        disposable=DISPOSABLE, panel=[2, 0], arms=list(range(5)), config=asdict(ctx['config']),
        arm_seconds=seconds, write_seconds=write_seconds, panel_seconds=elapsed,
        hash_seconds=hashing, projected_seconds=forecast, must_detach=forecast > 600,
        forecast_does_not_credit_parallel_speedup=True, cpu_affinity=cpus,
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
    assert timing['disposable'] == DISPOSABLE and timing['panel'] == [2, 0] and timing['arms'] == list(range(5))
    assert canonical_digest(timing['config']) == canonical_digest(asdict(source.CONFIG))
    assert timing['panel_seconds'] > 0 and timing['hash_seconds'] > 0
    assert len(timing['arm_seconds']) == 5 and all(x > 0 for x in timing['arm_seconds'])
    assert timing['write_seconds'] > 0
    assert timing['panel_seconds'] == max(timing['arm_seconds'])+timing['write_seconds']/5
    assert timing['projected_seconds'] == 480*timing['panel_seconds']+2*timing['hash_seconds']+180
    assert timing['must_detach'] is (timing['projected_seconds'] > 600)
    assert timing['input_sha256'] == hashes
    source_verified(root, hashes)
    expected_benchmark = {str(root/'tmp'/f'{RUN_ID}_benchmark'/p) for p in ('panel.npz', 'verification.json')}
    assert set(timing['benchmark_files']) == expected_benchmark
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
        child = subprocess.Popen([sys.executable, '-m', 'laws_confirmation.l23_contact_intervention',
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
                        checked_blocks=len(records), checked_panels=30*len(records), updated_utc=utc_now()), root)
                    print(f'D084 block {t}: all thirty panels independently replayed and checked', flush=True)
            except Exception:
                for future in pending:
                    future.cancel()
                raise  # preserve running workers' artifacts; no replacement jobs or retry
        blocks, metrics = [], []
        for t in source.TISSUES:
            with np.load(out/f'block_{t}.npz', allow_pickle=False) as saved:
                blocks.append(saved['values']); metrics.append(saved['metrics'])
        summary, focal, check = summary_of(blocks, metrics), focal_of(blocks), checker()
        assert check.check_summary(blocks, metrics, summary, focal)
        source.base.atomic_npz(out/'summary.npz', summary, root)
        with np.load(out/'summary.npz', allow_pickle=False) as saved:
            assert check.check_summary(blocks, metrics, dict(saved), focal)
        analysis = contract() | dict(completed_utc=utc_now(), passes=True, focal=focal,
            block_records=[records[t] for t in source.TISSUES],
            rotation_max_abs=max(r['rotation_max_abs'] for r in records.values()),
            replay_max_abs=max(p['replay_max_abs'] for r in records.values() for p in r['panels']))
        strict_json(out/'analysis.json', analysis, root)
        assert check.check_summary(blocks, metrics, summary, json.loads((out/'analysis.json').read_text())['focal'])
        assert all(sha256_file(Path(p)) == digest for p, digest in manifest['input_sha256'].items())
        verification = dict(passes=True, independently_replayed_panels=480, source_bridge_panels=96,
            independently_checked_snapshots=2400, saved_pool_verified=True, input_hashes_unchanged=True,
            input_hashes=len(manifest['input_sha256']), checked_utc=utc_now())
        strict_json(out/'verification.json', verification, root)
        paths = [out/f'block_{t}.{ext}' for t in source.TISSUES for ext in ('npz', 'json')]
        paths += [out/p for p in ('summary.npz', 'analysis.json', 'verification.json', 'input_hashes.sha256')]
        assert len(paths) == 36
        write_hash_manifest(paths, out/'output_hashes.sha256', root)
        assert source.old.checker().check_hashes(out/'output_hashes.sha256') == 36
        total_bytes = sum(p.stat().st_size for p in paths)
        assert total_bytes < ALLOWANCE
        status = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start, checked_blocks=16, independently_replayed_panels=480,
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
