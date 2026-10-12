"""Frozen D143 crossed random-effects moments; no fitting or outcome selection."""
import numpy as np
from . import diagnostics as dev

CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
SEED, DRAWS = 14320260917, 10000


def case_components(y):
    y = np.asarray(y, float)
    if y.shape[-2:] != (4, 4) or not np.isfinite(y).all():
        raise ValueError('four noise rows and four address columns required')
    grand = y.mean(axis=(-2, -1), keepdims=True)
    row = y.mean(axis=-1, keepdims=True)-grand
    col = y.mean(axis=-2, keepdims=True)-grand
    residual = y-grand-row-col
    sn = np.mean(row**2, axis=(-2, -1)); sa = np.mean(col**2, axis=(-2, -1))
    si = np.mean(residual**2, axis=(-2, -1))
    st = np.mean((y-grand)**2, axis=(-2, -1))
    np.testing.assert_allclose(sn+sa+si, st, atol=1e-12, rtol=0)
    vn, va, vi = 4*sn/3-4*si/9, 4*sa/3-4*si/9, 16*si/9
    wn = y.var(axis=-2, ddof=1).mean(axis=-1)
    wa = y.var(axis=-1, ddof=1).mean(axis=-1)
    np.testing.assert_allclose(wn, vn+vi, atol=1e-12, rtol=0)
    np.testing.assert_allclose(wa, va+vi, atol=1e-12, rtol=0)
    return dict(noise_main=vn, address_main=va, interaction=vi, total=vn+va+vi,
        address_minus_noise=va-vn, noise_at_fixed_address=wn, address_at_fixed_noise=wa,
        finite_noise=sn, finite_address=sa, finite_interaction=si, finite_total=st)


def components(y):
    if np.shape(y)[-3:] != (64, 4, 4):
        raise ValueError('64 complete case panels per group required')
    return {k: v.mean(axis=-1) for k, v in case_components(y).items()}


def group_statistics(y, draws):
    if y.shape != (16, 4, 4, 4) or draws.shape != (DRAWS, 16):
        raise ValueError('sixteen founder blocks and whole-block bootstrap required')
    point = components(y.reshape(64, 4, 4))
    # Resampling the per-case sufficient moments is exactly group-mean recomputation.
    cases = case_components(y)
    rows = {}
    for k, value in point.items():
        boot = cases[k][draws].mean(axis=(1, 2))
        assert np.isfinite(boot).all()
        rows[k] = dict(estimate=float(value), pointwise_block_bootstrap_95=np.quantile(boot, [.025, .975]).tolist())
    return rows


def fidelity(block):
    packets = np.concatenate((block['incoming'][..., 0, None, :], block['outgoing']), axis=-2)
    fields = np.ascontiguousarray(packets).view('<f8').reshape(4, 4, 4, 4, 4, 16, 16)
    centered = fields-fields.mean(axis=(-2, -1), keepdims=True)
    scale = fields.std(axis=(-2, -1)); result = np.zeros((4, 4, 4, 4, 4))
    for ci, (role, _) in enumerate(CASES):
        scores = np.einsum('sij,...ij->...s', dev.template_bank()[role], centered[:, :, :, ci], optimize=False)
        np.divide(scores.max(axis=-1), 256*scale[:, :, :, ci], out=result[:, :, :, ci], where=scale[:, :, :, ci] > 0)
    return result


def summarize(blocks, metadata):
    if len(blocks) != 16 or len(metadata) != 16:
        raise ValueError('all sixteen founder blocks required')
    y = np.stack([b['terminal_values'][..., -1, 0]-b['terminal_values'][..., -1, 1] for b in blocks])
    assert y.shape == (16, 4, 4, 4, 4) and np.isfinite(y).all()
    gen = np.stack([b['values'][..., -1, 0]-b['values'][..., -1, 1] for b in blocks])
    trajectory = np.concatenate((gen, y[..., None]), axis=-1)
    shapes = np.stack([fidelity(b) for b in blocks])
    labels = np.array([[[[[[p['selector']['inferred_family'] for p in entry['paths'][ci]['generations']]+
        [entry['paths'][ci]['terminal']['selector']['inferred_family']] for ci in range(4)]
        for entry in noise] for noise in life] for life in m['lives']] for m in metadata], dtype=object)
    draws = np.random.default_rng(SEED).integers(0, 16, (DRAWS, 16))
    groups = {}
    for ci, (role, writer) in enumerate(CASES):
        panel = y[..., ci]; flat = panel.reshape(64, 4, 4)
        trace = trajectory[..., ci, :]; fit = shapes[..., ci, :]
        stages = [components(trace[..., g].reshape(64, 4, 4)) for g in range(4)]
        group = dict(primary=group_statistics(panel, draws),
            terminal_panels=flat.tolist(), case_components={k: v.tolist() for k, v in case_components(flat).items()},
            mean_preference_G1_G4=trace.mean(axis=(0, 1, 2, 3)).tolist(),
            negative_preference_G1_G4=(trace < 0).sum(axis=(0, 1, 2, 3)).tolist(),
            zero_preference_G1_G4=(trace == 0).sum(axis=(0, 1, 2, 3)).tolist(),
            non_own_guide_G1_G4=(labels[..., ci, :] != role).sum(axis=(0, 1, 2, 3)).tolist(),
            mean_record_best_F0_F3=fit.mean(axis=(0, 1, 2, 3)).tolist(),
            stage_noise_at_fixed_address=[float(v['noise_at_fixed_address']) for v in stages],
            stage_address_at_fixed_noise=[float(v['address_at_fixed_noise']) for v in stages],
            labelled_terminal_cells=1024, nominal_distinct_cells=1024 if writer == 'translated' else 256,
            aligned_aliases=0 if writer == 'translated' else 768)
        groups[f'{"AB"[role]}_{writer}'] = group
    return dict(schema='d143_crossed_address_noise_v1', stage='FIXED_COHORT_CROSSED_EXISTING_STREAMS',
        blocks=list(range(90000, 90016)), independent_blocks=16, lives_per_block=4, cases=256,
        noise_levels=4, address_levels=4, labelled_terminal_cells=4096,
        nominal_distinct_condition_stream_cells=2560, aligned_address_aliases=1536,
        diagonal_cells=1024, novel_ordinary_off_diagonal_cells=1536,
        new_founders=0, new_noise_histories=0, refitted_models=0,
        bootstrap_seed=SEED, bootstrap_draws=DRAWS, groups=groups,
        method_of_moments_clipped=False, multiplicity_adjusted=False, automatic_successor=False,
        interpretation='Mechanistic crossing of four already-sampled address and noise histories on known record-host pairs; not a new prospective founder or challenge test.')
