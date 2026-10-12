#!/usr/bin/env python3
"""Plot saved D140 fields from a portable extract; no scientific-model imports."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.cm import ScalarMappable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'paper_assets/data/retained-reconstruction-history-v1.npz'
METADATA = DATA.with_suffix('.json')
DEST = ROOT / 'paper_assets/figures'
INK, MUTED, TEAL, AMBER = '#123b49', '#52616b', '#087f8c', '#a76a12'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 19,
                     'svg.fonttype': 'none', 'svg.hashsalt': 'forms-d140-history-v1',
                     'text.color': INK, 'axes.labelcolor': INK})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    meta = json.loads(METADATA.read_text())
    if sha(DATA) != meta['data_sha256']:
        raise ValueError('Portable data hash mismatch')
    with np.load(DATA, allow_pickle=False) as archive:
        data = {key: archive[key].copy() for key in archive.files}
    body_limit = max(float(np.max(np.abs(data[key]))) for key in
                     ('read_end_bodies', 'writer_end_bodies', 'terminal_bodies'))
    record_limit = max(float(np.max(np.abs(data[key]))) for key in ('initial_records', 'outgoing_records'))
    norms = {'V': TwoSlopeNorm(vmin=-body_limit, vcenter=0, vmax=body_limit),
             'p': TwoSlopeNorm(vmin=-record_limit, vcenter=0, vmax=record_limit)}
    cmap = plt.get_cmap('RdBu_r')
    fig = plt.figure(figsize=(17.5, 9.2), facecolor='white')
    fig.text(.035, .949, 'One retained reconstruction history', fontsize=29, weight='bold')
    fig.text(.035, .897, 'D140  ·  block 78000  ·  life 0  ·  both supplied pattern roles  ·  illustrative, not inferential', fontsize=18, color=MUTED)
    left, right = .151, .973
    dx = (right - left) / 11
    width, height = dx * .91, .153
    centers = [left + (i + .5) * dx for i in range(11)]
    ys = [.645, .465, .255, .075]
    group_specs = [('Same F0', [0]), ('G1', [1, 2, 3]), ('G2', [4, 5, 6]),
                   ('G3', [7, 8, 9]), ('G4', [10])]
    for label, columns in group_specs:
        x = np.mean([centers[i] for i in columns])
        fig.text(x, .844, label, ha='center', fontsize=22, weight='bold')
    labels = ['p₀'] + ['V read', 'V write', 'p out'] * 3 + ['V read']
    for x, label in zip(centers, labels):
        fig.text(x, .807, label, ha='center', fontsize=15.5, color=MUTED)
    for row, (ri, ai) in enumerate((r, a) for r in range(2) for a in range(2)):
        arm = meta['selection']['arms'][ai]
        color = TEAL if arm == 'aligned' else AMBER
        y = ys[row]
        fig.text(.035, y + .114, 'Role ' + ('A' if ri == 0 else 'B'), fontsize=22, weight='bold')
        fig.text(.035, y + .067, arm.capitalize(), fontsize=19, color=color, weight='bold')
        fields = [('p', data['initial_records'][ri])]
        for gi in range(3):
            fields += [('V', data['read_end_bodies'][ri, ai, gi]),
                       ('V', data['writer_end_bodies'][ri, ai, gi]),
                       ('p', data['outgoing_records'][ri, ai, gi])]
        fields.append(('V', data['terminal_bodies'][ri, ai]))
        for col, (kind, field) in enumerate(fields):
            ax = fig.add_axes([centers[col] - width / 2, y, width, height])
            ax.imshow(field, cmap=cmap, norm=norms[kind], origin='upper', interpolation='nearest', aspect='equal')
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color('#849ba5' if kind == 'p' else '#c5cfd4')
                spine.set_linewidth(1.2 if kind == 'p' else .75)
    # Figure coordinates preserve actual phase order without joining fresh bodies into one trajectory.
    fig.add_artist(plt.Line2D([.035, .973], [.434, .434], transform=fig.transFigure, color='#d7e1e5', lw=1.2))
    for x in [left + dx, left + 4 * dx, left + 7 * dx, left + 10 * dx]:
        fig.add_artist(plt.Line2D([x, x], [.080, .789], transform=fig.transFigure, color='#e1e7e9', lw=.8, zorder=0))
    # Colorbars outside the field grid; zero and both exact shared limits are displayed.
    for kind, rect, label, lim in [
        ('V', [.153, .031, .25, .012], 'Body V', body_limit),
        ('p', [.635, .031, .25, .012], 'Record p', record_limit),
    ]:
        cax = fig.add_axes(rect)
        cb = fig.colorbar(ScalarMappable(norm=norms[kind], cmap=cmap), cax=cax, orientation='horizontal', ticks=[-lim, 0, lim])
        cb.ax.set_xticklabels([f'{-lim:.2f}', '0', f'{lim:.2f}'])
        cb.ax.tick_params(labelsize=13, pad=2, length=2)
        fig.text(rect[0] - .01, rect[1] + .006, label, ha='right', va='center', fontsize=15)
        cb.outline.set_linewidth(.5)
    DEST.mkdir(exist_ok=True)
    outputs = []
    for ext in ('png', 'svg'):
        path = DEST / f'data-reconstruction-history-v1.{ext}'
        fig.savefig(path, dpi=240, facecolor='white', metadata={'Creator': 'Matplotlib', **({'Date': None} if ext == 'svg' else {})})
        outputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    plt.close(fig)
    record = {'schema': 'forms_retained_history_assets_v1', 'figure_id': 'fig-reconstruction-history',
              'kind': 'illustrative retained pattern fields', 'png': 'data-reconstruction-history-v1.png',
              'input': str(DATA.relative_to(ROOT)), 'input_sha256': sha(DATA),
              'metadata': str(METADATA.relative_to(ROOT)), 'metadata_sha256': sha(METADATA),
              'renderer': str(Path(__file__).relative_to(ROOT)), 'renderer_sha256': sha(Path(__file__)),
              'outputs': outputs, 'body_scale': [-body_limit, body_limit], 'record_scale': [-record_limit, record_limit],
              'scales': 'One symmetric limit per quantity over every displayed field; no clipping or per-panel normalization',
              'spatial_interpolation': 'nearest; no smoothing', 'extra_spatial_alignment': False,
              'new_simulations': 0, 'new_statistical_tests': 0}
    (DEST / 'reconstruction-history-assets-v0.10.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Rendered retained fields as PNG/SVG; separate common scales for body and record.')


if __name__ == '__main__':
    main()
