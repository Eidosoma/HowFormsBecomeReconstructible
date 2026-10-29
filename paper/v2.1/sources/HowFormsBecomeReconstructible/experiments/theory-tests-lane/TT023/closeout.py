"""Saved-evidence closeout, written after completion and before effect inspection.

Does not integrate trajectories, modify the completed run, or extend the panel.
Uses the frozen custody/score checks and regenerates every planned summary.
"""
import time
import traceback
from common import *
import analysis
import design
import execute
import run


def main():
    destination = ROOT / 'checks/closeout_v1'
    destination.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    completed_path = ROOT / 'runs/counterfactual_v1/COMPLETE.json'
    directory = completed_path.parent
    try:
        frozen = read_json(ROOT / 'FREEZE.json')
        complete = read_json(completed_path)
        original_files = dict(complete['outputs'])
        original_files[str(completed_path)] = sha(completed_path)
        assert complete['status'] == 'COMPLETE' and complete['role'] == 'development'
        assert not (directory / 'FAILED.json').exists()
        assert complete['inputs'] == frozen['inputs'] == runtime_hashes()
        assert complete['environment'] == frozen['environment'] == execute.environment()
        assert complete['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
        verify(frozen['inputs']); verify(frozen['evidence']); verify(original_files)
        assert {str(p) for p in directory.rglob('*') if p.is_file()} == set(original_files)
        assert source_check() == 289 and baseline_check() == 44
        assert complete['blocks'] == frozen['blocks'] == list(BLOCKS)
        write_json(destination / 'ORIGINAL_FILES.json', original_files)
        write_json(destination / 'RUNNING.json', dict(started_utc=now(),
            trigger='USER_STATUS_REQUEST', outcome_effects_inspected_before_closeout=False,
            code_sha256=sha(__file__), new_dynamics=0))
        block_checks = {}
        acquisition = []
        for index in BLOCKS:
            path = directory / f'tissue_{index}'
            block_checks[str(index)] = run.saved_check(path)
            acquisition.append(read_json(path / 'CHECK.json'))
        saved = {key: sum(v[key] for v in block_checks.values())
                 for key in ('arrays', 'records', 'packet_handoffs', 'new_dynamics')}
        assert saved == complete['saved_verification'] == dict(
            arrays=6528, records=3072, packet_handoffs=192, new_dynamics=0)
        fields = ('arm_batches', 'new_repairs', 'new_reads', 'retained_repairs',
                  'reused_read_slots', 'native_arrays')
        native = {key: sum(v[key] for v in acquisition) for key in fields}
        assert all(v['status'] == 'PASS' and v['max_native_error'] == 0. for v in acquisition)
        native['max_native_error'] = 0.
        assert native == complete['verification'] == dict(arm_batches=192,
            new_repairs=128, new_reads=64, retained_repairs=64, reused_read_slots=128,
            native_arrays=2304, max_native_error=0.)
        summary = analysis.summary(directory, 'development')
        assert serialized(summary) == (directory / 'SUMMARY.json').read_bytes()
        assert analysis.report(read_json(directory / 'SUMMARY.json')) == (directory / 'REPORT.md').read_text()
        assert analysis.report(summary) == (directory / 'REPORT.md').read_text()
        for family in design.FAMILIES:
            arms = summary['families'][family]['arms']
            for arm in design.ARMS:
                assert arms[arm]['n'] == 256 and len(arms[arm]['by_record']) == 64
                assert len(arms[arm]['by_block']) == 4
                assert sum(v['n'] for v in arms[arm]['by_message'].values()) == 256
                assert sum(v['n'] for v in arms[arm]['by_injury'].values()) == 256
            for record in arms['full_off']['by_record']:
                assert len({arms[a]['by_record'][record]['recipient']
                            for a in ('full_off', 'subtract_off', 'zero_off')}) == 1
        verify(frozen['inputs']); verify(frozen['evidence']); verify(original_files)
        receipt = dict(status='PASS', study='TT023', completed_utc=now(),
            seconds=time.monotonic()-tick, code=str(Path(__file__).resolve()), code_sha256=sha(__file__),
            written_after_acquisition=True, written_before_effect_inspection=True,
            new_dynamics=0, new_receiving_assays=0, original_run_unchanged=True,
            original_run_status='COMPLETE', run_completion=str(completed_path),
            run_completion_sha256=sha(completed_path), freeze_sha256=sha(ROOT / 'FREEZE.json'),
            frozen_inputs=len(frozen['inputs']), frozen_evidence=len(frozen['evidence']),
            original_run_files=len(original_files), source_files=289, baseline_batches=44,
            saved_verification=saved, retained_acquisition_verification=native,
            summary_sha256=sha(directory / 'SUMMARY.json'), report_sha256=sha(directory / 'REPORT.md'),
            summary_byte_identical=True, report_byte_identical=True,
            all_arms_and_strata_retained=True, shared_off_controls_verified=True,
            scientific_classification=summary['classification'],
            fresh_population_confirmation=False, significance_verdict=False,
            outputs={str(p):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        write_json(destination / 'COMPLETE.json', receipt)
        write_json(ROOT / 'CLOSEOUT.json', receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k != 'outputs'}, sort_keys=True), flush=True)
    except BaseException as error:
        write_json(destination / 'FAILED.json', dict(status='FAILED', failed_utc=now(),
            error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == '__main__':
    main()
