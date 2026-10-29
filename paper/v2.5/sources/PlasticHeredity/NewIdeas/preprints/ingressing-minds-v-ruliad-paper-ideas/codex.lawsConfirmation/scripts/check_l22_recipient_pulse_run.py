"""Independent D195 saved constraints and scalar role/future statistics.

No D193 production import. Saved checks do not advance physical dynamics;
execution-time full replays are bound to the exact stored arrays and metadata.
"""

from dataclasses import asdict
import hashlib
import importlib.util
import math
from pathlib import Path

import numpy as np


def module(name):
    spec = importlib.util.spec_from_file_location('d193_checks_'+name, Path(__file__).with_name(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


kernel = module('check_l22_recipient_pulse_kernel')
old = module('check_l22_snapshot_routes_run')
source, boundary, physical = old.source, old.boundary, old.physical
exact, close = old.exact, old.close
METRICS, TOL, FUTURES, ROLES = old.METRICS, 2e-12, ('future_1', 'future_2'), ('A', 'B')
KINDS = ('LL', 'YL', 'LL_pulse', 'YL_pulse', 'writer_off', 'writer_off_pulse', 'trace_writer', 'snapshot_writer')


def expected_scope():
    names = tuple(f'{p}__{s}__{k}' for p in ('common', 'residual') for s in ROLES for k in KINDS)
    names += ('common__incoming', 'residual__incoming', 'intact_parent', 'supplied_positive', 'reader_off')
    terms = {}
    for p in ('common', 'residual'):
        rows = dict(disturbance_interaction={'LL_pulse':1.,'YL_pulse':-1.,'LL':-1.,'YL':1.},
            contingent_body_undisturbed={'LL':1.,'YL':-1.}, contingent_body_disturbed={'LL_pulse':1.,'YL_pulse':-1.},
            own_disturbance={'LL_pulse':1.,'LL':-1.}, yoked_disturbance={'YL_pulse':1.,'YL':-1.})
        rows.update({k+'_vs_snapshot':{k:1.,'snapshot_writer':-1.} for k in ('LL','YL','LL_pulse','YL_pulse')})
        for key,a,b in (('writer_undisturbed','LL','writer_off'),('writer_disturbed','LL_pulse','writer_off_pulse'),
            ('off_pulse_identity','writer_off_pulse','writer_off'),('writer_off_identity','writer_off','incoming'),
            ('trace_vs_snapshot','trace_writer','snapshot_writer'),('trace_vs_LL_structural','trace_writer','LL'),
            ('snapshot_gain','snapshot_writer','incoming')): rows[key]={a:1.,b:-1.}
        terms.update({p+'__'+k: {p+'__'+a: c for a, c in v.items()} for k, v in rows.items()})
    return names, terms


def scope(names, comparisons):
    a, b = expected_scope(); assert tuple(names) == a and comparisons == b
    assert len(a) == 37 and len(b) == 32
    return dict(passes=True, packet_names=37, comparisons=32, paths=32, donors=4, body_free_paths=8)


def source_saved(ctx, bundle):
    assert set(bundle) == {'before', 'parent', 'original', 'boundary', 'proof', 'provenance'}
    cfg, p = ctx['config'], bundle['provenance']
    assert p['index'] == ctx['index'] and p['new_founders'] == 0 and p['old_source_replay_retained'] is True
    if ctx['index'] == 603191:
        assert p['role'] == 'reused_excluded_disposable' and p['source_regenerated'] is False
        assert len(p['source_sha256']) == 10
    else:
        assert ctx['index'] == 703193 and p['role'] == 'miniature_qualification'
        assert p['source_regenerated'] is True and p['source_sha256'] == {} and p['old_source_directory'] is None
    source.saved_source(ctx, bundle['before'], bundle['parent'], bundle['original'], bundle['proof'])
    o = bundle['original']
    check = boundary.check(bundle['parent']['theta'], o['kept_V'], o['fresh'], o['damaged_theta'],
                           ctx['index'], cfg.replicates, bundle['boundary'])
    return dict(passes=True, source_replay_retained=True, boundary=check, new_dynamics=0, new_founders=0)


initial = old.initial
draws = old.draws


def saved_repair(ctx, start, index, stream, spec, raw, meta, proof, own_trace=None, donor=None, seal=None):
    from laws_confirmation.l17_r_channel import state_digest
    from laws_confirmation.io import canonical_digest

    cfg, k = ctx['config'], spec['kind']
    free, captured = k in ('trace_writer', 'snapshot_writer'), k == 'LL'
    byoke, wyoke = k in ('YL','YL_pulse'), k == 'trace_writer'
    pulse, event = k.endswith('_pulse'), cfg.sweeps//2+1
    uses = byoke or wyoke
    other = (stream if k == 'self_replay' else ('B' if stream == 'A' else 'A')) if uses else None
    assert set(spec) == {'packet', 'kind'} and k in KINDS and spec['packet'] in ('common', 'residual')
    assert proof['pulse_checked'] is pulse
    assert proof['passes'] and proof['full_dynamics_replayed'] and proof['all_inputs_replayed']
    assert proof['trace_verified'] is (uses or captured) and proof['independent_physics_implementation'] is False
    assert proof['recipient_dynamics_sweeps'] == (0 if free else cfg.sweeps)
    assert proof['donor_replay_sweeps'] == (cfg.sweeps if uses else 0)
    assert proof['saved_raw_sha256'] == state_digest(raw)
    assert proof['saved_metadata_sha256'] == canonical_digest(meta)
    assert proof['outgoing_sha256'] == hashlib.sha256(raw[f's{cfg.sweeps}_theta'].tobytes()).hexdigest()
    assert proof['donor_seal_sha256'] == (None if captured else seal)
    assert (own_trace is not None) == captured and (donor is not None) == uses
    if captured:
        assert proof['saved_trace_sha256'] == kernel.header(ctx, start, index, spec['packet'], stream, own_trace)
        assert own_trace.provenance['rng_final'] == meta['rng_final']
    else: assert proof['saved_trace_sha256'] is None
    donor_hash = kernel.header(ctx, start, index, spec['packet'], other, donor) if uses else None
    assert meta['seconds'] >= 0 and np.isfinite(meta['seconds'])
    for key in ('inputs_sha256',):
        assert isinstance(meta[key], str) and len(meta[key]) == 64 and all(c in '0123456789abcdef' for c in meta[key])
    if not free:
        assert isinstance(meta['rng_final'], str) and len(meta['rng_final']) == 64
    expected_meta = dict(pulse=dict(enabled=pulse,step=event if pulse else None,rows=[4,12],columns=[4,12],operation='sign_inversion_V_only',random_draws=0), spec=spec, index=index, stream=stream, boundary_input_sha256=state_digest(start),
        physical_sha256=kernel.physical(ctx), snapshot_sha256=hashlib.sha256(start['V'].tobytes()).hexdigest(),
        donor_sha256=donor_hash, donor_stream=other, body_free=free, body_theta_fixed=True,
        rng_final=None if free else meta['rng_final'], inputs_sha256=meta['inputs_sha256'],
        body_sweeps=0 if free else cfg.sweeps, writer_sweeps=0 if k in ('writer_off','writer_off_pulse') else cfg.sweeps,
        carrier_bytes_per_record=2048, snapshot_bytes_per_record=2048,
        trace_input_bytes_per_record=(cfg.sweeps+1)*2048 if uses else 0,
        trace_output_bytes_per_record=(cfg.sweeps+1)*2048 if captured else 0,
        capture_trace=captured, seconds=meta['seconds'])
    assert meta == expected_meta
    keys = ('theta', 'S', 'writer_input') if free else (*physical.KEYS, 'S', 'body_input', 'writer_input')
    expected_keys = {f's{t}_{key}' for t in cfg.times for key in keys}
    if pulse: expected_keys |= {'pulse_'+phase+'_'+key for phase in ('before','after','step') for key in physical.KEYS}
    assert set(raw) == expected_keys
    if pulse:
        before = raw['pulse_before_V']; after = raw['pulse_after_V']
        for row in range(16):
            for col in range(16):
                exact(after[:,row,col],(-1 if 4<=row<12 and 4<=col<12 else 1)*before[:,row,col])
        for key in ('ema','R','theta'): exact(raw['pulse_before_'+key],raw['pulse_after_'+key])
        if event-1 in cfg.times:
            for key in physical.KEYS: exact(raw['pulse_before_'+key],raw[f's{event-1}_{key}'])
        if event in cfg.times:
            for key in physical.KEYS: exact(raw['pulse_step_'+key],raw[f's{event}_{key}'])
    for value in raw.values():
        assert value.dtype == np.float64 and value.shape == start['V'].shape and np.isfinite(value).all()
    exact(raw['s0_theta'], start['theta'])
    if not free:
        exact(raw['s0_V'], start['V']); exact(raw['s0_R'], start['V']); exact(raw['s0_ema'], start['ema'])
    for t in cfg.times:
        exact(raw[f's{t}_S'], start['V'])
        if t == 0:
            exact(raw['s0_writer_input'], start['V'])
            if not free: exact(raw['s0_body_input'], start['V'])
        else:
            expected_writer = donor.frames[t] if wyoke else (start['V'] if free else raw[f's{t}_R'])
            exact(raw[f's{t}_writer_input'], expected_writer)
            if byoke: exact(raw[f's{t}_body_input'], donor.frames[t-1])
            if captured: exact(raw[f's{t}_body_input'], own_trace.frames[t-1])
        if captured: exact(raw[f's{t}_R'], own_trace.frames[t])
        if k in ('writer_off','writer_off_pulse'): exact(raw[f's{t}_theta'], start['theta'])


def routing(ctx, bundle, paths, packets, traces):
    names,_=expected_scope(); cfg=ctx['config']; keys=(*physical.KEYS,'S','body_input','writer_input')
    assert set(paths)==set(names[:-5]) and set(packets)==set(names)
    assert set(traces)=={n for n in names[:-5] if n.endswith('__LL')}
    for name,raw in paths.items(): exact(packets[name],raw[f's{cfg.sweeps}_theta'])
    for family in ('common','residual'):
        exact(packets[family+'__incoming'],bundle['boundary'][family])
        for role in ROLES:
            other='B' if role=='A' else 'A'
            def path(kind): return paths[f'{family}__{role}__{kind}']
            for t in cfg.times:
                exact(path('LL')[f's{t}_R'],traces[f'{family}__{role}__LL'].frames[t])
                exact(path('LL')[f's{t}_body_input'],traces[f'{family}__{role}__LL'].frames[max(t-1,0)])
                exact(path('trace_writer')[f's{t}_theta'],paths[f'{family}__{other}__LL'][f's{t}_theta'])
                for a,b in (('LL','writer_off'),('LL_pulse','writer_off_pulse')):
                    for key in ('V','ema','R','S','body_input','writer_input'): exact(path(a)[f's{t}_{key}'],path(b)[f's{t}_{key}'])
                for off in ('writer_off','writer_off_pulse'): exact(path(off)[f's{t}_theta'],packets[family+'__incoming'])
                exact(paths[f'{family}__A__snapshot_writer'][f's{t}_theta'],paths[f'{family}__B__snapshot_writer'][f's{t}_theta'])
                if t<=cfg.sweeps//2:
                    for base in ('LL','YL','writer_off'):
                        for key in keys: exact(path(base)[f's{t}_{key}'],path(base+'_pulse')[f's{t}_{key}'])
            assert sorted(packets[f'{family}__{s}__LL'].tobytes() for s in ROLES)==sorted(packets[f'{family}__{s}__trace_writer'].tobytes() for s in ROLES)
    exact(packets['intact_parent'],bundle['parent']['theta'])
    exact(packets['supplied_positive'],.3*np.repeat(ctx['codes'],cfg.replicates,axis=0))
    exact(packets['reader_off'],bundle['boundary']['common'])
    return dict(passes=True,fixed_reader_isolation=True,own_trace_bridges=4,
        recorded_writer_equalities=True,swapped_packet_multiset_identity=True,
        identity_is_not_scientific_evidence=True,snapshot_role_identity=True,writer_off_exact=True,
        pre_event_identity=True,pulse_paths=12,packets=37)


def reader_context(ctx, local, future):
    assert type(ctx['index']) is int and future in FUTURES and set(ctx) == set(local)
    assert local['index'] == f"d193-yoked-reference-v1:{ctx['index']}:{future}"
    assert all(ctx[k] is local[k] for k in ctx if k != 'index')


def saved_reader(ctx, future, theta, raw, meta, cfg, disabled):
    assert future in FUTURES
    address = f"d193-yoked-reference-v1:{ctx['index']}:{future}"
    birth = physical.Coupled(address, 'assay_birth', cfg.parents*cfg.draws, 'l22-fixed-record-readout-v1')
    v = .2*birth.standard_normal((4*cfg.parents*cfg.draws, 16, 16)); v -= v.mean(axis=(-2, -1), keepdims=True)
    exact(raw['s0_V'], v); assert meta['birth_rng_final'] == birth.digest()
    source.scalar.reader_saved(ctx['codes'], theta, raw, meta, cfg, disabled)


def statistics(records, draws, reported):
    names, terms = expected_scope(); assert set(records) == set(draws) == set(names)
    n = len(records[names[0]]); assert n > 0 and n % 4 == 0
    parents, count_draws = n//4, draws[names[0]].shape[1]
    for name in names:
        assert len(records[name]) == n and draws[name].shape == (n, count_draws, 3) and count_draws > 0
        assert draws[name].dtype == np.float64 and np.isfinite(draws[name]).all()
        for i, row in enumerate(records[name]):
            assert set(row) == set(METRICS) | {'world', 'message', 'replicate'}
            assert (row['world'], row['message'], row['replicate']) == (i, i//parents, i % parents)
            assert all(math.isfinite(row[k]) for k in METRICS)
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

    def transitions(a):
        return {k: dict(records=count([math.fsum(row[j] for row in rec)/count_draws for rec in a]),
            draws=count([row[j] for rec in a for row in rec])) for j, k in enumerate(METRICS[:3])}

    def aggregate(rows, behavior):
        value = dict(arms={name: means(r) for name, r in rows.items()}, contrasts={})
        for name, weights in terms.items():
            delta_rows = [{k: math.fsum(w*rows[c][i][k] for c, w in weights.items()) for k in METRICS} for i in range(n)]
            delta = [[[math.fsum(w*float(behavior[c][i][j][k]) for c, w in weights.items()) for k in range(3)]
                      for j in range(count_draws)] for i in range(n)]
            value['contrasts'][name] = dict(coefficients=weights, per_record=[[r[k] for k in METRICS] for r in delta_rows],
                per_draw_behavior=delta, **means(delta_rows), transitions=dict(pooled=transitions(delta),
                    by_message=[transitions(delta[m*parents:(m+1)*parents]) for m in range(4)]))
        return value

    base = tuple(p+'__'+k for p in ('common', 'residual') for k in KINDS)+names[-5:]
    values, behavior = {}, {}
    for s in ROLES:
        mapping = {p+'__'+k: f'{p}__{s}__{k}' for p in ('common', 'residual') for k in KINDS}
        mapping.update({k: k for k in names[-5:]})
        values[s] = {k: records[mapping[k]] for k in base}; behavior[s] = {k: draws[mapping[k]].tolist() for k in base}
    average_rows = {k: [{metric: math.fsum(values[s][k][i][metric] for s in ROLES)/2 for metric in METRICS}
                        for i in range(n)] for k in base}
    average_behavior = {k: [[[math.fsum(behavior[s][k][i][j][z] for s in ROLES)/2 for z in range(3)]
                            for j in range(count_draws)] for i in range(n)] for k in base}
    expected = dict(schema='d193_role_statistics_v1', records=n, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        reader_draws=count_draws, roles=list(ROLES), named_arms={k: means(records[k]) for k in names},
        by_role={s: aggregate(values[s], behavior[s]) for s in ROLES}, role_mean=aggregate(average_rows, average_behavior),
        role_pooling='within_record_and_paired_draw', confirmatory=False, fitted_models=0, new_founders=0, serial_renewal=False)
    close(reported, expected)
    # These equalities follow from packet identity, not independent scientific evidence.
    for p in ('common', 'residual'):
        for k in ('trace_writer',):
            close(reported['role_mean']['arms'][p+'__'+k], reported['role_mean']['arms'][p+'__LL'])
    return dict(passes=True, independent_scalar_statistics=True, comparisons=32, records=n, roles=2)


def summary(futures, reported, index):
    assert set(futures) == set(FUTURES) and set(reported['by_future']) == set(FUTURES)
    names, _ = expected_scope()
    expected = dict(schema='d193_two_future_block_v1', index=index, futures=list(FUTURES), roles=list(ROLES),
        by_future=reported['by_future'], new_only=reported['new_only'], records=len(futures['future_1'][0][names[0]]),
        named_reads=74, repair_paths=32, comparisons=32, old_outcomes_pooled=False, new_founders=0,
        confirmatory=False, fitted_models=0, serial_renewal=False, pooled_recorded_writer_identity_is_structural=True)
    close(reported, expected)
    for f in FUTURES: statistics(*futures[f], reported['by_future'][f])
    rows, behavior = {}, {}
    for name in names:
        groups = [futures[f][0][name] for f in FUTURES]; assert len(groups[0]) == len(groups[1])
        rows[name] = []
        for i, r in enumerate(groups[0]):
            identity = {k: r[k] for k in ('world', 'message', 'replicate')}
            assert identity == {k: groups[1][i][k] for k in identity}
            rows[name].append(identity | {k: math.fsum(g[i][k] for g in groups)/2 for k in METRICS})
        a, b = [futures[f][1][name] for f in FUTURES]; assert a.shape == b.shape
        behavior[name] = np.asarray([list(x)+list(y) for x, y in zip(a, b)])
    statistics(rows, behavior, reported['new_only'])
    return dict(passes=True, equal_future_and_role_weighting=True, new_dynamics=0)


def costs(value, proof, cfg):
    names, _ = expected_scope(); expected = set(names[:-5])
    assert set(value['repairs']) == expected
    assert value['source_verification_seconds'] >= 0 and value['sealing_seconds'] >= 0
    assert value['donor_paths'] == 4 and value['body_repair_paths'] == 24 and value['body_free_paths'] == 8
    assert value['named_reads'] == 74 and value['unique_reads'] == sum(f['unique_reads'] for f in proof['futures'].values())
    assert value['independent_physics_implementation'] is False
    for name, row in value['repairs'].items():
        kind = name.split('__')[2]; free = kind in ('snapshot_writer', 'trace_writer')
        uses = kind in ('YL','YL_pulse','trace_writer')
        assert row['body_free'] is free and row['donor_generation'] is (kind == 'LL')
        assert row['body_sweeps'] == row['recipient_replay_sweeps'] == (0 if free else cfg.sweeps)
        assert row['writer_sweeps'] == (0 if kind in ('writer_off','writer_off_pulse') else cfg.sweeps)
        assert row['donor_replay_sweeps'] == (cfg.sweeps if uses else 0)
        assert row['trace_generated_bytes'] == (4*cfg.replicates*(cfg.sweeps+1)*2048 if kind == 'LL' else 0)
        assert all(row[k] >= 0 and math.isfinite(row[k]) for k in ('compute_seconds', 'write_reload_seconds', 'independent_replay_seconds'))
