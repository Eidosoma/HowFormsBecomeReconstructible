"""Freeze fresh confirmation after qualification and full-duration timing."""
from dataclasses import asdict
from datetime import datetime,timezone
import math
import shutil
from common import *
import design
import execute

def main():
    assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
    inputs=runtime_hashes();source_check();evidence_check()
    qp=Path(read_json(ROOT/'QUALIFICATION.json')['path']);q=read_json(qp)
    bp=ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json';b=read_json(bp)
    assert q['status']=='PASS' and b['status']=='COMPLETE'
    assert q['inputs']==b['inputs'] and q['environment']==b['environment']==execute.environment()
    amendment=read_json(ROOT/'BUDGET_ESTIMATOR_AMENDMENT.json')
    assert {p for p in set(inputs)|set(q['inputs']) if inputs.get(p)!=q['inputs'].get(p)}=={str(ROOT/'freeze.py')}
    assert amendment['old_sha256']==q['inputs'][str(ROOT/'freeze.py')]==sha(ROOT/'checks/budget_estimator_v1/freeze_before.py')
    assert amendment['new_sha256']==sha(__file__) and amendment['scientific_inputs_changed'] is False
    verify(q['outputs']);verify(b['outputs'])
    resource=read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
    assert resource['admission_pass'] and resource['planned_workers']==2
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds()<180
    planned=design.expected('confirmation',len(BLOCKS));timings=list(b['component_timings'].values())
    repair_rate=max(v['repair_seconds']/v['repair_batches'] for v in timings)
    reader_rate=max(v['reader_seconds']/v['reader_batches'] for v in timings)
    saved_rate=max(v['saved_seconds']/v['saved_arrays'] for v in timings)
    baseline_rate=max(v['baseline_seconds']/len(design.families('benchmark')) for v in timings)
    baseline_work=baseline_rate*len(BLOCKS)*len(design.FAMILIES)
    measured=max(v['acquisition_seconds']+v['saved_seconds'] for v in timings)
    fixed=max(0,b['seconds']-measured-b['final_verification_seconds']-b['final_analysis_seconds']-b['final_manifest_seconds'])
    compute=(baseline_work+repair_rate*planned['repair_batches']+reader_rate*planned['reader_batches']+saved_rate*planned['saved_arrays'])/2
    final_saved=max(saved_rate*planned['saved_arrays'],b['final_verification_seconds']*planned['saved_arrays']/b['verification']['saved_arrays'])
    rates={kind:max(v['storage_bytes'][kind]/v[denom] for v in timings)
        for kind,denom in (('repair','repair_batches'),('reader','reader_batches'),('other','paired_rows'))}
    baseline_bytes=max(v['storage_bytes']['baseline'] for v in timings)*len(BLOCKS)*2
    outer_bytes=max(0,b['retained_bytes']-sum(sum(v['storage_bytes'].values()) for v in timings))
    scale=planned['paired_rows']/b['verification']['paired_rows']
    aggregate_scale=(len(BLOCKS)*len(design.FAMILIES)*len(design.DAMAGE))/(len(b['blocks'])*len(design.families('benchmark'))*len(design.damage_levels('benchmark')))
    storage=math.ceil(1.3*(baseline_bytes+rates['repair']*planned['repair_batches']+rates['reader']*planned['reader_batches']+
        rates['other']*planned['paired_rows']+outer_bytes*aggregate_scale)+128*1024**2)
    # Final summary merges per-block record aggregates, not all receiving rows.
    # Per-block raw-row analysis/conditional uncertainty is already in saved cost.
    outer=(fixed*len(BLOCKS)/2+b['final_analysis_seconds']*aggregate_scale+
        b['final_manifest_seconds']*storage/b['retained_bytes'])
    forecast=1.5*(compute+final_saved+outer)+600
    deadline=math.ceil(2*forecast+600)
    admission=dict(recorded_utc=now(),forecast_seconds=forecast,deadline_seconds=deadline,estimated_output_bytes=storage,
        rates=dict(repair=repair_rate,reader=reader_rate,saved=saved_rate,baseline=baseline_rate,outer=fixed),
        components=dict(two_worker_seconds=compute,final_saved_seconds=final_saved,outer_seconds=outer,safety_factor=1.5,headroom_seconds=600),
        forecast_limit_seconds=24*3600,deadline_limit_seconds=48*3600,byte_limit=execute.RUN_LIMIT,
        pass_runtime=forecast<24*3600 and deadline<=48*3600,pass_storage=storage<execute.RUN_LIMIT and shutil.disk_usage(ROOT).free>=execute.RUN_LIMIT+execute.RESERVE)
    write_json(ROOT/'ADMISSION.json',admission)
    assert admission['pass_runtime'] and admission['pass_storage'],admission
    evidence=dict(read_json(ROOT/'EVIDENCE.json')['files'])
    evidence.update({str(p):sha(p) for p in (qp,bp,ROOT/'RESERVATION.json',ROOT/'RESERVATION_REVIEW.json',ROOT/'ADMISSION.json',ROOT/'PRELAUNCH_RESOURCE_CHECK.json',ROOT/'BUDGET_ESTIMATOR_AMENDMENT.json',ROOT/'checks/budget_estimator_v1/freeze_before.py')})
    cfg,rcfg=design.configs('confirmation')
    frozen=dict(status='FROZEN_PROSPECTIVE_CONDITIONAL_CORRECTION_CONFIRMATION',study='TT028',frozen_utc=now(),
        blocks=list(BLOCKS),population_units=len(BLOCKS),records_per_family=16*len(BLOCKS),
        families=list(design.FAMILIES),arms_by_body={b:list(design.arms(b)) for b in design.BODIES},damage=design.MIX,
        independent_corruptions=2,new_recipient_draws=8,developed_bodies_per_record=1,
        config=asdict(cfg),readout=asdict(rcfg),primary=design.PRIMARY,claims=design.claims(),
        family_alpha=.05,per_claim_alpha=design.ALPHA,selected_winner=False,serial_endpoint=False,
        inputs=inputs,evidence=evidence,environment=execute.environment(),cpus=b['cpus'],workers=2,numerical_threads=1,
        planned_verification=planned,forecast_seconds=forecast,deadline_seconds=deadline,estimated_output_bytes=storage,
        run_byte_limit=execute.RUN_LIMIT,free_reserve_bytes=execute.RESERVE,record_bytes=2048,
        new_production_outcomes_generated=False,prior_development_exposed=True,scientific_baseline_reuse=False,
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    write_json(ROOT/'FREEZE.json',frozen)
    print({k:frozen[k] for k in ('status','population_units','forecast_seconds','deadline_seconds','estimated_output_bytes','planned_verification')},flush=True)
if __name__=='__main__':main()
