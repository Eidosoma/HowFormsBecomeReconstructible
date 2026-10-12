"""Independent D111 construction, observation, statistics and native replay.

Uses D097's independently restated physics; does not call D111's production
birth, rank matcher, simulator, measurement or summarizer. Not clean-room/E6.
"""
from dataclasses import asdict

import numpy as np

from laws_confirmation import l15_repair_speed as native
from laws_confirmation.io import canonical_digest

physics = native.checker()
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l16-body-content-v1'
KINDS = ('intact', 'shuffled', 'alternative', 'sham', 'full_own', 'full_alternative')
CASES = tuple((r, g, k) for r in (0, 1) for g in (.2, 0.) for k in KINDS)
METRICS = ('own_fidelity', 'alternative_fidelity', 'amp_fraction', 'body_mean',
           'body_rms', 'reference_mean', 'reference_rms', 'vr_mae', 'roughness')


def mask():
    y, x = np.indices((16, 16))
    return (y >= 4) & (y < 12) & (x >= 4) & (x < 12)


def ranked(values, guide):
    order = sorted(range(len(guide)), key=lambda i: (float(guide[i]), i))
    result = np.empty_like(values)
    ordered_values = sorted(values.tolist())
    for value, address in zip(ordered_values, order):
        result[address] = value
    return result


def initial(sources, role, kind, perm, resting):
    original, donor = sources[role, 0], sources[1-role, 0]
    body = original.copy()
    if kind == 'full_alternative':
        body[:] = ranked(original.flatten(), donor.flatten()).reshape(16, 16)
    elif kind != 'full_own':
        body[mask()] = resting
        addresses = np.flatnonzero(~mask())
        values = original.ravel()[addresses]
        if kind == 'shuffled':
            body.ravel()[addresses] = values[perm]
        elif kind in ('alternative', 'sham'):
            guide = donor if kind == 'alternative' else original
            body.ravel()[addresses] = ranked(values, guide.ravel()[addresses])
    return np.stack([body, body.copy(), sources[role, 2].copy()])


def settle(tissue, ladder, bp, theta, random, seed, futures, steps):
    field = np.full((16, 16), -1.)
    if seed == 0:
        field[:, :8] = 1.
    else:
        assert seed == 1
        field[:8] = 1.
    v = np.repeat(field[None], futures, axis=0)
    v += tissue.copy_jitter * random.standard_normal(v.shape)
    state = (v, v.copy(), v.copy())
    for _ in range(steps):
        state = physics.step(*state, theta, tissue, ladder, bp.c_m, bp.rho,
                             random.standard_normal(v.shape))
    return np.stack(state)


def observe(raw, cfg):
    rows = []
    addresses = np.flatnonzero(mask())
    for ci, (role, _, _) in enumerate(CASES):
        own = raw['sources'][role, 0].ravel()[addresses] > 0
        other = raw['sources'][1-role, 0].ravel()[addresses] > 0
        times = []
        for v, _, ref in raw['states'][ci]:
            eligible = abs(v) > cfg.amp_threshold
            signs = v.ravel()[addresses] > 0
            ok = eligible.ravel()[addresses]
            times.append([np.count_nonzero((signs == own) & ok)/64,
                np.count_nonzero((signs == other) & ok)/64,
                eligible.sum()/256, v.sum()/256, np.sqrt((v*v).sum()/256),
                ref.sum()/256, np.sqrt((ref*ref).sum()/256), abs(v-ref).sum()/256,
                (abs(v-v[:, (np.arange(16)-1) % 16]).sum() +
                 abs(v-v[(np.arange(16)-1) % 16, :]).sum())/512])
        rows.append(times)
    return np.asarray(rows, dtype=np.float64)


def check_life(raw, meta, cfg, replay=True):
    expected = dict(theta=(16, 16), sources=(2, 3, 16, 16), permutations=(2, 192),
                    states=(24, len(cfg.times), 3, 16, 16), values=(24, len(cfg.times), 9))
    assert set(raw) == set(expected)
    for key, shape in expected.items():
        assert raw[key].shape == shape and np.isfinite(raw[key]).all()
        assert raw[key].dtype == (np.int64 if key == 'permutations' else np.float64)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    assert type(meta['life']) is int and 0 <= meta['life'] < cfg.lives
    assert meta['theta_writable'] is False and meta['donor_reference_transferred'] is False
    assert meta['ema_reset_to_birth_v'] is True
    tissue, ladder, bp = physics.parameters(meta)
    theta = tissue.threshold_spread * generator(tissue.tissue_tag, meta['index']).standard_normal((16, 16))
    maximum = compare(raw['theta'], theta)
    source_rng = []
    for role in (0, 1):
        random = generator(TAG, meta['index'], meta['life'], 'settle')
        # Always rebuild source states, even during the saved read-only audit.
        state = settle(tissue, ladder, bp, theta, random, role, 1, cfg.settle)[:, 0]
        maximum = max(maximum, compare(raw['sources'][role], state))
        source_rng.append(canonical_digest(random.bit_generator.state))
        perm = generator(TAG, meta['index'], meta['life'], f'shuffle:{role}').permutation(192)
        np.testing.assert_array_equal(raw['permutations'][role], perm)
    nested(meta['source_rng'], source_rng)
    assert len(set(meta['source_rng'])) == 1
    for ci, (role, gain, kind) in enumerate(CASES):
        start = initial(raw['sources'], role, kind, raw['permutations'][role], tissue.resting)
        np.testing.assert_array_equal(raw['states'][ci, 0], start)
        if kind not in ('full_own', 'full_alternative'):
            assert np.all(start[0, mask()] == tissue.resting)
            np.testing.assert_array_equal(np.sort(start[0, ~mask()]), np.sort(raw['sources'][role, 0, ~mask()]))
        else:
            np.testing.assert_array_equal(np.sort(start[0].ravel()), np.sort(raw['sources'][role, 0].ravel()))
        np.testing.assert_array_equal(start[2], raw['sources'][role, 2])
        if kind == 'sham':
            match = CASES.index((role, gain, 'intact'))
            np.testing.assert_array_equal(raw['states'][ci], raw['states'][match])
        random = generator(TAG, meta['index'], meta['life'], 'regrow')
        if replay:
            state = tuple(x[None].copy() for x in start)
            saved = [start]
            for t in range(1, cfg.recovery+1):
                state = physics.step(*state, theta, tissue, ladder, gain, bp.rho,
                                     random.standard_normal((1, 16, 16)))
                if t in cfg.times:
                    saved.append(np.stack([x[0] for x in state]))
            maximum = max(maximum, compare(raw['states'][ci], np.stack(saved)))
        else:
            for _ in range(cfg.recovery):
                random.standard_normal((1, 16, 16))
        assert meta['branch_rng'][ci] == canonical_digest(random.bit_generator.state)
    assert len(meta['branch_rng']) == 24 and len(set(meta['branch_rng'])) == 1
    observed = observe(raw, cfg)
    np.testing.assert_array_equal(raw['values'][..., :3], observed[..., :3])
    np.testing.assert_allclose(raw['values'], observed, rtol=0, atol=1e-12)
    metric_error = float(np.max(abs(raw['values']-observed)))
    # Stored complete replay is a proof record, not a fresh dynamics replay.
    if not replay:
        assert meta['replay']['full_life_replay'] is True
        assert 0 <= meta['replay']['max_abs'] <= 1e-10
        assert meta['replay']['exact_sham_aliases'] == 4
    return dict(full_life_replay=bool(replay), max_abs=max(maximum, metric_error),
                dynamics_max_abs=maximum, metric_max_abs=metric_error, exact_sham_aliases=4)


def check_block(raw, meta, cfg, replay=False):
    nested(meta['config'], asdict(cfg))
    assert len(meta['lives']) == cfg.lives and type(meta['index']) is int
    assert all(v.shape[0] == cfg.lives for v in raw.values())
    for life in range(cfg.lives):
        m = meta['lives'][life]
        assert m['index'] == meta['index'] and m['life'] == life
        check_life({k: v[life] for k, v in raw.items()}, m, cfg, replay)
    return True


def statistics(values, draws):
    assert values.ndim == 2 and values.shape[0] == 8 and np.isfinite(values).all()
    tissue = np.sum(values, axis=1) / values.shape[1]
    means = tissue[draws].sum(axis=1) / 8
    result = dict(mean=float(tissue.sum()/8), block_means=tissue.tolist(), life_values=values.tolist(),
                  pointwise_block_bootstrap_95=np.percentile(means, [2.5, 97.5]).tolist())
    for prefix, array in (('block_', tissue), ('life_', values)):
        result[prefix+'positive'] = int(np.count_nonzero(array > 1e-12))
        result[prefix+'negative'] = int(np.count_nonzero(array < -1e-12))
        result[prefix+'tied'] = int(np.count_nonzero(abs(array) <= 1e-12))
    return result


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 24, len(cfg.times), 9)
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8))
    rows = []
    for ti, t in enumerate(cfg.times):
        for gi, gain in enumerate((.2, 0.)):
            for name, left, right in (('alternative_minus_shuffled_preference', 2, 1),
                    ('alternative_minus_intact_preference', 2, 0),
                    ('full_alternative_minus_full_own_preference', 5, 4)):
                effects = []
                for role in (0, 1):
                    offset = 12*role+6*gi
                    l, r = values[:, :, offset+left, ti], values[:, :, offset+right, ti]
                    effects.append((l[..., 1]-l[..., 0])-(r[..., 1]-r[..., 0]))
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', (effects[0]+effects[1])*.5)):
                    rows.append(dict(name=name, gain=gain, time=t, role=role, **statistics(effect, draws)))
            effect = sum(values[:, :, 12*r+6*gi, ti, 0]-values[:, :, 12*r+6*gi+1, ti, 0] for r in (0, 1))*.5
            rows.append(dict(name='intact_minus_shuffled_own_fidelity', gain=gain, time=t,
                role='both', **statistics(effect, draws)))
    selected = {(r['name'], r['gain'], r['role']): r for r in rows if r['time'] == cfg.recovery}
    primary = selected['alternative_minus_shuffled_preference', 0., 'both']
    gate = [selected['full_alternative_minus_full_own_preference', 0., r] for r in (0, 1)]
    directional = [selected['alternative_minus_shuffled_preference', 0., r] for r in (0, 1)]
    disagreement = []
    for b in blocks:
        counts = []
        for life in range(cfg.lives):
            a, z = b['sources'][life, :, 0]
            counts.append(int(((a[mask()] > 0) != (z[mask()] > 0)).sum()))
        disagreement.append(counts)
    qualified = bool(min(min(row) for row in disagreement) > 0 and
                     min(g['pointwise_block_bootstrap_95'][0] for g in gate) > 0)
    positive = primary['pointwise_block_bootstrap_95'][0] > 0 and min(r['mean'] for r in directional) > 0
    expected = dict(schema='l16_body_content_qualification_v1', tissues=list(range(56000, 56008)),
        primary=primary, readout_gates=gate, directional_primary=directional,
        readout_qualified=qualified, label=('READOUT_NOT_QUALIFIED' if not qualified else
            'QUALIFIED_CONTEXT_STEERING' if positive else 'CONTEXT_STEERING_UNRESOLVED'),
        target_disagreement_cells=disagreement, contrasts=rows, cell_means=values.mean(axis=(0, 1)).tolist(),
        cases=[list(c) for c in CASES], times=list(cfg.times), metrics=list(METRICS), blocks=8,
        lives_per_block=cfg.lives, independent_main_confirmation_run=False,
        secondary_intervals_multiplicity_adjusted=False, absolute_fidelity_gate=None)
    nested(summary, expected)
    return True


def check_source(raw, meta):
    from hidden_genome.config import KnifeConfig
    nested(meta['config'], asdict(KnifeConfig()))
    assert set(raw) == {'theta', 'sources', 'finals'}
    assert raw['sources'].shape == (2, 3, 8, 16, 16) and raw['finals'].shape == (20, 8, 16, 16)
    tissue, ladder, bp = physics.parameters(meta)
    index = meta['index']; assert index in range(6)
    theta = tissue.threshold_spread * generator(tissue.tissue_tag, index).standard_normal((16, 16))
    maximum = compare(raw['theta'], theta)
    for i, phase in enumerate(('settle', 'alt')):
        expected = settle(tissue, ladder, bp, theta, generator('hidden-genome-v1', phase, index), i, 8, 120)
        maximum = max(maximum, compare(raw['sources'][i], expected))
    region = np.zeros((16, 16), bool); region[:8, :8] = True
    changed = theta.copy()
    changed[region] = generator('hidden-genome-v1', 'knife', index).permutation(theta[region])
    zero = theta.copy(); zero[region] = 0.
    variants = dict(intact=theta, scrambled=changed, zeroed=zero)
    table = dict(tissue=index, fidelity={}, fidelity_vs_alt={}, floor={})
    counter = 0
    for label, gain in (('R_on', .2), ('R_off', 0.)):
        for context, th in [('floor', 'intact')] + [(c, t) for c in ('intact', 'reset', 'transplant')
                                                   for t in ('intact', 'scrambled', 'zeroed')]:
            v = raw['sources'][0, 0].copy()
            if context != 'floor':
                v[:, region] = tissue.resting
            if context == 'reset':
                v[:, ~region] = tissue.resting
            elif context == 'transplant':
                v[:, ~region] = raw['sources'][1, 0, :, ~region].T
            state = (v, v.copy(), raw['sources'][0, 2].copy())
            random = generator('hidden-genome-v1', 'regrow', index)
            for _ in range(240):
                state = physics.step(*state, variants[th], tissue, ladder, gain, bp.rho,
                                     random.standard_normal((8, 16, 16)))
            maximum = max(maximum, compare(raw['finals'][counter], state[0])); counter += 1
            score = lambda ref: float(np.mean(np.mean((((state[0] > 0) == (ref > 0)) &
                                       (abs(state[0]) > .2))[:, region], axis=-1)))
            if context == 'floor':
                table['floor'][label] = score(raw['sources'][0, 0])
            else:
                key = f'{label}|{context}|{th}'
                table['fidelity'][key] = score(raw['sources'][0, 0])
                table['fidelity_vs_alt'][key] = score(raw['sources'][1, 0])
    nested(meta['result'], table)
    difference = (raw['sources'][0, 0] > 0) != (raw['sources'][1, 0] > 0)
    return dict(full_source_replay=True, max_abs=maximum, branches=20, futures_per_branch=8,
        old_region_disagreement=difference[:, region].sum(axis=1).tolist(),
        centred_region_disagreement=difference[:, mask()].sum(axis=1).tolist())


if __name__ == '__main__':
    from laws_confirmation.l16_body_content_run import main
    main(default_command='audit')
