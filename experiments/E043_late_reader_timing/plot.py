"""Audited receiving-schedule comparisons on unchanged packets."""
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
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); r=p.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((r/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(r/'COMPLETE.json')
    s = json.loads((r/'summary.json').read_text()); dest = HERE/'figures'/r.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharex=True, sharey=True)
    labels = ['Original', 'Extra time alone', 'Delayed with extra time']
    for row, h in enumerate((24, 32)):
        for ax, d in zip(axes[row], s['damage']):
            for i, t in enumerate(s['timings']):
                for reader, offset, color in (('fixed_four', -.12, '#888888'), ('local_strength', .12, '#008c87')):
                    x = s['groups'][str(h)][reader][t]['both_cues'][d]['own']
                    v, lo, hi = [100*z for z in (x['mean'], *x['ci95'])]
                    ax.errorbar(v, i+offset, xerr=np.maximum(0, [[v-lo], [hi-v]]), fmt='o', color=color, capsize=3,
                        label=reader if i == 0 else None)
            ax.axvline(75, ls=':', color='black', lw=.8); ax.set(title=f'Record after {h} renewals · {d}', xlim=(-3, 103), xlabel='Both cues correct (%)')
            ax.grid(axis='x', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    axes[0, 0].set_yticks(range(3), labels); axes[0, 0].invert_yaxis()
    handles, label = axes[0, 0].get_legend_handles_labels(); fig.legend(handles, ['Fixed-four receiver', 'Normalized receiver'], loc='lower center', ncol=2, frameon=False)
    title = 'EXCLUDED TECHNICAL RUN' if s['mode'] != 'scientific' else '512 existing lineages; packets unchanged'
    fig.suptitle('E043: timing on late bridge-rewrite records · '+title)
    fig.text(.5, .055, 'Pointwise whole-block 95% intervals. Receiving intervention only; serial renewal is unchanged.', ha='center', fontsize=9)
    fig.tight_layout(rect=(.03, .09, 1, .95))
    for ext in ('png', 'svg'): fig.savefig(dest/f'expression.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(r/'summary.json'), complete_sha256=sha(r/'COMPLETE.json'), audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'),
        plot_code_sha256=sha(__file__), outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__': main()
