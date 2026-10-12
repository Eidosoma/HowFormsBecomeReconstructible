"""Independent packet reconstruction, unchanged receiver replay and inference audit."""
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
from E015_functional_inheritance.audit import pack, unpack, random, read_json, sha, verify, EXPECTED
from E022_reader_compensation.audit import load_arrays, equal
from E023_receiver_compensation.audit import replay_assay
import numpy as np
CONDITIONS=('copy','copy_plus_restored','rebuilt_without_restored','rebuilt')
RECEIVERS=('fixed_four','local_strength')
PANELS=tuple((c,r) for r in RECEIVERS for c in CONDITIONS)
ARMS=('own','foreign','shuffled','erased','untrained','communication_off','source_cut')
DAMAGE=('intact','scattered','square')
RULES=(1,-1,1,-1);CUES=(1,-1)


def inspect_block(task):
    run,block,label,cfg,cycle=task
    spec=read_json(HERE/'SOURCE_DATA.json')[label];source=ROOT/spec['path']
    for name,digest in spec['provenance_sha256'].items():assert sha(source/name)==digest
    for name,digest in spec['files'][str(block)].items():assert sha(source/name)==digest
    receipt=read_json(source/'INDEPENDENT_AUDIT.json')
    assert receipt['status']=='PASS' and receipt['complete_sha256']==sha(source/'COMPLETE.json')
    masks=[];copies=[];rebuilt=None;original=None
    for g in (1,2,3):
        with np.load(source/f'boundary_{block:06d}_g{g}.npz',allow_pickle=False) as saved:
            masks.append(saved['renewal_mask']);outgoing=saved['outgoing']
        if original is None:original=outgoing[4].copy()
        equal(original,outgoing[4]);copies.append(unpack(outgoing[5]))
        if g==3:rebuilt=outgoing[2].copy();copied=outgoing[5].copy()
    masks=np.stack(masks);R=cfg['recipients']
    assert masks.dtype==bool and masks.shape==(3,4,R,16,16)
    available=np.zeros((3,4,R,2,16,16),bool)
    for y in range(16):
        for x in range(16):
            available[:,:,:,0,y,x]=~(masks[:,:,:,y,x]|masks[:,:,:,y,(x+1)%16])
            available[:,:,:,1,y,x]=~(masks[:,:,:,y,x]|masks[:,:,:,(y+1)%16,x])
    for g in range(3):equal(copies[g],unpack(original)*available[:g+1].all(axis=0))
    common=available.all(axis=0);current=available[2];restored=current & ~common
    M,Rw=unpack(copied),unpack(rebuilt)
    assert not M[~common].any() and not Rw[~current].any()
    expected=np.stack((M,M,Rw,Rw))
    for f,r,d,y,x in np.argwhere(restored):
        expected[1,f,r,d,y,x]=Rw[f,r,d,y,x]
        expected[2,f,r,d,y,x]=0.
    packets=pack(expected)
    intervention=load_arrays(run/f'intervention_{block:06d}.npz')
    for key,value in dict(records=packets,renewal_masks=masks,current=current,common=common,
        restored=restored,copy_packet=copied,rebuilt_packet=rebuilt).items():equal(value,intervention[key])
    meta=read_json(run/f'worker_{block}.json')
    assert meta['block']==block and meta['source']==label and meta['source_files_sha256']==spec['files'][str(block)]
    assert meta['original_endpoint_packets_and_all_terminal_arrays_exact']
    raw=load_arrays(run/f'assay_{block:06d}.npz')
    with np.load(source/f'assay_{block:06d}_h3.npz',allow_pickle=False) as old:
        for key in ('permutations','masks','birth'):equal(raw[key],old[key])
        equal(raw['packets'][[0,3]],old['packets'][[5,2]])
        for key in ('receiver_denominators','end','late_mean'):equal(raw[key][[0,3,4,7]],old[key][[5,2,13,10]])
        equal(raw['late_ports'][:,[0,3,4,7]],old['late_ports'][:,[5,2,13,10]])
    c,m,v=replay_assay(raw,packets,block,3,cfg,cycle)
    return dict(correct=c,margin=m,output=v,accuracy=c.mean(axis=(1,2,3)),
        both_cues=c.all(axis=3).mean(axis=(1,2)),mean_margin=m.mean(axis=(1,2,3)),
        rules=np.stack([c[:,[r,r+2]][...,0].mean(axis=(1,2,3)) for r in range(2)],axis=1))


def audit(run,workers=8):
    started=time.monotonic()
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    manifest=verify(run);contract=manifest['contract'];label=contract['source']
    spec=read_json(HERE/'SOURCE_DATA.json')[label]
    cfg,cycle,ids=contract['config'],contract['cycle'],contract['blocks']
    assert cfg==spec['config'] and cycle==spec['cycle'] and ids==spec['blocks']
    assert ids==({'cohort':list(range(23000,23032)),'benchmark':[900024],'fixture':[900025]}[label])
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
    draws=random('E026','bootstrap','restoration').integers(0,len(ids),(10000,len(ids)))
    def check(x,st):
        equal(x,st['block_means']);assert float(x.mean())==st['mean']
        equal(np.quantile(x[draws].mean(axis=1),[.025,.975]),st['ci95'])
    s=read_json(run/'summary.json');technical=label!='cohort'
    for key,value in dict(experiment='E026',source=label,blocks=ids,cfg=cfg,cycle=cycle,
        conditions=list(CONDITIONS),receivers=list(RECEIVERS),panels=[list(x) for x in PANELS],arms=list(ARMS),damage=list(DAMAGE),
        founders=4*len(ids),lineages=4*cfg['recipients']*len(ids),original_endpoint_replay_exact=True,
        new_teaching_or_renewal=False,new_independent_cohort=False,
        status='TECHNICAL_ONLY' if technical else 'RESTORATION_DIAGNOSTIC_COMPLETE',
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
                values=dict(total_gap=p[3]-p[0],restoration_with_copied_survivors=p[1]-p[0],
                    restoration_with_rebuilt_survivors=p[3]-p[2],rewritten_survivors_without_restoration=p[2]-p[0],
                    rewritten_survivors_with_restoration=p[3]-p[1],interaction=(p[3]-p[2])-(p[1]-p[0]))
                assert set(s['contrasts'][receiver])==set(values)
                for name,value in values.items():check(value,s['contrasts'][receiver][name][metric][damage])
    assert set(s['focal'])=={'restoration_with_rebuilt_survivors','restoration_with_copied_survivors'}
    for name,item in s['focal'].items():
        st=s['contrasts']['local_strength'][name]['both_cues']['scattered']
        assert item['statistics']==st
        assert item['lower_bound_above_zero']==(None if technical else st['ci95'][0]>0)
        assert item['lower_bound_above_010']==(None if technical else st['ci95'][0]>.10)
    if label=='cohort':
        old=read_json(ROOT/spec['path']/'summary.json')
        for receiver in RECEIVERS:
            for new,previous in (('copy','masked_copy'),('rebuilt','strength_compensated')):
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
    verify(run)
    result=dict(status='PASS',finished_utc=datetime.now(timezone.utc).isoformat(),blocks=len(ids),individual_observations=count,
        source_files_and_prior_audit_provenance_verified=True,independent_mask_partition_and_hybrids_exact=True,
        original_endpoint_packets_and_all_terminal_arrays_exact=True,all_receiving_updates_replayed_exactly=True,
        denominators_after_all_interventions_and_controls_verified=True,source_isolation_exact_at_every_update=True,
        all_scores_csv_rows_contrasts_intervals_and_context_gates_reproduced=True,
        source_teaching_and_renewal_scope='Prior audited provenance; no new teaching or renewal replay',
        complete_sha256=sha(run/'COMPLETE.json'),audit_code_sha256=sha(__file__),workers=workers,seconds=time.monotonic()-started)
    with (run/'INDEPENDENT_AUDIT.json').open('x') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args();assert 1<=args.workers<=12 and args.run.resolve().is_relative_to(HERE)
    print(json.dumps(audit(args.run.resolve(),args.workers),indent=2),flush=True)
