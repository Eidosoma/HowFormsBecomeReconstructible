#!/usr/bin/env python3
"""Plot the retained P11 classifier traces; no simulation or new inference."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'paper_assets/data/retained-editable-lineage-v1.npz'
META = DATA.with_suffix('.json')
DEST = ROOT / 'paper_assets/figures'
INK, GRAY = '#123b49', '#53636d'
COLORS = ['#07848a', '#bf7925', '#8057a6']
STYLES = ['-', '--', ':']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13,
                     'svg.fonttype': 'none', 'svg.hashsalt': 'forms-p11-history-v1',
                     'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': '#84969e'})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    meta = json.loads(META.read_text())
    if sha(DATA) != meta['data_sha256']:
        raise ValueError('P11 portable data hash mismatch')
    with np.load(DATA, allow_pickle=False) as archive:
        data = {key: archive[key].copy() for key in archive.files}
    panels = ['founders', 'r01', 'r02', 'r03', 'rewrite', 'r04', 'r05', 'r06']
    titles = ['M writing\nFounder cells', 'Replacement 1', 'Replacement 2', 'Replacement 3',
              'E rewriting\nSame R3 cells', 'Replacement 4', 'Replacement 5', 'Replacement 6']
    fig = plt.figure(figsize=(17.8, 9.5), facecolor='white')
    fig.text(.045, .956, 'P11: a retained editable lineage', fontsize=28, weight='bold')
    fig.text(.045, .914, 'Written-founder / open-route history  ·  finer numerical resolution  ·  all three recipients shown',
             fontsize=16, color=GRAY)
    grid = fig.add_gridspec(2, 4, left=.079, right=.980, bottom=.222, top=.812,
                           width_ratios=[.4, 1, 1, 1], hspace=.60, wspace=.12)
    displayed = []
    for n, (panel, title) in enumerate(zip(panels, titles)):
        ax = fig.add_subplot(grid[n // 4, n % 4])
        phases = [p for p in meta['phases'] if p['panel'] == panel]
        start, end = phases[0]['logical_interval'][0], phases[-1]['logical_interval'][1]
        writing = panel in ('founders', 'rewrite')
        removal = start + (20000 if writing else 80000)
        for phase in phases:
            a, b = np.array(phase['logical_interval']) / 1000
            if phase['isolated']:
                ax.axvspan(a, b, facecolor='#e2eeed', zorder=0)
                ax.axvspan(b - 2.5, b, facecolor='#bdd5d2', zorder=0)
                label = 'H' + phase['name'][-1]
            elif writing:
                ax.axvspan(a, b, facecolor='#fff0d8', zorder=0)
                label = 'cue'
            else:
                active = phase['scheduled_pupils']
                label = str(active[0] + 1) if active else 'off'
            ax.text((a + b) / 2, 1.018, label, transform=ax.get_xaxis_transform(),
                    ha='center', va='bottom', fontsize=9, color=GRAY)
            ax.axvline(a, color='#d9e1e4', lw=.7, zorder=0)
            key, indices = phase['key'], phase['target_indices']
            times = (data[key + '_times'] + phase['logical_interval'][0]) / 1000
            for cell, index in enumerate(indices):
                values = data[key + '_delta'][:, index]
                displayed.extend([float(values.min()), float(values.max())])
                ax.plot(times, values, color=COLORS[cell], linestyle=STYLES[cell], lw=1.7,
                        solid_capstyle='round', zorder=4)
        # The threshold band is shared across panels and is not a model intervention.
        ax.axhspan(-2, 2, facecolor='#e9e5f0', zorder=1)
        for threshold in (-2, 2):
            ax.axhline(threshold, color='#7b687c', ls=(0, (3, 3)), lw=.85, zorder=2)
        ax.axvline(removal / 1000, color=INK, lw=1.2, ls=(0, (2, 2)), zorder=5)
        ax.plot(removal / 1000, 89, marker='v', ms=7, color=INK, clip_on=False)
        ax.set(xlim=(start / 1000, end / 1000), ylim=(-70, 90))
        ax.set_yticks([-60, -30, 0, 30, 60, 90])
        ticks = [start, start + 20000, end] if writing else [start, start + 40000, start + 80000, end]
        ax.set_xticks(np.array(ticks) / 1000)
        ax.tick_params(axis='both', labelsize=12)
        ax.spines[['top', 'right']].set_visible(False)
        if not writing:
            title += f'\nNew cells: R{int(panel[1:])} / 00–02'
        ax.set_title(title, fontsize=15, weight='bold', pad=30)
        if n % 4 == 0:
            ax.set_ylabel('miR200 total − Zeb mRNA total', fontsize=13, labelpad=10)
            ax.text(.03, .84, 'E > +2', transform=ax.transAxes, fontsize=10, color=GRAY)
            ax.text(.03, .10, 'M < −2', transform=ax.transAxes, fontsize=10, color=GRAY)
        else:
            ax.tick_params(labelleft=False)
    if min(displayed) < -70 or max(displayed) > 90:
        raise ValueError('Fixed common display range would clip saved values')
    fig.text(.52, .150, 'Logical lineage time (×10³ model units); separate panels preserve cell identities',
             ha='center', fontsize=15)
    cell_handles = [Line2D([0], [0], color=c, ls=s, lw=2, label=f'Cell {i:02d} within each group')
                    for i, (c, s) in enumerate(zip(COLORS, STYLES))]
    fig.legend(handles=cell_handles, loc='lower center', bbox_to_anchor=(.52, .092), ncol=3,
               frameon=False, fontsize=13)
    events = [Patch(facecolor='#fff0d8', label='Temporary cue'),
              Patch(facecolor='#e2eeed', label='H1 / H2: isolated holds'),
              Patch(facecolor='#bdd5d2', label='Last quarter scored'),
              Line2D([0], [0], color=INK, ls=':', marker='v', label='Cue / teacher removed')]
    fig.legend(handles=events, loc='lower center', bbox_to_anchor=(.52, .045), ncol=4,
               frameon=False, fontsize=12)
    fig.text(.52, .021, 'Contacts 1 → 2 → 3, then off  ·  X between −2 and +2  ·  saved samples every 100 units  ·  descriptive, not independent replicates',
             ha='center', fontsize=11, color=GRAY)
    outputs = []
    for suffix in ('png', 'svg'):
        path = DEST / f'data-editable-lineage-history-v1.{suffix}'
        fig.savefig(path, dpi=240, facecolor='white', metadata={'Creator': 'Matplotlib', **({'Date': None} if suffix == 'svg' else {})})
        outputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    plt.close(fig)
    record = {'schema': 'forms_retained_history_assets_v1', 'figure_id': 'fig-editable-lineage',
              'kind': 'illustrative retained classifier trajectories', 'png': 'data-editable-lineage-history-v1.png',
              'input': str(DATA.relative_to(ROOT)), 'input_sha256': sha(DATA),
              'metadata': str(META.relative_to(ROOT)), 'metadata_sha256': sha(META),
              'renderer': str(Path(__file__).relative_to(ROOT)), 'renderer_sha256': sha(Path(__file__)),
              'outputs': outputs, 'display_range': [-70, 90], 'clipping': False,
              'display': 'All saved target-cell samples, connected within cells only; no smoothing, decimation, or cross-cell interpolation',
              'new_simulations': 0, 'new_statistical_tests': 0}
    (DEST / 'editable-lineage-history-assets-v0.10.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Rendered P11 saved trajectories in eight panels; no model executed.')


if __name__ == '__main__':
    main()
