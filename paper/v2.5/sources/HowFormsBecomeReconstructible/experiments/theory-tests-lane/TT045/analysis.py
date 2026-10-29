"""Paired future estimates conditional on fixed states; separate source blocks."""
from common import *


def units(x):
    x = np.asarray(x); assert np.isfinite(x).all(); u = np.rint(x*12).astype(np.int16)
    near(u/12, x); assert np.isin(u, (0, 3, 4, 6, 12)).all(); return u


def contrasts(x): return np.einsum('qa,na...->nq...', COEFFICIENTS, x)
def counts(x): return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)
def mcse(x, axis): return np.std(x, axis=axis, ddof=1)/np.sqrt(x.shape[axis])


def joint(a, b):
    return np.stack([np.stack([((np.sign(a) == i)&(np.sign(b) == j)).sum(0)
                    for j in (-1, 0, 1)], axis=-1) for i in (-1, 0, 1)], axis=-2)


def masks(view, world):
    if view == 'all_masks': return list(range(4))
    if view.startswith('mask:'): return [MASKS.index(view[5:])]
    return [m for m in range(4) if GEOMETRIES[geometry(m, world)] == view[9:]]


def decompositions(x):
    exact(x[:, 4], x[:, 0]+x[:, 3]); exact(x[:, 4], x[:, 2]+x[:, 1])
    exact(x[:, 6], x[:, 1]-x[:, 0]); exact(x[:, 6], x[:, 3]-x[:, 2])


def local(data):
    out = {}
    for p in PROFILES:
        for suffix in ('', '_margin'):
            x = data[p+suffix]/(1 if suffix else 12)
            out[p+suffix+'_mean'] = x.mean(3); out[p+suffix+'_mc_se'] = mcse(x, 3)
            delta = x[:, 1]-x[:, 0]
            out[p+suffix+'_packet_mean'] = delta.mean(2); out[p+suffix+'_packet_mc_se'] = mcse(delta, 2)
    return out


def block(cases, data):
    lookup = {case_key(c):i for i,c in enumerate(cases)}; n = len(CONDITIONS); nf = data['continuing'].shape[3]
    assert len(cases) == len(lookup) == 1152 and nf >= 2
    nb = data['fresh'].shape[2]; assert nb in (1, 4)
    for p, birth_count in (('continuing', 1), ('fresh', nb)):
        assert data[p].shape == data[p+'_margin'].shape == (1152, 2, birth_count, nf, 6, 4)
        assert data[p].dtype == np.int16 and np.isin(data[p], (0, 3, 4, 6, 12)).all()
        assert np.isfinite(data[p+'_margin']).all()
    assert data['original'].shape == (1152, nb, 4)
    out = dict(records=np.zeros(n, dtype=np.int32), mask_cases=np.zeros(n, dtype=np.int32),
               position_futures=np.zeros(n, dtype=np.int32))
    fs = dict(levels=(4, 6, 4), effects=(7, 6, 4), level_mc_se=(4, 6, 4), effect_mc_se=(7, 6, 4),
        margin_levels=(4, 6, 4), margin_effects=(7, 6, 4), margin_level_mc_se=(4, 6, 4), margin_effect_mc_se=(7, 6, 4),
        future_levels=(4, nf, 6, 4), future_effects=(7, nf, 6, 4),
        future_margin_levels=(4, nf, 6, 4), future_margin_effects=(7, nf, 6, 4),
        temporal_change=(4, 4), temporal_mc_se=(4, 4), future_temporal_change=(4, nf, 4), original_levels=(4,))
    cs = dict(record_counts=(7, 6, 4, 3), case_counts=(7, 6, 4, 3), future_counts=(7, 6, 4, 3),
        timing_joint_record=(7, 4, 3, 3), timing_joint_future=(7, 4, 3, 3),
        temporal_counts=(4, 4, 3), temporal_future_counts=(4, 4, 3))
    for k, shape in fs.items(): out[k] = np.full((n, *shape), np.nan)
    for k, shape in cs.items(): out[k] = np.zeros((n, *shape), dtype=np.int64)
    for j, condition in enumerate(CONDITIONS):
        damage, family, group, view, source = condition.split('|'); worlds = []
        for w in range(16):
            h = cases[lookup[damage, family, MASKS[0], source, w]]['developed_score']
            if group == 'all' or group == f'message:{w//4}' or (group == 'history:unique_pass' and h == 1) or (group == 'history:other' and h != 1): worlds.append(w)
        if not worlds: continue
        ids = np.array([[lookup[damage, family, MASKS[m], source, w] for m in masks(view, w)] for w in worlds]); flat = ids.ravel()
        out['records'][j] = len(worlds); out['mask_cases'][j] = len(flat); out['position_futures'][j] = len(worlds)*nf
        # Each profile uses its actual fixed states; all profiles use the same futures.
        per_future = np.concatenate([data[p][ids].mean((1, 3)) for p in PROFILES], axis=1)
        delta = contrasts(per_future); decompositions(delta)
        assert np.all(delta[:, (0, 1, 6), :, 0] == 0), 'packets cannot change initial body expression'
        for prefix, value in (('', per_future/12), ('margin_', np.concatenate([data[p+'_margin'][ids].mean((1, 3)) for p in PROFILES], axis=1))):
            future_levels = value.mean(0) if prefix else per_future.mean(0)/12
            future_effects = contrasts(value).mean(0) if prefix else delta.mean(0)/12
            out['future_'+prefix+'levels'][j] = future_levels; out['future_'+prefix+'effects'][j] = future_effects
            out[prefix+'levels'][j] = future_levels.mean(1); out[prefix+'effects'][j] = future_effects.mean(1)
            out[prefix+'level_mc_se'][j] = mcse(future_levels, 1); out[prefix+'effect_mc_se'][j] = mcse(future_effects, 1)
        position_delta = delta.mean(2)
        future_delta = delta.transpose(0, 2, 1, 3, 4).reshape(-1, 7, 6, 4)
        injury = np.concatenate([data[p][flat].mean((2, 3)) for p in PROFILES], axis=1)
        out['record_counts'][j] = counts(position_delta); out['case_counts'][j] = counts(contrasts(injury))
        out['future_counts'][j] = counts(future_delta)
        out['timing_joint_record'][j] = joint(position_delta[:, :, 4], position_delta[:, :, 5])
        out['timing_joint_future'][j] = joint(future_delta[:, :, 4], future_delta[:, :, 5])
        for field, values in (('timing_joint_record', 'record_counts'), ('timing_joint_future', 'future_counts')):
            np.testing.assert_array_equal(out[field][j].sum(-1), out[values][j, :, 4])
            np.testing.assert_array_equal(out[field][j].sum(-2), out[values][j, :, 5])
        temporal = per_future[:, :, :, 5]-per_future[:, :, :, 4]
        future_temporal = temporal.mean(0)/12
        out['future_temporal_change'][j] = future_temporal; out['temporal_change'][j] = future_temporal.mean(1)
        out['temporal_mc_se'][j] = mcse(future_temporal, 1); out['temporal_counts'][j] = counts(temporal.mean(2))
        out['temporal_future_counts'][j] = counts(temporal.transpose(0, 2, 1, 3).reshape(-1, 4, 4))
        assert np.all(out['record_counts'][j].sum(-1) == len(worlds))
        assert np.all(out['case_counts'][j].sum(-1) == len(flat))
        assert np.all(out['future_counts'][j].sum(-1) == len(worlds)*nf)
        out['original_levels'][j] = data['original'][ids].mean((0, 1, 2))/12
    return out


def combine(blocks):
    out = {}; n = np.stack([b['records'] for b in blocks])
    for key in blocks[0]:
        a = np.stack([b[key] for b in blocks]); out['block_'+key] = a
        if np.issubdtype(a.dtype, np.integer): out[key] = a.sum(0); continue
        if key.startswith('future_'): continue  # Separate seed banks; retain their identities by block.
        w = n.reshape((*n.shape, *(1 for _ in range(a.ndim-2)))); ok = w > 0; v = np.where(ok, a, 0)
        if key.endswith('_mc_se'):
            equal_num = np.sqrt(np.square(v).sum(0)); pooled_num = np.sqrt(np.square(v*w).sum(0))
        else: equal_num = v.sum(0); pooled_num = (v*w).sum(0)
        out['equal_'+key] = np.divide(equal_num, ok.sum(0), out=np.full_like(a[0], np.nan), where=ok.sum(0)>0)
        out['pooled_'+key] = np.divide(pooled_num, w.sum(0), out=np.full_like(a[0], np.nan), where=w.sum(0)>0)
    return out


def report(a, role):
    lines = ['# TT045 — fresh forcing on fixed states and packets', '',
        f'Role: {role}; {futures(role)} new futures per fixed state; {len(selected(role))} exposed source blocks.',
        'C is one continuing state; F is the equally weighted empirical mixture of saved fresh states. All states receive all new futures.',
        'T0/T1 are the actual preserved/late-written packets. Memory feedback and writing are off.',
        'Monte Carlo SE conditions on these fixed source records; it is not population uncertainty. Individual estimates remain coarse.', '']
    for damage in DAMAGE:
        j = INDEX[f'{damage}|residual|all|all_masks|own']; lines += [f'## {damage}: residual / own / all histories and masks', '',
            '| Contrast | 900 effect (pp) | MC SE (pp) | 1000 effect (pp) | MC SE (pp) |', '|---|---:|---:|---:|---:|']
        for q, name in enumerate(COMPARISONS):
            v = 100*a['equal_effects'][j, q, :, 0]; se = 100*a['equal_effect_mc_se'][j, q, :, 0]
            lines.append(f'| {name} | {v[4]:.6f} | {se[4]:.6f} | {v[5]:.6f} | {se[5]:.6f} |')
        lines += ['', 'Absolute success (%) at 900 / 1000 in C-T0/C-T1/F-T0/F-T1 order:',
            str((100*a['equal_levels'][j, :, 4:, 0]).tolist()), '', 'Injury-case harm/tie/gain at 900 / 1000, averaging actual states and futures:']
        for q,name in enumerate(COMPARISONS): lines.append(name+': '+str(a['case_counts'][j, q, 4:, 0].tolist()))
        lines += ['', 'Block effects at 900 / 1000 (pp), fixed source order:']
        for q,name in enumerate(COMPARISONS): lines.append(name+': '+str((100*a['block_effects'][:, j, q, 4:, 0]).tolist()))
        lines += ['', 'Secondary margin effects at 900 / 1000:', str(a['equal_margin_effects'][j, :, 4:, 0].tolist()),
            '', 'Historical original-packet recipient score (%; old randomness): '+str(float(100*a['equal_original_levels'][j, 0])), '']
    lines += ['All cases, fixed-state estimates, paired signs, timing-sign joint counts, future means and both metrics remain in saved arrays.',
        'New forcing futures do not create new source records. Four production blocks remain the population units.',
        'TT044 endpoints are saved separately as historical data. No serial writing, new population confirmation or uninterrupted-performance claim.', '']
    return '\n'.join(lines)


def summary(directory, role):
    ids = selected(role); blocks = [arrays(directory/f'tissue_{i}'/'AGGREGATE.npz') for i in ids]
    a = combine(blocks); save(directory/'SUMMARY.npz', a)
    with (directory/'REPORT.md').open('x') as f: f.write(report(a, role))
    write(directory/'AXES.json', dict(conditions=CONDITIONS, profiles=PROFILES, arms=ARMS, times=TIMES, credits=CREDITS,
        comparisons=COMPARISONS, coefficients=COEFFICIENTS.tolist(), signs=SIGNS,
        endpoint_axes=['case', 'packet', 'fixed_starting_state', 'new_future', 'relative_time', 'credit'],
        actual_starting_states={p:initial_count(p, role) for p in PROFILES}, new_futures_per_fixed_state=futures(role),
        fixed_state_mean_axes=['case','packet','fixed_starting_state','relative_time','credit'],
        fixed_state_packet_mean_axes=['case','fixed_starting_state','relative_time','credit'],
        timing_joint_axes=['contrast','credit','sign_at_900','sign_at_1000'],
        future_summary_axes=['condition','arm_or_contrast','new_future','relative_time','credit'],
        mc_se_scope='conditional on fixed source records; entire block/future is the simulation replicate',
        probability_storage='integer twelfths', margin_storage='float64 credit-versus-best-other',
        restored_state_crossed_with_every_new_future=True, historical_outcomes_separate=True))
    proofs = [read(directory/f'tissue_{i}'/'CHECK.json')['verification'] for i in ids]
    return {k:max(p[k] for p in proofs) if k == 'max_native_error' else sum(p[k] for p in proofs) for k in proofs[0]}
