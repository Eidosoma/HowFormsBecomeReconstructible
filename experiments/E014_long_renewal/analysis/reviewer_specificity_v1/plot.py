"""Native-scale, publication-ready figures from the verified score decomposition."""
import argparse
from pathlib import Path
from analysis import HERE, FACTORS, CHECKPOINTS, read, sha, write_json
from common import cap_cpus, utc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

COLORS = {'rewrite':'#176783', 'foreign':'#b55624', 'copy':'#515761'}
LABELS = {'rewrite':'Own record', 'foreign':'Matched foreign record', 'copy':'Protected copy'}


def series(ax, stats, factor, stages, x, metric='qualified', legend=True, bands=True):
    for arm, marker in (('rewrite', 'o'), ('foreign', 's'), ('copy', '^')):
        entries = [stats[f'{factor}/{s}/{arm}/{metric}'] for s in stages]
        y = np.array([e['mean'] for e in entries]); ci = np.array([e['ci95'] for e in entries])
        ax.plot(x, y, marker=marker, ms=4, lw=1.6, color=COLORS[arm], ls='--' if arm == 'copy' else '-',
                label=LABELS[arm] if legend else None)
        if bands: ax.fill_between(x, ci[:, 0], ci[:, 1], color=COLORS[arm], alpha=.09)
    own = [stats[f'{factor}/{s}/rewrite/{metric}']['mean'] for s in stages]
    foreign = [stats[f'{factor}/{s}/foreign/{metric}']['mean'] for s in stages]
    ax.fill_between(x, own, foreign, color=COLORS['rewrite'], alpha=.22, linewidth=0)
    ax.grid(axis='y', alpha=.17); ax.set_xticks(x)


def save(fig, out, stem, outputs):
    for ext in ('png', 'svg', 'pdf'):
        p = out/f'{stem}.{ext}'; assert not p.exists(); fig.savefig(p, dpi=180); outputs[p.name] = sha(p)
    plt.close(fig)


def main(products):
    cap_cpus(1); products = products.resolve(); assert products.is_relative_to(HERE)
    summary = read(products/'summary.json'); stats = summary['statistics']; outputs = {}
    audited = read(products/'AUDIT.json')
    assert audited['status'] == 'PASS' and audited['summary_sha256'] == sha(products/'summary.json')
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False,
                         'svg.fonttype':'none', 'pdf.fonttype':42})
    stages = [f'after_{h}' for h in CHECKPOINTS]; x = np.array(CHECKPOINTS)
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.2), layout='constrained', sharey=True)
    for ax, factor in zip(axes, FACTORS):
        series(ax, stats, factor, stages, x)
        ax.set(xlim=(0, 17), ylim=(0, 1), xlabel='Completed rewrites', ylabel='Qualified agreement Q (native 0–1 score)',
               title=f'{2048//factor**2} bytes'+(' · compact record' if factor == 4 else ' · full field'))
        if factor == 4:
            handles, labels = ax.get_legend_handles_labels()
            handles.append(Patch(facecolor=COLORS['rewrite'], alpha=.22)); labels.append('Own−foreign gap')
            ax.legend(handles, labels, loc='upper left', frameon=False, fontsize=9)
        inset = ax.inset_axes([.13, .13, .73, .35])
        series(inset, stats, factor, stages, x, legend=False, bands=False)
        inset.set(xlim=(0, 17), ylim=(.58, .80), title='Detail: same Q units'); inset.title.set_fontsize(8)
        inset.tick_params(labelsize=8); inset.set_yticks([.6, .7, .8])
        q = stats[f'{factor}/after_16/rewrite/qualified']; f = stats[f'{factor}/after_16/foreign/qualified']; c = stats[f'{factor}/after_16/copy/qualified']
        d = stats[f'{factor}/after_16/rewrite_minus_foreign/qualified']
        ax.text(.02, -.22, f'At 16: own {q["mean"]:.4f}; foreign {f["mean"]:.4f}; protected {c["mean"]:.4f}\n'
            f'Incremental own−foreign: {100*d["mean"]:.3f} points [{100*d["ci95"][0]:.3f}, {100*d["ci95"][1]:.3f}]',
            transform=ax.transAxes, fontsize=9, va='top')
    fig.suptitle('Historical specificity is the own−foreign gap, not total agreement\nE014: all 64 blocks / 256 founders; fresh checkpoint readers', fontsize=13)
    fig.supxlabel('Bands: pointwise 95% whole-block intervals. Every arm is scored against the same own-founder prototype.', fontsize=9)
    save(fig, products, 'historical_specificity', outputs)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7), layout='constrained', sharey=True)
    for ax, factor in zip(axes, FACTORS):
        x = np.arange(16)
        series(ax, stats, factor, [f'G{g}' for g in range(1, 17)], x)
        ax.set(xlabel='Rewrites completed before this lineage read', ylabel='Qualified agreement Q (native 0–1)',
               ylim=(0, 1), xticks=(0, 2, 7, 15), title=f'{2048//factor**2} bytes')
        if factor == 4: ax.legend(frameon=False, loc='lower left', fontsize=9)
    fig.suptitle('E014 lineage reads — separate from fresh checkpoint probes')
    fig.supxlabel('G1 follows zero rewrites; G16 follows 15. Reader streams differ from checkpoint probes. Bands: pointwise 95% block intervals.', fontsize=9)
    save(fig, products, 'lineage_agreement', outputs)

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.5), layout='constrained')
    palette = ('#176783', '#679a44', '#9d65a0', '#c4c4c4')
    for col, factor in enumerate(FACTORS):
        ax = axes[0, col]
        for metric, label, color, marker in (('qualified', 'Qualified agreement Q', '#176783', 'o'),
                ('sign', 'Sign agreement S', '#679a44', 's'), ('amplitude', 'Amplitude-qualified A', '#9d65a0', '^')):
            e = [stats[f'{factor}/{s}/rewrite/{metric}'] for s in stages]; y = np.array([z['mean'] for z in e]); ci = np.array([z['ci95'] for z in e])
            ax.plot(CHECKPOINTS, y, marker=marker, color=color, label=label, ms=4)
            ax.fill_between(CHECKPOINTS, ci[:, 0], ci[:, 1], color=color, alpha=.12)
        ax.set(title=f'{2048//factor**2} bytes · own-record arm', xlabel='Completed rewrites', ylabel='Fraction of all 256 sites', ylim=(0, 1), xticks=CHECKPOINTS)
        ax.grid(axis='y', alpha=.2); ax.legend(frameon=False, fontsize=9, loc='lower left')
        ax = axes[1, col]; bottom = np.zeros(4)
        for metric, label, color in zip(('qualified', 'matched_unresolved', 'mismatched_resolved', 'mismatched_unresolved'),
                ('Matching + resolved (Q)', 'Matching + unresolved', 'Mismatching + resolved', 'Mismatching + unresolved'), palette):
            y = np.array([stats[f'{factor}/{s}/rewrite/{metric}']['mean'] for s in stages])
            ax.bar(np.arange(4), y, bottom=bottom, label=label, color=color, width=.62); bottom += y
        ax.set(xticks=np.arange(4), xticklabels=CHECKPOINTS, xlabel='Completed rewrites', ylabel='Four exhaustive score categories', ylim=(0, 1))
        if col == 0: ax.legend(frameon=False, fontsize=8, loc='upper center', bbox_to_anchor=(.5, -.18), ncol=2)
    fig.suptitle('The score combines sign matching and amplitude qualification\nQ = S − matched-but-unresolved fraction; Q generally differs from S×A', fontsize=13)
    fig.supxlabel('Same unprescribed E014 apparatus; strict |v|>.2. All 256 sites retained. New intervals are descriptive, pointwise 95% block intervals.', fontsize=9)
    save(fig, products, 'sign_amplitude', outputs)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout='constrained'); names = ('homogeneous', 'heterogeneous')
    g = [summary['pilot_context'][n] for n in names]; colors = ['#b55624', '#176783']
    rates = [z['formation_fraction'] for z in g]
    axes[0].bar(range(2), rates, color=colors, width=.55)
    axes[0].axhline(.75, color='#555', ls='--', lw=1, label='75% required')
    for i, z in enumerate(g): axes[0].text(i, rates[i]+.035, f'{z["formation_qualified"]}/32', ha='center')
    axes[0].set(ylim=(0, 1), ylabel='Fraction of founders passing formation', title='Formation qualification'); axes[0].legend(frameon=False, loc='lower left')
    y = np.array([z['historical_contrast']['mean'] for z in g]); ci = np.array([z['historical_contrast']['ci95'] for z in g])
    axes[1].bar(range(2), y, color=colors, width=.55, yerr=np.stack((y-ci[:, 0], ci[:, 1]-y)), capsize=4)
    for i, z in enumerate(g): axes[1].text(i, ci[i, 1]+.02, f'+{100*y[i]:.2f} points', ha='center')
    axes[1].set(ylim=(0, .39), ylabel='Own−foreign Q (native score difference)', title='Historical dependence after three rewrites')
    for ax in axes: ax.set_xticks(range(2), ['Homogeneous', 'Shared heterogeneous']); ax.grid(axis='y', alpha=.15)
    fig.suptitle('A strong history effect does not establish stable formation\nE001 development pilot: eight blocks / 32 founders per setting', fontsize=13)
    fig.supxlabel('Both settings pass the diversity criterion. All founders retained. Intervals are exploratory 95% whole-block intervals; no pooling with E014.', fontsize=9)
    save(fig, products, 'pilot_history_formation', outputs)
    write_json(products/'FIGURE_PROVENANCE.json', dict(utc=utc(), code_sha256=sha(__file__),
        summary_sha256=sha(products/'summary.json'), audit_sha256=sha(products/'AUDIT.json'), outputs_sha256=outputs))
    print('Saved four figure sets (PNG, SVG and PDF).')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--products', type=Path, required=True); main(p.parse_args().products)
