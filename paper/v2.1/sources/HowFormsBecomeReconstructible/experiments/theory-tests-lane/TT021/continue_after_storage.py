"""Execution-only continuation: preserve 62 blocks and generate two unstarted ones."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import time
import traceback

import common as c
import execute as original
import run
import analysis

ROOT=c.ROOT
OLD=ROOT/'runs/confirmation_v1'
NEW=ROOT/'runs/confirmation_continuation_v1'
QUAL=ROOT/'checks/continuation_v1'
MISSING=(21000062,21000063)


def inputs():
    value=c.runtime_hashes()
    for name in ('continue_after_storage.py','CONTINUATION_AMENDMENT.md'):
        value[str(ROOT/name)]=c.sha(ROOT/name)
    return value


def own_files(directory):
    result=[]
    for entry in directory.iterdir():
        if entry.is_symlink():continue
        if entry.is_file():result.append(entry)
        elif entry.is_dir():result.extend(p for p in entry.rglob('*') if p.is_file())
    return sorted(result)


def make_view(directory,carried,missing,total):
    assert set(carried).isdisjoint(missing) and set(carried)|set(missing)==set(total)
    for index,path in carried.items():
        assert c.read_json(Path(path)/'CONFIG.json')['tissue']==index
        assert c.read_json(Path(path)/'SAVED_CHECK.json')['status']=='PASS'
    directory.mkdir(parents=True,exist_ok=False)
    for index,path in carried.items():
        (directory/f'tissue_{index}').symlink_to(Path(path).resolve(),target_is_directory=True)
    for index in missing:assert not (directory/f'tissue_{index}').exists()


def qualified():
    result=c.read_json(QUAL/'COMPLETE.json')
    assert result['status']=='PASS' and result['inputs']==inputs()
    c.verify(result['inputs']);c.verify(result['outputs'])
    return result


def qualify():
    QUAL.mkdir(parents=True,exist_ok=False);tick=time.monotonic();bound=inputs()
    c.write_json(QUAL/'STARTED.json',dict(started_utc=c.now(),inputs=bound,new_cohort_generated=False))
    try:
        registration=c.read_json(ROOT/'REGISTRATION.json')
        assert c.runtime_hashes()==registration['inputs'] and original.environment()==registration['environment']
        c.verify(registration['inputs']);c.verify(registration['evidence'])
        base=ROOT/'checks/qualification_v1/serial'
        retained={str(p):c.sha(p) for p in base.rglob('*') if p.is_file()}
        cfg=replace(c.model.CONFIG,replicates=1,settle=3,imprint=5,sweeps=4,times=(0,1,2,4))
        rcfg=replace(c.model.READOUT,parents=1,draws=2,sweeps=4,times=(0,1,4))
        view=QUAL/'linked_miniature'
        make_view(view,{c.DISPOSABLE[0]:base/f'tissue_{c.DISPOSABLE[0]}'},[c.DISPOSABLE[1]],c.DISPOSABLE)
        original.paired_batch(view,[c.DISPOSABLE[1]],cfg,rcfg,registration['cpus'],'excluded continuation qualification')
        checks=[]
        for index in c.DISPOSABLE:
            source=base/f'tissue_{index}';target=view/f'tissue_{index}'
            assert run.saved_check(target,cfg,rcfg)==c.read_json(source/'SAVED_CHECK.json')
            for name in ('records.json','contrasts.json','read_map.json'):
                assert (source/name).read_bytes()==(target/name).read_bytes()
            left,right=[c.read_json(path/'PROVENANCE.json') for path in (source,target)]
            for category in ('source','repairs','reads'):
                assert set(left[category])==set(right[category])
                for name in left[category]:assert left[category][name]['arrays']==right[category][name]['arrays']
            assert left['packets']['arrays']==right['packets']['arrays']
        checks.append('linked carry and newly generated excluded block equal original arrays, scores, routes and contrasts')
        for label,fn in (
            ('overlapping carried and missing blocks rejected',lambda:make_view(QUAL/'bad_overlap',{c.DISPOSABLE[0]:base/f'tissue_{c.DISPOSABLE[0]}'},c.DISPOSABLE,c.DISPOSABLE)),
            ('wrong carried tissue rejected',lambda:make_view(QUAL/'bad_tissue',{c.DISPOSABLE[0]:base/f'tissue_{c.DISPOSABLE[1]}'},[c.DISPOSABLE[1]],c.DISPOSABLE)),
            ('existing view cannot be overwritten',lambda:make_view(view,{},c.DISPOSABLE,c.DISPOSABLE)),
            ('changed carry hash rejected',lambda:c.verify({str(base/f'tissue_{c.DISPOSABLE[0]}/CHECK.json'):'0'*64})),
        ):
            try:fn()
            except (AssertionError,FileExistsError):checks.append(label)
            else:raise AssertionError(label)
        c.verify(retained);c.verify(bound)
        checks.append('all original miniature and registered runtime inputs unchanged')
        outputs={str(p):c.sha(p) for p in own_files(QUAL)}
        result=dict(status='PASS',completed_utc=c.now(),seconds=time.monotonic()-tick,checks=checks,
            inputs=bound,outputs=outputs,new_cohort_generated=False,scientific_outcome_summaries_inspected=False)
        c.write_json(QUAL/'COMPLETE.json',result)
        return {k:v for k,v in result.items() if k not in ('inputs','outputs')}
    except BaseException as error:
        c.write_json(QUAL/'FAILED.json',dict(status='FAILED',error=repr(error),traceback=traceback.format_exc()));raise


def prepare():
    qualified();tick=time.monotonic()
    attempt=ROOT/'continuation_preparation/v1';attempt.mkdir(parents=True,exist_ok=False)
    try:
        registration=c.read_json(ROOT/'REGISTRATION.json');failed=c.read_json(OLD/'FAILED.json')
        assert failed['error']=="AssertionError('storage reserve')" and not (OLD/'COMPLETE.json').exists()
        assert c.runtime_hashes()==registration['inputs'] and original.environment()==registration['environment']
        c.verify(registration['inputs']);c.verify(registration['evidence'])
        assert not NEW.exists() and not (ROOT/'CONTINUATION_REGISTRATION.json').exists()
        carried={i:str(OLD/f'tissue_{i}') for i in c.BLOCKS if (OLD/f'tissue_{i}').is_dir()}
        assert list(carried)==list(c.BLOCKS[:-2]) and tuple(i for i in c.BLOCKS if i not in carried)==MISSING
        for index in MISSING:assert not (OLD/f'worker_{index}.json').exists()
        before={str(p):c.sha(p) for p in own_files(OLD)}
        saved={};proofs={}
        for index,path in carried.items():
            block=Path(path);proof=c.read_json(block/'CHECK.json')
            assert proof['status']=='PASS' and proof['max_native_error']==0. and proof['max_average_error']<=2e-12
            value=run.saved_check(block,c.model.CONFIG,c.model.READOUT)
            assert value==c.read_json(block/'SAVED_CHECK.json')
            saved[index]=value;proofs[index]={k:proof[k] for k in ('records','repair_paths','logical_assays','unique_assays','native_arrays','exact_alias_checks','max_native_error','max_average_error')}
        c.verify(before)
        carry=dict(status='PASS',checked_utc=c.now(),blocks=carried,hashes=before,saved=saved,verification=proofs,
            seconds=time.monotonic()-tick,new_trajectories=0,scientific_outcome_summaries_inspected=False)
        c.write_json(ROOT/'CONTINUATION_CARRY.json',carry)
        benchmark=c.read_json(ROOT/'runs/benchmark_v1/COMPLETE.json')
        forecast=benchmark['seconds']*10+carry['seconds']+120
        started=datetime.fromisoformat(c.read_json(OLD/'RUNNING.json')['started_utc'])
        original_deadline=started+timedelta(seconds=registration['deadline_seconds'])
        remaining=(original_deadline-datetime.now(timezone.utc)).total_seconds()
        assert remaining>forecast
        deadline=int(min(remaining-1,3*forecast+600))
        assert sum(Path(p).stat().st_size for p in before)<original.RUN_LIMIT
        assert shutil.disk_usage(ROOT).free>=original.RUN_LIMIT+original.RESERVE
        evidence=dict(registration['evidence'])
        for path in (ROOT/'REGISTRATION.json',ROOT/'CONTINUATION_CARRY.json',QUAL/'COMPLETE.json',
                     ROOT/'STORAGE_FAILURE_REVIEW.json',ROOT/'CONTINUATION_RESOURCE_CHECK.json'):
            evidence[str(path)]=c.sha(path)
        result=dict(registered_utc=c.now(),inputs=inputs(),evidence=evidence,original_registration_sha256=c.sha(ROOT/'REGISTRATION.json'),
            original_run=str(OLD),combined_run=str(NEW),carried_blocks=list(carried),unstarted_blocks=list(MISSING),
            scientific_rules_unchanged=True,environment=original.environment(),workers=2,numerical_threads=1,cpus=registration['cpus'],
            forecast_seconds=forecast,deadline_seconds=deadline,original_absolute_deadline_retained=True,
            original_deadline_utc=original_deadline.isoformat(),
            run_byte_limit=original.RUN_LIMIT,free_reserve_bytes=original.RESERVE,
            execution_amendment_after_62_generated=True,scientific_outcome_summaries_inspected=False,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        c.write_json(ROOT/'CONTINUATION_REGISTRATION.json',result)
        c.write_json(attempt/'COMPLETE.json',dict(status='PASS',completed_utc=c.now(),registration_sha256=c.sha(ROOT/'CONTINUATION_REGISTRATION.json')))
        return dict(status='CONTINUATION_REGISTERED',carried_blocks=62,unstarted_blocks=list(MISSING),
            carry_check_seconds=carry['seconds'],forecast_seconds=forecast,deadline_seconds=deadline,verified_carried_files=len(before))
    except BaseException as error:
        c.write_json(attempt/'FAILED.json',dict(status='FAILED',error=repr(error),traceback=traceback.format_exc()));raise


def execute():
    registration=c.read_json(ROOT/'CONTINUATION_REGISTRATION.json')
    c.verify(registration['inputs']);c.verify(registration['evidence'])
    assert inputs()==registration['inputs'] and original.environment()==registration['environment']
    carry=c.read_json(ROOT/'CONTINUATION_CARRY.json');c.verify(carry['hashes'])
    assert sorted(os.sched_getaffinity(0))[-2:]==registration['cpus']
    absolute_remaining=(datetime.fromisoformat(registration['original_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
    assert absolute_remaining>registration['forecast_seconds']
    deadline=min(registration['deadline_seconds'],int(absolute_remaining)-1)
    tick=time.monotonic();make_view(NEW,{int(k):v for k,v in carry['blocks'].items()},MISSING,c.BLOCKS)
    def expire(signum,frame):raise TimeoutError('continuation deadline')
    signal.signal(signal.SIGALRM,expire);signal.alarm(deadline)
    c.write_json(NEW/'RUNNING.json',dict(status='RUNNING',started_utc=c.now(),pid=os.getpid(),
        registration_sha256=c.sha(ROOT/'CONTINUATION_REGISTRATION.json'),carried_blocks=62,unstarted_blocks=list(MISSING),
        workers=2,numerical_threads=1,cpus=registration['cpus'],deadline_seconds=deadline,
        original_deadline_utc=registration['original_deadline_utc'],automatic_polling=False))
    fd=os.environ.pop('TT021_CONTINUE_READY_FD',None)
    if fd is not None:os.write(int(fd),b'READY\n');os.close(int(fd))
    try:
        assert shutil.disk_usage(ROOT).free>original.RESERVE+256*1024**2
        result=original.paired_batch(NEW,MISSING,c.model.CONFIG,c.model.READOUT,registration['cpus'],'prospective confirmation')
        for index in MISSING:
            assert run.saved_check(NEW/f'tissue_{index}',c.model.CONFIG,c.model.READOUT)==result[index]['saved']
        c.verify(carry['hashes'])
        summary=analysis.summary(NEW);c.write_json(NEW/'SUMMARY.json',summary)
        with (NEW/'REPORT.md').open('x') as f:
            f.write('Execution amendment: 62 unchanged blocks carried after a storage halt; only the two unstarted blocks completed. See ../../CONTINUATION_AMENDMENT.md.\n\n'+analysis.report(summary))
        assert c.serialized(analysis.summary(NEW))==(NEW/'SUMMARY.json').read_bytes()
        assert (NEW/'REPORT.md').read_text()=='Execution amendment: 62 unchanged blocks carried after a storage halt; only the two unstarted blocks completed. See ../../CONTINUATION_AMENDMENT.md.\n\n'+analysis.report(c.read_json(NEW/'SUMMARY.json'))
        checks={int(k):v for k,v in carry['verification'].items()}
        saved={int(k):v for k,v in carry['saved'].items()}
        for index in MISSING:checks[index]=result[index]['proof'];saved[index]=result[index]['saved']
        fields=('records','repair_paths','logical_assays','unique_assays','native_arrays','exact_alias_checks')
        verification={k:sum(v[k] for v in checks.values()) for k in fields}
        verification.update(max_native_error=0.,max_average_error=max(v['max_average_error'] for v in checks.values()))
        saved_totals={k:sum(v[k] for v in saved.values()) for k in ('array_receipts','scalar_record_rows','packet_routes')}
        outputs={str(p):c.sha(p) for p in own_files(NEW)}
        logical_bytes=sum(Path(p).stat().st_size for p in carry['hashes'])+sum(Path(p).stat().st_size for p in outputs)
        assert logical_bytes<original.RUN_LIMIT and shutil.disk_usage(ROOT).free>=original.RESERVE
        c.verify(registration['inputs']);c.verify(registration['evidence']);c.verify(carry['hashes'])
        complete=dict(status='COMPLETE',completed_utc=c.now(),started_utc=c.read_json(NEW/'RUNNING.json')['started_utc'],
            seconds=time.monotonic()-tick,blocks=list(c.BLOCKS),original_run=str(OLD),original_failure_preserved=True,
            inputs=registration['inputs'],outputs=outputs,carried_outputs=carry['hashes'],
            registration_sha256=c.sha(ROOT/'REGISTRATION.json'),continuation_registration_sha256=c.sha(ROOT/'CONTINUATION_REGISTRATION.json'),
            carried_blocks=62,new_blocks=list(MISSING),verification=verification,saved_verification=saved_totals,
            combined_retained_bytes=logical_bytes,primary=summary['primary'],environment=original.environment(),
            workers=2,numerical_threads=1,execution_amendment=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        c.write_json(NEW/'COMPLETE.json',complete);signal.alarm(0)
        return {k:v for k,v in complete.items() if k not in ('inputs','outputs','carried_outputs')}
    except BaseException as error:
        c.write_json(NEW/'FAILED.json',dict(status='FAILED',failed_utc=c.now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False));raise


def launch():
    registration=c.read_json(ROOT/'CONTINUATION_REGISTRATION.json')
    c.verify(registration['inputs']);c.verify(registration['evidence'])
    assert inputs()==registration['inputs'] and not NEW.exists()
    assert original.environment()==registration['environment']
    assert (datetime.fromisoformat(registration['original_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()>registration['forecast_seconds']
    assert shutil.disk_usage(ROOT).free>=original.RUN_LIMIT+original.RESERVE
    readfd,writefd=os.pipe();env=dict(os.environ,TT021_CONTINUE_READY_FD=str(writefd))
    log=ROOT/'confirmation_continuation_v1.log'
    with log.open('xb') as stream:
        process=subprocess.Popen(['bash',str(c.LANE/'run_python.sh'),str(Path(__file__).resolve()),'--execute'],
            cwd=c.LANE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,env=env,
            start_new_session=True,pass_fds=(writefd,))
    os.close(writefd);ready=select.select([readfd],[],[],30)[0];message=os.read(readfd,64) if ready else b'';os.close(readfd)
    receipt=dict(status='DETACHED_STARTED' if message==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        pid=process.pid,acknowledged_utc=c.now(),log=str(log),registration_sha256=c.sha(ROOT/'CONTINUATION_REGISTRATION.json'),
        carried_blocks=62,new_blocks=list(MISSING),workers=2,numerical_threads=1,cpus=registration['cpus'],
        forecast_seconds=registration['forecast_seconds'],deadline_seconds=registration['deadline_seconds'],
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    c.write_json(ROOT/'CONTINUATION_LAUNCH.json',receipt);assert message==b'READY\n',receipt
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    for option in ('qualify','prepare','execute','launch'):group.add_argument('--'+option,action='store_true')
    args=parser.parse_args()
    action=next(name for name in ('qualify','prepare','execute','launch') if getattr(args,name))
    print(c.json.dumps(globals()[action](),sort_keys=True),flush=True)
