"""Freeze the new population only after complete excluded qualification."""
from common import *
import execute,math


def main():
    pp=ROOT/'checks/preflight_v1/COMPLETE.json';qp=ROOT/'runs/qualification_v1/COMPLETE.json'
    pre,q=read(pp),read(qp);code=inputs()
    assert pre['status']=='PASS' and q['status']=='COMPLETE' and q['serial_parallel_bitwise_equal']
    assert pre['inputs']==q['inputs']==code and q['environment']==execute.environment()
    verify(pre['outputs']);verify(q['outputs']);verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
    blocks=[read(ROOT/f'runs/qualification_v1/tissue_{i}/COMPLETE.json') for i in EXCLUDED]
    source=max(b['source_seconds']+b['writer_seconds'] for b in blocks)
    rate=max(b['physical_seconds']/b['verification']['physical_continuations'] for b in blocks)
    reduction=max(b['analysis_seconds'] for b in blocks)*16
    forecast=math.ceil(1.5*(len(BLOCKS)/2*(source+rate*physical_bound('confirmation')+reduction))+120)
    assert forecast<MAX_FORECAST,'measured production forecast exceeds fixed ceiling'
    projected=phase_bound('confirmation')+ADMIN_BYTES
    assert size()+projected<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE+projected
    assert not (ROOT/'runs/confirmation_v1').exists()
    evidence=[pp,qp,ARCHIVE/'PLAN.json',ARCHIVE/'BENCHMARK.json',ARCHIVE/'COMPLETE.json',ARCHIVE/'archive.py']
    frozen=dict(study='TT046',frozen_utc=now(),inputs=code,evidence={str(p):sha(p) for p in evidence},
        environment=execute.environment(),cpus=[6,7],workers=2,numerical_threads=1,blocks=BLOCKS,run_name='confirmation_v1',
        forecast_seconds=forecast,deadline_seconds=max(600,2*forecast),maximum_forecast_seconds=MAX_FORECAST,
        forecast_rule='1.5 * 16 waves * (slower measured source/writer seconds + slower reader seconds/batch * 672 + 16 * slower reduction seconds) + 120',
        measured_source_writer_seconds=source,measured_read_seconds_per_batch=rate,per_block_reduction_allowance_seconds=reduction,
        forecast_new_output_bytes=projected,study_output_ceiling_bytes=LIMIT,free_reserve_bytes=RESERVE,
        new_production_outcomes_generated=False,source_population_reused=False,population_confirmation=True,
        fixed_fresh_states_per_record=4,new_futures_per_fixed_state=8,independent_population_blocks=32,
        primary='Fresh-state packet effect under full replacement and full-minus-intact effect difference, each at 900 and 1000; all four bounds must exceed zero.',
        family_alpha=.05,per_endpoint_alpha=ALPHA,all_cases_and_paired_harms_retained=True,
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    write(ROOT/'FREEZE.json',frozen);return frozen
