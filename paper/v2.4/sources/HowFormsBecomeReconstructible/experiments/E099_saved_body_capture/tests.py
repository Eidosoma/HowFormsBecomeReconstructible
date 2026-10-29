"""Excluded tests for capture substitutions, fixed support and full reader replay."""
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,dump,new_run,sha,utc
from E077_fresh_reconstruction_tradeoff import model as old,audit_model as old_audit
from E099_saved_body_capture import data,model,audit,inference
from E099_saved_body_capture.plan import HERE,ROOT,PRIMARY,CONTRASTS,STARTS,settings,expected_identities,references
from E099_saved_body_capture.run import code_paths,worker,inventory


def synthetic_writer(v,mask,beta=3.):
    physical=old.reader.surviving_edges(mask)
    w,o,c,f=old.capture(v,physical,beta)
    x=np.tanh(beta*v); m=(x[...,0,:,:]+x[...,1,:,:])/2
    product=np.stack((m*np.roll(m,-1,-1),m*np.roll(m,-1,-2)),axis=-3)
    return dict(end=v,masks=mask,outgoing=old.base.encode(w),ordinary=o,contrast=c,fallback=f,cue_independent=product)


def capture_edge_cases():
    assert references()==audit.refs()
    shape=(18,4,1,2,16,16); mask=np.zeros((4,1,16,16),bool)
    e=np.zeros((4,4,1,2,16,16),bool); e[0,0,0,0,0,0]=True
    for scale in (0.,1e-80,.1):
        v=np.full(shape,scale); v[...,0,1]=-.1
        writer=synthetic_writer(v,mask)
        inter=model.intervene(writer,dict(eligible=e),dict(writer_beta=3.))
        data.equal(inter,audit.intervene(writer,dict(eligible=e),dict(writer_beta=3.)))
        w=old.base.decode(inter['packets'])
        assert w[:18].tobytes()==old.base.decode(writer['outgoing']).tobytes()
        for s in (26,30,34): assert w[s][0,0,0,0,0].tobytes()==w[13][0,0,0,0,0].tobytes()
        # The inherited coactivity reduction yields +0 here. The byte checks
        # above require preserving its actual zero sign, not inventing -0.
        if scale==0.: assert w[30,0,0,0,0,0]==0.
    # Empty selection leaves every counterfactual exactly equal to its own body.
    empty=np.zeros_like(e); writer=synthetic_writer(np.full(shape,.2),mask)
    inter=model.intervene(writer,dict(eligible=empty),dict(writer_beta=3.)); data.equal(inter,audit.intervene(writer,dict(eligible=empty),dict(writer_beta=3.)))
    w=old.base.decode(inter['packets']); assert w.tobytes()==w[references()[0]].tobytes()
    # All selected endpoints injured: replacement preserves the physical zeros.
    injured=mask.copy(); injured[0,0,0,0]=True
    writer=synthetic_writer(np.full(shape,.2),injured)
    inter=model.intervene(writer,dict(eligible=e),dict(writer_beta=3.)); data.equal(inter,audit.intervene(writer,dict(eligible=e),dict(writer_beta=3.)))
    assert not old.base.decode(inter['packets'])[inter['eligible']].any()
    # Equal-and-opposite coactivity terms cancel exactly, while contrast survives.
    v=np.full(shape,.1)
    v[13,0,0,:,0,0]=[.2,.1]; v[13,0,0,:,0,1]=[.1,-.2]
    writer=synthetic_writer(v,mask)
    assert writer['ordinary'][13,0,0,0,0,0]==0 and writer['contrast'][13,0,0,0,0,0]!=0
    for fn in (model.intervene,audit.intervene):
        try: fn(writer,dict(eligible=e),dict(writer_beta=3.))
        except AssertionError as error: assert 'support mismatch' in str(error).lower()
        else: raise AssertionError('Support mismatch was not rejected')
    # Corrupted saved capture is rejected before terminal dynamics.
    writer=synthetic_writer(np.full(shape,.1),mask); writer['ordinary'][0,0,0,0,0,0]+=.01
    for fn in (model.intervene,audit.intervene):
        try: fn(writer,dict(eligible=e),dict(writer_beta=3.))
        except AssertionError: pass
        else: raise AssertionError('Corrupted source capture accepted')
    return dict(empty_and_injured_masks=True,zero_sign_bits_and_tiny_weights=True,support_mismatch_rejected=True,corrupt_capture_rejected=True)


def tables_thresholds_and_criterion():
    rows=[]
    for i,(o,s,m,h) in enumerate(np.ndindex(2,2,2,2)):
        for d in (0,1):
            r=dict(task=1,arm=0,founder=0,recipient=i,draw=d,old_E098_draw=d,
                P_ind_O_both=o,P_ind_S_both=s,P_ind_M_both=m,P_ind_H_both=h,
                I_pair_H_both=o,P_pair_H_both=s,I_ind_H_both=m)
            rows.append(r)
    assert inference.factorial_table(rows)['counts']==np.full((2,2,2,2),2).tolist()
    table=inference.joint_table(rows,('I_pair_H','P_pair_H'),('I_ind_H','P_ind_H'))
    assert table['counts']==np.full((4,4),2).tolist()
    assert table['after_harms']['comparisons']==8 and table['after_harms']['same_context_both_draws']==4
    for r in rows: r['component_interaction_both']=r['P_ind_H_both']-r['P_ind_M_both']-r['P_ind_S_both']+r['P_ind_O_both']
    events=inference.contrast_events(rows,'component_interaction')
    assert events['distribution']['2.0']==events['distribution']['-2.0']==2
    def stat(lo,hi): return dict(mean=(lo+hi)/2,ci97_5=[lo,hi],ci95=[lo,hi],block_means=[(lo+hi)/2])
    stats={PRIMARY[0]:stat(.01,.05),PRIMARY[1]:stat(-.01,.01)}
    assert not inference.decision(stats)['conjunction_met']
    stats[PRIMARY[1]]=stat(.01,.03); assert inference.decision(stats)['conjunction_met']
    stats[PRIMARY[0]]=stat(0,.03); assert not inference.decision(stats)['conjunction_met']
    stats[PRIMARY[0]]=stat(-.03,-.01)
    assert inference.decision(stats)['conclusion']=='ORDINARY_SELECTED_CAPTURE_OUTPERFORMS_HYBRID'
    for value,expected in ((.25,False),(np.nextafter(.25,1),True),(np.nextafter(.25,0),False)):
        v=np.empty((1,4,1,2,2))
        for f,c in np.ndindex(4,2):
            sign=(1.,-1.,1.,-1.)[f]*(1.,-1.)[c]; v[0,f,0,c]=[sign*value,-sign*value]
        scores=old.score(v,.25); data.equal(scores,old_audit.score(v,.25)); assert (scores['both']==expected).all()
    assert len(expected_identities(settings('scientific')))==4096
    assert 38*4*4*2*2*32==77824
    return dict(factorial_configurations=16,joint_configurations=16,strict_threshold_checked=True,conjunction_checked=True)


def archived_reader_parity():
    cfg=settings('benchmark'); task=9000980
    packets=data.pinned('benchmark','terminal_packets_9000980.npz')['packets']
    archived=data.pinned('benchmark','assay_9000980_r0.npz')
    fresh=old.develop(packets,task,cfg['config'],cfg['reader'],'E098_terminal_0',0)
    data.equal(fresh,archived)
    return dict(all_archived_reader_fields_and_state_hashes_exact=True)


def complete_fixtures():
    cfg=settings('fixture'); path=HERE/'analysis'/f'fixture_{time.time_ns()}'
    run=new_run(path,code_paths()+[HERE/'SOURCE_DATA.json'],dict(**cfg,workers=1,excluded=True))
    rows=[]; erased=[]
    for b in cfg['blocks']:
        _,r,e,report=worker((str(run),b,cfg)); assert report['status']=='PASS'; rows.extend(r); erased.extend(e)
    summary=inference.analyze(rows,'fixture')
    assert summary['primary_conclusion']=='EXCLUDED_TECHNICAL_ONLY' and summary['criterion_met'] is None
    assert summary['legacy_tables_checked']==12
    data.export(run/'cases.csv',rows); data.export(run/'individual_two_draw_means.csv',data.averages(rows))
    events,fields=data.events(rows); data.export(run/'events.csv',events,fields); data.export(run/'empty_events.csv',[],fields)
    data.export(run/'erased_controls.csv',erased)
    assert len(events)==sum(r[k+'_both']!=0 for r in rows for k in CONTRASTS)
    assert all(r['filter_pruned_pair_both']==0 for r in rows)
    assert not any(k.startswith('old_E098_') for g in summary['groups'].values() for k in g['statistics'])
    dump(run/'summary.json',summary); (run/'REPORT.md').write_text(inference.report(summary))
    return str(run.relative_to(ROOT))


def main():
    cap_cpus(1); resources=inventory(1); folder=HERE/'analysis'; folder.mkdir(exist_ok=True)
    i=1
    while (folder/f'tests_attempt_{i:03d}.json').exists(): i+=1
    start=time.monotonic(); checks={}; paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        for fn in (capture_edge_cases,tables_thresholds_and_criterion,archived_reader_parity,complete_fixtures):
            evidence=fn(); checks[fn.__name__]=dict(status='PASS',evidence=evidence); print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,checks=checks,inputs_sha256=paths,
                    registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{i:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-start,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc())); raise
    dump(folder/f'tests_attempt_{i:03d}.json',result)
    print(json.dumps(dict(status='PASS',seconds=result['seconds'],checks=checks)),flush=True)


if __name__=='__main__': main()
