"""Independent replay and inference. No production model imports."""
import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, EXPECTED, pack, unpack, pair, ports, random, advance
from E022_reader_compensation.audit import masks_for, source_record, advance_compensated
import numpy as np

PAIRINGS = (('paired',1.,1.), ('noise_0999',1.,.999), ('noise_099',1.,.99),
    ('noise_09',1.,.9), ('noise_0',1.,0.), ('reset_099',.99,1.), ('reset_0',0.,1.))
WRITERS = ('exact_rewrite','tolerance_rewrite','ordinary_rewrite','contrast_rewrite','exact_preserve')
CONDITIONS = tuple(p[0]+'/'+w for p in PAIRINGS for w in WRITERS)
COUNTS = ('available_edges','exact_zero_available','ordinary_selected_available',
    'returning_edges','exact_zero_returning','ordinary_selected_returning',
    'nonzero_outgoing_returning','strong_outgoing_returning','zero_incoming_available',
    'new_nonzero_available','returning_cells','returning_reachable_before','returning_reachable_after')
RULES, CUES = np.array([1.,-1.,1.,-1.]), np.array([1.,-1.])


def load(path):
    with np.load(path,allow_pickle=False) as h: return {k:h[k] for k in h.files}


def equal(a,b):
    assert a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()


def equal_dict(a,b):
    assert set(a)==set(b),(set(a)-set(b),set(b)-set(a))
    for key in a:
        try: equal(a[key],b[key])
        except AssertionError as e: raise AssertionError(key) from e


def check_compact(path,raw,kind):
    saved=load(path); meta=json.loads(saved.pop('__index__').tobytes())
    keep=(('masks','birth','end','mean_ports','outgoing','noise_moments','counts','sums','write_state_hashes')
        if kind=='boundary' else ('masks','birth','end','mean_ports'))
    assert meta['kind']==kind and meta['retained']==list(keep) and set(meta['arrays'])==set(raw)
    assert set(saved)==set(keep)
    for key,value in raw.items():
        expected=dict(shape=list(value.shape),dtype=value.dtype.str,
            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())
        assert meta['arrays'][key]==expected,(str(path),key)
        if key in saved: equal(value,saved[key])


def edges(mask):
    live=~mask; out=np.empty((*mask.shape[:-2],2,16,16),bool)
    for y,x in np.ndindex(16,16):
        out[...,0,y,x]=live[...,y,x]&live[...,y,(x+1)%16]
        out[...,1,y,x]=live[...,y,x]&live[...,(y+1)%16,x]
    return out


def denominators(w):
    result=np.empty(w.shape[:-3]+(16,16)); a=abs(w)
    for y,x in np.ndindex(16,16):
        result[...,y,x]=a[...,0,y,x]+a[...,0,y,(x-1)%16]+a[...,1,y,x]+a[...,1,(y-1)%16,x]
    return result


def noise_pairs(z,e,which):
    rhos=[p[which] for p in PAIRINGS]; first=pair(z)
    out=np.empty((7,*first.shape[:2],2,16,16))
    for s,rho in enumerate(rhos):
        out[s,:,:,0]=first
        out[s,:,:,1]=first if rho==1. else pair(rho*z+np.sqrt(1.-rho*rho)*e)
    return out


def capture(v,beta):
    x=np.tanh(beta*v); shape=(35,4,v.shape[2],2,16,16)
    contrast=np.empty(shape); ordinary=np.empty(shape)
    for direction,y,xx in np.ndindex(2,16,16):
        yy,nx=(y,(xx+1)%16) if direction==0 else ((y+1)%16,xx)
        a,b=x[:,:,:,:,y,xx],x[:,:,:,:,yy,nx]
        contrast[:,:,:,direction,y,xx]=((a[:,:,:,0]-a[:,:,:,1])/2)*((b[:,:,:,0]-b[:,:,:,1])/2)
        total=np.zeros(a.shape[:-1]); total+=a[:,:,:,0]*b[:,:,:,0]
        total+=a[:,:,:,1]*b[:,:,:,1]; total/=2
        ordinary[:,:,:,direction,y,xx]=total
    used=np.zeros(shape,bool); computed=np.empty(shape)
    for n in range(35):
        policy=n%5
        if policy in (0,4): used[n]=contrast[n]==0.
        elif policy==1: used[n]=np.abs(contrast[n])<=.0001
        elif policy==2: used[n]=True
        computed[n]=contrast[n]
        computed[n][used[n]]=ordinary[n][used[n]]
    return computed,contrast,used


def reach(w):
    result=np.zeros(w.shape[:-3]+(16,16),bool); start=list(zip(*np.where(ports()[0])))
    for index in np.ndindex(w.shape[:-3]):
        h,v=w[index]; seen=result[index]; queue=deque(start)
        for y,x in start: seen[y,x]=True
        while queue:
            y,x=queue.popleft()
            for yy,xx,edge in ((y,(x+1)%16,h[y,x]),(y,(x-1)%16,h[y,(x-1)%16]),
                ((y+1)%16,x,v[y,x]),((y-1)%16,x,v[(y-1)%16,x])):
                if edge!=0 and not seen[yy,xx]: seen[yy,xx]=True; queue.append((yy,xx))
    return result


def mechanism(old,new,available,mask,previous,contrast,used):
    returning=previous&~mask
    rr=np.zeros(available.shape,bool)
    for y,x in np.ndindex(16,16):
        rr[...,0,y,x]=available[...,0,y,x]&(returning[...,y,x]|returning[...,y,(x+1)%16])
        rr[...,1,y,x]=available[...,1,y,x]&(returning[...,y,x]|returning[...,(y+1)%16,x])
    av=np.broadcast_to(available,new.shape); rr=np.broadcast_to(rr,new.shape)
    cells=np.broadcast_to(returning,new.shape[:-3]+(16,16))
    fields=(av,av&(contrast==0),av&used,rr,rr&(contrast==0),rr&used,rr&(new!=0),
        rr&(np.abs(new)>.5),av&(old==0),av&(old==0)&(new!=0))
    count=[field.sum(axis=(-3,-2,-1),dtype=np.int64) for field in fields]
    count += [cells.sum(axis=(-2,-1),dtype=np.int64),
        (cells&reach(old)).sum(axis=(-2,-1),dtype=np.int64),
        (cells&reach(new)).sum(axis=(-2,-1),dtype=np.int64)]
    sums=np.stack((np.where(rr,np.abs(new),0.).sum(axis=(-3,-2,-1)),
        np.where(rr,np.abs(contrast),0.).sum(axis=(-3,-2,-1))),axis=-1)
    return np.stack(count,axis=-1),sums


def replay(incoming,block,g,previous,cfg,cycle):
    R=cfg['recipients']; p=ports(); mask=masks_for(block,g,R,renewal=True)[:,:,1]
    assert np.all(mask.sum(axis=(-2,-1))==24) and not (mask&p.any(axis=0)).any()
    physical=edges(mask); old=unpack(incoming)*physical; denominator=denominators(old)
    stream=random('E022',block,'develop',g); independent=random('E051',block,'innovation',g)
    shape=(2,R,16,16)
    birth=cfg['birth_sd']*noise_pairs(stream.standard_normal(shape),independent.standard_normal(shape),1)
    v=np.empty((35,4,R,2,16,16))
    for n in range(35): v[n]=birth[n//5]
    live=(~mask)[None,:,:,None]; cue=CUES.reshape(1,1,1,2,1)
    v*=live; v[...,p[0]]=cue; trace=[]; moments=np.zeros((7,6))
    for t in range(cycle['read_steps']):
        noise=noise_pairs(stream.standard_normal(shape),independent.standard_normal(shape),2)
        a,b=noise[:,:,:,0],noise[:,:,:,1]
        for k,term in enumerate((a,b,a*a,b*b,a*b)): moments[:,k]+=term.sum(axis=(1,2,3,4))
        moments[:,5]+=a[0].size
        v=advance_compensated(v,old[:,:,:,None],denominator[:,:,:,None],noise.repeat(5,axis=0),cfg,t>=cycle['settling_steps'])
        v*=live; v[...,p[0]]=cue
        if t>=cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
    end=v.copy(); trace=np.array(trace); computed,contrast,used=capture(end,cfg['writer_beta'])
    retained=np.zeros(computed.shape,bool); new=np.zeros_like(computed)
    for n in range(35):
        if n%5==4: retained[n]=physical&(np.abs(old[n])>.5)
        writable=physical&~retained[n]
        new[n][retained[n]]=old[n][retained[n]]; new[n][writable]=computed[n][writable]
    counts,sums=mechanism(old,new,physical,mask,previous,contrast,used)
    stream=random('E022',block,'write',g); scaffold=physical[None,:,:,None].astype(float)
    hashes=np.empty((cycle['write_steps'],35,32),np.uint8)
    for t in range(cycle['write_steps']):
        noise=pair(stream.standard_normal(shape))[None,:,:,None]
        v=advance(v,scaffold,2.,noise,cfg); v*=live; v[...,p[0]]=cue
        for n in range(35): hashes[t,n]=np.frombuffer(hashlib.sha256(v[n].astype('<f8').tobytes(order='C')).digest(),np.uint8)
    return dict(incoming=incoming.copy(),masks=mask,effective_packets=pack(old),denominator=denominator,
        birth=birth,end=end,late_ports=trace,mean_ports=trace.mean(axis=0),computed_packets=pack(computed),
        outgoing=pack(new),retained=retained,noise_moments=moments,counts=counts,sums=sums,
        write_end=v,write_state_hashes=hashes)


def assay(incoming,block,h,cfg,cycle):
    packets=np.concatenate((incoming,np.zeros_like(incoming[:1])),axis=0)
    R=cfg['recipients']; p=ports(); mask=masks_for(block,h,R)
    effective=unpack(packets)[:,:,:,None]*edges(mask)[None]; denominator=denominators(effective)
    stream=random('E022',block,'assay',h); birth=cfg['birth_sd']*pair(stream.standard_normal((2,R,3,16,16)))
    v=np.empty((len(packets),4,R,2,3,16,16))
    for n,c in np.ndindex(len(packets),2): v[n,:,:,c]=birth
    live=(~mask)[None,:,:,None]; cue=CUES.reshape(1,1,1,2,1,1)
    v*=live; v[...,p[0]]=cue; trace=[]
    for t in range(cycle['read_steps']):
        noise=pair(stream.standard_normal((2,R,3,16,16)))[None,:,:,None]
        v=advance_compensated(v,effective[:,:,:,None],denominator[:,:,:,None],noise,cfg,t>=cycle['settling_steps'])
        v*=live; v[...,p[0]]=cue
        if t>=cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
    trace=np.array(trace)
    return dict(records=packets,masks=mask,effective_packets=pack(effective),denominator=denominator,
        birth=birth,end=v,late_ports=trace,mean_ports=trace.mean(axis=0))


def score(values,cfg):
    target=RULES.reshape(1,4,1,1,*((1,)*(values.ndim-5)))*CUES.reshape(1,1,1,2,*((1,)*(values.ndim-5)))
    one=target*values[...,0]; two=-target*values[...,1]
    return dict(correct=(one>cfg['margin'])&(two>cfg['margin']),margin=np.minimum(one,two),ports=values)


def inspect(task):
    output,block,cfg,cycle,mode=task; started=time.monotonic(); cap_cpus(8)
    source=load(output/f'source_{block:06d}.npz'); acquired,_=source_record(source,block,cfg)
    spec=json.loads((HERE/'SOURCE_DATA.json').read_text())
    reference=ROOT/spec['reference'][mode] if mode!='scientific' else None
    if reference is not None:
        old=load(reference/f'source_{block:06d}.npz'); meta=json.loads(old.pop('__index__').tobytes())
        equal_dict({k:v for k,v in source.items() if k!='capture_states'},old)
        assert hashlib.sha256(source['capture_states'].tobytes()).hexdigest()==meta['arrays']['capture_states']['sha256']
        old_cases=load(reference/f'cases_{block:06d}.npz')
        panels=json.loads((reference/'summary.json').read_text())['panels']
    initial=acquired[:,None].repeat(cfg['recipients'],axis=1)
    packets=initial[None].repeat(35,axis=0); previous=np.zeros((4,cfg['recipients'],16,16),bool)
    cases={}; body={k:[] for k in ('correct','margin','ports')}; counts=[]; sums=[]; moments=[]
    def check_assay(h,records):
        raw=assay(records,block,h,cfg,cycle); check_compact(output/f'assay_{block:06d}_h{h}.npz',raw,'assay')
        scores=score(raw['mean_ports'],cfg)
        for key,value in scores.items(): cases[f'assay_h{h}_{key}']=value
        if reference is not None:
            mapping=((0,'initial'),) if h==0 else ((0,'bridge_rewrite'),(2,'standard_rewrite'),(4,'bridge_preserve'))
            for n,name in mapping:
                i=panels.index([h,name,'local_strength'])
                for key,value in scores.items(): equal(value[n],old_cases[key][i][...,0,:] if key=='ports' else old_cases[key][i][...,0])
            i=panels.index([h,'initial' if h==0 else 'bridge_rewrite','local_strength'])
            for key,value in scores.items(): equal(value[-1],old_cases[key][i][...,3,:] if key=='ports' else old_cases[key][i][...,3])
    check_assay(0,initial[None])
    for g in range(1,33):
        raw=replay(packets,block,g,previous,cfg,cycle); check_compact(output/f'boundary_{block:06d}_g{g}.npz',raw,'boundary')
        scores=score(raw['mean_ports'],cfg)
        if reference is not None:
            old=load(reference/f'boundary_{block:06d}_g{g}.npz'); equal(raw['masks'],old['renewal_mask'])
            for n,old_n in ((0,3),(2,1),(4,2)):
                equal(raw['outgoing'][n],old['outgoing'][old_n])
                for key,value in scores.items(): equal(value[n],old_cases['body_'+key][g-1,old_n])
        packets=raw['outgoing'].copy(); previous=raw['masks'].copy()
        for key,value in scores.items(): body[key].append(value)
        counts.append(raw['counts']); sums.append(raw['sums']); moments.append(raw['noise_moments'])
        if g in (8,16,24,32): check_assay(g,packets)
    cases.update({'body_'+k:np.array(v) for k,v in body.items()})
    cases.update(counts=np.array(counts),sums=np.array(sums),noise_moments=np.array(moments))
    equal_dict(cases,load(output/f'cases_{block:06d}.npz'))
    receipt=json.loads((output/f'worker_{block}.json').read_text())
    assert receipt['block']==block and receipt['generations']==32 and receipt['conditions']==35
    assert receipt['source_sha256']==sha(output/f'source_{block:06d}.npz')
    assert receipt['legacy_three_policies_all_boundaries_and_assays_match']==(mode!='scientific')
    return dict(cases=cases,seconds=time.monotonic()-started)


def expected_values(data):
    values={}
    for h in (0,8,16,24,32):
        names=('initial','erased') if h==0 else (*CONDITIONS,'erased')
        for n,name in enumerate(names):
            for j,injury in enumerate(('intact','scattered','square')):
                values[f'assay/{h}/{name}/{injury}']=np.array([d[f'assay_h{h}_correct'][n,:,:,:,j].all(axis=2).mean() for d in data])
    for g in range(32):
        for n,name in enumerate(CONDITIONS):
            values[f'body/{g+1}/{name}']=np.array([d['body_correct'][g,n].all(axis=2).mean() for d in data])
    for p,_,_ in PAIRINGS:
        for w in WRITERS:
            x=values[f'assay/32/{p}/{w}/scattered']
            if p!='paired': values[f'pairing_effect/{p}/{w}']=x-values[f'assay/32/paired/{w}/scattered']
            if w!='exact_rewrite': values[f'writer_effect/{p}/{w}']=x-values[f'assay/32/{p}/exact_rewrite/scattered']
    count=np.array([d['counts'][1:].sum(axis=(0,2,3)) for d in data])
    sums=np.array([d['sums'][1:].sum(axis=(0,2,3)) for d in data])
    fields=(('exact_zero_returning',4,3),('ordinary_selected_returning',5,3),('nonzero_returning',6,3),
        ('strong_returning',7,3),('new_nonzero_available',9,8),('returning_reachable_before',11,10),
        ('returning_reachable_after',12,10),('ordinary_selected_available',2,0))
    for n,name in enumerate(CONDITIONS):
        for key,a,b in fields:
            assert (count[:,n,b]>0).all(); values[f'mechanism/{name}/{key}']=count[:,n,a]/count[:,n,b]
        for j,key in enumerate(('mean_abs_returning_weight','mean_abs_returning_contrast')):
            values[f'mechanism/{name}/{key}']=sums[:,n,j]/count[:,n,3]
    return values


def audit(output,workers):
    started=time.monotonic(); cap_cpus(8); m=verify(output); c=m['contract']
    summary=json.loads((output/'summary.json').read_text()); mode=c['mode']; ids=c['blocks']; cfg=c['config']; cycle=c['cycle']
    spec=json.loads((HERE/'SOURCE_DATA.json').read_text()); previous=set()
    for rel,digest in {**spec['sha256'],**spec['prior_manifest_sha256']}.items(): assert sha(ROOT/rel)==digest,rel
    for rel in spec['prior_manifest_sha256']: previous.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(previous)==spec['prior_block_ids'] and not previous.intersection(spec['blocks'])
    assert spec['blocks']==list(range(34000,34032)) and ids==(spec['blocks'] if mode=='scientific' else [900041])
    expected_cfg=dict(EXPECTED); expected_cycle=dict(read_steps=2048,settling_steps=1024,write_steps=128,generations=32)
    if mode=='fixture':
        expected_cfg.update(recipients=2,teach_steps=12,capture_steps=6,observe_steps=4)
        expected_cycle.update(read_steps=24,settling_steps=12,write_steps=8)
    elif mode=='benchmark': expected_cfg['recipients']=1; expected_cycle.update(read_steps=128,settling_steps=64)
    else: assert mode=='scientific'
    assert cfg==expected_cfg and cycle==expected_cycle
    assert summary['cfg']==cfg and summary['cycle']==cycle and summary['mode']==mode and summary['blocks']==ids
    assert c['experiment']==summary['experiment']=='E051'
    assert c['pairings']==summary['pairings']==[list(p) for p in PAIRINGS]
    assert c['writers']==summary['writers']==list(WRITERS) and c['conditions']==summary['conditions']==list(CONDITIONS)
    assert c['tolerance']==summary['tolerance']==1e-4 and summary['counts']==list(COUNTS)
    assert summary['sums']==['absolute_outgoing_returning','absolute_contrast_returning']
    assert summary['assay_horizons']==[0,8,16,24,32] and c['generations']==32
    assert not c['prior_cases_pooled'] and not summary['prior_cases_pooled']
    assert summary['fresh_scientific_histories']==(mode=='scientific')
    for flag in ('original_E041_full_qualification_tested','independent_teaching_or_assay_noise_tested',
        'combined_noise_reset_perturbation_tested','tolerance_selected_from_outcomes'): assert summary[flag] is False
    assert summary['primary_perturbations']==['noise_0999','reset_099'] and summary['allowable_loss']==.05 and summary['absolute_floor']==.75
    assert summary['legacy_reference_match']==(True if mode!='scientific' else None)
    if mode!='scientific': verify(ROOT/spec['reference'][mode])
    with ProcessPoolExecutor(max_workers=min(workers,len(ids))) as pool:
        results=list(pool.map(inspect,[(output,b,cfg,cycle,mode) for b in ids]))
    data=[r['cases'] for r in results]; values=expected_values(data); stats=summary['statistics']
    assert set(values)==set(stats)
    draw=random('E051','bootstrap','cue_pairing_robustness').integers(0,len(ids),(10000,len(ids)))
    for key,x in values.items():
        s=stats[key]; assert s['block_means']==x.tolist() and s['mean']==float(x.mean()),key
        assert s['ci95']==np.quantile(x[draw].mean(axis=1),[.025,.975]).tolist(),key
    gates={'paired_baseline_lower_above_075':stats['assay/32/paired/exact_rewrite/scattered']['ci95'][0]>.75}
    labels={}
    for condition in ('noise_0999','reset_099'):
        low,high=stats[f'pairing_effect/{condition}/exact_rewrite']['ci95']
        absolute=stats[f'assay/32/{condition}/exact_rewrite/scattered']['ci95'][0]>.75
        gates[condition+'_lower_above_075']=absolute
        gates[condition+'_difference_lower_above_minus_005']=low>-.05
        label='ROBUST_WITHIN_FIVE_POINTS' if gates['paired_baseline_lower_above_075'] and absolute and low>-.05 else 'LOSS_EXCEEDS_FIVE_POINTS' if high<-.05 else 'UNRESOLVED'
        labels[condition]=None if mode!='scientific' else label
    expected_status='TECHNICAL_ONLY' if mode!='scientific' else 'PAIRING_ROBUSTNESS_ESTABLISHED' if all(gates.values()) else 'PAIRING_ROBUSTNESS_NOT_ESTABLISHED'
    assert summary['status']==expected_status and summary['primary_classifications']==labels
    assert summary['primary_decision']==(None if mode!='scientific' else all(gates.values()))
    assert summary['primary_gates']=={k:None if mode!='scientific' else v for k,v in gates.items()}
    body=sum(d['body_correct'].size for d in data)
    terminal=sum(d[f'assay_h{h}_correct'].size for d in data for h in (0,8,16,24,32))
    assert body==summary['body_cue_observations'] and terminal==summary['terminal_cue_observations']
    assert summary['lineages_per_condition']==len(ids)*4*cfg['recipients']
    result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-started,worker_seconds=[r['seconds'] for r in results],
        complete_sha256=sha(output/'COMPLETE.json'),audit_code_sha256=sha(__file__),summaries_checked=len(stats),
        blocks=len(ids),body_cue_observations=body,terminal_cue_observations=terminal,
        all_teaching_rebuilding_holding_and_assays_replayed=True,all_mechanism_counts_and_connectivity_replayed=True,
        legacy_three_policies_all_boundaries_and_assays_match=mode!='scientific',scientific_decision=summary['primary_decision'])
    destination=output/'INDEPENDENT_AUDIT.json'; assert not destination.exists(); dump(destination,result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('run',type=Path); p.add_argument('--workers',type=int,default=8)
    args=p.parse_args(); assert 1<=args.workers<=8; audit(args.run.resolve(),args.workers)
