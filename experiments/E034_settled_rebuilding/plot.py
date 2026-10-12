"""Audited crossed renewal/receiving comparison."""
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
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); r = p.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((r/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(r/'COMPLETE.json')
    s = json.loads((r/'summary.json').read_text()); dest = HERE/'figures'/r.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharex=True, sharey=True)
    pairs = [('original', 'original'), ('original', 'delayed'), ('delayed', 'original'), ('delayed', 'delayed')]
    labels = ['Original renewal / original test', 'Delayed renewal / original test',
              'Original renewal / delayed test', 'Delayed renewal / delayed test']
    for ax, injury in zip(axes, s['damage']):
        for i, (timing, condition) in enumerate(pairs):
            for reader, offset, color in (('fixed_four', -.12, '#888888'), ('local_strength', .12, '#008c87')):
                x = s['groups'][timing][reader][condition]['both_cues'][injury]['own']
                v, lo, hi = [100*z for z in (x['mean'], *x['ci95'])]
                ax.errorbar(v, i+offset, xerr=np.maximum(0, [[v-lo], [hi-v]]), fmt='o', color=color, capsize=3,
                            label=reader if i == 0 else None)
        ax.axvline(75, ls=':', color='black', lw=.8)
        ax.set(title=injury.capitalize()+' terminal test', xlim=(-3, 103), xlabel='Both cues correct (%)')
        ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yticks(range(4), labels); axes[0].invert_yaxis()
    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(handles, ['Fixed-four receiver', 'Normalized receiver'], loc='lower center', ncol=2, frameon=False)
    title = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else '512 existing lineages; generation 8 to 9'
    fig.suptitle('E034: longer settling during rebuilding · '+title)
    fig.text(.5, .09, 'Writer and total read steps unchanged. Pointwise whole-block 95% intervals; one renewal boundary.', ha='center', fontsize=9)
    fig.tight_layout(rect=(.03, .14, 1, .92))
    for ext in ('png', 'svg'): fig.savefig(dest/f'rebuilding.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(r/'summary.json'), complete_sha256=sha(r/'COMPLETE.json'),
        audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__':
    main()
