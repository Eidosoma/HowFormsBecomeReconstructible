"""Report every current gate and, only when generated, the frozen future test."""
from pathlib import Path
import json
import numpy as np
from h006 import engine as e
from h006.inference import mean_pairs, future_decision


def pct(stat):
    if stat['mean'] is None:
        return 'unavailable'
    value = f"{100*stat['mean']:.2f}"
    if stat['low'] is not None:
        value += f" [{100*stat['low']:.2f}, {100*stat['high']:.2f}]"
    return value


def analyze(out):
    out = Path(out)
    config = json.loads((out/'config.json').read_text())
    selection = json.loads((out/'SELECTION.json').read_text())
    audited = json.loads((out/'audit.json').read_text())['passed']
    has_futures = bool(list(out.glob('future_*.npz')))
    enrollment = json.loads((out/'ENROLLMENT.json').read_text()) if (out/'ENROLLMENT.json').exists() else None
    summary = dict(experiment='H006', classification=config['classification'], selection=selection,
                   enrollment=enrollment, audit_passed=audited, futures_generated=has_futures,
                   variants=e.VARIANTS, arms=e.ARMS, checkpoints=e.CHECKPOINTS,
                   selected_dose=selection['selected_dose'], decision=dict(qualified=False, gates={}))
    lines = ['# H006: record organization at matched present function', '',
             config['classification']+'.', '',
             'Dose selection uses eight exposed development networks; sixteen separate development networks test the selected dose. '
             'All H006 probes and future tapes are new. Present equivalence uses one-point bounds.', '',
             '| Unique edge flips | Matched packets | Nonempty selection blocks | All current selection gates pass |',
             '|---|---:|---:|---|']
    for row in selection['decisions']:
        lines.append(f"| {row['dose']} | {row['matches']} | {row['nonempty_blocks']} | {row['passed']} |")
    lines += ['', f"Selected dose: **{selection['selected_dose']}**."]
    if selection['selected_dose'] is None:
        summary['verdict'] = 'NO_ADMISSIBLE_DOSE'
        lines += ['', '**NO_ADMISSIBLE_DOSE.** No dose passed every frozen present-function gate. '
                  'No assay probes or study futures were generated. No fallback dose or relaxed observer was used.']
    elif enrollment is not None:
        current = enrollment['decision']
        lines += ['', f"Assay match: {current['matches']}/256 packets in {current['nonempty_blocks']}/16 networks."
                  if config['mode'] == 'development' else f"Engineering assay matches: {current['matches']}/16.",
                  '', '| Variant | Independent current success, % [95% interval] |', '|---|---:|']
        for v in e.VARIANTS:
            lines.append(f"| {v} | {pct(current['current_success'][v])} |")
        lines += ['', 'Failed current assay gates: '+(', '.join(k for k, v in current['gates'].items() if not v) or 'none')+'.']
        if not has_futures:
            summary['verdict'] = 'PRESENT_GATE_FAILED'
            lines += ['', '**PRESENT_GATE_FAILED.** The selected dose failed independent assay validation. '
                      'No study futures were generated and no second dose was tried.']
    if has_futures:
        rows, futures, persistence, all_feasible, pair_future, eligibility, feasibility = [], [], [], [], [], [], []
        for seed in config['assay_seeds']:
            with np.load(out/f'assay_{seed}.npz') as p:
                eligible = p['eligible'][0]
                feasible = p['feasible']
            successes, uninterrupted = [], []
            for fork in range(e.FORKS):
                with np.load(out/f'future_{seed}_{fork:02d}.npz') as raw:
                    successes.append(raw['success'])
                    uninterrupted.append(raw['uninterrupted'])
            successes, uninterrupted = np.array(successes), np.array(uninterrupted)
            row = dict(seed=seed, matched=int(eligible.sum()), feasible=int(feasible.sum()))
            if eligible.any():
                f = mean_pairs(successes, eligible).mean(axis=0)
                u = mean_pairs(uninterrupted, eligible).mean(axis=0)
                futures.append(f)
                persistence.append(u)
                row.update(matched_success=f.tolist(), matched_uninterrupted=u.tolist())
            if feasible.any():
                a = mean_pairs(successes, feasible).mean(axis=0)
                all_feasible.append(a)
                row['all_feasible_success'] = a.tolist()
            rows.append(row)
            pair_future.append(successes[:, -1].mean(axis=0))
            eligibility.append(eligible)
            feasibility.append(feasible)
        futures = np.array(futures).reshape(-1, 4, 3, len(e.ARMS))
        persistence = np.array(persistence).reshape(-1, 3, len(e.ARMS))
        decision, estimate = future_decision(futures, enrollment['decision']['passed'], config, audited)
        summary.update(decision=decision, block_rows=rows,
                       matched_mean_success=futures.mean(axis=0).tolist() if len(futures) else None,
                       all_feasible_mean_success=np.mean(all_feasible, axis=0).tolist() if all_feasible else None,
                       uninterrupted={v: {a: estimate(persistence[:, i, j]) for j, a in enumerate(e.ARMS)}
                                      for i, v in enumerate(e.VARIANTS)})
        summary['verdict'] = 'DEVELOPMENT_CANDIDATE' if decision['qualified'] else 'DOES_NOT_QUALIFY'
        np.savez_compressed(out/'pair_summary.npz', seeds=config['assay_seeds'], eligible=np.array(eligibility),
                            feasible=np.array(feasibility), terminal_future_probability=np.array(pair_future),
                            variants=np.array(e.VARIANTS), arms=np.array(e.ARMS))
        lines += ['', '| Variant | Terminal renewal, % [95% interval] | Uninterrupted, % | Protected copy, % |',
                  '|---|---:|---:|---:|']
        for v in e.VARIANTS:
            lines.append(f"| {v} | {pct(decision['terminal'][v]['renewal'])} | {pct(summary['uninterrupted'][v]['renewal'])} | {pct(decision['terminal'][v]['protected_copy'])} |")
        lines += ['', '| Primary contrast | Difference, percentage points [95% interval] | Adjusted lower, points |',
                  '|---|---:|---:|']
        for name, stat in decision['primary_contrasts'].items():
            lower = 'unavailable' if stat['directional_lower'] is None else f"{100*stat['directional_lower']:.2f}"
            lines.append(f'| {name} | {pct(stat)} | {lower} |')
        lines += ['', 'Failed future decision gates: '+(', '.join(k for k, v in decision['gates'].items() if not v) or 'none')+'.',
                  '', '| Record arm | Unchanged, % | Output flips, % | Hidden flips, % |', '|---|---:|---:|---:|']
        for arm in e.ARMS:
            lines.append('| '+arm+' | '+' | '.join(pct(decision['terminal'][v][arm]) for v in e.VARIANTS)+' |')
    if config['mode'] == 'benchmark':
        summary['verdict'] = 'ENGINEERING_ONLY'
        summary['decision']['qualified'] = None
    lines += ['', '**Decision: '+summary['verdict']+'.**', '',
              'Each intervention preserves the record histogram, norm and nonzero count. The locations have matched cue degrees '
              'and equal gained perturbation strength. Hidden connections are an active comparator. Base-plus-record norm '
              'is retained separately because its cross terms may differ.',
              'Current validation concerns a finite observer, not exact latent current equality. Present-based selection limits '
              'the estimand to the declared matched packets. All decisions and current intervals, including failed doses, '
              'are retained in summary.json. No smaller effect, different dose, all-candidate subset, intermediate checkpoint '
              'or uninterrupted outcome can replace a failed primary.',
              'The records are intervened on at the initial boundary; all later renewal writes use only current body activity. '
              'This study does not establish discovered competence or superiority to copying. No private material is imported; '
              'H004/H005 and the forms manuscript are unchanged.',
              f'Retained audit passed: {audited}.', '']
    e.e.save(out/'summary.json', summary)
    (out/'REPORT.md').write_text('\n'.join(lines))
    plot(out, summary)
    return summary


def plot(out, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    rows = summary['selection']['decisions']
    axes[0].bar([str(r['dose']) for r in rows], [r['matches'] for r in rows],
                color=['#117a59' if r['passed'] else '#929292' for r in rows])
    axes[0].set(title='Present-only dose selection', xlabel='Unique flipped edges', ylabel='Matched packets')
    axes[0].axhline(64, color='#8c4242', linestyle=':', label='Minimum coverage')
    axes[0].legend(fontsize=7)
    enrollment = summary['enrollment']
    if enrollment:
        rows = enrollment['decision']['blocks']
        axes[1].bar(range(len(rows)), [r['matched'] for r in rows], color='#477b93')
        axes[1].set(title='Independent assay match', xlabel='Base network', ylabel='Matched packets (of 16)', ylim=(0, 17))
    else:
        axes[1].text(.5, .5, 'No admissible dose\nAssay not opened', ha='center', va='center', transform=axes[1].transAxes)
        axes[1].set_axis_off()
    if summary.get('matched_mean_success') is not None:
        values = np.array(summary['matched_mean_success'])
        for i, (v, color) in enumerate(zip(e.VARIANTS, ['#777777', '#b3483e', '#117a59'])):
            current = enrollment['decision']['current_success'][v]['mean']
            axes[2].plot([0, *e.CHECKPOINTS], 100*np.r_[current, values[:, i, 0]], '-o', label=v, color=color)
        axes[2].legend(fontsize=7)
        axes[2].set(title='Common future, matched packets', xlabel='Additional replacements', ylabel='Success (%)', ylim=(-3, 103))
    else:
        axes[2].text(.5, .5, 'No study futures generated', ha='center', va='center', transform=axes[2].transAxes)
        axes[2].set_axis_off()
    fig.suptitle(f"H006 · {summary['verdict']} · selected dose {summary['selected_dose']}", fontsize=11)
    for ax in axes:
        if ax.axison:
            ax.grid(axis='y', alpha=.15)
    fig.savefig(Path(out)/'overview.png', dpi=160)
    fig.savefig(Path(out)/'overview.pdf')
    plt.close(fig)
