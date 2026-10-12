"""Report every dose under the sealed one-replacement feasibility rules."""
from pathlib import Path
import json
import numpy as np
from h007 import engine as e
from h007.io import save
from h007.inference import mean_pairs, transmission_decision

METRICS = ('joint_functional_retention', 'own_retained', 'distinct',
           'body_success', 'reader_success')


def pct(stat):
    if stat['mean'] is None:
        return 'unavailable'
    value = f"{100*stat['mean']:.2f}"
    if stat['low'] is not None:
        value += f" [{100*stat['low']:.2f}, {100*stat['high']:.2f}]"
    return value


def point(value):
    return 'unavailable' if value is None else f'{100*value:.2f}'


def analyze(out):
    out = Path(out)
    config = json.loads((out/'config.json').read_text())
    enrollment = json.loads((out/'ENROLLMENT.json').read_text())
    audited = json.loads((out/'audit.json').read_text())['passed']
    has_replacements = enrollment['allow_replacements']
    per_dose = [[] for _ in e.DOSES]
    pair_metrics = {name: [] for name in METRICS}
    eligibility, feasibility = [], []
    if has_replacements:
        for seed in config['seeds']:
            with np.load(out/f'present_{seed}.npz') as present:
                eligible, feasible = present['eligible'], present['feasible']
            trials = {name: [] for name in METRICS}
            for trial in range(e.TRIALS):
                with np.load(out/f'replacement_{seed}_{trial:02d}.npz') as raw:
                    for name in METRICS:
                        trials[name].append(raw[name])
            averages = {name: np.mean(values, axis=0) for name, values in trials.items()}
            for name, values in averages.items():
                pair_metrics[name].append(values)
            eligibility.append(eligible)
            feasibility.append(feasible)
            for d, dose in enumerate(e.DOSES):
                row = dict(seed=seed, dose=dose, matched=int(eligible[d].sum()), feasible=int(feasible.sum()))
                if row['matched']:
                    row['matched_metrics'] = {name: mean_pairs(values[d], eligible[d]).tolist()
                                              for name, values in averages.items()}
                if row['feasible']:
                    row['all_feasible_metrics'] = {name: mean_pairs(values[d], feasible).tolist()
                                                   for name, values in averages.items()}
                per_dose[d].append(row)
        np.savez_compressed(out/'pair_summary.npz', seeds=config['seeds'], doses=e.DOSES,
                            eligible=np.array(eligibility), feasible=np.array(feasibility),
                            variants=np.array(e.VARIANTS), arms=np.array(e.ARMS),
                            **{name: np.array(values) for name, values in pair_metrics.items()})

    results = []
    for d, current in enumerate(enrollment['decisions']):
        result = dict(dose=e.DOSES[d], current=current, transmission=None, blocks=per_dose[d])
        if has_replacements:
            matched = [row['matched_metrics'] for row in per_dose[d] if row['matched']]
            decision, estimate = transmission_decision(
                [row['joint_functional_retention'] for row in matched], current['passed'], config, audited)
            estimates = {}
            for name in METRICS:
                if name in ('joint_functional_retention', 'distinct'):
                    estimates[name] = {arm: estimate(np.array([row[name][a] for row in matched]))
                                       for a, arm in enumerate(e.ARMS)}
                else:
                    estimates[name] = {variant: {arm: estimate(np.array([row[name][v][a] for row in matched]))
                                                 for a, arm in enumerate(e.ARMS)}
                                       for v, variant in enumerate(e.VARIANTS)}
            result.update(transmission=decision, estimates=estimates)
        results.append(result)
    passing = [r['dose'] for r in results if r['transmission'] is not None and r['transmission']['passed']]
    nominated = max(passing) if passing and config['mode'] == 'development' else None
    verdict = ('ENGINEERING_ONLY' if config['mode'] == 'benchmark' else
               'NO_ADMISSIBLE_CURRENT_MATCH' if not has_replacements else
               'FEASIBILITY_CANDIDATE' if nominated is not None else 'DOES_NOT_QUALIFY')
    summary = dict(experiment='H007', classification=config['classification'], verdict=verdict,
                   nominated_dose=nominated, passing_doses=passing if config['mode'] == 'development' else [],
                   replacements_generated=has_replacements, audit_passed=audited,
                   variants=e.VARIANTS, arms=e.ARMS, trials_per_network=e.TRIALS,
                   additional_replacements=1, results=results)
    save(out/'summary.json', summary)
    report(out, summary, config)
    plot(out, summary)
    return summary


def report(out, summary, config):
    lines = ['# H007: coherent hidden-pattern transmission', '', config['classification']+'.', '',
             '**Decision: '+summary['verdict']+'.** Nominated hidden-pair dose: **'+str(summary['nominated_dose'])+'**.', '',
             'This is a one-replacement feasibility screen. Every dose uses the original body-only writer, '
             'fixed gain-4 reader and paired damage/read tapes. Current enrollment was sealed before any '
             'replacement observations. All four doses and their failures are retained.', '',
             '| Hidden pairs swapped | Matched packets | Nonempty networks | Unchanged current, % [95% interval] | Swapped current, % [95% interval] | Current gates |',
             '|---|---:|---:|---:|---:|---|']
    for result in summary['results']:
        c = result['current']
        lines.append(f"| {result['dose']} | {c['matches']} | {c['nonempty_blocks']} | "
                     f"{pct(c['current_success']['unchanged'])} | {pct(c['current_success']['hidden_swap'])} | {c['passed']} |")
    lines += ['', 'Current success and all four output differences must have 97.5% bootstrap intervals inside '
              '±1 percentage point, with at least 64 matches across 16 networks and ≥95% success in both variants. '
              'The wider equivalence intervals account for four screened doses; the table shows marginal 95% intervals.']
    if not summary['replacements_generated']:
        lines += ['', 'No dose passed all current gates. No study replacement trials were generated.']
    else:
        lines += ['', '| Hidden pairs | Joint functional exact retention, % [95% interval] | Adjusted lower, % | Renewal minus read-off, points | Renewal minus write-off, points | Full screen passes |',
                  '|---|---:|---:|---:|---:|---|']
        for result in summary['results']:
            t = result['transmission']
            stats = t['statistics']
            joint = stats['joint_functional_retention']
            lines.append(f"| {result['dose']} | {pct(joint)} | {point(joint['directional_lower'])} | "
                         f"{pct(stats['renewal_minus_read_off'])} | {pct(stats['renewal_minus_write_off'])} | {t['passed']} |")
        lines += ['', 'Joint retention requires both intended, distinct packets to be reproduced exactly and both rebuilt '
                  'bodies and fresh readers to pass the original function threshold. The mean must reach 80%, its '
                  'adjusted lower bound 70%, and each read/write route contrast must reach 50 points with a positive '
                  'adjusted lower bound. Bounds use quantile .05/12. Trials and packets are averaged within each '
                  'network before equal network weighting. Different doses can have different matched cohorts.']
    for result in summary['results']:
        lines += ['', f"## Dose {result['dose']}", '',
                  'Failed current gates: '+(', '.join(k for k, v in result['current']['gates'].items() if not v) or 'none')+'.', '',
                  '| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |',
                  '|---|---:|---:|']
        for name, stat in result['current']['differences'].items():
            interval = f"[{point(stat['equivalence_low'])}, {point(stat['equivalence_high'])}]"
            lines.append(f"| {name} | {point(stat['mean'])} | {interval} |")
        if result['transmission'] is not None:
            lines += ['', 'Failed full-screen gates: '+(', '.join(k for k, v in result['transmission']['gates'].items() if not v) or 'none')+'.', '',
                      '| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |',
                      '|---|---:|---:|---:|---:|---:|---:|']
            stats = result['estimates']
            for arm in e.ARMS:
                values = [stats['reader_success'][v][arm] for v in e.VARIANTS]
                values += [stats['own_retained'][v][arm] for v in e.VARIANTS]
                values += [stats['distinct'][arm], stats['joint_functional_retention'][arm]]
                lines.append('| '+arm+' | '+' | '.join(point(s['mean']) for s in values)+' |')
    lines += ['', 'All source networks were already exposed in H003 development; H004 confirmation was excluded. '
              'Current validation is a finite, cohort-level observer and does not guarantee equality for every packet. '
              'Sources without an exact opposing observation pair, fully correct visible output, or eight hidden '
              'sites of each sign are excluded by the same structural rule at every dose.', '',
              'Swaps preserve the full weight histogram, norm, visible record block and coordinate-permutation '
              'invariants. Shared base weights remain fixed; base-plus-record norms are retained separately. '
              'The intervention changes more edges than H006 and is not an equal-size comparison with its edge flips.', '',
              'Exact self-retention is deliberately stronger than functional continuation. A passed screen establishes '
              'feasibility for one replacement, not different long-term durability, useful reciprocal repair, '
              'discovered competence or superiority to protected copying. Failed doses cannot be rescued by another '
              'endpoint. No sixteen-replacement study is launched here and H005/H006 verdicts remain unchanged.', '',
              'Complete block rows, every gate, all route controls and independently replayed raw observations are '
              'retained. No private code, data, trained states or text entered the screen. No manuscript was edited.', '',
              f"Retained audit passed: {summary['audit_passed']}. Number of source networks: {len(config['seeds'])}.", '']
    if config['mode'] == 'benchmark':
        lines += ['Engineering used one excluded network and forced every trial to exercise the complete pipeline. '
                  'It cannot establish population equivalence or nominate a scientific dose.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))


def plot(out, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    results = summary['results']
    x = np.arange(len(results))
    labels = [str(r['dose']) for r in results]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3), layout='constrained')
    axes[0].bar(x, [r['current']['matches'] for r in results],
                color=['#117a59' if r['current']['passed'] else '#929292' for r in results])
    axes[0].axhline(64, color='#8c4242', linestyle=':', label='Minimum coverage')
    axes[0].set(title='Current match coverage', ylabel='Matched packets')
    axes[0].legend(fontsize=8)
    for variant, color in zip(e.VARIANTS, ['#777777', '#117a59']):
        stats = [r['current']['current_success'][variant] for r in results]
        values = np.array([np.nan if s['mean'] is None else 100*s['mean'] for s in stats])
        axes[1].plot(x, values, '-o', label=variant, color=color)
    axes[1].axhline(95, color='#8c4242', linestyle=':')
    axes[1].set(title='Independent current validation', ylabel='Success (%)', ylim=(0, 103))
    axes[1].legend(fontsize=8)
    if summary['replacements_generated']:
        for arm, color in [('renewal', '#117a59'), ('read_off', '#b3483e'), ('write_off', '#617995')]:
            stats = [r['estimates']['joint_functional_retention'][arm] for r in results]
            values = [np.nan if s['mean'] is None else 100*s['mean'] for s in stats]
            axes[2].plot(x, values, '-o', color=color, label=arm)
            if all(s['low'] is not None for s in stats):
                axes[2].fill_between(x, [100*s['low'] for s in stats], [100*s['high'] for s in stats], color=color, alpha=.15)
        axes[2].axhline(80, color='#8c4242', linestyle=':', label='80% mean gate')
        axes[2].set(title='One damaged replacement', ylabel='Joint functional exact retention (%)', ylim=(-3, 103))
        axes[2].legend(fontsize=8)
    else:
        axes[2].text(.5, .5, 'No admissible current match\nNo replacement trials generated',
                     ha='center', va='center', transform=axes[2].transAxes)
        axes[2].set_axis_off()
    for ax in axes:
        if ax.axison:
            ax.set_xticks(x, labels)
            ax.set_xlabel('Hidden pairs swapped')
            ax.grid(axis='y', alpha=.15)
    fig.suptitle(f"H007 · {summary['verdict']} · one-replacement feasibility only", fontsize=12)
    fig.savefig(Path(out)/'overview.png', dpi=160)
    fig.savefig(Path(out)/'overview.pdf')
    plt.close(fig)
