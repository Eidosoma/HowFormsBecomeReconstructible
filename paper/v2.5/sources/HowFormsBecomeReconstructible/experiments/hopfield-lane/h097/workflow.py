"""Frozen constrained-inheritance pilot with shared CPU admission and independent closeout."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,multiprocessing,os,shutil,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h061.workflow import watch
from h063.workflow import compare
from h095.workflow import FILES as PARENT_FILES
from h097 import model as m,audit,measure,diagnostics,report
PIN='7d0cc8ee0319c2037f01b197f293a10657806d19467bf18b17f86766aff5587f'
TRANSPORT_PIN='2e2ad2c8170de8c512b645c8d405c6b12ce89e328f58b0076cdc2dfd1d61160e'
FILES=PARENT_FILES+['h095/INTERPRETATION.md','h096/DESIGN.md','h096/null_check.py','h096/INTERPRETATION.md']+['h097/'+name for name in
    ('PROTOCOL.md','compiler.py','model.py','audit.py','measure.py','diagnostics.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','records','writer_packets','completion_fits','unique_neural_reads','unique_native_reads',
    'assay_cases','panel_case_rows','transition_rows','stability_rows','unchanged_boundary_arrays','pair_energy_comparisons',
    'single_energy_comparisons','diagnostic_checks','independently_verified_rows','saved_array_reload_checks','saved_graph_reload_checks','saved_raw_bundles')
def read(path):return json.loads(Path(path).read_text())
def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k] for k in f.files}
def historical(parent):return dict(read(parent/'historical_verdicts.json'),h095=read(parent/'main/summary.json')['findings'],h095_primary_scores=read(parent/'main/summary.json')['primary_scores'])
def binding_check(binding):assert checksum(binding['tape_path'])==binding['tape_sha256']

def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['parent']);transport=Path(config['transport_control'])
    assert checksum(parent/'checksums.json')==PIN==config['parent_manifest_sha256'];verify(parent,'checksums.json')
    assert checksum(transport/'checksums.json')==TRANSPORT_PIN==config['transport_manifest_sha256'];verify(transport,'checksums.json')
    assert read(parent/'COMPLETE.json')['integrity_passed'] and read(out/'historical_verdicts.json')==historical(parent)
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['networks']==m.NETWORKS==16 and config['engineering']==m.ENGINEERING==4
    assert config['root_seed']==m.SEED==97097 and config['conditions']==list(m.CONDITIONS)
    assert config['observed_labels_per_packet']==8 and config['actual_handoffs']==2
    assert config['available_edges_per_child']==4064 and config['available_channels_per_child']==24
    assert config['regularization']==.1 and not config['copy_has_protected_blueprint']
    bindings=read(out/'input_bindings.json');seen=set()
    for group in bindings.values():
        for b in group:
            binding_check(b);assert b['tape_digest'] not in seen;seen.add(b['tape_digest'])
            tape=load(b['tape_path']);assert m.digest(tape)==b['tape_digest']
            for k,v in m.tapes(b['cohort'],b['block']).items():np.testing.assert_array_equal(tape[k],v)
    assert len(seen)==20
    return config


def boundary_checks(raws,graphs):
    checks=0
    for origin in m.ORIGINS:
        for kind in m.KINDS:
            records=[]
            for c in m.CONDITIONS:
                node=next(r for r in graphs[c]['records'] if r['operation']=='founder' and r['origin']==origin and r['kind']==kind)
                records.append(m.get_record(raws[c],graphs[c],node['id']))
            for k in records[0]:np.testing.assert_array_equal(records[0][k],records[1][k]);checks+=1
    # G0 paths and independent native paths have identical apparatus across conditions.
    key=lambda r:tuple(r[k] for k in ('origin','route','policy','generation','birth'))
    maps=[{key(r):r for r in graphs[c]['lineages']} for c in m.CONDITIONS]
    assert maps[0].keys()==maps[1].keys()
    for identity in maps[0]:
        origin,route,policy,g,b=identity
        if g!=0 and route not in m.BASELINES:continue
        data=[m.get_read(raws[c],graphs[c],mapping[identity]['read']) for c,mapping in zip(m.CONDITIONS,maps)]
        for k in data[0]:np.testing.assert_array_equal(data[0][k],data[1][k]);checks+=1
    return checks


def task(argument):
    out,binding=argument;out=Path(out);tick=time.perf_counter();block=binding['block'];stem=f'block_{block:03d}'
    try:
        binding_check(binding);tape=load(binding['tape_path'])
        commitment=out/'commitments'/(stem+'.json');save(commitment,dict(**binding,committed_utc=utc(),acquisition_started=False));pin=checksum(commitment)
        all_raw={};graphs={};audits=[];reloads=0
        for condition in m.CONDITIONS:
            raw,graph=m.run_tapes(tape,condition);path=out/'new_raw'/(stem+'_'+condition+'.npz')
            with path.open('xb') as f:np.savez_compressed(f,**raw)
            save(out/'paths'/(stem+'_'+condition+'.json'),graph)
            saved=load(path);assert saved.keys()==raw.keys()
            for k in raw:np.testing.assert_array_equal(raw[k],saved[k],err_msg=k)
            reloads+=len(raw);assert read(out/'paths'/(stem+'_'+condition+'.json'))==graph
            all_raw[condition]=saved;graphs[condition]=graph
            audits.append(audit.network(saved,graph,binding['cohort'],block,condition))
        unchanged=boundary_checks(all_raw,graphs)
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
            assay_cases=1920,panel_case_rows=3840,transition_rows=1152,stability_rows=1296,unchanged_boundary_arrays=unchanged,
            pair_energy_comparisons=sum(a['pair_energy_comparisons'] for a in audits),single_energy_comparisons=sum(a['single_energy_comparisons'] for a in audits),
            diagnostic_checks=probechecks,independently_verified_rows=rowchecks,saved_array_reload_checks=reloads,saved_graph_reload_checks=3,saved_raw_bundles=3,
            max_writer_normal_residual=max(a['max_writer_normal_residual'] for a in audits),max_field_error=max(a['max_field_error'] for a in audits),
            max_pair_energy_error=max(a['max_pair_energy_error'] for a in audits),minimum_decision_boundary_distance=min(a['minimum_decision_boundary_distance'] for a in audits),
            raw_sha256=checksum(path),acquisition_sha256={c:checksum(out/'new_raw'/(stem+'_'+c+'.npz')) for c in m.CONDITIONS},metadata_sha256=checksum(out/'paths'/(stem+'.json')),
            both_conditions_newly_acquired=True,all_new_trajectories_replayed=True,all_actual_packets_verified=True,heldout_truth_excluded_from_writing=True,physical_constraints_verified=True)
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
        all_new_trajectories_replayed=True,all_actual_packets_verified=True,both_conditions_newly_acquired=True,physical_constraints_verified=True,findings=summary['findings'],
        comparative_superiority_qualified=False,new_population_qualification=False)
    assert checked['records']==734*n and checked['writer_packets']==checked['completion_fits']==596*n
    assert checked['assay_cases']==1920*n and checked['transition_rows']==1152*n and checked['panel_case_rows']==3840*n
    assert checked['independently_verified_rows']==summary['diagnostic_rows'];save(out/'verification.json',checked);return checked

def execute(out):
    from h097 import fixtures
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
            historical_verdicts_unchanged=True,new_observed_labels_per_packet=0,completion_fits=main['completion_fits'],forecast_predictors=0,next_campaign_launched=False))
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
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h097_connection_loss_')
    suffix=out.name.removeprefix('h097_connection_loss_');receipt=ROOT/'.cache'/('h097_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.pid'),out.with_suffix('.log'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h095_fresh_context_v1';transport=ROOT/'runs/h096_transport_null_v1'
    assert checksum(parent/'checksums.json')==PIN;verify(parent,'checksums.json');assert read(parent/'COMPLETE.json')['integrity_passed']
    assert checksum(transport/'checksums.json')==TRANSPORT_PIN;verify(transport,'checksums.json')
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    assert len(FILES)==len(set(FILES));out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir();bindings={};seen=set()
    from h095 import model as predecessor
    legacy={m.digest(predecessor.tapes(c,b)) for c,n in (('engineering',4),('confirmation',32)) for b in range(n)}
    for cohort,key,n in (('engineering','engineering',m.ENGINEERING),('development','main',m.NETWORKS)):
        bindings[key]=[]
        for block in range(n):
            tape=m.tapes(cohort,block);digest=m.digest(tape);assert digest not in seen|legacy;seen.add(digest)
            path=out/'inputs'/f'{cohort}_{block:03d}.npz'
            with path.open('xb') as f:np.savez_compressed(f,**tape)
            bindings[key].append(dict(block=block,cohort=cohort,tape_path=str(path),tape_sha256=checksum(path),tape_digest=digest))
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    save(out/'input_bindings.json',bindings);save(out/'historical_verdicts.json',historical(parent))
    save(out/'config.json',dict(experiment='H097',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,parent=str(parent),parent_manifest_sha256=PIN,
        transport_control=str(transport),transport_manifest_sha256=TRANSPORT_PIN,networks=m.NETWORKS,engineering=m.ENGINEERING,root_seed=m.SEED,conditions=list(m.CONDITIONS),
        observed_labels_per_packet=8,generated_responses_per_packet=16,actual_handoffs=2,generations=[0,1,2],capability_task_fraction=.75,source_gap=.25,
        available_edges_per_child=4064,available_channels_per_child=24,regularization=.1,solver_relative_tolerance=1e-12,solver_max_iterations=512,
        normal_equation_tolerance=5e-10,copy_has_protected_blueprint=False,native_controls_use_separate_substrate=True,
        query_hold_sweeps=1,held_context_sites=32,true_context_resupplied=False,classification='fixed development pilot',both_conditions_newly_acquired=True,
        input_tapes_committed=20,legacy_tape_digests_checked=len(legacy),main_outcomes_generated_before_freeze=False,
        worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,closeout_receipt=str(receipt),watch_receipt=str(ROOT/'.cache'/('h097_watch_'+suffix+'.json')),next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h097/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h097/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,short_run_watcher_authorized=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('prepare','execute','watch'):mode.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
