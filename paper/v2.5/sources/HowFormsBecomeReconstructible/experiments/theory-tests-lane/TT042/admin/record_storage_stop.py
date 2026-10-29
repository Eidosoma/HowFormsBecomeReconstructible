"""User-requested status: retain passed qualification and the failed storage gate."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
def replace_file(p,value):
 p=Path(p);tmp=p.with_name(p.name+'.storage-status');write(tmp,value);tmp.replace(p)
def main():
 review=ROOT/'status_reviews/storage_gate_v1';process=read(review/'PROCESS_CHECK.json')
 assert process['status']=='PASS' and not (ROOT/'runs/exchange_v1').exists() and not (ROOT/'FREEZE.json').exists()
 complete=ROOT/'runs/qualification_v1/COMPLETE.json';q=read(complete);failed=read(ROOT/'QUEUE_FAILED.json')
 assert q['status']=='COMPLETE' and q['serial_parallel_bitwise_equal']
 assert 'freeze.py' in failed['traceback'] and 'size()+projected<LIMIT' in failed['traceback']
 assert inputs()==q['inputs'];verify(q['outputs']);verify(q['inputs'])
 handoff=read(ROOT/'LAUNCH_HANDOFF.json');verify(handoff['files'])
 archive=review/'prior_handoff';archive.mkdir();bound={}
 paths=set(handoff['files'])|{str(ROOT/'LAUNCH_HANDOFF.json'),str(ROOT/'CURRENT_EXECUTION.json')}
 for name in sorted(paths):
  p=Path(name);dst=archive/p.relative_to(LANE);dst.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(p,dst);bound[name]=dict(archive=str(dst),sha256=sha(p));assert sha(dst)==sha(p)
 write(review/'ARCHIVE.json',bound)
 measured=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 projected=math.ceil(3*q['retained_bytes']+64*1024**2);free=shutil.disk_usage(ROOT).free
 value=dict(status='QUALIFIED_STOPPED_BEFORE_PRODUCTION',reviewed_utc=now(),qualification_status='PASS',
  qualification_seconds=q['seconds'],qualification_completed_utc=q['completed_utc'],qualification_sha256=sha(complete),
  verification=q['verification'],serial_parallel_bitwise_equal=True,production_started=False,production_outcomes_exist=False,
  no_active_jobs=True,all_recorded_processes_exited=True,production_runtime_forecast_seconds=math.ceil(3*q['seconds']+60),
  budget=dict(study_bytes_at_review=measured,additional_output_forecast_bytes=projected,study_cap_bytes=LIMIT,
   projected_study_total_bytes=measured+projected,free_bytes_at_review=free,free_space_reserve_bytes=RESERVE,
   required_free_bytes=RESERVE+projected,storage_formula='three times retained two-block benchmark bytes plus 64 MiB'),
  scientific_failure=False,reason='Storage projection exceeds the fixed study cap and free-space admission threshold.',
  changed_scientific_definitions=False,changed_resource_limits=False,deleted_evidence=False,automatic_retry=False,
  next_step='Review a tighter justified output forecast or lossless storage layout before a separately recorded production continuation; retain passed qualification and all evidence.')
 write(review/'REVIEW.json',value)
 text='''

User-requested status review on 24 October: **qualified, stopped before
production**. Full excluded qualification passed in **6 minutes 13 seconds**,
including exact serial/parallel equivalence, 8,480 independently replayed native
arrays and 5,760 saved diagonal state comparisons. The controller then stopped
at the storage admission gate. Its conservative forecast exceeded both the
1 GiB study cap and the free-space threshold needed to retain the 4 GiB reserve.

No production directory or production freeze was created. All workers and the
controller have exited; no new production exchange result exists. This is a
resource stop, not a failed physical check. The measured production runtime
forecast would be 19 minutes 39 seconds once admitted. No limits were changed,
no evidence was deleted, and no retry was launched. Preserve the qualified work
while reviewing the output forecast or a lossless storage layout for the next
recorded continuation. See [status review](status_reviews/storage_gate_v1/REVIEW.json).
'''
 for name in ('README.md','EXECUTION.md'):
  with (ROOT/name).open('a') as f:f.write(text)
 current=read(ROOT/'CURRENT_EXECUTION.json');current.update(status='QUALIFIED_STORAGE_STOP_REVIEWED',reviewed_utc=value['reviewed_utc'],
  status_review='TT042/status_reviews/storage_gate_v1/REVIEW.json',no_active_jobs=True,production_started=False,
  production_completed=False,qualification_status='PASS',automatic_retry=False)
 replace_file(ROOT/'CURRENT_EXECUTION.json',current)
 intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=now()
 intake['body_packet_exchange_development'].update(status='QUALIFIED_STORAGE_STOP_REVIEWED',observed_utc=value['reviewed_utc'],
  qualification_status='PASS',full_qualification_pending_at_handoff=False,production_started=False,
  production_outcomes_exist=False,no_active_jobs=True,status_review='TT042/status_reviews/storage_gate_v1/REVIEW.json')
 replace_file(LANE/'prediction_intake_status.json',intake)
 brief='''

TT042 status review: full excluded qualification passed in 6 minutes 13 seconds,
but the fixed storage gate stopped the sequence before production. All processes
have exited; no production results exist. Physical replay and serial/parallel
equivalence passed. The projected output exceeded the study cap and reserve
threshold; no limits were raised, evidence deleted or retry launched. Preserve
the qualification for a justified storage correction. See
[review](TT042/status_reviews/storage_gate_v1/REVIEW.json).
'''
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
  with (LANE/name).open('a') as f:f.write(brief)
 event=dict(recorded_utc=now(),study='TT042',event='user_requested_status_storage_stop',qualification_status='PASS',
  new_production_outcomes_generated=False,scientific_definitions_changed=False,resource_limits_changed=False,automatic_retry=False)
 with (LANE/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(event,sort_keys=True)+'\n')
 files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl')]
 files += [ROOT/n for n in ('README.md','EXECUTION.md','CURRENT_EXECUTION.json','status_reviews/storage_gate_v1/REVIEW.json',
  'status_reviews/storage_gate_v1/PROCESS_CHECK.json','status_reviews/storage_gate_v1/ARCHIVE.json','admin/record_storage_stop.py')]
 write(review/'HANDOFF.json',dict(status='PASS',recorded_utc=now(),files={str(p):sha(p) for p in files},scientific_results_inspected=False,production_started=False))
 print(json.dumps({k:v for k,v in value.items() if k!='verification'},sort_keys=True))
if __name__=='__main__':main()
