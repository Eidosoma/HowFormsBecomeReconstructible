"""One bounded disposable qualification and standalone cost measurement."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

import numpy as np

from ec_common import ROOT, C, P, ev, read, ledger, require, configure, verify_snapshot, environment, Guard, complete
from ec_probe import measure, verify_case
import pipeline


def worker(folder, fixture, regime, deadline):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    configure()
    packet = pipeline.synthetic_packets()[fixture]
    rule = 1 if fixture % 2 == 0 else -1
    key = [-99000 - fixture, 'fixture_' + C['benchmark']['fixtures'][fixture], fixture, 0]
    boundary = [.4, .4, .4, .4, .4, 1., .05, 0., 0., 0., .02]
    # Supplied synthetic covariates exercise probability arithmetic only.
    identity = dict(fixture=fixture, regime=regime, input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'))
    ledger.atomic_json(folder / 'START.json', dict(utc=ev.utc(), pid=os.getpid(), identity=identity,
        supplied_synthetic_boundary=True, new_scientific_outcomes=0))
    guard = Guard(folder, deadline)
    records = {}
    order = C['benchmark']['models'].copy()
    if (fixture + C['benchmark']['regimes'].index(regime)) % 2:
        order.reverse()
    for mode in order:
        records[mode] = measure(packet, rule, key, regime, mode, boundary, folder / mode, guard)
    checked = verify_case(records)
    ledger.atomic_json(folder / 'VERIFICATION.json', checked)
    payload = dict(verification=checked, order=order,
        timings={name: {k: v for k, v in receipt.items() if k.endswith('_seconds') or k in ('native_reads', 'flat_native_reads')}
                 for name, (_, receipt) in records.items()})
    guard.check()
    ledger.commit(folder, identity, payload)


def stop(processes):
    for p in processes:
        if p.poll() is None:
            p.terminate()
    for p in processes:
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def wait_wave(processes, deadline):
    with ThreadPoolExecutor(max_workers=len(processes)) as pool:
        futures = [pool.submit(p.wait) for p in processes]
        try:
            for f in as_completed(futures, timeout=max(.001, deadline - time.time())):
                require(f.result() == 0, 'Disposable worker failed; preserve failure without retry')
        except BaseException:
            stop(processes)
            raise


def summarize(case_timings, workers):
    require(len(case_timings) == 8 and workers == C['benchmark']['workers'], 'Complete benchmark at the measured concurrency required')
    models = {}
    for name in C['benchmark']['models']:
        values = [v[name] for v in case_timings]
        require(all(all(math.isfinite(v[k]) and v[k] > 0 for k in ('without_audit_wall_seconds',
            'total_wall_seconds', 'without_audit_cpu_seconds', 'primary_cpu_seconds')) for v in values), 'Invalid timing evidence')
        models[name] = dict(cases=len(values),
            maximum_without_audit_wall_seconds=max(v['without_audit_wall_seconds'] for v in values),
            maximum_total_wall_seconds=max(v['total_wall_seconds'] for v in values),
            mean_without_audit_cpu_seconds=math.fsum(v['without_audit_cpu_seconds'] for v in values) / len(values),
            maximum_primary_cpu_seconds=max(v['primary_cpu_seconds'] for v in values),
            total_audit_cpu_seconds=math.fsum(v['audit_cpu_seconds'] for v in values))
    # Replay all64 direct reads, including the cached prefix, rather than extrapolate a56-read shortcut.
    development = 1.5 * math.ceil(864 / workers) * models['direct64']['maximum_total_wall_seconds'] + 120
    return dict(models=models, exposed_108_block_development=dict(packet_regimes=864, workers=workers,
        primary_native_reads=864 * 64, flat_native_reads=864 * 2, new_acquisition_reads=0, new_future_outcomes=0,
        conservative_wall_seconds=development, within_preferred_hour=development <= 3600,
        within_six_hour_maximum=development <= 21600,
        pricing_rule='1.5 * ceil(864/workers) * slowest observed complete direct64 case, including audit, +120s.',
        limits='Synthetic timing forecast; no guarantee. Shared source checking, cached aggregation and report overhead may differ. A later job must enforce its declared hard stop and complete-cohort rule.'),
        prospective_sample_size_justified=False,
        prospective_followup='Price acquisition and full futures separately after a development estimate of the new paired comparator gaps. A108-block replication size is not automatically adequate for smaller equal-read gaps.')


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    wall = time.monotonic()
    deadline = time.time() + C['benchmark']['hard_wall_seconds']
    processes = []

    def expired(*_):
        raise TimeoutError('Fixed benchmark deadline or termination; no automatic retry')

    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, C['benchmark']['hard_wall_seconds'])
    try:
        (folder / 'logs').mkdir()
        (folder / 'units').mkdir()
        (folder / 'tmp').mkdir()
        ledger.atomic_json(folder / 'START.json', dict(utc=ev.utc(), pid=os.getpid(), scope='disposable_native_benchmark',
            input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'), deadline_epoch=deadline,
            hard_wall_seconds=C['benchmark']['hard_wall_seconds'], automatic_polling=False,
            automatic_retry=False, automatic_successor=False))
        ev.status(folder, status='RUNNING', stage='verification_and_admission')
        input_count = verify_snapshot()
        configure()
        sys.path.insert(0, str(ROOT / 'native/inherited/reference'))
        import cpu_preflight
        cpu = cpu_preflight.collect()
        workers = C['benchmark']['workers']
        cpu['planned_threads'] = workers + 1
        cpu['within_limit'] = cpu['other_active_or_recently_busy_threads'] + workers + 1 <= 12
        ledger.atomic_json(folder / 'CPU_ADMISSION.json', cpu)
        require(cpu['within_limit'], 'Shared CPU budget unavailable; no automatic retry')
        guard = Guard(folder, deadline)
        cases = [(i, regime) for i in range(len(C['benchmark']['fixtures'])) for regime in C['benchmark']['regimes']]
        for begin in range(0, len(cases), workers):
            guard.check()
            wave, streams = [], []
            try:
                for fixture, regime in cases[begin:begin + workers]:
                    name = f'fixture_{fixture}_{regime}'
                    stream = (folder / 'logs' / (name + '.log')).open('xb')
                    streams.append(stream)
                    command = [sys.executable, str(ROOT / 'ec_benchmark.py'), 'worker', '--output', str(folder / 'units' / name),
                               '--fixture', str(fixture), '--regime', regime, '--deadline', str(deadline)]
                    process = subprocess.Popen(command, cwd=ROOT, env=environment(folder / 'tmp'),
                        stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
                    processes.append(process)
                    wave.append(process)
                wait_wave(wave, deadline)
            finally:
                for stream in streams:
                    stream.close()
            ev.status(folder, status='RUNNING', stage='disposable_benchmark', completed_cases=min(begin + workers, len(cases)), total_cases=len(cases))
        timings = []
        retained = {}
        primary = flat = 0
        for fixture, regime in cases:
            case = folder / 'units' / f'fixture_{fixture}_{regime}'
            committed = ledger.verify(case, dict(fixture=fixture, regime=regime, input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json')))
            records = {}
            for mode in C['benchmark']['models']:
                receipt = read(case / (mode + '.json'))
                raw = ev.load(case / (mode + '.npz'), receipt['raw_sha256'])
                records[mode] = raw, receipt
                primary += receipt['native_reads']
                flat += receipt['flat_native_reads']
            require(verify_case(records) == read(case / 'VERIFICATION.json') == committed['payload']['verification'], 'Saved case verification differs')
            timings.append(committed['payload']['timings'])
            retained[(fixture, regime)] = records
        paired = 0
        for fixture in range(4):
            for mode in C['benchmark']['models']:
                matched, independent = retained[(fixture, 'matched')][mode], retained[(fixture, 'independent')][mode]
                for branch in (['writer'] if mode in ('pooled32', 'successor32') else []) + ['successor' if mode == 'successor32' else 'direct']:
                    a, b = matched[0], independent[0]
                    require(np.array_equal(a[branch + '_mask'], b[branch + '_mask']), 'Regime injuries are not paired')
                    require(np.array_equal(a[branch + '_birth'][:, 0], b[branch + '_birth'][:, 0]), 'Base cue birth differs')
                    require(np.array_equal(a[branch + '_birth'][:, 0], a[branch + '_birth'][:, 1]), 'Matched birth cues differ')
                    paired += len(a[branch + '_mask'])
        require(primary == 1600 and flat == 56 and paired == 800, 'Disposable workload accounting differs')
        prices = summarize(timings, workers)
        prices.update(scope='Disposable qualification and cost measurement; no forecast efficacy result.',
            native_byte_audits='PASS', scalar_endpoint_and_prediction='PASS', prefix_and_shared_reads='PASS',
            regimes_and_injuries_paired='PASS', primary_native_reads=primary, flat_native_reads=flat,
            new_scientific_outcomes=0, new_fits=0, automatic_successor=False)
        ledger.atomic_json(folder / 'RESULTS.json', prices)
        lines = ['Equal-read comparator qualification and standalone pricing.', '',
            'All eight synthetic cases passed separate flat dynamics, scalar response/probability checks, shared-read byte comparisons and paired-regime checks.', '',
            '| Predictor | Read budget | Mean CPU excluding audit, seconds | Slowest wall including audit, seconds |',
            '|---|---:|---:|---:|']
        for name in C['benchmark']['models']:
            m = prices['models'][name]
            lines.append(f"| {name} | {8 if name == 'direct8' else 64} | {m['mean_without_audit_cpu_seconds']:.4f} | {m['maximum_total_wall_seconds']:.4f} |")
        cost = prices['exposed_108_block_development']
        lines += ['', f"A complete development comparison on864 already exposed packet/regime cases is priced at{cost['conservative_wall_seconds']/60:.2f} minutes with{workers} workers, the slowest observed direct64 case, a1.5 factor and120s overhead.", '',
            'This is a forecast, not a guarantee or a launch. Such a run would replay all64 direct reads, check the existing eight-read prefix, and form the pooled comparator from cached writer reads. It would add55,296 primary and1,728 flat audit reads, with no new founders or long-horizon futures. All108 exposed blocks and four existing futures per packet/regime must remain enrolled.', '',
            'Shared boundary acquisition, transfer and training are historical costs, not included in these marginal measurement timings. A joint measurement can reuse writer32 and direct64 observations:128 unique native reads cover all five predictors. Standalone per-predictor costs remain0,8,64,64,64.', '',
            'The prospective study remains unpriced until the new paired loss gaps supply a precision calculation. Neither successful numerical qualification nor the old exposed-data model ranking establishes equal-read forecast superiority or RDT-specific evidence.', '']
        with (folder / 'REPORT.md').open('x') as stream:
            stream.write('\n'.join(lines))
        guard.check()
        verify_snapshot()
        complete(folder, dict(decision='EQUAL_READ_NATIVE_QUALIFICATION_PASS', scope='disposable_native_benchmark',
            input_files_verified=input_count, input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'),
            wall_seconds=time.monotonic() - wall, primary_native_reads=primary, flat_native_reads=flat,
            new_scientific_outcomes=0, new_fits=0, automatic_successor=False))
        print(prices, flush=True)
    except BaseException as error:
        stop(processes)
        ledger.atomic_json(folder / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        ev.status(folder, status='FAILED', automatic_retry=False)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['run', 'worker'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', type=int)
    parser.add_argument('--regime', choices=['matched', 'independent'])
    parser.add_argument('--deadline', type=float)
    args = parser.parse_args()
    if args.mode == 'run':
        run(args.output)
    else:
        worker(args.output, args.fixture, args.regime, args.deadline)
