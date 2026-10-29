"""Separate receiving profiles, paired feedback effects and retained harms."""
from common import *


def units(x):
    x = np.asarray(x); assert np.isfinite(x).all(); u = np.rint(x*12).astype(np.int16)
    near(u/12, x); assert np.isin(u, (0, 3, 4, 6, 12)).all(); return u


def contrasts(x): return np.einsum('qa,na...->nq...', COEFFICIENTS, x)
def counts(x): return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)


def joint(b, r):
    return np.stack([np.stack([((np.sign(b) == i) & (np.sign(r) == j)).sum(0)
                              for j in (-1, 0, 1)], axis=-1) for i in (-1, 0, 1)], axis=-2)


def masks(view, world):
    if view == 'all_masks': return list(range(4))
    if view.startswith('mask:'): return [MASKS.index(view[5:])]
    return [m for m in range(4) if GEOMETRIES[geometry(m, world)] == view[9:]]


def decompositions(x):
    exact(x[:, 4], x[:, 0]+x[:, 3]); exact(x[:, 4], x[:, 2]+x[:, 1])
    exact(x[:, 6], x[:, 1]-x[:, 0]); exact(x[:, 6], x[:, 3]-x[:, 2])


def block(cases, data):
    lookup = {case_key(c): i for i, c in enumerate(cases)}; n = len(CONDITIONS)
    assert len(cases) == len(lookup) == 1152
    result = dict(records=np.zeros(n, dtype=np.int32), mask_cases=np.zeros(n, dtype=np.int32))
    fs = dict(levels=(2, 4, 6, 4), effects=(2, 7, 6, 4), margin_levels=(2, 4, 6, 4),
              margin_effects=(2, 7, 6, 4), temporal_change=(2, 4, 4), original_levels=(4,))
    cs = dict(record_counts=(2, 7, 6, 4, 3), case_counts=(2, 7, 6, 4, 3), draw_counts=(2, 7, 6, 4, 3),
              temporal_counts=(2, 4, 4, 3), profile_joint_counts=(7, 6, 4, 3, 3))
    for k, shape in fs.items(): result[k] = np.full((n, *shape), np.nan)
    for k, shape in cs.items(): result[k] = np.zeros((n, *shape), dtype=np.int64)
    for j, condition in enumerate(CONDITIONS):
        d, f, g, view, source = condition.split('|'); worlds = []
        for w in range(16):
            h = cases[lookup[d, f, MASKS[0], source, w]]['developed_score']
            if g == 'all' or g == f'message:{w//4}' or (g == 'history:unique_pass' and h == 1) or (g == 'history:other' and h != 1): worlds.append(w)
        if not worlds: continue
        ids = np.array([[lookup[d, f, MASKS[m], source, w] for m in masks(view, w)] for w in worlds]); flat = ids.ravel()
        result['records'][j] = len(worlds); result['mask_cases'][j] = len(flat); profile_deltas = []
        for pi, profile in enumerate(PROFILES):
            per_draw = data[profile][ids].mean(1); record = per_draw.mean(2)
            delta = contrasts(record); decompositions(delta); profile_deltas.append(delta)
            assert np.all(delta[:, :4, 0] == 0), 'packet/feedback cannot change initial observed body'
            margin = data[profile+'_margin'][ids].mean((1, 3))
            result['levels'][j, pi] = record.mean(0)/12; result['effects'][j, pi] = delta.mean(0)/12
            result['margin_levels'][j, pi] = margin.mean(0); result['margin_effects'][j, pi] = contrasts(margin).mean(0)
            result['record_counts'][j, pi] = counts(delta)
            result['case_counts'][j, pi] = counts(contrasts(data[profile][flat].mean(2)))
            draw_delta = contrasts(per_draw).transpose(0, 2, 1, 3, 4).reshape(-1, 7, 6, 4)
            result['draw_counts'][j, pi] = counts(draw_delta)
            temporal = record[:, :, 5]-record[:, :, 4]
            result['temporal_change'][j, pi] = temporal.mean(0)/12; result['temporal_counts'][j, pi] = counts(temporal)
            assert np.all(result['record_counts'][j, pi].sum(-1) == len(worlds))
            assert np.all(result['case_counts'][j, pi].sum(-1) == len(flat))
            assert np.all(result['draw_counts'][j, pi].sum(-1) == len(worlds)*data[profile].shape[2])
        result['profile_joint_counts'][j] = joint(*profile_deltas)
        for pi in range(2):
            np.testing.assert_array_equal(result['profile_joint_counts'][j].sum(-1 if pi == 0 else -2), result['record_counts'][j, pi])
        result['original_levels'][j] = data['original'][ids].mean((0, 1, 2))/12
    return result


def combine(blocks):
    out = {}; n = np.stack([b['records'] for b in blocks])
    for key in blocks[0]:
        a = np.stack([b[key] for b in blocks]); out['block_'+key] = a
        if np.issubdtype(a.dtype, np.integer): out[key] = a.sum(0); continue
        weights = n.reshape((*n.shape, *(1 for _ in range(a.ndim-2)))); ok = weights > 0; values = np.where(ok, a, 0)
        out['equal_'+key] = np.divide(values.sum(0), ok.sum(0), out=np.full_like(a[0], np.nan), where=ok.sum(0) > 0)
        out['pooled_'+key] = np.divide((values*weights).sum(0), weights.sum(0), out=np.full_like(a[0], np.nan), where=weights.sum(0) > 0)
    return out


def report(a, role):
    lines = ['# TT043 — packet usefulness and memory feedback', '',
             f'Role: {role}; exposed development; original forcing and fresh draws reused.',
             'F0/F1 set memory feedback c_m to 0/0.2; rho stays 0.002. T0/T1 are preserved/late-written packets.',
             'Contrasts pair identical initial bodies and forcing within each profile. Profiles are distinct receiving environments.',
             'Harm/tie/gain counts average actual masks and draws within each source position. Continuing observations are not repeated as fresh draws.', '']
    for d in DAMAGE:
        j = INDEX[f'{d}|residual|all|all_masks|own']; lines += [f'## {d}: residual / own / all histories and masks', '']
        for pi, profile in enumerate(PROFILES):
            lines += [f'### {profile}', '', '| Contrast | 900 updates (pp) | 1000 updates (pp) | Harm / tie / gain at 900 | Harm / tie / gain at 1000 |',
                      '|---|---:|---:|---|---|']
            for q, name in enumerate(COMPARISONS):
                v = 100*a['equal_effects'][j, pi, q, :, 0]
                lines.append(f"| {name} | {v[4]:.6f} | {v[5]:.6f} | {a['record_counts'][j, pi, q, 4, 0].tolist()} | {a['record_counts'][j, pi, q, 5, 0].tolist()} |")
            lines += ['', 'Levels at 900 / 1000 (%), in F0T0 / F0T1 / F1T0 / F1T1 order:',
                      str((100*a['equal_levels'][j, pi, :, 4:, 0]).tolist()), '',
                      'Four block effects at 1000 (pp), in fixed source order:']
            for q, name in enumerate(COMPARISONS): lines.append(name+': '+str((100*a['block_effects'][:, j, pi, q, 5, 0]).tolist()))
            lines += ['', 'Secondary continuous-margin effects at 1000:', str(a['equal_margin_effects'][j, pi, :, 5, 0].tolist()), '']
        lines += ['Inherited original-packet fresh-recipient target score (%): '+str(float(100*a['equal_original_levels'][j, 0])), '']
    lines += ['All cases, paired harms, checkpoints, four credits, families, sources, histories, tasks, mask and geometry strata remain in the arrays.',
              'Four exposed population blocks; no new independent futures, capacity estimate, confirmation, uninterrupted-performance or serial-inheritance claim.',
              'Feedback-off fresh V/ema/theta replay the original assay, while R is now a nonfeeding tracker. This is not full R-state identity.', '']
    return '\n'.join(lines)


def summary(directory, role):
    ids = selected(role); blocks = [arrays(directory/f'tissue_{i}'/'AGGREGATE.npz') for i in ids]
    a = combine(blocks); save(directory/'SUMMARY.npz', a)
    with (directory/'REPORT.md').open('x') as f: f.write(report(a, role))
    write(directory/'AXES.json', dict(conditions=CONDITIONS, profiles=PROFILES, arms=ARMS, feedback_packet_pairs=CROSSES,
          times=TIMES, credits=CREDITS, comparisons=COMPARISONS, coefficients=COEFFICIENTS.tolist(), signs=SIGNS,
          endpoint_axes=['case', 'arm', 'actual_draw', 'relative_time', 'credit'], probability_storage='integer twelfths',
          margin_storage='float64 continuous target-versus-best-other', new_independent_draws=0))
    proofs = [read(directory/f'tissue_{i}'/'CHECK.json')['verification'] for i in ids]
    return {k: max(p[k] for p in proofs) if k == 'max_native_error' else sum(p[k] for p in proofs) for k in proofs[0]}
