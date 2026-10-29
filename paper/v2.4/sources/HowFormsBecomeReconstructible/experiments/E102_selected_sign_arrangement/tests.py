"""Excluded permutation controls, exact archived parity and full reader replay."""
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,dump,new_run,sha,utc
from E077_fresh_reconstruction_tradeoff import model as old,audit_model as old_audit
from E102_selected_sign_arrangement import data,model,audit,inference
from E102_selected_sign_arrangement.plan import HERE,ROOT,PRIMARY,CONTRASTS,STARTS,METRICS,settings,expected_identities
from E102_selected_sign_arrangement.run import code_paths,worker,inventory


def synthetic_regions(selection='partial'):
    stream=np.random.default_rng(102)
    w=stream.uniform(-1,1,(18,4,1,2,16,16))
    e=np.zeros((4,4,1,2,16,16),bool)
    if selection=='all': e[:]=True
    elif selection in ('partial','homogeneous'): e[...,::3,::3]=True
    elif selection=='singleton': e[...,0,0,0]=True
    elif selection!='empty': raise ValueError(selection)
    if selection=='homogeneous': w[4:8][e]=abs(w[4:8][e])
    w[4:8][~e]=w[:4][~e]
    physical=np.ones((4,1,2,16,16),bool)
    for slot in (16,17):
        w[slot,1]=w[slot,0]; w[slot,3]=w[slot,2]
    masks=np.zeros(w.shape,bool); masks[:4]=e; masks[4:8]=e
    return dict(packets=old.base.encode(w),eligible=masks,physical=physical)


def reject(fn,fragment):
    try: fn()
    except AssertionError as error:
        assert fragment.lower() in str(error).lower(),str(error)
    else: raise AssertionError('Invalid input accepted: '+fragment)


def permutation_edge_cases():
    cfg=settings('fixture'); task=9000980; first=None
    for selection in ('partial','all','empty','homogeneous','singleton'):
        saved=data.component_model.intervene(synthetic_regions(selection))
        inter=model.intervene(saved,task); data.equal(inter,audit.intervene(saved,task))
        model.preflight_checks(inter)
        w=old.base.decode(inter['packets']); d,s=w[8:12],w[12:16]
        for loc in np.ndindex(d.shape[:3]):
            mapping=inter['shuffle_source_edge'][loc].ravel()
            inverse=np.argsort(mapping)
            recovered=np.copysign(abs(d[loc].ravel()),s[loc].ravel()[inverse])
            assert recovered.tobytes()==d[loc].ravel().tobytes()
        data.equal(inter,model.intervene(saved,task))
        if selection in ('empty','homogeneous','singleton'):
            assert d.tobytes()==s.tobytes(),'Degenerate permutation must not be rerolled'
        else: assert d.tobytes()!=s.tobytes()
        if selection=='partial':
            other=model.intervene(saved,task+1)
            assert inter['shuffle_source_edge'].tobytes()!=other['shuffle_source_edge'].tobytes()
        for draw in (0,1):
            fresh=old.develop(inter['packets'],task,cfg['config'],cfg['reader'],f'E102_terminal_{draw}',0)
            data.equal(fresh,old_audit.develop(inter['packets'],task,cfg['config'],cfg['reader'],f'E102_terminal_{draw}',0))
            dg,cp=model.diagnostics(inter,fresh); dg2,cp2=audit.diagnostics(inter,fresh)
            data.equal(dg,dg2); data.equal(cp,cp2)
            cases=old.score(fresh['mean_ports'],.25); data.equal(cases,old_audit.score(fresh['mean_ports'],.25))
            model.checks(inter,fresh,cases,cp,draw)
            assert not dg['donor_unsigned_coupling_l1'][4:16].any()
            assert not dg['postinjury_donor_unsigned_coupling_l1'][4:16].any()
            if selection=='partial' and draw==0: first=(inter,fresh,cases,cp)
    for a,b in ((-0.,0.),(0.,-0.),(1e-280,-2e-280),(-.2,.7)):
        regions=synthetic_regions(); w=old.base.decode(regions['packets'])
        w[0,0,0,0,0,0]=a; w[4,0,0,0,0,0]=b; regions['packets']=old.base.encode(w)
        saved=data.component_model.intervene(regions)
        inter=model.intervene(saved,task); data.equal(inter,audit.intervene(saved,task)); model.preflight_checks(inter)
        out=old.base.decode(inter['packets']); d,s=out[8:12],out[12:16]
        assert abs(d).tobytes()==abs(s).tobytes()
        assert d[d==0].tobytes()==s[d==0].tobytes()
    regions=synthetic_regions(); regions['physical'][0,0,0,0,0]=False
    w=old.base.decode(regions['packets']); w[:,0,0,0,0,0]=0.; regions['packets']=old.base.encode(w)
    saved=data.component_model.intervene(regions); inter=model.intervene(saved,task)
    data.equal(inter,audit.intervene(saved,task)); model.preflight_checks(inter)
    assert not old.base.decode(inter['packets'])[:,0,0,0,0,0].any()
    for loc,fragment in (((0,0),'support mismatch'),((0,1),'outside donor mismatch')):
        saved=data.component_model.intervene(synthetic_regions()); w=old.base.decode(saved['packets'])
        w[0,0,0,0,*loc]=0.; saved['packets']=old.base.encode(w)
        for fn in (model.intervene,audit.intervene): reject(lambda:fn(saved,task),fragment)
    inter,fresh,cases,cp=first
    broken={k:v.copy() for k,v in inter.items()}; broken['shuffle_source_edge'][0,0,0].ravel()[0]=1
    reject(lambda:model.checks(broken,fresh,cases,cp,0),'bijective')
    broken={k:v.copy() for k,v in inter.items()}; broken['injury_masks'][0,0,0,0,0]^=True
    reject(lambda:model.checks(broken,fresh,cases,cp,0),'conditioning mismatch')
    writer=data.pinned('benchmark','source_writer_9000980.npz')
    pruning=data.pinned('benchmark','source_pruning_9000980.npz')
    writer['ordinary'][0,0,0,0,0,0]+=.01
    for fn in (data.capture_model.intervene,data.capture_audit.intervene): reject(lambda:fn(writer,pruning,cfg['config']),'')
    return dict(scalar_vector_permutation_and_inverse=True,exact_original_endpoints=True,
        empty_singleton_homogeneous_all_selected_and_injured=True,no_outcome_conditioning_or_rerolls=True,
        sign_counts_exact_in_every_stratum_and_both_injuries=True,stored_zero_bits_and_tiny_weights=True,
        fixed_magnitudes_denominators_and_absolute_coupling=True,full_synthetic_reader_replay=True,
        corrupt_sources_masks_and_maps_rejected=True)


def tables_thresholds_and_criterion():
    rows=[]
    for i,values in enumerate(np.ndindex(2,2,2,2)):
        for draw in (0,1):
            r=dict(task=1,arm=0,kind='native',history='sham',founder=0,recipient=i,draw=draw,
                   old_E098_draw=draw,old_E099_draw=draw,old_E100_draw=draw,old_E101_draw=draw)
            for label,value in zip(STARTS,values):
                for metric in METRICS:r[label+'_'+metric]=float(value)
            for prefix,starts in data.LEGACY:
                for label in starts:
                    for metric in METRICS:r[prefix+label+'_'+metric]=0.
            for name,parts in CONTRASTS.items():
                for metric in METRICS:r[name+'_'+metric]=sum(c*r[v+'_'+metric] for v,c in parts.items())
            assert r['selected_transfer_both']==r['donor_sign_both']+r['magnitude_only_both']
            assert r['selected_transfer_both']==r['arrangement_advantage_both']+r['shuffled_transfer_both']
            assert r['donor_sign_both']==r['arrangement_advantage_both']+r['shuffle_sign_both']
            rows.append(r)
    assert inference.outcome_table(rows)['counts']==np.full((2,2,2,2),2).tolist()
    for name in CONTRASTS:
        result=inference.contrast_events(rows,name)
        assert result['positive']['same_context_both_draws']>0 and result['negative']['same_context_both_draws']>0
        assert result['distribution']['-2.0']==result['distribution']['2.0']==0
    events,fields=data.events(rows)
    assert len(events)==sum(r[c+'_both']!=0 for r in rows for c in CONTRASTS)
    assert {e['event_kind'] for e in events}=={'gain','harm'}
    def stat(lo,hi):return dict(mean=(lo+hi)/2,ci97_5=[lo,hi],ci95=[lo,hi],block_means=[(lo+hi)/2])
    stats={PRIMARY[0]:stat(.01,.05),PRIMARY[1]:stat(-.01,.01)}
    assert not inference.decision(stats)['conjunction_met']
    stats[PRIMARY[1]]=stat(.01,.03); assert inference.decision(stats)['conjunction_met']
    stats[PRIMARY[0]]=stat(0,.03); assert not inference.decision(stats)['conjunction_met']
    stats[PRIMARY[0]]=stat(-.03,-.01)
    assert inference.decision(stats)['conclusion']=='SHUFFLE_OUTPERFORMS_DONOR_ARRANGEMENT'
    reject(lambda:inference.statistics(rows,['old_E101_N00_both'],[1],np.ones((1,1))), '')
    for value,expected in ((.25,False),(np.nextafter(.25,1),True),(np.nextafter(.25,0),False)):
        v=np.empty((1,4,1,2,2))
        for f,c in np.ndindex(4,2):
            sign=(1.,-1.,1.,-1.)[f]*(1.,-1.)[c]; v[0,f,0,c]=[sign*value,-sign*value]
        scores=old.score(v,.25); data.equal(scores,old_audit.score(v,.25)); assert (scores['both']==expected).all()
    assert len(expected_identities(settings('scientific')))==4096
    assert 18*4*4*2*2*32==36864
    return dict(all_outcome_configurations_and_three_path_identities=True,every_gain_and_harm_exported=True,
        strict_threshold_and_two_primary_requirements=True,old_endpoints_excluded_from_new_intervals=True)


def archived_reader_parity():
    cfg=settings('benchmark'); task=9000980
    packets=data.pinned('benchmark','interventions_9000980.npz')['packets']
    archived=data.pinned('benchmark','assay_9000980_r0.npz')
    fresh=old.develop(packets,task,cfg['config'],cfg['reader'],'E101_terminal_0',0)
    data.equal(fresh,archived)
    return dict(all_E101_archived_reader_fields_and_state_hashes_exact=True)


def complete_fixtures():
    cfg=settings('fixture'); path=HERE/'analysis'/f'fixture_{time.time_ns()}'
    run=new_run(path,code_paths()+[HERE/'SOURCE_DATA.json'],dict(**cfg,workers=1,excluded=True))
    rows=[]; erased=[]
    for b in cfg['blocks']:
        _,r,e,report=worker((str(run),b,cfg)); assert report['status']=='PASS'; rows.extend(r); erased.extend(e)
    summary=inference.analyze(rows,'fixture')
    assert summary['primary_conclusion']=='EXCLUDED_TECHNICAL_ONLY' and summary['criterion_met'] is None
    assert summary['legacy_tables_checked']==42 and summary['outcome_tables_checked']==6
    data.export(run/'cases.csv',rows); data.export(run/'individual_two_draw_means.csv',data.averages(rows))
    events,fields=data.events(rows); data.export(run/'events.csv',events,fields); data.export(run/'empty_events.csv',[],fields)
    data.export(run/'erased_controls.csv',erased)
    assert len(events)==sum(r[k+'_both']!=0 for r in rows for k in CONTRASTS)
    assert not any(k.startswith('old_') for g in summary['groups'].values() for k in g['statistics'])
    dump(run/'summary.json',summary); (run/'REPORT.md').write_text(inference.report(summary))
    return str(run.relative_to(ROOT))


def main():
    cap_cpus(1); resources=inventory(1); folder=HERE/'analysis'; folder.mkdir(exist_ok=True)
    i=1
    while (folder/f'tests_attempt_{i:03d}.json').exists():i+=1
    start=time.monotonic(); checks={}; paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        for fn in (permutation_edge_cases,tables_thresholds_and_criterion,archived_reader_parity,complete_fixtures):
            evidence=fn(); checks[fn.__name__]=dict(status='PASS',evidence=evidence); print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,checks=checks,inputs_sha256=paths,
                    registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{i:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-start,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc()));raise
    dump(folder/f'tests_attempt_{i:03d}.json',result)
    print(json.dumps(dict(status='PASS',seconds=result['seconds'],checks=checks)),flush=True)


if __name__=='__main__':main()
