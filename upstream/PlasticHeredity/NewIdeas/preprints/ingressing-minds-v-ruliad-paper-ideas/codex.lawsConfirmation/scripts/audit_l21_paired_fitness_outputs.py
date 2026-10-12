"""D094 independent replay, metric, pooling and saved-output checks.

Reuses D086's already-restated sheet equations, not the production step,
writer, cut, boundary builder, metric or contrast implementation. The saved
audit shares strict I/O/provenance helpers, but rebuilds endpoint records
and arithmetic from raw arrays rather than trusting the production pool.
"""

from dataclasses import asdict
import hashlib
from itertools import product

import numpy as np

from laws_confirmation import l24_descendant_pilot as source
from laws_confirmation.io import canonical_digest, external_root


def generator(index, replicate, phase):
    digest = hashlib.sha256(f'l21-paired-fitness-v1:{index}:{replicate}:{phase}'.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], 'little'))


def metric(v, target, ever, fresh):
    result = np.empty((*v.shape[:-2], 6), float)
    for index in np.ndindex(v.shape[:-2]):
        x = v[index]; correct = (x > 0) == (target > 0); active = abs(x) > .2
        result[index] = (np.count_nonzero((correct & active) & ever)/ever.sum(),
                         np.count_nonzero((correct & active) & fresh)/fresh.sum(),
                         np.count_nonzero(correct & ever)/ever.sum(),
                         np.sum((x*target)[ever])/ever.sum(),
                         np.count_nonzero(correct & active)/256., np.count_nonzero(active)/256.)
    return result


def check_metrics(raw):
    ever = np.zeros((16, 16), bool)
    for i, end in enumerate(raw['prefix_ends']):
        ever |= raw['fresh'][i]
        np.testing.assert_allclose(raw['prefix_scores'][i],
            metric(end[0], raw['target'], ever, raw['fresh'][i]), rtol=0, atol=1e-14)
    ever |= raw['fresh'][-1]
    np.testing.assert_array_equal(ever, raw['ever'])
    for i, state in enumerate(raw['descendants']):
        np.testing.assert_allclose(raw['descendant_scores'][i],
            metric(state[0], raw['target'], ever, raw['fresh'][-1]), rtol=0, atol=1e-14)
    return True


def check_boundary(raw):
    birth = raw['descendants'][0]
    for arm, (theta, writer, ref) in enumerate(product(range(2), repeat=3)):
        np.testing.assert_array_equal(birth[:2, :, arm], raw['last_cut'][:2])
        expected_r = raw['last_cut'][2] if ref == 0 else np.zeros((3, 16, 16))
        expected_t = raw['last_cut'][3] if theta == 0 else np.broadcast_to(raw['native'], (3, 16, 16))
        np.testing.assert_array_equal(birth[2, :, arm], expected_r)
        np.testing.assert_array_equal(birth[3, :, arm], expected_t)
        if writer == 1:
            for state in raw['descendants']:
                np.testing.assert_array_equal(state[3, :, arm], expected_t)
    np.testing.assert_array_equal(raw['last_cut'][3], raw['prefix_ends'][-1, 3])
    np.testing.assert_array_equal(raw['last_cut'][2], raw['prefix_ends'][-1, 2])
    np.testing.assert_array_equal(raw['last_cut'][1], raw['last_cut'][0])
    return True


def check_contrasts(scores, rows):
    expected = {}
    arms = tuple(product(range(2), repeat=3))
    rates = (.001, .2, 1.)
    for i, u in enumerate(rates):
        cells = {a: scores[..., i, j, :] for j, a in enumerate(arms)}
        for axis, name, other in ((0, 'theta', ('writer', 'R')),
                                  (1, 'writer', ('theta', 'R')),
                                  (2, 'R', ('theta', 'writer'))):
            for a, b in product(range(2), repeat=2):
                intact = [a, b]; intact.insert(axis, 0)
                control = intact.copy(); control[axis] = 1
                key = f'{name}/u={u}/{other[0]}={a}/{other[1]}={b}'
                expected[key] = cells[tuple(intact)]-cells[tuple(control)]
        for ref in range(2):
            expected[f'theta_x_writer/u={u}/R={ref}'] = (
                cells[(0, 0, ref)]-cells[(1, 0, ref)]-cells[(0, 1, ref)]+cells[(1, 1, ref)])
    for i in (1, 2):
        expected[f'rate/u={rates[i]}_minus_0.001/intact'] = scores[..., i, 0, :]-scores[..., 0, 0, :]
    assert set(rows) == set(expected)
    for key in rows:
        np.testing.assert_array_equal(rows[key], expected[key])
    return True


def check_summary(records, result):
    """Rebuild block pooling and uncertainty without the production analyzer.

    Main identities are checked separately from arithmetic. No physics, file
    output or simulation entry point is called by this synthetic-testable check.
    """
    identities = tuple(product(range(41000, 41008), range(2)))
    config = dict(replicates=2, settle=120, cycles=8, inter_fission=500,
                  times=[0, 1, 50, 250, 500], rho=.002, norm=.3, amp_threshold=.2)
    seed = int.from_bytes(hashlib.sha256(b'l21-paired-fitness-v1:primary-bootstrap').digest()[:16], 'little')
    settings = dict(endpoint_schema='l21_paired_fitness_final_scores_v1',
        primary_contrast='theta/u=1.0/writer=0/R=0', primary_metric='ever_amplitude',
        primary_sweep=500, target_age_fissions=8, target_age_updates=4000,
        tissue_blocks=8, lives_per_block=2, bootstrap_unit='tissue', bootstrap_draws=20000,
        bootstrap_tag='l21-paired-fitness-v1:primary-bootstrap', bootstrap_seed=seed,
        bootstrap_generator='PCG64', quantiles=[.025, .975], quantile_method='linear',
        secondary_intervals=False, tie_rule='exact_zero', scientific_pass_threshold=None,
        source_controls_in_main_pool=False, incomplete_panels_allowed=False, analysis_validation_atol=1e-14)
    assert set(result) == {'schema', 'analysis', 'unit_order', 'axes', 'absolute', 'contrasts', 'primary'}
    assert result['schema'] == 'l21_paired_fitness_summary_v1' and result['analysis'] == settings
    assert result['unit_order'] == [dict(tissue=t, replicate=r) for t, r in identities]
    assert result['axes'] == dict(rates=[.001, .2, 1.],
        arms=[list(a) for a in product(('copy', 'native'), ('on', 'off'), ('copy', 'zero'))],
        metrics=['ever_amplitude', 'fresh_amplitude', 'ever_sign', 'ever_projection', 'whole_amplitude', 'active_fraction'])
    records = list(records); assert len(records) == 16
    by_id = {}
    for row in records:
        assert set(row) == {'schema', 'seed_tag', 'tissue', 'replicate', 'config_digest',
                            'sweep', 'target_age_fissions', 'target_age_updates', 'scores'}
        assert row['schema'] == 'l21_paired_fitness_final_scores_v1'
        assert row['seed_tag'] == 'l21-paired-fitness-v1' and row['config_digest'] == canonical_digest(config)
        for key, choices in (('tissue', range(41000, 41008)), ('replicate', range(2)),
                             ('sweep', [500]), ('target_age_fissions', [8]), ('target_age_updates', [4000])):
            assert type(row[key]) is int and row[key] in choices
        address = row['tissue'], row['replicate']
        assert address not in by_id
        x = row['scores']
        assert isinstance(x, np.ndarray) and x.shape == (3, 8, 6) and x.dtype == np.float64
        assert np.isfinite(x).all()
        for metric_index in (0, 1, 2, 4, 5):
            assert np.min(x[..., metric_index]) >= 0 and np.max(x[..., metric_index]) <= 1
        assert np.max(abs(x[..., 3])) <= 2
        assert np.all(x[..., 0] <= x[..., 2]) and np.all(x[..., 4] <= x[..., 5])
        by_id[address] = x
    assert set(by_id) == set(identities)
    x = np.array([[by_id[(t, r)] for r in range(2)] for t in range(41000, 41008)])

    def compare(actual, expected, *, exact=False):
        actual = np.asarray(actual); expected = np.asarray(expected)
        assert actual.shape == expected.shape and np.isfinite(actual).all() and np.isfinite(expected).all()
        if exact:
            np.testing.assert_array_equal(actual, expected)
        else:
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-14)

    blocks = (x[:, 0]+x[:, 1])/2.
    assert set(result['absolute']) == {'per_life', 'per_tissue', 'mean'}
    compare(result['absolute']['per_life'], x, exact=True)
    compare(result['absolute']['per_tissue'], blocks)
    compare(result['absolute']['mean'], sum(blocks)/8.)
    raw_effects = {name: np.array(row['per_life']) for name, row in result['contrasts'].items()}
    assert check_contrasts(x, raw_effects)
    for name, effects in raw_effects.items():
        block_effects = (effects[:, 0]+effects[:, 1])/2.
        row = result['contrasts'][name]
        assert set(row) == {'per_life', 'per_tissue', 'mean', 'positive_tissues', 'negative_tissues',
                            'tied_tissues', 'positive_lives', 'negative_lives', 'tied_lives'}
        compare(row['per_tissue'], block_effects)
        compare(row['mean'], sum(block_effects)/8.)
        for label, maximum in (('tissues', 8), ('lives', 16)):
            for direction in ('positive', 'negative', 'tied'):
                values = row[f'{direction}_{label}']
                assert isinstance(values, list) and len(values) == 6
                assert all(type(v) is int and 0 <= v <= maximum for v in values)
        for metric_index in range(6):
            for label, data in (('tissues', block_effects[:, metric_index]),
                                ('lives', effects[..., metric_index].ravel())):
                counts = dict(positive=sum(float(v) > 0 for v in data),
                              negative=sum(float(v) < 0 for v in data), tied=sum(float(v) == 0 for v in data))
                for direction, count in counts.items():
                    assert row[f'{direction}_{label}'][metric_index] == count

    primary = result['primary']
    assert set(primary) == {'contrast', 'metric', 'mean', 'interval95', 'bootstrap_means', 'draw_indices_sha256'}
    assert primary['contrast'] == 'theta/u=1.0/writer=0/R=0' and primary['metric'] == 'ever_amplitude'
    # Direct raw-cell subtraction: arm 0 is copy/on/copy, arm 4 native/on/copy.
    blocks = np.array([sum(x[b, r, 2, 0, 0]-x[b, r, 2, 4, 0] for r in range(2))/2 for b in range(8)])
    compare(primary['mean'], sum(blocks)/8.)
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = rng.integers(0, 8, (20000, 8), dtype=np.int64)
    assert primary['draw_indices_sha256'] == hashlib.sha256(draws.astype('<i8').tobytes()).hexdigest()
    # Separate arithmetic and an explicit linear order-statistic interpolation.
    bootstrap = sum(blocks[draws[:, j]] for j in range(8))/8.
    compare(primary['bootstrap_means'], bootstrap)
    ordered = np.sort(bootstrap)
    interval = []
    for q in (.025, .975):
        position = q*19999; lo = int(position); fraction = position-lo
        interval.append(ordered[lo]*(1-fraction)+ordered[lo+1]*fraction)
    compare(primary['interval95'], interval)
    return True


def replay_pair(raw, meta, ctx, cfg, *, root):
    """Independent complete prefix/descendant replay; never checkpoint-reset."""
    source.preflight(external_root(root))
    eq = source.checker(); index, rep = ctx['index'], meta['replicate']
    assert meta['tissue'] == index
    assert canonical_digest(meta['config']) == canonical_digest(asdict(cfg))
    tissue, ladder, api = ctx['tissue'], ctx['ladder'], ctx['api']
    native = eq.project(api['make_thresholds'](tissue)[None], .3)[0]
    np.testing.assert_array_equal(native, raw['native'])
    errors, rngs = [], []

    def compare(got, expected):
        assert got.shape == expected.shape and np.isfinite(got).all() and np.isfinite(expected).all()
        np.testing.assert_allclose(got, expected, rtol=0, atol=1e-10)
        np.testing.assert_array_equal(got > 0, expected > 0)
        errors.append(float(np.max(abs(got-expected))))

    def advance(state, random, rates):
        v, ema, ref, theta = state
        v, ema, ref = eq.step(v, ema, ref, theta, tissue, ladder, .2, .002,
                             random.standard_normal((1, 16, 16)))
        theta = theta.copy()
        for j, u in enumerate(np.broadcast_to(rates, (len(v),))):
            if u > 0:
                lam = u*.001
                theta[j] = eq.project((1-lam)*theta[j]+lam*np.tanh(ref[j]), .3)
        return np.stack((v, ema, ref, theta))

    def cut(state, random):
        axis = int(random.integers(0, 2, 1)[0]); side = int(random.integers(0, 2, 1)[0])
        kept = np.zeros((16, 16), bool)
        if axis == 0:
            kept[side*8:(side+1)*8, :] = True
        else:
            kept[:, side*8:(side+1)*8] = True
        v = np.where(kept, state[0], tissue.resting)
        v += tissue.copy_jitter*random.standard_normal((1, 16, 16))
        return np.stack((v, v.copy(), state[2].copy(), state[3].copy())), ~kept

    random = generator(index, rep, 'founder')
    v = api['launch_pattern'](0, tissue)[None]+tissue.copy_jitter*random.standard_normal((1, 16, 16))
    state = np.stack((v, v.copy(), v.copy(), native[None]))
    compare(raw['initial'], state[:, 0])
    for _ in range(cfg.settle):
        state = advance(state, random, 0.)
    compare(raw['founder'], state[:, 0])
    np.testing.assert_array_equal(raw['target'], np.sign(state[0, 0]))
    np.testing.assert_array_equal(raw['founder'][3], raw['native'])
    rngs.append(canonical_digest(random.bit_generator.state))
    state = np.repeat(state, 3, axis=1)
    for cycle in range(1, cfg.cycles):
        random = generator(index, rep, f'cycle_{cycle}')
        state, fresh = cut(state, random)
        compare(raw['prefix_cuts'][cycle-1], state)
        np.testing.assert_array_equal(raw['fresh'][cycle-1], fresh)
        for _ in range(cfg.inter_fission):
            state = advance(state, random, (.001, .2, 1.))
        compare(raw['prefix_ends'][cycle-1], state)
        rngs.append(canonical_digest(random.bit_generator.state))
    random = generator(index, rep, f'cycle_{cfg.cycles}')
    state, fresh = cut(state, random)
    compare(raw['last_cut'], state); np.testing.assert_array_equal(raw['fresh'][-1], fresh)
    panel = np.repeat(state[:, :, None], 8, axis=2)
    rates = []
    for i, u in enumerate((.001, .2, 1.)):
        for j, (theta, writer, ref) in enumerate(product(range(2), repeat=3)):
            if theta: panel[3, i, j] = native
            if ref: panel[2, i, j] = 0.
            rates.append(0. if writer else u)
    state = panel.reshape(4, 24, 16, 16)
    for tick in range(cfg.inter_fission+1):
        if tick:
            state = advance(state, random, rates)
        if tick in cfg.times:
            compare(raw['descendants'][cfg.times.index(tick)], state.reshape(4, 3, 8, 16, 16))
    rngs.append(canonical_digest(random.bit_generator.state))
    assert rngs == meta['rng_final']
    np.testing.assert_array_equal(raw['prefix_age_fissions'], np.arange(1, cfg.cycles))
    np.testing.assert_array_equal(raw['descendant_age_fissions'], np.full(len(cfg.times), cfg.cycles))
    np.testing.assert_array_equal(raw['descendant_age_updates'],
                                  (cfg.cycles-1)*cfg.inter_fission+np.array(cfg.times))
    assert check_boundary(raw) and check_metrics(raw)
    return max(errors)


def check_masks(masks):
    halves = []
    for axis, side in product(range(2), repeat=2):
        halves.append((np.indices((16, 16))[axis]//8) == side)
    assert masks.dtype == bool
    for mask in masks:
        assert any(np.array_equal(mask, half) for half in halves)


def check_pair_schema(raw, meta, tissue, replicate):
    """Main/full-disposable shapes, clocks and metadata; no new simulation."""
    specs = dict(initial=(4, 16, 16), founder=(4, 16, 16), native=(16, 16), target=(16, 16),
        prefix_cuts=(7, 4, 3, 16, 16), prefix_ends=(7, 4, 3, 16, 16), fresh=(8, 16, 16),
        ever=(16, 16), last_cut=(4, 3, 16, 16), descendants=(5, 4, 3, 8, 16, 16),
        prefix_scores=(7, 3, 6), descendant_scores=(5, 3, 8, 6), prefix_age_fissions=(7,),
        descendant_age_fissions=(5,), descendant_age_updates=(5,))
    assert set(raw) == set(specs)
    for name, shape in specs.items():
        dtype = bool if name in ('fresh', 'ever') else np.int64 if 'age_' in name else np.float64
        assert raw[name].shape == shape and raw[name].dtype == dtype
        assert np.isfinite(raw[name]).all()
    assert set(meta) == {'tissue', 'replicate', 'config', 'rng_final', 'common_target',
        'native_reset_is_not_zero', 'zero_R_relearns', 'inherited_body_fragment', 'result_bytes'}
    assert type(meta['tissue']) is int and meta['tissue'] == tissue
    assert type(meta['replicate']) is int and meta['replicate'] == replicate
    config = dict(replicates=2, settle=120, cycles=8, inter_fission=500,
                  times=[0, 1, 50, 250, 500], rho=.002, norm=.3, amp_threshold=.2)
    assert canonical_digest(meta['config']) == canonical_digest(config)
    for key in ('common_target', 'native_reset_is_not_zero', 'zero_R_relearns', 'inherited_body_fragment'):
        assert meta[key] is True
    assert type(meta['result_bytes']) is int and meta['result_bytes'] == sum(x.nbytes for x in raw.values())
    assert isinstance(meta['rng_final'], list) and len(meta['rng_final']) == 9
    assert all(isinstance(x, str) and len(x) == 64 and set(x) <= set('0123456789abcdef')
               for x in meta['rng_final'])
    check_masks(raw['fresh'])
    np.testing.assert_array_equal(raw['ever'], np.any(raw['fresh'], axis=0))
    np.testing.assert_array_equal(raw['target'], np.sign(raw['founder'][0]))
    np.testing.assert_array_equal(raw['founder'][3], raw['native'])
    np.testing.assert_array_equal(raw['initial'][3], raw['native'])
    np.testing.assert_array_equal(raw['initial'][1:3], np.broadcast_to(raw['initial'][0], (2, 16, 16)))
    np.testing.assert_array_equal(raw['prefix_age_fissions'], np.arange(1, 8))
    np.testing.assert_array_equal(raw['descendant_age_fissions'], [8]*5)
    np.testing.assert_array_equal(raw['descendant_age_updates'], [3500, 3501, 3550, 3750, 4000])
    return True


def check_source(raw, meta):
    """Check retained known E69 scalar bridge traces, not source field equivalence."""
    specs = dict(initial=(4, 16, 16), founder=(4, 16, 16), target=(16, 16), cuts=(8, 4, 16, 16),
                 ends=(8, 4, 16, 16), fresh=(8, 16, 16), values=(8, 6), score_age_fissions=(3,))
    assert set(raw) == set(specs)
    for name, shape in specs.items():
        dtype = bool if name == 'fresh' else np.int64 if name == 'score_age_fissions' else np.float64
        assert raw[name].shape == shape and raw[name].dtype == dtype and np.isfinite(raw[name]).all()
    assert set(meta) == {'tissue', 'u', 'replicate', 'source_fitness', 'traced_fitness',
                        'rng_final', 'source_config_digest', 'source_bridge_exact'}
    assert type(meta['tissue']) is int and meta['tissue'] == 0
    assert type(meta['replicate']) is int and meta['replicate'] in range(3)
    assert type(meta['u']) is float and meta['u'] in (.001, 1.)
    assert meta['source_config_digest'] == '00591e27961e0153932653bfb3642207f6f21ef77834960d7c20737c9f42b010'
    assert meta['source_bridge_exact'] is True
    assert isinstance(meta['rng_final'], str) and len(meta['rng_final']) == 64
    assert set(meta['rng_final']) <= set('0123456789abcdef')
    check_masks(raw['fresh'])
    np.testing.assert_array_equal(raw['score_age_fissions'], [6, 7, 8])
    np.testing.assert_array_equal(raw['target'], np.sign(raw['founder'][0]))
    ever = np.zeros((16, 16), bool)
    for i in range(8):
        previous = raw['founder'] if i == 0 else raw['ends'][i-1]
        np.testing.assert_array_equal(raw['cuts'][i, 2:], previous[2:])
        np.testing.assert_array_equal(raw['cuts'][i, 0], raw['cuts'][i, 1])
        ever |= raw['fresh'][i]
        np.testing.assert_allclose(raw['values'][i], metric(raw['ends'][i, 0], raw['target'],
                                   ever, raw['fresh'][i]), rtol=0, atol=1e-14)
    assert meta['source_fitness'] == meta['traced_fitness'] == float(raw['values'][-3:, 0].mean())
    assert 0 <= meta['source_fitness'] <= 1
    return True


def check_verification(record, identities, raw_sizes, metadata_sizes):
    assert set(record) == {'schema', 'rows', 'checked_pairs', 'independent_replays',
                           'intact_alias_orders', 'checked_utc'}
    assert record['schema'] == 'l21_paired_fitness_checks_v1'
    assert record['checked_pairs'] == record['independent_replays'] == 16
    assert record['intact_alias_orders'] == 32 and isinstance(record['checked_utc'], str)
    assert len(record['rows']) == 16
    for row, (tissue, replicate), raw_size, meta_size in zip(record['rows'], identities, raw_sizes, metadata_sizes):
        assert set(row) == {'tissue', 'replicate', 'replay_max_abs', 'intact_alias_orders',
            'saved_metrics_checked', 'full_replay', 'seconds', 'raw_bytes', 'metadata_bytes'}
        assert type(row['tissue']) is int and row['tissue'] == tissue
        assert type(row['replicate']) is int and row['replicate'] == replicate
        assert np.isfinite(row['replay_max_abs']) and 0 <= row['replay_max_abs'] <= 1e-10
        assert row['intact_alias_orders'] == 2
        assert row['saved_metrics_checked'] is True and row['full_replay'] is True
        assert np.isfinite(row['seconds']) and row['seconds'] > 0
        assert type(row['raw_bytes']) is int and row['raw_bytes'] == raw_size
        assert type(row['metadata_bytes']) is int and row['metadata_bytes'] == meta_size
    return True


def check_saved(root, *, complete=True):
    """Read-only hashes, exact saved inventory, raw metrics and independent pooling.

Full field replays were performed on each just-saved pair before its worker
reported completion; this later audit does not rerun dynamics or write files.
"""
    from laws_confirmation import l21_paired_fitness_run as run
    root = external_root(root)
    manifest = run.verify_manifest(root)
    directory = root/'outputs'/'l21_paired_fitness_v1_attempt1'
    control = root/'runs'/'l21_paired_fitness_v1_attempt1'
    identities = tuple(product(range(41000, 41008), range(2)))
    names = {f'pair_{t}_{r}.{ext}' for t, r in identities for ext in ('npz', 'json')} | {
        'summary.json', 'verification.json', 'input_hashes.sha256'}
    expected = names | ({'output_hashes.sha256'} if complete else set())
    assert {x.name for x in directory.iterdir()} == expected
    assert all(x.is_file() and not x.is_symlink() for x in directory.iterdir())
    assert not (control/'FAILED.json').exists()
    assert manifest['contract']['output_hash_count'] == len(names) == 35
    status = None
    if complete:
        status = run.read_json(control/'STATUS.json')
        assert status['status'] == 'COMPLETE' and status['run_id'] == 'l21_paired_fitness_v1_attempt1'
        assert status == run.read_json(control/'COMPLETE.json')
        current = run.hashes([directory/x for x in names])
        assert status['output_sha256'] == current
        assert (directory/'output_hashes.sha256').read_text() == run.hash_text(current)
        assert run.sha256_file(directory/'output_hashes.sha256') == status['hash_file_sha256']
        assert run.sha256_file(control/'MANIFEST.json') == status['manifest_sha256']
        assert status['output_bytes'] == sum(x.stat().st_size for x in directory.iterdir())
        assert 0 < status['output_bytes'] <= manifest['timing']['projected_bytes'] <= 512*1024**2
    records, sizes, meta_sizes = [], [], []
    for t, r in identities:
        raw = run.load_npz(directory/f'pair_{t}_{r}.npz')
        meta = run.read_json(directory/f'pair_{t}_{r}.json')
        assert check_pair_schema(raw, meta, t, r) and check_boundary(raw) and check_metrics(raw)
        records.append(dict(schema='l21_paired_fitness_final_scores_v1', seed_tag='l21-paired-fitness-v1',
            tissue=t, replicate=r, config_digest=canonical_digest(meta['config']), sweep=500,
            target_age_fissions=int(raw['descendant_age_fissions'][-1]),
            target_age_updates=int(raw['descendant_age_updates'][-1]), scores=raw['descendant_scores'][4]))
        sizes.append(sum(x.nbytes for x in raw.values()))
        meta_sizes.append((directory/f'pair_{t}_{r}.json').stat().st_size)
    assert check_verification(run.read_json(directory/'verification.json'), identities, sizes, meta_sizes)
    assert check_summary(records, run.read_json(directory/'summary.json'))
    result = dict(passed=True, input_hashes=len(manifest['input_sha256']), checked_pairs=16,
                  primary_block_count=8, contrast_arrays=44, metrics=6,
                  full_dynamics_repeated_by_saved_audit=False, saved_raw_metrics_and_pool_checked=True)
    if status is not None:
        assert status['saved_audit'] == result
    return result
