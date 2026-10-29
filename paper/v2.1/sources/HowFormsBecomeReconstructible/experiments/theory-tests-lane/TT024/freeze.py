"""Freeze the serial experiment after qualification, benchmark and admission."""
from dataclasses import asdict
from datetime import datetime,timezone
import math
import shutil
import traceback
from common import *
import design
import execute

def main():
    attempt=ROOT/'freeze_attempts/v1';attempt.mkdir(parents=True,exist_ok=False)
    try:
        assert not (ROOT/'FREEZE.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
        inputs=runtime_hashes();source_check();baseline_check()
        pointer=read_json(ROOT/'QUALIFICATION.json');qpath=Path(pointer['path']);assert sha(qpath)==pointer['sha256']
        qualification=read_json(qpath);bpath=ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json';benchmark=read_json(bpath)
        assert qualification['status']=='PASS' and benchmark['status']=='COMPLETE'
        assert qualification['inputs']==benchmark['inputs']==inputs
        assert qualification['environment']==benchmark['environment']==execute.environment()
        verify(qualification['outputs']);verify(benchmark['outputs'])
        resource=read_json(ROOT/'PRELAUNCH_RESOURCE_CHECK.json')
        assert resource['admission_pass'] and resource['planned_workers']==2
        assert (datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds()<180
        forecast=benchmark['seconds']*280+120;deadline=max(600,math.ceil(3*forecast+600));storage=benchmark['retained_bytes']*24
        assert forecast<16*3600 and deadline<48*3600 and storage<execute.RUN_LIMIT
        assert shutil.disk_usage(ROOT).free>=execute.RUN_LIMIT+execute.RESERVE
        cfg,rcfg=design.configs('development');evidence=dict(read_json(ROOT/'BASELINE_MANIFEST.json')['evidence'])
        evidence.update({str(p):sha(p) for p in (qpath,bpath,ROOT/'PRELAUNCH_RESOURCE_CHECK.json')})
        frozen=dict(status='FROZEN_EXPOSED_CASE_SERIAL_FILL_SUBTRACTION_DEVELOPMENT',study='TT024',frozen_utc=now(),
            blocks=list(BLOCKS),families=list(design.FAMILIES),arms=list(design.ARMS),futures=4,generations=8,
            config=asdict(cfg),readout=asdict(rcfg),comparisons=design.comparisons(),
            primary='residual:subtract_vs_full:terminal',population_blocks=4,records_per_family=64,
            forecast_seconds=forecast,deadline_seconds=deadline,estimated_output_bytes=storage,
            inputs=inputs,evidence=evidence,environment=execute.environment(),cpus=benchmark['cpus'],workers=2,numerical_threads=1,
            planned_verification=design.expected('development',4),run_byte_limit=execute.RUN_LIMIT,free_reserve_bytes=execute.RESERVE,
            original_controls_and_prefixes_exposed=True,new_scientific_continuations_generated=False,
            fresh_population_confirmation=False,significance_verdict=False,additional_injury_mask=True,
            randomness='Intentional exact TT022 serial environment reuse; no new population or stochastic namespace',
            automatic_polling=False,automatic_retry=False,automatic_successor=False,automatic_sample_extension=False)
        write_json(ROOT/'FREEZE.json',frozen)
        write_json(attempt/'COMPLETE.json',dict(status='PASS',completed_utc=now(),freeze_sha256=sha(ROOT/'FREEZE.json')))
        print(json.dumps({k:frozen[k] for k in ('status','forecast_seconds','deadline_seconds','estimated_output_bytes','planned_verification')},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(attempt/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc()));raise

if __name__=='__main__':main()
