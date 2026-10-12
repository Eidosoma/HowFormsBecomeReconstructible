"""D095 independent equations, record wiring, raw metrics and paired pooling.

Shares native parameters/initialization and the D086 restated equations only.
No production parent, cut, transplant, metric or summary is used for replay.
Saved audits are read-only and do not repeat dynamics.
"""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l24_descendant_pilot as source
from laws_confirmation.io import canonical_digest, external_root

TAG = 'l21-record-specificity-v1'
RECORDS = ['own', 'native', 'other_lineage', 'shuffled', 'reversed']
BACKGROUNDS = ['live', 'held_R_zero']
METRICS = ['ever_amplitude', 'fresh_amplitude', 'ever_sign', 'ever_projection',
           'whole_amplitude', 'active_fraction', 'donor_amplitude', 'donor_projection',
           'recipient_minus_donor_amplitude', 'recipient_minus_donor_projection']


def generator(index, life, phase):
    digest = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16], 'little')))


def metric(v, target, donor, ever, fresh):
    assert ever.dtype == fresh.dtype == bool and ever.any() and fresh.any()
    assert not np.any(fresh & ~ever)
    result = np.empty((*v.shape[:-2], 10), dtype=float)
    for index in np.ndindex(v.shape[:-2]):
        x = v[index]; correct = (x > 0) == (target > 0); active = abs(x) > .2
        other = (x > 0) == (donor > 0)
        own_amp = np.count_nonzero(correct & active & ever)/ever.sum()
        own_projection = (x*target)[ever].sum()/ever.sum()
        donor_amp = np.count_nonzero(other & active & ever)/ever.sum()
        donor_projection = (x*donor)[ever].sum()/ever.sum()
        result[index] = (own_amp, np.count_nonzero(correct & active & fresh)/fresh.sum(),
            np.count_nonzero(correct & ever)/ever.sum(), own_projection,
            np.count_nonzero(correct & active)/256., np.count_nonzero(active)/256.,
            donor_amp, donor_projection, own_amp-donor_amp, own_projection-donor_projection)
    return result


def check_metrics(raw):
    for life in range(2):
        ever = np.zeros((16, 16), bool)
        for cycle, end in enumerate(raw['prefix_ends'][life]):
            ever |= raw['fresh'][life, cycle]
            np.testing.assert_allclose(raw['prefix_values'][life, cycle], metric(end[0],
                raw['target'][life], raw['target'][1-life], ever, raw['fresh'][life, cycle]), rtol=0, atol=1e-14)
        ever |= raw['fresh'][life, -1]
        np.testing.assert_array_equal(raw['ever'][life], ever)
        np.testing.assert_array_equal(raw['target_disagreement'][life],
            ((raw['target'][life] > 0) != (raw['target'][1-life] > 0)) & ever)
        np.testing.assert_allclose(raw['values'][life], metric(raw['descendants'][life, :, 0],
            raw['target'][life], raw['target'][1-life], ever, raw['fresh'][life, -1]), rtol=0, atol=1e-14)
    return True


def check_records(raw, index):
    for life in range(2):
        own = raw['last_cut'][life, 3]
        order = generator(index, life, 'shuffle').permutation(256)
        np.testing.assert_array_equal(raw['permutations'][life], order)
        expected = [own, raw['native'], raw['last_cut'][1-life, 3],
                    own.reshape(-1)[order].reshape(16, 16), -own]
        np.testing.assert_array_equal(raw['records'][life], np.array(expected))
        np.testing.assert_array_equal(np.sort(raw['records'][life, 3].ravel()), np.sort(own.ravel()))
        for j, field in enumerate(expected):
            neighbors = sum(np.roll(field, offset, axis) for axis in (0, 1) for offset in (-1, 1))/4.
            g = [field.mean(), field.std(), np.sqrt((field*field).mean()),
                 np.sqrt(np.square(field-neighbors).mean())]
            np.testing.assert_allclose(raw['geometry'][life, j], g, rtol=0, atol=1e-14)
    return True


def check_boundary(raw):
    for life in range(2):
        parent = raw['last_cut'][life]
        np.testing.assert_array_equal(parent[2:], raw['prefix_ends'][life, -1, 2:])
        np.testing.assert_array_equal(parent[1], parent[0])
        for bg in range(2):
            for rec in range(5):
                born = raw['descendants'][life, 0, :, bg, rec]
                np.testing.assert_array_equal(born[:2], parent[:2])
                np.testing.assert_array_equal(born[2], parent[2] if bg == 0 else np.zeros((16, 16)))
                np.testing.assert_array_equal(born[3], raw['records'][life, rec])
                if bg == 1:
                    for state in raw['descendants'][life]:
                        np.testing.assert_array_equal(state[3, bg, rec], raw['records'][life, rec])
    return True


def check_schema(raw, meta, index, cfg):
    c, t = cfg.cycles, len(cfg.times)
    specs = dict(initial=(2, 4, 16, 16), founder=(2, 4, 16, 16), target=(2, 16, 16),
        prefix_cuts=(2, c-1, 4, 16, 16), prefix_ends=(2, c-1, 4, 16, 16), fresh=(2, c, 16, 16),
        last_cut=(2, 4, 16, 16), native=(16, 16), records=(2, 5, 16, 16), permutations=(2, 256),
        geometry=(2, 5, 4), ever=(2, 16, 16), target_disagreement=(2, 16, 16),
        descendants=(2, t, 4, 2, 5, 16, 16), values=(2, t, 2, 5, 10), prefix_values=(2, c-1, 10),
        prefix_age_fissions=(c-1,), descendant_age_fissions=(t,), descendant_age_updates=(t,))
    assert set(raw) == set(specs)
    for name, shape in specs.items():
        dtype = bool if name in ('fresh', 'ever', 'target_disagreement') else (
            np.int64 if 'age_' in name or name == 'permutations' else np.float64)
        assert raw[name].shape == shape and raw[name].dtype == dtype and np.isfinite(raw[name]).all()
    assert set(meta) == {'schema', 'tissue', 'config', 'seed_tag', 'donor_by_life', 'rng_final',
                         'result_bytes', 'inherited_V_fragment', 'R_zero_can_relearn'}
    assert meta['schema'] == 'l21_record_specificity_block_v1' and meta['seed_tag'] == TAG
    assert type(meta['tissue']) is int and meta['tissue'] == index
    assert canonical_digest(meta['config']) == canonical_digest(asdict(cfg))
    assert meta['donor_by_life'] == [1, 0] and all(type(x) is int for x in meta['donor_by_life'])
    assert meta['inherited_V_fragment'] is True and meta['R_zero_can_relearn'] is True
    assert type(meta['result_bytes']) is int and meta['result_bytes'] == sum(x.nbytes for x in raw.values())
    assert isinstance(meta['rng_final'], list) and len(meta['rng_final']) == 2
    for row in meta['rng_final']:
        assert isinstance(row, list) and len(row) == c+1
        assert all(isinstance(x, str) and len(x) == 64 and set(x) <= set('0123456789abcdef') for x in row)
    halves = [(np.indices((16, 16))[axis]//8 == side) for axis in (0, 1) for side in (0, 1)]
    for mask in raw['fresh'].reshape(-1, 16, 16):
        assert any(np.array_equal(mask, half) for half in halves)
    np.testing.assert_array_equal(raw['target'], np.sign(raw['founder'][:, 0]))
    for life in range(2):
        np.testing.assert_array_equal(raw['initial'][life, 1:3], np.broadcast_to(raw['initial'][life, 0], (2, 16, 16)))
        for name in ('initial', 'founder'):
            np.testing.assert_array_equal(raw[name][life, 3], raw['native'])
    np.testing.assert_array_equal(raw['prefix_age_fissions'], np.arange(1, c))
    np.testing.assert_array_equal(raw['descendant_age_fissions'], np.full(t, c))
    np.testing.assert_array_equal(raw['descendant_age_updates'], (c-1)*cfg.inter_fission+np.array(cfg.times))
    assert check_records(raw, index) and check_boundary(raw) and check_metrics(raw)
    return True


def replay(raw, meta, ctx, cfg, *, root):
    source.preflight(external_root(root))
    assert check_schema(raw, meta, ctx['index'], cfg)
    eq = source.checker(); tissue = ctx['tissue']; errors = []
    native = eq.project(ctx['api']['make_thresholds'](tissue)[None], .3)[0]
    np.testing.assert_array_equal(native, raw['native'])

    def compare(got, expected):
        errors.append(eq.compare(got, expected))

    def advance(state, random, writing):
        v, ema, ref, theta = state
        v, ema, ref = eq.step(v, ema, ref, theta, tissue, ctx['ladder'], .2, .002,
                             random.standard_normal((1, 16, 16)))
        theta = theta.copy()
        for i, enabled in enumerate(np.broadcast_to(writing, (len(v),))):
            if enabled:
                theta[i] = eq.project(.999*theta[i]+.001*np.tanh(ref[i]), .3)
        return np.stack((v, ema, ref, theta))

    def cut(state, random):
        axis = int(random.integers(0, 2, 1)[0]); side = int(random.integers(0, 2, 1)[0])
        kept = np.indices((16, 16))[axis]//8 == side
        v = np.where(kept, state[0], tissue.resting)+tissue.copy_jitter*random.standard_normal((1, 16, 16))
        return np.stack((v, v.copy(), state[2].copy(), state[3].copy())), ~kept

    parents, randoms, digests = [], [], []
    for life in range(2):
        random = generator(ctx['index'], life, 'founder')
        v = ctx['api']['launch_pattern'](0, tissue)[None]+tissue.copy_jitter*random.standard_normal((1, 16, 16))
        state = np.stack((v, v.copy(), v.copy(), native[None].copy()))
        compare(raw['initial'][life], state[:, 0])
        for _ in range(cfg.settle):
            state = advance(state, random, False)
        compare(raw['founder'][life], state[:, 0]); rngs = [canonical_digest(random.bit_generator.state)]
        for cycle in range(1, cfg.cycles):
            random = generator(ctx['index'], life, f'cycle_{cycle}')
            state, fresh = cut(state, random)
            compare(raw['prefix_cuts'][life, cycle-1], state[:, 0])
            np.testing.assert_array_equal(raw['fresh'][life, cycle-1], fresh)
            for _ in range(cfg.inter_fission):
                state = advance(state, random, True)
            compare(raw['prefix_ends'][life, cycle-1], state[:, 0])
            rngs.append(canonical_digest(random.bit_generator.state))
        random = generator(ctx['index'], life, f'cycle_{cfg.cycles}')
        state, fresh = cut(state, random)
        compare(raw['last_cut'][life], state[:, 0]); np.testing.assert_array_equal(raw['fresh'][life, -1], fresh)
        parents.append(state[:, 0].copy()); randoms.append(random); digests.append(rngs)
    for life in range(2):
        own = parents[life][3]
        order = generator(ctx['index'], life, 'shuffle').permutation(256)
        records = [own, native, parents[1-life][3], own.ravel()[order].reshape(16, 16), -own]
        state = np.repeat(parents[life][:, None], 10, axis=1)
        for bg in range(2):
            for rec in range(5):
                state[3, bg*5+rec] = records[rec]
                if bg:
                    state[2, bg*5+rec] = 0.
        for tick in range(cfg.inter_fission+1):
            if tick:
                state = advance(state, randoms[life], [True]*5+[False]*5)
            if tick in cfg.times:
                compare(raw['descendants'][life, cfg.times.index(tick)], state.reshape(4, 2, 5, 16, 16))
        digests[life].append(canonical_digest(randoms[life].bit_generator.state))
    assert digests == meta['rng_final']
    return max(errors)


def check_summary(rows, result):
    tissues = list(range(42000, 42008)); by_id = {}
    config = dict(replicates=2, settle=120, cycles=8, inter_fission=500,
                  times=[0, 1, 50, 250, 500], rho=.002, norm=.3, amp_threshold=.2)
    rows = list(rows); assert len(rows) == 8
    for row in rows:
        assert set(row) == {'tissue', 'seed_tag', 'config_digest', 'sweep', 'age_fissions', 'age_updates', 'values'}
        assert type(row['tissue']) is int and row['tissue'] in tissues and row['tissue'] not in by_id
        assert row['seed_tag'] == TAG and row['config_digest'] == canonical_digest(config)
        for key, value in (('sweep', 500), ('age_fissions', 8), ('age_updates', 4000)):
            assert type(row[key]) is int and row[key] == value
        v = row['values']
        assert isinstance(v, np.ndarray) and v.shape == (2, 2, 5, 10) and v.dtype == np.float64
        assert np.isfinite(v).all()
        assert np.all((v[..., [0, 1, 2, 4, 5, 6]] >= 0) & (v[..., [0, 1, 2, 4, 5, 6]] <= 1))
        assert np.all(abs(v[..., [3, 7]]) <= 2) and np.all(abs(v[..., 8]) <= 1) and np.all(abs(v[..., 9]) <= 4)
        assert np.all(v[..., 0] <= v[..., 2]) and np.all(v[..., 4] <= v[..., 5])
        np.testing.assert_allclose(v[..., 8:10], v[..., [0, 3]]-v[..., [6, 7]], rtol=0, atol=1e-14)
        by_id[row['tissue']] = v
    assert set(by_id) == set(tissues)
    x = np.array([by_id[t] for t in tissues]); blocks = (x[:, 0]+x[:, 1])/2.
    tag = TAG+':primary-bootstrap'; seed = int.from_bytes(hashlib.sha256(tag.encode()).digest()[:16], 'little')
    settings = dict(primary='own_minus_other_lineage/live', primary_metric='ever_amplitude', primary_sweep=500,
        target_age_fissions=8, target_age_updates=4000, tissue_blocks=8, lives_per_block=2,
        donor_pairing=[1, 0], bootstrap_unit='tissue', bootstrap_draws=20000, bootstrap_tag=tag,
        bootstrap_seed=seed, bootstrap_generator='PCG64', quantiles=[.025, .975], method='linear',
        secondary_intervals=False, scientific_pass_threshold=None)
    assert set(result) == {'schema', 'analysis', 'tissues', 'backgrounds', 'records', 'metrics', 'absolute', 'contrasts', 'primary'}
    assert result['schema'] == 'l21_record_specificity_summary_v1' and result['analysis'] == settings
    assert result['tissues'] == tissues and result['backgrounds'] == BACKGROUNDS
    assert result['records'] == RECORDS and result['metrics'] == METRICS

    def compare(got, expected):
        got, expected = np.asarray(got), np.asarray(expected)
        assert got.shape == expected.shape and np.isfinite(got).all()
        np.testing.assert_allclose(got, expected, rtol=0, atol=1e-14)

    assert set(result['absolute']) == {'per_life', 'per_tissue', 'mean'}
    compare(result['absolute']['per_life'], x); compare(result['absolute']['per_tissue'], blocks)
    compare(result['absolute']['mean'], sum(blocks)/8.)
    names = {f'own_minus_{rec}/{bg}' for bg in BACKGROUNDS for rec in RECORDS[1:]}
    assert set(result['contrasts']) == names
    for bg, background in enumerate(BACKGROUNDS):
        for j, record in enumerate(RECORDS[1:], 1):
            lives = x[:, :, bg, 0]-x[:, :, bg, j]; b = (lives[:, 0]+lives[:, 1])/2
            row = result['contrasts'][f'own_minus_{record}/{background}']
            assert set(row) == {'per_life', 'per_tissue', 'mean', 'positive_tissues', 'negative_tissues',
                                'tied_tissues', 'positive_lives', 'negative_lives', 'tied_lives'}
            compare(row['per_life'], lives); compare(row['per_tissue'], b); compare(row['mean'], sum(b)/8.)
            for unit, data in (('tissues', b), ('lives', lives.reshape(16, 10))):
                for direction, op in (('positive', lambda v: v > 0), ('negative', lambda v: v < 0), ('tied', lambda v: v == 0)):
                    expected = [sum(bool(op(v)) for v in data[:, i]) for i in range(10)]
                    values = row[f'{direction}_{unit}']
                    assert values == expected and all(type(v) is int for v in values)
    primary = result['primary']
    assert set(primary) == {'mean', 'interval95', 'bootstrap_means', 'draw_indices_sha256'}
    b = np.array([sum(x[i, life, 0, 0, 0]-x[i, life, 0, 2, 0] for life in range(2))/2 for i in range(8)])
    compare(primary['mean'], sum(b)/8)
    random = np.random.Generator(np.random.PCG64(seed))
    draws = random.integers(0, 8, (20000, 8), dtype=np.int64)
    assert primary['draw_indices_sha256'] == hashlib.sha256(draws.astype('<i8').tobytes()).hexdigest()
    bootstrap = sum(b[draws[:, j]] for j in range(8))/8.
    compare(primary['bootstrap_means'], bootstrap)
    ordered = np.sort(bootstrap); interval = []
    for q in (.025, .975):
        pos = q*19999; lo = int(pos); fraction = pos-lo
        interval.append(ordered[lo]*(1-fraction)+ordered[lo+1]*fraction)
    compare(primary['interval95'], interval)
    return True


def check_anchors(raw, record, root):
    from laws_confirmation import l21_paired_fitness_run as io
    assert set(raw) == {f'life_{t}_{life}' for t in range(41000, 41008) for life in range(2)}
    assert set(record) == {'known_lives', 'exact_cells', 'rng_exact', 'main_pool', 'seconds'}
    assert record['known_lives'] == 16 and record['exact_cells'] == 64
    assert record['rng_exact'] is True and record['main_pool'] is False
    assert np.isfinite(record['seconds']) and record['seconds'] > 0
    for t in range(41000, 41008):
        for life in range(2):
            original = io.load_npz(root/'outputs'/'l21_paired_fitness_v1_attempt1'/f'pair_{t}_{life}.npz')
            expected = np.take(original['descendants'][:, :, 2], [0, 4, 3, 7], axis=2).reshape(5, 4, 2, 2, 16, 16)
            np.testing.assert_array_equal(raw[f'life_{t}_{life}'], expected)
    return True


def check_row(row, tissue, raw_bytes, metadata_bytes):
    assert set(row) == {'tissue', 'replay_max_abs', 'alias_futures', 'saved_metrics_checked',
                       'full_replay', 'seconds', 'raw_bytes', 'metadata_bytes'}
    assert type(row['tissue']) is int and row['tissue'] == tissue
    assert np.isfinite(row['replay_max_abs']) and 0 <= row['replay_max_abs'] <= 1e-10
    assert type(row['alias_futures']) is int and row['alias_futures'] == 40
    assert row['saved_metrics_checked'] is True and row['full_replay'] is True
    assert np.isfinite(row['seconds']) and row['seconds'] > 0
    assert type(row['raw_bytes']) is int and row['raw_bytes'] == raw_bytes
    assert type(row['metadata_bytes']) is int and row['metadata_bytes'] == metadata_bytes
    return True


def check_saved(root, *, complete=True):
    from laws_confirmation import l21_record_specificity as p
    root = external_root(root); manifest = p.verify_manifest(root)
    out, run = root/'outputs'/p.RUN_ID, root/'runs'/p.RUN_ID
    names = {f'block_{t}.{ext}' for t in range(42000, 42008) for ext in ('npz', 'json')} | {
        'summary.json', 'verification.json', 'input_hashes.sha256'}
    assert {x.name for x in out.iterdir()} == names | ({'output_hashes.sha256'} if complete else set())
    assert all(x.is_file() and not x.is_symlink() for x in out.iterdir())
    assert not (run/'FAILED.json').exists() and manifest['contract']['output_hash_count'] == len(names) == 19
    status = None
    if complete:
        status = p.io.read_json(run/'STATUS.json')
        assert status['status'] == 'COMPLETE' and status['run_id'] == 'l21_record_specificity_v1_attempt1'
        assert status == p.io.read_json(run/'COMPLETE.json')
        current = p.io.hashes([out/n for n in names])
        assert status['output_sha256'] == current
        assert (out/'output_hashes.sha256').read_text() == p.io.hash_text(current)
        assert status['hash_file_sha256'] == p.sha256_file(out/'output_hashes.sha256')
        assert status['manifest_sha256'] == p.sha256_file(run/'MANIFEST.json')
        assert status['output_bytes'] == sum(x.stat().st_size for x in out.iterdir())
        assert 0 < status['output_bytes'] <= manifest['timing']['projected_bytes'] <= 512*1024**2
    verification = p.io.read_json(out/'verification.json')
    assert set(verification) == {'schema', 'rows', 'checked_blocks', 'independent_replays', 'alias_futures', 'checked_utc'}
    assert verification['schema'] == 'l21_record_specificity_checks_v1'
    assert verification['checked_blocks'] == verification['independent_replays'] == 8
    assert verification['alias_futures'] == 320 and isinstance(verification['checked_utc'], str)
    assert len(verification['rows']) == 8
    rows = []
    for i, t in enumerate(range(42000, 42008)):
        raw = p.io.load_npz(out/f'block_{t}.npz'); meta = p.io.read_json(out/f'block_{t}.json')
        assert check_schema(raw, meta, t, p.CONFIG)
        assert check_row(verification['rows'][i], t, sum(x.nbytes for x in raw.values()), (out/f'block_{t}.json').stat().st_size)
        rows.append(dict(tissue=t, seed_tag=TAG, config_digest=canonical_digest(meta['config']), sweep=500,
            age_fissions=int(raw['descendant_age_fissions'][-1]), age_updates=int(raw['descendant_age_updates'][-1]),
            values=raw['values'][:, 4]))
    assert check_summary(rows, p.io.read_json(out/'summary.json'))
    result = dict(passed=True, input_hashes=len(manifest['input_sha256']), checked_blocks=8,
        contrast_arrays=8, metrics=10, primary_block_count=8,
        full_dynamics_repeated_by_saved_audit=False, saved_raw_metrics_and_pool_checked=True)
    if complete:
        assert status['saved_audit'] == result
    return result
