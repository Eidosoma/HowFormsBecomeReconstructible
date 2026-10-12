"""CPU-admitted frozen worker: qualify, audit selected states, then run the fixed curve."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import resource
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from common import ROOT,read,write,sha,save_arrays,status,stamp,validate


def check_inputs(manifest):
    for name,digest in manifest['files_sha256'].items():assert sha(ROOT/name)==digest,name


def interrupted(signum,frame):
    raise RuntimeError('Worker received '+signal.Signals(signum).name)


def qualify(folder,cfg,manifest):
    q=folder/'qualification';q.mkdir(exist_ok=False)
    temporary=q/'tmp';temporary.mkdir();child_env=os.environ.copy();child_env['TMPDIR']=str(temporary)
    status(folder,status='RUNNING',phase='qualification_tests')
    with (q/'tests.log').open('xb') as log:
        result=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
            '--basetemp='+str(q/'test_work'),'--junitxml='+str(q/'tests.xml'),
            str(ROOT/'test_study.py'),str(ROOT/'test_admission.py')],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,env=child_env,check=False)
    assert result.returncode==0,'Qualification tests failed; see qualification/tests.log'
    tree=ET.parse(q/'tests.xml').getroot();suites=list(tree.iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts==dict(tests=7,failures=0,errors=0,skipped=0),counts
    write(q/'TESTS.json',dict(status='PASS',at_utc=stamp(),counts=counts,log_sha256=sha(q/'tests.log'),xml_sha256=sha(q/'tests.xml')))
    check_inputs(manifest)
    status(folder,status='RUNNING',phase='selected_failure_causal_audit')
    from causal_audit import main as audit
    audit_result=audit(folder/'causal_audit',cfg)
    assert audit_result['all_factual_bytes_match'] and audit_result['unique_contexts']==7
    status(folder,status='RUNNING',phase='known_control_benchmark')
    from benchmark import main as benchmark
    measured=benchmark(folder/'benchmark',cfg)
    assert measured['within_ceiling'] and measured['byte_equal'] and measured['new_frequency_outcomes']==0
    check_inputs(manifest)
    write(folder/'QUALIFIED.json',dict(status='PASS',at_utc=stamp(),tests=counts,
        benchmark_sha256=sha(folder/'benchmark/COMPLETE.json'),causal_audit_sha256=sha(folder/'causal_audit/COMPLETE.json'),
        manifest_sha256=sha(folder/'manifest.json'),measured_forecast_cpu_seconds=measured['forecast_cpu_seconds'],
        new_frequency_outcomes_before_qualification=0,policy_unchanged_after_causal_audit=True))
    print(f"Qualification passed: 7 tests, 7 paired causal contexts, byte-exact native controls. Measured curve forecast {measured['forecast_cpu_seconds']/60:.2f} CPU minutes.",flush=True)


def main(folder,ready_fd):
    begin=time.perf_counter();cpu=time.process_time();child_cpu=resource.getrusage(resource.RUSAGE_CHILDREN)
    child_cpu=child_cpu.ru_utime+child_cpu.ru_stime;lock=(folder/'worker.lock').open('a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        manifest=read(folder/'manifest.json');cfg=manifest['config'];validate(cfg);check_inputs(manifest)
        assert ROOT==folder/'inputs'
        assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
        for path,digest in read(ROOT/'sources/COMPLETE.json')['sources_sha256'].items():assert sha(path)==digest,path
        write(folder/'WORKER_STARTED.json',dict(status='RUNNING',at_utc=stamp(),pid=os.getpid(),
            ready_inputs_verified=True,persistent_host_process=True,executes_frozen_copy=True,
            qualification_pending=True,new_frequency_outcomes=0))
        status(folder,status='RUNNING',phase='startup_verified')
        os.write(ready_fd,b'READY\n');os.close(ready_fd);ready_fd=None
        qualify(folder,cfg,manifest)
        from source_data import load
        from serial import continue_block,assemble
        start_curve=time.perf_counter();curve_cpu=time.process_time()
        write(folder/'FREQUENCY_STARTED.json',dict(status='RUNNING',at_utc=stamp(),qualified_sha256=sha(folder/'QUALIFIED.json')))
        receipts=[]
        for b in cfg['blocks']:
            started=time.perf_counter();check_inputs(manifest)
            status(folder,status='RUNNING',phase='repair_frequency_continuation',block=b)
            initial,previous,controls=load(b)
            new=continue_block(initial,previous,b,cfg,reference=controls)
            d=assemble(new,controls)
            digest=save_arrays(folder/f'continuation_{b:06d}.npz',d)
            receipt=dict(status='COMPLETE',block=b,records=16,history=cfg['history_by_block'][str(b)],
                seconds=time.perf_counter()-started,continuation_sha256=digest,
                independent_optimizer_checks=int(d['independent_optimizer_checks'].sum()),
                selected_on_outcome=False,generations=cfg['generations'],branches=5,simulated_branches=3,reused_branches=2)
            assert receipt['independent_optimizer_checks']==160
            write(folder/f'worker_{b:06d}.json',receipt);receipts.append(receipt)
            print(f'Block {b} complete; all records and all five budgets retained through generation 32.',flush=True)
        status(folder,status='RUNNING',phase='analysis')
        from analyze import analyze,render
        analyze(folder,cfg)
        status(folder,status='RUNNING',phase='independent_verification')
        from verify import verify
        assert verify(folder,cfg)['status']=='PASS'
        render(folder,cfg);check_inputs(manifest)
        status(folder,status='COMPLETE',phase='complete',blocks_completed=cfg['blocks'])
        excluded={'console.log','PID','LAUNCH.json','worker.lock'}
        outputs={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name not in excluded}
        for sub in ('causal_audit','benchmark','qualification'):
            for p in sorted((folder/sub).iterdir()):
                if p.is_file():outputs[str(p.relative_to(folder))]=sha(p)
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),seconds=time.perf_counter()-begin,
            cpu_seconds=time.process_time()-cpu,qualification_child_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime-child_cpu,curve_seconds=time.perf_counter()-start_curve,curve_cpu_seconds=time.process_time()-curve_cpu,
            cpu_note='Worker CPU and qualification-child CPU are reported separately; sum them for total CPU. Curve CPU includes analysis and audit.',
            scientific_status='REPAIR_FREQUENCY_DEVELOPMENT_ON_EXPOSED_COHORT',blocks_completed=cfg['blocks'],records=256,
            scientific_read_contexts=23040,simulated_read_contexts=13824,new_continuation_contexts=13056,
            first_step_replay_contexts=768,reused_control_contexts=9216,independent_verification_passed=True,
            causal_audit_passed=True,receipts=receipts,outputs_sha256=outputs,automatic_successor=False))
        print('COMPLETE: causal audit, budget curve, costs, independent checks and report saved.',flush=True)
    except BaseException:
        failure=dict(status='FAILED',at_utc=stamp(),seconds=time.perf_counter()-begin,traceback=traceback.format_exc())
        if not (folder/'FAILED.json').exists():write(folder/'FAILED.json',failure)
        status(folder,status='FAILED',phase='failed');raise
    finally:
        if ready_fd is not None:os.close(ready_fd)
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--ready-fd',type=int,required=True)
    args=parser.parse_args();main(args.run.resolve(),args.ready_fd)
