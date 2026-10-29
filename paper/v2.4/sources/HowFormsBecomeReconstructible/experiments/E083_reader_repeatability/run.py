"""Fixed source blocks; two matched fresh reads and independent replay."""
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
from E083_reader_repeatability import data,model,audit_model,inference
from E083_reader_repeatability.plan import HERE,ROOT,NAMES,settings,cohort,source_block


def input_paths():
    import ast
    local=('PROTOCOL.md','DATA_DICTIONARY.md','SOURCE_DATA.json','plan.py','data.py','model.py',
        'audit_model.py','inference.py','individuals.py','run.py','workflow.py','tests.py','plot.py','prepare.py')
    paths={ROOT/'common.py',ROOT/'run_python.sh',ROOT/'RUN_POLICY.md'}|{HERE/p for p in local}
    pending=[p for p in paths if p.suffix=='.py'];seen=set()
    while pending:
        path=pending.pop()
        if path in seen:continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                candidate=ROOT/(name.replace('.','/')+'.py')
                if candidate.is_file() and candidate not in paths:paths.add(candidate);pending.append(candidate)
    return sorted(paths)


def checks(src,fresh,cases,records,cfg):
    import numpy as np
    fields=dict(source_preflight=data.preflight(src),
        source_packets_unchanged=src['packets'].tobytes()==records['packets'].tobytes(),
        outcome_partition=bool((sum(cases[k].astype(int) for k in ('both','correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign'))==1).all()),
        strict_threshold=np.array_equal(cases['both'],(cases['margin']>.25).all(-1)),
        opposite_is_wrong=bool((~cases['opposite_rule_success']|cases['any_wrong_sign']).all()),
        terminal_injury_count=bool((fresh['masks'].sum(axis=(-2,-1))==24).all()),
        terminal_ports_protected=not fresh['masks'][...,model.P.any(axis=0)].any(),
        finite_all_arrays=all(np.isfinite(v).all() for item in (fresh,cases,records) for v in item.values()),
        erased_reader_alias=all(fresh['end'][slot,f].tobytes()==fresh['end'][slot,f+1].tobytes() for slot in (8,17) for f in (0,2)),
        erased_at_most_half=all(not (cases['both'][slot,f]&cases['both'][slot,f+1]).any() for slot in (8,17) for f in (0,2)),
        matched_selected_postinjury_support=np.array_equal(fresh['effective'][18:22]!=0,fresh['effective'][22:26]!=0))
    empty=~(src['eligible']&model.reader.surviving_edges(fresh['masks'])).any(axis=(-3,-2,-1))
    fields['injury_empty_pattern_alias']=fresh['end'][18:22][empty].tobytes()==fresh['end'][22:26][empty].tobytes()
    for name,item in (('records',records),('terminal',fresh)):
        fields[name+'_natural_unit_gain']=np.allclose(abs(item['coupling']).sum(axis=-3),(item['denominator']>0).astype(float),rtol=0,atol=cfg['gain_tolerance'])
    fields={k:bool(v) for k,v in fields.items()};fields['pass']=all(fields.values());assert fields['pass'],fields
    return fields


def block(run,task,cfg):
    import numpy as np
    started=time.monotonic();src=data.source(cfg['mode'],task);other=data.source(cfg['mode'],task,independent=True);data.equal(src,other)
    data.save(run/f'source_{task:06d}.npz',src)
    reader_seconds=0.;audit_reader=0.;audit_static=0.;controls=[];fresh_all=[];raw_records=None
    for draw in cfg['reader_draws']:
        tick=time.monotonic();fresh=model.develop(src['packets'],source_block(task),cfg,cfg,'terminal_'+cohort(task),draw)
        reader_seconds+=time.monotonic()-tick
        cases,records=model.diagnostics(src['packets'],src['eligible'],fresh,cfg)
        for name,arrays in (('assay',fresh),('cases',cases)):data.save(run/f'{name}_{task:06d}_r{draw}.npz',arrays)
        if raw_records is None:data.save(run/f'records_{task:06d}.npz',records);raw_records=records
        else:data.equal(raw_records,records)
        tick=time.monotonic();fresh2=audit_model.develop(other['packets'],source_block(task),cfg,cfg,'terminal_'+cohort(task),draw)
        audit_reader+=time.monotonic()-tick;tick=time.monotonic();data.equal(fresh,fresh2)
        cases2,records2=audit_model.diagnostics(other['packets'],other['eligible'],fresh2,cfg)
        data.equal(cases,cases2);data.equal(records,records2)
        controls.append(checks(src,fresh,cases,records,cfg));audit_static+=time.monotonic()-tick
        fresh_all.append(fresh)
    assert not np.array_equal(fresh_all[0]['birth'],fresh_all[1]['birth'])
    assert not np.array_equal(fresh_all[0]['masks'],fresh_all[1]['masks'])
    assert not np.array_equal(fresh_all[0]['state_hashes'],fresh_all[1]['state_hashes'])
    full={str(d)+'_'+k:v for d,c in enumerate(controls) for k,v in c.items()};full.update(fresh_draws_differ=True,pass_=True)
    full['pass']=all(full.values())
    elapsed=time.monotonic()-started
    dump(run/f'worker_{task}.json',dict(block=task,source_block=source_block(task),cohort=cohort(task),status='PASS',utc=utc(),
        production_reader_seconds=reader_seconds,production_static_seconds=elapsed-reader_seconds-audit_reader-audit_static,
        audit_reader_seconds=audit_reader,audit_static_seconds=audit_static,seconds=elapsed,controls=full,
        terminal_cue_observations=26*4*cfg['recipients']*2*2,every_step_state_hashes_replayed=True,
        all_source_packets_and_denominators_replayed=True,source_bytes_verified=True,reader_draws=[0,1],
        additional_rewrites=0,writer_dynamics_repeated=False,all_source_cases_retained=True))


def execute(mode,workers):
    started=time.monotonic();cfg=settings(mode);job=HERE/'jobs'/NAMES[mode]
    check_inputs(job);data.verify_receipts(mode)
    run=new_run(HERE/'runs'/NAMES[mode],input_paths(),dict(experiment='E083',**cfg,workers=workers))
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
                dump(job/'status.json',dict(status='RUNNING',stage='reader_and_independent_replay',utc=utc(),completed_blocks=sorted(done),total_blocks=len(cfg['blocks']),workers=workers))
                print('Verified block',done[-1],flush=True)
        sources=[data.load(run/f'source_{b:06d}.npz') for b in cfg['blocks']]
        cases=[[data.load(run/f'cases_{b:06d}_r{d}.npz') for d in cfg['reader_draws']] for b in cfg['blocks']]
        reports=[json.loads((run/f'worker_{b}.json').read_text()) for b in cfg['blocks']];controls=[r['controls'] for r in reports]
        summary=inference.analyze(cfg['blocks'],sources,cases,controls,mode)
        checked=inference.audit(cfg['blocks'],sources,cases,controls,summary,mode)
        from E083_reader_repeatability.individuals import export
        summary['individual_counts']=export(run,cfg['blocks'],sources,cases,summary)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary))
        dump(run/'CHECKS.json',dict(status='PASS',blocks=len(done),summaries_checked=checked,
            all_source_packets_and_denominators_replayed=True,all_reader_states_replayed=True,controls_pass=True,
            terminal_cue_observations=sum(r['terminal_cue_observations'] for r in reports),
            individual_tables_independently_checked=True,old_endpoints_labeled_context_only=True,
            matched_reader_streams_verified=True,predecessor_dynamics_replayed=False,writer_dynamics_repeated=False))
        from E083_reader_repeatability.plot import plot
        plot(run,summary)
        times={f'{phase}_{kind}_block_seconds':[r[f'{phase}_{kind}_seconds'] for r in reports] for phase in ('production','audit') for kind in ('reader','static')}
        finish(run,started,dict(experiment='E083',blocks_completed=len(done),controls_pass=True,**times))
        dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
            blocks_checked=len(done),summaries_checked=checked,all_reader_states_replayed=True,
            all_source_packets_and_denominators_replayed=True,controls_pass=True,primary_effects=summary['primary_effects'],
            alignment_at_both_cohorts=summary['alignment_at_both_cohorts'],individual_tables_independently_checked=True,
            audit_model_sha256=sha(HERE/'audit_model.py'),inference_sha256=sha(HERE/'inference.py')))
    except BaseException:
        dump(run/'FAILED.json',dict(status='FAILED',utc=utc(),traceback=traceback.format_exc(),automatic_restart=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=NAMES,required=True);p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int)
    a=p.parse_args();cap_cpus(a.workers);assert 1<=a.workers<=8
    if a.worker is None:execute(a.mode,a.workers)
    else:
        run=HERE/'runs'/NAMES[a.mode];check_inputs(run);assert a.worker in settings(a.mode)['blocks']
        block(run,a.worker,settings(a.mode))
