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
    run = parser.parse_args().run.resolve(); cap_cpus()
    assert run.is_relative_to(HERE/'runs')
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    complete = json.loads((run/'COMPLETE.json').read_text())
    assert complete['outputs_sha256']['summary.json'] == sha(run/'summary.json')
    s = json.loads((run/'summary.json').read_text())
    output = HERE/'figures'/run.name; output.mkdir(parents=True, exist_ok=False)
    packets = [(0, 'initial')]+[(1, c) for c in s['conditions']]
    labels = ['Original packet', 'Baseline renewal', 'Degree-compensated renewal', 'Strength-compensated renewal',
              'Intact renewal', 'Protected copy', 'Copy with erased edges', 'Reading blocked', 'Writing blocked']
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 7.3), sharey=True)
    fig.subplots_adjust(left=.245, right=.985, top=.82, bottom=.22, wspace=.13)
    for ax, damage, title in zip(axes, s['damage'], ['Intact receiver', 'Receiver: 24 cells removed', 'Receiver: 3×3 lesion']):
        for i, (h, c) in enumerate(packets):
            for receiver, offset, color, marker in [('fixed_four', -.13, '#777777', 'o'), ('local_strength', .13, '#008c87', 's')]:
                st = s['groups'][str(h)][receiver][c]['both_cues'][damage]['own']
                mean, lo, hi = 100*st['mean'], 100*st['ci95'][0], 100*st['ci95'][1]
                ax.errorbar(mean, i+offset, xerr=np.maximum(0, [[mean-lo], [hi-mean]]), fmt=marker,
                    color=color, capsize=3, markersize=5, label=receiver if i == 0 else None)
        ax.set(title=title, xlim=(-3, 103), xticks=range(0, 101, 20), xlabel='Both cues correct (%)')
        ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yticks(np.arange(9), labels); axes[0].invert_yaxis()
    for ax in axes[:2]: ax.axvline(75, color='black', linestyle=':', linewidth=.8)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, ['Unchanged receiver', 'Normalized receiver'], loc='upper center', bbox_to_anchor=(.62, .905), ncol=2, frameon=False)
    cohort = 'excluded technical benchmark' if s['evidence_status'] == 'technical' else f"{len(s['blocks'])} fresh blocks / {s['lineages']} lineages"
    fig.suptitle(f'E023: local compensation in the receiving body · {cohort}', y=.975)
    p = s['primary']['statistics']
    fig.supxlabel(f"Primary scattered-terminal benefit for strength-compensated packets: {100*p['mean']:.1f} points "
        f"[95% {100*p['ci95'][0]:.1f}, {100*p['ci95'][1]:.1f}].\n"
        'Same packets, births, noise and injury in paired receivers. One replacement; writer unchanged.\n'
        'Whole-block intervals; secondary comparisons pointwise. Original packet is a horizon-0 reference.', fontsize=9, y=.028)
    for ext in ('png', 'svg'): fig.savefig(output/f'receiver_compensation.{ext}', dpi=170)
    plt.close(fig)
    dump(output/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(output.iterdir())}))
    print('Figures:', output, flush=True)


if __name__ == '__main__': main()
