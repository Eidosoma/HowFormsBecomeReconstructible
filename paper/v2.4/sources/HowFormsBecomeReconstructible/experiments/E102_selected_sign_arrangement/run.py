"""Selected sign arrangement with independent readers and bounded launch."""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E084_magnitude_placement.workflow import inventory
from E077_fresh_reconstruction_tradeoff import model as old, audit_model as old_audit
from E102_selected_sign_arrangement import data,model,audit,inference
from E102_selected_sign_arrangement.plan import HERE,ROOT,settings,identity,expected_identities



def code_paths():
    paths = set(HERE.glob('*.py')) | {HERE/'PROTOCOL.md',HERE/'DATA_DICTIONARY.md'}
    paths |= {ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md','SOURCE_SNAPSHOT.json','SOURCE_LICENSE.txt')}
    pending = [p for p in paths if p.suffix=='.py']; seen = set()
    while pending:
        p = pending.pop()
        if p in seen: continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text())):
            names = []
            if isinstance(node,ast.Import): names = [a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module: names = [node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                path = ROOT/(name.replace('.','/')+'.py')
                if path.is_file() and path not in paths: paths.add(path); pending.append(path)
    return sorted(paths)


def latest_tests():
    p = sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1]
    t = json.loads(p.read_text()); assert t['status']=='PASS'
    assert t['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert t['registry_sha256']==sha(HERE/'SOURCE_DATA.json')
    return p


def inputs(mode):
    paths = code_paths()+[HERE/'SOURCE_DATA.json',latest_tests()]
    if mode=='scientific': paths += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json',HERE/'analysis/prereader_support_v1.json']
    return paths


def qualification():
    q = json.loads((HERE/'analysis/qualification_v1.json').read_text()); assert q['status']=='PASS'
    for path,h in q['evidence'].items(): assert sha(ROOT/path)==h,path
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    freeze = json.loads((HERE/'SAMPLE_FREEZE.json').read_text())
    assert freeze['settings']==settings('scientific') and freeze['frozen_before_new_scientific_readers']
    assert freeze['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json')
    return q


def score(v,cfg):
    s = old.score(v,cfg['margin']); data.equal(s,old_audit.score(v,cfg['margin']))
    assert np.array_equal(s['both'],s['minimum_margin']>cfg['margin'])
    return s


def verify(name):
    run=HERE/'runs'/name; check_inputs(run)
    c=json.loads((run/'COMPLETE.json').read_text()); assert c['status']=='COMPLETE' and c['controls_pass']
    for path,h in c['outputs_sha256'].items(): assert sha(run/path)==h,path
    checks=json.loads((run/'CHECKS.json').read_text()); assert checks['status']=='PASS'; data.verify_registry()
    return run,c,checks


def launch(name,workers=0):
    qualification(); data.verify_registry(); resources=inventory()
    f=json.loads((HERE/'analysis/forecast_v1.json').read_text())
    workers=workers or min(4,12-resources['other_busy_capacity'],len(resources['affinity']))
    assert 1<=workers<=4 and workers+resources['other_busy_capacity']<=12
    assert resources['free_bytes']>f['storage_reserve_bytes']
    assert f['conservative_seconds_by_workers'][str(workers)]<=21600,'Resource review required; fixed sample unchanged'
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity'])
            for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda c:(burden[c],c))[:workers]); resources['selected_affinity']=selected
    os.sched_setaffinity(0,selected); cap_cpus(workers); assert not (HERE/'runs'/name).exists()
    job=new_run(HERE/'jobs'/name,inputs('scientific'),dict(**settings('scientific'),workers=workers,automatic_restart=False))
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(HERE/'run.py'),'run','--mode','scientific','--name',name,
            '--workers',str(workers)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,workers=workers,numerical_threads=1,detached=True,
        stdin='/dev/null',resources=resources,forecast=f,automatic_successor=False))
    status_path=HERE/'runs'/name/'STATUS.json'; deadline=time.monotonic()+45
    try:
        while time.monotonic()<deadline and proc.poll() is None:
            try: state=json.loads(status_path.read_text())
            except (FileNotFoundError,json.JSONDecodeError): time.sleep(.2); continue
            assert state['status']=='RUNNING',state
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            check_inputs(HERE/'runs'/name); check_inputs(job)
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,durable_status=state,
                stdin='/dev/null',frozen_inputs_verified=True,automatic_scientific_polling=False))
            print(json.dumps(dict(status='RUNNING',pid=proc.pid,workers=workers,
                expected_seconds=f['expected_seconds_by_workers'][str(workers)],
                conservative_seconds=f['conservative_seconds_by_workers'][str(workers)]))); return
        raise TimeoutError('No durable running status within bounded startup check; no restart')
    except BaseException:
        dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),pid=proc.pid,
            traceback=traceback.format_exc(),automatic_restart=False)); raise


def worker(args):
    run,task,cfg=args; run=Path(run); start=time.monotonic(); check_inputs(run)
    dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage='saved_source_capture_checks'))
    writer,saved,old_scores,prior_scores,region_scores,component_scores=data.source(cfg['mode'],task,run)
    inter=model.intervene(saved,task)
    data.equal(inter,audit.intervene(saved,task))
    if cfg['mode']=='scientific':
        expected=json.loads((HERE/'analysis/prereader_support_v1.json').read_text())['blocks'][str(task)]
        assert __import__('hashlib').sha256(inter['packets'].tobytes()).hexdigest()==expected['packets_sha256']
        assert __import__('hashlib').sha256(inter['shuffle_source_edge'].tobytes()).hexdigest()==expected['map_sha256']
    data.save(run/f'interventions_{task:06d}.npz',inter)
    end=np.stack([writer['end'][...,model.P[p]].mean(axis=-1) for p in (1,2)],axis=-1)
    writer_end=score(end,cfg['config']); writer_window=score(writer['mean_ports'],cfg['config'])
    data.save(run/f'source_writer_scores_{task:06d}.npz',
              {**{'end_'+k:v for k,v in writer_end.items()},**{'window_'+k:v for k,v in writer_window.items()}})
    rows=[]; erased=[]; nuisances=[]; reader_seconds=0.; controls=[]
    for draw in cfg['draws']:
        dump(run/f'progress_{task}.json',dict(utc=utc(),task=task,stage='new_terminal_reader_and_replay',draw=draw))
        tick=time.monotonic()
        fresh=old.develop(inter['packets'],task,cfg['config'],cfg['reader'],f'E102_terminal_{draw}',0)
        data.equal(fresh,old_audit.develop(inter['packets'],task,cfg['config'],cfg['reader'],f'E102_terminal_{draw}',0))
        reader_seconds+=time.monotonic()-tick
        cases=score(fresh['mean_ports'],cfg['config'])
        diagnostics,coupling=model.diagnostics(inter,fresh); dg2,cp2=audit.diagnostics(inter,fresh)
        data.equal(diagnostics,dg2); data.equal(coupling,cp2)
        controls.append(model.checks(inter,fresh,cases,coupling,draw))
        for k in ('birth','masks'): assert not np.array_equal(fresh[k],writer[k]),k
        for name,arrays in (('assay',fresh),('scores',cases),('diagnostics',diagnostics)):
            data.save(run/f'{name}_{task:06d}_r{draw}.npz',arrays)
        if draw==0: data.save(run/f'uninjured_coupling_{task:06d}.npz',coupling)
        else: data.equal(coupling,data.load(run/f'uninjured_coupling_{task:06d}.npz'))
        rows.extend(data.rows(task,draw,cfg,cases,diagnostics,old_scores[draw],prior_scores[draw],region_scores[draw],component_scores[draw],writer_end,writer_window))
        erased.extend(data.erased_rows(task,draw,cfg,cases,diagnostics))
        nuisances.append({k:fresh[k].copy() for k in ('birth','masks')})
    for key in nuisances[0]: assert not np.array_equal(nuisances[0][key],nuisances[1][key]),key
    data.export(run/f'cases_{task:06d}.csv',rows); data.export(run/f'erased_{task:06d}.csv',erased)
    elapsed=time.monotonic()-start
    report=dict(status='PASS',utc=utc(),task=task,seconds=elapsed,reader_seconds=reader_seconds,
        static_seconds=max(0.,elapsed-reader_seconds),checks=controls,
        record_contexts=len(rows)//2,context_draw_pairs=len(rows),terminal_cue_observations=18*4*cfg['recipients']*2*2,
        source_bytes_pinned=True,capture_independently_reconstructed=True,interventions_independently_constructed=True,
        terminal_states_independently_replayed=True,scores_and_diagnostics_independently_checked=True,
        original_endpoints_retained=True,writer_dynamics_repeated=False,new_source_blocks=0)
    dump(run/f'worker_{task}.json',report)
    return task,rows,erased,report


def execute(mode,name,workers):
    started=time.monotonic(); cfg=settings(mode); latest_tests()
    if mode=='scientific': qualification(); check_inputs(HERE/'jobs'/name)
    resources=inventory(workers); run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers))
    reports,parts,controls={},{},{}
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),mode=mode,workers=workers,
            completed_blocks=sorted(reports),total_blocks=len(cfg['blocks']),seconds=time.monotonic()-started,
            automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','pinned_source_verification'); data.verify_registry(); dump(run/'resources.json',resources)
        dump(run/'PREDICTION_FREEZE.json',dict(utc=utc(),before_new_terminal_reads=True,
            protocol_sha256=sha(HERE/'PROTOCOL.md'),manifest_sha256=sha(run/'manifest.json'),
            registry_sha256=sha(HERE/'SOURCE_DATA.json'),primary=cfg['primary'],confidence=cfg['primary_confidence'],
            blocks=cfg['blocks'],mode=mode,known_sources=True,source_selection=False))
        status('RUNNING','sign_permutation_and_new_reader_replay')
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('fork')) as pool:
            futures=[pool.submit(worker,(str(run),b,cfg)) for b in cfg['blocks']]
            for future in as_completed(futures):
                try: b,rows,erased,checked=future.result()
                except BaseException:
                    for pending in futures: pending.cancel()
                    raise
                reports[b]=checked; parts[b]=rows; controls[b]=erased
                status('RUNNING','sign_permutation_and_new_reader_replay')
                print(f'Verified block {b}: {checked["seconds"]:.2f} s',flush=True)
        status('RUNNING','all_endpoints_arrangement_and_harms')
        rows=[r for b in cfg['blocks'] for r in parts[b]]; erased=[r for b in cfg['blocks'] for r in controls[b]]
        ids=[identity(r)+(r['draw'],) for r in rows]
        assert len(ids)==len(set(ids)) and set(ids)==expected_identities(cfg)
        data.export(run/'cases.csv',rows); means=data.averages(rows); data.export(run/'individual_two_draw_means.csv',means)
        events,fields=data.events(rows); data.export(run/'events.csv',events,fields); data.export(run/'erased_controls.csv',erased)
        summary=inference.analyze(rows,mode); dump(run/'summary.json',summary)
        (run/'REPORT.md').write_text(inference.report(summary)); inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),record_contexts=len(means),context_draw_pairs=len(rows),
            terminal_cue_observations=sum(r['terminal_cue_observations'] for r in reports.values()),
            independent_block_means=summary['independent_block_means_checked'],
            new_joint_tables=summary['new_joint_tables_checked'],legacy_tables=summary['legacy_tables_checked'],
            outcome_tables=summary['outcome_tables_checked'],all_sources_and_capture_verified=True,
            all_interventions_and_reader_states_replayed=True,all_scores_and_diagnostics_checked=True,
            all_cases_endpoints_and_harms_retained=True,old_endpoints_excluded_from_new_intervals=True,
            primary_fixed_before_new_readers=True,event_rows=len(events),erased_control_rows=len(erased),
            writer_dynamics_repeated=False,new_source_blocks=0,workers=workers)
        dump(run/'CHECKS.json',checks); check_inputs(run); data.verify_registry()
        if mode=='scientific': check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished')
        outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,seconds=time.monotonic()-started,
            blocks=len(reports),workers=workers,controls_pass=True,outputs_sha256=outputs,
            primary_conclusion=summary['primary_conclusion'],criterion_met=summary['criterion_met']))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-started,blocks=len(reports))),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-started,completed_blocks=sorted(reports),
            traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure); dump(run/'STATUS.json',failure); raise


def preflight():
    target=HERE/'analysis/prereader_support_v1.json'; assert not target.exists()
    cfg=settings('scientific'); start=time.monotonic(); completed={}
    try:
        for b in cfg['blocks']:
            writer,saved,*_=data.source('scientific',b)
            inter=model.intervene(saved,b)
            data.equal(inter,audit.intervene(saved,b))
            completed[str(b)]=dict(capture_exact=True,selected_support_matched=True,original_packet_aliases_exact=True,permutation_independently_reconstructed=True,
                structural_checks=model.preflight_checks(inter),
                permutation_inventory=model.inventory(inter),
                map_sha256=__import__('hashlib').sha256(inter['shuffle_source_edge'].tobytes()).hexdigest(),
                packets_sha256=__import__('hashlib').sha256(inter['packets'].tobytes()).hexdigest())
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,blocks=completed,
            no_new_reader_outcomes=True,inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')})
        dump(target,result); return target
    except BaseException:
        dump(target,dict(status='FAILED',utc=utc(),blocks=completed,traceback=traceback.format_exc(),
            no_new_reader_outcomes=True)); raise


def qualify(name):
    run,c,checks=verify(name); assert c['mode']=='benchmark' and checks['blocks']==2
    assert not (HERE/'SAMPLE_FREEZE.json').exists() and not (HERE/'analysis/qualification_v1.json').exists()
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    pre=HERE/'analysis/prereader_support_v1.json'
    if not pre.exists(): preflight()
    pre_data=json.loads(pre.read_text()); assert pre_data['status']=='PASS'
    assert pre_data['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    bench,science=settings('benchmark'),settings('scientific'); details={}; raw=0
    for task in bench['blocks']:
        r=json.loads((run/f'worker_{task}.json').read_text())
        details[str(task)]=dict(reader_seconds=r['reader_seconds'],reader_scale=16,static_seconds=r['static_seconds'],
            static_scale=4,scaled_block_seconds=r['reader_seconds']*16+r['static_seconds']*4)
    block=max(v['scaled_block_seconds'] for v in details.values())
    for p in run.glob('*.npz'):
        with np.load(p,allow_pickle=False) as z: raw+=sum(z[k].nbytes for k in z.files)
    raw+=sum(p.stat().st_size for p in run.glob('*.csv'))
    reserve=math.ceil(raw*4/2*32*1.5)+512*1024**2
    forecast=dict(utc=utc(),block_details=details,scaled_block_seconds=block,scientific_blocks=32,timing_margin=3,
        storage_reserve_bytes=reserve,hard_resource_review_seconds=21600,
        expected_seconds_by_workers={str(w):block*math.ceil(32/w)+180 for w in range(1,5)},
        conservative_seconds_by_workers={str(w):3*block*math.ceil(32/w)+180 for w in range(1,5)})
    resources=inventory(); workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']))
    assert workers>=1 and forecast['conservative_seconds_by_workers'][str(workers)]<=21600,'Pre-reader resource review required'
    assert resources['free_bytes']>reserve
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'arrangement.png',
        latest_tests(),pre,HERE/'analysis/forecast_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,evidence=evidence,
        checks=checks,outputs_verified=len(c['outputs_sha256']),inputs_sha256=json.loads((run/'manifest.json').read_text())['inputs_sha256']))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=science,
        frozen_before_new_scientific_readers=True,new_source_blocks=0,all_known_sources_included=True,
        selection_based_on_outcomes=False,resources=resources,qualified_workers=workers,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json'),forecast_sha256=sha(HERE/'analysis/forecast_v1.json')))
    print(json.dumps(forecast,indent=2))


def closeout(name):
    run,c,checks=verify(name); assert c['mode']=='scientific' and c['blocks']==32
    assert checks['record_contexts']==2048 and checks['context_draw_pairs']==4096 and checks['terminal_cue_observations']==36864
    qualification(); check_inputs(HERE/'jobs'/name)
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('scientific')}
    target=HERE/'analysis/closeout_v1.json'; assert not target.exists()
    dump(target,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        outputs_verified=len(c['outputs_sha256']),frozen_inputs_verified=len(inputs('scientific')),
        figures_inspected=True,figure_sha256=sha(run/'arrangement.png'),seconds=c['seconds'],
        primary_conclusion=c['primary_conclusion'],criterion_met=c['criterion_met'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=('register','run','verify','qualify','launch','closeout','preflight'))
    p.add_argument('--mode',choices=('fixture','benchmark','scientific')); p.add_argument('--name')
    p.add_argument('--workers',type=int,default=0); p.add_argument('--figures-inspected',action='store_true')
    a=p.parse_args(); assert 0<=a.workers<=4
    if a.action=='launch': launch(a.name,a.workers)
    else:
        cap_cpus(a.workers or (4 if a.action=='qualify' else 1))
        if a.action=='register': data.register()
        elif a.action=='preflight': preflight()
        elif a.action=='run':
            assert a.mode and a.name; execute(a.mode,a.name,a.workers or 1)
        elif a.action=='verify':
            _,c,_=verify(a.name); print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        else:
            assert a.figures_inspected
            qualify(a.name) if a.action=='qualify' else closeout(a.name)
