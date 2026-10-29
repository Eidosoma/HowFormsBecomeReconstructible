from common import *
import math
import execute
def main():
 qp=ROOT/'checks/preflight_v1/COMPLETE.json';bp=ROOT/'runs/qualification_v1/COMPLETE.json'
 q,b=read(qp),read(bp);code=inputs()
 assert q['status']=='PASS' and b['status']=='COMPLETE' and b['serial_parallel_bitwise_equal']
 assert q['inputs']==b['inputs']==code and b['environment']==execute.environment()
 verify(q['outputs']);verify(b['outputs']);verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
 forecast=math.ceil(3*b['seconds']+60);assert forecast<4*3600
 projected=math.ceil(3*b['retained_bytes']+64*1024**2)
 assert size()+projected<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE+projected
 assert not (ROOT/'runs/exchange_v1').exists()
 value=dict(study='TT042',frozen_utc=now(),inputs=code,evidence={str(p):sha(p) for p in (qp,bp)},
  environment=execute.environment(),cpus=[6,7],workers=2,numerical_threads=1,blocks=BLOCKS,run_name='exchange_v1',
  forecast_seconds=forecast,deadline_seconds=max(600,2*forecast),forecast_new_output_bytes=projected,
  study_output_ceiling_bytes=LIMIT,free_reserve_bytes=RESERVE,forecast_rule='3 times the measured two-block excluded duration plus 60 seconds',
  source_population_exposed=True,source_forcing_reused=True,recipient_evidence_inherited=True,new_receiving_assays=0,
  new_production_outcomes_generated=False,confirmatory=False,all_cases_retained=True,
  primary='mix050; residual|all|all_masks|own; target at 1900; both conditional packet effects, both conditional body effects, total and interaction',
  automatic_polling=False,automatic_retry=False,automatic_successor=False)
 write(ROOT/'FREEZE.json',value);return value
