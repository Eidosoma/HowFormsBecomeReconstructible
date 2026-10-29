"""Bounded equal-read extension of the complete, already exposed study."""
import argparse
import hashlib
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

import numpy as np

from ec_common import ROOT, C, P, MODELS, ev, read, ledger, require, configure, verify_snapshot, environment, Guard, complete, verify_complete, manifest, probability_scalar, probability_matrix
from ec_probe import measure, independent_scores
from ec_source import D, Source, cases, verify_metadata
from ec_benchmark import stop, wait_wave
from ec_analysis import analyze, scalar_check


def identity(item):
    return dict(case_index=item['index'], key=item['row']['key'], regime=item['regime'],
        input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'))


def verify_new(item, raw, receipt, original):
    cached, old_receipt, old_forecast = original
    row, g = item['row'], item['regime']
    require(receipt['mode'] == 'direct64' and receipt['key'] == row['key'] and receipt['rule'] == row['rule'] and
            receipt['regime'] == g and receipt['stage'] == D['stage'] and receipt['namespace'] == D['namespace'] and
            receipt['boundary'] == row['boundary'], 'New direct measurement identity differs')
    require(receipt['native_reads'] == 64 and receipt['flat_native_reads'] == 2 and
            receipt['audits'] == [dict(probe=i, byte_exact=True, native_reads=1) for i in (0, 32)], 'Wrong equal-read or flat-audit budget')
    require(raw['probes'].tolist() == list(range(64)) and np.array_equal(raw['boundary'], row['boundary']) and
            hashlib.sha256(raw['packet'].tobytes()).hexdigest() == row['packet_sha256'], 'Wrong packet or probe coverage')
    for name in ('mask', 'birth', 'end', 'windows', 'outgoing', 'aligned', 'passed'):
        a, b = raw['direct_' + name][:8], cached['direct_' + name]
        require(a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), 'Original direct prefix differs: ' + name)
    require(raw['direct_windows'].shape == (64, 32, 1, 2, 2), 'Complete direct windows required')
    aligned, passed = independent_scores(raw['direct_windows'], row['rule'])
    require(np.max(abs(aligned - raw['direct_aligned'])) < 1e-12 and np.array_equal(passed, raw['direct_passed']), 'New scalar endpoints differ')
    require(len(receipt['forcing']) == 64 and len(old_receipt['forcing']) == 32, 'Complete forcing records required')
    for i, f in enumerate(receipt['forcing']):
        require(f['probe'] == i and f['branch'] == 'direct' and f['purpose'] == 'evaluation', 'Wrong forcing index or purpose')
        if i < 32:
            require(old_receipt['forcing'][i]['probe'] == i and f['sha256'] == old_receipt['forcing'][i]['purposes']['evaluation'], 'Cached evaluation forcing differs')
        for name in ('mask', 'birth'):
            require(hashlib.sha256(raw['direct_' + name][i].tobytes()).hexdigest() == f['sha256'][name], 'Saved forcing digest differs')
    noises = {f['sha256']['noise'] for f in receipt['forcing']}
    writers = {f['purposes']['writer']['noise'] for f in old_receipt['forcing']}
    require(len(noises) == 64 and len(writers) == 32 and noises.isdisjoint(writers), 'Independent draws were reused')
    q_direct = int(passed.sum()) / 64
    q_pool = (int(passed[:32].sum()) + int(cached['writer_passed'].sum())) / 64
    require(q_direct == receipt['q'], 'New direct success fraction differs')
    probability = float(probability_matrix(np.array([row['boundary'] + [q_direct]]), MODELS['direct64'])[0])
    require(abs(probability - receipt['probability']) < 1e-12 and abs(probability - probability_scalar(row['boundary'] + [q_direct], MODELS['direct64'])) < 1e-12,
            'New direct scalar forecast differs')
    pooled = float(probability_matrix(np.array([row['boundary'] + [q_pool]]), MODELS['pooled32'])[0])
    require(abs(pooled - probability_scalar(row['boundary'] + [q_pool], MODELS['pooled32'])) < 1e-12, 'Pooled scalar forecast differs')
    probabilities = {name: old_forecast['probabilities'][old] for name, old in D['cached_names'].items()}
    probabilities.update(direct64=receipt['probability'], pooled32=pooled)
    return dict(**row, regime=g, q_direct64=q_direct, q_pooled32=q_pool, probabilities=probabilities)


def worker(folder, index, deadline):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    wall, cpu = time.monotonic(), time.process_time()
    item = cases()[index]
    configure('development')
    ledger.atomic_json(folder / 'START.json', dict(utc=ev.utc(), pid=os.getpid(), identity=identity(item)))
    guard = Guard(folder, deadline)
    guard.check()
    original = Source().case(item)
    row = item['row']
    raw, receipt = measure(original[0]['packet'], row['rule'], row['key'], item['regime'], 'direct64',
        row['boundary'], folder / 'direct64', guard, stage=D['stage'])
    forecast = verify_new(item, raw, receipt, original)
    ledger.atomic_json(folder / 'FORECAST.json', forecast)
    payload = dict(case_index=index, native_reads=64, flat_native_reads=2, original_prefix_byte_exact=True,
        original_forcing_checks=32, new_fits=0, new_scientific_outcomes=0,
        unit_wall_seconds=time.monotonic() - wall, unit_cpu_seconds=time.process_time() - cpu,
        standalone_timings={k: v for k, v in receipt.items() if k.endswith('_seconds')})
    guard.check()
    ledger.commit(folder, identity(item), payload)


def qualification_price(wave_times, payloads):
    require(len(wave_times) == 2 and len(payloads) == 8 and D['workers'] == 4,
            'Both complete qualification waves at four workers required')
    benchmark = read(ROOT / 'context/EQUAL_BENCHMARK_RESULTS.json')
    old_max = benchmark['models']['direct64']['maximum_total_wall_seconds']
    times = [old_max, *wave_times, *[v['unit_wall_seconds'] for v in payloads]]
    require(all(math.isfinite(v) and v > 0 for v in times), 'Invalid qualification timing')
    estimate = 1.5 * math.ceil(D['cases'] / D['workers']) * max(times) + 120
    require(estimate <= D['hard_wall_seconds'] <= C['runtime']['overall_maximum_seconds'],
            'Full comparison exceeds its fixed runtime cap; no automatic launch or extension')
    return dict(conservative_wall_seconds=estimate, preferred_hour=estimate <= 3600,
        hard_wall_seconds=D['hard_wall_seconds'], measured_workers=4,
        rule='1.5 *216 waves * max(original synthetic maximum direct64, each real qualification unit, each real four-worker wave including imports) +120s',
        retained_original_maximum_seconds=old_max, qualification_wave_seconds=wave_times)


def verify_qualification(folder):
    result = verify_complete(Path(folder))
    require(result['decision'] == 'EXPOSED_ADAPTER_QUALIFICATION_PASS' and
            result['input_manifest_sha256'] == ev.sha(ROOT / 'INPUTS.json') and result['verified_cases'] == 8,
            'Matching frozen adapter qualification required')
    require(result['pricing']['conservative_wall_seconds'] <= D['hard_wall_seconds'], 'Qualification cost gate failed')
    return result


def execute(folder, scope, qualification=None):
    require(scope in ('qualification', 'development'), 'Unknown execution scope')
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    hard = D['qualification_wall_seconds'] if scope == 'qualification' else D['hard_wall_seconds']
    deadline = time.time() + hard
    processes = []

    def expired(*_):
        raise TimeoutError('Fixed development deadline or termination; no retry or extension')

    signal.signal(signal.SIGTERM, expired)
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, hard)
    try:
        for name in ('logs', 'units', 'tmp'):
            (folder / name).mkdir()
        ledger.atomic_json(folder / 'START.json', dict(utc=ev.utc(), pid=os.getpid(), scope=scope,
            deadline_epoch=deadline, hard_wall_seconds=hard, input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'),
            automatic_polling=False, automatic_retry=False, automatic_successor=False, exposure='DEVELOPMENT_ONLY'))
        ev.status(folder, status='RUNNING', stage='source_and_cpu_checks', scope=scope)
        input_count = verify_snapshot()
        ledger.atomic_json(folder / 'SOURCE_CHECK.json', verify_metadata())
        if scope == 'development':
            qualified = verify_qualification(qualification)
            ledger.atomic_json(folder / 'QUALIFICATION_BINDING.json', dict(path=str(qualification),
                complete_sha256=ev.sha(Path(qualification) / 'COMPLETE.json'), pricing=qualified['pricing']))
        sys.path.insert(0, str(ROOT / 'native/inherited/reference'))
        import cpu_preflight
        admission = cpu_preflight.collect()
        admission['planned_threads'] = D['workers'] + 1
        admission['within_limit'] = admission['other_active_or_recently_busy_threads'] + admission['planned_threads'] <= 12
        ledger.atomic_json(folder / 'CPU_ADMISSION.json', admission)
        require(admission['within_limit'], 'Shared CPU budget unavailable; no automatic retry')
        guard = Guard(folder, deadline)
        enrolled = cases()
        selected = enrolled[:8] if scope == 'qualification' else enrolled
        require(len(selected) == (8 if scope == 'qualification' else D['cases']), 'Declared case count differs')
        wave_times = []
        for begin in range(0, len(selected), D['workers']):
            guard.check()
            wave, streams = [], []
            wave_start = time.monotonic()
            try:
                for item in selected[begin:begin + D['workers']]:
                    index = item['index']
                    stream = (folder / 'logs' / f'case_{index:04d}.log').open('xb')
                    streams.append(stream)
                    command = [sys.executable, str(ROOT / 'ec_development.py'), 'worker', '--output', str(folder / 'units' / f'case_{index:04d}'),
                        '--index', str(index), '--deadline', str(deadline)]
                    process = subprocess.Popen(command, cwd=ROOT, env=environment(folder / 'tmp'), stdin=subprocess.DEVNULL,
                        stdout=stream, stderr=subprocess.STDOUT)
                    processes.append(process)
                    wave.append(process)
                wait_wave(wave, deadline)
            finally:
                for stream in streams:
                    stream.close()
            wave_times.append(time.monotonic() - wave_start)
            ev.status(folder, status='RUNNING', scope=scope, stage='direct64_replay',
                completed_cases=min(begin + D['workers'], len(selected)), total_cases=len(selected), early_efficacy_scores=False)
        ev.status(folder, status='RUNNING', scope=scope, stage='complete_saved_evidence_verification')
        source = Source()
        forecasts, payloads, pair = [], [], {}
        for item in selected:
            guard.check()
            unit = folder / 'units' / f"case_{item['index']:04d}"
            committed = ledger.verify(unit, identity(item))
            receipt = read(unit / 'direct64.json')
            raw = ev.load(unit / 'direct64.npz', receipt['raw_sha256'])
            forecast = verify_new(item, raw, receipt, source.case(item))
            require(forecast == read(unit / 'FORECAST.json'), 'Saved new prediction differs')
            forecasts.append(forecast)
            payloads.append(committed['payload'])
            key = tuple(item['row']['key'])
            if item['regime'] == 'matched':
                require(np.array_equal(raw['direct_birth'][:, 0], raw['direct_birth'][:, 1]), 'Matched cue births differ')
                pair[key] = (raw['direct_mask'], raw['direct_birth'][:, 0])
            else:
                masks, births = pair.pop(key)
                require(np.array_equal(masks, raw['direct_mask']) and np.array_equal(births, raw['direct_birth'][:, 0]), 'Regime forcing is not paired')
        require(not pair and sum(v['native_reads'] for v in payloads) == len(selected) * 64 and
                sum(v['flat_native_reads'] for v in payloads) == len(selected) * 2, 'Whole-panel read accounting differs')
        ledger.atomic_json(folder / 'FORECASTS.json', forecasts)
        ledger.atomic_json(folder / 'TIMINGS.json', dict(wave_wall_seconds=wave_times, cases=payloads))
        if scope == 'qualification':
            pricing = qualification_price(wave_times, payloads)
            result = dict(decision='EXPOSED_ADAPTER_QUALIFICATION_PASS', pricing=pricing,
                scope='technical_qualification_on_exposed_packets', efficacy_scores_computed=False)
        else:
            rows = read(ROOT / 'context/FRESH_COHORT.json')['rows']
            outcomes = read(ROOT / 'context/FRESH_OUTCOMES.json')
            scores = analyze(rows, forecasts, outcomes)
            checked = scalar_check(rows, forecasts, outcomes, scores)
            previous = read(ROOT / 'context/FRESH_ANALYSIS.json')
            for regime in D['regimes']:
                for name, old in D['cached_names'].items():
                    require(abs(scores['regimes'][regime]['brier'][name] - previous['regimes'][regime]['brier'][old]) < 1e-12,
                            'Historical forecasts or complete-cohort weighting changed')
            ledger.atomic_json(folder / 'ANALYSIS.json', scores)
            ledger.atomic_json(folder / 'INDEPENDENT_ANALYSIS_CHECK.json', checked)
            historical = read(ROOT / 'context/FRESH_AUDIT.json')['resources']
            costs = dict(new_primary_native_reads=len(selected) * 64, new_flat_native_reads=len(selected) * 2,
                new_worker_cpu_seconds=math.fsum(v['unit_cpu_seconds'] for v in payloads),
                historical_source_study=historical, standalone_native_reads=D['costs']['standalone_native_reads'],
                measured_standalone_benchmark=read(ROOT / 'context/EQUAL_BENCHMARK_RESULTS.json')['models'],
                joint_unique_native_reads_per_packet_regime=128, no_new_fits=True, no_new_future_outcomes=True,
                accounting='New direct64 includes replay of the previous direct8; retain both incurred costs. The128-read union is a future shared-measurement budget, not a discount on historical spend.')
            ledger.atomic_json(folder / 'COSTS.json', costs)
            lines = ['Equal-read comparison on108 already exposed acquisition blocks.', '',
                'Development evidence only. All432 selected packets, both cue-noise regimes and four saved futures were retained. All five archived predictors were frozen; no new fitting or long-horizon outcomes.', '',
                '| Predictor | Native reads | Matched Brier | Independent Brier |', '|---|---:|---:|---:|']
            for name in D['models']:
                lines.append(f"| {name} | {D['costs']['standalone_native_reads'][name]} | {scores['regimes']['matched']['brier'][name]:.9f} | {scores['regimes']['independent']['brier'][name]:.9f} |")
            lines += ['', '| Regime | Rival | Rival minus successor Brier | Descriptive block interval |', '|---|---|---:|---|']
            for regime in D['regimes']:
                for name, value in scores['regimes'][regime]['contrasts'].items():
                    lines.append(f"| {regime} | {name} | {value['mean_gain']:.9f} | [{value['descriptive_lower']:.9f}, {value['descriptive_upper']:.9f}] |")
            lines += ['', 'Positive differences favor successor32. Intervals describe exposed development blocks; they do not supply a new prospective or simultaneous confidence claim. Block loss vectors and covariance are retained for later precision planning.', '',
                f"New work used{costs['new_primary_native_reads']:,} primary reads and{costs['new_flat_native_reads']:,} flat audit reads; worker CPU{costs['new_worker_cpu_seconds']:.1f}s. Historical acquisition, probe and continuation costs remain in COSTS.json. Standalone CPU timings for each rival are retained from the native benchmark; equal native reads do not imply equal total cost.", '',
                'Every new direct8 prefix matched its original raw evidence exactly, and every first32 evaluation forcing commitment matched. Separate flat dynamics at0 and32, scalar endpoints/probabilities, paired regime injuries and base cues, full saved-file hashes, and separate scalar block scoring all passed.', '',
                D['claim_boundary'], '', 'No automatic follow-up. A fresh test requires a justified precision and runtime plan, frozen before new outcomes. Repair scheduling still requires evidence for paired repair benefit.', '']
            (folder / 'REPORT.md').write_text('\n'.join(lines))
            result = dict(decision='EXPOSED_EQUAL_READ_DEVELOPMENT_COMPLETE', scope='EXPOSED_DEVELOPMENT_ONLY',
                inferential_verdict='NO_NEW_CONFIRMATORY_VERDICT', independent_analysis_check=checked)
        guard.check()
        verify_snapshot()
        verify_metadata()
        result.update(verified_cases=len(selected), input_files_verified=input_count,
            input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json'), primary_native_reads=len(selected) * 64,
            flat_native_reads=len(selected) * 2, new_fits=0, new_scientific_outcomes=0,
            wall_seconds=time.monotonic() - start, automatic_retry=False, automatic_successor=False)
        complete(folder, result)
        print(dict(decision=result['decision'], verified_cases=len(selected), wall_seconds=result['wall_seconds']), flush=True)
    except BaseException as error:
        stop(processes)
        ledger.atomic_json(folder / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        ev.status(folder, status='FAILED', scope=scope, automatic_retry=False, partial_inference=False)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def launch(job, name, scope, qualification=None):
    job = Path(job).resolve()
    require(job.is_relative_to(ROOT / 'jobs') and name.replace('_', '').isalnum(), 'Local unique job and run required')
    inputs = job / 'inputs'
    require(manifest(inputs, ('INPUTS.json',)) == read(inputs / 'INPUTS.json')['sha256'], 'Frozen inputs changed')
    require(read(inputs / 'DEVELOPMENT.json') == D, 'Frozen development contract changed')
    output, receipt = ROOT / 'runs' / name, job / (name + '_LAUNCH.json')
    require(not output.exists() and not receipt.exists(), 'Never overwrite or retry a run')
    if scope == 'development':
        q = verify_complete(Path(qualification))
        require(q['decision'] == 'EXPOSED_ADAPTER_QUALIFICATION_PASS' and
                q['input_manifest_sha256'] == ev.sha(inputs / 'INPUTS.json') and q['pricing']['conservative_wall_seconds'] <= D['hard_wall_seconds'],
                'Matching successful cost and numerical qualification required')
    command = [sys.executable, str(inputs / 'ec_development.py'), 'run', '--scope', scope, '--output', str(output)]
    if qualification is not None:
        command += ['--qualification', str(Path(qualification).resolve())]
    logfile = job / (name + '.log')
    with logfile.open('xb') as stream:
        process = subprocess.Popen(command, cwd=inputs, env=environment(job / (name + '_tmp')),
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    result = dict(utc=ev.utc(), pid=process.pid, command=command, run=str(output), log=str(logfile),
        input_manifest_sha256=ev.sha(inputs / 'INPUTS.json'), scope=scope,
        hard_wall_seconds=D['hard_wall_seconds'] if scope == 'development' else D['qualification_wall_seconds'],
        detached=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    ledger.atomic_json(receipt, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['freeze', 'launch', 'run', 'worker'])
    parser.add_argument('--scope', choices=['qualification', 'development'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--name')
    parser.add_argument('--index', type=int)
    parser.add_argument('--deadline', type=float)
    args = parser.parse_args()
    if args.mode == 'freeze':
        from ec_manage import freeze
        print(freeze(args.name, 'development'))
    elif args.mode == 'launch':
        print(launch(args.job, args.name, args.scope, args.qualification))
    elif args.mode == 'run':
        execute(args.output, args.scope, args.qualification)
    else:
        worker(args.output, args.index, args.deadline)
