"""Finite-horizon durability curves from independently audited outputs."""
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
    args = parser.parse_args(); run = args.run.resolve(); cap_cpus(8)
    assert run.is_relative_to(HERE/'analysis' if args.fixture else HERE/'runs')
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    complete = json.loads((run/'COMPLETE.json').read_text())
    assert complete['outputs_sha256']['summary.json'] == sha(run/'summary.json')
    s = json.loads((run/'summary.json').read_text())
    output = HERE/'figures'/run.name; output.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), sharex=True, sharey=True)
    hs = [1, 3, 8, 16]
    selected = [('maturing', 'Preserve strong / refresh weak', '#008c87'),
        ('strength_compensated', 'Full rewriting', '#d17b0f'), ('selective', 'Old exact-zero infill', '#ab4674'),
        ('masked_copy', 'Copy with erased edges', '#777777'), ('maturing_read_blocked', 'Maturing: reading blocked', '#3575b1'),
        ('maturing_refresh_blocked', 'Maturing: refreshing blocked', '#67499c')]
    for row, receiver in enumerate(s['receivers']):
        for ax, injury in zip(axes[row], s['damage']):
            for condition, label, color in selected:
                st = [s['groups'][str(h)][receiver][condition]['both_cues'][injury]['own'] for h in hs]
                means = 100*np.array([x['mean'] for x in st])
                bounds = 100*np.array([x['ci95'] for x in st])
                ax.plot(hs, means, '-o', color=color, label=label, markersize=4)
                ax.fill_between(hs, bounds[:, 0], bounds[:, 1], color=color, alpha=.12)
            ax.axhline(75, color='black', linestyle=':', linewidth=.8)
            ax.set(title=f'{receiver} · {injury}', xticks=hs, ylim=(-3, 103), xlabel='Damaged replacements')
            ax.grid(alpha=.15); ax.spines[['top', 'right']].set_visible(False)
    for ax in axes[:, 0]: ax.set_ylabel('Both cues correct (%)')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(.5, .005))
    cohort = 'EXCLUDED TECHNICAL RUN' if s['evidence_status'] == 'technical' else f"{len(s['blocks'])} fresh blocks / {s['lineages']} lineages"
    fig.suptitle(f'E031: durability through sixteen renewals · {cohort}', fontsize=14)
    fig.text(.5, .095, 'Whole-block 95% intervals; secondary intervals pointwise. All ten policies and controls appear in the report.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .12, 1, .95))
    for ext in ('png', 'svg'): fig.savefig(output/f'durability.{ext}', dpi=160)
    plt.close(fig)
    dump(output/'provenance.json', dict(summary_sha256=sha(run/'summary.json'), complete_sha256=sha(run/'COMPLETE.json'),
        audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(output.iterdir())}))
    print('Figures:', output, flush=True)


if __name__ == '__main__': main()
