"""Frozen finite search with conditional untouched confirmation and resource admission."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,multiprocessing,os,shutil,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h063.workflow import compare
from h102.workflow import FILES as PARENT_FILES
from h103 import model as m,audit,measure,report,fixtures

FILES=PARENT_FILES+['h103/'+name for name in ('PROTOCOL.md','model.py','audit.py','measure.py','report.py','fixtures.py','workflow.py')]
PARENT_PIN='846543e9b362643502a68b72064fc8cb09bf0c5f39777c35cb464cbca18ca851'
TOTALS=('coordinate_decisions','field_arrays_checked','sweep_states_checked','reads_replayed','writer_packets_checked','actual_handoffs','independent_score_rows','h102_current_parity_arrays')
def read(p):return json.loads(Path(p).read_text())
def load(p):
    with np.load(p,allow_pickle=False) as f:return {k:f[k] for k in f.files}
def bound(b):assert checksum(b['path'])==b['sha256']
def task(arg):
    out,b,variants=arg;out=Path(out);tick=time.perf_counter();stem=f"block_{b['block']:03d}"
    try:
        bound(b);tape=load(b['path']);save(out/'commitments'/(stem+'.json'),dict(binding=b,variants=list(variants),committed_utc=utc(),acquisition_started=False))
        raw=m.run_tapes(tape,variants);path=out/'raw'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**raw)
        stored=load(path);assert raw.keys()==stored.keys()
        for key in raw:np.testing.assert_array_equal(stored[key],raw[key])
        checked=audit.network(stored,tape,variants);rows=measure.network(stored,tape,variants,b['block'])
        checked.update(independent_score_rows=measure.independent_scores(stored,tape,variants,rows),
            block=b['block'],variants=list(variants),saved_arrays_verified=len(stored),raw_sha256=checksum(path))
        save(out/'blocks'/(stem+'.json'),rows);save(out/'audits'/(stem+'.json'),checked);bound(b)
        return dict(**checked,active_seconds=time.perf_counter()-tick)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(utc=utc(),error=traceback.format_exc()));raise
def batch(out,bindings,variants,workers,progress):
    for name in ('raw','blocks','audits','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();result=[];arguments=[(out,b,variants) for b in bindings]
    if workers==1:
        for arg in arguments:result.append(task(arg));progress(completed_blocks=len(result),total_blocks=len(bindings))
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for f in as_completed([pool.submit(task,a) for a in arguments]):result.append(f.result());progress(completed_blocks=len(result),total_blocks=len(bindings))
    value=dict(workers=workers,active_seconds=time.perf_counter()-tick,tasks=sorted(result,key=lambda r:r['block']))
    save(out/'batch.json',value);return value
def finish(out,result,variants,phase,selected=None):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']]
    summary=report.produce(out,blocks,variants,phase,selected);report.plot(out,summary)
    verification=dict(passed=True,networks=len(blocks),phase=phase,**{k:sum(r[k] for r in result['tasks']) for k in TOTALS},
        maximum_field_error=max(r['maximum_field_error'] for r in result['tasks']),maximum_energy_error=max(r['maximum_energy_error'] for r in result['tasks']),
        minimum_boundary_distance=min(r['minimum_boundary_distance'] for r in result['tasks']),
        serialized_rows=summary['rows_serialized_and_verified'],verdict=summary['verdict'],writer_has_no_exact_zero_fallback=True,
        assessment_matched_across_horizons=True,protected_copy_invariance_passed=True,
        acquisition_gain=4.,assessment_gain=2.,supplying_gain=2.,record_edge_deletion=.2)
    save(out/'verification.json',verification);return summary,verification
def verify_inputs(out):
    verify(out,'freeze.json');c=read(out/'config.json');lane=Path(c['lane_root']);parent=Path(c['parent'])
    assert checksum(parent/'checksums.json')==PARENT_PIN;verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['integrity_passed'] and checksum(c['qualification_receipt'])==c['qualification_receipt_sha256']
    receipt=read(c['qualification_receipt'])
    assert receipt['passed'] and receipt['manifest_sha256']==PARENT_PIN
    assert receipt['verdict']=='CURRENT_REGIME_QUALIFIED_FOR_REVERSAL_TEST' and receipt['selected_cell']==3
    assert receipt['selected_gain']==2. and receipt['selected_deletion']==.2
    assert read(parent/'qualification/summary.json')['verdict']=='CURRENT_REGIME_QUALIFIED_FOR_REVERSAL_TEST'
    assert c['python']==sys.version and c['numpy']==np.__version__
    assert c['seed']==103103 and c['horizons']==[0,1,2,3,4] and c['cohorts']=={'engineering':4,'development':16,'confirmation':32}
    assert (c['acquisition_gain'],c['assessment_gain'],c['supplying_gain'],c['record_edge_deletion'])==(4.,2.,2.,.2)
    seen=set()
    for cohort,bindings in read(out/'input_bindings.json').items():
        for b in bindings:
            bound(b);tape=load(b['path'])
            expected=m.tapes(cohort,b['block']);assert tape.keys()==expected.keys()
            for k,v in expected.items():np.testing.assert_array_equal(tape[k],v)
            fingerprint=tape['targets'].tobytes()+tape['base'].tobytes();assert fingerprint not in seen;seen.add(fingerprint)
    assert len(seen)==52
    for name in FILES:assert checksum(out/'source'/name)==checksum(lane/name),name
    return c
def execute(out):
    assert ROOT==out/'source';tick=time.perf_counter();state=dict(state='RUNNING',phase='input_qualification',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        state.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick);save(out/'STATUS.json',state);print(json.dumps(state),flush=True)
    admissions=[]
    def admit(phase,workers,n=0):
        progress(phase=phase+'_admission',workers=0,completed_blocks=0,total_blocks=n)
        admissions.append(capacity(out/(phase+'_admission.json'),workers,progress));progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();admit('inputs',1);c=verify_inputs(out);bindings=read(out/'input_bindings.json')
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        tests=fixtures.run();save(out/'fixtures.json',tests)
        results={}
        for label,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(label,workers,4);results[label]=batch(out/label,bindings['engineering'],m.VARIANTS,workers,progress)
        equivalent=compare(out);serial=results['engineering_serial']['active_seconds'];parallel=results['engineering_parallel']['active_seconds']
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*12+120
        choice=dict(workers=workers,speedup=serial/parallel,serial_seconds=serial,parallel_seconds=parallel,**equivalent,
            conservative_remaining_seconds=forecast,threshold=1.15,decided_utc=utc(),decided_before_development=True)
        save(out/'worker_choice.json',choice);progress(conservative_remaining_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file());need=int(size*24+300_000_000)
        free=shutil.disk_usage(out).free;assert free>need;save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_remaining_bytes=need,free_bytes=free))
        admit('engineering_report',1);_,engineering=finish(out/'engineering_serial',results['engineering_serial'],m.VARIANTS,'engineering')
        admit('development',workers,16);development=batch(out/'development',bindings['development'],m.VARIANTS,workers,progress)
        admit('development_report',1);summary,dev=finish(out/'development',development,m.VARIANTS,'development')
        seal(out/'development','checksums.json',[p for p in sorted((out/'development').rglob('*')) if p.is_file()])
        verify(out/'development','checksums.json')
        selection=summary['selection'];selection.update(selected_utc=utc(),development_manifest_sha256=checksum(out/'development/checksums.json'))
        save(out/'selection.json',selection);selection_pin=checksum(out/'selection.json');fresh=None
        if selection['selected'] is not None:
            name=selection['selected'];variants=('unchanged',name,'random_'+name,'strength_'+name,'erased','donor')
            save(out/'confirmation_commitment.json',dict(selection_sha256=selection_pin,variants=variants,networks=32,committed_utc=utc(),confirmation_started=False))
            admit('confirmation',workers,32);confirmation=batch(out/'confirmation',bindings['confirmation'],variants,workers,progress)
            admit('confirmation_report',1);_,fresh=finish(out/'confirmation',confirmation,variants,'confirmation',name)
        assert checksum(out/'selection.json')==selection_pin;verify(out/'development','checksums.json')
        progress(phase='closeout',workers=1);verify_inputs(out)
        result=dict(passed=True,fixtures=tests,engineering=engineering,development=dev,confirmation=fresh,selection=selection,
            confirmed_networks=32 if fresh else 0,reserved_confirmation_unopened=fresh is None,worker_choice=choice,
            capacity_wait_seconds=sum(a['wait_seconds'] for a in admissions),elapsed_seconds=time.perf_counter()-tick,
            source_files_unchanged=len(FILES),historical_verdicts_unchanged=True,original_H097_acceptance='FAILED',
            H101_verdict_unchanged=True,H102_regime_used_without_reselection=True,
            acquisition_gain=4.,assessment_gain=2.,supplying_gain=2.,next_experiment_launched=False)
        save(out/'execution_summary.json',result)
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True,
            verdict=fresh['verdict'] if fresh else selection['verdict'],selected=selection['selected'],confirmed_networks=result['confirmed_networks'])
        save(out/'COMPLETE.json',state);seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'checksums.json']);verify(out,'checksums.json')
        receipt=Path(c['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),manifest_sha256=checksum(out/'checksums.json'),run=str(out),verdict=state['verdict'],
            confirmed_networks=result['confirmed_networks'],next_experiment_launched=False))
    except BaseException:
        failure=dict(state='FAILED',failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',state)
        raise
def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h103_gain2_reversal_')
    receipt=ROOT/'.cache'/(out.name+'_closeout.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.log'),out.with_suffix('.pid'),receipt))
    parent=ROOT/'runs/h102_current_calibration_v1';assert checksum(parent/'checksums.json')==PARENT_PIN;verify(parent,'checksums.json')
    qualification=ROOT/'.cache/h102_completion_verification_v1.json';prerequisite=read(qualification)
    assert prerequisite['passed'] and prerequisite['manifest_sha256']==PARENT_PIN
    assert prerequisite['verdict']=='CURRENT_REGIME_QUALIFIED_FOR_REVERSAL_TEST' and prerequisite['selected_cell']==3
    assert (prerequisite['selected_gain'],prerequisite['selected_deletion'])==(2.,.2)
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    assert len(FILES)==len(set(FILES))
    out.mkdir();(out/'inputs').mkdir();bindings={}
    for cohort,n in (('engineering',4),('development',16),('confirmation',32)):
        bindings[cohort]=[]
        for block in range(n):
            tape=m.tapes(cohort,block);path=out/'inputs'/f'{cohort}_{block:03d}.npz'
            with path.open('xb') as f:np.savez_compressed(f,**tape)
            bindings[cohort].append(dict(cohort=cohort,block=block,path=str(path),sha256=checksum(path)))
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    for name,source in (('RUN_POLICY.md',ROOT/'RUN_POLICY.md'),('shared_RUN_POLICY.md',ROOT.parent/'RUN_POLICY.md')):shutil.copyfile(source,out/name)
    save(out/'input_bindings.json',bindings)
    save(out/'config.json',dict(experiment='H103',created_utc=utc(),lane_root=str(ROOT),parent=str(parent),parent_manifest_sha256=PARENT_PIN,
        python=sys.version,numpy=np.__version__,seed=103103,cohorts=dict(engineering=4,development=16,confirmation=32),horizons=list(range(5)),
        variants=list(m.VARIANTS),routes=list(m.ROUTES),qualification_receipt=str(qualification),qualification_receipt_sha256=checksum(qualification),
        acquisition_gain=4.,assessment_gain=2.,supplying_gain=2.,record_edge_deletion=.2,neural_threshold=1e-12,exclusion_margin=5e-14,field_energy_tolerance=2e-11,
        shared_cpu_limit=12,numerical_threads=1,closeout_receipt=str(receipt),next_experiment_launched=False))
    save(out/'historical_verdicts.json',read(parent/'historical_verdicts.json'))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h103/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h103/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
    with out.with_suffix('.log').open('xb') as stream:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,
        forecast_pending_engineering=True,confirmation_conditional_on_frozen_development_gate=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',type=Path);parser.add_argument('--prepare',type=Path)
    args=parser.parse_args()
    if args.execute:execute(args.execute.resolve())
    elif args.prepare:prepare(args.prepare.resolve())
