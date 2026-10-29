"""Exclusive bounded two-arm pilot, with a whole-panel pre-future seal."""
import argparse
import os
from pathlib import Path
import resource
import shutil
import signal
import time
import traceback
import numpy as np
from study import ROOT, C, ARMS, REGIMES, ev, read, digest, require, ledger, cached_runner, verify_snapshot, admission
import actions
import paired
import analysis
import verify


class Guard:
    def __init__(self, folder, seconds):
        self.folder = folder
        self.end = time.monotonic() + seconds
        self.next_check = 0.

    def check(self):
        now = time.monotonic()
        if now >= self.end:
            raise TimeoutError('One-hour paired pilot deadline; no automatic extension')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > C['resources']['maximum_resident_bytes']:
            raise MemoryError('Resident-memory limit exceeded')
        if now >= self.next_check:
            if shutil.disk_usage(self.folder).free < C['resources']['minimum_free_disk_bytes']:
                raise OSError('Insufficient free disk')
            if sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file()) > C['resources']['maximum_saved_bytes']:
                raise OSError('Evidence size limit exceeded')
            self.next_check = now + 20


def work(folder, rows, forecasts, packets, guard, binding, stage='pilot', event=lambda *_: None):
    blocks, _, _ = analysis.scoring_pilot.validate(rows, forecasts)
    require(len(rows) == len(packets), 'Complete packets required before action seal')
    guard.check()
    initial, repair_receipts, repair_details = actions.prepare(rows, packets)
    action_sha = ev.save(folder / 'ACTIONS.npz', dict(initial_packets=initial, **repair_details))
    ev.write(folder / 'ACTIONS.json', repair_receipts)
    seal = folder / 'PANEL_SEAL.json'
    ledger.atomic_json(seal, dict(utc=ev.utc(), input_binding=binding, stage=stage, records=len(rows),
        case_regimes=len(forecasts), rows=rows, forecasts=forecasts, arms=list(ARMS),
        action_arrays_sha256=action_sha, action_receipts_sha256=ev.sha(folder / 'ACTIONS.json'),
        all_actions_and_forecasts_checked_before_any_future=True,
        branch_packet_sha256=[[digest(a) for a in case] for case in initial]))
    seal_sha = ev.sha(seal)
    references = []
    for block in blocks:
        indices = [i for i, r in enumerate(rows) if r['block'] == block]
        selected = [rows[i] for i in indices]
        require(1 <= len(selected) <= 4, 'At most four records per paired batch')
        audit_key = min(selected, key=lambda r: r['selection_hash'])['key']
        for regime in REGIMES:
            guard.check()
            target = folder / 'futures' / f'block_{block:06d}_{regime}'
            target.mkdir(parents=True)
            receipt, outcomes = paired.batch(selected, initial[indices], audit_key, regime, stage, target, guard, seal, seal_sha)
            checked = verify.continuation(target, selected, initial[indices], regime, stage, seal_sha, audit_key)
            ev.write(target / 'VERIFICATION.json', checked)
            identity = dict(binding=binding, block=block, regime=regime, keys=[r['key'] for r in selected], seal_sha256=seal_sha)
            ledger.commit(target, identity, dict(outcomes=outcomes, primary_native_reads=receipt['primary_native_reads'], flat_native_reads=receipt['flat_native_reads']))
            references.append(dict(reference=ledger.reference(folder, target), indices=indices, audit_key=audit_key, identity=identity))
            event('paired_batch_committed', dict(block=block, regime=regime, completed_batches=len(references), total_batches=2 * len(blocks)))
    outcomes = []
    for ref in references:
        target, committed = ledger.referenced(folder, ref['reference'], ref['identity'])
        labels = read(target / 'OUTCOMES.json')
        require(labels == committed['payload']['outcomes'], 'Committed labels differ')
        indices = ref['indices']
        verify.continuation(target, [rows[i] for i in indices], initial[indices], ref['identity']['regime'], stage, seal_sha, ref['audit_key'])
        outcomes.extend(labels)
    require(ev.sha(seal) == seal_sha and ev.sha(folder / 'ACTIONS.npz') == action_sha, 'Seal or action changed')
    result = analysis.analyze(rows, forecasts, outcomes)
    independent = verify.evaluate(rows, forecasts, outcomes, result)
    ev.write(folder / 'FUTURE_REFERENCES.json', [r['reference'] for r in references])
    ev.write(folder / 'ANALYSIS.json', result)
    ev.write(folder / 'VERIFICATION.json', independent)
    costs = dict(primary_native_reads=38 * len(outcomes), flat_native_reads=76 * len(blocks),
        physical_repair_calls=len(rows), logical_repair_calls=len(outcomes),
        repair_cpu_seconds=sum(r['repair_cpu_seconds'] for r in repair_receipts),
        optimizer_audit_cpu_seconds=sum(r['optimizer_audit_cpu_seconds'] for r in repair_receipts),
        physical_added_edges=sum(r['added_edges'] for r in repair_receipts),
        logical_added_edges=2 * sum(r['added_edges'] for r in repair_receipts),
        logical_added_absolute_weight=2 * sum(r['added_absolute_weight'] for r in repair_receipts),
        new_acquisition_reads=0, new_probe_reads=0, new_model_fits=0)
    ev.write(folder / 'RESOURCES.json', costs)
    with (folder / 'REPORT.md').open('x') as stream:
        stream.write(analysis.report(result, costs))
    return dict(signal=result['signal'], records=len(rows), blocks=len(blocks), case_regimes=len(outcomes),
        **costs, panel_seal_sha256=seal_sha, independent_analysis=True)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    def expired(*_):
        raise TimeoutError('One-hour hard deadline; no automatic retry')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(C['resources']['hard_wall_seconds'])
    try:
        ev.write(output / 'START.json', dict(utc=ev.utc(), pid=os.getpid(), hard_wall_seconds=C['resources']['hard_wall_seconds'], input_manifest_sha256=ev.sha(ROOT / 'INPUTS.json')))
        ev.status(output, status='RUNNING', stage='verification_and_admission')
        verified = verify_snapshot()
        for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
            require(os.environ.get(name) == '1', 'One numerical thread required')
        qualification = read(ROOT / 'QUALIFICATION.json')
        require(qualification['status'] == 'PASS' and qualification['forecast_seconds'] < 3600, 'Passing measured qualification required')
        admitted = admission()
        ev.write(output / 'CPU_ADMISSION.json', admitted)
        require(admitted['within_limit'], 'Shared CPU budget full; no retry')
        guard = Guard(output, max(0., C['resources']['hard_wall_seconds'] - (time.monotonic() - start)))
        rows, forecasts, packets = cached_runner.check_cache()
        require(len(rows) == 63 and len(forecasts) == 126 and sorted({r['block'] for r in rows}) == C['cohort']['blocks'], 'Wrong selected cohort')
        def event(stage, details):
            guard.check()
            ev.status(output, status='RUNNING', stage=stage, details=details)
        result = work(output, rows, forecasts, packets, guard, ev.sha(ROOT / 'INPUTS.json'), event=event)
        require(result['primary_native_reads'] == C['costs']['primary_future_reads'] and result['flat_native_reads'] == C['costs']['flat_future_reads'], 'Frozen read budget changed')
        verify_snapshot(); guard.check()
        hashes = {str(p.relative_to(output)): ev.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'STATUS.json'}
        ev.write(output / 'OUTPUTS.json', dict(sha256=hashes))
        complete = dict(utc=ev.utc(), status='COMPLETE', **result, wall_seconds=time.monotonic() - start,
            cpu_seconds=time.process_time() - cpu, peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            input_files_verified=verified, output_manifest_sha256=ev.sha(output / 'OUTPUTS.json'),
            automatic_successor=False, claim_scope=C['scope'])
        ledger.atomic_json(output / 'COMPLETE.json', complete)
        ev.status(output, status='COMPLETE', stage='complete')
        print(dict(status='COMPLETE', signal=result['signal'], wall_seconds=complete['wall_seconds']), flush=True)
    except BaseException as error:
        ledger.atomic_json(output / 'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        ev.status(output, status='FAILED', stage='failed')
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
