"""D188 analyst-defined, fixed-template/strength exchange; no dynamics."""

import numpy as np

NORM, TOL, MIN_REMAINDER = .3, 2e-12, 1e-12
CELLS = ('LL', 'LF', 'FL', 'FF', 'LL_roundtrip', 'FF_roundtrip')
FAMILIES = ('common', 'residual')
METRICS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
           'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')


def basis(codes):
    if codes.shape != (4, 16, 16) or codes.dtype != np.float64 or not np.isfinite(codes).all():
        raise ValueError('four finite float64 templates required')
    if np.max(np.abs(codes.mean(axis=(1, 2)))) > TOL:
        raise ValueError('templates must be centered')
    if not np.array_equal(codes[1], -codes[0]) or not np.array_equal(codes[3], -codes[2]):
        raise ValueError('the fixed template codebook consists of two signed pairs')
    q, r = np.linalg.qr(codes[[0, 2]].reshape(2, 256).T, mode='reduced')
    if np.min(np.abs(np.diag(r))) <= 1e-10:
        raise ValueError('rank-deficient template span')
    return q.T.reshape(2, 16, 16)


def split(theta, axes):
    if (theta.ndim != 3 or theta.shape[1:] != (16, 16) or theta.dtype != np.float64
            or len(theta) == 0 or not np.isfinite(theta).all()):
        raise ValueError('finite float64 packet fields required')
    mean = theta.mean(axis=(1, 2), keepdims=True)
    if np.max(np.abs(mean)) > TOL or np.max(np.abs(theta.std(axis=(1, 2))-NORM)) > TOL:
        raise ValueError('source packet must retain the original zero mean and strength')
    centered = theta-mean
    q = axes.reshape(2, 256)
    projected = (centered.reshape(len(theta), 256) @ q.T @ q).reshape(theta.shape)
    remainder = centered-projected
    rms = np.sqrt((remainder*remainder).mean(axis=(1, 2), keepdims=True))
    if np.any(rms <= MIN_REMAINDER): raise ValueError('degenerate orthogonal component; no case substitution')
    return dict(mean=mean, P=projected, Q=remainder, q_rms=rms)


def construct(live, fixed, codes):
    if live.shape != fixed.shape: raise ValueError('paired packet shapes differ')
    axes = basis(codes)
    sources = {'L': live, 'F': fixed}
    parts = {k: split(v, axes) for k, v in sources.items()}
    fields = {'basis': axes.copy()}
    for k, part in parts.items(): fields.update({k+'_'+n: v.copy() for n, v in part.items()})
    packets, metadata = {}, {}
    for name in CELLS:
        i, j = name[0], name[1]
        a, b = parts[i], parts[j]
        gain = a['q_rms']/b['q_rms']
        rebuilt = a['mean']+a['P']+gain*b['Q']
        original = name in ('LL', 'FF')
        value = sources[i].copy() if original else rebuilt
        if np.max(np.abs(value.std(axis=(1, 2))-sources[i].std(axis=(1, 2)))) > TOL:
            raise AssertionError('component exchange changed strength')
        coefficients = (value-sources[i]).reshape(len(value), 256) @ codes.reshape(4, 256).T/256
        if np.max(np.abs(coefficients)) > TOL: raise AssertionError('component exchange changed template coefficients')
        packets[name] = value
        metadata[name] = dict(template_provider=i, detail_provider=j, original_bytes=original,
            q_gain=gain[:, 0, 0].tolist(),
            template_energy=(a['P']**2).mean(axis=(1, 2)).tolist(),
            detail_energy=(a['Q']**2).mean(axis=(1, 2)).tolist(),
            output_std=value.std(axis=(1, 2)).tolist(), output_mean=value.mean(axis=(1, 2)).tolist(),
            template_max_abs=np.max(np.abs(coefficients), axis=1).tolist(),
            arithmetic_diagonal_max_abs=np.max(np.abs(rebuilt-sources[i]), axis=(1, 2)).tolist()
                if i == j else None)
    return packets, fields, metadata


def plan():
    return tuple(f'{f}__{n}' for f in FAMILIES for n in CELLS)+('intact_parent', 'supplied_positive', 'reader_off')


def bridges():
    result = {f'{f}__{n}': f'capture__{f}__own__{mode}'
              for f in FAMILIES for n, mode in (('LL', 'live'), ('FF', 'fixed'))}
    return result | {n: n for n in ('intact_parent', 'supplied_positive', 'reader_off')}


def contrasts():
    base = {
        'detail_at_L': {'LF': 1., 'LL': -1.},
        'detail_at_F': {'FF': 1., 'FL': -1.},
        'template_at_L': {'FL': 1., 'LL': -1.},
        'template_at_F': {'FF': 1., 'LF': -1.},
        'detail_mean': {'LF': .5, 'LL': -.5, 'FF': .5, 'FL': -.5},
        'template_mean': {'FL': .5, 'LL': -.5, 'FF': .5, 'LF': -.5},
        'interaction': {'FF': 1., 'FL': -1., 'LF': -1., 'LL': 1.},
        'diagonal_gap': {'FF': 1., 'LL': -1.},
        'roundtrip_L': {'LL_roundtrip': 1., 'LL': -1.},
        'roundtrip_F': {'FF_roundtrip': 1., 'FF': -1.},
    }
    return {f'{f}__{name}': {f'{f}__{cell}': w for cell, w in terms.items()}
            for f in FAMILIES for name, terms in base.items()}


def statistics(records, draws):
    """One whole block; no case exclusion, significance gate or fitted model."""
    if set(records) != set(draws) or set(records) != set(plan()):
        raise ValueError('complete fifteen-condition panel required')
    n = len(records['common__LL'])
    if n == 0 or n % 4: raise ValueError('four equal message groups required')
    parents = n//4
    matrices = {}
    for name, rows in records.items():
        if len(rows) != n: raise ValueError('paired records required')
        for i, row in enumerate(rows):
            if (row['world'], row['message'], row['replicate']) != (i, i//parents, i % parents):
                raise ValueError('record order changed')
        matrices[name] = np.array([[r[k] for k in METRICS] for r in rows], dtype=np.float64)
        d = draws[name]
        if (not np.isfinite(matrices[name]).all() or d.ndim != 2 or d.shape[0] != n
                or d.shape[1] == 0 or not np.isfinite(d).all()):
            raise ValueError('invalid score arrays')
        np.testing.assert_allclose(d.mean(axis=1), matrices[name][:, 0], rtol=0., atol=TOL)
    if len({d.shape for d in draws.values()}) != 1: raise ValueError('unpaired reader draws')

    def means(matrix):
        return dict(mean=dict(zip(METRICS, matrix.mean(axis=0).tolist())),
                    messages=[dict(zip(METRICS, m.mean(axis=0).tolist()))
                              for m in matrix.reshape(4, parents, len(METRICS))])

    def count(x):
        return dict(n=int(x.size), improved=int(np.sum(x > TOL)), worsened=int(np.sum(x < -TOL)),
                    tied=int(np.sum(np.abs(x) <= TOL)), net=float(x.mean()),
                    positive=float(np.maximum(x, 0.).mean()), negative=float(np.minimum(x, 0.).mean()))

    def transition(d):
        return dict(records=count(d.mean(axis=1)), draws=count(d))

    comparisons = {}
    for name, terms in contrasts().items():
        matrix = sum(w*matrices[k] for k, w in terms.items())
        delta = sum(w*draws[k] for k, w in terms.items())
        np.testing.assert_allclose(delta.mean(axis=1), matrix[:, 0], rtol=0., atol=TOL)
        comparisons[name] = dict(coefficients=terms, per_record=matrix.tolist(),
            per_draw_accuracy=delta.tolist(), **means(matrix),
            transitions=dict(pooled=transition(delta), by_message=[transition(d) for d in
                             delta.reshape(4, parents, delta.shape[1])]))
    return dict(schema='d188_single_block_component_exchange_v1', records=n, fields=list(METRICS),
                arms={k: means(v) for k, v in matrices.items()}, contrasts=comparisons,
                confirmatory=False, fitted_models=0, new_founders=0, serial_renewal=False)
