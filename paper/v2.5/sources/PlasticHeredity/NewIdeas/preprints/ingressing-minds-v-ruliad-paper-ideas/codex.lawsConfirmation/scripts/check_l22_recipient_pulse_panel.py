"""Independent D195 four-block scalar checker; frozen block checks are reused.

No production D195 aggregation import. Saved checks advance no dynamics.
"""

from dataclasses import asdict
import importlib.util
import math
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('d195_frozen_checks', Path(__file__).with_name('check_l22_recipient_pulse_run.py'))
frozen = importlib.util.module_from_spec(spec); spec.loader.exec_module(frozen)
kernel = frozen.kernel
source, boundary, physical = frozen.source, frozen.boundary, frozen.physical
exact, close = frozen.exact, frozen.close
METRICS, TOL, FUTURES, ROLES, KINDS = frozen.METRICS, frozen.TOL, frozen.FUTURES, frozen.ROLES, frozen.KINDS
expected_scope, scope = frozen.expected_scope, frozen.scope
initial, draws, saved_repair, routing = frozen.initial, frozen.draws, frozen.saved_repair, frozen.routing
reader_context, saved_reader = frozen.reader_context, frozen.saved_reader
statistics, summary, costs = frozen.statistics, frozen.summary, frozen.costs


def source_saved(ctx, bundle):
    assert set(bundle) == {'before', 'parent', 'original', 'boundary', 'proof', 'provenance'}
    cfg, p = ctx['config'], bundle['provenance']
    assert p['index'] == ctx['index'] and p['new_founders'] == 0 and p['old_source_replay_retained'] is True
    if ctx['index'] in BLOCKS:
        assert p['role'] == 'reused_exposed_main' and p['source_regenerated'] is False
        assert len(p['source_sha256']) == 10
    else:
        assert ctx['index'] == 703193 and p['role'] == 'miniature_qualification'
        assert p['source_regenerated'] is True and p['source_sha256'] == {} and p['old_source_directory'] is None
    source.saved_source(ctx, bundle['before'], bundle['parent'], bundle['original'], bundle['proof'])
    o = bundle['original']
    check = boundary.check(bundle['parent']['theta'], o['kept_V'], o['fresh'], o['damaged_theta'],
                           ctx['index'], cfg.replicates, bundle['boundary'])
    return dict(passes=True, source_replay_retained=True, boundary=check, new_dynamics=0, new_founders=0)


BLOCKS = (319100, 319101, 319102, 319103)


def panel_stream(data, reported, parents, count_draws):
    """Independent scalar reconstruction, not production aggregation."""
    assert set(data) == set(BLOCKS)
    names, terms = expected_scope()
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
                for own, other, pref in ds[name][j]: assert 0 <= own <= 1 and 0 <= other <= 1 and pref == own-other
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

    base = tuple(p+'__'+k for p in ('common', 'residual') for k in KINDS)+names[-5:]

    def aggregate_view(source_rows, source_draws):
        arms = {name: means([source_rows[i][name] for i in BLOCKS]) for name in base}
        contrasts = {}
        for name, weights in terms.items():
            rows = [[{k: math.fsum(w*source_rows[i][c][j][k] for c, w in weights.items()) for k in METRICS}
                     for j in range(n)] for i in BLOCKS]
            ds = [[[[math.fsum(w*float(source_draws[i][c][j, d, k]) for c, w in weights.items()) for k in range(3)]
                    for d in range(count_draws)] for j in range(n)] for i in BLOCKS]
            contrasts[name] = dict(coefficients=weights, **means(rows),
                per_record=[[[r[k] for k in METRICS] for r in b] for b in rows], per_draw_behavior=ds,
                transitions=dict(pooled=transition([r for b in ds for r in b]), by_block=[transition(b) for b in ds],
                    by_message=[transition([r for b in ds for r in b[m*parents:(m+1)*parents]]) for m in range(4)],
                    by_block_message=[[transition(b[m*parents:(m+1)*parents]) for m in range(4)] for b in ds]))
        return dict(arms=arms, contrasts=contrasts)

    role_rows, role_draws = {}, {}
    for role in ROLES:
        mapping = {p+'__'+k: f'{p}__{role}__{k}' for p in ('common', 'residual') for k in KINDS}
        mapping.update({k: k for k in names[-5:]})
        role_rows[role] = {i: {k: data[i][0][mapping[k]] for k in base} for i in BLOCKS}
        role_draws[role] = {i: {k: data[i][1][mapping[k]] for k in base} for i in BLOCKS}
    averaged_rows = {i: {k: [{metric: math.fsum(role_rows[s][i][k][j][metric] for s in ROLES)/2 for metric in METRICS}
                            for j in range(n)] for k in base} for i in BLOCKS}
    averaged_draws = {i: {k: np.array([[[math.fsum(float(role_draws[s][i][k][j, d, z]) for s in ROLES)/2
                                       for z in range(3)] for d in range(count_draws)] for j in range(n)])
                          for k in base} for i in BLOCKS}
    expected = dict(schema='d195_four_block_stream_v1', blocks=list(BLOCKS), records=16*parents,
        parents_per_message=parents, reader_draws=count_draws, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        roles=list(ROLES), named_arms={name: means([data[i][0][name] for i in BLOCKS]) for name in names},
        by_role={s: aggregate_view(role_rows[s], role_draws[s]) for s in ROLES},
        role_mean=aggregate_view(averaged_rows, averaged_draws),
        role_pooling='within_record_and_paired_draw', pooling_unit='equal_block', new_founders=0,
        confirmatory=False, fitted_models=0, serial_renewal=False)
    close(reported, expected)
    for p in ('common', 'residual'):
        for k in ('trace_writer',):
            close(reported['role_mean']['arms'][p+'__'+k], reported['role_mean']['arms'][p+'__LL'])
    return dict(passes=True, records=16*parents, comparisons=32, omission_divisor=3, independent_scalar_statistics=True)


def panel_summary(data, reported, parents, draws):
    assert set(data) == set(BLOCKS)
    expected = dict(schema='d195_recipient_pulse_panel_v1', blocks=list(BLOCKS), futures=list(FUTURES),
        records=16*parents, records_per_block=4*parents, reader_draws_per_future=draws,
        new_draws_per_record=2*draws, named_reads=296, repair_paths=128, body_free_paths=32,
        comparisons=32, own_trace_bridges=16, donor_paths=16, roles=list(ROLES),
        pooled_recorded_writer_identity_is_structural=True,
        new_founders=0, source_regenerated=False, benchmark_excluded=True, old_outcomes_pooled=False,
        confirmatory=False, fitted_models=0, serial_renewal=False, uncertainty_interval=None,
        pooling_unit='equal_block_equal_future_equal_role')
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
    return dict(passes=True, blocks=4, comparisons=32, equal_block_equal_future_equal_role=True,
                complete_controls=True, independent_scalar_statistics=True, new_dynamics=0)
