"""Bind saved donor pairs and construct support-matched swaps before native reads."""
import csv
import numpy as np
from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,validate,write
from reader import PORTS,available,decode,stream
import diagnostics_core as core


def new_masks(cfg,block,founders,recipients,replicates):
    eligible=np.flatnonzero(~PORTS.any(axis=0).ravel())
    masks=np.zeros((len(founders),len(replicates),16,16),bool)
    for case,(f,r) in enumerate(zip(founders,recipients)):
        for ri,rep in enumerate(replicates):
            random=stream(cfg['random_namespace'],int(block),'injury',int(rep),int(f)//2,int(r))
            masks[case,ri].flat[random.choice(eligible,cfg['injury_cells'],replace=False)]=True
    return masks


def select_donors(raw,histories,founders,recipients):
    own=[];donors=[]
    for h,f,r in zip(histories,founders,recipients):
        label,hi=('pulse',2) if h==1 else ('spacing',{0:0,2:1,3:2}[int(h)])
        panel=raw[label]['outgoing'][hi]
        own.append(panel[f,r]);donors.append(np.stack((panel[int(f)^2,r],panel[int(f)^3,r])))
    return np.stack(own),np.stack(donors)


def make_packets(base,donors,original,histories,founders,recipients,block,cfg):
    # base contains incoming and outgoing in that order; donor order is same/opposite.
    assert base.shape==(len(founders),2,4096) and donors.shape==base.shape
    w=decode(base);dw=decode(donors);a=available(original)
    incoming,outgoing=w[:,0],w[:,1]
    assert not outgoing[~a].any()
    edges=(~a)&(incoming!=0)
    common=edges&(dw[:,0]!=0)&(dw[:,1]!=0)
    full=np.where(a,outgoing,incoming)
    own=outgoing.copy();same=outgoing.copy();opposite=outgoing.copy();scrambled=outgoing.copy()
    own[common]=incoming[common]
    same[common]=abs(incoming[common])*np.sign(dw[:,0][common])
    opposite[common]=abs(incoming[common])*np.sign(dw[:,1][common])
    changed=[]
    for i,(h,f,r) in enumerate(zip(histories,founders,recipients)):
        indices=np.flatnonzero(common[i].ravel());signs=np.sign(incoming[i].ravel()[indices])
        random=stream(cfg['random_namespace'],int(block),'backup_signs',int(h),int(f),int(r))
        permuted=random.permutation(signs)
        scrambled[i].ravel()[indices]=abs(incoming[i].ravel()[indices])*permuted
        changed.append(int((signs!=permuted).sum()))
    values=np.stack((incoming,outgoing,full,own,same,opposite,scrambled,np.zeros_like(incoming),dw[:,0],dw[:,1]),axis=1)
    packets=np.ascontiguousarray(values,dtype='<f8').view(np.uint8).reshape(len(founders),10,4096)
    count=lambda value:value.sum(axis=(-3,-2,-1))
    fullmass=(abs(incoming)*edges).sum(axis=(-3,-2,-1))
    mass=(abs(incoming)*common).sum(axis=(-3,-2,-1))
    return dict(packets=packets,donor_packets=donors.copy(),donor_founders=np.stack((founders^2,founders^3),axis=1),
        backup_edges=edges,common_edges=common,backup_nonzero_count=count(edges),common_nonzero_count=count(common),
        common_magnitude_fraction=np.divide(mass,fullmass,out=np.zeros_like(mass),where=fullmass>0),
        donor_sign_differences=count(common&(np.sign(dw[:,0])!=np.sign(dw[:,1]))),
        scramble_sign_changes=np.array(changed),
        same_sign_changes=count(common&(np.sign(incoming)!=np.sign(dw[:,0]))),
        opposite_sign_changes=count(common&(np.sign(incoming)!=np.sign(dw[:,1]))))


def diagnostics(packets,masks,founders,steps):
    weights=decode(packets)[:,:,None]*available(masks)[:,None]
    rows=core.normalized(weights)
    signed=core.cue_transfer(rows,PORTS[0],steps);unsigned=core.cue_transfer(abs(rows),PORTS[0],steps)
    rule=np.where(founders%2==0,1.,-1.)[:,None,None]
    return dict(signed_transfer=core.minimum_task_transfer(signed,PORTS,rule),
        opposite_signed_transfer=core.minimum_task_transfer(signed,PORTS,-rule),
        unsigned_access=np.minimum(unsigned[...,PORTS[1]].mean(axis=-1),unsigned[...,PORTS[2]].mean(axis=-1)))


def prepare(cfg):
    validate(cfg);folder=ROOT/'prepared';folder.mkdir(exist_ok=False);bindings={}
    def bind(p,digest):
        assert sha(p)==digest,str(p)
        bindings[str(p.resolve())]=digest
    source=(ROOT/cfg['source_run']).resolve()
    bind(source/'COMPLETE.json',cfg['source_complete_sha256'])
    done=read(source/'COMPLETE.json');assert done['status']=='COMPLETE' and done['independent_verification_passed']
    bind(source/'manifest.json',done['outputs_sha256']['manifest.json'])
    manifest=read(source/'manifest.json');previous=source/'inputs/prepared'
    bind(previous/'COMPLETE.json',manifest['files_sha256']['prepared/COMPLETE.json'])
    prior=read(previous/'COMPLETE.json');assert prior['records']==64
    bind(previous/'enrollment.csv',prior['outputs_sha256']['enrollment.csv'])
    with (previous/'enrollment.csv').open() as f:enrollment=list(csv.DictReader(f))
    assert len(enrollment)==64 and all(int(r['current_pass'])==0 for r in enrollment)
    with (folder/'enrollment.csv').open('xb') as f:f.write((previous/'enrollment.csv').read_bytes())
    runs={};completions={}
    for label in ('spacing','pulse'):
        run=(ROOT/cfg[label+'_run']).resolve();runs[label]=run
        bind(run/'COMPLETE.json',cfg[label+'_complete_sha256']);completions[label]=read(run/'COMPLETE.json')
        assert completions[label]['status']=='COMPLETE' and completions[label]['native_replay_passed']
    outputs={'enrollment.csv':sha(folder/'enrollment.csv')};rows=[]
    for b,n in zip(cfg['blocks'],cfg['cases_per_block']):
        name=f'cases_{b:06d}.npz';bind(previous/name,prior['outputs_sha256'][name]);old=arrays(previous/name)
        assert len(old['founders'])==n and int(old['block'])==b
        raw={}
        for label,run in runs.items():
            native=f'boundary_{b:06d}_g13.npz';bind(run/native,completions[label]['outputs_sha256'][native])
            with np.load(run/native,allow_pickle=False) as z:raw[label]={'outgoing':z['outgoing']}
        own,donors=select_donors(raw,old['histories'],old['founders'],old['recipients'])
        equal(own,old['packets'][:,0],'source own incoming selection')
        records=make_packets(old['packets'][:,:2],donors,old['original_masks'],old['histories'],old['founders'],old['recipients'],b,cfg)
        equal(records['packets'][:,2],old['packets'][:,3],'full own hybrid identity')
        fresh=new_masks(cfg,b,old['founders'],old['recipients'],cfg['replicates'])
        original=old['original_masks'][:,None]
        features=diagnostics(records['packets'],fresh,old['founders'],cfg['transfer_steps'])
        control=diagnostics(records['packets'],original,old['founders'],cfg['transfer_steps'])
        for vi in (4,5,6):equal(features['unsigned_access'][:,3],features['unsigned_access'][:,vi],'matched unsigned transport')
        for key,val in control.items():
            for vi in (2,3,4,5,6):equal(val[:,1],val[:,vi],'original-mask transport identity')
        data={k:old[k] for k in ('block','histories','founders','recipients','original_masks','original_end','original_mean_ports','original_birth')}
        data.update(records,masks=fresh,replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),**features)
        data.update({'control_'+k:v for k,v in control.items()})
        outputs[name]=save_arrays(folder/name,data)
        for i in range(n):
            rows.append(dict(block=b,local_case=i,history=cfg['histories'][int(data['histories'][i])],founder=int(data['founders'][i]),recipient=int(data['recipients'][i]),
                same_donor_founder=int(data['donor_founders'][i,0]),opposite_donor_founder=int(data['donor_founders'][i,1]),
                **{k:int(data[k][i]) for k in ('backup_nonzero_count','common_nonzero_count','donor_sign_differences','scramble_sign_changes','same_sign_changes','opposite_sign_changes')},
                common_magnitude_fraction=float(data['common_magnitude_fraction'][i])))
    with (folder/'donor_matching.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    outputs['donor_matching.csv']=sha(folder/'donor_matching.csv')
    match=dict(cases=len(rows),backup_edges=sum(r['backup_nonzero_count'] for r in rows),common_edges=sum(r['common_nonzero_count'] for r in rows),
        donor_sign_differences=sum(r['donor_sign_differences'] for r in rows),identical_donor_cases=sum(r['donor_sign_differences']==0 for r in rows),
        zero_common_cases=sum(r['common_nonzero_count']==0 for r in rows),common_edges_min=min(r['common_nonzero_count'] for r in rows),common_edges_max=max(r['common_nonzero_count'] for r in rows),
        mean_common_edge_fraction=float(np.mean([r['common_nonzero_count']/r['backup_nonzero_count'] for r in rows])),
        mean_common_magnitude_fraction=float(np.mean([r['common_magnitude_fraction'] for r in rows])))
    write(folder/'MATCHING.json',match);outputs['MATCHING.json']=sha(folder/'MATCHING.json')
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=64,blocks=8,new_native_outcomes=0,
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','reader.py','prepare.py','diagnostics_core.py')},
        sources_sha256=bindings,outputs_sha256=outputs,donor_source_runs={k:str(v) for k,v in runs.items()},
        recipient_source_run=str(source),all_prior_cases_retained=True,donors_selected_using_outcomes=False))
    print(f'Prepared {len(rows)} recipient cases, 128 donor slots, ten records; no native outcomes generated.',flush=True)


if __name__=='__main__':prepare(read(ROOT/'config.json'))
