"""Saved-evidence closeout, written after acquisition before effect inspection.

Checks custody, packet routes, saved receiving states, scores and every summary.
No trajectories are integrated and the acquired run remains immutable.
"""
import time
import traceback
from common import *
import analysis
import design
import execute
import run


def main():
    destination = ROOT/'checks/closeout_v1'
    destination.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    complete_path = ROOT/'runs/paired_v1/COMPLETE.json'
    directory = complete_path.parent
    try:
        frozen = read_json(ROOT/'FREEZE.json')
        complete = read_json(complete_path)
        original_files = dict(complete['outputs'])
        original_files[str(complete_path)] = sha(complete_path)
        write_json(destination/'RUNNING.json', dict(started_utc=now(),
            trigger='USER_CONTINUE_REQUEST', outcome_effects_inspected_before_closeout=False,
            written_after_acquisition=True, code_sha256=sha(__file__), new_dynamics=0))
        assert complete['status'] == 'COMPLETE' and complete['role'] == 'development'
        assert not (directory/'FAILED.json').exists()
        assert complete['inputs'] == frozen['inputs'] == runtime_hashes()
        assert complete['environment'] == frozen['environment'] == execute.environment()
        assert complete['freeze_sha256'] == sha(ROOT/'FREEZE.json')
        verify(frozen['inputs']); verify(frozen['evidence']); verify(original_files)
        assert {str(p) for p in directory.rglob('*') if p.is_file()} == set(original_files)
        assert source_check() == 289 and baseline_check() == 36
        assert complete['blocks'] == frozen['blocks'] == list(BLOCKS)
        write_json(destination/'ORIGINAL_FILES.json', original_files)
        blocks = {}; acquisition = []
        for index in BLOCKS:
            path = directory/f'tissue_{index}'
            blocks[str(index)] = run.saved(path)
            assert blocks[str(index)] == read_json(path/'SAVED_CHECK.json')
            acquisition.append(read_json(path/'CHECK.json'))
        saved = {k: sum(v[k] for v in blocks.values())
                 for k in ('arrays', 'paired_rows', 'distinct_environments', 'new_dynamics')}
        assert saved == complete['saved_verification'] == dict(
            arrays=51200, paired_rows=65536, distinct_environments=64, new_dynamics=0)
        fields = ('native_batches', 'individual_assays', 'native_arrays', 'saved_arrays', 'paired_rows')
        native = {k: sum(v[k] for v in acquisition) for k in fields}
        native['max_native_error'] = 0.
        assert all(v['status'] == 'PASS' and v['max_native_error'] == 0. for v in acquisition)
        assert native == complete['verification'] == frozen['planned_verification'] == design.expected('development', 4)
        summary, conditional = analysis.summary(directory, 'development')
        assert serialized(summary) == (directory/'SUMMARY.json').read_bytes()
        assert serialized(conditional) == (directory/'CONDITIONAL.json').read_bytes()
        assert analysis.report(summary) == analysis.report(read_json(directory/'SUMMARY.json')) == (directory/'REPORT.md').read_text()
        assert summary['verification'] == complete['summary_verification'] == dict(
            status='PASS', rows=65536, telescoping_chains=8192, zero_preservation_rows=16384)
        assert summary['cycles'] == 8 and summary['historical_futures'] == summary['new_draws_per_packet'] == 4
        assert summary['primary'] == frozen['primary'] == 'residual:subtract_on:final_minus_initial'
        assert len(conditional) == 16384 and all(v['draws'] == 4 for v in conditional)
        for family in design.FAMILIES:
            arms = summary['families'][family]['arms']
            assert set(arms) == set(design.ARMS)
            for arm in design.ARMS:
                data = arms[arm]
                assert set(data['cycles']) == {str(g) for g in range(1, 9)}
                for v in [data['final_minus_initial']] + [data['cycles'][str(g)]['overall'] for g in range(1, 9)]:
                    assert v['n'] == 1024 and len(v['record_means']) == 64 and len(v['blocks']) == 4
                    assert sum(v['draw_changes'].values()) == 1024 and sum(v['record_changes'].values()) == 64
                for cycle in data['cycles'].values():
                    for key in ('messages', 'injury_strata', 'developed_status'):
                        assert sum(v['n'] for v in cycle[key].values()) == 1024
        verify(frozen['inputs']); verify(frozen['evidence']); verify(original_files)
        receipt = dict(status='PASS', study='TT025', completed_utc=now(), seconds=time.monotonic()-tick,
            code=str(Path(__file__).resolve()), code_sha256=sha(__file__), written_after_acquisition=True,
            written_before_effect_inspection=True, new_dynamics=0, new_receiving_assays=0,
            original_run_unchanged=True, original_run_status='COMPLETE', run_completion=str(complete_path),
            run_completion_sha256=sha(complete_path), freeze_sha256=sha(ROOT/'FREEZE.json'),
            frozen_inputs=len(frozen['inputs']), frozen_evidence=len(frozen['evidence']),
            original_run_files=len(original_files), source_files=289, baseline_groups=36,
            saved_verification=saved, retained_acquisition_verification=native,
            summary_verification=summary['verification'], conditional_pairs=len(conditional),
            summary_sha256=sha(directory/'SUMMARY.json'), conditional_sha256=sha(directory/'CONDITIONAL.json'),
            report_sha256=sha(directory/'REPORT.md'), summary_byte_identical=True,
            conditional_byte_identical=True, report_byte_identical=True, all_arms_and_strata_retained=True,
            actual_incoming_outgoing_routes_verified=True, paired_receiving_environments_verified=True,
            exact_preservation_and_telescoping_verified=True, scientific_classification=summary['classification'],
            fresh_population_confirmation=False, significance_verdict=False,
            outputs={str(p): sha(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        write_json(destination/'COMPLETE.json', receipt)
        write_json(ROOT/'CLOSEOUT.json', receipt)
        print(json.dumps({k: v for k, v in receipt.items() if k != 'outputs'}, sort_keys=True), flush=True)
    except BaseException as error:
        write_json(destination/'FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error),
            traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == '__main__':
    main()
