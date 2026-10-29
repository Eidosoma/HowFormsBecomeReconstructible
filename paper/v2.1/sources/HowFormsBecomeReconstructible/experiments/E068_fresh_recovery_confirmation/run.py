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
from E068_fresh_recovery_confirmation import data,model,audit_model,inference,sources
from E068_fresh_recovery_confirmation.plan import HERE,ROOT,NAMES,settings


def input_paths():
    # Snapshot the complete local Python import closure, including technical
    # projection checks, rather than guessing transitive model dependencies.
    import ast
    local=('PROTOCOL.md','SOURCE_DATA.json','plan.py','data.py','model.py',
        'audit_model.py','inference.py','run.py','workflow.py','tests.py','plot.py','prepare.py','sources.py')
    paths={ROOT/'common.py',ROOT/'run_python.sh',ROOT/'RUN_POLICY.md',ROOT/'SOURCE_SNAPSHOT.json',ROOT/'SOURCE_LICENSE.txt'}|{HERE/p for p in local}
    pending=[p for p in paths if p.suffix=='.py'];seen=set()
    while pending:
        p=pending.pop()
        if p in seen:continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                candidate=ROOT/(name.replace('.','/')+'.py')
                if candidate.is_file() and candidate not in paths:
                    paths.add(candidate);pending.append(candidate)
    return sorted(paths)


def block(run,b,cfg):
    import numpy as np
    from E068_fresh_recovery_confirmation.plan import index
    started=time.monotonic();source,source_controls,source_timings=sources.generate(run,b,cfg)
    recovery_started=time.monotonic()
    inter=model.intervene(source);production_rebuild_seconds=0.
    data.save(run/f'source_{b:06d}.npz',source)
    data.save(run/f'interventions_{b:06d}.npz',inter)
    incoming=inter['packets'];copied=incoming.copy();slots=[incoming.copy()]
    checks=dict(native_source_bytes=inter['packets'][:2].tobytes()==source['final'].tobytes(),
        initial_erased_zero=not model.base.decode(inter['packets'][4]).any())
    final,earlier=model.base.decode(source['final']),model.base.decode(source['initial'])
    mixed=model.base.decode(inter['packets'][2:4]);common=(final!=0)&(earlier!=0)
    checks.update(source_controls)
    checks.update(mixture_signs_fixed=np.array_equal(np.sign(mixed),np.sign(final)),
        mixture_support_fixed=np.array_equal(mixed!=0,final!=0),
        mixture_common_magnitudes_exact=np.array_equal(abs(mixed[common]),abs(earlier[common])),
        mixture_other_bytes_fixed=mixed[~common].tobytes()==final[~common].tobytes())
    for g in range(1,4):
        tick=time.monotonic();raw=model.rebuild(incoming,b,g,cfg['config'],cfg['cycle'])
        production_rebuild_seconds+=time.monotonic()-tick
        copied=model.copy_step(copied,raw['masks']);raw['copy_packets']=copied.copy()
        data.save(run/f'boundary_{b:06d}_g{g}.npz',raw)
        available=model.reader.surviving_edges(raw['masks'])
        outgoing=model.base.decode(raw['outgoing'])
        checks[f'g{g}_injury_count']=bool((raw['masks'].sum(axis=(-2,-1))==24).all())
        checks[f'g{g}_ports_protected']=not raw['masks'][...,model.P.any(axis=0)].any()
        checks[f'g{g}_missing_edges_zero']=not outgoing[np.broadcast_to(~available,outgoing.shape)].any()
        checks[f'g{g}_fallback_exact']=np.array_equal(raw['fallback'],(raw['contrast']==0)&available)
        checks[f'g{g}_copied_erased_zero']=not model.base.decode(copied[4]).any()
        checks[f'g{g}_erased_rule_partners_identical']=all(raw['outgoing'][4,f].tobytes()==raw['outgoing'][4,f+1].tobytes() for f in (0,2))
        incoming=raw['outgoing']
        if g in (1,3):slots.extend((incoming.copy(),copied[:4].copy()))
    packets=np.concatenate(slots)
    tick=time.monotonic();fresh=model.develop(packets,b,cfg['reader'],cfg['reader'],'terminal')
    production_reader_seconds=time.monotonic()-tick
    cases,records=model.diagnostics(packets,fresh,cfg['reader'])
    for name,arrays in (('records',records),('assay',fresh),('cases',cases)):
        data.save(run/f'{name}_{b:06d}.npz',arrays)
    production_seconds=time.monotonic()-recovery_started;tick=time.monotonic()
    inter2=audit_model.intervene(source);data.equal(inter,inter2)
    incoming=inter2['packets'];copied=incoming.copy();slots=[incoming.copy()]
    audit_rebuild_seconds=0.
    for g in range(1,4):
        t=time.monotonic();other=audit_model.rebuild(incoming,b,g,cfg['config'],cfg['cycle'])
        audit_rebuild_seconds+=time.monotonic()-t
        copied=audit_model.copy_step(copied,other['masks']);other['copy_packets']=copied.copy()
        data.equal(data.load(run/f'boundary_{b:06d}_g{g}.npz'),other)
        incoming=other['outgoing']
        if g in (1,3):slots.extend((incoming.copy(),copied[:4].copy()))
    packets2=np.concatenate(slots);assert packets.tobytes()==packets2.tobytes()
    t=time.monotonic();fresh2=audit_model.develop(packets2,b,cfg['reader'],cfg['reader'],'terminal')
    audit_reader_seconds=time.monotonic()-t;data.equal(fresh,fresh2)
    cases2,records2=audit_model.diagnostics(packets2,fresh2,cfg['reader'])
    data.equal(cases,cases2);data.equal(records,records2)
    checks['terminal_injury_count']=bool((fresh['masks'].sum(axis=(-2,-1))==24).all())
    checks['terminal_ports_protected']=not fresh['masks'][...,model.P.any(axis=0)].any()
    checks['initial_erased_no_success']=not cases['both'][4].any()
    checks['outcome_partition']=bool((sum(cases[k].astype(int) for k in ('both','correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign'))==1).all())
    checks['opposite_is_wrong']=bool((~cases['opposite_rule_success']|cases['any_wrong_sign']).all())
    checks['erased_rewrite_pairs_identical']=all(fresh['end'][s,f].tobytes()==fresh['end'][s,f+1].tobytes() for s in (4,9,18) for f in (0,2))
    checks['erased_rule_scores_at_most_half']=all(not (cases['both'][s,f]&cases['both'][s,f+1]).any() for s in (4,9,18) for f in (0,2))
    checks['copy_never_gains_support']=all(not cases['support_gained'][index(h,'copy',arm)].any() for h in (1,3) for arm in cfg['arms'][:4])
    checks['copy_never_changes_surviving_sign']=all(not cases['sign_changes'][index(h,'copy',arm)].any() for h in (1,3) for arm in cfg['arms'][:4])
    checks['copy_support_never_increases']=bool((cases['edges'][19:23]<=cases['edges'][10:14]).all())
    checks={k:bool(v) for k,v in checks.items()};checks['pass']=all(checks.values());assert checks['pass'],checks
    legacy_projection=False
    if cfg['mode']!='scientific':
        from E068_fresh_recovery_confirmation.tests import legacy_projection_check,alias_check
        legacy_projection_check(inter['packets'],b,cfg,data.load(run/f'boundary_{b:06d}_g1.npz'))
        alias_check(packets,b,cfg,fresh);legacy_projection=True
    audit_seconds=time.monotonic()-tick
    timings={**source_timings,
        'production_rebuild':production_rebuild_seconds,'production_terminal_read':production_reader_seconds,
        'production_recovery_static':production_seconds-production_rebuild_seconds-production_reader_seconds,
        'audit_rebuild':audit_rebuild_seconds,'audit_terminal_read':audit_reader_seconds,
        'audit_recovery_static':audit_seconds-audit_rebuild_seconds-audit_reader_seconds}
    dump(run/f'progress_{b}.json',dict(block=b,stage='verified',utc=utc()))
    dump(run/f'worker_{b}.json',dict(block=b,status='PASS',utc=utc(),timings=timings,
        ancestry_boundaries_replayed=32,source_continuation_boundaries_replayed=3,
        recovery_boundaries_replayed=3,fresh_sources=cfg['mode']=='scientific',
        source_projection_verified=cfg['mode']!='scientific',production_seconds=production_seconds,
        production_rebuild_seconds=production_rebuild_seconds,production_reader_seconds=production_reader_seconds,
        production_static_seconds=production_seconds-production_rebuild_seconds-production_reader_seconds,
        audit_seconds=audit_seconds,audit_rebuild_seconds=audit_rebuild_seconds,audit_reader_seconds=audit_reader_seconds,
        audit_static_seconds=audit_seconds-audit_rebuild_seconds-audit_reader_seconds,
        seconds=time.monotonic()-started,controls=checks,terminal_cue_observations=23*4*cfg['recipients']*2,
        legacy_writer_and_alias_projections_verified=legacy_projection,every_step_state_hashes_replayed=True,
        every_boundary_and_copy_replayed=True,source_bytes_verified=True))


def execute(mode,workers):
    started=time.monotonic();cfg=settings(mode);job=HERE/'jobs'/NAMES[mode]
    check_inputs(job);data.verify_receipts(mode)
    run=new_run(HERE/'runs'/NAMES[mode],input_paths(),dict(experiment='E068',**cfg,workers=workers))
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
                dump(job/'status.json',dict(status='RUNNING',stage='source_recovery_and_independent_replay',utc=utc(),
                    completed_blocks=sorted(done),total_blocks=len(cfg['blocks']),workers=workers))
                print('Verified block',done[-1],flush=True)
        cases=[data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        reports=[json.loads((run/f'worker_{b}.json').read_text()) for b in cfg['blocks']]
        controls=[r['controls'] for r in reports]
        summary=inference.analyze(cases,controls,mode);checked=inference.audit(cases,controls,summary,mode)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary))
        dump(run/'CHECKS.json',dict(status='PASS',blocks=len(done),summaries_checked=checked,
            all_boundaries_and_copies_replayed=True,all_reader_states_replayed=True,controls_pass=True,
            terminal_cue_observations=sum(r['terminal_cue_observations'] for r in reports),
            protected_and_erased_aliases_verified=True,source_dynamics_independently_replayed=True,
            ancestry_boundaries=32*len(done),source_continuation_boundaries=3*len(done),recovery_boundaries=3*len(done),old_scientific_cases_pooled=False))
        from E068_fresh_recovery_confirmation.plot import plot
        plot(run,summary)
        times={'phase_block_seconds':{key:[r['timings'][key] for r in reports] for key in reports[0]['timings']}}
        finish(run,started,dict(experiment='E068',blocks_completed=len(done),controls_pass=True,**times))
        dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
            blocks_checked=len(done),summaries_checked=checked,all_reader_states_replayed=True,
            all_boundaries_and_copies_replayed=True,source_dynamics_independently_replayed=True,
            fresh_sources=mode=='scientific',controls_pass=True,primary_effects=summary['primary_effects'],
            recovery_supported=summary['recovery_supported'],audit_model_sha256=sha(HERE/'audit_model.py'),
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
