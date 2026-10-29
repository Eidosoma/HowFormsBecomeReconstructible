#!/usr/bin/env python3
"""Figure 5: implemented information boundaries and unchanged D135/D140 estimates.

Render only saved report-table data and a code-checked protocol schematic.
No scientific module is imported, and no dynamics or statistics are rerun.
The original v1 figure, renderer and data remain unchanged.
"""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'paper_assets/data/renewal-update-v1.json'
DEST = ROOT / 'paper_assets/figures'
INK, TEAL, AMBER, MUTED = '#123b49', '#087f8c', '#bf740e', '#54636b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(DATA.read_text())
    values = {(r['campaign'], r['contrast'], r['role']): r for r in data['estimates']}
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 16, 'svg.fonttype': 'none',
        'svg.hashsalt': 'forms-writer-alignment-v0.10',
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#b9c6cb', 'text.color': INK,
        'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': INK,
    })
    fig = plt.figure(figsize=(12.8, 12.8))
    panel = fig.add_axes([0, 0, 1, 1])
    panel.set(xlim=(0, 1), ylim=(0, 1)); panel.axis('off')
    panel.text(.03, .968, 'A  How the next record is reconstructed', fontsize=23, weight='bold')
    panel.text(.03, .941,
               'Shared guide: 2 templates / 16 development records / 4096 bytes / never inherited',
               fontsize=16.3, color=MUTED)

    def box(x, y, title, body, color=INK, fill='#f7fafb'):
        panel.add_patch(FancyBboxPatch((x, y), .29, .183,
                        boxstyle='round,pad=0.006,rounding_size=0.009',
                        facecolor=fill, edgecolor='#c7d6dc', linewidth=1.2))
        panel.text(x+.014, y+.151, title, fontsize=18.3, weight='bold', color=color)
        panel.text(x+.014, y+.123, body, fontsize=16.1, va='top', linespacing=1.33)

    def arrow(start, end):
        panel.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=19,
                        linewidth=1.5, color=MUTED, shrinkA=0, shrinkB=0))

    box(.03, .711, '1  Reposition packet',
        '2048 bytes: a 16 x 16 field.\nScore 2 x 256 correlations.\nInverse-shift the field itself.\nKeep every incoming value.\nNo template substitution.', TEAL)
    box(.355, .711, '2  Read into fresh body',
        '300 updates; fresh V.\nInitialize R and moving\naverage to V; then develop.\nTheta writing is off;\nreference feedback is off.')
    box(.68, .711, '3  Remove packet input',
        'Retain V, moving average, R.\nStart new writer theta at zero.\nIncoming packet and guide\nare unavailable to writing.\nTheir body effects remain.', AMBER, '#fffaf0')
    box(.68, .475, '4  Write with feedback',
        '1000 updates; write from R.\nAligned: apply ' + r'$\theta_t$' + '.\nTranslated: apply ' + r'$T_{\delta_g}\theta_t$' + '.\n1 of 255 nonzero shifts;\nfixed for all 1000 updates.', AMBER, '#fffaf0')
    box(.355, .475, '5  Derive new packet',
        r'$p_{g+1}=\Pi_{0.3}[\tanh(R_{\mathrm{final}})]$' + '\n\n2048 bytes from final R.\nMean-center; set SD to 0.3.\nDo not transmit writer theta.', TEAL)
    box(.03, .475, '6  Reset the body',
        'Discard V, moving average,\nR and writer theta.\nOnly the new packet passes.\nThree rewrites (G1-G3);\nthen a fresh G4 read.', TEAL)
    arrow((.327, .801), (.347, .801)); arrow((.652, .801), (.672, .801))
    arrow((.825, .702), (.825, .667))
    arrow((.672, .565), (.652, .565)); arrow((.347, .565), (.327, .565))

    panel.add_patch(FancyBboxPatch((.03, .388), .94, .066,
                    boxstyle='round,pad=0.004,rounding_size=0.007',
                    facecolor='#edf5f6', edgecolor='none'))
    panel.text(.043, .430, 'Matched: F0 packet, guide, dynamics, phase lengths and per-phase random streams.',
               fontsize=15.5, weight='bold')
    panel.text(.043, .404, 'Each arm transmits its own new packet; later bodies and records can diverge.',
               fontsize=15.7)

    fig.text(.03, .355, 'B  Primary: alignment', fontsize=19, weight='bold')
    fig.text(.03, .331, 'Aligned minus translated', fontsize=15.8, color=MUTED)
    fig.text(.555, .355, 'C  Secondary: copying', fontsize=19, weight='bold')
    fig.text(.555, .331, 'Aligned minus protected copy', fontsize=15.8, color=MUTED)
    left = fig.add_axes([.18, .104, .29, .203])
    right = fig.add_axes([.708, .104, .252, .203])
    for ax in (left, right):
        ax.axvline(0, color='#7e8c92', lw=1, ls='--', zorder=0)
        ax.grid(axis='x', color='#e7edef', zorder=0)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y', length=0, pad=9, labelsize=15.5)
        ax.tick_params(axis='x', labelsize=14)
        ax.set_xlabel('Preference difference (points)', labelpad=9, fontsize=15)
    for y, cohort, color in [(1, 'D135', AMBER), (0, 'D140', TEAL)]:
        e = values[cohort, 'alignment', 'Pooled']
        left.errorbar(e['mean'], y,
                      xerr=[[e['mean']-e['low']], [e['high']-e['mean']]],
                      fmt='o', color=color, capsize=5, ms=8, lw=2)
        left.text(e['mean'], y-.24, f"+{e['mean']:.2f} [{e['low']:.2f}, {e['high']:.2f}]",
                  ha='center', fontsize=14, color=color)
    left.set_yticks([1, 0], ['D135\nReused founders', 'D140\nNew founders'])
    left.set(xlim=(-.5, 8), ylim=(-.65, 1.65))
    labels = []
    for j, (cohort, role) in enumerate((c, r) for c in ('D135', 'D140') for r in ('Pooled', 'A', 'B')):
        e = values[cohort, 'copy', role]
        right.errorbar(e['mean'], 5-j,
                       xerr=[[e['mean']-e['low']], [e['high']-e['mean']]],
                       fmt='D' if role == 'Pooled' else 'o',
                       color=AMBER if cohort == 'D135' else TEAL, capsize=4, ms=6, lw=1.8)
        labels.append(f'{cohort}  {role}')
    right.set_yticks(range(5, -1, -1), labels)
    right.set(xlim=(-10.3, 3.8), ylim=(-.7, 5.7))
    right.axhline(2.5, color='#dce5e8', lw=1)
    fig.text(.03, .031, 'Each cohort: 8 blocks, 4 paired lives per block, 2 supplied pattern roles.', fontsize=15)
    fig.text(.03, .010, 'Reported pointwise 95% block-bootstrap intervals. Separate cohorts; no new inference.',
             fontsize=14.5, color=MUTED)
    outputs = []
    for ext in ('png', 'svg'):
        path = DEST / f'data-serial-alignment-v2.{ext}'
        metadata = {'Creator': 'Matplotlib'}
        if ext == 'svg': metadata['Date'] = '2026-09-17'
        fig.savefig(path, dpi=240, facecolor='white', metadata=metadata)
        outputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    plt.close(fig)
    record = {
        'schema': 'forms_writer_alignment_assets_v1', 'input': str(DATA.relative_to(ROOT)),
        'input_sha256': sha(DATA), 'renderer': 'Matplotlib',
        'source_inspection': 'reviews/V0.10_MECHANISM_SOURCES.json',
        'source_inspection_sha256': sha(ROOT / 'reviews/V0.10_MECHANISM_SOURCES.json'),
        'figures': [{'id': 'fig-serial-alignment', 'kind': 'measured_with_schematic',
                     'png': 'data-serial-alignment-v2.png', 'outputs': outputs,
                     'panels': {'A': 'implemented protocol schematic',
                                'B': 'unchanged primary report-table estimates',
                                'C': 'unchanged secondary report-table estimates'}}],
        'renderer_path': str(Path(__file__).relative_to(ROOT)),
        'renderer_sha256': sha(Path(__file__)),
        'new_simulations': 0, 'new_statistical_tests': 0,
    }
    (DEST / 'writer-alignment-assets-v0.10.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Rendered Figure 5 mechanism and unchanged measured contrasts (PNG/SVG).')


if __name__ == '__main__':
    main()
