"""Independent D114 construction, observer, statistics and full native replay.

Uses D097's separately restated equations. Does not use D114's production
constructor, simulator, observer or summarizer. Shared source, not clean-room.
"""
from dataclasses import asdict

import numpy as np

from laws_confirmation import l15_repair_speed as native
from laws_confirmation.io import canonical_digest

physics = native.checker()
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l16-theta-content-v1'
KINDS = ('aligned', 'shuffled', 'sham', 'off', 'body_own', 'body_alternative')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = ('own_qualified', 'alternative_qualified', 'own_sign', 'alternative_sign',
    'amp_fraction', 'body_mean', 'body_rms', 'clip_fraction', 'roughness',
    'reference_mean', 'reference_rms', 'vr_mae')


def targets():
    y, x = np.indices((16, 16))
    return np.stack([np.where(y < 8, 1., -1.), np.where((x//4) % 2 == 0, 1., -1.)])


def projected(target, norm):
    x = np.tanh(1.5*target)
    x = x-x.mean()
    return x*(norm/max(float(x.std()), 1e-9))


def fields(perms, cfg):
    aligned = [projected(t, cfg.norm) for t in targets()]
    rows = []
    for role, kind in CASES:
        field = aligned[role].copy()
        if kind == 'shuffled':
            field = np.asarray([field.ravel()[i] for i in perms[role]]).reshape(16, 16)
        elif kind == 'sham':
            shuffled = field.ravel()[perms[role]]
            restored = np.empty(256, dtype=np.float64)
            for j, address in enumerate(perms[role]): restored[address] = shuffled[j]
            field = restored.reshape(16, 16)
        elif kind != 'aligned': field[:] = 0.
        rows.append(field)
    return np.stack(rows)


def birth(common, role, kind):
    body = common.copy()
    if kind == 'body_own': body = targets()[role]
    elif kind == 'body_alternative': body = targets()[1-role]
    return np.stack((body, body.copy(), common.copy()))


def observe(raw, cfg):
    table = []
    for ci, (role, _) in enumerate(CASES):
        rows = []
        for v, _, ref in raw['states'][ci]:
            eligible = abs(v) > cfg.amp_threshold
            own = (v > 0) == (raw['targets'][role] > 0)
            other = (v > 0) == (raw['targets'][1-role] > 0)
            rough = (abs(v-v[:, (np.arange(16)-1) % 16]).sum() +
                     abs(v-v[(np.arange(16)-1) % 16, :]).sum())/512
            rows.append([np.count_nonzero(own & eligible)/256,
                np.count_nonzero(other & eligible)/256, np.count_nonzero(own)/256,
                np.count_nonzero(other)/256, eligible.sum()/256, v.sum()/256,
                np.sqrt((v*v).sum()/256), np.count_nonzero(abs(v) == 2)/256, rough,
                ref.sum()/256, np.sqrt((ref*ref).sum()/256), abs(v-ref).sum()/256])
        table.append(rows)
    return np.asarray(table, dtype=np.float64)


def check_life(raw, meta, cfg, replay=True):
    metadata = {'index', 'life', 'config', 'cases', 'tissue', 'ladder', 'blueprint',
        'birth_rng', 'branch_rng', 'gain', 'theta_writable', 'target_reference_supplied',
        'primary_births_identical'}
    assert set(meta) in (metadata, metadata | {'replay'})
    expected = dict(targets=(2, 16, 16), common=(16, 16), permutations=(2, 256),
        theta=(12, 16, 16), states=(12, len(cfg.times), 3, 16, 16),
        values=(12, len(cfg.times), 12))
    assert set(raw) == set(expected)
    for key, shape in expected.items():
        assert raw[key].shape == shape and np.isfinite(raw[key]).all()
        assert raw[key].dtype == (np.int64 if key == 'permutations' else np.float64)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    assert type(meta['life']) is int and 0 <= meta['life'] < cfg.lives
    assert meta['theta_writable'] is False and meta['target_reference_supplied'] is False
    assert meta['primary_births_identical'] is True and meta['gain'] == 0.
    tissue, ladder, bp = physics.parameters(meta)
    index, life = meta['index'], meta['life']
    np.testing.assert_array_equal(raw['targets'], targets())
    random = generator(TAG, index, life, 'birth')
    common = .2*random.standard_normal((16, 16))
    np.testing.assert_array_equal(raw['common'], common)
    assert canonical_digest(random.bit_generator.state) == meta['birth_rng']
    perms = np.stack([generator(TAG, index, life, f'shuffle:{r}').permutation(256) for r in (0, 1)])
    np.testing.assert_array_equal(raw['permutations'], perms)
    expected_theta = fields(perms, cfg)
    np.testing.assert_array_equal(raw['theta'], expected_theta)
    for role in (0, 1):
        baseline = raw['theta'][CASES.index((role, 'aligned'))]
        assert abs(float(baseline.mean())) <= 1e-15 and abs(float(baseline.std())-.3) <= 1e-15
        for kind in ('shuffled', 'sham'):
            np.testing.assert_array_equal(np.sort(baseline.ravel()),
                np.sort(raw['theta'][CASES.index((role, kind))].ravel()))
    maximum = 0.; endings = []
    for ci, (role, kind) in enumerate(CASES):
        start = birth(common, role, kind)
        np.testing.assert_array_equal(raw['states'][ci, 0], start)
        state = tuple(x[None].copy() for x in start)
        random = generator(TAG, index, life, 'noise')
        saved = [start.copy()]
        for t in range(1, cfg.steps+1):
            noise = random.standard_normal((1, 16, 16))
            if replay:
                state = physics.step(*state, expected_theta[ci], tissue, ladder, 0., bp.rho, noise)
                if t in cfg.times: saved.append(np.stack([x[0] for x in state]))
        if replay: maximum = max(maximum, compare(raw['states'][ci], np.stack(saved)))
        endings.append(canonical_digest(random.bit_generator.state))
    nested(meta['branch_rng'], endings)
    assert len(set(endings)) == 1
    pairs = [((r, 'aligned'), (r, 'sham')) for r in (0, 1)] + [
        ((0, 'off'), (1, 'off')), ((0, 'body_own'), (1, 'body_alternative')),
        ((1, 'body_own'), (0, 'body_alternative'))]
    for left, right in pairs:
        np.testing.assert_array_equal(raw['states'][CASES.index(left)], raw['states'][CASES.index(right)])
    observed = observe(raw, cfg)
    np.testing.assert_allclose(raw['values'], observed, rtol=0, atol=1e-12)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum,
        metric_max_abs=float(abs(raw['values']-observed).max()), exact_signs=True,
        exact_aliases=5, paired_noise=True, fixed_theta_multisets=True)


def check_block(raw, meta, cfg, replay=True):
    assert set(meta) == {'index', 'config', 'lives'}
    assert type(meta['index']) is int and meta['index'] in (*range(58000, 58008), 514214)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    for array in raw.values(): assert array.shape[0] == cfg.lives
    for life, row in enumerate(meta['lives']):
        assert row['index'] == meta['index'] and row['life'] == life
        proof = row['replay']
        assert set(proof) == {'full_life_replay', 'dynamics_max_abs', 'metric_max_abs',
                             'exact_signs', 'exact_aliases', 'paired_noise', 'fixed_theta_multisets'}
        assert all(proof[k] is True for k in ('full_life_replay', 'exact_signs', 'paired_noise', 'fixed_theta_multisets'))
        assert proof['exact_aliases'] == 5 and 0 <= proof['dynamics_max_abs'] <= 1e-10
        assert 0 <= proof['metric_max_abs'] <= 1e-12
        current = check_life({k: a[life] for k, a in raw.items()}, row, cfg, replay)
        if replay: nested(proof, current)
    return True


def stats(x, draws):
    means = np.asarray([sum(row)/len(row) for row in x])
    boot = np.add.reduce(means[draws], axis=1)/8
    result = dict(mean=float(sum(means)/8), block_means=means.tolist(), life_values=x.tolist(),
                  pointwise_block_bootstrap_95=np.quantile(boot, [.025, .975]).tolist())
    for prefix, array in (('block_', means), ('life_', x)):
        result[prefix+'positive'] = int(np.count_nonzero(array > 1e-12))
        result[prefix+'negative'] = int(np.count_nonzero(array < -1e-12))
        result[prefix+'tied'] = int(np.count_nonzero(abs(array) <= 1e-12))
    return result


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    v = np.stack([b['values'] for b in blocks])
    assert v.shape == (8, cfg.lives, 12, len(cfg.times), 12) and np.isfinite(v).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8))
    rows = []
    for observer, col in (('qualified', 0), ('sign', 2)):
        for ti, t in enumerate(cfg.times):
            for name, lk, rk in (('aligned_minus_shuffled', 'aligned', 'shuffled'),
                ('aligned_minus_off', 'aligned', 'off'),
                ('aligned_minus_wrong_field', 'aligned', 'wrong'),
                ('body_own_minus_alternative', 'body_own', 'body_alternative')):
                effects = []
                for role in (0, 1):
                    li = CASES.index((role, lk))
                    ri = CASES.index((1-role, 'aligned')) if rk == 'wrong' else CASES.index((role, rk))
                    left = v[:, :, li, ti, col]-v[:, :, li, ti, col+1]
                    right = (v[:, :, ri, ti, col+1]-v[:, :, ri, ti, col] if rk == 'wrong'
                             else v[:, :, ri, ti, col]-v[:, :, ri, ti, col+1])
                    effects.append(left-right)
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', (effects[0]+effects[1])*.5)):
                    rows.append(dict(name=name, time=t, role=role, observer=observer, **stats(effect, draws)))
    pick = lambda name, role='both': next(x for x in rows if x['name'] == name and
        x['role'] == role and x['time'] == cfg.steps and x['observer'] == 'qualified')
    primary = pick('aligned_minus_shuffled')
    directions = [pick('aligned_minus_shuffled', r) for r in (0, 1)]
    gates = [pick('body_own_minus_alternative', r) for r in (0, 1)]
    disagreements = [[int(((b['targets'][i, 0] > 0) != (b['targets'][i, 1] > 0)).sum())
                      for i in range(cfg.lives)] for b in blocks]
    readable = all(x > 0 for row in disagreements for x in row) and all(
        x['pointwise_block_bootstrap_95'][0] > 0 for x in gates)
    positive = primary['pointwise_block_bootstrap_95'][0] > 0 and all(x['mean'] > 0 for x in directions)
    label = 'READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_THETA_CONTENT' if positive else 'THETA_CONTENT_UNRESOLVED'
    expected = dict(schema='l16_theta_content_qualification_v1', tissues=list(range(58000, 58008)),
        label=label, primary=primary, directional_primary=directions, readout_gates=gates,
        readout_qualified=bool(readable), target_disagreement_cells=disagreements, contrasts=rows,
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS),
        cell_means=v.mean(axis=(0, 1)).tolist(), blocks=8, lives_per_block=cfg.lives,
        absolute_fidelity_gate=None, secondary_intervals_multiplicity_adjusted=False,
        biological_or_learned_or_heredity_claim=False, independent_confirmation=False,
        independent_unit='random-stream block; fixed target pair and effective physics')
    nested(summary, expected)
    return True


def check_source(raw, meta):
    assert set(raw) == {'theta', 'states', 'target'}
    assert raw['theta'].shape == (3, 1, 16, 16) and raw['states'].shape == (3, 5, 3, 4, 16, 16)
    assert all(a.dtype == np.float64 and np.isfinite(a).all() for a in raw.values())
    tissue, ladder, bp = physics.parameters(meta)
    from writable_landlord.config import LandlordConfig
    nested(meta['config'], asdict(LandlordConfig()))
    assert meta['index'] == 0 and meta['known_outcomes'] is True and meta['new_verification_not_historical_raw'] is True
    np.testing.assert_array_equal(raw['target'], targets()[0])
    maximum = 0.; rows = []; endings = []
    for j, norm in enumerate((.3, .4, .5)):
        theta = projected(targets()[0], norm)[None]
        np.testing.assert_array_equal(raw['theta'][j], theta)
        random = generator('writable-landlord-v1', 'capacity', norm)
        v = .2*random.standard_normal((4, 16, 16)); state = (v, v.copy(), v.copy())
        saved = [np.stack(state)]
        for t in range(1, 301):
            state = physics.step(*state, theta, tissue, ladder, 0., bp.rho,
                                 random.standard_normal((4, 16, 16)))
            if t in (1, 20, 80, 300): saved.append(np.stack(state))
        maximum = max(maximum, compare(raw['states'][j], np.stack(saved)))
        rows.append(dict(norm=norm, pin=float(((state[0] > 0) == (targets()[0] > 0)).mean())))
        endings.append(canonical_digest(random.bit_generator.state))
    nested(meta['end_rng'], endings); nested(meta['result'], dict(rows=rows, chosen=.3))
    assert [x['pin'] for x in rows] == [.9736328125, .990234375, .9951171875]
    return dict(full_source_replay=True, max_abs=maximum, paths=12, known_rows=3,
                exact_source_scalars=True, new_main_norm_selected=False)


if __name__ == '__main__':
    from laws_confirmation.l16_theta_content_run import main
    main(default_command='audit')
