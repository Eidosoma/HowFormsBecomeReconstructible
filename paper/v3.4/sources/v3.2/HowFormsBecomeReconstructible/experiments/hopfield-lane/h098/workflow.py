"""Precision-corrected rerun of an exposed cohort, with complete convergence gates."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,multiprocessing,os,shutil,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h061.workflow import watch
from h063.workflow import compare
from h097.workflow import FILES as PARENT_FILES,boundary_checks,read,load
from h097 import measure,diagnostics
from h098 import model as m,compiler,audit,convergence,report
PIN='2e62d394cdd37450891e921607835b7cef3b52988bf5457c76b3ed15219707aa'
INVENTORY_PIN='a84bc47fd3812d3dc3e7473f28d21c4fdf807270adf9a62c2ca844d3d18a92f7'
PROBE_PINS={'h097_threshold_probe_v1':'912e54cb8c2a7ff9ef5de924e66a4003248bd83915c761f591f0331c93521622',
    'h097_relevant_boundary_probe_v2':'19c1de1d7b21d69e3f802ac83128cbca3e6d88570ebe36cad5fc18cc8d8e3e82'}
FILES=PARENT_FILES+['h097/NUMERICAL_DIAGNOSIS.md']+['h098/'+name for name in
    ('PROTOCOL.md','compiler.py','model.py','audit.py','convergence.py','local_checks.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','records','writer_packets','completion_fits','unique_neural_reads','unique_native_reads',
    'assay_cases','candidate_records','candidate_writer_packets','candidate_assay_cases',
    'panel_case_rows','transition_rows','stability_rows','unchanged_boundary_arrays','pair_energy_comparisons',
    'single_energy_comparisons','diagnostic_checks','independently_verified_rows','saved_array_reload_checks',
    'saved_graph_reload_checks','saved_raw_bundles','precision_comparison_checks','intact_anchor_arrays')

def historical(parent):
    return dict(read(parent/'historical_verdicts.json'),h097=dict(numerical_acceptance='FAILED',
        full_cohort_scientific_verdict_accepted=False,acquired_main_networks=16,passing_main_audits=15,
        affected_block=13,diagnosis='WRITER_PRECISION_SENSITIVE_READER',cohort_exposed=True))

def verify_parent(parent,inventory):
    assert checksum(parent/'freeze.json')==PIN
    assert read(parent/'FAILED.json')['state']=='FAILED' and not (parent/'COMPLETE.json').exists()
    assert checksum(inventory)==INVENTORY_PIN
    files=read(inventory)['files'];assert len(files)==635
    assert {str(p.relative_to(parent)) for p in parent.rglob('*') if p.is_file()}==set(files)
    for name,pin in files.items():assert checksum(parent/name)==pin,name
    return len(files)

def binding_check(binding):
    for prefix in ('tape','source_tape','intact_raw','intact_graph'):
        assert checksum(binding[prefix+'_path'])==binding[prefix+'_sha256'],prefix
    assert binding['tape_sha256']==binding['source_tape_sha256']

def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['parent'])
    verify_parent(parent,out/'parent_inventory.json')
    assert read(out/'historical_verdicts.json')==historical(parent)
    assert config['parent_freeze_sha256']==PIN and config['cohort_reused_from']=='H097'
    assert config['classification']=='NUMERICAL_CORRECTION_ON_EXPOSED_COHORT' and not config['fresh_confirmation']
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['networks']==m.NETWORKS==16 and config['engineering']==m.ENGINEERING==4
    assert config['root_seed']==m.SEED==97097 and config['conditions']==list(m.CONDITIONS)
    assert config['precisions']==list(m.PRECISIONS)
    assert config['observed_labels_per_packet']==8 and config['actual_handoffs']==2
    assert config['available_edges_per_child']==4064 and config['available_channels_per_child']==24
    assert config['regularization']==compiler.RIDGE==.1 and not config['copy_has_protected_blueprint']
    assert config['solver_relative_tolerances']==compiler.TOLERANCES and config['solver_max_iterations']==512
    assert config['neural_threshold']==1e-12 and config['exclusion_margin']==5e-14
    assert config['field_energy_tolerance']==2e-11 and config['normal_equation_tolerance']==5e-10
    assert np.finfo(np.longdouble).eps<np.finfo(np.float64).eps/1000
    for item in config['diagnostic_bindings']:
        assert checksum(item['path'])==item['sha256']
    for name,pin in PROBE_PINS.items():
        probe=Path(config['lane_root'])/'.cache'/name;assert checksum(probe/'checksums.json')==pin;verify(probe,'checksums.json')
    seen=set();bindings=read(out/'input_bindings.json')
    for group in bindings.values():
        for b in group:
            binding_check(b);assert b['tape_digest'] not in seen;seen.add(b['tape_digest'])
            tape=load(b['tape_path']);assert m.digest(tape)==b['tape_digest']
            for k,v in m.tapes(b['cohort'],b['block']).items():np.testing.assert_array_equal(tape[k],v)
    assert len(seen)==20
    return config

def task(argument):
    out,binding=argument;out=Path(out);tick=time.perf_counter();block=binding['block'];stem=f'block_{block:03d}'
    try:
        binding_check(binding);tape=load(binding['tape_path'])
        commitment=out/'commitments'/(stem+'.json');save(commitment,dict(**binding,committed_utc=utc(),acquisition_started=False));pin=checksum(commitment)
        acquired={};all_graphs={};audits=[];reloads=0
        # Preserve all four acquisitions before either precision can fail an audit.
        for precision in m.PRECISIONS:
            acquired[precision]={};all_graphs[precision]={}
            for condition in m.CONDITIONS:
                tag=condition if precision=='candidate' else precision+'_'+condition
                raw,graph=m.run_tapes(tape,condition,precision);path=out/'new_raw'/(stem+'_'+tag+'.npz')
                with path.open('xb') as f:np.savez_compressed(f,**raw)
                save(out/'paths'/(stem+'_'+tag+'.json'),graph)
                saved=load(path);assert saved.keys()==raw.keys()
                for k in raw:np.testing.assert_array_equal(raw[k],saved[k],err_msg=k)
                reloads+=len(raw);assert read(out/'paths'/(stem+'_'+tag+'.json'))==graph
                acquired[precision][condition]=saved;all_graphs[precision][condition]=graph
        converged={condition:convergence.compare(acquired['candidate'][condition],all_graphs['candidate'][condition],
            acquired['refined'][condition],all_graphs['refined'][condition]) for condition in m.CONDITIONS}
        all_raw=acquired['candidate'];graphs=all_graphs['candidate']
        anchor=convergence.intact_anchor(all_raw['intact'],graphs['intact'],load(binding['intact_raw_path']),read(binding['intact_graph_path']))
        save(out/'audits'/(stem+'_convergence.json'),dict(passed=True,conditions=converged,intact_anchor=anchor))
        unchanged=0
        for precision in m.PRECISIONS:
            unchanged+=boundary_checks(acquired[precision],all_graphs[precision])
            for condition in m.CONDITIONS:
                checked=audit.network(acquired[precision][condition],all_graphs[precision][condition],binding['cohort'],block,condition,precision)
                save(out/'audits'/(stem+'_'+precision+'_'+condition+'.json'),checked);audits.append(checked)
        rows={};completed={};transitions={};writers={};probes={};stability={};outputs=[];cases=None;probechecks=0;rowchecks=0
        for condition in m.CONDITIONS:
            raw=all_raw[condition];graph=graphs[condition]
            rows[condition]=measure.network(raw,graph,block)
            assert rows[condition]==measure.network(raw,graph,block,True);rowchecks+=sum(map(len,rows[condition].values()))
            completed[condition]=measure.completion_rows(raw,graph,block)
            assert completed[condition]==measure.completion_rows(raw,graph,block,True);rowchecks+=len(completed[condition])
            transitions[condition]=measure.transitions(raw,graph,block)
            assert transitions[condition]==measure.transitions(raw,graph,block,True);rowchecks+=len(transitions[condition])
            writers[condition]=measure.writers(raw,graph,block);rowchecks+=len(writers[condition])
            probes[condition],checked=diagnostics.extract(raw,graph);probechecks+=checked['checks']
            stability[condition]=diagnostics.tables(raw,graph,probes[condition],block)
            assert stability[condition]==diagnostics.tables(raw,graph,probes[condition],block,True);rowchecks+=len(stability[condition])
            output,metadata=measure.case_outputs(raw,graph);outputs.append(output)
            if cases is None:cases=metadata
            else:assert cases==metadata
        outputs=np.stack(outputs);combined=measure.combine(rows,completed,transitions,writers,stability,outputs,cases,tape['responses_own'],block)
        assert combined['arm_effects']==measure.arm_effects(outputs,cases,tape['responses_own'],block,True);rowchecks+=480
        flat=dict(comparison_outputs=outputs,comparison_target=tape['responses_own'])
        for condition in m.CONDITIONS:flat.update({condition+'_stability__'+k:v for k,v in probes[condition].items()})
        path=out/'raw'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**flat)
        saved=load(path);assert saved.keys()==flat.keys()
        for k in flat:np.testing.assert_array_equal(saved[k],flat[k])
        reloads+=len(flat)
        for condition in m.CONDITIONS:
            prefix=condition+'_stability__';bundle={k[len(prefix):]:v for k,v in saved.items() if k.startswith(prefix)}
            probechecks+=diagnostics.verify(all_raw[condition],graphs[condition],bundle)
        meta=dict(graphs=graphs,cases=cases);save(out/'paths'/(stem+'.json'),meta);assert read(out/'paths'/(stem+'.json'))==meta
        assert rowchecks==sum(map(len,combined.values()))
        result=dict(passed=True,block=block,numerical_checks=sum(a['numerical_checks'] for a in audits)+unchanged+probechecks,
            records=sum(a['records'] for a in audits),writer_packets=sum(a['writer_packets'] for a in audits),completion_fits=sum(a['completion_packets'] for a in audits),
            unique_neural_reads=sum(a['unique_neural_reads'] for a in audits),unique_native_reads=sum(a['unique_native_reads'] for a in audits),
            assay_cases=3840,candidate_records=734,candidate_writer_packets=596,candidate_assay_cases=1920,panel_case_rows=3840,transition_rows=1152,stability_rows=1296,unchanged_boundary_arrays=unchanged,
            pair_energy_comparisons=sum(a['pair_energy_comparisons'] for a in audits),single_energy_comparisons=sum(a['single_energy_comparisons'] for a in audits),
            diagnostic_checks=probechecks,independently_verified_rows=rowchecks,saved_array_reload_checks=reloads,saved_graph_reload_checks=5,saved_raw_bundles=5,
            precision_comparison_checks=sum(sum(a[k] for k in ('record_arrays','discrete_reader_arrays','native_reader_arrays','logical_read_uses'))+4 for a in converged.values()),
            intact_anchor_arrays=anchor['exact_arrays'],maximum_precision_coupling_difference=max(a['maximum_coupling_difference'] for a in converged.values()),
            both_precisions_converged=True,intact_baseline_preserved=True,original_exclusion_guard_unchanged=True,
            max_writer_normal_residual=max(a['max_writer_normal_residual'] for a in audits),max_field_error=max(a['max_field_error'] for a in audits),
            max_pair_energy_error=max(a['max_pair_energy_error'] for a in audits),minimum_decision_boundary_distance=min(a['minimum_decision_boundary_distance'] for a in audits),
            raw_sha256=checksum(path),acquisition_sha256={level+'_'+c:checksum(out/'new_raw'/(stem+'_'+(c if level=='candidate' else level+'_'+c)+'.npz')) for level in m.PRECISIONS for c in m.CONDITIONS},metadata_sha256=checksum(out/'paths'/(stem+'.json')),
            both_conditions_newly_acquired=True,both_precisions_newly_acquired=True,exposed_cohort_reused=True,all_new_trajectories_replayed=True,all_actual_packets_verified=True,heldout_truth_excluded_from_writing=True,physical_constraints_verified=True)
        save(out/'blocks'/(stem+'.json'),combined);save(out/'audits'/(stem+'.json'),result)
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
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']];summary=report.produce(out,blocks,main);n=len(blocks)
    checked=dict(passed=True,independent_networks=n,**{key:sum(t[key] for t in result['tasks']) for key in TOTALS},
        serialized_rows_checked=summary['serialized_rows_checked'],actual_handoffs=2,
        **{key:max(t[key] for t in result['tasks']) for key in ('max_field_error','max_pair_energy_error','max_writer_normal_residual')},
        minimum_decision_boundary_distance=min(t['minimum_decision_boundary_distance'] for t in result['tasks']),
        all_new_trajectories_replayed=True,all_actual_packets_verified=True,both_conditions_newly_acquired=True,both_precisions_newly_acquired=True,physical_constraints_verified=True,
        both_precisions_converged=all(t['both_precisions_converged'] for t in result['tasks']),
        intact_baseline_preserved=all(t['intact_baseline_preserved'] for t in result['tasks']),
        maximum_precision_coupling_difference=max(t['maximum_precision_coupling_difference'] for t in result['tasks']),
        original_H097_acceptance='FAILED',exposed_cohort_reused=True,fresh_confirmation=False,findings=summary['findings'],
        comparative_superiority_qualified=False,new_population_qualification=False)
    assert checked['records']==1468*n and checked['writer_packets']==checked['completion_fits']==1192*n
    assert checked['assay_cases']==3840*n and checked['transition_rows']==1152*n and checked['panel_case_rows']==3840*n
    assert checked['candidate_records']==734*n and checked['candidate_writer_packets']==596*n and checked['candidate_assay_cases']==1920*n
    assert checked['both_precisions_converged'] and checked['intact_baseline_preserved']
    assert checked['independently_verified_rows']==summary['diagnostic_rows'];save(out/'verification.json',checked);return checked

def execute(out):
    from h098 import fixtures
    assert ROOT==out/'source','Execute frozen sources only'
    tick=time.perf_counter();status=dict(state='RUNNING',phase='verify_inputs',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        status.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick);save(out/'STATUS.json',status);print(json.dumps(status),flush=True)
    admissions=[]
    def admit(phase,workers):
        counts=dict(completed_blocks=0,total_blocks=m.NETWORKS if phase=='main' else m.ENGINEERING) if phase in ('main','engineering_serial','engineering_parallel') else {}
        progress(phase=phase+'_admission',workers=0,**counts);admissions.append(capacity(out/(phase+'_admission.json'),workers,progress));progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();admit('verify_inputs',1);config=verify_inputs(out);bindings=read(out/'input_bindings.json')
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture',bindings['engineering'][0]);save(out/'fixtures.json',tests);results={}
        for group,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(group,workers);results[group]=batch(out/group,bindings['engineering'],workers,progress)
        equivalent=compare(out);serial,parallel=[results[k]['active_seconds'] for k in ('engineering_serial','engineering_parallel')]
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*(m.NETWORKS/m.ENGINEERING)+90
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,threshold=1.15,**equivalent,
            main_forecast_seconds=forecast,decided_before_main=True,decided_utc=utc());save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file());needed=int(4*size*(m.NETWORKS/m.ENGINEERING)+200_000_000)
        assert shutil.disk_usage(out).free>needed,'insufficient free disk for retained evidence'
        save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_main_bytes=needed,free_bytes=shutil.disk_usage(out).free,checked_before_main=True))
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers);result=batch(out/'main',bindings['main'],workers,progress)
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        waits=sum(a['wait_seconds'] for a in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=tests['count'],engineering=engineering,main=main,worker_choice=choice,
            capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,source_files_unchanged=len(FILES),parent_unchanged=True,
            historical_verdicts_unchanged=True,original_H097_acceptance='FAILED',original_H097_files_unchanged=635,
            exposed_cohort_reused=True,fresh_confirmation=False,both_precisions_converged=True,intact_baseline_preserved=True,new_observed_labels_per_packet=0,completion_fits=main['completion_fits'],forecast_predictors=0,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True);save(out/'COMPLETE.json',status)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json']);verify(out,'checksums.json')
        receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),main_rows=main['independently_verified_rows'],
            main_checks=main['numerical_checks'],both_precisions_converged=True,intact_baseline_preserved=True,original_H097_acceptance='FAILED',exposed_cohort_reused=True,fresh_confirmation=False,findings=main['findings'],completion_fits=main['completion_fits'],historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',phase=status['phase'],failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',status)
        raise

def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h098_precision_correction_')
    suffix=out.name.removeprefix('h098_precision_correction_');receipt=ROOT/'.cache'/('h098_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.pid'),out.with_suffix('.log'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h097_connection_loss_v1';inventory=ROOT/'.cache/h097_threshold_probe_v1/parent_inventory.json'
    verify_parent(parent,inventory)
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    assert len(FILES)==len(set(FILES));out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir();bindings={}
    original=read(parent/'input_bindings.json');original_files=read(inventory)['files']
    for key in ('engineering','main'):
        bindings[key]=[];group='engineering_serial' if key=='engineering' else 'main'
        for b in original[key]:
            src=Path(b['tape_path']);assert checksum(src)==b['tape_sha256']
            path=out/'inputs'/src.name;shutil.copyfile(src,path);stem=f"block_{b['block']:03d}"
            anchor_raw=parent/group/'new_raw'/(stem+'_intact.npz');anchor_graph=parent/group/'paths'/(stem+'_intact.json')
            bound=dict(b,tape_path=str(path),tape_sha256=checksum(path),source_tape_path=str(src),source_tape_sha256=b['tape_sha256'],
                intact_raw_path=str(anchor_raw),intact_raw_sha256=original_files[str(anchor_raw.relative_to(parent))],
                intact_graph_path=str(anchor_graph),intact_graph_sha256=original_files[str(anchor_graph.relative_to(parent))])
            binding_check(bound);bindings[key].append(bound)
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    shutil.copyfile(inventory,out/'parent_inventory.json')
    diagnostics=[]
    for src,name in ((ROOT/'.cache/h097_numerical_diagnosis_closeout_v1.json','diagnosis_receipt.json'),
        (ROOT/'.cache/h098_local_check_v1/result.json','local_check_result.json'),
        (ROOT/'.cache/h098_preflight_v2/result.json','preflight_result.json')):
        assert read(src)['passed'];shutil.copyfile(src,out/name);diagnostics.append(dict(path=str(src),sha256=checksum(src)))
    save(out/'input_bindings.json',bindings);save(out/'historical_verdicts.json',historical(parent))
    save(out/'config.json',dict(experiment='H098',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,parent=str(parent),parent_freeze_sha256=PIN,
        networks=m.NETWORKS,engineering=m.ENGINEERING,root_seed=m.SEED,conditions=list(m.CONDITIONS),precisions=list(m.PRECISIONS),
        observed_labels_per_packet=8,generated_responses_per_packet=16,actual_handoffs=2,generations=[0,1,2],capability_task_fraction=.75,source_gap=.25,
        available_edges_per_child=4064,available_channels_per_child=24,regularization=.1,solver_relative_tolerances=compiler.TOLERANCES,solver_max_iterations=512,
        neural_threshold=1e-12,exclusion_margin=5e-14,field_energy_tolerance=2e-11,normal_equation_tolerance=5e-10,
        copy_has_protected_blueprint=False,native_controls_use_separate_substrate=True,
        query_hold_sweeps=1,held_context_sites=32,true_context_resupplied=False,classification='NUMERICAL_CORRECTION_ON_EXPOSED_COHORT',
        cohort_reused_from='H097',fresh_confirmation=False,original_H097_acceptance='FAILED',both_conditions_newly_acquired=True,
        both_precisions_newly_acquired=True,precision_control_is_not_an_extra_sample=True,diagnostic_bindings=diagnostics,
        input_tapes_committed=20,main_correction_outcomes_generated_before_freeze=False,
        worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,closeout_receipt=str(receipt),watch_receipt=str(ROOT/'.cache'/('h098_watch_'+suffix+'.json')),next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h098/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h098/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,
        short_run_watcher_authorized=True,exposed_cohort_reused=True,fresh_confirmation=False,full_engineering_validation_required_before_main=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('prepare','execute','watch'):mode.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
