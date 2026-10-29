"""Finish verification of retained TT028 evidence after a report-order failure.

Written after acquisition and before scientific effect inspection. The frozen
experiment, failed execution directory, values, inference and report stay intact.
Only the report's claim traversal order is restored from the frozen design.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os
from pathlib import Path
import signal
import time
import traceback

from common import *
import analysis
import design
import execute
import inference
import run

JOB = ROOT/'runs/confirmation_v1'
DESTINATION = ROOT/'checks/closeout_v1'
PLAN = ROOT/'SAVED_CLOSEOUT_PLAN.json'


def registered_report(value):
    """Restore declared claim order without changing any field or numeric value."""
    fixed = dict(value)
    registered = dict(value['registered_inference'])
    assert set(registered['claims']) == set(design.claims())
    registered['claims'] = {name: registered['claims'][name] for name in design.claims()}
    fixed['registered_inference'] = registered
    assert serialized(fixed) == serialized(value)
    return analysis.report(fixed)


def worker(indices, cpu):
    os.sched_setaffinity(0, {cpu})
    os.nice(10)
    write_json(DESTINATION/f'worker_{cpu}.json', dict(
        started_utc=now(), pid=os.getpid(), parent_pid=os.getppid(), cpu=cpu,
        numerical_threads=1, blocks=list(indices), new_dynamics=0))
    result = {}
    for index in indices:
        tick = time.monotonic()
        directory = JOB/f'tissue_{index}'
        proof = run.saved(directory)
        assert proof == read_json(directory/'SAVED_CHECK.json')
        assert proof['status'] == 'PASS' and proof['new_dynamics'] == 0
        rebuilt, conditional = analysis.block_summary(directory, 'confirmation')
        assert serialized(rebuilt) == (directory/'SUMMARY.json').read_bytes()
        assert serialized(conditional) == (directory/'CONDITIONAL.json').read_bytes()
        assert len(conditional) == design.expected('confirmation', 1)['body_rows']
        assert all(v['draws'] == 8 and len(v['individual_draws']) == 8 and
                   v['pointwise_conditional_uncertainty']['independent_receiving_draws'] == 8
                   for v in conditional)
        receipt = dict(status='PASS', block=index, checked_utc=now(),
            seconds=time.monotonic()-tick, saved=proof,
            summary_byte_identical=True, conditional_byte_identical=True,
            conditional_pairs=len(conditional), new_dynamics=0,
            new_receiving_assays=0, scientific_effects_displayed=False)
        write_json(DESTINATION/f'block_{index}.json', receipt)
        result[str(index)] = receipt
        print(json.dumps(dict(stage='saved_block_verified', block=index,
                              new_dynamics=0)), flush=True)
    return result


def verify_panel(value):
    assert value['role'] == 'confirmation' and value['blocks'] == list(BLOCKS)
    assert value['population_units'] == 64
    assert value['primary'] == design.PRIMARY
    assert value['independent_corruptions'] == 2 and value['new_draws_per_packet'] == 8
    assert value['developed_bodies_per_starting_record'] == 1
    assert value['registered_inference'] == inference.results(value)
    assert value['registered_inference']['per_claim_alpha'] == .05/3
    base_endpoints = {'receiving', 'damage_effect', 'receiving_vs_original',
        'receiving_vs_full', 'receiving_donor_shift', 'body_vs_preservation',
        'body_vs_full', 'body_donor_minus_target'}
    for family in design.FAMILIES:
        assert set(value['panel'][family]) == set(design.DAMAGE)
        for damage in design.DAMAGE:
            assert set(value['panel'][family][damage]) == set(design.BODIES)
            for body in design.BODIES:
                arms = value['panel'][family][damage][body]
                assert set(arms) == set(design.arms(body))
                for arm, endpoints in arms.items():
                    expected = base_endpoints | ({'receiving_vs_foreign', 'receiving_vs_neutral'}
                        if arm in (design.PRESERVE, design.FULL) else set())
                    assert set(endpoints) == expected
                    for endpoint, groups in endpoints.items():
                        n = 2048 if endpoint.startswith('body_') else 16384
                        overall = groups['overall']
                        assert overall['n'] == n and len(overall['record_means']) == 1024
                        assert set(overall['blocks']) == {str(i) for i in BLOCKS}
                        assert sum(overall['pair_changes'].values()) == n
                        assert sum(overall['record_changes'].values()) == 1024
                        for group in ('messages', 'injury_strata', 'developed_status', 'source_body_status'):
                            assert sum(v['n'] for v in groups[group].values()) == n
    assert value['verification'] == dict(status='PASS', paired_rows=884736,
        body_rows=110592, zero_preservation_rows=294912,
        exact_comparator_row_references=True, unmeasured_source_comparisons_not_imputed=True,
        receiving_draws_not_counted_as_body_replicates=True)


def main():
    plan = read_json(PLAN)
    DESTINATION.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    def expire(*_):
        raise TimeoutError('TT028 saved closeout deadline exceeded')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(plan['deadline_seconds'])
    pool = None
    try:
        verify(plan['code_and_evidence'])
        frozen = read_json(ROOT/'FREEZE.json')
        assert runtime_hashes() == frozen['inputs']
        assert execute.environment() == frozen['environment']
        assert set(execute.environment()['numerical_threads'].values()) == {'1'}
        assert sorted(os.sched_getaffinity(0)) == plan['cpus']
        verify(frozen['inputs']); verify(frozen['evidence']); evidence_check()
        assert source_check() == 289
        assert frozen['blocks'] == list(BLOCKS)
        assert frozen['claims'] == design.claims()
        assert read_json(JOB/'RUNNING.json')['inputs'] == frozen['inputs']
        assert read_json(JOB/'FAILED.json')['status'] == 'FAILED'
        assert not (JOB/'COMPLETE.json').exists()
        write_json(DESTINATION/'RUNNING.json', dict(status='RUNNING', started_utc=now(),
            pid=os.getpid(), role='SAVED_EVIDENCE_CLOSEOUT', workers=2, cpus=plan['cpus'],
            numerical_threads=1, deadline_seconds=plan['deadline_seconds'],
            plan_sha256=sha(PLAN), freeze_sha256=sha(ROOT/'FREEZE.json'),
            original_run_status='FAILED', scientific_effects_inspected=False,
            new_dynamics=0, new_receiving_assays=0, automatic_polling=False,
            automatic_retry=False, automatic_successor=False))
        fd = os.environ.pop('TT028_CLOSEOUT_READY_FD', None)
        if fd is not None:
            os.write(int(fd), b'READY\n'); os.close(int(fd))
        original = {str(p): sha(p) for p in sorted(JOB.rglob('*')) if p.is_file()}
        assert len(original) == plan['original_file_count']
        retained = sum(Path(p).stat().st_size for p in original)
        assert retained == plan['original_bytes'] and retained < frozen['run_byte_limit']
        write_json(DESTINATION/'ORIGINAL_FILES.json', original)
        checks = [read_json(JOB/f'tissue_{i}/CHECK.json') for i in BLOCKS]
        expected = design.expected('confirmation', 64)
        assert expected == frozen['planned_verification']
        assert all(v['status'] == 'PASS' for v in checks)
        acquisition = {k: sum(v[k] for v in checks) for k in expected}
        assert acquisition == expected
        pool = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'))
        pending = [pool.submit(worker, BLOCKS[offset::2], cpu) for offset, cpu in enumerate(plan['cpus'])]
        results = {}
        for task in as_completed(pending):
            results.update(task.result())
        pool.shutdown(wait=True); pool = None
        assert set(results) == {str(i) for i in BLOCKS}
        saved = {k: sum(v['saved'][k] for v in results.values()) for k in
            ('arrays', 'paired_rows', 'body_rows', 'distinct_receiving_environments', 'baseline_saved_arrays', 'new_dynamics')}
        assert saved == dict(arrays=864192, paired_rows=884736, body_rows=110592,
            distinct_receiving_environments=1024, baseline_saved_arrays=7360, new_dynamics=0)
        summary = analysis.summary(JOB, 'confirmation')
        assert serialized(summary) == (JOB/'SUMMARY.json').read_bytes()
        assert serialized(summary['conditional_index']) == (JOB/'CONDITIONAL_INDEX.json').read_bytes()
        assert len(summary['conditional_index']) == 64
        assert sum(v['pairs'] for v in summary['conditional_index']) == 110592
        for row in summary['conditional_index']:
            assert sha(row['path']) == row['sha256']
        verify_panel(summary)
        original_report = (JOB/'REPORT.md').read_text()
        reloaded = read_json(JOB/'SUMMARY.json')
        assert analysis.report(summary) == registered_report(summary) == original_report
        assert registered_report(reloaded) == original_report
        assert sorted(analysis.report(reloaded).splitlines()) == sorted(original_report.splitlines())
        verify(frozen['inputs']); verify(frozen['evidence']); verify(plan['code_and_evidence'])
        verify(original)
        assert {str(p) for p in JOB.rglob('*') if p.is_file()} == set(original)
        receipt = dict(status='PASS', study='TT028', completed_utc=now(), seconds=time.monotonic()-tick,
            plan_sha256=sha(PLAN), code_sha256=sha(__file__), freeze_sha256=sha(ROOT/'FREEZE.json'),
            original_run_status='FAILED', original_run_unchanged=True,
            original_failure_sha256=sha(JOB/'FAILED.json'), original_files=len(original), retained_bytes=retained,
            frozen_inputs=len(frozen['inputs']), frozen_evidence=len(frozen['evidence']), source_files=289,
            blocks=list(BLOCKS), workers=2, cpus=plan['cpus'], numerical_threads=1,
            saved_verification=saved, retained_acquisition_verification=acquisition,
            summary_verification=summary['verification'], conditional_pairs=110592,
            summary_sha256=sha(JOB/'SUMMARY.json'), report_sha256=sha(JOB/'REPORT.md'),
            conditional_index_sha256=sha(JOB/'CONDITIONAL_INDEX.json'),
            summary_byte_identical=True, all_conditional_files_byte_identical=True,
            original_report_recovered_by_registered_claim_order_only=True,
            report_row_order_failure_preserved=True, no_numeric_or_inference_change=True,
            all_cases_preservation_paired_harms_and_source_controls_retained=True,
            written_after_acquisition=True, written_before_effect_inspection=True,
            scientific_effects_displayed_or_interpreted=False, fresh_population_confirmation=True,
            new_dynamics=0, new_receiving_assays=0, serial_endpoint=False,
            automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False,
            outputs={str(p): sha(p) for p in sorted(DESTINATION.rglob('*')) if p.is_file()})
        write_json(DESTINATION/'COMPLETE.json', receipt)
        write_json(ROOT/'CLOSEOUT.json', receipt)
        signal.alarm(0)
        print(json.dumps({k: v for k, v in receipt.items() if k not in ('outputs', 'blocks')}, sort_keys=True), flush=True)
    except BaseException as error:
        if pool is not None:
            for process in list((pool._processes or {}).values()):
                process.terminate()
            pool.shutdown(wait=True, cancel_futures=True)
        write_json(DESTINATION/'FAILED.json', dict(status='FAILED', failed_utc=now(),
            error=repr(error), traceback=traceback.format_exc(), automatic_retry=False,
            new_dynamics=0, original_run_unchanged=True))
        raise


if __name__ == '__main__':
    main()
