"""Independent ANOVA mean-squares and FFT reconstruction for D143."""
import numpy as np
from .crossed_audit import physics


def case_moments(y):
    assert y.shape[-2:] == (4, 4) and np.isfinite(y).all()
    grand = np.add.reduce(np.add.reduce(y, axis=-1), axis=-1)/16
    row_mean, col_mean = np.add.reduce(y, axis=-1)/4, np.add.reduce(y, axis=-2)/4
    interaction = y-row_mean[..., :, None]-col_mean[..., None, :]+grand[..., None, None]
    ms_n = 4*np.sum((row_mean-grand[..., None])**2, axis=-1)/3
    ms_a = 4*np.sum((col_mean-grand[..., None])**2, axis=-1)/3
    ms_i = np.sum(interaction**2, axis=(-2, -1))/9
    vn, va, vi = (ms_n-ms_i)/4, (ms_a-ms_i)/4, ms_i
    # Conditional variances restated by pairwise differences, not np.var.
    wn = sum(np.sum((y[..., i, :]-y[..., j, :])**2, axis=-1) for i in range(4) for j in range(i+1, 4))/48
    wa = sum(np.sum((y[..., :, i]-y[..., :, j])**2, axis=-1) for i in range(4) for j in range(i+1, 4))/48
    return dict(noise_main=vn, address_main=va, interaction=vi, total=vn+va+vi,
        address_minus_noise=va-vn, noise_at_fixed_address=wn, address_at_fixed_noise=wa,
        finite_noise=3*ms_n/16, finite_address=3*ms_a/16, finite_interaction=9*ms_i/16,
        finite_total=np.sum((y-grand[..., None, None])**2, axis=(-2, -1))/16)


def moments(y):
    assert y.shape[-3:] == (64, 4, 4)
    return {k: np.sum(v, axis=-1)/64 for k, v in case_moments(y).items()}


def check(summary, blocks, metadata):
    assert len(blocks) == len(metadata) == 16
    y = np.stack([b['terminal_values'][..., -1, 0]-b['terminal_values'][..., -1, 1] for b in blocks])
    draws = np.random.default_rng(14320260917).integers(0, 16, (10000, 16))
    yy, xx = np.indices((16, 16)); targets = (np.where(yy < 8, 1., -1.), np.where(xx % 8 < 4, 1., -1.))
    worst = 0.
    for ci, name in enumerate(('A_translated', 'A_aligned', 'B_translated', 'B_aligned')):
        g = summary['groups'][name]; role = ci//2
        panel = y[..., ci]; flat = panel.reshape(64, 4, 4)
        point, cases = moments(flat), case_moments(panel)
        expected = {}
        for k in point:
            boot = np.add.reduce(np.add.reduce(cases[k][draws], axis=2), axis=1)/64
            expected[k] = dict(estimate=float(point[k]), pointwise_block_bootstrap_95=np.percentile(boot, [2.5, 97.5]).tolist())
        physics.nested(g['primary'], expected)
        physics.nested(g['case_components'], {k: v.tolist() for k, v in case_moments(flat).items()})
        physics.nested(g['terminal_panels'], flat.tolist())
        gen = np.stack([b['values'][:, :, :, ci, :, -1, 0]-b['values'][:, :, :, ci, :, -1, 1] for b in blocks])
        trace = np.concatenate((gen, panel[..., None]), axis=-1)
        physics.nested(g['mean_preference_G1_G4'], (trace.sum(axis=(0, 1, 2, 3))/1024).tolist())
        assert g['negative_preference_G1_G4'] == (trace < 0).sum(axis=(0, 1, 2, 3)).tolist()
        assert g['zero_preference_G1_G4'] == (trace == 0).sum(axis=(0, 1, 2, 3)).tolist()
        for key in ('noise_at_fixed_address', 'address_at_fixed_noise'):
            physics.nested(g['stage_'+key], [float(moments(trace[..., stage].reshape(64, 4, 4))[key]) for stage in range(4)])
        counts, shape_sums = [0]*4, np.zeros(4)
        for bi, block in enumerate(blocks):
            for life in range(4):
                for noise in range(4):
                    for address in range(4):
                        entry = metadata[bi]['lives'][life][noise][address]['paths'][ci]
                        choices = [r['selector']['inferred_family'] for r in entry['generations']]+[entry['terminal']['selector']['inferred_family']]
                        for stage, choice in enumerate(choices): counts[stage] += int(choice != role)
                        packets = [block['incoming'][life, noise, address, ci, 0]]+list(block['outgoing'][life, noise, address, ci])
                        for stage, packet in enumerate(packets):
                            v = np.frombuffer(packet.tobytes(), '<f8').reshape(16, 16); sd = v.std()
                            fit = np.fft.ifft2(np.fft.fft2(v-v.mean())*np.conjugate(np.fft.fft2(targets[role]))).real.max()/(256*sd) if sd else 0.
                            shape_sums[stage] += fit
        assert g['non_own_guide_G1_G4'] == counts
        error = float(np.max(abs(shape_sums/1024-g['mean_record_best_F0_F3'])))
        assert error < 1e-12; worst = max(worst, error)
        assert g['labelled_terminal_cells'] == 1024
        assert g['nominal_distinct_cells'] == (1024 if ci%2 == 0 else 256)
        assert g['aligned_aliases'] == (0 if ci%2 == 0 else 768)
    expected = dict(schema='d143_crossed_address_noise_v1', stage='FIXED_COHORT_CROSSED_EXISTING_STREAMS',
        blocks=list(range(90000, 90016)), independent_blocks=16, lives_per_block=4, cases=256,
        noise_levels=4, address_levels=4, labelled_terminal_cells=4096,
        nominal_distinct_condition_stream_cells=2560, aligned_address_aliases=1536, diagonal_cells=1024,
        novel_ordinary_off_diagonal_cells=1536, new_founders=0, new_noise_histories=0, refitted_models=0,
        bootstrap_seed=14320260917, bootstrap_draws=10000, method_of_moments_clipped=False,
        multiplicity_adjusted=False, automatic_successor=False,
        interpretation='Mechanistic crossing of four already-sampled address and noise histories on known record-host pairs; not a new prospective founder or challenge test.')
    physics.nested({k: v for k, v in summary.items() if k != 'groups'}, expected)
    assert set(summary['groups']) == {'A_translated', 'A_aligned', 'B_translated', 'B_aligned'}
    return dict(passes=True, cases=256, independent_blocks=16, labelled_terminal_cells=4096,
        aligned_address_aliases=1536, diagonal_cells=1024, novel_ordinary_off_diagonal_cells=1536,
        fft_shape_checks=16384, max_shape_error=worst, new_dynamics=0)
