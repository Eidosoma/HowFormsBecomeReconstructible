"""Descriptive conditional variability and frozen-forecast error accounting."""
import csv
import json
import numpy as np
from h007.io import save
from h019.audit import load
from h034 import design as d, measure


def decompose(y, probabilities):
    assert y.dtype == bool and y.ndim == 2 and y.shape[1] >= 2
    assert probabilities.ndim == 2 and len(probabilities) == len(y)
    assert np.isfinite(probabilities).all() and ((probabilities >= 0) & (probabilities <= 1)).all()
    k = y.shape[1]; q = y.mean(axis=1)
    variance = q*(1-q)*k/(k-1)
    brier = ((probabilities[..., None]-y[:, None])**2).mean(axis=-1)
    excess = (probabilities-q[:, None])**2-variance[:, None]/k
    np.testing.assert_allclose(brier, variance[:, None]+excess, rtol=0, atol=1e-15)
    return dict(flip_count=y.sum(axis=1), flip_rate=q, conditional_variance=variance,
                brier=brier, excess_squared_error=excess)


def describe(rows, arrays, take):
    indices = np.flatnonzero(take)
    if len(indices) == 0:
        return dict(prefixes=0, source_networks=0, mixed_prefixes=0, mixed_source_networks=0,
                    flip_count_histogram=[0]*(d.TAILS+1), models={})
    selected = [rows[i] for i in indices]
    count = arrays['flip_count'][take]
    mixed = (count > 0) & (count < d.TAILS)
    physical = {(r['source_id'], r['cell'], r['probe_id'], r['branch'], r['tail']) for r in selected}
    category = arrays['category'][take]
    return dict(prefixes=len(indices), source_networks=len({r['source_id'] for r in selected}),
        distinct_physical_prefix_pairs=len(physical), futures_per_prefix=d.TAILS,
        mixed_prefixes=int(mixed.sum()),
        mixed_source_networks=len({r['source_id'] for r, value in zip(selected, mixed) if value}),
        always_unchanged_prefixes=int((count == 0).sum()), always_changed_prefixes=int((count == d.TAILS).sum()),
        flip_count_histogram=np.bincount(count, minlength=d.TAILS+1).tolist(),
        flip_rate_mean=float(arrays['flip_rate'][take].mean()),
        flip_rate_quantiles=np.quantile(arrays['flip_rate'][take], [0, .25, .5, .75, 1]).tolist(),
        mean_conditional_variance=float(arrays['conditional_variance'][take].mean()),
        gain_events=int(arrays['gain'][take].sum()), loss_events=int(arrays['loss'][take].sum()),
        observer_categories=np.bincount(category.ravel(), minlength=4).tolist(),
        component_changed_nonflips_both_fail=int(((category > 0) & (category < 3) & arrays['both_fail'][take]).sum()),
        models={name: dict(brier=float(arrays['brier'][take, j].mean()),
            estimated_excess_squared_error=float(arrays['excess_squared_error'][take, j].mean()),
            mean_saved_probability=float(arrays['saved_forecasts'][take, j].mean()))
            for j, name in enumerate(d.MODELS)})


def assemble(out, config):
    result = dict(label=d.LABEL, futures_per_prefix=d.TAILS, models_refitted=False,
        prior_verdicts_changed=False, predictive_validation_claim=False,
        sampling='Census of endpoint-6 label disagreements; 32 randomly selected agreement rows per cohort/cell/selection. Means are within the selected stratum, never pooled population scores.',
        uncertainty='These are descriptive Monte Carlo estimates on exposed H033 networks. Source networks, duplicate probes and common futures remain dependent. No row-based significance tests or confidence intervals are supplied. Zero observed variability in 32 futures does not prove deterministic outcomes.',
        decomposition='For fixed prefix and future law, q is the conditional flip probability. The unbiased variance estimate is K/(K-1)*qhat*(1-qhat). Estimated forecast excess error is (p-qhat)^2-variance/K; it can be negative from Monte Carlo error and is not clipped. Their sum equals the average Brier loss on new futures. This diagnoses fixed forecasts; it does not distinguish representation loss from fitting limitations.',
        prediction_caveat='Training probabilities are saved OOF predictions of a training-selected specification; its selection reused those CV scores. Test probabilities are unchanged sealed H033 forecasts. Both network cohorts were exposed before H034 was specified.', cohorts={})
    for split in ('train', 'test'):
        rows, chunks = [], []
        for task in config['tasks']:
            if task['split'] != split:
                continue
            folder = out/'raw'/task['name']
            assert json.loads((folder/'audit.json').read_text())['qualified']
            inputs = load(out/'inputs'/f'{task["name"]}.npz')
            values = load(folder/'outcomes.npz')
            # Independently recover the observer from every saved resolution.
            for level in range(3):
                raw = load(folder/f'raw_{level}.npz')
                expected = measure.outcomes(raw['history'])
                for key in values:
                    if key not in ('window_activation_displacement', 'final_state_distance'):
                        np.testing.assert_array_equal(expected[key], values[key])
                if level == 2:
                    for key in values:
                        np.testing.assert_array_equal(expected[key], values[key])
            values.update(decompose(values['flip'], inputs['saved_forecasts']))
            values['saved_forecasts'] = inputs['saved_forecasts']
            values['early_disagreement'] = inputs['early_disagreement']
            values['row_index'] = inputs['row_index']
            rows.extend(task['rows']); chunks.append(values)
        arrays = {key: np.concatenate([c[key] for c in chunks]) for key in chunks[0]}
        assert [r['row_index'] for r in rows] == arrays['row_index'].tolist()
        np.testing.assert_array_equal(arrays['saved_forecasts'][:, d.MODELS.index('persistence6')],
                                      arrays['saved_forecasts'][:, d.MODELS.index('same_observation')])
        np.savez_compressed(out/f'diagnostics_{split}.npz', **arrays)
        save(out/f'rows_{split}.json', rows)
        panels = []
        for cell in d.CELLS:
            for selection in d.SELECTIONS:
                take = np.array([(r['cell'], r['selection']) == (cell, selection) for r in rows])
                panels.append(dict(cell=cell, selection=selection, strata={
                    name: describe(rows, arrays, take & (arrays['early_disagreement'] == flag))
                    for name, flag in (('early_disagreement', True), ('early_agreement_sample', False))}))
        result['cohorts'][split] = dict(panels=panels, strata={name: describe(rows, arrays,
            arrays['early_disagreement'] == flag) for name, flag in
            (('early_disagreement', True), ('early_agreement_sample', False))})
        with (out/f'prefixes_{split}.csv').open('x', newline='') as stream:
            fields = ['row_index', 'cell', 'selection', 'source_id', 'probe_id', 'branch', 'tail',
                      'early_disagreement', 'inclusion_probability', 'flip_count', 'flip_rate', 'conditional_variance']
            fields += [name+'_'+metric for name in d.MODELS for metric in ('probability', 'brier', 'excess_error')]
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for i, row in enumerate(rows):
                record = {key: row[key] for key in fields[:9]}
                record.update({key: float(arrays[key][i]) for key in fields[9:12]})
                for j, name in enumerate(d.MODELS):
                    record.update({name+'_probability': float(arrays['saved_forecasts'][i, j]),
                        name+'_brier': float(arrays['brier'][i, j]),
                        name+'_excess_error': float(arrays['excess_squared_error'][i, j])})
                writer.writerow(record)
    mixed = sum(s['mixed_prefixes'] for c in result['cohorts'].values() for s in c['strata'].values())
    result['finding'] = ('CONDITIONAL_FUTURE_VARIATION_OBSERVED' if mixed else
                         'NO_VARIATION_OBSERVED_IN_32_FUTURES')
    save(out/'diagnosis.json', result)
    write_report(out, result)
    return result


def write_report(out, result):
    lines = ['# H034 — Future variation after an identical observed history', '',
        '**'+result['label']+'**. **'+result['finding']+'**.', '',
        result['sampling'], '', result['uncertainty'], '', result['decomposition'], '',
        result['prediction_caveat'], '',
        'The original target remains all three activations >0.5 at every endpoint 13–24.',
        'H031’s directional causal result and failed forecast-advantage test remain separate.',
        'H033’s two negative qualification verdicts are unchanged. Richer inherited tasks retain their own priority.', '',
        '| Cohort | Cell / selection | Early stratum | Prefixes | Source networks | Mixed outcomes across 32 futures | Mean flip rate | Estimated conditional variance |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for split, cohort in result['cohorts'].items():
        for panel in cohort['panels']:
            for label, group in panel['strata'].items():
                lines.append(f"| {split} | {panel['cell']} / {panel['selection']} | {label} | {group['prefixes']} | {group['source_networks']} | {group['mixed_prefixes']} | {group.get('flip_rate_mean', 0):.6f} | {group.get('mean_conditional_variance', 0):.6f} |")
    lines += ['', 'All model decompositions, gain/loss counts and observer categories are retained in diagnosis.json.',
        'The four observer categories are no changed component labels; component-only change;',
        'endpoint-success change with unchanged whole-window target; and whole-window target change.',
        'A varying outcome at the same state demonstrates a contribution from unobserved future replacements.',
        'Uniform sampled outcomes do not establish a fundamental prediction ceiling or guarantee future stability.', '',
        '![Conditional outcome counts on the exposed test cohort](overview.png)', '',
        '[Diagnosis](diagnosis.json) · [Numerics and execution](summary.json) ·',
        '[Frozen protocol](source/h034/PROTOCOL.md) · [Checksums](checksums.json)', '']
    (out/'REPORT.md').write_text('\n'.join(lines))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True)
    for ax, panel in zip(axes.ravel(), result['cohorts']['test']['panels']):
        for label, display, color in (('early_disagreement', 'Early disagreement', '#b24a19'),
                                      ('early_agreement_sample', 'Agreement sample', '#2365a4')):
            group = panel['strata'][label]
            ax.step(np.arange(d.TAILS+1), group['flip_count_histogram'], where='mid', label=display, color=color)
        ax.set_title(f"Cell {panel['cell']} / {panel['selection']}", fontsize=10)
        ax.set_xlabel('Futures with an outcome change / 32')
        ax.set_ylabel('Observed prefix pairs')
        ax.set_xlim(-.5, 32.5)
        ax.set_ylim(bottom=0)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('H034: fixed endpoint-6 states, independently drawn later entrants')
    fig.tight_layout()
    fig.savefig(out/'overview.png', dpi=180)
    fig.savefig(out/'overview.pdf')
    plt.close(fig)
