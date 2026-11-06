"""Fresh calibrated-reader campaign with frozen inputs, exact benchmarks and shared CPU admission."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,multiprocessing,os,shutil,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h063.workflow import compare
from h099.engineering import FILES as PARENT_FILES,PINS as ANCESTOR_PINS
from h098.workflow import verify_parent
from h100 import model as m,audit,measure,report

PIN='63a8b8de76666f3bc0d2ba19dd4051b4ae650ddcb650284cd80a999702ca576c'
FILES=PARENT_FILES+['h100/'+name for name in ('PROTOCOL.md','model.py','audit.py','measure.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','records','writer_packets','unique_neural_reads','unique_native_reads','pair_energy_comparisons',
    'single_energy_comparisons','transport_checks','calibration_checks','decoded_output_checks','saved_arrays_reloaded',
    'independently_verified_rows','physical_assay_cases','decoded_panel_rows','ledger_rows','actual_lineage_handoffs')
MAXIMA=('max_projection_record_error','max_field_error','max_pair_energy_error','maximum_transport_record_error','maximum_transport_reader_error')
def read(path):return json.loads(Path(path).read_text())
def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k] for k in f.files}
def binding_check(b):assert checksum(b['tape_path'])==b['tape_sha256']
def historical(lane):
    parent=lane/'runs/h098_precision_correction_v1'
    return dict(read(parent/'historical_verdicts.json'),h098=read(parent/'main/summary.json')['findings'],
        h099=dict(classification='ENGINEERING_LEARNED_OUTPUT_CALIBRATION',numerical_checks=617088,
            reference_repair_equals_retained_decoder=True,adaptive_copy_tied=True,fresh_confirmation=False))
def legacy_fingerprints(lane):
    full=set();tasks=set();functions=set()
    for name in ('h095_fresh_context_v1','h097_connection_loss_v1','h099_reader_calibration_v1'):
        for path in sorted((lane/'runs'/name/'inputs').glob('*.npz')):
            tape=load(path);core={k:v for k,v in tape.items() if k not in ('calibration_polarity','body_mask','body_available')}
            full.add(m.digest(core));tasks.add(m.task_digest(core))
            for origin in m.ORIGINS:functions.add(m.digest({'responses':core['responses_'+origin]}))
    return full,tasks,functions
def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');lane=Path(config['lane_root']);parent=Path(config['parent'])
    assert checksum(parent/'checksums.json')==PIN==config['parent_manifest_sha256'];verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['passed']
    for name,pin in ANCESTOR_PINS.items():
        source=lane/'runs'/name;assert checksum(source/'checksums.json')==pin;verify(source,'checksums.json')
    verify_parent(lane/'runs/h097_connection_loss_v1',lane/'.cache/h097_threshold_probe_v1/parent_inventory.json')
    assert read(out/'historical_verdicts.json')==historical(lane)
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['networks']==m.NETWORKS==32 and config['engineering']==m.ENGINEERING==4 and config['root_seed']==m.SEED==100100
    assert config['modes']==list(m.MODES) and config['reference_events']==2 and config['measured_reference_values']==96
    assert config['neural_threshold']==1e-12 and config['exclusion_margin']==5e-14
    for receipt in config['qualification_receipts']:
        assert checksum(receipt['path'])==receipt['sha256'] and read(receipt['path'])['passed']
    legacy,legacy_tasks,legacy_functions=legacy_fingerprints(lane);seen=set();tasks=set();functions=set()
    for group in read(out/'input_bindings.json').values():
        for b in group:
            binding_check(b);tape=load(b['tape_path']);assert m.digest(tape)==b['tape_digest']
            for k,v in m.tapes(b['cohort'],b['block']).items():np.testing.assert_array_equal(tape[k],v)
            core=m.digest(m.core_tape(tape,'canonical'));task=m.task_digest(tape)
            assert core not in seen|legacy and task not in tasks|legacy_tasks;seen.add(core);tasks.add(task)
            for origin in m.ORIGINS:
                fingerprint=m.digest({'responses':tape['responses_'+origin]});assert fingerprint not in functions|legacy_functions;functions.add(fingerprint)
    assert len(seen)==len(tasks)==36 and len(functions)==72
    return config

def task(argument):
    out,binding=argument;out=Path(out);tick=time.perf_counter();block=binding['block'];stem=f'block_{block:03d}'
    try:
        binding_check(binding);tape=load(binding['tape_path']);polarity=tape['calibration_polarity']
        commitment=out/'commitments'/(stem+'.json');save(commitment,dict(**binding,committed_utc=utc(),acquisition_started=False));pin=checksum(commitment)
        raws={};graphs={};reloads=0
        for space in m.SPACES:
            raw,graph=m.run_tapes(m.core_tape(tape,space));path=out/'new_raw'/(stem+'_'+space+'.npz')
            with path.open('xb') as f:np.savez_compressed(f,**raw)
            save(out/'paths'/(stem+'_'+space+'.json'),graph);saved=load(path);assert saved.keys()==raw.keys()
            for k in raw:np.testing.assert_array_equal(saved[k],raw[k]);reloads+=1
            assert read(out/'paths'/(stem+'_'+space+'.json'))==graph;raws[space]=saved;graphs[space]=graph
        transported=audit.transport_graph(raws['canonical'],graphs['canonical'],raws['physical'],graphs['physical'],polarity)
        audits=[audit.network(raws[space],graphs[space],m.core_tape(tape,space)) for space in m.SPACES]
        bank=m.calibration_bank(polarity);calibration=audit.decoded_bank(bank,polarity)
        bundle=measure.acquire_outputs(raws['physical'],graphs['physical'],bank)
        flat={**bundle,**{'calibration__'+k:v for k,v in bank.items()},'target':tape['responses_own']}
        path=out/'raw'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**flat)
        saved=load(path);assert saved.keys()==flat.keys()
        for k,v in flat.items():np.testing.assert_array_equal(saved[k],v);reloads+=1
        bank={k[len('calibration__'):]:v for k,v in saved.items() if k.startswith('calibration__')}
        assert calibration==audit.decoded_bank(bank,polarity)
        output_checks=measure.verify_bundle(saved,raws['physical'],graphs['physical'],bank)
        tables=measure.network(saved,graphs['physical'],saved['target'],block)
        assert tables==measure.network(saved,graphs['physical'],saved['target'],block,True)
        result=dict(passed=True,block=block,**{k:sum(a[k] for a in audits) for k in ('numerical_checks','records','writer_packets','unique_neural_reads','unique_native_reads','pair_energy_comparisons','single_energy_comparisons')},
            **{k:max(a[k] for a in audits) for k in ('max_projection_record_error','max_field_error','max_pair_energy_error')},
            minimum_decision_boundary_distance=min(a['minimum_decision_boundary_distance'] for a in audits),
            maximum_transport_record_error=transported['maximum_record_error'],maximum_transport_reader_error=transported['maximum_reader_float_error'],
            transport_checks=transported['checks'],calibration_checks=2*calibration['checks'],decoded_output_checks=output_checks,
            saved_arrays_reloaded=reloads,independently_verified_rows=sum(map(len,tables.values())),physical_assay_cases=720,
            decoded_panel_rows=4320,ledger_rows=1056,actual_lineage_handoffs=sum(r['generation']>0 for r in graphs['physical']['lineages']),
            calibration=calibration,transport=transported,all_actual_packets_verified=True,all_new_trajectories_replayed=True,
            extra_task_labels=0,canonical_controls_are_not_samples=True,raw_sha256=checksum(path),
            acquisition_sha256={space:checksum(out/'new_raw'/(stem+'_'+space+'.npz')) for space in m.SPACES})
        save(out/'blocks'/(stem+'.json'),tables);save(out/'audits'/(stem+'.json'),result)
        assert checksum(commitment)==pin;binding_check(binding)
        return dict(**result,active_seconds=time.perf_counter()-tick,commitment_sha256=pin)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(error=traceback.format_exc(),utc=utc()));raise

def batch(out,bindings,workers,progress):
    for name in ('raw','new_raw','paths','blocks','audits','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();tasks=[];arguments=[(out,b) for b in bindings]
    if workers==1:
        for arg in arguments:tasks.append(task(arg));progress(completed_blocks=len(tasks),total_blocks=len(bindings))
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for future in as_completed([pool.submit(task,arg) for arg in arguments]):tasks.append(future.result());progress(completed_blocks=len(tasks),total_blocks=len(bindings))
    result=dict(workers=workers,active_seconds=time.perf_counter()-tick,tasks=sorted(tasks,key=lambda r:r['block']));save(out/'batch.json',result);return result

def finish(out,result,main):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']]
    summary=report.produce(out,blocks,[r['calibration'] for r in result['tasks']],main);n=len(blocks)
    checked=dict(passed=True,independent_networks=n,**{k:sum(r[k] for r in result['tasks']) for k in TOTALS},
        **{k:max(r[k] for r in result['tasks']) for k in MAXIMA},
        minimum_decision_boundary_distance=min(r['minimum_decision_boundary_distance'] for r in result['tasks']),
        findings=summary['findings'],serialized_rows_checked=summary['serialized_rows_checked'],actual_handoffs_per_lineage=2,
        historical_verdicts_unchanged=True,original_H097_acceptance='FAILED',population_qualification=False,next_campaign_launched=False)
    assert checked['records']==606*n and checked['writer_packets']==468*n and checked['actual_lineage_handoffs']==128*n
    assert checked['independently_verified_rows']==summary['diagnostic_rows']==5416*n
    save(out/'verification.json',checked);return checked

def execute(out):
    from h100 import fixtures
    assert ROOT==out/'source','execute only frozen source'
    tick=time.perf_counter();state=dict(state='RUNNING',phase='verify_inputs',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        state.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick);save(out/'STATUS.json',state);print(json.dumps(state),flush=True)
    admissions=[]
    def admit(phase,workers):
        counts=dict(completed_blocks=0,total_blocks=m.NETWORKS if phase=='main' else m.ENGINEERING) if phase in ('main','engineering_serial','engineering_parallel') else {}
        progress(phase=phase+'_admission',workers=0,**counts);admissions.append(capacity(out/(phase+'_admission.json'),workers,progress));progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();admit('verify_inputs',1);config=verify_inputs(out);bindings=read(out/'input_bindings.json')
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture',bindings['engineering'][0]);save(out/'fixtures.json',tests)
        results={}
        for name,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(name,workers);results[name]=batch(out/name,bindings['engineering'],workers,progress)
        equivalent=compare(out);serial,parallel=[results[k]['active_seconds'] for k in ('engineering_serial','engineering_parallel')]
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*(m.NETWORKS/m.ENGINEERING)+90
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,threshold=1.15,**equivalent,
            main_forecast_seconds=forecast,decided_before_main=True,decided_utc=utc());save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file());needed=int(4*size*(m.NETWORKS/m.ENGINEERING)+200_000_000)
        free=shutil.disk_usage(out).free;assert free>needed,'insufficient free disk for retained evidence'
        save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_main_bytes=needed,free_bytes=free))
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers);result=batch(out/'main',bindings['main'],workers,progress)
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        waits=sum(a['wait_seconds'] for a in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=tests['count'],engineering=engineering,main=main,worker_choice=choice,
            capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,source_files_unchanged=len(FILES),
            historical_verdicts_unchanged=True,original_H097_acceptance='FAILED',fresh_networks=32,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True);save(out/'COMPLETE.json',state)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json']);verify(out,'checksums.json')
        receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),
            main_checks=main['numerical_checks'],main_rows=main['independently_verified_rows'],findings=main['findings'],fresh_networks=32,
            original_H097_acceptance='FAILED',historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',state)
        raise

def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name=='h100_fresh_reader_turnover_v1'
    receipt=ROOT/'.cache/h100_closeout_v1.json'
    assert not any(p.exists() for p in (out,out.with_suffix('.log'),out.with_suffix('.pid'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h099_reader_calibration_v1';assert checksum(parent/'checksums.json')==PIN;verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['passed']
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    assert len(FILES)==len(set(FILES));out.mkdir();(out/'inputs').mkdir()
    legacy,legacy_tasks,legacy_functions=legacy_fingerprints(ROOT);seen=set();tasks=set();functions=set();bindings={}
    for cohort,key,n in (('engineering','engineering',m.ENGINEERING),('confirmation','main',m.NETWORKS)):
        bindings[key]=[]
        for block in range(n):
            tape=m.tapes(cohort,block);core=m.digest(m.core_tape(tape,'canonical'));task=m.task_digest(tape)
            assert core not in seen|legacy and task not in tasks|legacy_tasks;seen.add(core);tasks.add(task)
            for origin in m.ORIGINS:
                fingerprint=m.digest({'responses':tape['responses_'+origin]});assert fingerprint not in functions|legacy_functions;functions.add(fingerprint)
            path=out/'inputs'/f'{cohort}_{block:03d}.npz'
            with path.open('xb') as f:np.savez_compressed(f,**tape)
            bindings[key].append(dict(block=block,cohort=cohort,tape_path=str(path),tape_sha256=checksum(path),tape_digest=m.digest(tape),task_digest=task))
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    qualifications=[]
    for name in ('h098_completion_verification_v1.json','h099_completion_verification_v1.json','h100_preflight_v1/result.json'):
        path=ROOT/'.cache'/name;assert read(path)['passed'];qualifications.append(dict(path=str(path),sha256=checksum(path)))
    save(out/'input_bindings.json',bindings);save(out/'historical_verdicts.json',historical(ROOT))
    save(out/'config.json',dict(experiment='H100',created_utc=utc(),lane_root=str(ROOT),parent=str(parent),parent_manifest_sha256=PIN,
        python=sys.version,numpy=np.__version__,root_seed=m.SEED,networks=m.NETWORKS,engineering=m.ENGINEERING,modes=list(m.MODES),
        observed_task_responses=8,actual_handoffs_per_lineage=2,reference_events=2,measured_reference_values=96,learned_calibration_signs=48,
        neural_threshold=1e-12,exclusion_margin=5e-14,neural_record_tolerance=4e-14,native_fit_tolerance=2e-12,field_energy_tolerance=2e-11,
        information_unequal_copy_comparison_labelled=True,calibration_affects_recurrence=False,classification='FRESH_FINITE_COHORT_CONFIRMATION',
        qualification_receipts=qualifications,legacy_tapes_checked=len(legacy),legacy_tasks_checked=len(legacy_tasks),legacy_functions_checked=len(legacy_functions),
        input_tapes_committed=36,main_outcomes_generated_before_freeze=False,worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,
        closeout_receipt=str(receipt),original_H097_acceptance='FAILED',next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h100/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h100/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,
        forecast_over_600_seconds=True,engineering_and_exact_benchmarks_gate_main=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',type=Path);mode.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    else:execute(args.execute.resolve())
