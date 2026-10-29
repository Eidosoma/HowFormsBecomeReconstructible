"""Cross starting state with realized forcing, retaining actual denominators."""
from common import *


def units(x):
    x = np.asarray(x); assert np.isfinite(x).all(); u = np.rint(x*12).astype(np.int16)
    near(u/12, x); assert np.isin(u, (0, 3, 4, 6, 12)).all(); return u


def contrasts(x): return np.einsum('qa,na...->nq...', COEFFICIENTS, x)
def counts(x): return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)


def masks(view, world):
    if view == 'all_masks': return list(range(4))
    if view.startswith('mask:'): return [MASKS.index(view[5:])]
    return [m for m in range(4) if GEOMETRIES[geometry(m, world)] == view[9:]]


def decompositions(x):
    exact(x[:, 23], x[:, 18]+x[:, 21]); exact(x[:, 23], x[:, 20]+x[:, 19])
    exact(x[:, 22], x[:, 19]-x[:, 18]); exact(x[:, 22], x[:, 21]-x[:, 20])
    exact(x[:, 22], x[:, 17]-x[:, 16])
    for offset in (4, 10):
        exact(x[:, offset+4], x[:, offset]+x[:, offset+3])
        exact(x[:, offset+4], x[:, offset+2]+x[:, offset+1])


def block(cases, data):
    lookup = {case_key(c): i for i, c in enumerate(cases)}; n = len(CONDITIONS)
    assert len(cases) == len(lookup) == 1152
    nd = data['FF'].shape[2]; assert nd in (1, 4)
    for cell in CELLS:
        shape = (1152, 2, 1 if cell == 'CC' else nd, 6, 4)
        assert data[cell].shape == data[cell+'_margin'].shape == shape
        assert data[cell].dtype == np.int16 and np.isin(data[cell], (0, 3, 4, 6, 12)).all()
        assert np.isfinite(data[cell+'_margin']).all()
    assert data['original'].shape == (1152, nd, 4) and data['original'].dtype == np.int16
    result = dict(records=np.zeros(n, dtype=np.int32), mask_cases=np.zeros(n, dtype=np.int32),
                  paired_indices=np.zeros((n, NCON), dtype=np.int64))
    fs = dict(levels=(8, 6, 4), effects=(NCON, 6, 4), margin_levels=(8, 6, 4),
              margin_effects=(NCON, 6, 4), temporal_change=(8, 4), original_levels=(4,))
    cs = dict(record_counts=(NCON, 6, 4, 3), case_counts=(NCON, 6, 4, 3),
              paired_index_counts=(NCON, 6, 4, 3), temporal_counts=(8, 4, 3))
    for k, shape in fs.items(): result[k] = np.full((n, *shape), np.nan)
    for k, shape in cs.items(): result[k] = np.zeros((n, *shape), dtype=np.int64)
    for j, condition in enumerate(CONDITIONS):
        d, f, g, view, source = condition.split('|'); worlds = []
        for w in range(16):
            h = cases[lookup[d, f, MASKS[0], source, w]]['developed_score']
            if g == 'all' or g == f'message:{w//4}' or (g == 'history:unique_pass' and h == 1) or (g == 'history:other' and h != 1): worlds.append(w)
        if not worlds: continue
        ids = np.array([[lookup[d, f, MASKS[m], source, w] for m in masks(view, w)] for w in worlds]); flat = ids.ravel()
        result['records'][j] = len(worlds); result['mask_cases'][j] = len(flat)
        # First average actual masks, then actual receiving indices within each cell.
        per_index = [data[cell][ids].mean(1) for cell in CELLS]
        record = np.concatenate([x.mean(2) for x in per_index], axis=1)
        delta = contrasts(record); decompositions(delta)
        assert np.all(delta[:, [0, 1, 2, 3, 4, 5, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23], 0] == 0)
        margin = np.concatenate([data[cell+'_margin'][ids].mean((1, 3)) for cell in CELLS], axis=1)
        result['levels'][j] = record.mean(0)/12; result['effects'][j] = delta.mean(0)/12
        result['margin_levels'][j] = margin.mean(0); result['margin_effects'][j] = contrasts(margin).mean(0)
        result['record_counts'][j] = counts(delta)
        injury = np.concatenate([data[cell][flat].mean(2) for cell in CELLS], axis=1)
        result['case_counts'][j] = counts(contrasts(injury))
        # CC is a shared comparator only. Its own contrast retains ONE index.
        paired = np.concatenate([np.broadcast_to(x, (len(worlds), 2, nd, 6, 4)) for x in per_index], axis=1)
        paired_delta = contrasts(paired)
        for q, actual in enumerate(PAIRED_ENV_COUNTS):
            m = actual or nd; values = paired_delta[:, q, :m].reshape(-1, 6, 4)
            result['paired_index_counts'][j, q] = counts(values)
            result['paired_indices'][j, q] = len(worlds)*m
        temporal = record[:, :, 5]-record[:, :, 4]
        result['temporal_change'][j] = temporal.mean(0)/12; result['temporal_counts'][j] = counts(temporal)
        assert np.all(result['record_counts'][j].sum(-1) == len(worlds))
        assert np.all(result['case_counts'][j].sum(-1) == len(flat))
        assert np.all(result['paired_index_counts'][j].sum(-1) == result['paired_indices'][j, :, None, None])
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
    lines = ['# TT044 — receiving state and realized forcing', '',
             f'Role: {role}; exposed development; all source states and forcing streams reused.',
             'C/F mean continuing/fresh; first letter selects initial V/ema/R, second selects forcing. Feedback is zero throughout.',
             'T0/T1 are preserved/late-written packets. Two ordered decompositions are retained; neither is a unique mediated fraction.',
             'Counts below average actual masks and receiving indices within source position. CC has one actual condition; other cells use the original paired index.', '']
    for d in DAMAGE:
        j = INDEX[f'{d}|residual|all|all_masks|own']; lines += [f'## {d}: residual / own / all histories and masks', '',
            '| Contrast | 900 updates (pp) | 1000 updates (pp) | Harm / tie / gain at 900 | Harm / tie / gain at 1000 |',
            '|---|---:|---:|---|---|']
        for q, name in enumerate(COMPARISONS):
            v = 100*a['equal_effects'][j, q, :, 0]
            lines.append(f"| {name} | {v[4]:.6f} | {v[5]:.6f} | {a['record_counts'][j, q, 4, 0].tolist()} | {a['record_counts'][j, q, 5, 0].tolist()} |")
        lines += ['', 'Levels at 900 / 1000 (%), in CC-T0 / CC-T1 / CF-T0 / CF-T1 / FC-T0 / FC-T1 / FF-T0 / FF-T1 order:',
                  str((100*a['equal_levels'][j, :, 4:, 0]).tolist()), '', 'Block effects at 900 / 1000 (pp), in fixed source order:']
        for q, name in enumerate(COMPARISONS): lines.append(name+': '+str((100*a['block_effects'][:, j, q, 4:, 0]).tolist()))
        lines += ['', 'Secondary continuous-margin effects at 900 / 1000:', str(a['equal_margin_effects'][j, :, 4:, 0].tolist()), '',
                  'Inherited original-packet recipient target score (%): '+str(float(100*a['equal_original_levels'][j, 0])), '']
    lines += ['All cases, paired harms, checkpoints, four credits, families, sources, histories, tasks, mask and geometry strata remain in the arrays.',
              'The continuing comparator is shared in paired-index arithmetic, not replicated evidence. Other cells use matching fresh index d, not a Cartesian product.',
              'The production unit is the population block (four exposed blocks). No new independent futures, capacity estimate, confirmation or serial-inheritance claim.',
              'The experiment changes realized forcing streams, not their distribution or amplitude. Initial V/ema/R are changed together.', '']
    return '\n'.join(lines)


def summary(directory, role):
    ids = selected(role); blocks = [arrays(directory/f'tissue_{i}'/'AGGREGATE.npz') for i in ids]
    a = combine(blocks); save(directory/'SUMMARY.npz', a)
    with (directory/'REPORT.md').open('x') as f: f.write(report(a, role))
    write(directory/'AXES.json', dict(conditions=CONDITIONS, cells=CELLS, cell_factors=CELL_FACTORS, arms=ARMS,
          times=TIMES, credits=CREDITS, comparisons=COMPARISONS, coefficients=COEFFICIENTS.tolist(), signs=SIGNS,
          cell_endpoint_axes=['case', 'packet', 'actual_index', 'relative_time', 'credit'],
          cell_actual_indices={c:cell_draws(c, role) for c in CELLS},
          contrast_paired_indices={q:(m or draws(role)) for q,m in zip(COMPARISONS, PAIRED_ENV_COUNTS)},
          paired_index_note='CC shared as comparator only; packet_CC counted once; d is paired, not a Cartesian product',
          probability_storage='integer twelfths', margin_storage='float64 credit-versus-best-other', new_independent_draws=0))
    proofs = [read(directory/f'tissue_{i}'/'CHECK.json')['verification'] for i in ids]
    return {k: max(p[k] for p in proofs) if k == 'max_native_error' else sum(p[k] for p in proofs) for k in proofs[0]}
