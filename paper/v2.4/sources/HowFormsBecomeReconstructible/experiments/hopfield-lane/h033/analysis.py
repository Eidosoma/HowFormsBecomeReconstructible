"""One paired 30-contrast family, with separate budget and representation verdicts."""
import json
import numpy as np
from h007.io import save, verify
from h019.audit import load
from h024.analysis import simultaneous_intervals
from h033 import design as d, predict, measure


def evaluate(predictions, target, rows, bootstrap):
    y = predict.flips(target); n = bootstrap.shape[1]
    assert len(rows) == len(y) == 6*n*8*d.TAILS
    assert bootstrap.shape == (d.BOOTSTRAPS, n)
    assert np.issubdtype(bootstrap.dtype, np.integer) and ((bootstrap >= 0) & (bootstrap < n)).all()
    assert set(predictions) == set(d.MODELS)
    all_losses, all_errors = {}, {}
    for name, p in predictions.items():
        assert p.shape == y.shape and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
        all_losses[name] = (p-y)**2
        all_errors[name] = (p >= .5) != y
    panels, losses, errors = [], {m: [] for m in d.MODELS}, {m: [] for m in d.MODELS}
    for cell in d.CELLS:
        for selection in d.SELECTIONS:
            indices = np.array([i for i, r in enumerate(rows) if r['cell'] == cell and r['selection'] == selection])
            assert [rows[i]['source_id'] for i in indices] == np.repeat(np.arange(n), 8*d.TAILS).tolist()
            assert [rows[i]['branch'] for i in indices] == np.tile(np.repeat(np.arange(1, 9), d.TAILS), n).tolist()
            assert [rows[i]['tail'] for i in indices] == np.tile(np.arange(d.TAILS), n*8).tolist()
            values = y[indices].reshape(n, 8, d.TAILS)
            full_target = target[indices[::8*d.TAILS]//(8*d.TAILS)]
            baseline = full_target[:, 0]
            for name in d.MODELS:
                losses[name].append(all_losses[name][indices].reshape(n, 8, d.TAILS).mean(axis=(1, 2)))
                errors[name].append(all_errors[name][indices].reshape(n, 8, d.TAILS).mean(axis=(1, 2)))
            event_networks = int(values.any(axis=(1, 2)).sum())
            nonevent_networks = int((~values).any(axis=(1, 2)).sum())
            trials = []
            for branch in d.branches():
                j = branch['branch']; changed = full_target[:, j] != baseline
                difference = full_target[:, j].astype(int)-baseline.astype(int)
                trials.append(dict(**branch, successes=int(full_target[:, j].sum()),
                    flips=int(changed.sum()), gains=int((difference > 0).sum()), losses=int((difference < 0).sum()),
                    networks_with_flip=int(changed.any(axis=1).sum())))
            fractions = np.array([rows[i]['actual_fraction'] for i in indices]).reshape(n, 8, d.TAILS)
            capped = np.array([rows[i]['capped'] for i in indices]).reshape(n, 8, d.TAILS)
            np.testing.assert_array_equal(fractions, np.repeat(fractions[..., :1], d.TAILS, axis=-1))
            np.testing.assert_array_equal(capped, np.repeat(capped[..., :1], d.TAILS, axis=-1))
            for first in (0, 4):
                np.testing.assert_array_equal(fractions[:, first:first+4], np.repeat(fractions[:, first:first+1], 4, axis=1))
            panels.append(dict(cell=cell, selection=selection, networks=n, flip_events=int(values.sum()),
                flip_trials=int(values.size), event_networks=event_networks, nonevent_networks=nonevent_networks,
                informative=event_networks >= 8 and nonevent_networks >= 8 and int(values.sum()) >= 32,
                variants=trials, capped_networks=capped[:, [0, 4], 0].sum(axis=0).tolist(),
                actual_fraction_quantiles=np.quantile(fractions[:, [0, 4], 0], [0, .5, 1], axis=0).T.tolist(),
                zero_dose_networks=int((fractions[:, 0, 0] == 0).sum()),
                duplicate_with_fixed_probe=int(sum(rows[i]['probe_id'] == 0 for i in indices[::8*d.TAILS]))
                    if selection == d.SELECTIONS[1] else 0))
    losses = {name: np.array(value) for name, value in losses.items()}
    errors = {name: np.array(value) for name, value in errors.items()}
    labels, contrasts = [], []
    for panel, p in enumerate(panels):
        for comparator in (*d.COMPARATORS, d.ABLATION):
            labels.append(dict(panel=panel, cell=p['cell'], selection=p['selection'], comparator=comparator,
                question='observation_budget' if comparator == d.ABLATION else 'representation'))
            contrasts.append(losses[comparator][panel]-losses[d.CANDIDATE][panel])
    point, bands, radius = simultaneous_intervals(np.array(contrasts), bootstrap)
    family = [dict(label, improvement=float(p), simultaneous_ci95=ci.tolist())
              for label, p, ci in zip(labels, point, bands)]
    for i, panel in enumerate(panels):
        def passes(row):
            return bool(panel['informative'] and row['improvement'] > d.PREDICTION_MARGIN
                and row['simultaneous_ci95'][0] > 0
                and errors[d.CANDIDATE][i].mean() <= errors[row['comparator']][i].mean())
        same = [r for r in family if r['panel'] == i and r['question'] == 'representation']
        extra = [r for r in family if r['panel'] == i and r['question'] == 'observation_budget']
        panel['qualified_representation_advantage'] = all(passes(r) for r in same)
        panel['qualified_observation_budget_gain'] = passes(extra[0])
    representation = [i for i, p in enumerate(panels) if p['qualified_representation_advantage']]
    observation = [i for i, p in enumerate(panels) if p['qualified_observation_budget_gain']]
    return dict(label='PROSPECTIVE_DEVELOPMENT', primary_candidate=d.CANDIDATE,
        verdict='PERSISTENCE_REPRESENTATION_ADVANTAGE' if representation else 'NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE',
        observation_verdict='ADDITIONAL_OBSERVATION_GAIN' if observation else 'NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN',
        qualified_representation_panels=representation, qualified_observation_panels=observation, panels=panels,
        scores={name: [dict(panel=i, brier=float(losses[name][i].mean()), classification_error=float(errors[name][i].mean()))
                      for i in range(6)] for name in d.MODELS},
        forecast_family=family, forecast_family_size=30, simultaneous_radius=radius,
        uncertainty='One approximate simultaneous 95% family of 30 contrasts: 24 same-observation representation contrasts and six observation-budget contrasts. Whole test networks are resampled with all cells, selections, branches and tails paired. Conditional on the fitted training models.',
        interpretation='Fresh root 33033; H031/H032 supply hypotheses only and no pooled outcomes. All same-budget predictors may use both trajectories through replacement 6, while persistence3 is an explicit three-replacement ablation using the same recipe. Endpoints 13–24 define the unchanged reconstruction target. A positive budget verdict means extra observations help this fitted predictor, not that a representation beats equally informed alternatives or that RDT generally outperforms them. Earlier verdicts remain unchanged.')


def write_report(out, result):
    lines = ['# H033 — Early finite-response persistence', '', '**'+result['verdict']+'**', '',
        'Observation-budget verdict: **'+result['observation_verdict']+'**.', '', result['interpretation'], '',
        '| Setting | Probe | Flip events / pairs | Event networks | Representation qualifies | Extra observations qualify |',
        '| --- | --- | --- | --- | --- | --- |']
    for p in result['panels']:
        lines.append(f"| {p['cell']} | {p['selection']} | {p['flip_events']}/{p['flip_trials']} | {p['event_networks']}/{p['networks']} | {p['qualified_representation_advantage']} | {p['qualified_observation_budget_gain']} |")
    lines += ['', 'Positive comparisons concern prediction of either gains or losses in reconstruction.',
        'All directions, doses, signs and unchanged outcomes are retained. Variant counts, caps',
        'and achieved doses are in evaluation.json. Each trial is forecast after its own observed',
        'six-step prefix; tails are correlated observations, never independent network replicates.', '',
        '| Cell / probe | Question | Comparator | Brier advantage | Simultaneous 95% interval |',
        '| --- | --- | --- | --- | --- |']
    for r in result['forecast_family']:
        lines.append(f"| {r['cell']} / {r['selection']} | {r['question']} | {r['comparator']} | {r['improvement']:.6f} | {r['simultaneous_ci95']} |")
    lines += ['', 'Qualification requires eight networks with a flip, eight with an unchanged outcome',
        'and 32 flips; Brier advantage >0.005, positive simultaneous lower bound and no worse',
        'classification error at 0.5. Representation must pass against all four equal-budget',
        'comparators. Same-observation can choose the candidate exactly; a tie does not qualify.', '',
        result['uncertainty'], '', '| Model | Training-selected specification | Grouped CV Brier |',
        '| --- | --- | --- |']
    for name in d.MODELS:
        selected = json.loads((out/'models'/name/'model.json').read_text())['selected']
        lines.append(f"| {name} | {selected['id']} | {selected['brier']:.6f} |")
    lines += ['', '| Model | Panel | Test Brier | Classification error |', '| --- | --- | --- | --- |']
    for name, scores in result['scores'].items():
        for r in scores:
            lines.append(f"| {name} | {r['panel']} | {r['brier']:.6f} | {r['classification_error']:.6f} |")
    lines += ['', '![All declared comparisons](overview.png)', '',
        '[Evaluation](evaluation.json) · [Numerics](summary.json) · [Protocol](source/h033/PROTOCOL.md) ·',
        '[Forecast seal](prediction_sha256.json) · [Test submission](TEST_SUBMISSION.json) · [Checksums](checksums.json)',
        '', 'No later study launches automatically.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(15, 10), layout='constrained', gridspec_kw={'width_ratios': [1, 1.8]})
    for ax, question, title in zip(axes, ('observation_budget', 'representation'),
            ('Three extra observed replacements', 'Equal observation budget')):
        family = [r for r in result['forecast_family'] if r['question'] == question]
        values = np.array([r['improvement'] for r in family]); bands = np.array([r['simultaneous_ci95'] for r in family])
        labels = [f"{r['cell']} / {'fixed' if r['selection'] == d.SELECTIONS[0] else 'selected'} / {r['comparator']}" for r in family]
        ax.errorbar(values, np.arange(len(family)), xerr=np.vstack((values-bands[:, 0], bands[:, 1]-values)), fmt='o', capsize=3)
        ax.axvline(0, color='black', linewidth=.8); ax.axvline(d.PREDICTION_MARGIN, color='gray', linestyle='--')
        ax.set_yticks(np.arange(len(family)), labels, fontsize=8); ax.invert_yaxis(); ax.grid(axis='x', alpha=.2)
        ax.set_title(title); ax.set_xlabel('Brier advantage of persistence6')
    fig.suptitle('H033: one simultaneous 95% family across both questions')
    fig.savefig(out/'overview.png', dpi=170); fig.savefig(out/'overview.pdf'); plt.close(fig)


def closeout(out):
    measure.require_test_seal(out); verify(out, 'test_sha256.json')
    target = predict.targets(out, 'test')
    predictions = {name: load(out/'models'/name/'predictions.npz')['prediction'] for name in d.MODELS}
    rows = json.loads((out/'rows_test.json').read_text())
    result = evaluate(predictions, target, rows, load(out/'bootstrap.npz')['indices'])
    np.savez_compressed(out/'targets_test.npz', target=target, flip=predict.flips(target))
    save(out/'evaluation.json', result); write_report(out, result)
    return result
