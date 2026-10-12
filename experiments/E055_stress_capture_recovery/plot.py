"""Native-score body/recipient comparison bound to the independently audited summary."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import dump, sha, utc
from E055_stress_capture_recovery.plan import HERE, NAMES, HISTORIES
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(mode):
    run = HERE/'runs'/NAMES[mode]; dest = HERE/'figures'/NAMES[mode]
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(run/'COMPLETE.json')
    s = json.loads((run/'summary.json').read_text()); stats = s['statistics']
    dest.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharey=True)
    for h, history in enumerate(HISTORIES):
        for p, pulse in enumerate(('sham', 'pulse')):
            body = [f'body/both/{history}/{pulse}/{t}' for t in ('before', 'early', 'late')]
            fresh = [f'fresh/both/{history}/{pulse}_{t}/scattered' for t in ('early', 'late')]
            for ax, keys, labels in ((axes[h, 0], body, ('Before', 'Pulse end', 'After recovery')),
                                    (axes[h, 1], fresh, ('Early record', 'Late record'))):
                y = np.array([stats[k]['mean'] for k in keys])*100
                bounds = np.array([stats[k]['interval'] for k in keys])*100
                ax.errorbar(np.arange(len(y))+.025*(p*2-1), y,
                    yerr=np.maximum(0, np.stack((y-bounds[:, 0], bounds[:, 1]-y))),
                    fmt='o-', capsize=3, label=pulse)
                ax.set_xticks(range(len(labels)), labels); ax.set_ylim(-3, 103); ax.grid(alpha=.2)
        protected = 100*stats[f'fresh/both/{history}/protected_sham/scattered']['mean']
        axes[h, 1].axhline(protected, color='gray', linestyle=':', label='protected packet')
        axes[h, 0].set_ylabel('Both-cue success (%)')
        axes[h, 0].set_title(history.replace('_', ' ')+': current body')
        axes[h, 1].set_title('Fresh recipient, scattered injury')
        for ax in axes[h]: ax.legend(fontsize=8, loc='best')
    fig.suptitle('E055: pulse effects before and after the record boundary\n'+s['status']+'; pointwise block-bootstrap 95% intervals', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .95))
    for ext in ('png', 'svg'): fig.savefig(dest/f'capture_recovery.{ext}', dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json', dict(utc=utc(), audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        summary_sha256=sha(run/'summary.json'), plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir()) if p.is_file()}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--mode', required=True, choices=NAMES); main(p.parse_args().mode)
