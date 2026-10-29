"""Excluded checks of noise construction, legacy equality, replay and inference."""
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,dump,new_run,rng,sha,utc
from E077_fresh_reconstruction_tradeoff import model as old,audit_model as old_audit
from E098_writer_pairing_tradeoff import data,model,audit,inference
from E098_writer_pairing_tradeoff.plan import HERE,ROOT,PRIMARY,CONTRASTS,settings,expected_identities
from E098_writer_pairing_tradeoff.run import code_paths,worker,scaled_source,inventory


def archived_paired_equivalence():
    data.verify_registry(); cfg=settings('benchmark')
    raw=data.load(ROOT/'E077_fresh_reconstruction_tradeoff/runs/benchmark_v1/rewrite_900041.npz')
    result=model.rebuild(raw['incoming'],900041,cfg['config'],cfg['cycle'])
    data.equal(result,audit.rebuild(raw['incoming'],900041,cfg['config'],cfg['cycle']))
    data.equal(model.legacy_projection(result),raw)
    data.equal(dict(ports=model.end_ports(result)),dict(ports=audit.end_ports(result)))
    return dict(block=900041,archived_full_paired_projection_exact=True,modified_writer_replayed=True)


def noise_and_capture_contract():
    cfg=dict(settings('fixture')['config'],recipients=1,dt=0.,birth_sd=0.,observe_steps=1)
    steps=dict(read_steps=1,settling_steps=0,write_steps=1)
    empty=old.base.encode(np.zeros((9,4,1,2,16,16)))
    b=9000982; result=model.rebuild(empty,b,cfg,steps)
    data.equal(result,audit.rebuild(empty,b,cfg,steps))
    stream=rng('E077',b,'develop',1); stream.standard_normal((2,1,16,16))
    z=old.base.paired_founders(stream.standard_normal((2,1,16,16)))
    z2=old.base.paired_founders(rng('E098',b,'writer_second_cue',1).standard_normal((2,1,16,16)))
    free=(~result['masks']) & ~old.P.any(axis=0)
    for slot,cue in np.ndindex(18,2):
        expected=cfg['noise']*(z2 if slot>=9 and cue==1 else z)
        assert result['end'][slot,:,:,cue][free].tobytes()==expected[free].tobytes()
    assert np.array_equal(result['birth'],np.zeros_like(result['birth']))
    assert np.array_equal(result['end'][:9,:,:,0],result['end'][9:,:,:,0])
    assert not np.array_equal(result['end'][:9,:,:,1],result['end'][9:,:,:,1])
    assert (result['masks'].sum((-2,-1))==24).all() and not result['masks'][...,old.P.any(axis=0)].any()
    expected=old.capture(result['end'],old.reader.surviving_edges(result['masks']),cfg['writer_beta'])
    assert old.base.encode(expected[0]).tobytes()==result['outgoing'].tobytes()
    assert not np.array_equal(result['write_end'],result['end'])
    # At zero read noise the complete physical trajectories and records coincide.
    zero=model.rebuild(empty,b,dict(settings('fixture')['config'],recipients=1,noise=0.),settings('fixture')['cycle'])
    data.equal(zero,audit.rebuild(empty,b,dict(settings('fixture')['config'],recipients=1,noise=0.),settings('fixture')['cycle']))
    for k in ('end','mean_ports','outgoing','ordinary','contrast','fallback','write_end'):
        assert zero[k][:9].tobytes()==zero[k][9:].tobytes(),k
    # The innovations retain unit Gaussian marginals; they are not a sum of two
    # unnormalized streams. This also catches accidental equal stream tags.
    a=rng('E077',b,'develop',1).standard_normal(100000)
    c=rng('E098',b,'writer_second_cue',1).standard_normal(100000)
    assert abs(np.corrcoef(a,c)[0,1])<.02
    for x in (a,c): assert abs(x.mean())<.02 and abs(x.var()-1)<.03
    return dict(actual_one_step_noise_checked=True,zero_noise_equivalence=True,capture_precedes_holding=True)


def threshold_tables_and_decision():
    # All 16 endpoint configurations, twice, must stay separate.
    rows=[]
    for i,bits in enumerate(np.ndindex(2,2,2,2)):
        a,p,x,y=bits
        for draw in (0,1):
            row=dict(task=1,arm=0,founder=0,recipient=i,draw=draw,
                     I0_both=a,P0_both=p,I1_paired_both=x,P1_paired_both=y,
                     I1_independent_both=1-x,P1_independent_both=1-y)
            for name,parts in CONTRASTS.items(): row[name+'_both']=sum(v*row[k+'_both'] for k,v in parts.items())
            rows.append(row)
    for noise in ('paired','independent'):
        table=inference.table(rows,noise); assert table['counts']==np.full((4,4),2).tolist()
        assert all(v['denominator']==8 for v in table['conditional'].values())
        assert table['later_harms']['comparisons']==8 and table['later_harms']['same_context_both_draws']==4
    interaction=inference.contrast_events(rows,'interaction')
    assert interaction['distribution']['2.0']==interaction['distribution']['-2.0']==8
    empty=inference.table([rows[0]],'paired')
    assert empty['conditional']['both_succeed']['empty'] and empty['conditional']['both_succeed']['later_harm_fraction'] is None
    def stat(lo,hi): return dict(mean=(lo+hi)/2,ci97_5=[lo,hi],ci95=[lo,hi],block_means=[(lo+hi)/2])
    st={PRIMARY[0]:stat(.01,.05),PRIMARY[1]:stat(-.01,.01),'pruning_paired_both':stat(-.1,-.02)}
    assert not inference.decision(st)['conjunction_met']  # intact damage alone cannot qualify
    st[PRIMARY[1]]=stat(.01,.02)
    assert inference.decision(st)['conclusion']=='PENALTY_ATTENUATED_WITH_PRUNED_IMPROVEMENT'
    st['pruning_paired_both']=stat(-.01,.01)
    assert inference.decision(st)['conjunction_met'] and not inference.decision(st)['paired_baseline_cost_negative']
    assert inference.classify(stat(0,.01))['direction']=='UNRESOLVED'
    assert inference.classify(stat(-.02,-.01))['direction']=='NEGATIVE'
    # Exact threshold and adjacent floating point values, both founder rules.
    for value,expected in ((.25,False),(np.nextafter(.25,1),True),(np.nextafter(.25,0),False)):
        v=np.empty((1,4,1,2,2))
        for f,c in np.ndindex(4,2):
            sign=(1.,-1.,1.,-1.)[f]*(1.,-1.)[c]
            v[0,f,0,c]=[sign*value,-sign*value]
        s=old.score(v,.25); data.equal(s,old_audit.score(v,.25)); assert (s['both']==expected).all()
    assert len(expected_identities(settings('scientific')))==4096
    t=scaled_source(dict(production_acquisition=1.,production_ancestry_read=1.,production_ancestry_write=1.,source_recovery_both=1.),
                    settings('benchmark'),settings('scientific'))
    assert {k:v['scale'] for k,v in t.items()}==dict(production_acquisition=1.,production_ancestry_read=64.,
        production_ancestry_write=4.,source_recovery_both=64.)
    return dict(binary_table_cells=16,strict_threshold_checked=True,damage_only_rejected=True)


def fresh_pipeline_and_exports():
    cfg=settings('fixture'); path=HERE/'analysis'/f'fixture_{time.time_ns()}'
    run=new_run(path,code_paths()+[HERE/'SOURCE_DATA.json'],dict(**cfg,workers=1,excluded=True))
    rows=[]; erased=[]
    for b in cfg['blocks']:
        _,part,control,result=worker((str(run),b,cfg)); assert result['status']=='PASS'
        rows.extend(part); erased.extend(control)
    summary=inference.analyze(rows,'fixture')
    assert summary['primary_conclusion']=='EXCLUDED_TECHNICAL_ONLY' and summary['criterion_met'] is None
    data.export(run/'cases.csv',rows); data.export(run/'individual_two_draw_means.csv',data.averages(rows))
    events,fields=data.events(rows); data.export(run/'events.csv',events,fields); data.export(run/'empty_events.csv',[],fields)
    data.export(run/'erased_controls.csv',erased)
    assert len(events)==sum(r[k+'_both']!=0 for r in rows for k in CONTRASTS)
    for g in summary['groups'].values(): assert g['writer_contexts']*2==g['comparisons']
    dump(run/'summary.json',summary); (run/'REPORT.md').write_text(inference.report(summary))
    return str(run.relative_to(ROOT))


def main():
    cap_cpus(1); resources=inventory(1); folder=HERE/'analysis'; folder.mkdir(exist_ok=True)
    i=1
    while (folder/f'tests_attempt_{i:03d}.json').exists(): i+=1
    start=time.monotonic(); checks={}; paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        for fn in (noise_and_capture_contract,threshold_tables_and_decision,archived_paired_equivalence,fresh_pipeline_and_exports):
            evidence=fn(); checks[fn.__name__]=dict(status='PASS',evidence=evidence)
            print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,checks=checks,inputs_sha256=paths,
                    registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{i:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-start,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc())); raise
    dump(folder/f'tests_attempt_{i:03d}.json',result)
    print(json.dumps(dict(status='PASS',seconds=result['seconds'],checks=checks)),flush=True)


if __name__=='__main__': main()
