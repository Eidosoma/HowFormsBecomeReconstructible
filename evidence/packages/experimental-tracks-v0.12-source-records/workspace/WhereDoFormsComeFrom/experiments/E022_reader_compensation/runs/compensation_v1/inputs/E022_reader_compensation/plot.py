"""Audited one-boundary compensation comparisons, with explicit provenance."""
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
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    cap_cpus()
    assert run.is_relative_to(HERE/'runs')
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    complete = json.loads((run/'COMPLETE.json').read_text())
    assert complete['outputs_sha256']['summary.json'] == sha(run/'summary.json')
    s = json.loads((run/'summary.json').read_text())
    output = HERE/'figures'/run.name
    output.mkdir(parents=True, exist_ok=False)
    labels = ['Original packet', 'Unchanged reader', 'Physical-degree compensation', 'Local-strength compensation',
              'Intact renewal', 'Protected copy', 'Copy with erased edges', 'Reading blocked', 'Writing blocked']
    colors = ['#222222', '#747474', '#3268a8', '#008c87', '#4d963e', '#536878', '#ad792d', '#c76536', '#a84e86']
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.3), sharey=True)
    fig.subplots_adjust(left=.24, right=.985, top=.84, bottom=.22, wspace=.13)
    for ax, damage, title in zip(axes, s['damage'], ['Intact assay', 'Assay: 24 cells removed', 'Assay: 3×3 lesion']):
        for i, (h, condition) in enumerate(s['panels']):
            st = s['groups'][str(h)][condition]['both_cues'][damage]['own']
            mean, lo, hi = 100*st['mean'], 100*st['ci95'][0], 100*st['ci95'][1]
            ax.errorbar(mean, i, xerr=np.maximum(0, [[mean-lo], [hi-mean]]), fmt='o', color=colors[i], capsize=3, markersize=6)
        ax.set(title=title, xlim=(-3, 103), xticks=range(0, 101, 20), xlabel='Both cues correct (%)')
        ax.grid(axis='x', alpha=.2)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yticks(np.arange(9), labels)
    axes[0].invert_yaxis()
    axes[0].axvline(75, color='black', linestyle=':', linewidth=.8)
    cohort = 'excluded technical benchmark' if s['evidence_status'] == 'technical' else f"{len(s['blocks'])} fresh blocks / {s['lineages']} lineages"
    fig.suptitle(f'E022: local compensation during one damaged renewal · {cohort}', y=.96)
    p = s['primary']['statistics']
    fig.supxlabel(f"Primary benefit, strength compensation minus unchanged reading: {100*p['mean']:.1f} points "
        f"[95% {100*p['ci95'][0]:.1f}, {100*p['ci95'][1]:.1f}].\n"
        'One replacement; 24 non-port cells absent from birth. Writer and terminal reader unchanged.\n'
        'Whole-block intervals; secondary comparisons pointwise. Original packet is a horizon-0 reference.', fontsize=9, y=.025)
    for extension in ('png', 'svg'):
        fig.savefig(output/f'reader_compensation.{extension}', dpi=170)
    plt.close(fig)
    dump(output/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))
    print('Figures:', output, flush=True)


if __name__ == '__main__': main()
