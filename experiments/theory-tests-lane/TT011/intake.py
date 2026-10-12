"""Reconstruct P05 donors, packets, masks and all linear diagnostics."""
from datetime import datetime
from pathlib import Path
import numpy as np
import arithmetic as a
import native as n
import support as s

VARIANTS=['incoming','outgoing','full_own','common_own','same_task','opposite_task','scrambled','erased','donor_same_full','donor_opposite_full']


def construct(old,donors,block,cfg):
    weights=n.decode(old['packets'][:,:2]);dw=n.decode(donors);live=n.available(old['original_masks'])
    incoming,outgoing=weights[:,0],weights[:,1];e=(~live)&(incoming!=0);k=e&(dw[:,0]!=0)&(dw[:,1]!=0)
    s.require(not outgoing[~live].any(),'No outgoing edge crosses original injury')
    full=incoming.copy();full[live]=outgoing[live]
    own=outgoing.copy();same=outgoing.copy();opposite=outgoing.copy();shuffled=outgoing.copy()
    own[k]=incoming[k];same[k]=abs(incoming[k])*np.where(dw[:,0][k]>0,1.,-1.);opposite[k]=abs(incoming[k])*np.where(dw[:,1][k]>0,1.,-1.)
    changes=[]
    for i in range(len(incoming)):
        indices=np.flatnonzero(k[i]);signs=np.where(incoming[i].ravel()[indices]>0,1.,-1.)
        rng=n.random_stream(cfg['random_namespace'],block,'backup_signs',int(old['histories'][i]),int(old['founders'][i]),int(old['recipients'][i]))
        # Permute indices then apply signs; identity permutations are retained.
        permuted=signs[rng.permutation(len(indices))]
        shuffled[i].ravel()[indices]=abs(incoming[i].ravel()[indices])*permuted;changes.append(int((signs!=permuted).sum()))
    count=lambda x:x.sum(axis=(-2,-1))
    mass=(abs(incoming)*k).sum(axis=(-2,-1));total=(abs(incoming)*e).sum(axis=(-2,-1))
    values=np.stack([incoming,outgoing,full,own,same,opposite,shuffled,np.zeros_like(incoming),dw[:,0],dw[:,1]],axis=1)
    return dict(packets=n.encode(values),donor_packets=donors.copy(),
        donor_founders=np.array([[2*(1-int(f)//2)+int(f)%2,2*(1-int(f)//2)+1-int(f)%2] for f in old['founders']],dtype=np.int64),
        backup_edges=e.reshape(-1,2,16,16),common_edges=k.reshape(-1,2,16,16),
        backup_nonzero_count=count(e),common_nonzero_count=count(k),
        common_magnitude_fraction=np.divide(mass,total,out=np.zeros_like(mass),where=total>0),
        donor_sign_differences=count(k&((dw[:,0]>0)!=(dw[:,1]>0))),scramble_sign_changes=np.array(changes),
        same_sign_changes=count(k&((incoming>0)!=(dw[:,0]>0))),opposite_sign_changes=count(k&((incoming>0)!=(dw[:,1]>0))))


def diagnostics(packets,masks,founders):
    w=n.decode(packets)[:,:,None]*n.available(masks)[:,None]
    h,v=w[...,0,:],w[...,1,:];rows=np.stack([h,h[...,n.LEFT],v,v[...,n.UP]])
    denominator=np.sum(abs(rows),axis=0);rows=np.divide(rows,denominator,out=np.zeros_like(rows),where=denominator>0)
    results=[]
    for operator in [rows,abs(rows)]:
        x=np.zeros_like(h);x[...,n.PORTS[0]]=1.
        for _ in range(64):
            x=operator[0]*x[...,n.RIGHT]+operator[1]*x[...,n.LEFT]+operator[2]*x[...,n.DOWN]+operator[3]*x[...,n.UP]
            x[...,n.PORTS[0]]=1.
        results.append([x[...,port].mean(axis=-1) for port in n.PORTS[1:]])
    rule=np.where(founders%2==0,1.,-1.)[:,None,None];first,second=results[0]
    return dict(signed_transfer=np.minimum(rule*first,-rule*second),
                opposite_signed_transfer=np.minimum(-rule*first,rule*second),unsigned_access=np.minimum(*results[1]))


def run(output,blocks=None,progress=None):
    receipt=s.verify_sources();cfg=s.config('p05');base=s.HERE/'source/p05'
    s.require(cfg['blocks']==list(range(34000,34008)) and cfg['cases_per_block']==[7,11,9,4,4,4,16,9],'Unchanged cohort')
    s.require(cfg['variants']==VARIANTS and cfg['regimes']==['original','fresh'],'Record and regime ordering')
    s.require(cfg['replicates']==list(range(16)) and cfg['original_replicates']==[0] and cfg['budgets']==[2048],'Read scope')
    s.require(cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25) and cfg['settling_steps']==1024 and cfg['transfer_steps']==64 and cfg['injury_cells']==24,'Native settings')
    s.require(cfg['random_namespace']=='P05_backup_task_swap_v0_1' and cfg['bootstrap_seed']==2026101003 and cfg['bootstrap_replicates']==20000,'Stream contract')
    prepared_receipt=s.read(base/'inputs/prepared/COMPLETE.json');old_root=Path(prepared_receipt['recipient_source_run'])
    enrollment=s.table(base/'inputs/prepared/enrollment.csv')
    s.require(enrollment==s.table(s.origin(old_root/'inputs/prepared/enrollment.csv')) and len(enrollment)==64,'Exact prior enrollment')
    s.require(all(int(row['current_pass'])==0 for row in enrollment),'All originally selected failures')
    blocks=cfg['blocks'] if blocks is None else blocks;data={};matching=[];contexts=0;retained=0;ordered_error=0.;csr_error=0.;cache={}
    for block in blocks:
        if progress:progress('construction_and_diagnostics',block=block)
        d=s.prepared('p05',block);raw=s.observed('p05',block);old=s.arrays(s.origin(old_root/f'inputs/prepared/cases_{block:06d}.npz'))
        count=cfg['cases_per_block'][cfg['blocks'].index(block)];s.require(len(d['founders'])==count and int(d['block'])==block,'Block size')
        for key in ['block','histories','founders','recipients','original_masks','original_birth','original_end','original_mean_ports']:
            s.equal(d[key],old[key],'Audited P04 antecedent '+key)
        s.equal(d['packets'][:,:2],old['packets'][:,:2],'Audited input records');s.equal(d['packets'][:,2],old['packets'][:,3],'Audited full hybrid')
        s.equal(n.recapture(d['original_end'],d['original_masks']),d['packets'][:,1],'Independent outgoing recapture')
        source_panels={}
        for label,path in prepared_receipt['donor_source_runs'].items():
            with np.load(s.origin(Path(path)/f'boundary_{block:06d}_g13.npz'),allow_pickle=False) as z:source_panels[label]=z['outgoing']
        donors=[]
        for i,(h,f,r) in enumerate(zip(d['histories'],d['founders'],d['recipients'],strict=True)):
            label,j={0:('spacing',0),1:('pulse',2),2:('spacing',1),3:('spacing',2)}[int(h)]
            panel=source_panels[label][j];s.equal(panel[f,r],d['packets'][i,0],'Own generation thirteen record')
            pair=2*(1-int(f)//2);donors.append(np.stack([panel[pair+int(f)%2,r],panel[pair+1-int(f)%2,r]]))
            row=[v for v in enrollment if int(v['block'])==block and int(v['local_case'])==i]
            s.require(len(row)==1 and row[0]['history']==cfg['histories'][h] and int(row[0]['founder'])==f and int(row[0]['recipient'])==r,'Ordered enrollment identity')
        made=construct(old,np.stack(donors),block,cfg)
        for key,value in made.items():
            if key=='common_magnitude_fraction':s.close(value,d[key],1e-12,'Magnitude fraction')
            else:s.equal(value,d[key],'Record reconstruction '+key)
        s.equal(n.fresh_masks(cfg,block,d['founders'],d['recipients'],cfg['replicates']),d['masks'],'Every fresh mask')
        s.require((d['original_masks'].sum(axis=(-2,-1))==24).all() and not d['original_masks'].reshape(count,256)[:,np.concatenate(n.PORTS)].any(),'Original injury contract')
        s.equal(d['replicates'],np.arange(16),'Replicate labels');s.equal(d['original_replicates'],np.array([0]),'Control label')
        for key,value in d.items():s.equal(value,raw[key],'Retained prepared field '+key);retained+=1
        for prefix,masks in [('control_',d['original_masks'][:,None]),('',d['masks'])]:
            computed=diagnostics(d['packets'],masks,d['founders'])
            for key,value in computed.items():ordered_error=max(ordered_error,s.close(value,d[prefix+key],2e-14,'Ordered '+prefix+key))
            s.equal(np.sign(computed['signed_transfer'][:,4]-computed['signed_transfer'][:,5]),
                    np.sign(d[prefix+'signed_transfer'][:,4]-d[prefix+'signed_transfer'][:,5]),'Exact rival decisions and ties')
            for v in [4,5,6]:s.equal(computed['unsigned_access'][:,3],computed['unsigned_access'][:,v],'Matched unsigned diagnostic')
            for i,vi,ri in np.ndindex(computed['signed_transfer'].shape):
                packet=d['packets'][i,vi];mask=masks[i,ri];key=(packet.tobytes(),mask.tobytes());rule=1 if d['founders'][i]%2==0 else -1
                if key not in cache:cache[key]=(n.diagnostic_csr(packet,mask,1),n.diagnostic_csr(packet,mask,-1))
                intended,opposite=cache[key] if rule==1 else cache[key][::-1]
                for field,value in [('signed_transfer',intended[0]),('opposite_signed_transfer',opposite[0]),('unsigned_access',intended[1])]:
                    csr_error=max(csr_error,abs(value-float(computed[field][i,vi,ri])))
                contexts+=1
            # Downstream summaries use independently regenerated diagnostic values.
            for key,value in computed.items():raw[prefix+key]=value
        s.require(csr_error<=2e-14,'CSR diagnostic cross-check')
        for i in range(count):
            matching.append(dict(block=block,local_case=i,history=cfg['histories'][int(d['histories'][i])],founder=int(d['founders'][i]),recipient=int(d['recipients'][i]),
                                 same_donor_founder=int(d['donor_founders'][i,0]),opposite_donor_founder=int(d['donor_founders'][i,1]),
                                 **{k:int(made[k][i]) for k in ['backup_nonzero_count','common_nonzero_count','donor_sign_differences','scramble_sign_changes','same_sign_changes','opposite_sign_changes']},
                                 common_magnitude_fraction=float(made['common_magnitude_fraction'][i])))
        worker=s.read(base/f'run/worker_{block:06d}.json')
        s.require(worker['status']=='COMPLETE' and worker['block']==block and worker['cases']==count and worker['input_sha256']==s.sha(base/f'inputs/prepared/cases_{block:06d}.npz') and worker['output_sha256']==s.sha(base/f'run/reads_{block:06d}.npz'),'Worker coverage and identities')
        data[block]=raw
    if blocks==cfg['blocks']:
        a.compare_table(matching,base/'inputs/prepared/donor_matching.csv',['block','local_case'])
        match=dict(cases=len(matching),backup_edges=sum(r['backup_nonzero_count'] for r in matching),common_edges=sum(r['common_nonzero_count'] for r in matching),
          donor_sign_differences=sum(r['donor_sign_differences'] for r in matching),identical_donor_cases=sum(r['donor_sign_differences']==0 for r in matching),
          zero_common_cases=sum(r['common_nonzero_count']==0 for r in matching),common_edges_min=min(r['common_nonzero_count'] for r in matching),common_edges_max=max(r['common_nonzero_count'] for r in matching),
          mean_common_edge_fraction=a.average(r['common_nonzero_count']/r['backup_nonzero_count'] for r in matching),mean_common_magnitude_fraction=a.average(r['common_magnitude_fraction'] for r in matching))
        a.compare_tree(match,s.read(base/'inputs/prepared/MATCHING.json'),'Donor matching summary')
    start=s.read(base/'run/START.json');manifest=s.read(base/'run/manifest.json')
    s.require(start['manifest_sha256']==s.sha(base/'run/manifest.json'),'Launch manifest')
    chronology=[s.read(base/name)['at_utc'] for name in ['inputs/prepared/COMPLETE.json','run/manifest.json','run/START.json','run/WORKER_STARTED.json','run/COMPLETE.json']]
    s.require([datetime.fromisoformat(t) for t in chronology]==sorted(datetime.fromisoformat(t) for t in chronology),'Recorded local chronology')
    result=dict(status='PASS',source_files=len(receipt['files_sha256']),blocks=blocks,cases=len(matching),donor_slots=2*len(matching),prepared_fields_checked=retained,
                diagnostic_contexts=contexts,unique_diagnostic_contexts=len(cache),maximum_ordered_error=ordered_error,maximum_csr_error=csr_error,
                chronology=chronology,full_native_replay_performed=False,new_task_outcomes=False)
    s.dump(output/'INTAKE_AUDIT.json',result);return data,result
