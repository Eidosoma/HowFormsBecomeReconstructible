"""D192 panel source, route identities and independent scalar aggregation.

No import of the D192 executor or scientific model. Saved-only checks never
advance physical dynamics; full replay is supplied by the qualified kernel
checker at execution time and bound to each saved payload.
"""

from dataclasses import asdict
import hashlib
import importlib.util
import math
from pathlib import Path

import numpy as np


def module(name):
    spec = importlib.util.spec_from_file_location('d192_checks_'+name, Path(__file__).with_name(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


kernel = module('check_l22_snapshot_routes')
source = module('check_l22_fresh_founders')
boundary = module('check_l22_active_form_boundary')
physical = source.physical
exact, close = physical.exact, source.scalar.close
METRICS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
           'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')
TOL, FUTURES = 2e-12, ('future_1', 'future_2')
KINDS = ('B0W0', 'B0W1', 'B1W0', 'B1W1', 'held_B1W1', 'held_B0W1', 'snapshot_only',
         'writer_off', 'scrambled_B1W1', 'ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live')


def scope(names, comparisons, bridges):
    expected_names, terms, expected_bridges = expected_scope()
    assert tuple(names) == expected_names and comparisons == terms and bridges == expected_bridges
    return dict(passes=True, packet_names=35, comparisons=54, native_saved_bridges=12)


def expected_scope():
    names = tuple(p+'__'+n for p in ('common', 'residual') for n in KINDS)
    names += tuple(p+'__'+n for p in ('common', 'residual') for n in ('ordinary_average', 'captured_average', 'incoming'))
    names += ('intact_parent', 'supplied_positive', 'reader_off')
    result, bridges = {}, {}
    for p in ('common', 'residual'):
        local = {}
        for fixed in (0, 1):
            local[f'body_at_W{fixed}'] = {f'B1W{fixed}': 1., f'B0W{fixed}': -1.}
            local[f'writer_at_B{fixed}'] = {f'B{fixed}W1': 1., f'B{fixed}W0': -1.}
        local['body_mean'] = {f'B{b}W{w}': (2*b-1)/2 for b in (0, 1) for w in (0, 1)}
        local['writer_mean'] = {f'B{b}W{w}': (2*w-1)/2 for b in (0, 1) for w in (0, 1)}
        local['interaction'] = {f'B{b}W{w}': float((2*b-1)*(2*w-1)) for b in (0, 1) for w in (0, 1)}
        for cell in ('B0W0', 'B0W1', 'B1W0', 'B1W1'):
            local[cell+'_gain'] = {cell: 1., 'incoming': -1.}
            local[cell+'_vs_snapshot'] = {cell: 1., 'snapshot_only': -1.}
        pairs = {
            'snapshot_gain': ('snapshot_only', 'incoming'), 'writer': ('B1W1', 'writer_off'),
            'organization': ('B1W1', 'scrambled_B1W1'), 'capture_fixed': ('B1W1', 'ordinary_fixed'),
            'capture_live': ('captured_live', 'ordinary_live'), 'theta_feedback': ('captured_live', 'B1W1'),
            'live_reference_refresh': ('captured_live', 'captured_held_live'),
            'captured_average': ('B1W1', 'captured_average'), 'ordinary_average': ('ordinary_fixed', 'ordinary_average'),
            'held_body_equality': ('held_B1W1', 'snapshot_only'), 'held_no_body_equality': ('held_B0W1', 'snapshot_only'),
            'writer_off_equality': ('writer_off', 'incoming')}
        local.update({n: {a: 1., b: -1.} for n, (a, b) in pairs.items()})
        result.update({p+'__'+n: {p+'__'+k: v for k, v in row.items()} for n, row in local.items()})
        for current, old in (('B1W1', f'capture__{p}__own__fixed'), ('writer_off', f'capture__{p}__own__writer_off'),
                ('ordinary_fixed', f'{p}__own__fixed'), ('ordinary_live', f'{p}__own__live'),
                ('captured_live', f'capture__{p}__own__live'), ('captured_held_live', f'capture__{p}__own__reference_held')):
            bridges[p+'__'+current] = old
    assert len(names) == 35 and len(result) == 54 and len(bridges) == 12
    return names, result, bridges


def source_saved(ctx, bundle):
    cfg, p = ctx['config'], bundle['provenance']
    assert set(bundle) == {'before', 'parent', 'original', 'boundary', 'proof', 'provenance', 'bridges'}
    assert p['index'] == ctx['index'] and p['new_founders'] == 0 and p['old_source_replay_retained'] is True
    if ctx['index'] in (319100, 319101, 319102, 319103):
        assert p['role'] == 'reused_exposed_main' and p['source_regenerated'] is False
        assert len(p['source_sha256']) == 22
    else:
        assert ctx['index'] == 703192 and p['role'] == 'miniature_qualification'
        assert p['source_regenerated'] is True and p['source_sha256'] == {} and p['old_source_directory'] is None
    source.saved_source(ctx, bundle['before'], bundle['parent'], bundle['original'], bundle['proof'])
    o, parent = bundle['original'], bundle['parent']
    result = boundary.check(parent['theta'], o['kept_V'], o['fresh'], o['damaged_theta'], ctx['index'], cfg.replicates, bundle['boundary'])
    expected = set()
    for name in expected_scope()[2]:
        keys = {f's{t}_{k}' for t in cfg.times for k in physical.KEYS}
        if name.endswith(('__B1W1', '__ordinary_fixed')): keys |= {f'a{t}_{k}' for t in cfg.times for k in ('mean', 'theta')}
        expected |= {name+'::'+k for k in keys}
    assert set(bundle['bridges']) == expected
    return dict(passes=True, source_replay_retained=True, boundary=result, new_dynamics=0, new_founders=0)


def initial(built, spec, state):
    assert set(state) == set(physical.KEYS)
    exact(state['V'], built['body_own']); exact(state['theta'], built[spec['packet']])
    exact(state['ema'], np.zeros_like(state['V'])); exact(state['R'], np.zeros_like(state['V']))


def saved_repair(ctx, start, index, spec, raw, meta, proof):
    from laws_confirmation.l17_r_channel import state_digest
    from laws_confirmation.io import canonical_digest
    cfg = ctx['config']; kind = spec['kind']
    assert proof['passes'] and proof['full_dynamics_replayed']
    assert proof['saved_raw_sha256'] == state_digest(raw)
    assert proof['saved_metadata_sha256'] == canonical_digest(meta)
    assert proof['outgoing_sha256'] == hashlib.sha256(raw[f's{cfg.sweeps}_theta'].tobytes()).hexdigest()
    assert meta['route_spec'] == spec and meta['boundary_input_sha256'] == state_digest(start)
    native = kind in ('ordinary_fixed', 'ordinary_live', 'captured_live', 'captured_held_live')
    free = kind == 'snapshot_only'
    average = kind == 'ordinary_fixed' or (kind == 'gated' and all(spec[k] for k in ('body_access', 'writer_access', 'write')))
    expected = {f's{t}_{k}' for t in cfg.times for k in (('theta', 'S', 'writer_input') if free else
        physical.KEYS if native else (*physical.KEYS, 'S', 'U', 'body_input', 'writer_input', 'a'))}
    if average: expected |= {f'a{t}_{k}' for t in cfg.times for k in ('mean', 'theta')}
    if kind == 'scrambled': expected.add('snapshot_permutations')
    assert set(raw) == expected
    for name, v in raw.items():
        assert np.isfinite(v).all()
        if name == 'snapshot_permutations': assert v.shape == (cfg.replicates, 256) and v.dtype == np.int64
        elif name.endswith('_a'): assert v.shape == () and v.dtype == np.float64
        else: assert v.shape == start['V'].shape and v.dtype == np.float64
    exact(raw['s0_theta'], start['theta'])
    if not free:
        exact(raw['s0_V'], start['V']); exact(raw['s0_ema'], start['ema'])
    if native:
        captured = kind.startswith('captured')
        exact(raw['s0_R'], start['V'] if captured else start['R'])
        assert meta['native_bridge'] is True and meta['body_free'] is False
        assert proof['route_native_bridge'] is True and proof['native_state_max_abs'] == 0.
        return
    assert meta['native_bridge'] is False and meta['body_free'] is free and meta['body_theta_fixed'] is True
    assert proof['state_max_abs'] == 0. and proof['direct_inputs_replayed'] and proof['body_free'] is free
    assert 0 <= meta['decomposition_max_abs'] == proof['decomposition_max_abs'] <= TOL
    s = start['V'].copy()
    if kind == 'scrambled':
        tag = f'd192-snapshot-routes-v1:{index}:snapshot_shuffle'.encode()
        rng = np.random.default_rng(int.from_bytes(hashlib.sha256(tag).digest()[:16], 'little'))
        perms = np.array([rng.permutation(256) for _ in range(cfg.replicates)])
        exact(perms, raw['snapshot_permutations'])
        s = np.stack([v.ravel()[perms[i % cfg.replicates]].reshape(16, 16) for i, v in enumerate(s)])
    assert meta['snapshot_sha256'] == hashlib.sha256(s.tobytes()).hexdigest()
    assert meta['snapshot_bytes_per_record'] == meta['carrier_bytes_per_record'] == 2048
    assert meta['snapshot_observations_per_record'] == 1
    assert meta['body_sweeps'] == (0 if free else cfg.sweeps)
    assert meta['writer_sweeps'] == (cfg.sweeps if spec['write'] else 0)
    assert meta['average_observations_per_record'] == (cfg.sweeps+1 if average else 0)
    rho = 0. if kind in ('held', 'snapshot_only') else ctx['bp'].rho
    factors = [1.]
    for _ in range(cfg.sweeps): factors.append((1-rho)*factors[-1])
    for t in cfg.times:
        exact(raw[f's{t}_S'], s)
        if free:
            exact(raw[f's{t}_writer_input'], s); assert meta['rng_final'] is None
        else:
            exact(raw[f's{t}_a'], np.asarray(factors[t]))
            u = raw[f's{t}_R']-factors[t]*s
            exact(raw[f's{t}_U'], u)
            exact(raw[f's{t}_writer_input'], raw[f's{t}_R'] if spec['writer_access'] else u)
            if t == 0: exact(raw['s0_body_input'], s if spec['body_access'] else np.zeros_like(s))
            else:
                prev = raw[f's{t}_body_input'] if spec['body_access'] else raw[f's{t}_body_input']+factors[t-1]*s
                np.testing.assert_allclose(raw[f's{t}_R'], prev+rho*(raw[f's{t}_V']-prev), rtol=0., atol=TOL)
            if not spec['write']: exact(raw[f's{t}_theta'], start['theta'])


def routing(ctx, bundle, paths, packets):
    names, _, bridges = expected_scope(); cfg = ctx['config']
    assert set(paths) == {p+'__'+n for p in ('common', 'residual') for n in KINDS}
    assert set(packets) == set(names)
    for name, raw in paths.items(): exact(packets[name], raw[f's{cfg.sweeps}_theta'])
    for name in bridges:
        original = {k.split('::', 1)[1]: v for k, v in bundle['bridges'].items() if k.startswith(name+'::')}
        for k, v in original.items(): exact(paths[name][k], v)
    for p in ('common', 'residual'):
        exact(packets[p+'__incoming'], bundle['boundary'][p])
        for name in ('writer_off',): exact(packets[p+'__'+name], packets[p+'__incoming'])
        for name in ('held_B1W1', 'held_B0W1', 'captured_held_live'):
            exact(packets[p+'__'+name], packets[p+'__snapshot_only'])
            for t in cfg.times: exact(paths[p+'__'+name][f's{t}_theta'], paths[p+'__snapshot_only'][f's{t}_theta'])
        for name, arm in (('ordinary_average', 'ordinary_fixed'), ('captured_average', 'B1W1')):
            exact(packets[p+'__'+name], paths[p+'__'+arm][f'a{cfg.sweeps}_theta'])
        for b in (0, 1):
            for t in cfg.times:
                for k in ('V', 'ema', 'R', 'U', 'a', 'body_input'):
                    exact(paths[f'{p}__B{b}W0'][f's{t}_{k}'], paths[f'{p}__B{b}W1'][f's{t}_{k}'])
    exact(packets['intact_parent'], bundle['parent']['theta'])
    exact(packets['supplied_positive'], .3*np.repeat(ctx['codes'], cfg.replicates, axis=0))
    exact(packets['reader_off'], bundle['boundary']['common'])
    return dict(passes=True, exact_native_saved_bridges=12, fixed_reader_isolation=True,
                protected_writer_equalities=True, writer_off_exact=True, packets=35)


def reader_context(ctx, local, future):
    assert type(ctx['index']) is int and future in FUTURES and set(ctx) == set(local)
    assert local['index'] == f"d192-snapshot-routes-v1:{ctx['index']}:{future}"
    assert all(ctx[k] is local[k] for k in ctx if k != 'index')


def saved_reader(ctx, future, theta, raw, meta, cfg, disabled):
    assert future in FUTURES
    address = f"d192-snapshot-routes-v1:{ctx['index']}:{future}"
    birth = physical.Coupled(address, 'assay_birth', cfg.parents*cfg.draws, 'l22-fixed-record-readout-v1')
    v = .2*birth.standard_normal((4*cfg.parents*cfg.draws, 16, 16))
    v -= v.mean(axis=(-2, -1), keepdims=True)
    exact(raw['s0_V'], v); assert meta['birth_rng_final'] == birth.digest()
    source.scalar.reader_saved(ctx['codes'], theta, raw, meta, cfg, disabled)


def draws(raw, cfg, actual):
    expected = []
    for i in range(4*cfg.parents):
        m = i//cfg.parents; partner = (m+2) % 4
        expected.append([[float(raw['probabilities'][i*cfg.draws+j, m]),
            float(raw['probabilities'][i*cfg.draws+j, partner]),
            float(raw['probabilities'][i*cfg.draws+j, m]-raw['probabilities'][i*cfg.draws+j, partner])]
            for j in range(cfg.draws)])
    exact(actual, np.asarray(expected, dtype=np.float64))


def statistics(records, draws, reported):
    names, terms, _ = expected_scope(); assert set(records) == set(draws) == set(names)
    n = len(records[names[0]]); assert n > 0 and n % 4 == 0
    parents, count_draws = n//4, draws[names[0]].shape[1]
    for name in names:
        assert len(records[name]) == n and draws[name].shape == (n, count_draws, 3) and count_draws > 0
        assert draws[name].dtype == np.float64 and np.isfinite(draws[name]).all()
        for i, row in enumerate(records[name]):
            assert set(row) == set(METRICS) | {'world', 'message', 'replicate'}
            assert (row['world'], row['message'], row['replicate']) == (i, i//parents, i % parents)
            for j, k in enumerate(METRICS[:3]):
                assert abs(math.fsum(float(v) for v in draws[name][i, :, j])/count_draws-row[k]) <= TOL
            for own, other, pref in draws[name][i]: assert 0 <= own <= 1 and 0 <= other <= 1 and pref == own-other

    def means(rows):
        return dict(mean={k: math.fsum(r[k] for r in rows)/n for k in METRICS},
            messages=[{k: math.fsum(r[k] for r in rows[m*parents:(m+1)*parents])/parents for k in METRICS} for m in range(4)])

    def count(values):
        return dict(n=len(values), improved=sum(v > TOL for v in values), worsened=sum(v < -TOL for v in values),
            tied=sum(abs(v) <= TOL for v in values), net=math.fsum(values)/len(values),
            positive=math.fsum(max(v, 0.) for v in values)/len(values), negative=math.fsum(min(v, 0.) for v in values)/len(values))

    def transition(a):
        return {k: dict(records=count([math.fsum(row[j] for row in record)/count_draws for record in a]),
            draws=count([row[j] for record in a for row in record])) for j, k in enumerate(METRICS[:3])}

    expected = dict(schema='d192_single_block_routes_v1', records=n, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        reader_draws=count_draws, arms={name: means(records[name]) for name in names}, contrasts={},
        confirmatory=False, fitted_models=0, new_founders=0, serial_renewal=False)
    for name, weights in terms.items():
        rows = [{k: math.fsum(w*records[c][i][k] for c, w in weights.items()) for k in METRICS} for i in range(n)]
        delta = [[[math.fsum(w*float(draws[c][i, j, k]) for c, w in weights.items()) for k in range(3)]
                  for j in range(count_draws)] for i in range(n)]
        expected['contrasts'][name] = dict(coefficients=weights, per_record=[[r[k] for k in METRICS] for r in rows],
            per_draw_behavior=delta, **means(rows), transitions=dict(pooled=transition(delta),
                by_message=[transition(delta[m*parents:(m+1)*parents]) for m in range(4)]))
    close(reported, expected)
    return dict(passes=True, independent_scalar_statistics=True, comparisons=54, records=n)


def summary(futures, reported, index):
    assert set(futures) == set(FUTURES) and set(reported['by_future']) == set(FUTURES)
    expected = dict(schema='d192_two_future_block_v1', index=index, futures=list(FUTURES),
        by_future=reported['by_future'], new_only=reported['new_only'], records=len(futures['future_1'][0]['common__B1W1']),
        named_reads=70, repair_paths=26, comparisons=54, old_outcomes_pooled=False,
        new_founders=0, confirmatory=False, fitted_models=0, serial_renewal=False)
    close(reported, expected)
    for f in FUTURES: statistics(*futures[f], reported['by_future'][f])
    rows, values = {}, {}
    for name in expected_scope()[0]:
        groups = [futures[f][0][name] for f in FUTURES]
        assert len(groups[0]) == len(groups[1])
        rows[name] = []
        for i, r in enumerate(groups[0]):
            identity = {k: r[k] for k in ('world', 'message', 'replicate')}
            assert identity == {k: groups[1][i][k] for k in identity}
            rows[name].append(identity | {k: math.fsum(g[i][k] for g in groups)/2 for k in METRICS})
        a, b = [futures[f][1][name] for f in FUTURES]; assert a.shape == b.shape
        values[name] = np.array([list(x)+list(y) for x, y in zip(a, b)])
    statistics(rows, values, reported['new_only'])
    return dict(passes=True, equal_future_weighting=True, new_dynamics=0)


def costs(value, proof, cfg):
    expected = {p+'__'+n for p in ('common', 'residual') for n in KINDS}
    assert set(value['repairs']) == expected
    assert value['held_bridges'] == proof['held_bridges'] and value['source_verification_seconds'] >= 0
    assert value['body_repair_paths'] == 24 and value['body_free_paths'] == 2 and value['named_reads'] == 70
    assert value['unique_reads'] == sum(f['unique_reads'] for f in proof['futures'].values())
    assert value['independent_physics_implementation'] is False
    for name, row in value['repairs'].items():
        free = name.endswith('__snapshot_only')
        assert row['body_free'] is free and row['body_sweeps'] == (0 if free else cfg.sweeps)
        assert row['native_writer_sweeps'] == (0 if name.endswith('__writer_off') else cfg.sweeps)
        assert row['averaging_writer_sweeps'] == (cfg.sweeps if name.endswith(('__B1W1', '__ordinary_fixed')) else 0)
        assert row['total_repair_seconds'] >= 0 and row['independent_replay_seconds'] >= 0


BLOCKS = (319100, 319101, 319102, 319103)


def panel_stream(data, reported, parents, count_draws):
    """Independent scalar reconstruction, not production aggregation."""
    assert set(data) == set(BLOCKS)
    names, terms, _ = expected_scope()
    n = 4*parents
    for i in BLOCKS:
        rows, ds = data[i]
        assert set(rows) == set(ds) == set(names)
        for name in names:
            assert len(rows[name]) == n and ds[name].shape == (n, count_draws, 3)
            for j, r in enumerate(rows[name]):
                assert set(r) == set(METRICS) | {'world', 'message', 'replicate'}
                assert (r['world'], r['message'], r['replicate']) == (j, j//parents, j % parents)
                assert all(math.isfinite(r[k]) for k in METRICS)
                for k, field in enumerate(METRICS[:3]):
                    assert abs(math.fsum(float(v) for v in ds[name][j, :, k])/count_draws-r[field]) <= TOL

    def means(rows):
        def avg(selected): return {k: math.fsum(r[k] for r in selected)/len(selected) for k in METRICS}
        by_block = [avg(b) for b in rows]
        return dict(mean={k: math.fsum(r[k] for r in by_block)/4 for k in METRICS}, by_block=by_block,
            by_message=[avg([r for b in rows for r in b[m*parents:(m+1)*parents]]) for m in range(4)],
            by_block_message=[[avg(b[m*parents:(m+1)*parents]) for m in range(4)] for b in rows],
            leave_one_block_out=[{k: math.fsum(by_block[j][k] for j in range(4) if i != j)/3 for k in METRICS} for i in range(4)])

    def count(xs):
        return dict(n=len(xs), improved=sum(v > TOL for v in xs), worsened=sum(v < -TOL for v in xs),
            tied=sum(abs(v) <= TOL for v in xs), net=math.fsum(xs)/len(xs),
            positive=math.fsum(max(v, 0.) for v in xs)/len(xs), negative=math.fsum(min(v, 0.) for v in xs)/len(xs))

    def transition(rows):
        return {k: dict(records=count([math.fsum(r[j] for r in world)/count_draws for world in rows]),
            draws=count([r[j] for world in rows for r in world])) for j, k in enumerate(METRICS[:3])}

    arms = {name: means([data[i][0][name] for i in BLOCKS]) for name in names}
    contrasts = {}
    for name, weights in terms.items():
        rows = [[{k: math.fsum(w*data[i][0][c][j][k] for c, w in weights.items()) for k in METRICS}
                 for j in range(n)] for i in BLOCKS]
        ds = [[[[math.fsum(w*float(data[i][1][c][j, d, k]) for c, w in weights.items()) for k in range(3)]
                for d in range(count_draws)] for j in range(n)] for i in BLOCKS]
        contrasts[name] = dict(coefficients=weights, **means(rows),
            per_record=[[[r[k] for k in METRICS] for r in b] for b in rows], per_draw_behavior=ds,
            transitions=dict(pooled=transition([r for b in ds for r in b]), by_block=[transition(b) for b in ds],
                by_message=[transition([r for b in ds for r in b[m*parents:(m+1)*parents]]) for m in range(4)],
                by_block_message=[[transition(b[m*parents:(m+1)*parents]) for m in range(4)] for b in ds]))
    expected = dict(schema='d192_four_block_stream_v1', blocks=list(BLOCKS), records=16*parents,
        parents_per_message=parents, reader_draws=count_draws, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        arms=arms, contrasts=contrasts, pooling_unit='equal_block', new_founders=0,
        confirmatory=False, fitted_models=0, serial_renewal=False)
    close(reported, expected)
    return dict(passes=True, records=16*parents, comparisons=54, omission_divisor=3, independent_scalar_statistics=True)


def panel_summary(data, reported, parents, draws):
    assert set(data) == set(BLOCKS)
    expected = dict(schema='d192_snapshot_routes_panel_v1', blocks=list(BLOCKS), futures=list(FUTURES),
        records=16*parents, records_per_block=4*parents, reader_draws_per_future=draws,
        new_draws_per_record=2*draws, named_reads=280, repair_paths=104, body_free_paths=8,
        comparisons=54, native_saved_bridges=48, held_fixed_bridges=8,
        new_founders=0, source_regenerated=False, benchmark_excluded=True, old_outcomes_pooled=False,
        confirmatory=False, fitted_models=0, serial_renewal=False, uncertainty_interval=None,
        pooling_unit='equal_block_equal_future')
    assert set(reported) == set(expected) | {'by_future', 'new_only'}
    close({k: reported[k] for k in expected}, expected)
    assert set(reported['by_future']) == set(FUTURES)
    pooled = {}
    for i in BLOCKS:
        assert set(data[i]) == set(FUTURES)
        records, values = {}, {}
        for name in expected_scope()[0]:
            groups = [data[i][f][0][name] for f in FUTURES]
            assert all(len(g) == 4*parents for g in groups)
            records[name] = []
            for j, first in enumerate(groups[0]):
                identity = {k: first[k] for k in ('world', 'message', 'replicate')}
                assert identity == {k: groups[1][j][k] for k in identity}
                records[name].append(identity | {k: math.fsum(g[j][k] for g in groups)/2 for k in METRICS})
            values[name] = np.array([[data[i][f][1][name][j, d].tolist() for f in FUTURES for d in range(draws)]
                                     for j in range(4*parents)])
        pooled[i] = records, values
    for f in FUTURES: panel_stream({i: data[i][f] for i in BLOCKS}, reported['by_future'][f], parents, draws)
    panel_stream(pooled, reported['new_only'], parents, 2*draws)
    return dict(passes=True, blocks=4, comparisons=54, equal_block_equal_future=True,
                complete_controls=True, independent_scalar_statistics=True, new_dynamics=0)
