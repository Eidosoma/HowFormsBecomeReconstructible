"""Independent writer and normalized-reader calculations on saved bodies.

Weights have two reciprocal edge planes: right and down. No production modules
are imported. The linear transfer calculation is not the nonlinear native assay.
"""
import numpy as np


def incident(weights):
    h, v = weights[..., 0, :, :], weights[..., 1, :, :]
    return h + np.roll(h, 1, -1) + v + np.roll(v, 1, -2)


def directions(weights):
    h, v = weights[..., 0, :, :], weights[..., 1, :, :]
    return np.stack((h, np.roll(h, 1, -1), v, np.roll(v, 1, -2)), axis=-3)


def available_edges(mask):
    alive = ~mask
    return np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)


def writer_pair(body, available, beta=3., tolerance=1e-4):
    x = np.tanh(beta * body)
    plus, minus = x[..., 0, :, :], x[..., 1, :, :]
    d = (plus-minus)/2
    common = (plus+minus)/2
    q = np.stack((d*np.roll(d, -1, -1), d*np.roll(d, -1, -2)), axis=-3)
    c = np.stack(((plus*np.roll(plus, -1, -1)+minus*np.roll(minus, -1, -1))/2,
                  (plus*np.roll(plus, -1, -2)+minus*np.roll(minus, -1, -2))/2), axis=-3)
    exact = np.where(available, np.where(q != 0., q, c), 0.)
    tol = np.where(available, np.where(np.abs(q) > tolerance, q, c), 0.)
    restored = np.sign(exact)*np.abs(tol)
    return dict(d=d, common=common, q=q, c=c, exact=exact, tolerance=tol, sign_restored=restored)


def normalized(weights):
    rows = directions(weights)
    denominator = np.sum(np.abs(rows), axis=-3)
    return np.divide(rows, denominator[..., None, :, :], out=np.zeros_like(rows),
                     where=denominator[..., None, :, :] > 0)


def apply_rows(rows, values):
    return (rows[..., 0, :, :]*np.roll(values, -1, -1)
            + rows[..., 1, :, :]*np.roll(values, 1, -1)
            + rows[..., 2, :, :]*np.roll(values, -1, -2)
            + rows[..., 3, :, :]*np.roll(values, 1, -2))


def cue_transfer(rows, input_port, steps):
    value = np.zeros(rows.shape[:-3]+rows.shape[-2:])
    value[..., input_port] = 1.
    for _ in range(steps):
        value = apply_rows(rows, value)
        value[..., input_port] = 1.
    if np.max(np.abs(value)) > 1+1e-12:
        raise AssertionError("Normalized linear influence escaped [-1,1]")
    return value


def masked_mean(value, mask):
    numerator = np.sum(np.where(mask, value, 0.), axis=(-2, -1))
    denominator = np.sum(mask, axis=(-2, -1))
    return np.divide(numerator, denominator, out=np.zeros_like(numerator, dtype=float), where=denominator > 0)


def ratio(numerator, denominator):
    return np.divide(numerator, denominator, out=np.zeros_like(numerator, dtype=float), where=denominator > 0)


def minimum_task_transfer(field, ports, rules):
    a = field[..., ports[1]].mean(axis=-1)*rules
    b = -field[..., ports[2]].mean(axis=-1)*rules
    return np.minimum(a, b)


def features(body, mask, ports, rules, steps=64, tolerance=1e-4):
    """Batch shape N; body (N,2,S,S), mask (N,S,S), rule (N,)."""
    available = available_edges(mask)
    pair = writer_pair(body, available, tolerance=tolerance)
    eligible = (~mask) & (~ports[0])
    av_count = available.sum(axis=(-3, -2, -1))
    nonzero_contrast = available & (pair['q'] != 0)
    nonzero_count = nonzero_contrast.sum(axis=(-3, -2, -1))
    swapped = nonzero_contrast & (np.abs(pair['q']) <= tolerance)
    exact, tol = pair['exact'], pair['tolerance']
    flips = available & (exact*tol < 0)
    normalized_rows = {name:normalized(pair[name]) for name in ('exact', 'tolerance', 'sign_restored')}
    row_difference = np.abs(normalized_rows['exact']-normalized_rows['tolerance']).sum(axis=-3)
    answer = dict(
        available_edges=av_count,
        nonzero_contrast_edges=nonzero_count,
        newly_substituted_fraction=ratio(swapped.sum(axis=(-3, -2, -1)), av_count),
        sign_flip_fraction=ratio(flips.sum(axis=(-3, -2, -1)), av_count),
        raw_weight_change_mean=ratio(np.abs(exact-tol).sum(axis=(-3, -2, -1)), av_count),
        reader_row_l1_mean=masked_mean(row_difference, eligible),
        reader_row_l1_max=np.max(np.where(eligible, row_difference, 0), axis=(-2, -1)),
        body_contrast_alignment=minimum_task_transfer(pair['d'], ports, rules))
    body_changes = []
    for cue in (0, 1):
        difference = apply_rows(normalized_rows['tolerance'], body[:, cue])-apply_rows(normalized_rows['exact'], body[:, cue])
        body_changes.append(masked_mean(np.abs(difference), eligible))
    answer['body_reader_change_mean'] = np.mean(body_changes, axis=0)
    for name, rows in normalized_rows.items():
        w = pair[name]
        conflicts = (w*pair['q'] < 0) & nonzero_contrast
        conflict_weight = directions(np.abs(w)*conflicts)
        den = directions(np.abs(w)).sum(axis=-3)
        conflict_mass = ratio(conflict_weight.sum(axis=-3), den)
        h, v = w[:, 0], w[:, 1]
        # Signs first, so tiny nonzero products do not underflow during cycle counting.
        loop_sign = np.sign(h)*np.sign(np.roll(v, -1, -1))*np.sign(np.roll(h, -1, -2))*np.sign(v)
        loop_count = (loop_sign != 0).sum(axis=(-2, -1))
        signed = cue_transfer(rows, ports[0], steps)
        unsigned = cue_transfer(np.abs(rows), ports[0], steps)
        answer.update({
            name+'_conflict_edge_fraction':ratio(conflicts.sum(axis=(-3, -2, -1)), nonzero_count),
            name+'_conflict_mass':masked_mean(conflict_mass, eligible),
            name+'_negative_plaquette_fraction':ratio((loop_sign < 0).sum(axis=(-2, -1)), loop_count),
            name+'_nonzero_plaquettes':loop_count,
            name+'_zero_denominator_fraction':masked_mean(den == 0, eligible),
            name+'_signed_transfer':minimum_task_transfer(signed, ports, rules),
            name+'_unsigned_access':np.minimum(unsigned[..., ports[1]].mean(axis=-1), unsigned[..., ports[2]].mean(axis=-1))})
    for key, value in answer.items():
        if not np.isfinite(value).all():
            raise AssertionError("Nonfinite feature: "+key)
    return answer, pair


def score_ports(mean_ports, rules, margin=.25):
    target = rules[..., None]*np.array([1., -1.])
    margins = np.minimum(target*mean_ports[..., 0], -target*mean_ports[..., 1])
    return margins.min(axis=-1), (margins > margin).all(axis=-1), margins
