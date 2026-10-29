"""Fixed blocks with immediate independent replay and retained raw evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,check_inputs,dump,finish,new_run,sha,utc
from E065_fresh_compatibility_confirmation import data,model,audit_model,inference,source_model,source_audit
import numpy as np
from E062_cross_stage_compatibility import graph
from E065_fresh_compatibility_confirmation.plan import HERE,ROOT,NAMES,settings


def input_paths():
    external=('common.py','run_python.sh','RUN_POLICY.md','SOURCE_SNAPSHOT.json','SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py','E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py','E017_reader_timing/model.py','E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py','E022_reader_compensation/audit.py',
        'E054_record_interventions/model.py','E054_record_interventions/audit_model.py','E054_record_interventions/plan.py',
        'E055_stress_capture_recovery/model.py','E055_stress_capture_recovery/audit_model.py','E055_stress_capture_recovery/plan.py',
        'E056_sign_magnitude_substitution/model.py','E056_sign_magnitude_substitution/audit_model.py','E056_sign_magnitude_substitution/plan.py',
        'E057_fresh_capture_confirmation/plan.py',
        'E062_cross_stage_compatibility/model.py','E062_cross_stage_compatibility/audit_model.py',
        'E062_cross_stage_compatibility/graph.py','E062_cross_stage_compatibility/plan.py',
        'E064_magnitude_subset_intervention/model.py','E064_magnitude_subset_intervention/audit_model.py',
        'E064_magnitude_subset_intervention/plan.py')
    local=('PROTOCOL.md','SOURCE_DATA.json','plan.py','data.py','source_model.py','source_audit.py',
        'model.py','audit_model.py','inference.py','run.py','workflow.py','tests.py','plot.py','prepare.py')
    return [ROOT/p for p in external]+[HERE/p for p in local]


def block(run,b,cfg):
    started=time.monotonic();timings={};R=cfg['recipients'];mode=cfg['mode']
    config=model.base.Config(**cfg['config'])
    def elapsed(name,tick):timings[name]=timings.get(name,0.)+time.monotonic()-tick
    def accumulate(prefix,values):
        for k,v in values.items():timings[prefix+'_'+k]=timings.get(prefix+'_'+k,0.)+v
    def progress(stage,g=0):dump(run/f'progress_{b}.json',dict(block=b,stage=stage,generation_verified=g,utc=utc()))
    progress('acquisition')
    tick=time.monotonic();acquisition=source_model.reader.acquisition.teach(b,config)
    data.save(run/f'acquisition_{b:06d}.npz',acquisition);elapsed('production_acquisition',tick)
    tick=time.monotonic();audit_acquired,_=source_audit.source_record(acquisition,b,cfg['config']);elapsed('audit_acquisition',tick)
    if mode!='scientific':data.equal(acquisition,data.reference(mode,'E057','acquisition_900041.npz'))
    packets=acquisition['acquired'][1,:,None].repeat(R,axis=1)[None]
    audit_packets=audit_acquired[:,None].repeat(R,axis=1)[None]
    data.equal({'packets':packets},{'packets':audit_packets})
    controls=dict(acquisition_replayed=True,source_boundaries_replayed=True,continuation_replayed=True,
        source_ports_protected=True,source_injury_count=True,legacy_technical_projection=mode!='scientific',
        fresh_registered_sources=mode=='scientific')
    for g in range(1,33):
        raw,t=source_model.rebuild(packets,b,g,config,cfg['source_cycle'],'E022');accumulate('production_source',t)
        tick=time.monotonic();data.save(run/f'source_boundary_{b:06d}_g{g}.npz',raw);elapsed('production_storage',tick)
        other,t=source_audit.rebuild(audit_packets,b,g,cfg['config'],cfg['source_cycle'],'E022');accumulate('audit_source',t)
        data.equal(raw,other);data.legacy_boundary(mode,'source',g,raw)
        controls['source_ports_protected'] &= not raw['masks'][...,model.P.any(axis=0)].any()
        controls['source_injury_count'] &= (raw['masks'].sum(axis=(-2,-1))==24).all()
        packets=raw['outgoing'].copy();audit_packets=other['outgoing'].copy();progress('source',g)
    tick=time.monotonic();body,outgoing=source_model.perturb(packets,b,cfg['body']);elapsed('production_pulse',tick)
    data.save(run/f'body_{b:06d}.npz',body);data.save(run/f'outgoing_{b:06d}.npz',outgoing)
    tick=time.monotonic();body2,outgoing2=source_audit.perturb(audit_packets,b,cfg['body']);elapsed('audit_pulse',tick)
    data.equal(body,body2);data.equal(outgoing,outgoing2);data.legacy_body(mode,body,outgoing)
    controls.update(before_equal=np.array_equal(body['states'][:,0,0],body['states'][:,1,0]),
        pulse_ports_protected=not body['pulse_sites'][...,model.P.any(axis=0)].any(),
        pulse_living_only=not (body['pulse_sites']&body['masks']).any(),
        pulse_site_count=(body['pulse_sites'].sum(axis=(-2,-1))==cfg['body']['pulse_sites']).all())
    initial=outgoing['packets'].copy();packets=initial.copy();audit_packets=outgoing2['packets'].copy()
    for g in range(1,4):
        raw,t=source_model.rebuild(packets,b,g,config,cfg['continuation'],'E058');accumulate('production_continuation',t)
        tick=time.monotonic();data.save(run/f'continuation_{b:06d}_g{g}.npz',raw);elapsed('production_storage',tick)
        other,t=source_audit.rebuild(audit_packets,b,g,cfg['config'],cfg['continuation'],'E058');accumulate('audit_continuation',t)
        data.equal(raw,other);data.legacy_boundary(mode,'continuation',g,raw)
        controls['source_ports_protected'] &= not raw['masks'][...,model.P.any(axis=0)].any()
        controls['source_injury_count'] &= (raw['masks'].sum(axis=(-2,-1))==24).all()
        packets=raw['outgoing'].copy();audit_packets=other['outgoing'].copy();progress('continuation',g)
    source=dict(initial=initial,final=packets)
    if mode!='scientific':
        previous=data.reference(mode,'E062','source_900041.npz')
        data.equal(source,{k:previous[k] for k in source})
    tick=time.monotonic();inter=model.intervene(source);elapsed('production_terminal_static',tick)
    if mode!='scientific':
        old62=data.reference(mode,'E062','interventions_900041.npz')['packets']
        old64=data.reference(mode,'E064','interventions_900041.npz')['packets']
        data.equal({'packets':inter['packets']},{'packets':np.concatenate((old62[:8],old64[2:6],old62[10:11]))})
    progress('terminal_reader')
    tick=time.monotonic();fresh=model.assay(inter['packets'],b,cfg['reader']);elapsed('production_terminal_read',tick)
    tick=time.monotonic();fresh.update(graph.batch(fresh['effective']))
    cases,checks=model.diagnostics(source,inter,fresh,cfg['reader']);elapsed('production_terminal_static',tick)
    tick=time.monotonic()
    for name,arrays in (('source',source),('interventions',inter),('assay',fresh),('cases',cases)):
        data.save(run/f'{name}_{b:06d}.npz',arrays)
    elapsed('production_storage',tick)
    tick=time.monotonic();inter2=audit_model.intervene(dict(initial=outgoing2['packets'],final=audit_packets))
    data.equal(inter,inter2);elapsed('audit_terminal_static',tick)
    tick=time.monotonic();fresh2=audit_model.assay(inter2['packets'],b,cfg['reader']);elapsed('audit_terminal_read',tick)
    tick=time.monotonic();fresh2.update(audit_model.graph_batch(fresh2['effective']));data.equal(fresh,fresh2)
    cases2,checks2=audit_model.diagnostics(source,inter2,fresh2,cfg['reader'])
    data.equal(cases,cases2);assert checks==checks2 and checks2['pass'],checks2;elapsed('audit_terminal_static',tick)
    controls.pop('legacy_technical_projection');controls.pop('fresh_registered_sources')
    controls.update(checks);controls={k:bool(v) for k,v in controls.items()};controls['pass']=all(controls.values())
    assert controls['pass'],controls
    progress('verified')
    dump(run/f'worker_{b}.json',dict(block=b,status='PASS',utc=utc(),seconds=time.monotonic()-started,
        timings=timings,controls=controls,terminal_cue_observations=13*4*R*2,
        source_boundaries_replayed=32,continuation_boundaries_replayed=3,
        reduced_legacy_projection_verified=mode!='scientific',fresh_sources=mode=='scientific',
        every_step_state_hashes_replayed=True,all_interventions_and_graphs_replayed=True))


def execute(mode,workers):
    started=time.monotonic();cfg=settings(mode);job=HERE/'jobs'/NAMES[mode]
    check_inputs(job);data.verify_receipts(mode)
    run=new_run(HERE/'runs'/NAMES[mode],input_paths(),dict(experiment='E065',**cfg,workers=workers))
    def launch(b):
        with (run/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'run.py'),'--mode',mode,'--workers',str(workers),'--worker',str(b)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        return b
    done=[]
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(launch,b) for b in cfg['blocks']]
            for fut in as_completed(futures):
                try:done.append(fut.result())
                except BaseException:
                    for pending in futures:pending.cancel()
                    raise
                dump(job/'status.json',dict(status='RUNNING',stage='source_and_reader_replay',utc=utc(),
                    completed_blocks=sorted(done),total_blocks=len(cfg['blocks']),workers=workers))
                print('Verified block',done[-1],flush=True)
        cases=[data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        reports=[json.loads((run/f'worker_{b}.json').read_text()) for b in cfg['blocks']]
        controls=[r['controls'] for r in reports]
        summary=inference.analyze(cases,controls,mode);checked=inference.audit(cases,controls,summary,mode)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary))
        dump(run/'CHECKS.json',dict(status='PASS',blocks=len(done),summaries_checked=checked,
            all_interventions_and_graphs_replayed=True,all_reader_states_replayed=True,controls_pass=True,
            terminal_cue_observations=sum(r['terminal_cue_observations'] for r in reports),
            nochange_alias_verified=True,source_dynamics_independently_replayed=True,source_boundaries=32*len(done),continuation_boundaries=3*len(done),old_scientific_cases_pooled=False))
        from E065_fresh_compatibility_confirmation.plot import plot
        plot(run,summary)
        times={'phase_block_seconds':{key:[r['timings'][key] for r in reports] for key in reports[0]['timings']}}
        finish(run,started,dict(experiment='E065',blocks_completed=len(done),controls_pass=True,**times))
        dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
            blocks_checked=len(done),summaries_checked=checked,all_reader_states_replayed=True,
            all_interventions_and_graphs_replayed=True,controls_pass=True,primary_effects=summary['primary_effects'],
            primary_confirmed=summary['primary_confirmed'],audit_model_sha256=sha(HERE/'audit_model.py'),
            inference_sha256=sha(HERE/'inference.py')))
    except BaseException:
        dump(run/'FAILED.json',dict(status='FAILED',utc=utc(),traceback=traceback.format_exc(),automatic_restart=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=NAMES,required=True)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int)
    a=p.parse_args();cap_cpus(a.workers);assert 1<=a.workers<=8
    if a.worker is None:execute(a.mode,a.workers)
    else:
        run=HERE/'runs'/NAMES[a.mode];check_inputs(run);assert a.worker in settings(a.mode)['blocks']
        block(run,a.worker,settings(a.mode))
