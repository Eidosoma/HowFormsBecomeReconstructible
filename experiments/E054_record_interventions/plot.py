"""Audited common-assay outcome plot with explicit technical labeling."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import dump, sha, utc
from E054_record_interventions.plan import HERE, NAMES, HISTORIES, ARMS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(mode):
    run = HERE/'runs'/NAMES[mode]; summary = json.loads((run/'summary.json').read_text())
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    out = HERE/'figures'/NAMES[mode]; out.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    for h, history in enumerate(HISTORIES):
        for ax, metric in zip(axes, ('both', 'aligned_transfer')):
            stats = [summary['statistics'][f'{metric}/{history}/{arm}/scattered'] for arm in ARMS]
            y = np.array([s['mean'] for s in stats]); factor = 100 if metric == 'both' else 1
            ax.plot(np.arange(11), factor*y, 'o-', label=history, alpha=.8, markersize=4)
            ax.set_xticks(range(11), [a.replace('_', ' ') for a in ARMS], rotation=55, ha='right')
            ax.grid(alpha=.2)
    axes[0].set_ylabel('Both-cue task success (%)'); axes[0].set_ylim(-3, 103)
    axes[1].set_ylabel('Rule-aligned signed transfer'); axes[1].axhline(0, color='black', lw=.8)
    axes[0].legend(fontsize=8)
    fig.suptitle('E054 — '+('TECHNICAL VALIDATION ONLY; excluded block 900041' if mode != 'scientific' else 'Existing E051 records, fresh readers')+'\nScattered injury; points show means, intervals retained in summary')
    for ext in ('png', 'svg'): fig.savefig(out/f'record_interventions.{ext}', dpi=150)
    plt.close(fig)
    dump(out/'provenance.json', dict(utc=utc(), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        summary_sha256=sha(run/'summary.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=NAMES, required=True); main(p.parse_args().mode)
