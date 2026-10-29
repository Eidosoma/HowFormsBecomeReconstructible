"""Saved-evidence closeout written after acquisition and before effect inspection.

Rechecks frozen custody, initializers, packet routes, scores and all summaries.
Does not integrate trajectories or change the completed run.
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
    tick=time.monotonic();complete_path=ROOT/'runs/serial_v1/COMPLETE.json';directory=complete_path.parent
    try:
        frozen=read_json(ROOT/'FREEZE.json');complete=read_json(complete_path)
        original_files=dict(complete['outputs']);original_files[str(complete_path)]=sha(complete_path)
        assert complete['status']=='COMPLETE' and complete['role']=='development'
        assert not (directory/'FAILED.json').exists()
        assert complete['inputs']==frozen['inputs']==runtime_hashes()
        assert complete['environment']==frozen['environment']==execute.environment()
        assert complete['freeze_sha256']==sha(ROOT/'FREEZE.json')
        verify(frozen['inputs']);verify(frozen['evidence']);verify(original_files)
        assert {str(p) for p in directory.rglob('*') if p.is_file()}==set(original_files)
        assert source_check()==289 and baseline_check()==44
        assert complete['blocks']==frozen['blocks']==list(BLOCKS)
        write_json(destination/'ORIGINAL_FILES.json',original_files)
        write_json(destination/'RUNNING.json',dict(started_utc=now(),trigger='USER_STATUS_REQUEST',
            outcome_effects_inspected_before_closeout=False,code_sha256=sha(__file__),new_dynamics=0))
        blocks={};acquisition=[]
        for index in BLOCKS:
            path=directory/f'tissue_{index}';blocks[str(index)]=run.saved_check(path)
            acquisition.append(read_json(path/'CHECK.json'))
        saved={k:sum(v[k] for v in blocks.values()) for k in ('arrays','records','packet_handoffs','new_dynamics')}
        assert saved==complete['saved_verification']==dict(arrays=37120,records=2048,packet_handoffs=1152,new_dynamics=0)
        fields=('arm_batches','new_repairs','new_reads','retained_repairs','reused_read_slots','native_arrays')
        native={k:sum(v[k] for v in acquisition) for k in fields};native['max_native_error']=0.
        assert all(v['status']=='PASS' and v['max_native_error']==0. for v in acquisition)
        assert native==complete['verification']==frozen['planned_verification']==design.expected('development',4)
        summary=analysis.summary(directory,'development')
        assert serialized(summary)==(directory/'SUMMARY.json').read_bytes()
        assert analysis.report(summary)==analysis.report(read_json(directory/'SUMMARY.json'))==(directory/'REPORT.md').read_text()
        assert summary['generations']==8 and summary['futures']==4 and summary['records_per_family']==64
        for family in design.FAMILIES:
            value=summary['families'][family]
            assert set(value['arms'])==set(design.ARMS) and set(value['contrasts'])==set(design.comparisons())
            for arm in design.ARMS:
                v=value['arms'][arm]
                assert v['n']==256 and len(v['by_record'])==64 and len(v['by_block'])==4
                assert len(v['development_by_generation'])==len(v['repaired_by_generation'])==8
                assert len(v['body_by_generation_and_injury'])==8
                for group in v['terminal_by_injury'].values():assert sum(x['n'] for x in group.values())==256
                for group in v['body_by_generation_and_injury']:assert sum(x['n'] for x in group.values())==256
            for contrast in value['contrasts'].values():
                for endpoint in analysis.ENDPOINTS:
                    assert sum(contrast[endpoint]['record_changes'].values())==64
                    assert sum(contrast[endpoint]['draw_changes'].values())==256
                    assert len(contrast[endpoint]['blocks'])==4
        verify(frozen['inputs']);verify(frozen['evidence']);verify(original_files)
        receipt=dict(status='PASS',study='TT024',completed_utc=now(),seconds=time.monotonic()-tick,
            code=str(Path(__file__).resolve()),code_sha256=sha(__file__),written_after_acquisition=True,
            written_before_effect_inspection=True,new_dynamics=0,new_receiving_assays=0,
            original_run_unchanged=True,original_run_status='COMPLETE',run_completion=str(complete_path),
            run_completion_sha256=sha(complete_path),freeze_sha256=sha(ROOT/'FREEZE.json'),
            frozen_inputs=len(frozen['inputs']),frozen_evidence=len(frozen['evidence']),
            original_run_files=len(original_files),source_files=289,baseline_batches=44,
            saved_verification=saved,retained_acquisition_verification=native,
            summary_sha256=sha(directory/'SUMMARY.json'),report_sha256=sha(directory/'REPORT.md'),
            summary_byte_identical=True,report_byte_identical=True,all_arms_and_strata_retained=True,
            original_controls_and_prefixes_verified=True,own_evolving_packet_and_body_routes_verified=True,
            scientific_classification=summary['classification'],fresh_population_confirmation=False,significance_verdict=False,
            outputs={str(p):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        write_json(destination/'COMPLETE.json',receipt);write_json(ROOT/'CLOSEOUT.json',receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k!='outputs'},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(destination/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),
            traceback=traceback.format_exc(),automatic_retry=False));raise

if __name__=='__main__':main()
