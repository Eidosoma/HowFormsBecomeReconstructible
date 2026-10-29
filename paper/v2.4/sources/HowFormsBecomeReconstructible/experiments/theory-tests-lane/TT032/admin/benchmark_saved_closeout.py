"""Complete the timed-out benchmark's saved-only verification; preserve its failure."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis
import design
import execute
import os
import run
import signal
import time
import traceback


def main():
    job=ROOT/'runs/benchmark_v1';dest=ROOT/'checks/benchmark_saved_closeout_v1'
    dest.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    resource=read_json(ROOT/'BENCHMARK_CLOSEOUT_RESOURCE_CHECK.json')
    assert resource['admission_pass'] and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds()<180
    os.sched_setaffinity(0,{resource['cpus'][-1]})
    original={str(p):sha(p) for p in sorted(job.rglob('*')) if p.is_file()}
    write_json(dest/'ORIGINAL_FILES.json',original)
    inputs=read_json(job/'RUNNING.json')['inputs'];assert inputs==runtime_hashes()
    assert read_json(job/'FAILED.json')['error']=="TimeoutError('TT032 600-second limit')"
    assert not (job/'COMPLETE.json').exists()
    def expire(*_):raise TimeoutError('TT032 benchmark saved closeout 600-second limit')
    def forbidden(*args,**kwargs):raise AssertionError('new dynamics forbidden in saved-only closeout')
    run.kernel.repair=forbidden;run.receiving.read=forbidden
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    try:
        checks={}
        for index in design.indices('benchmark'):
            path=job/f'tissue_{index}';proof=run.saved(path)
            assert read_json(path/'SAVED_CHECK.json')==dict(status='PASS',verification=proof,new_dynamics=0)
            assert serialized(analysis.block(path))==(path/'SUMMARY.json').read_bytes()
            checks[str(index)]=proof
        final_verification_seconds=time.monotonic()-tick;t=time.monotonic()
        summary=analysis.summary(job,'benchmark');write_json(dest/'SUMMARY.json',summary)
        rendered=analysis.report(summary)
        assert rendered==analysis.report(read_json(dest/'SUMMARY.json'))
        with (dest/'REPORT.md').open('x') as f:f.write(rendered)
        write_json(dest/'BLOCK_CHECKS.json',checks)
        verify(inputs);verify(original)
        assert original=={str(p):sha(p) for p in sorted(job.rglob('*')) if p.is_file()}
        manifest=read_json(ROOT/'INPUT_MANIFEST.json');verify(manifest['benchmark']);verify(manifest['evidence'])
        value=dict(status='PASS_SAVED_ONLY_CLOSEOUT',completed_utc=now(),seconds=time.monotonic()-tick,
            inputs=inputs,outputs={str(p):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()},
            original_files_manifest=str(dest/'ORIGINAL_FILES.json'),original_failure_preserved=True,
            original_failure_sha256=sha(job/'FAILED.json'),original_files=len(original),
            final_verification_seconds=final_verification_seconds,final_analysis_seconds=time.monotonic()-t,
            verification=summary['verification'],environment=execute.environment(),new_dynamics=0,
            benchmark_effects_inspected=False,production_started=False,original_benchmark_not_reclassified=True)
        write_json(dest/'COMPLETE.json',value);signal.alarm(0)
        print({k:value[k] for k in ('status','seconds','original_files','new_dynamics','original_failure_preserved')},flush=True)
    except BaseException as error:
        write_json(dest/'FAILED.json',dict(status='FAILED',error=repr(error),traceback=traceback.format_exc(),new_dynamics=0));raise


if __name__=='__main__':main()
