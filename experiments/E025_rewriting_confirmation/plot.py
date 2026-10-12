"""Audited paired receiver outcomes, with source and image hashes."""
import argparse
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import cap_cpus, dump, sha
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('run', type=Path)
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args(); run = args.run.resolve(); cap_cpus()
    if args.fixture:
        assert run.is_relative_to(HERE/'analysis')
        assert json.loads((run/'manifest.json').read_text())['contract']['mode'] == 'technical_fixture'
    else:
        assert run.is_relative_to(HERE/'runs')
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    complete = json.loads((run/'COMPLETE.json').read_text())
    assert complete['outputs_sha256']['summary.json'] == sha(run/'summary.json')
    s = json.loads((run/'summary.json').read_text())
    output = HERE/'figures'/run.name; output.mkdir(parents=True, exist_ok=False)
    labels = ['Baseline renewal', 'Degree-compensated renewal', 'Strength-compensated renewal',
              'Intact renewal', 'Protected copy', 'Copy with erased edges', 'Reading blocked', 'Writing blocked']
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 10), sharey=True)
    fig.subplots_adjust(left=.245, right=.985, top=.855, bottom=.16, wspace=.13, hspace=.36)
    for row, h in enumerate((1, 3)):
        for ax, damage, title in zip(axes[row], s['damage'], ['Intact receiver', 'Receiver: 24 cells removed', 'Receiver: 3×3 lesion']):
            for i, c in enumerate(s['conditions']):
                for receiver, offset, color, marker in [('fixed_four', -.13, '#777777', 'o'), ('local_strength', .13, '#008c87', 's')]:
                    st = s['groups'][str(h)][receiver][c]['both_cues'][damage]['own']
                    mean, lo, hi = 100*st['mean'], 100*st['ci95'][0], 100*st['ci95'][1]
                    ax.errorbar(mean, i+offset, xerr=np.maximum(0, [[mean-lo], [hi-mean]]), fmt=marker,
                        color=color, capsize=3, markersize=5, label=receiver if i == 0 else None)
            ax.set(title=f'{h} replacement(s) · {title}', xlim=(-3, 103), xticks=range(0, 101, 20), xlabel='Both cues correct (%)')
            ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
            if damage in ('intact', 'scattered'): ax.axvline(75, color='black', linestyle=':', linewidth=.8)
    axes[0, 0].set_yticks(np.arange(8), labels); axes[0, 0].invert_yaxis()
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, ['Unchanged receiver', 'Normalized receiver'], loc='upper center', bbox_to_anchor=(.62, .94), ncol=2, frameon=False)
    cohort = 'excluded technical fixture' if args.fixture else ('excluded technical benchmark' if s['evidence_status'] == 'technical' else f"{len(s['blocks'])} fresh blocks / {s['lineages']} lineages")
    fig.suptitle(f'E025: fresh confirmation of the rewriting advantage · {cohort}', y=.985)
    p = s['primary']['statistics']
    fig.supxlabel(f"Primary scattered-terminal advantage after three renewals, candidate minus cumulative-erasure copy: {100*p['mean']:.1f} points "
        f"[95% {100*p['ci95'][0]:.1f}, {100*p['ci95'][1]:.1f}].\n"
        'Fresh 24-cell loss at each renewal. Same packets, births, noise and injury in paired terminal receivers.\n'
        'Whole-block intervals; secondary comparisons pointwise. Original-packet reference is retained in the report.', fontsize=9, y=.028)
    for ext in ('png', 'svg'): fig.savefig(output/f'rewriting_confirmation.{ext}', dpi=170)
    plt.close(fig)
    dump(output/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(output.iterdir())}))
    print('Figures:', output, flush=True)


if __name__ == '__main__': main()
