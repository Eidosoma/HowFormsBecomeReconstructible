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
from E073_saved_cohort_reversal_replication import data,model,audit_model,inference
from E073_saved_cohort_reversal_replication.plan import HERE,ROOT,NAMES,settings


def input_paths():
    # Snapshot the complete local Python import closure, including technical
    # projection checks, rather than guessing transitive model dependencies.
    import ast
    local=('PROTOCOL.md','DATA_DICTIONARY.md','SOURCE_DATA.json','plan.py','data.py','model.py',
        'audit_model.py','inference.py','run.py','workflow.py','tests.py','plot.py','prepare.py')
    paths={ROOT/'common.py',ROOT/'run_python.sh',ROOT/'RUN_POLICY.md'}|{HERE/p for p in local}
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


def block(run, b, cfg):
    import numpy as np
    started = time.monotonic()
    source = data.source(cfg['mode'], b)
    inter = model.intervene(source)
    data.save(run/f'source_{b:06d}.npz', source)
    data.save(run/f'interventions_{b:06d}.npz', inter)
    tick = time.monotonic()
    raw = model.rebuild(inter['packets'], b, 1, cfg['config'], cfg['cycle'])
    production_rebuild_seconds = time.monotonic()-tick
    data.save(run/f'rewrite_{b:06d}.npz', raw)
    packets = np.concatenate((inter['packets'], raw['outgoing']))
    tick = time.monotonic()
    fresh = model.develop(packets, b, cfg['reader'], cfg['reader'], 'terminal')
    production_reader_seconds = time.monotonic()-tick
    cases, records, transition = model.diagnostics(packets, inter, fresh, raw, cfg['reader'])
    for name, arrays in (('records', records), ('assay', fresh), ('cases', cases), ('transition', transition)):
        data.save(run/f'{name}_{b:06d}.npz', arrays)
    production_seconds = time.monotonic()-started

    tick = time.monotonic()
    inter2 = audit_model.intervene(source)
    data.equal(inter, inter2)
    t = time.monotonic()
    raw2 = audit_model.rebuild(inter2['packets'], b, 1, cfg['config'], cfg['cycle'])
    audit_rebuild_seconds = time.monotonic()-t
    data.equal(raw, raw2)
    packets2 = np.concatenate((inter2['packets'], raw2['outgoing']))
    assert packets.tobytes() == packets2.tobytes()
    t = time.monotonic()
    fresh2 = audit_model.develop(packets2, b, cfg['reader'], cfg['reader'], 'terminal')
    audit_reader_seconds = time.monotonic()-t
    data.equal(fresh, fresh2)
    cases2, records2, transition2 = audit_model.diagnostics(packets2, inter2, fresh2, raw2, cfg['reader'])
    data.equal(cases, cases2); data.equal(records, records2); data.equal(transition, transition2)

    old, original = model.base.decode(source['incoming']), model.base.decode(source['outgoing'])
    initial = model.base.decode(inter['packets'])
    eligible = inter['eligible']
    available = model.reader.surviving_edges(source['masks'])
    expected_source = np.where(available, np.where(source['fallback'], source['ordinary'], source['contrast']), 0.)
    physical = model.reader.surviving_edges(raw['masks'])
    output = model.base.decode(raw['outgoing'])
    expected_output = np.where(physical, np.where(raw['fallback'], raw['ordinary'], raw['contrast']), 0.)
    empty = ~eligible.any(axis=(-3, -2, -1))
    writer_empty = ~(eligible & physical).any(axis=(-3, -2, -1))
    terminal_empty = ~(eligible & model.reader.surviving_edges(fresh['masks'])).any(axis=(-3, -2, -1))
    checks = dict(
        source_capture_bytes=expected_source.tobytes() == original.tobytes(),
        source_fallback_exact=np.array_equal(source['fallback'], (source['contrast'] == 0) & available),
        eligibility_exact=np.array_equal(eligible, (old[:4] == 0) & (original[:4] != 0) & source['fallback'][:4]),
        original_bytes_exact=inter['packets'][:4].tobytes() == source['outgoing'][:4].tobytes(),
        erased_source_exact=inter['packets'][8].tobytes() == source['outgoing'][4].tobytes(),
        selected_positive_zero=not initial[4:8][eligible].any() and not np.signbit(initial[4:8][eligible]).any(),
        outside_bytes_exact=initial[4:8][~eligible].tobytes() == original[:4][~eligible].tobytes(),
        source_support_exact=np.array_equal(initial[4:8] != 0, (original[:4] != 0) & ~eligible),
        writer_receives_only_intervened_packets=raw['incoming'].tobytes() == inter['packets'].tobytes(),
        full_capture_without_repeated_pruning=output.tobytes() == expected_output.tobytes(),
        rewrite_fallback_exact=np.array_equal(raw['fallback'], (raw['contrast'] == 0) & physical),
        rewrite_physical_support=not output[np.broadcast_to(~physical, output.shape)].any(),
        final_slots_equal_complete_writer_output=packets[9:].tobytes() == raw['outgoing'].tobytes(),
        initial_slots_unchanged=packets[:9].tobytes() == inter['packets'].tobytes(),
        empty_selection_writer_alias=raw['outgoing'][4:8][empty].tobytes() == raw['outgoing'][:4][empty].tobytes(),
        writer_injury_empty_alias=raw['outgoing'][4:8][writer_empty].tobytes() == raw['outgoing'][:4][writer_empty].tobytes(),
        terminal_injury_empty_alias=fresh['end'][4:8][terminal_empty].tobytes() == fresh['end'][:4][terminal_empty].tobytes(),
        empty_selection_final_reader_alias=fresh['end'][13:17][empty].tobytes() == fresh['end'][9:13][empty].tobytes(),
        selected_capture_partition=np.array_equal(transition['fallback_selected']+transition['contrast_selected'], transition['rewritten_selected']),
        selected_capture_bounded=bool((transition['rewritten_selected'] <= transition['available_selected']).all()),
        outcome_partition=bool((sum(cases[k].astype(int) for k in ('both','correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign')) == 1).all()),
        opposite_is_wrong=bool((~cases['opposite_rule_success'] | cases['any_wrong_sign']).all()),
        erased_source_pairs_identical=all(source['outgoing'][4,f].tobytes() == source['outgoing'][4,f+1].tobytes() for f in (0,2)),
        erased_writer_pairs_identical=all(raw['outgoing'][8,f].tobytes() == raw['outgoing'][8,f+1].tobytes() for f in (0,2)),
        erased_reader_pairs_identical=all(fresh['end'][s,f].tobytes() == fresh['end'][s,f+1].tobytes() for s in (8,17) for f in (0,2)),
        erased_opposite_rules_at_most_half=all(not (cases['both'][s,f] & cases['both'][s,f+1]).any() for s in (8,17) for f in (0,2)))
    for prefix, item in (('writer', raw), ('terminal', fresh)):
        checks[prefix+'_injury_count'] = bool((item['masks'].sum(axis=(-2,-1)) == 24).all())
        checks[prefix+'_ports_protected'] = not item['masks'][..., model.P.any(axis=0)].any()
    for prefix, item in (('writer', raw), ('terminal', fresh), ('records', records)):
        gain = abs(item['coupling']).sum(axis=-3)
        checks[prefix+'_natural_unit_gain'] = np.allclose(gain, (item['denominator'] > 0).astype(float), rtol=0, atol=cfg['gain_tolerance'])
    checks = {k: bool(v) for k,v in checks.items()}
    checks['pass'] = all(checks.values())
    assert checks['pass'], checks
    legacy_projection = False
    if cfg['mode'] != 'scientific':
        from E073_saved_cohort_reversal_replication.tests import legacy_projection_check
        legacy_projection_check(source, inter, packets, b, cfg, raw, fresh)
        legacy_projection = True
    audit_seconds = time.monotonic()-tick
    dump(run/f'worker_{b}.json', dict(block=b, status='PASS', utc=utc(),
        production_seconds=production_seconds, production_rebuild_seconds=production_rebuild_seconds,
        production_reader_seconds=production_reader_seconds,
        production_static_seconds=production_seconds-production_rebuild_seconds-production_reader_seconds,
        audit_seconds=audit_seconds, audit_rebuild_seconds=audit_rebuild_seconds, audit_reader_seconds=audit_reader_seconds,
        audit_static_seconds=audit_seconds-audit_rebuild_seconds-audit_reader_seconds,
        seconds=time.monotonic()-started, controls=checks,
        terminal_cue_observations=18*4*cfg['recipients']*2, writer_cue_episodes=9*4*cfg['recipients']*2,
        legacy_projections_verified=legacy_projection, every_step_state_hashes_replayed=True,
        one_rewrite_and_removal_replayed=True, source_bytes_verified=True,
        source_boundary=1, additional_rewrites=1, repeated_pruning=False, all_source_cases_retained=True))


def execute(mode,workers):
    started=time.monotonic();cfg=settings(mode);job=HERE/'jobs'/NAMES[mode]
    check_inputs(job);data.verify_receipts(mode)
    run=new_run(HERE/'runs'/NAMES[mode],input_paths(),dict(experiment='E073',**cfg,workers=workers))
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
                dump(job/'status.json',dict(status='RUNNING',stage='rewriting_and_independent_replay',utc=utc(),
                    completed_blocks=sorted(done),total_blocks=len(cfg['blocks']),workers=workers))
                print('Verified block',done[-1],flush=True)
        cases=[data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        reports=[json.loads((run/f'worker_{b}.json').read_text()) for b in cfg['blocks']]
        controls=[r['controls'] for r in reports]
        summary=inference.analyze(cases,controls,mode);checked=inference.audit(cases,controls,summary,mode)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary))
        dump(run/'CHECKS.json',dict(status='PASS',blocks=len(done),summaries_checked=checked,
            one_rewrite_and_removal_replayed=True,all_reader_states_replayed=True,controls_pass=True,
            terminal_cue_observations=sum(r['terminal_cue_observations'] for r in reports),
            writer_cue_episodes=sum(r['writer_cue_episodes'] for r in reports),
            matched_reader_streams_verified=True,predecessor_dynamics_replayed=False))
        from E073_saved_cohort_reversal_replication.plot import plot
        plot(run,summary)
        times={f'{phase}_{kind}_block_seconds':[r[f'{phase}_{kind}_seconds'] for r in reports]
            for phase in ('production','audit') for kind in ('rebuild','reader','static')}
        finish(run,started,dict(experiment='E073',blocks_completed=len(done),controls_pass=True,**times))
        dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),
            blocks_checked=len(done),summaries_checked=checked,all_reader_states_replayed=True,
            one_rewrite_and_removal_replayed=True,controls_pass=True,primary_effects=summary['primary_effects'],
            persistence_supported=summary['persistence_supported'],reversal_replicated=summary['reversal_replicated'],
            audit_model_sha256=sha(HERE/'audit_model.py'),
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
