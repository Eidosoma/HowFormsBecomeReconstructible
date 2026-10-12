#!/usr/bin/env python3
"""Render a scientific contrast plot and P11 protocol schematic from saved inputs."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'paper_assets/data/renewal-update-v1.json'
DEST = ROOT / 'paper_assets/figures'
INK, TEAL, AMBER, MUTED = '#123b49', '#087f8c', '#bf740e', '#54636b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': '#b9c6cb',
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': INK})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(fig, stem, identifier, kind):
    outputs = []
    for extension in ('png', 'svg'):
        path = DEST / f'{stem}.{extension}'
        fig.savefig(path, dpi=240, facecolor='white', metadata={'Creator': 'Matplotlib'})
        outputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    plt.close(fig)
    return {'id': identifier, 'kind': kind, 'png': stem + '.png', 'outputs': outputs}


def plot(data):
    values = {(r['campaign'], r['contrast'], r['role']): r for r in data['estimates']}
    fig = plt.figure(figsize=(12.8, 7.2))
    fig.text(.045, .94, 'Alignment improves renewal; some information is still lost', size=19, weight='bold')
    fig.text(.045, .888, 'Three reconstruction boundaries | one fixed guide | separate founder cohorts', size=12, color=MUTED)
    left = fig.add_axes([.18, .245, .27, .54])
    right = fig.add_axes([.66, .245, .29, .54])
    left.set_title('Primary: aligned minus translated', loc='left', fontsize=12, pad=22, weight='bold')
    right.set_title('Secondary: aligned minus protected copy', loc='left', fontsize=12, pad=22, weight='bold')
    for ax in (left, right):
        ax.axvline(0, color='#7e8c92', lw=1, ls='--', zorder=0)
        ax.grid(axis='x', color='#e7edef', zorder=0)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y', length=0, pad=12)
        ax.set_xlabel('Preference difference (points)', labelpad=10)
    labels = []
    for y, cohort, color in [(1, 'D135', AMBER), (0, 'D140', TEAL)]:
        e = values[cohort, 'alignment', 'Pooled']
        left.errorbar(e['mean'], y, xerr=[[e['mean'] - e['low']], [e['high'] - e['mean']]],
                      fmt='o', color=color, capsize=5, ms=9, lw=2)
        left.text(e['mean'], y-.20, f"+{e['mean']:.2f} [{e['low']:.2f}, {e['high']:.2f}]",
                  ha='center', fontsize=10, color=color)
    left.set_yticks([1, 0], ['D135\nKnown founders', 'D140\nNew founders'])
    left.set_xlim(-.5, 8)
    left.set_ylim(-.65, 1.65)
    for j, (cohort, role) in enumerate((c, r) for c in ('D135', 'D140') for r in ('Pooled', 'A', 'B')):
        y = 5-j
        e = values[cohort, 'copy', role]
        color = AMBER if cohort == 'D135' else TEAL
        right.errorbar(e['mean'], y, xerr=[[e['mean'] - e['low']], [e['high'] - e['mean']]],
                       fmt='D' if role == 'Pooled' else 'o', color=color, capsize=4, ms=6, lw=1.8)
        labels.append(f'{cohort}  {role}')
    right.set_yticks(range(5, -1, -1), labels)
    right.set_ylim(-.7, 5.7)
    right.set_xlim(-10.3, 3.8)
    right.axhline(2.5, color='#dce5e8', lw=1)
    fig.text(.045, .12, 'Each cohort: 8 blocks, 4 paired lives per block, 2 supplied pattern roles.', size=11)
    fig.text(.045, .075, 'Bars: reported pointwise 95% block-bootstrap intervals. No cohort pooling or new inference.', size=10, color=MUTED)
    fig.text(.045, .035, 'A positive primary does not imply lossless renewal. The D140 pooled copy contrast is unresolved.', size=10, color=MUTED)
    return save(fig, 'data-serial-alignment-v1', 'fig-serial-alignment', 'measured')


def diagram(data):
    assert data['P11']['all_five_gates_pass']
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(.035, .932, 'An editable lineage', size=30, weight='bold')
    ax.text(.035, .872, 'A state can pass to new carriers, be changed, and pass onward again.', size=17, color=MUTED)
    titles = ['1  Write M', '2  Replace carriers', '3  Rewrite to E', '4  Replace again']
    subtitles = ['Temporary M cues', 'Three M handovers', 'Temporary E cues', 'Three E handovers']
    for i in range(4):
        x = .035 + i*.242
        color = AMBER if i < 2 else TEAL
        ax.add_patch(FancyBboxPatch((x, .34), .213, .45, boxstyle='round,pad=0.009',
                                   facecolor='#fbfcfd', edgecolor='#ccd9dd', linewidth=1.4))
        ax.text(x+.012, .738, titles[i], fontsize=18, weight='bold', color=color)
        ax.text(x+.012, .689, subtitles[i], fontsize=13, color=MUTED)
        if i in (0, 2):
            before, after = ('E', 'M') if i == 0 else ('M', 'E')
            ax.text(x+.106, .585, f'{before}  →  {after}', fontsize=28, ha='center', color=color, weight='bold')
            for j in range(3):
                ax.add_patch(Circle((x+.064+j*.042, .503), .013, color=color))
            detail = 'Three fresh E targets' if i == 0 else 'The actual current carriers'
            ax.text(x+.106, .439, detail, fontsize=12, ha='center')
            ax.text(x+.106, .382, 'Remove cues; test retention', fontsize=11, ha='center', color=MUTED)
        else:
            state = 'M' if i == 1 else 'E'
            for j in range(3):
                cx = x+.040+j*.067
                ax.text(cx, .59, f'{state}{j+1}', fontsize=16, ha='center', color=color, weight='bold')
                for dx, dy in [(-.011, 0), (.011, 0), (0, -.031)]:
                    ax.add_patch(Circle((cx+dx, .534+dy), .0095, color=color))
                if j < 2:
                    ax.add_patch(FancyArrowPatch((cx+.020, .523), (cx+.046, .523),
                                                arrowstyle='-|>', mutation_scale=12, color=MUTED))
            ax.text(x+.106, .438, 'Three cells in every group', fontsize=12, ha='center')
            ax.text(x+.106, .382, 'Remove every old teacher', fontsize=11, ha='center', color=MUTED)
        if i < 3:
            ax.add_patch(FancyArrowPatch((x+.222, .557), (x+.233, .557),
                                        arrowstyle='-|>', mutation_scale=18, color=INK, lw=1.8))
    ax.text(.04, .262, 'Reported outcome', size=16, weight='bold', color=TEAL)
    ax.text(.04, .212, 'Both written and ordinary-M founders complete the chain at both numerical resolutions.', size=14)
    ax.text(.04, .143, 'Controls', size=14, weight='bold')
    ax.text(.13, .143, 'Blocked communication prevents transfer; sham and no-cue rewriting retain M.', size=13, color=MUTED)
    ax.text(.04, .078, 'P11 protocol schematic. Cells, cues, contacts and schedules are supplied; no cell division or autonomous goal selection.', size=11, color=MUTED)
    ax.text(.04, .036, 'New stock and all stages use bounded integration clocks. Shared deterministic preparations are not population replicates.', size=11, color=MUTED)
    return save(fig, 'diagram-editable-lineage-v1', 'fig-editable-lineage', 'schematic')


def main():
    data = json.loads(DATA.read_text())
    figures = [plot(data), diagram(data)]
    record = {'schema': 'forms_update_assets_v1', 'input': str(DATA.relative_to(ROOT)),
              'input_sha256': sha(DATA), 'figures': figures, 'renderer': 'Matplotlib',
              'new_simulations': 0, 'new_statistical_tests': 0}
    (DEST / 'renewal-update-assets.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Rendered alignment plot and editable-lineage schematic as PNG and SVG.')


if __name__ == '__main__':
    main()
