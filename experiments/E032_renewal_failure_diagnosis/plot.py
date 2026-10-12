"""Saved record and body measurements, explicitly exploratory."""
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
    r = parser.parse_args().run.resolve(); cap_cpus(8)
    a = json.loads((r/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status'] == 'PASS' and a['complete_sha256'] == sha(r/'COMPLETE.json')
    s = json.loads((r/'summary.json').read_text()); series = s['series']
    dest = HERE/'figures'/r.name; dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    metrics = [('packet', 'strong', 'Strong edges in outgoing record', range(17)),
        ('packet', 'changed_sign_nonzero', 'Edges with changed acquired sign', range(17)),
        ('graph', 'output_reachable_fraction', 'Output cells reachable through strong edges', range(17)),
        ('body', 'both_correct', 'Current body: both cues correct', range(1, 17)),
        ('body', 'locked_output_failure', 'Current body: at least one output locked', range(1, 17)),
        ('transitions', 'never_failed_yet', 'No observed body failure so far', range(1, 17))]
    for ax, (kind, field, title, generations) in zip(axes.ravel(), metrics):
        for c, label, color in [('maturing', 'Preserve strong / refresh weak', '#008c87'), ('strength_compensated', 'Full rewriting', '#d17b0f')]:
            values = [series[f'{kind}.g{g}.{c}.{field}'] for g in generations]
            ax.plot(list(generations), [x['mean'] for x in values], '-o', label=label, color=color, markersize=3)
            ax.fill_between(list(generations), [x['ci95'][0] for x in values], [x['ci95'][1] for x in values], color=color, alpha=.15)
        ax.set(title=title, xlabel='Replacement', xticks=[0, 1, 3, 8, 16] if kind in ('packet', 'graph') else [1, 3, 8, 16])
        ax.grid(alpha=.15); ax.spines[['top', 'right']].set_visible(False)
        if kind != 'packet': ax.set_ylim(-.03, 1.03)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False)
    title = 'EXCLUDED TECHNICAL FIXTURE' if s['status'] == 'TECHNICAL_ONLY' else 'Exploratory diagnosis of existing E031 histories'
    fig.suptitle('E032 · '+title)
    fig.text(.5, .065, 'Pointwise whole-block intervals. Sign changes and strong-edge connectivity are descriptive, not causal tests.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .09, 1, .94))
    for ext in ('png', 'svg'): fig.savefig(dest/f'diagnosis.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(summary_sha256=sha(r/'summary.json'), complete_sha256=sha(r/'COMPLETE.json'),
        audit_sha256=sha(r/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir())}))


if __name__ == '__main__': main()
