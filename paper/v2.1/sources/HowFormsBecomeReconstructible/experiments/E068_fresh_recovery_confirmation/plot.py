"""Absolute function and the three prospective recovery requirements."""
import numpy as np


def plot(run, s):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stats = s['statistics']
    fig, ax = plt.subplots(1, 3, figsize=(17, 5), layout='constrained')
    horizons = [0, 1, 3]
    for kind, policy, label, color, style in (
            ('mixture', 'rewrite', 'Mixture: rewrite', '#c2410c', '-'),
            ('native', 'rewrite', 'Native: rewrite', '#2563eb', '-'),
            ('mixture', 'copy', 'Mixture: cumulative erasure', '#c2410c', '--')):
        keys = [f'native/both/h{h}_' + ('' if h == 0 else policy + '_') + kind + '_pooled' for h in horizons]
        vals = [stats[k] for k in keys]
        m = 100 * np.array([v['mean'] for v in vals]); bounds = 100 * np.array([v['interval'] for v in vals]).T
        ax[0].errorbar(horizons, m, yerr=np.maximum(0, np.stack((m - bounds[0], bounds[1] - m))),
                       fmt='o' + style, color=color, label=label, capsize=3)
    erased = [stats['native/both/' + ('h0_erased' if h == 0 else f'h{h}_rewrite_erased')]['mean'] * 100 for h in horizons]
    ax[0].plot(horizons, erased, 'o:', color='gray', label='Erased start: rewrite')
    baseline = stats['native/both/h0_mixture_pooled']['mean'] * 100
    ax[0].axhline(baseline, color='#c2410c', lw=1, alpha=.5, label='Unchanged mixture')
    ax[0].set(xticks=horizons, xlabel='Additional rewrites', ylabel='Both-cue success (%)', ylim=(-2, 102), title='Absolute function; pointwise 95%')
    ax[0].legend(frameon=False, fontsize=8)
    from E068_fresh_recovery_confirmation.plan import PRIMARY
    for i, name in enumerate(PRIMARY):
        v = stats['effect/both/pooled/' + name]; m = 100 * v['mean']; lo, hi = [100 * z for z in v['interval']]
        ax[1].errorbar(m, i, xerr=np.maximum(0, [[m - lo], [hi - m]]), fmt='o', color='#7e22ce', capsize=4)
    ax[1].axvline(0, color='gray', lw=1)
    ax[1].set(yticks=[0, 1, 2], yticklabels=['Absolute recovery', 'Beyond matched erasure', 'Beyond erased start'],
              xlabel='Percentage points', ylim=(-.6, 2.6), title='Three-rewrite primaries; 98.3333%')
    bottom = np.zeros(3)
    for metric, label, color in (('both', 'Success', '#15803d'), ('correct_signs_below_threshold', 'Correct signs, weak', '#ca8a04'),
                                ('zero_without_wrong_sign', 'Zero without wrong sign', '#a3a3a3'), ('any_wrong_sign', 'Wrong sign present', '#b91c1c')):
        vals = [100 * stats[f'native/{metric}/' + ('h0_' if h == 0 else f'h{h}_rewrite_') + 'mixture_pooled']['mean'] for h in horizons]
        ax[2].bar(np.arange(3), vals, bottom=bottom, label=label, color=color)
        bottom += vals
    ax[2].set(xticks=np.arange(3), xticklabels=horizons, xlabel='Additional rewrites', ylabel='Mixture reads (%)',
              ylim=(0, 102), title='Descriptive outcome composition')
    ax[2].legend(frameon=False, fontsize=8)
    fig.suptitle('E068 · ordinary rebuilding from an incompatible current record\n' + s['status'], fontsize=12)
    fig.savefig(run / 'rebuilding.png', dpi=150)
    fig.savefig(run / 'rebuilding.svg')
    plt.close(fig)
