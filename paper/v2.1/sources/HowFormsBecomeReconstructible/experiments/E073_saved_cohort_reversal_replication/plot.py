"""Native-scale success and both prespecified persistence contrasts."""
import numpy as np


def plot(run, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    stats = summary['statistics']
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), layout='constrained')
    for ax, kind in zip(axes[:2], ('mixture', 'native'), strict=True):
        for policy, color in (('intact', '#2563eb'), ('pruned', '#c2410c')):
            rows = [stats[f'native/both/h{h}_{policy}_{kind}_pooled'] for h in (0, 1)]
            means = 100*np.array([r['mean'] for r in rows])
            ci = 100*np.array([r['interval'] for r in rows]).T
            ax.errorbar((0, 1), means, yerr=np.maximum(0, np.stack((means-ci[0], ci[1]-means))),
                        marker='o', color=color, label=policy, capsize=4)
        ax.set(xticks=(0, 1), xticklabels=('Before rewrite', 'After one rewrite'),
               xlim=(-.2, 1.2), ylim=(0, 105), ylabel='Both-cue success (%)',
               title=kind.title()+'; pooled histories; 95%')
        ax.legend(frameon=False)
    for h, color in ((0, '#64748b'), (1, '#c2410c')):
        row = stats[f'effect/both/pooled/mixture_gain_h{h}']
        mean = row['mean']*100
        lo, hi = np.array(row['interval'])*100
        axes[2].errorbar(mean, h, xerr=np.maximum(0, np.array([[mean-lo], [hi-mean]])),
                         fmt='o', capsize=4, color=color)
    axes[2].axvline(0, color='gray', lw=1)
    axes[2].set(yticks=(0, 1), yticklabels=('Immediate', 'After rewrite'), ylim=(-.5, 1.5),
                xlabel='Pruned minus intact (points)', title='Mixture primaries; adjusted 97.5%')
    fig.suptitle('E073 · saved-cohort reversal replication\n'+summary['status'])
    fig.savefig(run/'persistence.png', dpi=150)
    fig.savefig(run/'persistence.svg')
    plt.close(fig)
