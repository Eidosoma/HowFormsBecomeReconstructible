"""Freeze, execute and replay the bounded matched-channel development study."""
import argparse
from datetime import datetime, timezone
import itertools
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

import study as s


def utc():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def inputs():
    return [s.HERE/name for name in ('study.py', 'checks.py', 'run.py', 'plan.json', 'PROTOCOL.md')]+[s.LANE/'run_python.sh']


def hashes():
    return {str(p.relative_to(s.LANE)): s.sha(p) for p in inputs()}


def render(output, result, benchmark):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), layout='constrained')
    for row, k in enumerate(s.PLAN['prefixes']):
        for col, endpoint in enumerate(s.PLAN['endpoints']):
            ax = axes[row, col]
            for j, name in enumerate(('logistic', 'boosted')):
                item = result['contrasts'][f'k{k}.{endpoint}.history_gain_{name}']
                low, high = np.asarray(item['descriptive_interval'])*1000
                ax.hlines(j, low, high, color='#245879', linewidth=2)
                ax.plot(1000*item['mean'], j, 'o', color='#245879')
            ax.axvline(0, color='#777', linewidth=1)
            ax.set_yticks([0, 1], ['Logistic', 'Boosting']); ax.set_ylim(1.5, -.5)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
            ax.set_xlabel('Brier reduction from history (×10⁻³)')
            ax.set_title(f'Observe {k}: '+('terminal' if endpoint == 'terminal' else 'future path and terminal'))
            ax.grid(axis='x', alpha=.2)
    fig.suptitle(('Excluded synthetic timing input' if benchmark else 'History versus the same 24 latest diagnostic channels')+
        '\nPositive favors history; descriptive intervals hold fitted forecasts fixed', fontsize=12)
    fig.savefig(output/'history_gains.png', dpi=160)
    fig.savefig(output/'history_gains.pdf')
    plt.close(fig)


def report(output, result, benchmark):
    lines = ['# Current diagnostics and history forecast results', '',
        ('Excluded synthetic timing input. Reference forecasts are technical 0.5 placeholders.' if benchmark else
         'Retrospective E041 development comparison: 32 blocks and 512 lineages. All 24 raw diagnostic channels are available to both current and history predictors.'), '',
        'The latest diagnostics include prior-write quantities and are not a complete physical state. Training blocks provide long-horizon labels. This comparison does not test the RDT v0.2 fresh-assay model.', '',
        '| Prefix | Target | Model | Brier loss | Log loss |',
        '| ---: | --- | --- | ---: | ---: |']
    for k, endpoint, model in itertools.product(s.PLAN['prefixes'], s.PLAN['endpoints'], s.PLAN['models']):
        item = result['scores'][f'k{k}.{endpoint}.{model}']
        lines.append(f"| {k} | {endpoint} | {model} | {item['brier']:.6f} | {item['log_loss']:.6f} |")
    lines += ['', '| Prefix | Target | Contrast | Brier reduction | Descriptive interval |',
              '| ---: | --- | --- | ---: | --- |']
    for key, item in result['contrasts'].items():
        prefix, endpoint, name = key.split('.')
        low, high = item['descriptive_interval']
        lines.append(f"| {prefix[1:]} | {endpoint} | {name} | {item['mean']:+.6f} | [{low:+.6f}, {high:+.6f}] |")
    lines += ['', 'Positive history gain means lower loss from the 75-feature history representation than from the 24 latest measurements within the same learning procedure. Positive additional-current-channel gain means lower loss from 24 than from six latest measurements in logistic regression.', '',
        'Intervals resample the 32 block differences with fitted out-of-fold predictions fixed. They omit training and selection uncertainty; no confirmatory significance, equivalence or multiple-comparison claim is made. The path targets differ in remaining duration between cutoffs. Every specified comparison is retained.', '',
        f"There were {result['fit_calls']} new fitting calls and {result['prediction_scores_checked']} scalar prediction-score checks. Earlier forecasts were reused from the immutable TT001 run; the new models use identical grouped folds and tuning grids. The observation/storage costs of history are greater and are not represented as equal.", '',
        'Source and code hashes, tuning decisions, scores, predictions and figures are retained beside this report. No new native trajectory was generated.', '',
        '![Matched-channel history gains](history_gains.png)', '']
    with (output/'REPORT.md').open('x') as f:
        f.write('\n'.join(lines))


def replay(output):
    c = json.loads((output/'COMPLETE.json').read_text())
    for rel, expected in c['outputs_sha256'].items():
        if s.sha(output/rel) != expected:
            raise ValueError('Stored output changed: '+rel)
    manifest = json.loads((output/'manifest.json').read_text())
    if manifest['code_sha256'] != hashes():
        raise ValueError('Replay code mismatch')
    result, predictions, folds = s.evaluate(s.load_data(), s.PLAN)
    with np.load(output/'predictions.npz', allow_pickle=False) as old:
        for key, value in predictions.items():
            if value.dtype != old[key].dtype or value.shape != old[key].shape or value.tobytes() != old[key].tobytes():
                raise ValueError('Replay prediction mismatch: '+key)
        np.testing.assert_array_equal(folds, old['fold'])
    previous = json.loads((output/'summary.json').read_text())
    for name in ('scores', 'contrasts', 'fits'):
        if result[name] != previous[name]:
            raise ValueError('Replay changed '+name)
    dump(output/'REPLAY.json', dict(status='PASS', utc=utc(), prediction_bytes_equal=True,
        scores_contrasts_and_settings_equal=True, scope='Same implementation replay; not external replication.'))
    print(json.dumps({'status': 'REPLAY_PASS', 'output': str(output)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['benchmark', 'development', 'replay'], required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.replace('_', '').isalnum():
        raise ValueError('Use a simple unique run name')
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    output = s.HERE/'runs'/args.name
    if args.mode == 'replay':
        replay(output); return
    code = hashes()
    forecast = None
    if args.mode == 'development':
        bench = s.HERE/'runs/benchmark_v1'
        b = json.loads((bench/'COMPLETE.json').read_text())
        m = json.loads((bench/'manifest.json').read_text())
        if b['status'] != 'COMPLETE' or m['code_sha256'] != code:
            raise ValueError('Need successful benchmark with unchanged inputs')
        forecast = 3*b['seconds']+90
        if forecast > s.PLAN['foreground_limit_seconds']:
            raise ValueError('Exceeds foreground limit; use parent detached policy')
    if shutil.disk_usage(s.HERE).free < s.PLAN['storage_reserve_bytes']:
        raise ValueError('Insufficient storage reserve')
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    try:
        for p in inputs():
            dest = output/'inputs'/p.relative_to(s.LANE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
        dump(output/'manifest.json', dict(study='TT002', mode=args.mode, started_utc=utc(),
            retrospective=True, code_sha256=code, prior_complete_sha256=s.PLAN['prior_complete_sha256'],
            prior_run=str(s.PRIOR), prior_references=s.REUSED,
            foreground_forecast_seconds=forecast, python=sys.version, platform=platform.platform(),
            numpy=np.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__,
            threads={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
            cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None))
        with (output/'technical_checks.log').open('x') as f:
            subprocess.run([sys.executable, '-B', str(s.HERE/'checks.py')], stdout=f, stderr=subprocess.STDOUT, check=True)
        benchmark = args.mode == 'benchmark'
        data = s.e.synthetic(seed=s.PLAN['synthetic_seed']) if benchmark else s.load_data()
        if not benchmark:
            with (s.LANE/'exposure_register.jsonl').open('a') as f:
                f.write(json.dumps(dict(event='DEVELOPMENT_REUSE_STARTED', utc=utc(), study='TT002',
                    classification='DEVELOPMENT', prior_run=s.PLAN['prior_run'], run=args.name,
                    scope='Already exposed TT001 arrays and forecasts; no E051 data.'))+'\n')
        result, predictions, folds = s.evaluate(data, s.PLAN, benchmark=benchmark,
            progress=lambda key: print('Scored '+key, flush=True))
        summary = dict(status='EXCLUDED_SYNTHETIC_BENCHMARK' if benchmark else 'RETROSPECTIVE_DEVELOPMENT_COMPLETE',
            rdt_verdict='NOT_TESTED', blocks=len(np.unique(data.groups)), lineages=len(data.groups), **result)
        dump(output/'summary.json', summary)
        with (output/'predictions.npz').open('xb') as f:
            np.savez_compressed(f, groups=data.groups, fold=folds, **predictions)
        dump(output/'CALCULATION_CHECK.json', dict(status='PASS',
            scores_checked=result['prediction_scores_checked'], contrasts_checked=len(result['contrasts']),
            reused_forecasts_checked=not benchmark, scope='Separate scalar scores and contrast resampling; not simulator replication.'))
        report(output, result, benchmark)
        render(output, result, benchmark)
        if hashes() != code:
            raise ValueError('Inputs changed during run')
        s.verify_prior()
        outputs = {str(p.relative_to(output)): s.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        elapsed = time.monotonic()-start
        dump(output/'COMPLETE.json', dict(status='COMPLETE', utc=utc(), seconds=elapsed,
            rdt_verdict='NOT_TESTED', outputs_sha256=outputs))
        print(json.dumps({'status': 'COMPLETE', 'mode': args.mode, 'seconds': elapsed,
            'new_fit_calls': result['fit_calls'], 'output': str(output)}), flush=True)
    except BaseException:
        dump(output/'FAILED.json', dict(status='FAILED', utc=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
