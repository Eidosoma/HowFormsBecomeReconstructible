"""Small post-result diagnosis of sealed H034 forecasts; no fitting or futures."""
from pathlib import Path
from collections import defaultdict
from statistics import fmean
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys

MODELS = ('labels6', 'margins6', 'raw6', 'persistence3', 'persistence6', 'same_observation')
EDGES = (0., .01, .05, .10, .20, .30, .40, .50, .75, 1.)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def summarize(rows, model):
    if not rows:
        return dict(rows=0, networks=0, mean_forecast=None, mean_flip_rate=None, bias=None, brier=None, excess_error=None)
    mean_p = fmean(float(r[model+'_probability']) for r in rows)
    mean_q = fmean(float(r['flip_rate']) for r in rows)
    return dict(rows=len(rows), networks=len({r['source_id'] for r in rows}),
        mean_forecast=mean_p, mean_flip_rate=mean_q, bias=mean_p-mean_q,
        brier=fmean(float(r[model+'_brier']) for r in rows),
        excess_error=fmean(float(r[model+'_excess_error']) for r in rows))


def execute(out):
    freeze = json.loads((out/'freeze.json').read_text())
    assert all(digest(out/name) == expected for name, expected in freeze.items())
    groups = {}; checks = 0
    for split in ('train', 'test'):
        with (out/'inputs'/f'prefixes_{split}.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            q = float(row['flip_rate']); v = 32*q*(1-q)/31
            assert float(row['flip_count']) == q*32
            assert abs(v-float(row['conditional_variance'])) < 1e-12
            for model in MODELS:
                p = float(row[model+'_probability']); brier = p*p-2*p*q+q
                assert 0 <= p <= 1
                assert abs(brier-float(row[model+'_brier'])) < 1e-12
                assert abs((p-q)**2-v/32-float(row[model+'_excess_error'])) < 1e-12
                checks += 3
            assert row['same_observation_probability'] == row['persistence6_probability']
        for disagreement in (False, True):
            selected = [r for r in rows if (r['early_disagreement'] == 'True') == disagreement]
            panels = [('all_selected_rows', selected)] + [
                (f'cell_{cell}_{selection}', [r for r in selected if r['cell'] == cell and r['selection'] == selection])
                for cell, selection in sorted({(r['cell'], r['selection']) for r in selected})]
            for panel, subset in panels:
                key = f'{split}/{"disagreement" if disagreement else "agreement"}/{panel}'
                source_rows = defaultdict(list)
                for r in subset:
                    source_rows[r['source_id']].append(r)
                groups[key] = {}
                for model in MODELS:
                    network = [summarize(r, model) for r in source_rows.values()]
                    equal_network = {k: fmean(r[k] for r in network) for k in
                        ('mean_forecast', 'mean_flip_rate', 'bias', 'brier', 'excess_error')}
                    bins = []
                    for low, high in zip(EDGES[:-1], EDGES[1:]):
                        included = [r for r in subset if low <= float(r[model+'_probability']) < high or
                                    (high == 1 and float(r[model+'_probability']) == 1)]
                        bins.append(dict(lower=low, upper=high, **summarize(included, model)))
                    assert sum(b['rows'] for b in bins) == len(subset)
                    groups[key][model] = dict(row_weighted=summarize(subset, model), equal_network=equal_network, bins=bins)
    result = dict(classification='POST_RESULT_SAVED_FORECAST_CALIBRATION_DIAGNOSIS',
        fits=0, new_futures=0, prior_verdicts_changed=False, groups=groups,
        checked_model_identities=checks, probability_bins=EDGES,
        limitations='Exposed cohorts and selected strata; dependent rows; finite 32-future frequencies; descriptive, not population inference or a representation-versus-fit diagnosis.')
    save(out/'diagnosis.json', result)
    lines = ['# H034 — Saved-forecast calibration diagnosis', '',
        'Post-result description of exposed cohorts; no model fits, new futures or changed prior verdicts.', '',
        '| Cohort / disagreement panel | Pairs | Networks | Observed flip frequency | Candidate forecast | Candidate bias | Labels forecast | Labels bias |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for key, models in groups.items():
        if '/disagreement/' not in key:
            continue
        a, b = [models[m]['row_weighted'] for m in ('persistence6', 'labels6')]
        lines.append(f'| {key} | {a["rows"]} | {a["networks"]} | {a["mean_flip_rate"]:.4f} | {a["mean_forecast"]:.4f} | {a["bias"]:+.4f} | {b["mean_forecast"]:.4f} | {b["bias"]:+.4f} |')
    lines += ['', 'Bias is forecast minus observed frequency. Totals weight the selected prefix pairs equally; related rows are not independent. '
        'The JSON additionally retains equal-network means, all agreement controls, all six models and fixed-bin calibration summaries including empty bins.', '',
        'A bias within this selected stratum is not an estimate for the original population. '
        'Thirty-two sampled futures do not reveal exact conditional probabilities. '
        'This diagnosis does not distinguish information loss from fitting, regularization or model-class limitations. '
        'No fitted recalibration is applied, and the same-observation comparator still ties the candidate exactly.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))
    save(out/'COMPLETE.json', dict(state='COMPLETE', completed_utc=datetime.now(timezone.utc).isoformat(),
        groups=len(groups), checked_model_identities=checks, fits=0, new_futures=0))
    save(out/'checksums.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'checksums.json'})
    print(out/'REPORT.md')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.run:
        execute(args.run.resolve()); return
    lane = Path(__file__).resolve().parent.parent
    prior = lane/'runs/h034_branching_v1'; out = lane/'runs/h034_calibration_v1'
    manifest = json.loads((prior/'checksums.json').read_text())
    out.mkdir(exist_ok=False); (out/'inputs').mkdir(); (out/'source').mkdir()
    for name in ('prefixes_train.csv', 'prefixes_test.csv'):
        assert digest(prior/name) == manifest[name]
        shutil.copyfile(prior/name, out/'inputs'/name)
    shutil.copyfile(Path(__file__).resolve(), out/'source/calibration.py')
    shutil.copyfile(lane/'h034/CALIBRATION_PLAN.md', out/'source/CALIBRATION_PLAN.md')
    save(out/'config.json', dict(prior=str(prior), prior_manifest_sha256=digest(prior/'checksums.json'),
        classification='POST_RESULT_DIAGNOSTIC', models=MODELS, bins=EDGES, fits=0, new_futures=0))
    save(out/'freeze.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    subprocess.run([sys.executable, '-B', str(out/'source/calibration.py'), '--run', str(out)], check=True)


if __name__ == '__main__':
    main()
