"""Admission from full-duration excluded native/replay/retention timings."""
from dataclasses import asdict
import math
import shutil
from common import *
import design
import execute


def main():
    qp=ROOT/'checks/qualification_v2/COMPLETE.json';bp=ROOT/'runs/benchmark_v2/COMPLETE.json'
    q=read_json(qp);b=read_json(bp);inputs=runtime_hashes()
    assert q['status']=='PASS' and b['status']=='COMPLETE' and q['inputs']==b['inputs']==inputs
    assert q['environment']==b['environment']==execute.environment()
    verify(q['outputs']);verify(b['outputs'])
    eq=read_json(ROOT/'checks/scheduling_equivalence_v1/COMPLETE.json')
    assert eq['status']=='PASS' and eq['scientific_outputs_identical'] and eq['inputs']==inputs
    verify(eq['evidence'])
    resources=read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
    assert resources['admission_pass'] and resources['planned_workers']==2
    assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resources['recorded_utc'])).total_seconds()<180
    timing=list(b['component_timings'].values());planned=design.expected('development',64);upper=design.upper('development',64)
    rates={name:max(t[name+'_seconds']/t[denom] for t in timing) for name,denom in
        (('repair','repair_batches'),('reader','reader_batches'),('saved','saved_arrays'))}
    source=max(t['source_seconds'] for t in timing)*64*4
    analysis=max(t['analysis_seconds'] for t in timing)*64*2
    row=max(t['row_seconds']/t['paired_rows'] for t in timing)*planned['paired_rows']
    compute=(source+rates['repair']*upper['repair_batches']+rates['reader']*upper['reader_batches']+
        rates['saved']*upper['saved_arrays']+analysis+row)/2
    final_saved=max(rates['saved']*upper['saved_arrays']/2,
        b['final_verification_seconds']*upper['saved_arrays']/b['verification']['saved_arrays'])
    byte_rates={k:max(t['storage_bytes'][k]/t[denom] for t in timing) for k,denom in
        (('repair','repair_batches'),('reader','reader_batches'),('other','paired_rows'))}
    storage=math.ceil(1.4*(byte_rates['repair']*upper['repair_batches']+byte_rates['reader']*upper['reader_batches']+
        byte_rates['other']*planned['paired_rows'])+512*1024**2)
    outer=b['final_analysis_seconds']*64+b['final_manifest_seconds']/b['retained_bytes']*storage
    forecast=math.ceil(1.5*(compute+final_saved+outer)+600)
    deadline=min(48*3600,max(3600,math.ceil(2*forecast+3600)))
    admission=dict(recorded_utc=now(),forecast_seconds=forecast,deadline_seconds=deadline,
        maximum_forecast_seconds=30*3600,estimated_output_bytes=storage,run_byte_limit=execute.RUN_LIMIT,
        rates=rates,storage_rates=byte_rates,physical_batch_upper_bounds=upper,logical_counts=planned,
        components=dict(two_worker_seconds=compute,final_saved_seconds=final_saved,outer_seconds=outer,safety_factor=1.5,headroom_seconds=600),
        pass_runtime=forecast<30*3600 and deadline<=48*3600,
        pass_storage=storage<execute.RUN_LIMIT and shutil.disk_usage(ROOT).free>=execute.RUN_LIMIT+execute.RESERVE)
    write_json(ROOT/'ADMISSION.json',admission)
    assert admission['pass_runtime'] and admission['pass_storage'],admission
    cfg,rcfg=design.configs('development')
    evidence=dict(read_json(ROOT/'INPUT_MANIFEST.json')['evidence'],**{str(p):sha(p) for p in
        (qp,bp,ROOT/'ADMISSION.json',ROOT/'PRELAUNCH_RESOURCE_CHECK.json',ROOT/'SCHEDULING_AMENDMENT.json',
         ROOT/'checks/benchmark_saved_closeout_v1/COMPLETE.json',ROOT/'checks/scheduling_equivalence_v1/COMPLETE.json')})
    value=dict(study='TT032',status='FROZEN_EXPOSED_COHORT_RESET_INTERVENTION',frozen_utc=now(),
        inputs=inputs,evidence=evidence,environment=execute.environment(),blocks=list(BLOCKS),source_blocks=64,
        source_records_per_family=1024,source_population_exposed=True,families=design.FAMILIES,damage=['mix100'],
        masks=design.MASKS,body_sources=design.BODIES,resets=design.RESETS,budgets=design.BUDGETS,
        reused_corruption_realizations=2,new_receiving_draws=4,config=asdict(cfg),readout=asdict(rcfg),
        mean_offset_matched=True,exact_duplicate_reuse_declared=True,foreign_permutations_simulated_directly=True,
        cpus=resources['cpus'],workers=2,numerical_threads=1,planned_logical_verification=planned,
        physical_batch_upper_bounds=upper,forecast_seconds=forecast,deadline_seconds=deadline,
        estimated_output_bytes=storage,run_byte_limit=execute.RUN_LIMIT,free_reserve_bytes=execute.RESERVE,
        record_bytes=2048,production_counterfactual_outcomes_generated=False,
        fresh_population_confirmation=False,serial_endpoint=False,fitted_policy=False,
        TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED',
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    write_json(ROOT/'FREEZE.json',value)
    print({k:value[k] for k in ('status','forecast_seconds','deadline_seconds','estimated_output_bytes','physical_batch_upper_bounds','planned_logical_verification')},flush=True)


if __name__=='__main__':main()
