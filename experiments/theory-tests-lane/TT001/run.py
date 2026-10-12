"""Append-only benchmark and retrospective development execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import scipy
import sklearn

import audit
import evaluator as e
from operators import short_probe_counterexample
from source import load_dataset, read_portable, save_dataset, sha, source_metadata, utc

HERE = Path(__file__).resolve().parent
LANE = HERE.parent


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def inputs():
    return [HERE/name for name in ('evaluator.py', 'operators.py', 'source.py', 'audit.py',
            'checks.py', 'plot.py', 'run.py', 'plan.json', 'PROTOCOL.md')]+[LANE/'run_python.sh']


def code_hashes():
    return {str(p.relative_to(LANE)): sha(p) for p in inputs()}


def report(output, summary, plan):
    lines = ['# Conventional forecast development results', '',
        'Status: '+summary['status']+'. RDT verdict: NOT_TESTED.', '',
        f"{summary['blocks']} blocks and {summary['lineages']} lineages. Outer evaluation separates whole blocks; fitting and tuning use training blocks only. The source cohort was already exposed as development evidence.", '',
        'Predictor inputs stop after rebuild 3 or 8. Training blocks provide their long-horizon outcomes. These results do not establish short-only calibration, causal effects or cross-apparatus transfer.', '',
        '| Prefix | Target | Model | Brier loss | Log loss | Brier gain over prevalence | Descriptive interval |',
        '| ---: | --- | --- | ---: | ---: | ---: | --- |']
    for k in plan['prefixes']:
        for endpoint in plan['endpoints']:
            for model in plan['models']:
                s = summary['scores'][f'k{k}.{endpoint}.{model}']
                g = s['brier_gain_over_prevalence']; lo, hi = g['descriptive_interval']
                lines.append(f"| {k} | {endpoint} | {model} | {s['brier']:.6f} | {s['log_loss']:.6f} | {g['mean']:+.6f} | [{lo:+.6f}, {hi:+.6f}] |")
    lines += ['', 'Positive Brier gain means lower prediction error. Intervals resample the 32 block loss differences while holding out-of-fold predictions fixed. They do not include training-selection uncertainty, and no confirmatory or multiplicity-adjusted claim is made.', '',
        f"All recorded rebuilding bodies pass in {summary['body_all_successes']}/{summary['lineages']} histories; terminal recipients pass in {summary['terminal_successes']}/{summary['lineages']}. The path forecast target starts after its prefix and additionally requires terminal success, so it is a distinct endpoint.", '',
        '| Prefix | Target | Observed frequency |', '| ---: | --- | ---: |']
    for k in plan['prefixes']:
        for endpoint in plan['endpoints']:
            s = summary['scores'][f'k{k}.{endpoint}.prevalence']
            lines.append(f"| {k} | {endpoint} | {s['observed_rate']:.6f} |")
    lines += ['', f"The workflow made {summary['total_fit_calls']} model fit calls, including inner tuning. One process and one numerical thread were used. The current-readout model has six inputs; the prefix models have 75 inputs from up to 24 recorded channels per generation. Diagnostic packet comparisons require external observation of incoming and outgoing state.", '',
        'The source adapter verifies completion and array identities, checks all diagnostic columns against E042, and compares outcomes and margins with original E041 case arrays. The separate calculation check covers extracted feature summaries, group splits, every prediction score, bins and descriptive intervals. Original dynamics and library optimizers are not independently reimplemented.', '',
        'All predictions, losses, selected parameters, input arrays and software identities are retained. `predictions.npz` and `development_dataset.npz` make the selected development comparison portable. `inputs/` preserves the executed code and protocol. Revisions after these results require a new development version; prospective RDT testing needs its own candidate, calibrated margins and eligible unseen conditions.', '',
        '![Brier-score comparisons](brier_comparisons.png)', '']
    (output/'REPORT.md').write_text('\n'.join(lines))


def replay(output):
    manifest = json.loads((output/'manifest.json').read_text())
    complete = json.loads((output/'COMPLETE.json').read_text())
    for rel, digest in complete['outputs_sha256'].items():
        if sha(output/rel) != digest:
            raise ValueError(f'Output changed: {rel}')
    if manifest['code_sha256'] != code_hashes():
        raise ValueError('Replay requires original code')
    plan = json.loads((output/'inputs/TT001/plan.json').read_text())
    data = read_portable(output/'development_dataset.npz')
    result, predictions, fold = e.evaluate(data, plan)
    with np.load(output/'predictions.npz', allow_pickle=False) as expected:
        for key, value in predictions.items():
            np.testing.assert_array_equal(value, expected[key])
    saved = json.loads((output/'summary.json').read_text())
    if result['scores'] != saved['scores'] or result['fits'] != saved['fits']:
        raise ValueError('Replay differs')
    checking = audit.check(data, result, predictions, fold, plan, e.design, e.probe)
    dump(output/'REPLAY.json', dict(status='PASS', utc=utc(), prediction_arrays_byte_equal=True,
        exact_scores_and_selected_settings=True, check=checking,
        scope='Same implementation deterministic replay, not external replication.'))
    print(json.dumps({'status': 'REPLAY_PASS', 'output': str(output)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('benchmark', 'development', 'replay'), required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.replace('_', '').isalnum():
        raise ValueError('Use a simple run name')
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    output = HERE/'runs'/args.name
    if args.mode == 'replay':
        replay(output); return
    plan = json.loads((HERE/'plan.json').read_text())
    hashes = code_hashes()
    if args.mode == 'development':
        benchmark = HERE/'runs/benchmark_v1'
        b = json.loads((benchmark/'COMPLETE.json').read_text())
        old = json.loads((benchmark/'manifest.json').read_text())
        if b['status'] != 'COMPLETE' or old['code_sha256'] != hashes:
            raise ValueError('Need successful benchmark with unchanged inputs')
        estimate = 3*b['seconds']+90
        if estimate > plan['foreground_limit_seconds']:
            raise ValueError('Forecast exceeds foreground policy; prepare detached execution')
        if shutil.disk_usage(HERE).free < plan['storage_reserve_bytes']:
            raise ValueError('Insufficient storage reserve')
    else:
        estimate = None
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    try:
        for p in inputs():
            dest = output/'inputs'/p.relative_to(LANE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
        manifest = dict(study='TT001', mode=args.mode, started_utc=utc(), code_sha256=hashes,
            retrospective=True, prior_aggregate_outcomes_known=True, rdt_candidate=None,
            source_identity=source_metadata(plan), forecast_seconds=estimate,
            python=sys.version, platform=platform.platform(), numpy=np.__version__,
            scipy=scipy.__version__, sklearn=sklearn.__version__,
            cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            threads={name: os.environ.get(name) for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
        dump(output/'manifest.json', manifest)
        with (output/'technical_checks.log').open('x') as log:
            subprocess.run([sys.executable, '-B', str(HERE/'checks.py')],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        if args.mode == 'benchmark':
            data = e.synthetic(seed=42)
            provenance = dict(status='EXCLUDED_SYNTHETIC', real_array_access=False)
        else:
            with (LANE/'exposure_register.jsonl').open('a') as f:
                f.write(json.dumps(dict(event='RAW_ARRAY_ACCESS_STARTED', utc=utc(), study='TT001',
                    classification='DEVELOPMENT', source_families=['E041', 'E042', 'E046'],
                    run=args.name, outcome_scope='Known cohort; full derived histories accessed for development.'))+'\n')
            data, provenance = load_dataset(plan)
        dump(output/'source_provenance.json', provenance)
        save_dataset(output/'development_dataset.npz', data)
        result, predictions, fold = e.evaluate(data, plan, lambda k: print('Scored', k, flush=True))
        verification = audit.check(data, result, predictions, fold, plan, e.design, e.probe)
        verification['utc'] = utc()
        summary = dict(status='EXCLUDED_SYNTHETIC_BENCHMARK' if args.mode == 'benchmark' else 'RETROSPECTIVE_DEVELOPMENT_COMPLETE',
            rdt_verdict='NOT_TESTED', blocks=len(np.unique(data.groups)), lineages=len(data.groups),
            body_all_successes=int(data.body.all(axis=1).sum()), terminal_successes=int(data.terminal.sum()),
            **result)
        with (output/'predictions.npz').open('xb') as handle:
            np.savez_compressed(handle, groups=data.groups, fold=fold, **predictions)
        dump(output/'summary.json', summary)
        dump(output/'CALCULATION_CHECK.json', verification)
        dump(output/'exact_counterexamples.json', short_probe_counterexample())
        report(output, summary, plan)
        from plot import render
        render(output, summary, plan)
        if code_hashes() != hashes:
            raise ValueError('Inputs changed during execution')
        if args.mode == 'development':
            source_metadata(plan)
        outputs = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        dump(output/'COMPLETE.json', dict(status='COMPLETE', utc=utc(), seconds=time.monotonic()-start,
             rdt_verdict='NOT_TESTED', outputs_sha256=outputs,
             storage_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())))
        print(json.dumps(dict(status='COMPLETE', mode=args.mode, seconds=time.monotonic()-start,
                              output=str(output), fits=result['total_fit_calls'])), flush=True)
    except BaseException:
        dump(output/'FAILED.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
