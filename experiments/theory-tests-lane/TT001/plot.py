"""Fixed four-panel view of development Brier-score comparisons."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def render(output, summary, plan):
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    labels = ['Prevalence', 'Markov', 'Current logistic', 'Prefix logistic', 'Prefix boosted']
    for row, k in enumerate(plan['prefixes']):
        for col, endpoint in enumerate(plan['endpoints']):
            ax = axes[row, col]
            items = [summary['scores'][f'k{k}.{endpoint}.{m}']['brier_gain_over_prevalence'] for m in plan['models']]
            means = np.array([a['mean'] for a in items])
            bounds = np.array([a['descriptive_interval'] for a in items])
            y = np.arange(len(items))
            ax.hlines(y, bounds[:, 0], bounds[:, 1], color='#245879', linewidth=2)
            ax.plot(means, y, 'o', color='#245879')
            ax.axvline(0, color='#888888', linewidth=1)
            ax.set_yticks(y, labels); ax.invert_yaxis()
            ax.set_title(f'Observe {k} rebuilds · '+('Terminal success' if endpoint == 'terminal' else 'Future path and terminal'))
            ax.set_xlabel('Brier improvement over training prevalence')
            ax.grid(axis='x', alpha=.2)
    fig.suptitle('Conventional forecasts on exposed E041 development data\nPositive values improve prediction; intervals condition on fitted cross-validation predictions', fontsize=12)
    fig.savefig(output/'brier_comparisons.png', dpi=160)
    fig.savefig(output/'brier_comparisons.pdf')
    plt.close(fig)
