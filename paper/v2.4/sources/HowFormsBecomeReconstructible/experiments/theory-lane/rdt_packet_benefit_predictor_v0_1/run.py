"""Small development calculation; no native simulation or automatic successor."""
import argparse
import json
from pathlib import Path
import resource
import signal
import time
import traceback
import core
import scalar_audit as audit
import data
from data import ev, read


def report(result, source, elapsed):
    names = {'candidate': 'Packet + proposed repair response', 'packet_blind': 'Packet without repair response',
        'ordinary_risk': 'Benefit from TT008 risk', 'direct_risk': 'Benefit from direct-probe risk',
        'successor_risk': 'Benefit from successor-probe risk', 'zero': 'Zero benefit', 'regime_mean': 'Mean benefit by noise regime'}
    lines = ['**Cheap packet-only repair-benefit predictor: development screen.**', '',
        '**' + result['decision'] + '**. ' + result['interpretation'], '',
        'The target is the observed paired terminal difference, repaired minus unrepaired, including harms. The candidate has three standardized inputs: noise condition, original signed 64-step transfer and the repair-induced change in that transfer. One ridge penalty of1 was fixed before this calculation; there was no feature or penalty search. Task rule and port geometry are supplied equally to the comparison. Whole acquisition blocks, including both regimes and all related records, were excluded together; scaling and fitting use training blocks only.', '',
        'The table reports held-out-block mean squared error of the paired difference, not ordinary binary-outcome Brier scores. Lower is better. The family and procedure were chosen after inspecting earlier outcomes, so these are development diagnostics even though each fitted model excludes its test block. Overlapping training folds do not supply independent replications or a confirmatory confidence interval.', '',
        '| Benefit predictor | Matched MSE | Independent MSE | Extra full native probes per case/regime |',
        '|---|---:|---:|---:|']
    for model in core.MODELS:
        lines.append(f"| {names[model]} | {result['regimes']['matched']['scores'][model]:.8f} | {result['regimes']['independent']['scores'][model]:.8f} | {core.P['costs']['extra_native_probes'][model]} |")
    lines += ['', 'Advance requires strictly lower candidate error than every comparator in both noise conditions. Equality fails. This is a research-spending gate, not an effect-size or significance claim. A failed version is retained without retuning it after inspection.', '',
        '| Noise | Comparator | Comparator minus candidate MSE | Candidate better |', '|---|---|---:|---|']
    for regime in core.REGIMES:
        for model, row in result['regimes'][regime]['comparator_gains'].items():
            lines.append(f"| {regime} | {names[model]} | {row['mean_gain']:.8f} | {row['candidate_better']} |")
    lines += ['', 'Offline action diagnostics apply the repair only when the out-of-block benefit prediction is strictly positive. The already observed two branches supply the diagnostic outcome. The threshold was not selected from outcomes. Repair-every-case and no repair remain explicit baselines. These points consume different resources: the table is not an equal-full-budget policy competition, a cost-optimal rule or a sequential scheduler test.', '',
        '| Noise | Rule | Weighted terminal success | Applied repairs | Extra native probes | Deployment optimizer calls |',
        '|---|---|---:|---:|---:|---:|']
    for regime in core.REGIMES:
        for model in ('no_repair', 'repair_all', *core.MODELS):
            q = result['regimes'][regime]['policies'][model]
            name = names.get(model, model)
            lines.append(f"| {regime} | {name} | {q['weighted_terminal_success']:.6f} | {q['applied_repairs']} | {q['extra_native_probe_reads']} | {q['total_deployment_optimizer_calls']} |")
    lines += ['', f"All 63 original/repaired packet pairs were checked against their pre-future action seal and independently evaluated for signed transfer. The two transfer calculations used {source['feature_cpu_seconds']:.6f}s CPU, plus {source['feature_audit_cpu_seconds']:.6f}s for separate transfer checks. Previously measured repair computation used {source['prior_physical_repair_cpu_seconds']:.6f}s across63 unique packets. Those timings are separate observations, not a measured combined deployment latency.", '',
        'The candidate must compute a dry-run repair for every packet, including packets for which it later declines intervention. Reuse that computed repair if selected; do not omit the preparation cost or charge a second solve unnecessarily. Ordinary/direct/successor risk comparators also use the same available boundary information and previously frozen forecasting apparatus. Extra full probes are0,8,64 respectively. Shared boundary acquisition, transfer, model fitting/scaling and inference are not free. Dry-run computation, applied repair, stored apparatus and edge changes are distinct resources.', '',
        'The source contains only thirteen discordant record/regime pairs from sixteen selected blocks. Repeated noise conditions for one packet do not create independent founders. All inputs, folds, model coefficients, held-out predictions, block losses and action diagnostics are retained. Separate scalar normal equations, elimination, predictions and weighted reductions check the NumPy implementation. These checks do not constitute independent laboratory replication.', '',
        f"Development calculation completed in {elapsed:.2f}s. No new native reads, paired futures or scientific runs were generated. The final all-development-data models are archived for reproducibility; an archived model does not imply permission or qualification to use it on a new study.", '']
    if result['advance_gate_pass']:
        lines += ['The spending gate passes. Before new-founder acquisition, freeze a separate test contract, measure its complete runtime and qualify its implementation. Prefer a one-hour cap. No such run is launched automatically by this calculation.', '']
    else:
        lines += ['The spending gate fails. This candidate is not advanced to a new-founder simulation. The result limits this compact reduction; it does not establish that repair benefit is unlearnable or that a favorable subgroup can rescue the candidate. The source pilot remains unresolved and its harms are retained. A revised hypothesis must receive a new version and be identified as outcome-informed development.', '']
    lines += ['This uses conventional graph transfer and regression; no RDT-specific predictive law or endogenous maintenance claim is established.', '']
    return '\n'.join(lines)


def work(output):
    output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    def timeout(*_):
        raise TimeoutError('Development calculation exceeded its fixed five-minute ceiling')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(core.P['resources']['development_cap_seconds'])
    try:
        manifest = read(core.ROOT / 'INPUTS.json')
        data.verify_files(core.ROOT, manifest['sha256'], ('INPUTS.json',))
        ev.write(output / 'START.json', dict(utc=ev.utc(), input_manifest_sha256=ev.sha(core.ROOT / 'INPUTS.json')))
        ev.status(output, status='RUNNING', stage='source_and_feature_checks')
        records, source = data.prepare(output)
        folds, predictions = {}, []
        for block in core.P['blocks']:
            folds[str(block)], p = core.fold(records, block)
            predictions.extend(p)
        result = core.evaluate(records, predictions)
        checked = audit.evaluate(records, folds, predictions, result)
        final = {name: core.fit(records, name) for name in core.MODELS}
        for name, state in final.items(): audit.check_fit(records, name, state)
        ev.write(output / 'FOLD_MODELS.json', folds)
        ev.write(output / 'OUT_OF_BLOCK_PREDICTIONS.json', predictions)
        ev.write(output / 'ANALYSIS.json', result)
        ev.write(output / 'VERIFICATION.json', checked)
        ev.write(output / 'FINAL_MODELS.json', dict(scope='Archived all-development-data models; advancement depends on the separate gate.', models=final))
        with (output / 'REPORT.md').open('x') as stream:
            stream.write(report(result, source, time.monotonic() - start))
        data.verify_files(core.ROOT, manifest['sha256'], ('INPUTS.json',))
        outputs = {str(p.relative_to(output)): ev.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'STATUS.json'}
        ev.write(output / 'OUTPUTS.json', dict(sha256=outputs))
        complete = dict(utc=ev.utc(), status='COMPLETE', decision=result['decision'],
            advance_gate_pass=result['advance_gate_pass'], wall_seconds=time.monotonic() - start,
            cpu_seconds=time.process_time() - cpu, peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            records=63, paired_records=126, blocks=16, fitted_fold_models=112, archived_final_models=7,
            independent_scalar_audit=True, new_native_reads=0, new_future_outcomes=0,
            input_manifest_sha256=ev.sha(core.ROOT / 'INPUTS.json'), output_manifest_sha256=ev.sha(output / 'OUTPUTS.json'),
            automatic_successor=False)
        ev.write(output / 'COMPLETE.json', complete)
        ev.status(output, status='COMPLETE', stage='complete')
        print(dict(status='COMPLETE', decision=complete['decision'], wall_seconds=complete['wall_seconds']), flush=True)
    except BaseException as error:
        ev.write(output / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        ev.status(output, status='FAILED', stage='failed')
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    work(parser.parse_args().output)
