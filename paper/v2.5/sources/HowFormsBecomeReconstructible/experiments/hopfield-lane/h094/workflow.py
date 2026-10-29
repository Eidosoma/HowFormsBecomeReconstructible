"""Frozen completion experiment, CPU admission, exact benchmarks and closeout."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,multiprocessing,os,shutil,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h061.workflow import watch
from h063.workflow import compare
from h093.workflow import FILES as PARENT_FILES
from h094 import model as m,audit,measure,geometry,report,fixtures

PIN='fa7f62e97c617f8a2812b70e36eff8f964212625c005fb82b7a3ede6f565ac92'
FILES=PARENT_FILES+['h093/INTERPRETATION.md']+['h094/'+name for name in
    ('PROTOCOL.md','model.py','dynamics.py','reference.py','audit.py','measure.py','geometry.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','source_score_rows','baseline_geometry_rows','baseline_rows_anchored','new_records','new_writer_packets',
    'completion_fits','unchanged_founder_and_prequery_arrays','transition_rows','new_unique_neural_reads','new_unique_native_reads','new_assay_cases','pair_energy_comparisons','single_energy_comparisons',
    'geometry_checks','independently_verified_rows','saved_array_reload_checks','saved_graph_reload_checks','saved_raw_bundles')

def read(path):return json.loads(Path(path).read_text())
def historical(parent):return dict(read(parent/'historical_verdicts.json'),h093=read(parent/'main/summary.json')['findings'],h093_primary_scores=read(parent/'main/summary.json')['primary_scores'])
def binding_check(binding):
    for item in binding['files']:assert checksum(item['path'])==item['sha256'],item['path']

def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['parent'])
    assert checksum(parent/'checksums.json')==PIN==config['parent_manifest_sha256'];verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['integrity_passed'] and read(out/'historical_verdicts.json')==historical(parent)
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['networks']==m.NETWORKS==16 and config['engineering']==m.ENGINEERING==4
    assert config['conditions']==list(m.CONDITIONS) and config['original_root_seed']==m.SEED==89089 and config['actual_handoffs']==2
    assert config['observed_labels_per_packet']==8 and config['generated_responses_per_packet']==16
    assert config['interaction_strength']==1 and config['interaction_active_in_gap'] and config['copy_all_interactions']
    assert config['query_hold_sweeps']==1 and config['held_context_sites']==32 and not config['true_context_resupplied'] and config['extra_context_buffer_values']==0
    for group in read(out/'input_bindings.json').values():
        for binding in group:binding_check(binding)
    return config

def task(argument):
    out,binding=argument;tick=time.perf_counter();block=binding['block'];stem=f'block_{block:03d}'
    try:
        binding_check(binding);commitment=out/'commitments'/(stem+'.json')
        save(commitment,dict(**binding,committed_utc=utc(),new_acquisition_started=False));pin=checksum(commitment)
        source=fixtures.load(binding['source_raw']);original_graph=read(binding['source_graph']);source_rows=read(binding['source_rows'])
        cohort='engineering' if binding['cohort']=='engineering' else 'development';tape={k:source[k].copy() for k in m.tapes(cohort,block)}
        raw,graph=m.run_tapes(tape);new_path=out/'new_raw'/(stem+'_protected.npz')
        with new_path.open('xb') as f:np.savez_compressed(f,**raw)
        save(out/'paths'/(stem+'_protected.json'),graph);reloaded=fixtures.load(new_path);assert reloaded.keys()==raw.keys()
        for key in raw:np.testing.assert_array_equal(raw[key],reloaded[key],err_msg=key)
        reloads=len(raw);raw=reloaded;assert read(out/'paths'/(stem+'_protected.json'))==graph
        unchanged=fixtures.baseline_boundary_checks(source,original_graph,raw,graph)
        checked=audit.network(raw,graph,cohort,block)
        rows={};geo={};diagnostics={};metas={};graphs={};transitions={};outputs=[];cases=None;geochecks=[];row_checks=0
        for condition,r,g in [('unprotected',source,original_graph),('protected',raw,graph)]:
            rows[condition]=measure.network(r,g,block,condition=='protected')
            assert rows[condition]==measure.network(r,g,block,condition=='protected',True);row_checks+=sum(map(len,rows[condition].values()))
            diagnostics[condition],metas[condition],c=geometry.extract(r,g,condition=='protected');geochecks.append(c)
            geo[condition]=geometry.tables(diagnostics[condition],metas[condition],block);row_checks+=geometry.verify(diagnostics[condition],metas[condition],geo[condition])
            transitions[condition]=measure.transitions(r,g,block)
            assert transitions[condition]==measure.transitions(r,g,block,True);row_checks+=len(transitions[condition])
            output,metadata=measure.old.case_outputs(r,g);outputs.append(output);graphs[condition]=g
            if cases is None:cases=metadata
            else:assert cases==metadata
        anchored=measure.anchor(rows['unprotected'],geo['unprotected'],source_rows)
        completions=measure.completion_rows(raw,graph,block);assert completions==measure.completion_rows(raw,graph,block,True);row_checks+=len(completions)
        outputs=np.stack(outputs);combined=measure.combine(rows,geo,completions,outputs,cases,tape['responses_own'],block,transitions)
        assert combined['arm_effects']==measure.arm_effects(outputs,cases,tape['responses_own'],block,True);row_checks+=360
        flat=dict(comparison_outputs=outputs,comparison_target=tape['responses_own'])
        for condition in m.CONDITIONS:flat.update({condition+'_geometry__'+k:v for k,v in diagnostics[condition].items()})
        path=out/'raw'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**flat)
        saved=fixtures.load(path);assert saved.keys()==flat.keys()
        for key in flat:np.testing.assert_array_equal(saved[key],flat[key])
        reloads+=len(flat);geo_reload=0
        for condition in m.CONDITIONS:
            prefix=condition+'_geometry__';bundle={k[len(prefix):]:v for k,v in saved.items() if k.startswith(prefix)}
            geo_reload+=geometry.validate(bundle,metas[condition])
        meta=dict(graphs=graphs,geometry_metadata=metas,cases=cases);save(out/'paths'/(stem+'.json'),meta)
        assert read(out/'paths'/(stem+'.json'))==meta
        assert row_checks==sum(map(len,combined.values()))==7552+sum(len(rows[c]['trajectories']) for c in m.CONDITIONS)
        result=dict(passed=True,block=block,unchanged_founder_and_prequery_arrays=unchanged,transition_rows=768,numerical_checks=checked['numerical_checks']+unchanged+sum(c['geometry_checks'] for c in geochecks)+geo_reload,
            source_score_rows=1440,baseline_geometry_rows=288,baseline_rows_anchored=anchored,new_records=checked['records'],
            new_writer_packets=checked['writer_packets'],completion_fits=checked['completion_packets'],new_unique_neural_reads=checked['unique_neural_reads'],
            new_unique_native_reads=checked['unique_native_reads'],new_assay_cases=checked['assay_cases'],pair_energy_comparisons=checked['pair_energy_comparisons'],
            single_energy_comparisons=checked['single_energy_comparisons'],geometry_checks=sum(c['geometry_checks'] for c in geochecks)+geo_reload,
            independently_verified_rows=row_checks,saved_array_reload_checks=reloads,saved_graph_reload_checks=2,saved_raw_bundles=2,
            max_projection_record_error=checked['max_projection_record_error'],max_field_error=max([checked['max_field_error']]+[c['geometry_max_field_error'] for c in geochecks]),
            max_pair_energy_error=checked['max_pair_energy_error'],max_geometry_energy_error=max(c['geometry_max_energy_error'] for c in geochecks),
            minimum_decision_boundary_distance=min([checked['minimum_decision_boundary_distance']]+[c['geometry_minimum_boundary_distance'] for c in geochecks]),
            raw_sha256=checksum(path),new_raw_sha256=checksum(new_path),metadata_sha256=checksum(out/'paths'/(stem+'.json')),
            all_new_trajectories_replayed=True,all_actual_packets_verified=True,heldout_truth_excluded_from_writing=True,copy_invariance=True)
        save(out/'blocks'/(stem+'.json'),combined);save(out/'audits'/(stem+'.json'),result)
        assert checksum(commitment)==pin;binding_check(binding)
        return dict(**result,active_seconds=time.perf_counter()-tick,commitment_sha256=pin)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(error=traceback.format_exc(),utc=utc()));raise

def batch(out,bindings,workers,progress):
    for name in ('raw','new_raw','paths','blocks','audits','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();tasks=[];arguments=[(out,binding) for binding in bindings]
    if workers==1:
        for arg in arguments:tasks.append(task(arg));progress(completed_blocks=len(tasks),total_blocks=len(bindings))
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for future in as_completed([pool.submit(task,arg) for arg in arguments]):tasks.append(future.result());progress(completed_blocks=len(tasks),total_blocks=len(bindings))
    result=dict(workers=workers,active_seconds=time.perf_counter()-tick,tasks=sorted(tasks,key=lambda r:r['block']))
    save(out/'batch.json',result);return result

def finish(out,result,main):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']];summary=report.produce(out,blocks,main);n=len(blocks)
    checked=dict(passed=True,independent_networks=n,**{key:sum(t[key] for t in result['tasks']) for key in TOTALS},
        serialized_rows_checked=summary['serialized_rows_checked'],actual_handoffs=2,
        **{key:max(t[key] for t in result['tasks']) for key in ('max_field_error','max_pair_energy_error','max_geometry_energy_error','max_projection_record_error')},
        minimum_decision_boundary_distance=min(t['minimum_decision_boundary_distance'] for t in result['tasks']),
        all_new_trajectories_replayed=True,all_actual_packets_verified=True,baseline_anchored=True,findings=summary['findings'],
        comparative_superiority_qualified=False,new_population_qualification=False)
    assert checked['source_score_rows']==1440*n and checked['baseline_geometry_rows']==288*n
    assert checked['new_records']==303*n and checked['new_writer_packets']==checked['completion_fits']==234*n and checked['new_assay_cases']==720*n
    assert checked['transition_rows']==768*n
    assert checked['independently_verified_rows']==summary['diagnostic_rows'];save(out/'verification.json',checked);return checked

def execute(out):
    assert ROOT==out/'source','Execute frozen sources only'
    tick=time.perf_counter();status=dict(state='RUNNING',phase='verify_inputs',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        status.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick);save(out/'STATUS.json',status);print(json.dumps(status),flush=True)
    admissions=[]
    def admit(phase,workers):
        counts=dict(completed_blocks=0,total_blocks=m.NETWORKS if phase=='main' else m.ENGINEERING) if phase in ('main','engineering_serial','engineering_parallel') else {}
        progress(phase=phase+'_admission',workers=0,**counts);admissions.append(capacity(out/(phase+'_admission.json'),workers,progress));progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();config=verify_inputs(out);bindings=read(out/'input_bindings.json')
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture',bindings['engineering'][0]);save(out/'fixtures.json',tests);results={}
        for group,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(group,workers);results[group]=batch(out/group,bindings['engineering'],workers,progress)
        equivalent=compare(out);serial,parallel=[results[k]['active_seconds'] for k in ('engineering_serial','engineering_parallel')]
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*4+90
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,
            threshold=1.15,**equivalent,main_forecast_seconds=forecast,decided_before_main=True,decided_utc=utc())
        save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file());needed=int(4*size*4+200_000_000)
        assert shutil.disk_usage(out).free>needed,'insufficient free disk for retained evidence'
        save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_main_bytes=needed,free_bytes=shutil.disk_usage(out).free,checked_before_main=True))
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers);result=batch(out/'main',bindings['main'],workers,progress)
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        prior=read(Path(config['parent'])/'main/summary.json')['primary_scores'];current=read(out/'main/summary.json')['cases']
        for name,panel,g,reader in [('heldout_g0','heldout',0,'pair'),('trained_g2','trained',2,'ordinary'),('heldout_g2','heldout',2,'ordinary')]:
            row=report.score(current,'unprotected',panel,g,reader)
            for key in ('task_correct','query_correct','bit_correct','exact_correct'):assert row[key]==prior[name][key]
        waits=sum(a['wait_seconds'] for a in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=tests['count'],engineering=engineering,main=main,worker_choice=choice,
            capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,source_files_unchanged=len(FILES),parent_unchanged=True,
            historical_verdicts_unchanged=True,new_observed_labels=0,completion_fits=main['completion_fits'],forecast_predictors=0,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True);save(out/'COMPLETE.json',status)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json']);verify(out,'checksums.json')
        receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),main_rows=main['independently_verified_rows'],
            main_checks=main['numerical_checks'],findings=main['findings'],completion_fits=main['completion_fits'],historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',phase=status['phase'],failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',status)
        raise

def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h094_context_hold_')
    suffix=out.name.removeprefix('h094_context_hold_');receipt=ROOT/'.cache'/('h094_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.pid'),out.with_suffix('.log'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h093_interactions_v1';assert checksum(parent/'checksums.json')==PIN;verify(parent,'checksums.json');assert read(parent/'COMPLETE.json')['integrity_passed']
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    assert len(FILES)==len(set(FILES));manifest=read(parent/'checksums.json');bindings={}
    for cohort,group,n in (('engineering','engineering_serial',4),('main','main',16)):
        bindings[cohort]=[]
        for block in range(n):
            stem=f'block_{block:03d}'
            names=dict(source_raw=f'{group}/new_raw/{stem}_interactions.npz',source_graph=f'{group}/paths/{stem}_interactions.json',source_rows=f'{group}/blocks/{stem}.json')
            binding=dict(block=block,cohort=cohort,**{k:str(parent/v) for k,v in names.items()},files=[dict(path=str(parent/v),sha256=manifest[v]) for v in names.values()])
            binding_check(binding);bindings[cohort].append(binding)
    out.mkdir(parents=True,exist_ok=False)
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    save(out/'input_bindings.json',bindings);save(out/'historical_verdicts.json',historical(parent))
    save(out/'config.json',dict(experiment='H094',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,parent=str(parent),parent_manifest_sha256=PIN,
        networks=16,engineering=4,original_root_seed=89089,conditions=list(m.CONDITIONS),observed_labels_per_packet=8,generated_responses_per_packet=16,
        actual_handoffs=2,generations=[0,1,2],capability_task_fraction=.75,source_gap=.25,interaction_strength=1,interaction_active_in_gap=True,copy_all_interactions=True,query_hold_sweeps=1,held_context_sites=32,true_context_resupplied=False,extra_context_buffer_values=0,classification='exposed-cohort internal-context transition intervention',
        worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,closeout_receipt=str(receipt),watch_receipt=str(ROOT/'.cache'/('h094_watch_'+suffix+'.json')),next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h094/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h094/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,short_run_watcher_authorized=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    for key in ('prepare','execute','watch'):mode.add_argument('--'+key,type=Path)
    args=p.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
