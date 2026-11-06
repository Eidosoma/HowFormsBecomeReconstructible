"""Resource-qualified single development launch; no automatic successor."""
from pc_common import *
import argparse
import math
import subprocess
import time
from pc_admission import admission


def budget(available):
    require(available>=1,'No worker capacity inside shared 12-thread ceiling')
    workers=min(6,available)
    q=read(ROOT/'QUALIFICATION.json');require(q['status']=='PASS','Successful qualification required')
    old=[r for r in csv_rows(PRICE_REPORT/'timings.csv') if r['depth']=='2']
    prior=dict(native=max(float(r['native_and_forcing_wall_seconds'])/60 for r in old),
        audit=max(float(r['flat_audit_wall_seconds'])/3 for r in old),
        evidence=max((float(r['evidence_and_replay_checks_wall_seconds'])+float(r['persistence_wall_seconds']))/60 for r in old))
    new=q['native_receipts']
    current=dict(native=max(sum(r['phase_seconds'][k]['wall'] for k in ('writer2','terminal','scoring'))/40 for r in new),
        audit=max(r['phase_seconds']['flat_audit']['wall']/2 for r in new),
        evidence=max((r['input_retrieval_seconds']['wall']+sum(r['phase_seconds'][k]['wall'] for k in ('evidence','persistence')))/40 for r in new))
    chosen={k:max(prior[k],current[k]) for k in prior}
    sequential=25520*(chosen['native']+chosen['evidence'])+1276*chosen['audit']
    # The 71-feature family is the largest candidate; price eight families using
    # its complete nested path, plus the measured full scoring path and audit reserve.
    fitting=max(300.,1.5*(8*q['synthetic_fit_cost']['wall_seconds']+q['synthetic_scoring_wall_seconds']+120.))
    forecast=1.25*sequential/workers+fitting
    hard=max(3600,1800*math.ceil(forecast/1800))
    require(hard<=21600,'Full cohort cannot fit the user six-hour ceiling at available concurrency')
    return dict(workers=workers,parent_thread_reserve=1,phase_maxima_prior=prior,
        phase_maxima_current=current,phase_maxima_chosen=chosen,sequential_native_wall_forecast=sequential,
        native_sensitivity_multiplier=1.25,fitting_scoring_audit_reserve_seconds=fitting,
        full_forecast_seconds=forecast,hard_wall_seconds=hard,
        rule='One hour if sufficient; otherwise smallest 30-minute increment covering the conservative full-cohort forecast, at most six hours. No extension or partial-cohort inference.')


def main(job):
    job=job.resolve();require(job.is_relative_to(ROOT/'jobs'),'Job confined to this package')
    freeze=verify_freeze()
    q=read(ROOT/'QUALIFICATION.json')
    for name,h in q['code_sha256'].items():require(sha(ROOT/name)==h,'Source changed after qualification: '+name)
    require(sha(ROOT/'prepared/SOURCES.json')==q['prepared_source_sha256'],'Qualified source export changed')
    job.mkdir(parents=True,exist_ok=False)
    admitted=admission();write(job/'CPU_ADMISSION.json',admitted)
    costs=budget(admitted['available_worker_slots'])
    require(admitted['other_active_or_recently_busy_threads']+costs['workers']+1<=12,'Shared thread cap')
    write(job/'BUDGET.json',costs)
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    command=[sys.executable,str(ROOT/'pc_run.py'),'--output',str(job/'run'),
             '--workers',str(costs['workers']),'--seconds',str(costs['hard_wall_seconds'])]
    with (job/'run.log').open('xb') as log:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,
                               stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    write(job/'LAUNCH.json',dict(utc=utc(),pid=child.pid,command=command,freeze_sha256=freeze,
        scope='POST_HOC_RETAINED_DEVELOPMENT',workers=costs['workers'],hard_wall_seconds=costs['hard_wall_seconds'],
        forecast_seconds=costs['full_forecast_seconds'],automatic_retry=False,automatic_successor=False,
        polling='No assistant polling until completion or a user status request.'))
    time.sleep(3.)
    startup=dict(utc=utc(),pid=child.pid,exit_code=child.poll(),start_receipt_present=(job/'run/START.json').exists(),
                 failure_receipt_present=(job/'run/FAILURE.json').exists())
    write(job/'STARTUP_CHECK.json',startup)
    print(json.dumps(dict(job=str(job),startup=startup,workers=costs['workers'],
                         forecast_minutes=costs['full_forecast_seconds']/60,hard_minutes=costs['hard_wall_seconds']/60,
                         other_threads=admitted['other_active_or_recently_busy_threads'])),flush=True)
    require(startup['exit_code'] is None and not startup['failure_receipt_present'],'Development failed at startup; preserve failure, no retry')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);a=p.parse_args();main(a.job)
