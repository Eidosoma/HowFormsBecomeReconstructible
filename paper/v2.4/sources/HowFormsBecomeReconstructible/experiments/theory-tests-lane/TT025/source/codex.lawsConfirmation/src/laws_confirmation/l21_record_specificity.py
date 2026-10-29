"""D095: lineage/address-specificity at the fixed L21 boundary.

Frozen D094 code is imported read-only; no historical file is patched.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

from . import l21_paired_fitness as old
from . import l21_paired_fitness_run as io
from .io import canonical_digest, environment_manifest, external_root, require_beneath, sha256_file, utc_now

TAG, RUN_ID = 'l21-record-specificity-v1', 'l21_record_specificity_v1_attempt1'
TISSUES, DISPOSABLE, WORKERS = tuple(range(42000, 42008)), 514121, 4
CONFIG = old.CONFIG
SHORT = replace(old.SHORT, replicates=2)
RECORDS = ('own', 'native', 'other_lineage', 'shuffled', 'reversed')
BACKGROUNDS = ('live', 'held_R_zero')
METRICS = (*old.METRICS, 'donor_amplitude', 'donor_projection',
           'recipient_minus_donor_amplitude', 'recipient_minus_donor_projection')
GEOMETRY = ('mean', 'std', 'rms', 'periodic_neighbor_rms')
PRIMARY = 'own_minus_other_lineage/live'
SCIENCE = ('src/laws_confirmation/l21_record_specificity.py',
           'scripts/audit_l21_record_specificity_outputs.py',
           'tests/test_l21_record_specificity.py', 'scripts/run_l21_record_specificity.sh',
           'protocols/L21_RECORD_SPECIFICITY_V1.md')
WS = Path(__file__).resolve().parents[2]
OLD_COMPLETE_SHA = 'd3d888470304e9b6c3168aa41e31350286f2533a35f2a35adf68412300c4cb57'


def seed(index, life, phase):
    if type(index) is not int or index < 0 or type(life) is not int or life not in (0, 1):
        raise ValueError('nonnegative integer tissue and life 0/1 required')
    return int.from_bytes(hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()[:16], 'little')


class Noise(old.SharedNoise):
    def __init__(self, index, life, phase):
        self.generator = np.random.Generator(np.random.PCG64(seed(index, life, phase)))


def geometry(records):
    delta = records-(np.roll(records, 1, -1)+np.roll(records, -1, -1)
                     +np.roll(records, 1, -2)+np.roll(records, -1, -2))/4
    return np.stack((records.mean((-2, -1)), records.std((-2, -1)),
        np.sqrt(np.square(records).mean((-2, -1))), np.sqrt(np.square(delta).mean((-2, -1)))), -1)


def make_records(parents, native, index):
    if parents.shape != (2, 4, 16, 16) or native.shape != (16, 16):
        raise ValueError('two same-tissue parents and one native field required')
    if not np.isfinite(parents).all() or not np.isfinite(native).all():
        raise ValueError('finite record sources required')
    records, permutations = [], []
    for life in range(2):
        theta = parents[life, 3]
        order = Noise(index, life, 'shuffle').generator.permutation(256)
        records.append(np.stack((theta, native, parents[1-life, 3],
                                 theta.ravel()[order].reshape(16, 16), -theta)))
        permutations.append(order)
    return np.stack(records), np.stack(permutations)


def boundary(parent, records):
    if parent.shape != (4, 16, 16) or records.ndim != 3 or records.shape[1:] != (16, 16) or not len(records):
        raise ValueError('one parent and a positive record bank required')
    if not np.isfinite(parent).all() or not np.isfinite(records).all():
        raise ValueError('finite boundary fields required')
    panel = np.broadcast_to(parent[:, None, None], (4, 2, len(records), 16, 16)).copy()
    panel[3] = records
    panel[2, 1] = 0.
    return panel


def children(ctx, parent, records, random, cfg=CONFIG):
    panel = boundary(parent, records)
    state = panel.reshape(4, -1, 16, 16)
    rates = np.repeat([1., 0.], len(records))
    saved = []
    for tick in range(cfg.inter_fission+1):
        if tick:
            state = old.advance(ctx, state, random, rates, cfg)
        if tick in cfg.times:
            saved.append(state.reshape(panel.shape).copy())
    return np.stack(saved)


def measure(v, target, donor, ever, fresh, cfg=CONFIG):
    own = old.scores(v, target, ever, fresh, cfg)
    other = old.scores(v, donor, ever, fresh, cfg)
    return np.concatenate((own, other[..., [0, 3]],
                           own[..., [0, 3]]-other[..., [0, 3]]), axis=-1)


def parent(ctx, life, cfg):
    api = ctx['api']; index = ctx['index']
    native = api['project_theta'](api['make_thresholds'](ctx['tissue'])[None], cfg.norm)[0]
    random = Noise(index, life, 'founder')
    v = api['launch_pattern'](0, ctx['tissue'])[None]+ctx['tissue'].copy_jitter*random.standard_normal((1, 16, 16))
    state = np.stack((v, v.copy(), v.copy(), native[None].copy()))
    initial = state[:, 0].copy()
    for _ in range(cfg.settle):
        state = old.advance(ctx, state, random, 0., cfg)
    founder = state[:, 0].copy(); digests = [random.digest()]
    cuts, ends, masks = [], [], []
    for cycle in range(1, cfg.cycles):
        random = Noise(index, life, f'cycle_{cycle}')
        state, fresh = old.cut(ctx, state, random)
        cuts.append(state[:, 0].copy()); masks.append(fresh[0].copy())
        for _ in range(cfg.inter_fission):
            state = old.advance(ctx, state, random, 1., cfg)
        ends.append(state[:, 0].copy()); digests.append(random.digest())
    random = Noise(index, life, f'cycle_{cfg.cycles}')
    state, fresh = old.cut(ctx, state, random); masks.append(fresh[0].copy())
    return dict(initial=initial, founder=founder, target=np.sign(founder[0]),
                prefix_cuts=np.stack(cuts), prefix_ends=np.stack(ends), fresh=np.stack(masks),
                last_cut=state[:, 0].copy(), native=native), digests, random


def execute(index, *, root, cfg=CONFIG):
    root = external_root(root); old.source.preflight(root)
    if type(index) is not int or index < 0 or cfg.replicates != 2:
        raise ValueError('integer tissue and two reciprocal lineages required')
    ctx = old.context(index)
    parents, rngs, futures = [], [], []
    for life in range(2):
        result, digests, random = parent(ctx, life, cfg)
        parents.append(result); rngs.append(digests); futures.append(random)
    np.testing.assert_array_equal(parents[0]['native'], parents[1]['native'])
    raw = {key: np.stack([row[key] for row in parents]) for key in parents[0] if key != 'native'}
    raw['native'] = parents[0]['native']
    raw['records'], raw['permutations'] = make_records(raw['last_cut'], raw['native'], index)
    raw['geometry'] = geometry(raw['records'])
    raw['ever'] = np.any(raw['fresh'], axis=1)
    raw['target_disagreement'] = ((raw['target'] > 0) != (raw['target'][::-1] > 0)) & raw['ever']
    states, values, prefix = [], [], []
    for life in range(2):
        saved = children(ctx, raw['last_cut'][life], raw['records'][life], futures[life], cfg)
        states.append(saved); rngs[life].append(futures[life].digest())
        values.append(measure(saved[:, 0], raw['target'][life], raw['target'][1-life],
                              raw['ever'][life], raw['fresh'][life, -1], cfg))
        mask = np.zeros((16, 16), bool); rows = []
        for cycle in range(cfg.cycles-1):
            mask |= raw['fresh'][life, cycle]
            rows.append(measure(raw['prefix_ends'][life, cycle, 0], raw['target'][life],
                                raw['target'][1-life], mask, raw['fresh'][life, cycle], cfg))
        prefix.append(rows)
    raw.update(descendants=np.stack(states), values=np.stack(values), prefix_values=np.array(prefix),
        prefix_age_fissions=np.arange(1, cfg.cycles), descendant_age_fissions=np.full(len(cfg.times), cfg.cycles),
        descendant_age_updates=(cfg.cycles-1)*cfg.inter_fission+np.array(cfg.times))
    meta = dict(schema='l21_record_specificity_block_v1', tissue=index, config=asdict(cfg), seed_tag=TAG,
        donor_by_life=[1, 0], rng_final=rngs, result_bytes=sum(x.nbytes for x in raw.values()),
        inherited_V_fragment=True, R_zero_can_relearn=True)
    if any(not np.isfinite(x).all() for x in raw.values()):
        raise ValueError('nonfinite retained block; no automatic retry')
    return raw, meta


def analysis_contract():
    tag = TAG+':primary-bootstrap'
    return dict(primary=PRIMARY, primary_metric='ever_amplitude', primary_sweep=500,
        target_age_fissions=8, target_age_updates=4000, tissue_blocks=8, lives_per_block=2,
        donor_pairing=[1, 0], bootstrap_unit='tissue', bootstrap_draws=20000, bootstrap_tag=tag,
        bootstrap_seed=int.from_bytes(hashlib.sha256(tag.encode()).digest()[:16], 'little'),
        bootstrap_generator='PCG64', quantiles=[.025, .975], method='linear',
        secondary_intervals=False, scientific_pass_threshold=None)


def endpoint(raw, meta):
    if canonical_digest(meta['config']) != canonical_digest(asdict(CONFIG)):
        raise ValueError('full frozen configuration required')
    np.testing.assert_array_equal(raw['descendant_age_fissions'], [8]*5)
    np.testing.assert_array_equal(raw['descendant_age_updates'], [3500, 3501, 3550, 3750, 4000])
    if raw['values'].shape != (2, 5, 2, 5, 10):
        raise ValueError('all declared checkpoint values required')
    row = dict(tissue=meta['tissue'], seed_tag=meta['seed_tag'], config_digest=canonical_digest(meta['config']),
               sweep=500, age_fissions=8, age_updates=4000, values=raw['values'][:, -1].copy())
    validate_endpoint(row)
    return row


def validate_endpoint(row):
    if set(row) != {'tissue', 'seed_tag', 'config_digest', 'sweep', 'age_fissions', 'age_updates', 'values'}:
        raise ValueError('exact endpoint schema required')
    if type(row['tissue']) is not int or row['tissue'] not in TISSUES:
        raise ValueError('main tissue identity required')
    if row['seed_tag'] != TAG or row['config_digest'] != canonical_digest(asdict(CONFIG)):
        raise ValueError('wrong endpoint provenance')
    for key, expected in (('sweep', 500), ('age_fissions', 8), ('age_updates', 4000)):
        if type(row[key]) is not int or row[key] != expected:
            raise ValueError('wrong endpoint age')
    v = row['values']
    if not isinstance(v, np.ndarray) or v.shape != (2, 2, 5, 10) or v.dtype != np.float64 or not np.isfinite(v).all():
        raise ValueError('finite complete float64 endpoint required')
    if np.any((v[..., [0, 1, 2, 4, 5, 6]] < 0) | (v[..., [0, 1, 2, 4, 5, 6]] > 1)):
        raise ValueError('invalid fidelity range')
    if np.any(abs(v[..., [3, 7]]) > 2) or np.any(abs(v[..., 8]) > 1) or np.any(abs(v[..., 9]) > 4):
        raise ValueError('invalid signed metric range')
    if np.any(v[..., 0] > v[..., 2]) or np.any(v[..., 4] > v[..., 5]):
        raise ValueError('invalid amplitude/sign relationship')
    np.testing.assert_allclose(v[..., 8:10], v[..., [0, 3]]-v[..., [6, 7]], rtol=0, atol=1e-14)


def summarize(rows):
    rows = list(rows)
    if len(rows) != 8:
        raise ValueError('all eight paired-lineage blocks required')
    by_id = {}
    for row in rows:
        validate_endpoint(row)
        if row['tissue'] in by_id:
            raise ValueError('duplicate block')
        by_id[row['tissue']] = row['values']
    x = np.stack([by_id[t] for t in TISSUES])
    block = x.mean(1); effects = {}
    for bg, name in enumerate(BACKGROUNDS):
        for j, record in enumerate(RECORDS[1:], 1):
            lives = x[:, :, bg, 0]-x[:, :, bg, j]; blocks = lives.mean(1)
            result = dict(per_life=lives.tolist(), per_tissue=blocks.tolist(), mean=blocks.mean(0).tolist())
            for unit, values, axes in (('tissues', blocks, (0,)), ('lives', lives, (0, 1))):
                for direction, mask in (('positive', values > 0), ('negative', values < 0), ('tied', values == 0)):
                    result[f'{direction}_{unit}'] = mask.sum(axes).tolist()
            effects[f'own_minus_{record}/{name}'] = result
    cfg = analysis_contract(); rng = np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    indices = rng.integers(0, 8, (20000, 8), dtype=np.int64)
    blocks = np.array(effects[PRIMARY]['per_tissue'])[:, 0]
    boot = blocks[indices].mean(1)
    return dict(schema='l21_record_specificity_summary_v1', analysis=cfg, tissues=list(TISSUES),
        backgrounds=list(BACKGROUNDS), records=list(RECORDS), metrics=list(METRICS),
        absolute=dict(per_life=x.tolist(), per_tissue=block.tolist(), mean=block.mean(0).tolist()),
        contrasts=effects, primary=dict(mean=float(blocks.mean()), interval95=np.quantile(boot, [.025, .975], method='linear').tolist(),
        bootstrap_means=boot.tolist(), draw_indices_sha256=hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest()))


def checker():
    spec = importlib.util.spec_from_file_location('d095_checker', WS/SCIENCE[1])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def contract():
    return dict(run_id=RUN_ID, decision='D095', tag=TAG, config=asdict(CONFIG), tissues=list(TISSUES),
        disposable=DISPOSABLE, rate=1., records=list(RECORDS), backgrounds=list(BACKGROUNDS),
        metrics=list(METRICS), geometry=list(GEOMETRY), donor_by_life=[1, 0], founders=16,
        parent_prefixes=16, final_futures=160, target_age_fissions=8, target_age_updates=4000,
        primary=PRIMARY, analysis=analysis_contract(), baseline_run=old.RUN_ID,
        matched_wrong_lineage_same_tissue=True, shuffle_preserves_exact_histogram=True,
        reversal_exact=True, normalize_transplants=False, donor_selection_by_outcomes=False,
        geometry_is_secondary=True, backgrounds_not_a_full_writer_R_factorial=True,
        inherited_V_fragment=True, R_zero_can_relearn=True, renewal_test=False,
        evolution=False, target_depth_sweep=False, max_cpus=4, detach_above_seconds=600,
        reserve_bytes=old.source.RESERVE, allowance_bytes=old.source.ALLOWANCE,
        output_names=list(output_names()), source_alias_lives=16,
        source_alias_cells=64, output_hash_count=19, alias_futures_per_block=40,
        forecast='8*checked_block_seconds+anchor_seconds+2*hash_seconds+180',
        storage_forecast='8*(raw_block_bytes+metadata_bytes+4096)+32MiB',
        benchmark_files=['block.npz', 'block.json', 'checks.json', 'anchors.npz', 'anchorchecks.json'],
        automatic_retry=False, automatic_followup=False)


def output_names():
    return tuple(f'block_{t}.{ext}' for t in TISSUES for ext in ('npz', 'json'))+(
        'summary.json', 'verification.json', 'input_hashes.sha256')


def baseline_paths(root):
    control = root/'runs'/old.RUN_ID
    assert sha256_file(control/'COMPLETE.json') == OLD_COMPLETE_SHA, 'D094 completion identity changed'
    assert old.checker().check_saved(root)['passed']
    original = io.verify_manifest(root)
    out = root/'outputs'/old.RUN_ID
    return sorted(set([Path(x) for x in original['input_sha256']] +
        [out/n for n in (*io.output_names(), 'output_hashes.sha256')] +
        [control/n for n in ('MANIFEST.json', 'STATUS.json', 'COMPLETE.json')] +
        [WS/'reviews/L21_PAIRED_FITNESS_2026-09-11.md']))


def test_proof(path, root):
    path = require_beneath(path, root/'logs')
    if path.is_symlink() or not path.name.startswith('d095_') or path.suffix != '.xml':
        raise ValueError('external D095 JUnit report required')
    report = ET.parse(path).getroot(); cases = report.findall('.//testcase')
    assert cases and not any(report.findall('.//'+tag) for tag in ('failure', 'error', 'skipped'))
    assert len({(c.get('classname'), c.get('name')) for c in cases}) == len(cases)
    own = {c.get('name') for c in cases if c.get('classname', '').endswith('test_l21_record_specificity')}
    assert {'test_dynamic_independent_replay', 'test_dynamic_singleton_and_order_aliases',
            'test_dynamic_saved_reload', 'test_dynamic_checker_independent_of_production'} <= own
    assert len(own) >= 60
    return dict(path=str(path), tests=len(cases), d095_tests=len(own), failed=0, skipped=0,
                required_dynamics=4)


def freeze_path(root):
    return root/'tmp'/f'{RUN_ID}_freeze.json'


def timing_path(root):
    return root/'tmp'/f'{RUN_ID}_benchmark.json'


def freeze(root, report):
    old.source.preflight(root)
    for path in (freeze_path(root), timing_path(root), root/'tmp'/f'{RUN_ID}_benchmark',
                 root/'runs'/RUN_ID, root/'outputs'/RUN_ID):
        if path.exists():
            raise FileExistsError('immutable attempt already reserved')
    proof = test_proof(report, root)
    inputs = io.hashes([*baseline_paths(root), *(WS/x for x in SCIENCE), Path(proof['path'])])
    record = dict(contract=contract(), input_sha256=inputs, test_proof=proof,
        frozen_utc=utc_now(), main_outcomes_seen=False, environment=environment_manifest())
    io.write_json(freeze_path(root), record, root)
    print(json.dumps(dict(status='FROZEN', input_files=len(inputs))), flush=True)
    return record


def frozen_inputs(root):
    record = io.read_json(freeze_path(root))
    assert canonical_digest(record['contract']) == canonical_digest(contract())
    assert record['main_outcomes_seen'] is False and record['environment'] == environment_manifest()
    proof = test_proof(Path(record['test_proof']['path']), root)
    assert record['test_proof'] == proof
    current = io.hashes([*baseline_paths(root), *(WS/x for x in SCIENCE), Path(proof['path'])])
    assert record['input_sha256'] == current, 'frozen input drift'
    return current


def aliases(raw, meta, ctx, cfg):
    """Each record alone, then reversed ordering; full checkpoints bit-exact."""
    count = 0
    for life in range(2):
        for order in ((0,), (1,), (2,), (3,), (4,), (4, 3, 2, 1, 0)):
            random = Noise(ctx['index'], life, f'cycle_{cfg.cycles}')
            state, fresh = old.cut(ctx, raw['prefix_ends'][life, -1, :, None], random)
            np.testing.assert_array_equal(state[:, 0], raw['last_cut'][life])
            np.testing.assert_array_equal(fresh[0], raw['fresh'][life, -1])
            saved = children(ctx, state[:, 0], np.take(raw['records'][life], order, axis=0), random, cfg)
            np.testing.assert_array_equal(saved, np.take(raw['descendants'][life], order, axis=3))
            assert random.digest() == meta['rng_final'][life][-1]
            count += 2*len(order)
    assert count == 40
    return count


def anchors(root):
    old.source.preflight(root); started = time.monotonic(); raw = {}
    for tissue in old.TISSUES:
        for life in range(2):
            path = root/'outputs'/old.RUN_ID/f'pair_{tissue}_{life}'
            original = io.load_npz(path.with_suffix('.npz')); meta = io.read_json(path.with_suffix('.json'))
            ctx = old.context(tissue); random = old.SharedNoise(tissue, life, 'cycle_8')
            cut, fresh = old.cut(ctx, original['prefix_ends'][-1, :, 2:3], random)
            np.testing.assert_array_equal(cut[:, 0], original['last_cut'][:, 2])
            np.testing.assert_array_equal(fresh[0], original['fresh'][-1])
            records = np.stack((cut[3, 0], original['native']))
            raw[f'life_{tissue}_{life}'] = children(ctx, cut[:, 0], records, random)
            assert random.digest() == meta['rng_final'][-1]
    record = dict(known_lives=16, exact_cells=64, rng_exact=True, main_pool=False,
                  seconds=time.monotonic()-started)
    assert checker().check_anchors(raw, record, root)
    return raw, record


def checked_block(root, directory, stem, tissue):
    started = time.monotonic(); raw, meta = execute(tissue, root=root)
    io.write_npz(directory/f'{stem}.npz', raw, root); io.write_json(directory/f'{stem}.json', meta, root)
    saved = io.load_npz(directory/f'{stem}.npz'); metadata = io.read_json(directory/f'{stem}.json')
    for name in raw:
        np.testing.assert_array_equal(raw[name], saved[name])
    assert canonical_digest(metadata) == canonical_digest(meta)
    check = checker(); ctx = old.context(tissue)
    assert check.check_schema(saved, metadata, tissue, CONFIG)
    error = check.replay(saved, metadata, ctx, CONFIG, root=root)
    count = aliases(saved, metadata, ctx, CONFIG)
    return dict(tissue=tissue, replay_max_abs=error, alias_futures=count, saved_metrics_checked=True,
        full_replay=True, seconds=time.monotonic()-started, raw_bytes=sum(x.nbytes for x in saved.values()),
        metadata_bytes=(directory/f'{stem}.json').stat().st_size)


def forecast(seconds, anchor_seconds, hash_seconds, raw_bytes, metadata_bytes):
    if not all(np.isfinite(x) and x > 0 for x in (seconds, anchor_seconds, hash_seconds, raw_bytes, metadata_bytes)):
        raise ValueError('positive finite timing and sizes required')
    duration = 8*seconds+anchor_seconds+2*hash_seconds+180
    size = 8*(raw_bytes+metadata_bytes+4096)+32*1024**2
    if size > old.source.ALLOWANCE:
        raise RuntimeError('fixed storage allowance exceeded')
    return dict(projected_seconds=duration, projected_bytes=size, must_detach=duration > 600,
                forecast_does_not_credit_parallel_speedup=True)


def benchmark(root):
    old.source.preflight(root)
    if timing_path(root).exists():
        raise FileExistsError('immutable benchmark exists')
    start = time.monotonic(); inputs = frozen_inputs(root); hash_seconds = time.monotonic()-start
    directory = require_beneath(root/'tmp'/f'{RUN_ID}_benchmark', root); directory.mkdir()
    try:
        row = checked_block(root, directory, 'block', DISPOSABLE)
        io.write_json(directory/'checks.json', row, root)
        raw, record = anchors(root)
        io.write_npz(directory/'anchors.npz', raw, root); io.write_json(directory/'anchorchecks.json', record, root)
        assert checker().check_anchors(io.load_npz(directory/'anchors.npz'), io.read_json(directory/'anchorchecks.json'), root)
        timing = dict(run_id=RUN_ID, completed_utc=utc_now(), disposable=DISPOSABLE, effects_not_reported=True,
            checked_block=row, anchors=record, hash_seconds=hash_seconds, input_sha256=inputs,
            freeze_sha256=sha256_file(freeze_path(root)), files=io.hashes(list(directory.iterdir())),
            **forecast(row['seconds'], record['seconds'], hash_seconds, row['raw_bytes'], row['metadata_bytes']))
        assert inputs == frozen_inputs(root)
        io.write_json(timing_path(root), timing, root)
        print(json.dumps({k: timing[k] for k in ('projected_seconds', 'must_detach', 'projected_bytes')}), flush=True)
        return timing
    except Exception as error:
        io.failure(directory, error, root)
        raise


def validate_timing(root, timing, inputs):
    assert timing['run_id'] == RUN_ID and timing['disposable'] == DISPOSABLE
    assert timing['effects_not_reported'] is True and timing['freeze_sha256'] == sha256_file(freeze_path(root))
    assert timing['input_sha256'] == inputs
    directory = root/'tmp'/f'{RUN_ID}_benchmark'
    assert {x.name for x in directory.iterdir()} == {'block.npz', 'block.json', 'checks.json', 'anchors.npz', 'anchorchecks.json'}
    assert timing['files'] == io.hashes(list(directory.iterdir()))
    row = io.read_json(directory/'checks.json'); record = io.read_json(directory/'anchorchecks.json')
    assert timing['checked_block'] == row and timing['anchors'] == record
    raw, meta = io.load_npz(directory/'block.npz'), io.read_json(directory/'block.json')
    assert checker().check_schema(raw, meta, DISPOSABLE, CONFIG)
    assert checker().check_row(row, DISPOSABLE, sum(x.nbytes for x in raw.values()), (directory/'block.json').stat().st_size)
    assert checker().check_anchors(io.load_npz(directory/'anchors.npz'), record, root)
    for key, value in forecast(row['seconds'], record['seconds'], timing['hash_seconds'], row['raw_bytes'], row['metadata_bytes']).items():
        assert timing[key] == value
    return True


def prepare(root):
    old.source.preflight(root); run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError('immutable main attempt exists')
    inputs = frozen_inputs(root); timing = io.read_json(timing_path(root))
    assert validate_timing(root, timing, inputs)
    inputs = inputs | timing['files'] | io.hashes([freeze_path(root), timing_path(root)])
    manifest = dict(contract=contract(), input_sha256=inputs, hash_contract=canonical_digest(inputs),
        timing=timing, environment=environment_manifest(), prepared_utc=utc_now())
    require_beneath(run, root).mkdir(); require_beneath(out, root).mkdir()
    io.write_json(run/'MANIFEST.json', manifest, root)
    with (out/'input_hashes.sha256').open('x') as handle:
        handle.write(io.hash_text(inputs))
    io.write_json(run/'STATUS.json', dict(status='PREPARED', run_id=RUN_ID), root)
    print(json.dumps(dict(status='PREPARED', input_files=len(inputs), **{k: timing[k]
        for k in ('projected_seconds', 'must_detach', 'projected_bytes')})), flush=True)
    return manifest


def verify_manifest(root):
    manifest = io.read_json(root/'runs'/RUN_ID/'MANIFEST.json')
    assert canonical_digest(manifest['contract']) == canonical_digest(contract())
    assert manifest['environment'] == environment_manifest()
    inputs = frozen_inputs(root); timing = io.read_json(timing_path(root))
    assert manifest['timing'] == timing and validate_timing(root, timing, inputs)
    inputs = inputs | timing['files'] | io.hashes([freeze_path(root), timing_path(root)])
    assert manifest['input_sha256'] == inputs and manifest['hash_contract'] == canonical_digest(inputs)
    assert (root/'outputs'/RUN_ID/'input_hashes.sha256').read_text() == io.hash_text(inputs)
    return manifest


def prepared(root):
    manifest = verify_manifest(root); run = root/'runs'/RUN_ID
    assert io.read_json(run/'STATUS.json') == dict(status='PREPARED', run_id=RUN_ID)
    assert not any((run/n).exists() for n in ('COMPLETE.json', 'FAILED.json', 'EXECUTION.lock'))
    assert {x.name for x in (root/'outputs'/RUN_ID).iterdir()} == {'input_hashes.sha256'}
    return manifest


def detach(root):
    old.source.preflight(root); manifest = prepared(root); run = root/'runs'/RUN_ID
    (run/'LAUNCH.lock').mkdir()
    logs = [root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout', 'stderr')]
    with logs[0].open('xb') as stdout, logs[1].open('xb') as stderr:
        child = subprocess.Popen([sys.executable, '-m', 'laws_confirmation.l21_record_specificity',
            '--external-root', str(root), '--run'], cwd=WS, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True)
    record = dict(pid=child.pid, launched_utc=utc_now(), polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'], status=str(run/'STATUS.json'),
        stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    io.write_json(run/'LAUNCH.json', record, root); print(json.dumps(record, indent=2), flush=True)
    return record


def detached_guard(root, required):
    if required:
        if not (root/'runs'/RUN_ID/'LAUNCH.lock').is_dir() or os.getsid(0) != os.getpid():
            raise RuntimeError('new-session detached launch required; lock alone is insufficient')
        if Path('/proc/self/fd/0').resolve() != Path('/dev/null'):
            raise RuntimeError('detached stdin must be /dev/null')
        for fd, kind in ((1, 'stdout'), (2, 'stderr')):
            if Path(f'/proc/self/fd/{fd}').resolve() != root/'logs'/f'{RUN_ID}.{kind}.log':
                raise RuntimeError('detached output must use declared external logs')


def worker(root, tissue):
    return checked_block(root, root/'outputs'/RUN_ID, f'block_{tissue}', tissue)


def run_experiment(root):
    old.source.preflight(root); manifest = prepared(root)
    detached_guard(root, manifest['timing']['must_detach'])
    run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        checks = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            pending = {pool.submit(worker, root, t): t for t in TISSUES}
            try:
                for future in as_completed(pending):
                    tissue = pending[future]; checks[tissue] = future.result()
                    old.source.preflight(root, starting=False)
                    old.source.strict_json(run/'STATUS.json', dict(status='RUNNING', run_id=RUN_ID,
                        checked_blocks=len(checks), updated_utc=utc_now()), root)
                    print(f'D095 block {tissue}: saved full replay and 40 alias futures pass', flush=True)
            except Exception:
                for future in pending:
                    future.cancel()
                raise
        assert set(checks) == set(TISSUES)
        rows = [endpoint(io.load_npz(out/f'block_{t}.npz'), io.read_json(out/f'block_{t}.json')) for t in TISSUES]
        io.write_json(out/'summary.json', summarize(rows), root)
        io.write_json(out/'verification.json', dict(schema='l21_record_specificity_checks_v1',
            rows=[checks[t] for t in TISSUES], checked_blocks=8, independent_replays=8,
            alias_futures=320, checked_utc=utc_now()), root)
        audit = checker().check_saved(root, complete=False)
        paths = [out/n for n in output_names()]; current = io.hashes(paths)
        with (out/'output_hashes.sha256').open('x') as handle:
            handle.write(io.hash_text(current))
        size = sum(x.stat().st_size for x in out.iterdir())
        assert size <= manifest['timing']['projected_bytes'] <= old.source.ALLOWANCE
        old.source.preflight(root, starting=False)
        status = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
            output_bytes=size, output_sha256=current, manifest_sha256=sha256_file(run/'MANIFEST.json'),
            hash_file_sha256=sha256_file(out/'output_hashes.sha256'), saved_audit=audit)
        io.write_json(run/'COMPLETE.json', status, root); old.source.strict_json(run/'STATUS.json', status, root)
        print(json.dumps({k: status[k] for k in ('status', 'elapsed_seconds', 'output_bytes', 'saved_audit')}, indent=2), flush=True)
        return 0
    except Exception as error:
        io.failure(run, error, root)
        old.source.strict_json(run/'STATUS.json', dict(status='FAILED', run_id=RUN_ID,
            error=str(error), automatic_retry=False), root)
        raise


def main():
    if sys.flags.optimize:
        raise RuntimeError('optimized Python disables audit assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path, required=True)
    parser.add_argument('--test-report', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze', 'benchmark', 'prepare', 'run', 'detach', 'audit'):
        group.add_argument('--'+name, action='store_true')
    args = parser.parse_args(); root = external_root(args.external_root)
    if args.freeze != (args.test_report is not None):
        parser.error('--test-report required only with --freeze')
    if args.audit:
        print(json.dumps(checker().check_saved(root), indent=2)); return 0
    if args.freeze:
        freeze(root, args.test_report); return 0
    for name in ('benchmark', 'prepare', 'run', 'detach'):
        if getattr(args, name):
            result = (run_experiment if name == 'run' else globals()[name])(root)
            return result if type(result) is int else 0


if __name__ == '__main__':
    raise SystemExit(main())
