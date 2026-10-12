"""Independent mask selection, new body trajectories, packet interventions and terminal replay."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from E015_functional_inheritance.audit import advance, pair, pack, unpack, ports, random, read_json, sha, verify, EXPECTED
from E022_reader_compensation.audit import load_arrays, equal, masks_for, advance_compensated, correlations
from E023_receiver_compensation.audit import replay_assay
import numpy as np
CONDITIONS=('kept_refreshed','kept_frozen','erased_refreshed','erased_frozen')
RECEIVERS=('fixed_four','local_strength')
PANELS=tuple((c,r) for r in RECEIVERS for c in CONDITIONS)
ARMS=('own','foreign','shuffled','erased','untrained','communication_off','source_cut')
DAMAGE=('intact','scattered','square')
RULES=(1,-1,1,-1);CUES=(1,-1)


def replay_body(raw, incoming, masks, available, target, block, cfg, cycle):
    R, p = cfg['recipients'], ports()
    equal(raw['incoming'],incoming);equal(raw['renewal_masks'],masks)
    equal(raw['available'],available);equal(raw['target'],target)
    body_masks=np.stack((masks[2],masks[2]));equal(raw['body_masks'],body_masks)
    before=unpack(incoming)
    effective=np.stack((before*available[2],before*available[2]))
    for f,r,d,y,x in np.argwhere(target):effective[1,f,r,d,y,x]=0.
    packets=pack(effective);equal(raw['read_packets'],packets)
    denominator=np.empty((2,4,R,16,16))
    w=abs(effective)
    for y in range(16):
        for x in range(16):
            denominator[...,y,x]=w[...,0,y,x]+w[...,0,y,(x-1)%16]+w[...,1,y,x]+w[...,1,(y-1)%16,x]
    equal(denominator,raw['read_denominators'])
    assert np.isfinite(denominator).all() and (denominator>=0).all()
    stream=random('E022',block,'develop',3)
    birth=cfg['birth_sd']*pair(stream.standard_normal((2,R,16,16)))
    equal(birth,raw['birth'])
    v=np.broadcast_to(birth[None,:,:,None],(2,4,R,2,16,16)).copy()
    active=(~body_masks)[:,:,:,None];weights=effective[:,:,:,None]
    v*=active;cue=np.array(CUES).reshape(1,1,1,2,1);v[...,p[0]]=cue
    trace=[]
    for t in range(cycle['read_steps']):
        noise=pair(stream.standard_normal((2,R,16,16)))[None,:,:,None]
        v=advance_compensated(v,weights,denominator[:,:,:,None],noise,cfg,t>=cycle['settling_steps'])
        v*=active;v[...,p[0]]=cue
        assert not (v*body_masks[:,:,:,None]).any()
        if t>=cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
    equal(v,raw['developed_end']);equal(trace,raw['developed_late_ports'])
    packets.fill(0);equal(packets,raw['erased_packets'])
    captured=pack(correlations(v,cfg['writer_beta']).mean(axis=3))
    equal(captured,raw['computed_packets'])
    assert not unpack(captured)[:,~available[2]].any()
    stream=random('E022',block,'write',3)
    scaffold=np.stack((available[2],available[2]))[:,:,:,None].astype(float)
    assert raw['write_states'].shape==(cycle['write_steps'],2,4,R,2,16,16)
    for t in range(cycle['write_steps']):
        noise=pair(stream.standard_normal((2,R,16,16)))[None,:,:,None]
        v=advance(v,scaffold,2.,noise,cfg);v*=active;v[...,p[0]]=cue
        assert not (v*body_masks[:,:,:,None]).any()
        equal(v,raw['write_states'][t])
    equal(v,raw['write_end'])
    captured_weights=unpack(captured)
    final=np.stack((captured_weights[0],captured_weights[0],captured_weights[1],captured_weights[1]))
    for f,r,d,y,x in np.argwhere(target):
        final[1,f,r,d,y,x]=before[f,r,d,y,x]
        final[3,f,r,d,y,x]=before[f,r,d,y,x]
    assert not final[:,~available[2]].any() and np.max(abs(final))<=1.
    records=pack(final);equal(records,raw['records'])
    values=np.asarray(trace).mean(axis=0)
    desired=np.array(RULES).reshape(1,4,1,1)*np.array(CUES).reshape(1,1,1,2)
    a,b=desired*values[...,0],-desired*values[...,1]
    correct=(a>cfg['margin'])&(b>cfg['margin']);margin=np.minimum(a,b)
    descriptions=[]
    for f in range(4):
        for r in range(R):
            t=target[f,r];count=int(np.count_nonzero(t));old=abs(before[f,r][t])
            row=dict(founder=f,lineage=r,target_count=count,incoming_nonzero=int(np.count_nonzero(old)))
            for label,vector in [('incoming',old),('kept',abs(captured_weights[0,f,r][t])),('erased',abs(captured_weights[1,f,r][t]))]:
                row[label+'_mean_abs']=float(np.mean(vector)) if count else 0.
                row[label+'_strong']=int(np.count_nonzero(vector>.5))
            descriptions.append(row)
    return records,dict(correct=correct,margin=margin,output=values,accuracy=correct.mean(axis=(1,2,3)),
        both_cues=correct.all(axis=3).mean(axis=(1,2)),mean_margin=margin.mean(axis=(1,2,3)),strength=descriptions)


def inspect_block(task):
    run,block,label,cfg,cycle=task
    spec=read_json(HERE/'SOURCE_DATA.json')[label];source=ROOT/spec['path']
    for name,digest in spec['provenance_sha256'].items():assert sha(source/name)==digest
    source_complete=read_json(source/'COMPLETE.json')
    for name,digest in spec['files'][str(block)].items():
        assert sha(source/name)==digest==source_complete['outputs_sha256'][name]
    receipt=read_json(source/'INDEPENDENT_AUDIT.json')
    assert receipt['status']=='PASS' and receipt['complete_sha256']==sha(source/'COMPLETE.json')
    masks=[];copies=[];original=None;incoming=None;R=cfg['recipients']
    for g in (1,2,3):
        with np.load(source/f'boundary_{block:06d}_g{g}.npz',allow_pickle=False) as saved:
            mask=saved['renewal_mask'];outgoing=saved['outgoing']
        equal(mask,masks_for(block,g,R,renewal=True)[:,:,1]);masks.append(mask)
        if original is None:original=outgoing[4].copy()
        equal(original,outgoing[4]);copies.append(unpack(outgoing[5]))
        if g==2:incoming=outgoing[2].copy()
    masks=np.stack(masks)
    assert masks.dtype==bool and masks.shape==(3,4,R,16,16)
    assert (masks.sum(axis=(-2,-1))==24).all() and not (masks & ports().any(axis=0)).any()
    available=np.zeros((3,4,R,2,16,16),bool)
    for y in range(16):
        for x in range(16):
            available[:,:,:,0,y,x]=~(masks[:,:,:,y,x]|masks[:,:,:,y,(x+1)%16])
            available[:,:,:,1,y,x]=~(masks[:,:,:,y,x]|masks[:,:,:,(y+1)%16,x])
    for g in range(3):equal(copies[g],unpack(original)*available[:g+1].all(axis=0))
    target=(~available[0]) & available[1] & available[2]
    assert not unpack(incoming)[~available[1]].any()
    raw=load_arrays(run/f'boundary_{block:06d}.npz')
    records,body=replay_body(raw,incoming,masks,available,target,block,cfg,cycle)
    with np.load(source/f'boundary_{block:06d}_g3.npz',allow_pickle=False) as old:
        equal(raw['incoming'],old['incoming'][2]);equal(raw['birth'],old['birth'])
        for key in ('body_masks','read_packets','read_denominators','developed_end','computed_packets','write_end'):
            equal(raw[key][0],old[key][2])
        for key in ('developed_late_ports','write_states'):equal(raw[key][:,0],old[key][:,2])
        equal(records[0],old['outgoing'][2])
    meta=read_json(run/f'worker_{block}.json')
    assert meta['block']==block and meta['source']==label and meta['source_files_sha256']==spec['files'][str(block)]
    assert meta['original_generation_three_body_and_terminal_arrays_exact']
    raw=load_arrays(run/f'assay_{block:06d}.npz')
    with np.load(source/f'assay_{block:06d}_h3.npz',allow_pickle=False) as old:
        for key in ('permutations','masks','birth'):equal(raw[key],old[key])
        equal(raw['packets'][0],old['packets'][2])
        for key in ('receiver_denominators','end','late_mean'):equal(raw[key][[0,4]],old[key][[2,10]])
        equal(raw['late_ports'][:,[0,4]],old['late_ports'][:,[2,10]])
    c,m,v=replay_assay(raw,records,block,3,cfg,cycle)
    return dict(correct=c,margin=m,output=v,accuracy=c.mean(axis=(1,2,3)),body=body,
        both_cues=c.all(axis=3).mean(axis=(1,2)),mean_margin=m.mean(axis=(1,2,3)),
        rules=np.stack([c[:,[r,r+2]][...,0].mean(axis=(1,2,3)) for r in range(2)],axis=1))


def check_bodies(run,results,ids,cfg,s,check):
    metrics=(('accuracy','accuracy'),('both_cues','both_cues'),('margin','mean_margin'))
    for metric,key in metrics:
        array=np.array([r['body'][key] for r in results])
        for k,reading in enumerate(('kept','erased')):check(array[:,k],s['bodies'][reading][metric])
        check(array[:,0]-array[:,1],s['body_contrasts'][metric])
    fields=('target_count','incoming_nonzero','incoming_mean_abs','incoming_strong','kept_mean_abs','kept_strong','erased_mean_abs','erased_strong')
    assert set(s['target_strength'])==set(fields)
    for key in fields:
        check(np.array([np.mean([row[key] for row in result['body']['strength']]) for result in results]),s['target_strength'][key])
    assert s['empty_target_sets']==sum(row['target_count']==0 for result in results for row in result['body']['strength'])
    with (run/'target_strength.csv').open(newline='') as handle:
        rows=csv.DictReader(handle);count=0
        for block,result in zip(ids,results):
            for expected in result['body']['strength']:
                row=next(rows);count+=1
                assert int(row['block'])==block
                for key,value in expected.items():assert float(row[key])==value,(key,row[key],value)
        assert next(rows,None) is None and count==4*cfg['recipients']*len(ids)
    count=0
    with (run/'body_observations.csv').open(newline='') as handle:
        rows=csv.DictReader(handle)
        for block,result in zip(ids,results):
            body=result['body']
            for k,reading in enumerate(('kept','erased')):
                for f in range(4):
                    for r in range(cfg['recipients']):
                        for c,cue in enumerate(CUES):
                            row=next(rows);count+=1;ix=(k,f,r,c)
                            assert (int(row['block']),row['reading'],int(row['founder']),int(row['rule']),int(row['lineage']),int(row['cue']))==(block,reading,f,RULES[f],r,cue)
                            assert int(row['success'])==body['correct'][ix] and float(row['margin'])==body['margin'][ix]
                            assert float(row['output_A'])==body['output'][ix+(0,)] and float(row['output_B'])==body['output'][ix+(1,)]
        assert next(rows,None) is None
    assert count==s['body_individual_observations']==len(ids)*2*4*cfg['recipients']*2
    assert s['target_definition']=='not available at g1; available at g2 and g3; no weight threshold'
    return count


def audit(run,workers=8):
    started=time.monotonic()
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    manifest=verify(run);contract=manifest['contract'];label=contract['source']
    spec=read_json(HERE/'SOURCE_DATA.json')[label]
    cfg,cycle,ids=contract['config'],contract['cycle'],contract['blocks']
    assert cfg==spec['config'] and cycle==spec['cycle'] and ids==spec['blocks']
    assert ids==({'cohort':list(range(24000,24032)),'benchmark':[900027],'fixture':[900027]}[label])
    assert contract['mode']=={'cohort':'post_hoc_intervention','benchmark':'technical','fixture':'technical_fixture'}[label]
    if label!='fixture':
        assert cfg==(dict(EXPECTED,recipients=1) if label=='benchmark' else EXPECTED)
        assert cycle==dict(read_steps=2048,settling_steps=256,write_steps=128,generations=3)
    assert contract['panels']==[list(p) for p in PANELS] and contract['gain']==2.
    assert contract['conditions']==list(CONDITIONS) and contract['receivers']==list(RECEIVERS)
    source_manifest=read_json(ROOT/spec['path']/'manifest.json')
    for rel,digest in source_manifest['inputs_sha256'].items():
        assert sha(ROOT/rel)==digest and sha(ROOT/spec['path']/'inputs'/rel)==digest
    with ProcessPoolExecutor(max_workers=min(workers,len(ids))) as pool:
        results=list(pool.map(inspect_block,[(run,b,label,cfg,cycle) for b in ids]))
    arrays={key:np.array([r[raw] for r in results]) for key,raw in
        (('accuracy','accuracy'),('both_cues','both_cues'),('margin','mean_margin'),('rules','rules'))}
    draws=random('E028','bootstrap','precursor').integers(0,len(ids),(10000,len(ids)))
    def check(x,st):
        equal(x,st['block_means']);assert float(x.mean())==st['mean']
        equal(np.quantile(x[draws].mean(axis=1),[.025,.975]),st['ci95'])
    s=read_json(run/'summary.json');technical=label!='cohort'
    for key,value in dict(experiment='E028',source=label,blocks=ids,cfg=cfg,cycle=cycle,
        conditions=list(CONDITIONS),receivers=list(RECEIVERS),panels=[list(x) for x in PANELS],arms=list(ARMS),damage=list(DAMAGE),
        founders=4*len(ids),lineages=4*cfg['recipients']*len(ids),original_endpoint_replay_exact=True,
        new_teaching=False,new_generation_three_read_variants=2,new_independent_cohort=False,
        status='TECHNICAL_ONLY' if technical else 'PRECURSOR_DIAGNOSTIC_COMPLETE',
        evidence_status='technical' if technical else 'post_hoc_saved_cohort_intervention').items():assert s[key]==value,key
    for k,(condition,receiver) in enumerate(PANELS):
        group=s['groups'][receiver][condition];gates={}
        for d,damage in enumerate(DAMAGE):
            for a,arm in enumerate(ARMS):
                for metric in ('accuracy','both_cues','margin'):check(arrays[metric][:,k,d,a],group[metric][damage][arm])
                if a:
                    st=group['own_minus_control'][damage][arm]
                    check(arrays['accuracy'][:,k,d,0]-arrays['accuracy'][:,k,d,a],st)
                    gates[f'advantage_{damage}_{arm}']=st['ci95'][0]>.10
            for ri,rule in enumerate((1,-1)):
                st=group['own_accuracy_by_rule'][str(rule)][damage]
                check(arrays['rules'][:,k,ri,d],st);gates[f'accuracy_rule_{rule}_{damage}']=st['ci95'][0]>.75
        assert group['gates']==gates and group['all_original_gates_pass']==all(gates.values())
    for ri,receiver in enumerate(RECEIVERS):
        for metric in ('accuracy','both_cues','margin'):
            for d,damage in enumerate(DAMAGE):
                p=[arrays[metric][:,4*ri+i,d,0] for i in range(4)]
                values=dict(total_effect=p[0]-p[3],rewrite_with_precursors=p[0]-p[1],
                    precursors_with_rewriting=p[0]-p[2],rewrite_without_precursors=p[2]-p[3],
                    precursors_without_rewriting=p[1]-p[3],interaction=(p[0]-p[1])-(p[2]-p[3]))
                assert set(s['contrasts'][receiver])==set(values)
                for name,value in values.items():check(value,s['contrasts'][receiver][name][metric][damage])
    assert set(s['focal'])=={'rewrite_with_precursors','precursors_with_rewriting'}
    for name,item in s['focal'].items():
        st=s['contrasts']['local_strength'][name]['both_cues']['scattered']
        assert item['statistics']==st
        assert item['lower_bound_above_zero']==(None if technical else st['ci95'][0]>0)
        assert item['lower_bound_above_010']==(None if technical else st['ci95'][0]>.10)
    if label=='cohort':
        old=read_json(ROOT/spec['path']/'summary.json')
        for receiver in RECEIVERS:
            for new,previous in (('kept_refreshed','strength_compensated'),):
                for metric in ('accuracy','both_cues','margin'):
                    for damage in DAMAGE:
                        for arm in ARMS:
                            equal(s['groups'][receiver][new][metric][damage][arm]['block_means'],
                                  old['groups']['3'][receiver][previous][metric][damage][arm]['block_means'])
    count=0
    with (run/'observations.csv').open(newline='') as handle:
        rows=csv.DictReader(handle)
        for block,result in zip(ids,results):
            for k,(condition,receiver) in enumerate(PANELS):
                for f in range(4):
                    for r in range(cfg['recipients']):
                        for c,cue in enumerate(CUES):
                            for d,damage in enumerate(DAMAGE):
                                for a,arm in enumerate(ARMS):
                                    row=next(rows);count+=1;ix=(k,f,r,c,d,a)
                                    assert (int(row['block']),row['condition'],row['receiver'],int(row['founder']),int(row['rule']),int(row['lineage']),int(row['cue']),row['damage'],row['arm'])==(block,condition,receiver,f,RULES[f],r,cue,damage,arm)
                                    assert int(row['success'])==result['correct'][ix] and float(row['margin'])==result['margin'][ix]
                                    assert float(row['output_A'])==result['output'][ix+(0,)] and float(row['output_B'])==result['output'][ix+(1,)]
        assert next(rows,None) is None
    assert count==s['individual_observations']==len(ids)*8*4*cfg['recipients']*2*3*7
    body_count=check_bodies(run,results,ids,cfg,s,check)
    verify(run)
    result=dict(status='PASS',finished_utc=datetime.now(timezone.utc).isoformat(),blocks=len(ids),individual_observations=count,
        body_individual_observations=body_count,source_files_and_prior_audit_provenance_verified=True,
        independent_mask_only_target_and_factorial_packets_exact=True,all_generation_three_body_updates_replayed_exactly=True,
        original_generation_three_body_and_terminal_arrays_exact=True,all_receiving_updates_replayed_exactly=True,
        denominators_after_all_interventions_and_controls_verified=True,source_isolation_exact_at_every_update=True,
        all_scores_csv_rows_contrasts_intervals_and_context_gates_reproduced=True,
        source_teaching_and_renewal_scope='Teaching and g1/g2: prior audited provenance. Two g3 read/holding trajectories and all terminal updates independently replayed',
        complete_sha256=sha(run/'COMPLETE.json'),audit_code_sha256=sha(__file__),workers=workers,seconds=time.monotonic()-started)
    with (run/'INDEPENDENT_AUDIT.json').open('x') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args();assert 1<=args.workers<=12 and args.run.resolve().is_relative_to(HERE)
    print(json.dumps(audit(args.run.resolve(),args.workers),indent=2),flush=True)
