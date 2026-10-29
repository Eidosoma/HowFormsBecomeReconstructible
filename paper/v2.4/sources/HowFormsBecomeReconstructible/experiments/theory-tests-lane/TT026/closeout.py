"""Post-acquisition saved-evidence closeout, before outcome interpretation.

Rechecks custody, actual gated states, scoring, pairing and complete tables.
No trajectories are integrated; the completed acquisition remains immutable.
"""
import time
import traceback
from common import *
import analysis
import design
import execute
import run

def main():
    destination=ROOT/'checks/closeout_v1';destination.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();complete_path=ROOT/'runs/window_v1/COMPLETE.json';directory=complete_path.parent
    try:
        frozen=read_json(ROOT/'FREEZE.json');complete=read_json(complete_path)
        original=dict(complete['outputs']);original[str(complete_path)]=sha(complete_path)
        write_json(destination/'RUNNING.json',dict(started_utc=now(),trigger='USER_STATUS_REQUEST',
            written_after_acquisition=True,outcome_effects_inspected_before_closeout=False,
            code_sha256=sha(__file__),new_dynamics=0))
        assert complete['status']=='COMPLETE' and complete['role']=='development'
        assert not (directory/'FAILED.json').exists()
        assert complete['inputs']==frozen['inputs']==runtime_hashes()
        assert complete['environment']==frozen['environment']==execute.environment()
        assert complete['freeze_sha256']==sha(ROOT/'FREEZE.json')
        verify(frozen['inputs']);verify(frozen['evidence']);verify(original)
        assert {str(p) for p in directory.rglob('*') if p.is_file()}==set(original)
        assert source_check()==289 and baseline_check()==36
        assert complete['blocks']==frozen['blocks']==list(BLOCKS)
        write_json(destination/'ORIGINAL_FILES.json',original)
        blocks={};acquisition=[]
        for index in BLOCKS:
            path=directory/f'tissue_{index}';blocks[str(index)]=run.saved(path)
            assert blocks[str(index)]==read_json(path/'SAVED_CHECK.json')
            acquisition.append(read_json(path/'CHECK.json'))
        saved={k:sum(v[k] for v in blocks.values()) for k in
            ('arrays','paired_rows','body_rows','distinct_receiving_environments','legacy_control_arrays','new_dynamics')}
        assert saved==complete['saved_verification']==dict(arrays=22400,paired_rows=14336,
            body_rows=3584,distinct_receiving_environments=64,legacy_control_arrays=1152,new_dynamics=0)
        expected=design.expected('development',4)
        native={k:sum(v[k] for v in acquisition) for k in expected if k!='max_native_error'}
        native['max_native_error']=0.
        assert all(v['status']=='PASS' and v['max_native_error']==0. for v in acquisition)
        assert native==complete['verification']==frozen['planned_verification']==expected
        summary,conditional=analysis.summary(directory,'development')
        assert serialized(summary)==(directory/'SUMMARY.json').read_bytes()
        assert serialized(conditional)==(directory/'CONDITIONAL.json').read_bytes()
        assert analysis.report(summary)==analysis.report(read_json(directory/'SUMMARY.json'))==(directory/'REPORT.md').read_text()
        assert summary['verification']==complete['summary_verification']==dict(status='PASS',paired_rows=14336,
            body_rows=3584,zero_preservation_rows=2048,receiving_draws_not_counted_as_body_replicates=True)
        assert summary['historical_futures']==summary['new_draws_per_packet']==4
        assert summary['primary']==frozen['primary']=='residual:corrected_duration_curve:outgoing_minus_incoming'
        assert set(summary['primary_curve'])==set(design.CORRECTED)
        assert summary['budgets']==list(design.BUDGETS)
        assert len(conditional)==3584 and all(v['draws']==4 for v in conditional)
        for family in design.FAMILIES:
            arms=summary['families'][family]['arms'];assert set(arms)==set(design.ARMS)
            for arm in design.ARMS:
                data=arms[arm]
                assert set(data)=={'receiving','receiving_vs_full','repaired_body','repaired_body_vs_full'}
                for endpoint,groups in data.items():
                    n=1024 if endpoint.startswith('receiving') else 256
                    v=groups['overall'];assert v['n']==n and len(v['record_means'])==64 and len(v['blocks'])==4
                    assert sum(v['pair_changes'].values())==n and sum(v['record_changes'].values())==64
                    for key in ('messages','injury_strata','developed_status'):
                        assert sum(v['n'] for v in groups[key].values())==n
        verify(frozen['inputs']);verify(frozen['evidence']);verify(original)
        receipt=dict(status='PASS',study='TT026',completed_utc=now(),seconds=time.monotonic()-tick,
            code=str(Path(__file__).resolve()),code_sha256=sha(__file__),written_after_acquisition=True,
            written_before_effect_inspection=True,new_dynamics=0,new_receiving_assays=0,
            original_run_unchanged=True,original_run_status='COMPLETE',run_completion=str(complete_path),
            run_completion_sha256=sha(complete_path),freeze_sha256=sha(ROOT/'FREEZE.json'),
            frozen_inputs=len(frozen['inputs']),frozen_evidence=len(frozen['evidence']),original_run_files=len(original),
            source_files=289,baseline_groups=36,saved_verification=saved,retained_acquisition_verification=native,
            summary_verification=summary['verification'],conditional_pairs=len(conditional),
            summary_sha256=sha(directory/'SUMMARY.json'),conditional_sha256=sha(directory/'CONDITIONAL.json'),
            report_sha256=sha(directory/'REPORT.md'),summary_byte_identical=True,conditional_byte_identical=True,
            report_byte_identical=True,all_durations_controls_and_strata_retained=True,
            actual_gated_repair_and_packet_routes_verified=True,paired_receiving_environments_verified=True,
            preserved_packet_and_separate_body_counts_verified=True,scientific_classification=summary['classification'],
            fresh_population_confirmation=False,significance_verdict=False,serial_endpoint=False,
            outputs={str(p):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        write_json(destination/'COMPLETE.json',receipt);write_json(ROOT/'CLOSEOUT.json',receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k!='outputs'},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(destination/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),
            traceback=traceback.format_exc(),automatic_retry=False));raise

if __name__=='__main__':main()
