"""D094 pure synthetic tests; actual dynamics require explicit opt-in + space.

Default tests generate no scientific futures and write no artifacts. Dynamic
checks are deliberately skipped until L21_ENABLE_DYNAMICS=1 and the unchanged
preflight succeeds. A skip is never recorded as successful dynamic validation.
"""

from copy import deepcopy
from dataclasses import asdict, replace
import inspect
from itertools import product
import json
import os
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l21_paired_fitness as p
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT, canonical_digest


def test_contract_is_not_an_evolution_or_automatic_launch():
    c = p.contract()
    assert c['rates'] == [.001, .2, 1.]
    assert (c['units'], c['parent_prefixes'], c['final_futures']) == (16, 48, 384)
    assert (c['target_age_fissions'], c['target_age_updates']) == (8, 4000)
    assert c['common_founder_target'] and not c['founder_writing']
    assert c['V_fragment_inherited'] and c['R_zero_is_not_reader_off']
    assert c['intervened_boundaries'] == 1 and c['parent_prefix_boundaries'] == 7
    assert c['source_control']['known_outcomes'] and not c['source_control']['paired_across_u']
    assert not any(c[k] for k in ('hard_reset', 'evolutionary_selection', 'heritable_fraction',
                                  'target_age_manipulation', 'automatic_followup'))
    assert c['main_runner_enabled']
    assert c['scientific_pass_threshold'] is None
    assert c['primary'] == dict(u=1., theta='copy_minus_native', writer='on', R='copy',
                                sweep=500, metric='ever_amplitude')
    assert c['storage_reserve_bytes']+c['storage_allowance_bytes'] == 4831838208


@pytest.mark.parametrize('change', [dict(replicates=0), dict(settle=0), dict(cycles=1),
    dict(cycles=True), dict(inter_fission=1.5), dict(times=()), dict(times=(0, 0, 500)),
    dict(times=(1, 500)), dict(times=(0, 501)), dict(times=(0, 500.,)),
    dict(rho=.001), dict(norm=float('nan')), dict(amp_threshold=.1)])
def test_bad_config(change):
    with pytest.raises(ValueError):
        replace(p.CONFIG, **change)


def synthetic_boundary():
    parent = (np.arange(4*3*256, dtype=float).reshape(4, 3, 16, 16)+1)/5000.
    parent[1] = parent[0]
    native = np.linspace(-.5, .5, 256).reshape(16, 16)
    birth = p.boundary_panel(parent, native)
    return dict(last_cut=parent, native=native, descendants=np.stack((birth, birth.copy())),
                prefix_ends=parent[None].copy())


def test_boundary_changes_only_declared_fields_and_copies_inputs():
    raw = synthetic_boundary(); before = deepcopy(raw)
    assert p.checker().check_boundary(raw)
    raw['descendants'][0, 3, 0, 0, 0, 0] += 2
    np.testing.assert_array_equal(raw['last_cut'], before['last_cut'])
    np.testing.assert_array_equal(raw['native'], before['native'])
    np.testing.assert_array_equal(raw['descendants'][0, :, :, 1], before['descendants'][0, :, :, 1])


@pytest.mark.parametrize('arm', range(8))
@pytest.mark.parametrize('field', range(4))
def test_each_boundary_field_corruption_detected(arm, field):
    raw = synthetic_boundary()
    raw['descendants'][0, field, 0, arm, 0, 0] += .01
    with pytest.raises(AssertionError):
        p.checker().check_boundary(raw)


@pytest.mark.parametrize('arm', [2, 3, 6, 7])
def test_writer_off_must_remain_bit_exact(arm):
    raw = synthetic_boundary(); raw['descendants'][1, 3, 1, arm, 0, 0] += 1e-15
    with pytest.raises(AssertionError):
        p.checker().check_boundary(raw)


@pytest.mark.parametrize('batch', [1, 3, 8, 24])
def test_random_stream_coupling_and_batch_size_invariance(batch):
    a = p.SharedNoise(1, 0, 'cycle_8'); b = p.SharedNoise(1, 0, 'cycle_8')
    for _ in range(3):
        np.testing.assert_array_equal(a.integers(0, 2, batch), np.repeat(b.integers(0, 2, 1), batch))
        np.testing.assert_array_equal(a.standard_normal((batch, 16, 16)),
                                      np.broadcast_to(b.standard_normal((1, 16, 16)), (batch, 16, 16)))
    assert a.digest() == b.digest()


def test_independent_random_address_and_checker_namespace():
    addresses = [p.seed(i, r, phase) for i, r, phase in product((1, 2), (0, 1), ('founder', 'cycle_1', 'cycle_8'))]
    assert len(set(addresses)) == len(addresses)
    a = p.SharedNoise(2, 1, 'cycle_8'); b = p.checker().generator(2, 1, 'cycle_8')
    np.testing.assert_array_equal(a.standard_normal((1, 16, 16)), b.standard_normal((1, 16, 16)))
    assert 'u' not in inspect.signature(p.seed).parameters and 'arm' not in inspect.signature(p.seed).parameters


@pytest.mark.parametrize('shape', [(0, 16, 16), (3, 8, 16), (16, 16), (2, 3, 16, 16)])
def test_noise_rejects_wrong_batch(shape):
    with pytest.raises(ValueError):
        p.SharedNoise(1, 0, 'test').standard_normal(shape)


def test_metrics_strict_threshold_and_zero_sign_convention():
    target = np.ones((16, 16)); target[0, 0] = 0.
    v = np.ones((3, 8, 16, 16)); v[..., 0, 0] = -.2
    mask = np.ones((16, 16), bool)
    values = p.scores(v, target, mask, mask)
    np.testing.assert_allclose(values, p.checker().metric(v, target, mask, mask), atol=1e-14, rtol=0)
    np.testing.assert_array_equal(values[..., 0], np.full((3, 8), 255/256))
    np.testing.assert_array_equal(values[..., 2], np.ones((3, 8)))


@pytest.mark.parametrize('bad', ['empty_ever', 'empty_fresh', 'not_subset', 'nan_v', 'nan_target', 'int_mask'])
def test_metrics_refuse_silent_invalid_cells(bad):
    v = np.ones((3, 8, 16, 16)); target = np.ones((16, 16))
    ever = np.ones((16, 16), bool); fresh = ever.copy()
    if bad == 'empty_ever': ever[:] = False
    if bad == 'empty_fresh': fresh[:] = False
    if bad == 'not_subset': ever[0, 0] = False
    if bad == 'nan_v': v[0, 0, 0, 0] = np.nan
    if bad == 'nan_target': target[0, 0] = np.nan
    if bad == 'int_mask': ever = ever.astype(int)
    with pytest.raises(ValueError):
        p.scores(v, target, ever, fresh)


def test_conditional_effects_and_no_false_interaction():
    f = np.empty((2, 3, 3, 8, 6))
    for u, (arm, (t, w, r)) in product(range(3), enumerate(product(range(2), repeat=3))):
        f[..., u, arm, :] = .1*u+.2*(1-t)+.03*(1-w)+.01*(1-r)
    rows = p.contrasts(f)
    assert len(rows) == 44 and p.checker().check_contrasts(f, rows)
    np.testing.assert_allclose(rows['theta/u=1.0/writer=0/R=0'], .2, atol=1e-15, rtol=0)
    for key in rows:
        if key.startswith('theta_x_writer'):
            np.testing.assert_allclose(rows[key], 0., atol=1e-15, rtol=0)
    rows['theta/u=1.0/writer=0/R=0'] *= -1
    with pytest.raises(AssertionError):
        p.checker().check_contrasts(f, rows)


def test_nonadditive_writer_interaction_is_retained():
    f = np.zeros((3, 8, 6)); f[:, 0] = .1
    rows = p.contrasts(f)
    assert p.checker().check_contrasts(f, rows)
    np.testing.assert_array_equal(rows['theta_x_writer/u=1.0/R=0'], np.full(6, .1))
    np.testing.assert_array_equal(rows['theta_x_writer/u=1.0/R=1'], np.zeros(6))


@pytest.mark.parametrize('free,allowed,deficit', [(4831838207, False, 1), (4831838208, True, 0),
                                                (4816109568, False, 15728640)])
def test_storage_gate_unchanged(monkeypatch, free, allowed, deficit):
    monkeypatch.setattr(p.shutil, 'disk_usage', lambda path: SimpleNamespace(free=free))
    report = p.resource_report(DEFAULT_EXTERNAL_ROOT)
    assert report['storage_allows_start'] is allowed and report['shortfall_bytes'] == deficit


def test_dynamics_entry_points_preflight_before_context(monkeypatch):
    def blocked(*args, **kwargs): raise RuntimeError('test storage block')
    def forbidden(*args, **kwargs): raise AssertionError('dynamics reached before guard')
    monkeypatch.setattr(p.source, 'preflight', blocked)
    monkeypatch.setattr(p, 'context', forbidden)
    with pytest.raises(RuntimeError, match='test storage block'):
        p.execute_pair(p.DISPOSABLE, 0, root=DEFAULT_EXTERNAL_ROOT, cfg=p.SHORT)
    with pytest.raises(RuntimeError, match='test storage block'):
        p.source_control(.001, 0, root=DEFAULT_EXTERNAL_ROOT)


@pytest.mark.parametrize('index,rep', [(-1, 0), (True, 0), (41000, -1), (41000, 2), (41000, .0)])
def test_invalid_main_addresses_rejected_without_dynamics(monkeypatch, index, rep):
    monkeypatch.setattr(p.source, 'preflight', lambda root: None)
    monkeypatch.setattr(p, 'context', lambda index: pytest.fail('context must not be reached'))
    with pytest.raises(ValueError):
        p.execute_pair(index, rep, root=DEFAULT_EXTERNAL_ROOT)


@pytest.mark.parametrize('u,rep', [(True, 0), (.2, 0), (.001, -1), (.001, 3), (1., .0)])
def test_invalid_source_addresses_rejected_without_dynamics(monkeypatch, u, rep):
    monkeypatch.setattr(p.source, 'preflight', lambda root: None)
    monkeypatch.setattr(p, 'context', lambda index: pytest.fail('context must not be reached'))
    with pytest.raises(ValueError):
        p.source_control(u, rep, root=DEFAULT_EXTERNAL_ROOT)


def synthetic_score_records():
    """Hand-built tables, not simulator output; effects are binary fractions."""
    records = []
    for block, tissue in enumerate(p.TISSUES):
        for replicate in range(2):
            x = np.broadcast_to(np.array([.5, .5, .75, .25, .5, .75]), (3, 8, 6)).copy()
            effect = (-4, -2, 0, 1, 2, 4, 5, 6)[block]/64 + (-1 if replicate == 0 else 1)/128
            x[2, 0, 0] += effect
            x[1, 1, 3] -= effect
            records.append(dict(schema=p.SCORE_SCHEMA, seed_tag=p.TAG, tissue=tissue,
                replicate=replicate, config_digest=canonical_digest(asdict(p.CONFIG)),
                sweep=500, target_age_fissions=8, target_age_updates=4000, scores=x))
    return records


@pytest.fixture(scope='module')
def synthetic_summary():
    records = synthetic_score_records()
    return records, p.summarize(records)


def test_analysis_unit_and_fixed_bootstrap_contract():
    c = p.contract()['analysis']
    assert p.contract(p.SHORT)['analysis'] is None
    assert (c['tissue_blocks'], c['lives_per_block']) == (8, 2)
    assert c['bootstrap_unit'] == 'tissue' and c['bootstrap_draws'] == 20000
    assert c['bootstrap_generator'] == 'PCG64' and c['quantile_method'] == 'linear'
    assert c['quantiles'] == [.025, .975] and c['tie_rule'] == 'exact_zero'
    assert not c['secondary_intervals'] and not c['source_controls_in_main_pool']
    assert not c['incomplete_panels_allowed'] and c['scientific_pass_threshold'] is None


def test_independent_summary_and_all_directions(synthetic_summary):
    records, result = synthetic_summary
    assert p.checker().check_summary(records, result)
    row = result['contrasts'][p.PRIMARY_KEY]
    np.testing.assert_array_equal(np.array(row['per_tissue'])[:, 0], np.array([-4, -2, 0, 1, 2, 4, 5, 6])/64)
    assert result['primary']['mean'] == 12/512
    assert [row[f'{s}_tissues'][0] for s in ('positive', 'negative', 'tied')] == [5, 2, 1]
    assert [row[f'{s}_lives'][0] for s in ('positive', 'negative', 'tied')] == [11, 5, 0]
    assert len(result['primary']['bootstrap_means']) == 20000
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_no_pseudoreplication_of_descendants_or_lives(synthetic_summary):
    _, result = synthetic_summary
    lives = np.array(result['contrasts'][p.PRIMARY_KEY]['per_life'])[..., 0].ravel()
    # Deliberately wrong 16-life bootstrap is detectably different on this table.
    rng = np.random.Generator(np.random.PCG64(result['analysis']['bootstrap_seed']))
    naive = lives[rng.integers(0, 16, (20000, 16))].mean(axis=1)
    naive_interval = np.quantile(naive, [.025, .975])
    actual = result['primary']['interval95']
    assert naive_interval[1]-naive_interval[0] < actual[1]-actual[0]


def test_pooling_order_invariant_without_mutating_inputs(synthetic_summary):
    records, result = synthetic_summary; before = deepcopy(records)
    assert p.summarize(list(reversed(records))) == result
    ordered = p.ordered_final_scores(records); ordered.flat[0] += .1
    for left, right in zip(records, before):
        np.testing.assert_array_equal(left['scores'], right['scores'])
        assert {k: v for k, v in left.items() if k != 'scores'} == {k: v for k, v in right.items() if k != 'scores'}


@pytest.mark.parametrize('bad', ['missing', 'extra', 'duplicate', 'source_tissue', 'disposable',
    'replicate', 'boolean_id', 'wrong_sweep', 'float_sweep', 'wrong_age', 'wrong_age_updates',
    'wrong_seed_tag', 'wrong_config', 'wrong_schema', 'extra_field', 'missing_field',
    'wrong_shape', 'float32', 'list_scores', 'nan', 'inf', 'negative_fidelity',
    'over_one', 'over_projection', 'amplitude_exceeds_sign', 'whole_exceeds_active'])
def test_main_pool_rejects_wrong_or_incomplete_records(bad):
    records = synthetic_score_records(); row = records[0]
    if bad == 'missing': records.pop()
    elif bad == 'extra': records.append(deepcopy(row))
    elif bad == 'duplicate': records[-1] = deepcopy(row)
    elif bad == 'source_tissue': row['tissue'] = 0
    elif bad == 'disposable': row['tissue'] = p.DISPOSABLE
    elif bad == 'replicate': row['replicate'] = 2
    elif bad == 'boolean_id': row['replicate'] = False
    elif bad == 'wrong_sweep': row['sweep'] = 250
    elif bad == 'float_sweep': row['sweep'] = 500.
    elif bad == 'wrong_age': row['target_age_fissions'] = 7
    elif bad == 'wrong_age_updates': row['target_age_updates'] = 3999
    elif bad == 'wrong_seed_tag': row['seed_tag'] = 'ancestry-world-v1'
    elif bad == 'wrong_config': row['config_digest'] = canonical_digest(asdict(p.SHORT))
    elif bad == 'wrong_schema': row['schema'] = 'source_control'
    elif bad == 'extra_field': row['selection_coefficient'] = 0.
    elif bad == 'missing_field': del row['target_age_updates']
    elif bad == 'wrong_shape': row['scores'] = row['scores'][:, :1]
    elif bad == 'float32': row['scores'] = row['scores'].astype(np.float32)
    elif bad == 'list_scores': row['scores'] = row['scores'].tolist()
    elif bad == 'nan': row['scores'][0, 0, 0] = np.nan
    elif bad == 'inf': row['scores'][0, 0, 0] = np.inf
    elif bad == 'negative_fidelity': row['scores'][0, 0, 0] = -.01
    elif bad == 'over_one': row['scores'][0, 0, 5] = 1.01
    elif bad == 'over_projection': row['scores'][0, 0, 3] = 2.01
    elif bad == 'amplitude_exceeds_sign': row['scores'][0, 0, 0] = .8
    elif bad == 'whole_exceeds_active': row['scores'][0, 0, 4] = .8
    with pytest.raises(ValueError):
        p.summarize(records)


def synthetic_final_pair():
    record = synthetic_score_records()[0]
    raw = dict(descendant_scores=np.repeat(record['scores'][None], 5, axis=0),
               descendant_age_fissions=np.full(5, 8),
               descendant_age_updates=np.array([3500, 3501, 3550, 3750, 4000]))
    raw['descendant_scores'][:-1, ..., 0] = .125
    meta = dict(tissue=41000, replicate=0, config=asdict(p.CONFIG))
    return raw, meta, record


def test_endpoint_extraction_is_final_not_tail_mean_and_owns_arrays():
    raw, meta, expected = synthetic_final_pair()
    result = p.final_score_record(raw, meta)
    for key in result:
        if key != 'scores': assert result[key] == expected[key]
    np.testing.assert_array_equal(result['scores'], expected['scores'])
    result['scores'].flat[0] += .01
    np.testing.assert_array_equal(raw['descendant_scores'][-1], expected['scores'])


@pytest.mark.parametrize('bad', ['short_config', 'missing_time', 'earlier_age', 'last_age', 'float_age', 'float_updates'])
def test_endpoint_rejects_disposable_or_ambiguous_clock(bad):
    raw, meta, _ = synthetic_final_pair()
    if bad == 'short_config': meta['config'] = asdict(p.SHORT)
    elif bad == 'missing_time': raw['descendant_scores'] = raw['descendant_scores'][1:]
    elif bad == 'earlier_age': raw['descendant_age_updates'][0] = 0
    elif bad == 'last_age': raw['descendant_age_fissions'][-1] = 7
    elif bad == 'float_age': raw['descendant_age_fissions'] = raw['descendant_age_fissions'].astype(float)
    elif bad == 'float_updates': raw['descendant_age_updates'] = raw['descendant_age_updates'].astype(float)
    with pytest.raises(ValueError):
        p.final_score_record(raw, meta)


@pytest.mark.parametrize('effect', [-.125, 0., .125])
def test_zero_width_interval_is_not_a_scientific_gate(effect):
    records = synthetic_score_records()
    for row in records:
        row['scores'][2, 0, 0] = .5+effect
    result = p.summarize(records)
    assert p.checker().check_summary(records, result)
    assert result['primary']['interval95'] == [effect, effect]
    assert result['analysis']['scientific_pass_threshold'] is None


def test_summary_checker_does_not_call_production_analysis_or_quantiles(synthetic_summary, monkeypatch):
    records, result = synthetic_summary
    def forbidden(*args, **kwargs): raise AssertionError('production arithmetic reused')
    for name in ('summarize', 'ordered_final_scores', 'contrasts', 'analysis_contract', '_validate_score_record'):
        monkeypatch.setattr(p, name, forbidden)
    monkeypatch.setattr(np, 'quantile', forbidden)
    assert p.checker().check_summary(records, result)


@pytest.mark.parametrize('bad', ['schema', 'analysis', 'unit_order', 'axes', 'absolute_lives',
    'absolute_blocks', 'absolute_mean', 'effect_lives', 'effect_blocks', 'effect_mean',
    'block_directions', 'life_directions', 'direction_shape', 'missing_contrast', 'extra_contrast', 'extra_row_field',
    'primary_mean', 'primary_metric', 'primary_interval', 'bootstrap_tail', 'draw_hash', 'interval_nan'])
def test_summary_corruptions_detected(synthetic_summary, bad):
    records, original = synthetic_summary; result = deepcopy(original)
    effect = result['contrasts'][p.PRIMARY_KEY]
    if bad == 'schema': result['schema'] = 'other'
    elif bad == 'analysis': result['analysis']['tissue_blocks'] = 16
    elif bad == 'unit_order': result['unit_order'].reverse()
    elif bad == 'axes': result['axes']['arms'].reverse()
    elif bad == 'absolute_lives': result['absolute']['per_life'][0][0][0][0][0] += .01
    elif bad == 'absolute_blocks': result['absolute']['per_tissue'][0][0][0][0] += .01
    elif bad == 'absolute_mean': result['absolute']['mean'][0][0][0] += .01
    elif bad == 'effect_lives': effect['per_life'][0][0][0] += .01
    elif bad == 'effect_blocks': effect['per_tissue'][0][0] += .01
    elif bad == 'effect_mean': effect['mean'][0] += .01
    elif bad == 'block_directions': effect['tied_tissues'][0] += 1
    elif bad == 'life_directions': effect['positive_lives'][0] += 1
    elif bad == 'direction_shape': effect['positive_tissues'].append(0)
    elif bad == 'missing_contrast': del result['contrasts'][p.PRIMARY_KEY]
    elif bad == 'extra_contrast': result['contrasts']['unregistered'] = deepcopy(effect)
    elif bad == 'extra_row_field': effect['selection_coefficient'] = 0.
    elif bad == 'primary_mean': result['primary']['mean'] += .01
    elif bad == 'primary_metric': result['primary']['metric'] = 'ever_projection'
    elif bad == 'primary_interval': result['primary']['interval95'][0] += .01
    elif bad == 'bootstrap_tail': result['primary']['bootstrap_means'][-1] += .01
    elif bad == 'draw_hash': result['primary']['draw_indices_sha256'] = '0'*64
    elif bad == 'interval_nan': result['primary']['interval95'][0] = float('nan')
    with pytest.raises(AssertionError):
        p.checker().check_summary(records, result)


@pytest.mark.parametrize('name', tuple(p.contrasts(np.zeros((3, 8, 6)))))
def test_every_pooled_contrast_independently_checked(synthetic_summary, name):
    records, original = synthetic_summary; result = deepcopy(original)
    result['contrasts'][name]['mean'][5] += .01
    with pytest.raises(AssertionError):
        p.checker().check_summary(records, result)


@pytest.fixture(scope='module')
def dynamic_example():
    if os.environ.get('L21_ENABLE_DYNAMICS') != '1':
        pytest.skip('actual dynamics pending explicit opt-in and external launch headroom')
    p.source.preflight(DEFAULT_EXTERNAL_ROOT)
    return p.execute_pair(p.DISPOSABLE, 0, root=DEFAULT_EXTERNAL_ROOT, cfg=p.SHORT)


def test_dynamic_full_independent_replay(dynamic_example):
    raw, meta = dynamic_example
    assert p.checker().replay_pair(raw, meta, p.context(p.DISPOSABLE), p.SHORT,
                                  root=DEFAULT_EXTERNAL_ROOT) <= 1e-10
    assert p.checker().check_contrasts(raw['descendant_scores'][-1], p.contrasts(raw['descendant_scores'][-1]))


def test_dynamic_common_founder_and_exact_writer_off(dynamic_example):
    raw, _ = dynamic_example
    np.testing.assert_array_equal(raw['founder'][3], raw['native'])
    assert p.checker().check_boundary(raw) and p.checker().check_metrics(raw)


def test_dynamic_intact_unforked_and_rate_order_aliases(dynamic_example):
    raw, _ = dynamic_example; ctx = p.context(p.DISPOSABLE)
    # An ordinary, three-rate source-physics continuation must match arm 0.
    for order in ((0, 1, 2), (2, 0, 1)):
        random = p.SharedNoise(p.DISPOSABLE, 0, f'cycle_{p.SHORT.cycles}')
        before = np.take(raw['prefix_ends'][-1], order, axis=1)
        state, fresh = p.cut(ctx, before, random)
        rates = np.take(np.array(p.RATES), order)
        for _ in range(p.SHORT.inter_fission):
            state = p.advance(ctx, state, random, rates, p.SHORT)
        np.testing.assert_array_equal(state, np.take(raw['descendants'][-1, :, :, 0], order, axis=1))
        np.testing.assert_array_equal(fresh, np.broadcast_to(raw['fresh'][-1], fresh.shape))


@pytest.mark.parametrize('key', ['initial', 'founder', 'target', 'prefix_cuts', 'prefix_ends',
    'fresh', 'last_cut', 'descendants', 'prefix_scores', 'descendant_scores',
    'prefix_age_fissions', 'descendant_age_fissions', 'descendant_age_updates'])
def test_dynamic_replay_rejects_corrupted_retention(dynamic_example, key):
    raw, meta = deepcopy(dynamic_example)
    if raw[key].dtype == bool: raw[key].flat[0] = ~raw[key].flat[0]
    else: raw[key].flat[0] += 1
    with pytest.raises(AssertionError):
        p.checker().replay_pair(raw, meta, p.context(p.DISPOSABLE), p.SHORT,
                                root=DEFAULT_EXTERNAL_ROOT)
