"""Standalone scientific time-course figure from the declared analysis."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from extract import HERE, read, sha, write_json


def main():
    folder = HERE / 'results'
    summary = read(folder / 'analysis.json')
    colors = {'exact_rewrite': '#31363b', 'tolerance_rewrite': '#c94535',
              'sign_restored': '#b38927', 'magnitude_restored': '#368967',
              'single_tolerance_rewrite': '#2875b8'}
    labels = {'exact_rewrite': 'Original', 'tolerance_rewrite': 'Repeated tolerance',
              'sign_restored': 'Restore signs', 'magnitude_restored': 'Restore magnitudes',
              'single_tolerance_rewrite': 'Single pulse → original'}
    panels = [('body_pass', 'Native body success', 'Both-cue success (%)', 100),
              ('signed_transfer', 'Cue transmission in the outgoing record', 'Signed transfer (64 linear steps)', 1),
              ('reader_distance_original', 'Distance from the original history', 'Mean row L1 distance', 1),
              ('hypothetical_tolerance_substitution_fraction', 'Susceptibility to tolerance substitution', 'Available edges with 0 < |q| ≤ 10⁻⁴ (%)', 100)]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.8), constrained_layout=True)
    for ax, (metric, title, ylabel, factor) in zip(axes.flat, panels):
        for w in colors:
            values = [r for r in summary['curves'] if r['writer'] == w]
            x = [r['generation'] for r in values]
            y = factor*np.array([r['metrics'][metric]['mean'] for r in values])
            ax.plot(x, y, color=colors[w], label=labels[w], lw=2 if w in ('exact_rewrite', 'tolerance_rewrite', 'single_tolerance_rewrite') else 1.4,
                linestyle='-' if w in ('exact_rewrite', 'tolerance_rewrite', 'single_tolerance_rewrite') else '--')
        ax.axvline(4, color='#888888', lw=.8, ls=':')
        ax.set(title=title, xlabel='Rebuild generation', ylabel=ylabel, xlim=(3, 32))
        ax.grid(alpha=.18)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0, 0].set_ylim(-2, 103)
    handles, labels_ = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc='outside lower center', ncol=3, frameon=False, fontsize=10)
    fig.suptitle('Recovery after one tolerance write versus continued tolerance writing\n'
                 'Eight exposed blocks · 128 lineages per policy · O resumes for the pulse at generation 4', fontsize=13)
    outputs = {}
    for suffix in ('png', 'svg', 'pdf'):
        path = folder / ('recovery_timecourses.' + suffix)
        assert not path.exists()
        fig.savefig(path, dpi=180)
        outputs[path.name] = sha(path)
    plt.close(fig)
    write_json(folder / 'figure_provenance.json', dict(analysis_sha256=sha(folder / 'analysis.json'),
        code_sha256=sha(HERE / 'plot.py'), outputs_sha256=outputs,
        uncertainty='Lines are equal-block means. No inferential bands; all eight block values retained in analysis.json.',
        native_vs_surrogate='Body success is native; transmission and row distances are record diagnostics.'))


if __name__ == '__main__':
    main()
