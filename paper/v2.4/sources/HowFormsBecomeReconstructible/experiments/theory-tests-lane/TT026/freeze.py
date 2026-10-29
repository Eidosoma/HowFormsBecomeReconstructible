"""Freeze only after excluded qualification, full benchmark and admission."""
from datetime import datetime, timezone
from dataclasses import asdict
import math
import shutil
from common import *
import design
import execute

def main():
    assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
    inputs=runtime_hashes();source_check();baseline_check()
    pointer=read_json(ROOT/'QUALIFICATION.json');qpath=Path(pointer['path'])
    assert sha(qpath)==pointer['sha256'];q=read_json(qpath)
    bpath=ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json';b=read_json(bpath)
    assert q['status']=='PASS' and b['status']=='COMPLETE'
    assert q['inputs']==b['inputs']==inputs
    assert q['environment']==b['environment']==execute.environment()
    verify(q['outputs']);verify(b['outputs'])
    resource=read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
    assert resource['admission_pass'] and resource['planned_workers']==2
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds()<180
    planned=design.expected('development',4)
    scale=max(planned[k]/b['verification'][k] for k in ('repair_batches','reader_batches'))
    forecast=b['seconds']*scale*1.5+180;deadline=max(600,math.ceil(3*forecast+600))
    storage=math.ceil(b['retained_bytes']*scale*1.3+64*1024**2)
    assert forecast<16*3600 and deadline<48*3600 and storage<execute.RUN_LIMIT
    assert shutil.disk_usage(ROOT).free>=execute.RUN_LIMIT+execute.RESERVE
    cfg,rcfg=design.configs('development');evidence=dict(read_json(ROOT/'BASELINE_MANIFEST.json')['evidence'])
    evidence.update({str(p):sha(p) for p in (qpath,bpath,ROOT/'PRELAUNCH_RESOURCE_CHECK.json')})
    value=dict(status='FROZEN_EXPOSED_CASE_WRITING_WINDOW_DEVELOPMENT',study='TT026',frozen_utc=now(),
        blocks=list(BLOCKS),families=list(design.FAMILIES),arms=list(design.ARMS),writing_budgets=list(design.BUDGETS),
        historical_futures=4,new_draws=4,repair_updates=1000,config=asdict(cfg),readout=asdict(rcfg),
        primary='residual:corrected_duration_curve:outgoing_minus_incoming',population_blocks=4,records_per_family=64,
        record_bytes=2048,namespace=design.TAG,forecast_seconds=forecast,deadline_seconds=deadline,
        benchmark_scale=scale,estimated_output_bytes=storage,inputs=inputs,evidence=evidence,
        environment=execute.environment(),cpus=b['cpus'],workers=2,numerical_threads=1,planned_verification=planned,
        run_byte_limit=execute.RUN_LIMIT,free_reserve_bytes=execute.RESERVE,
        starting_records_and_history_exposed=True,new_production_gated_repairs_generated=False,
        new_production_receiving_draws_generated=False,fresh_population_confirmation=False,
        significance_verdict=False,serial_endpoint=False,task_labels_enter_receiving_physics=False,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,automatic_sample_extension=False)
    write_json(ROOT/'FREEZE.json',value)
    print(json.dumps({k:value[k] for k in ('status','forecast_seconds','deadline_seconds','estimated_output_bytes','planned_verification')},sort_keys=True))

if __name__=='__main__':main()
