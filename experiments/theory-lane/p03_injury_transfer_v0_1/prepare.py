"""Bind the exposed cohort and freeze new injuries without native read outcomes."""
import csv
import numpy as np

from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,validate,write
import diagnostics_core as core
from reader import PORTS,available,decode,stream


def new_masks(cfg,block,founders,recipients,replicates):
    eligible=np.flatnonzero(~PORTS.any(axis=0).ravel())
    assert len(eligible)==244
    masks=np.zeros((len(founders),len(replicates),16,16),bool)
    for case,(founder,recipient) in enumerate(zip(founders,recipients)):
        for ri,rep in enumerate(replicates):
            rng=stream(cfg['random_namespace'],int(block),'injury',int(rep),int(founder)//2,int(recipient))
            cells=rng.choice(eligible,size=cfg['injury_cells'],replace=False)
            masks[case,ri].flat[cells]=True
    return masks


def four_packets(packets,original_masks):
    incoming=decode(packets[:,0:1])[:,0]
    deletion=incoming*available(original_masks)
    erased_only=np.ascontiguousarray(deletion,dtype='<f8').view(np.uint8).reshape(len(packets),4096)
    return np.stack((packets[:,0],packets[:,1],erased_only,np.zeros_like(packets[:,0])),axis=1)


def diagnostics(packets,masks,founders,steps):
    # packets case, variant, byte; masks regime, case, draw, y, x.
    weights=decode(packets)[None,:,:,None]*available(masks)[:,:,None]
    rows=core.normalized(weights)
    signed=core.cue_transfer(rows,PORTS[0],steps)
    unsigned=core.cue_transfer(abs(rows),PORTS[0],steps)
    rules=np.where(founders%2==0,1.,-1.)[None,:,None,None]
    return dict(signed_transfer=core.minimum_task_transfer(signed,PORTS,rules),
                unsigned_access=np.minimum(unsigned[...,PORTS[1]].mean(axis=-1),unsigned[...,PORTS[2]].mean(axis=-1)))


def prepare(cfg):
    validate(cfg)
    folder=ROOT/'prepared';folder.mkdir(exist_ok=False)
    source_run=(ROOT/cfg['source_run']).resolve()
    bindings={}
    def bind(path,digest):
        assert sha(path)==digest,str(path)
        bindings[str(path)]=digest
    bind(source_run/'COMPLETE.json',cfg['source_complete_sha256'])
    done=read(source_run/'COMPLETE.json')
    assert done['status']=='COMPLETE' and done['independent_verification_passed']
    bind(source_run/'manifest.json',done['outputs_sha256']['manifest.json'])
    manifest=read(source_run/'manifest.json')
    old=source_run/'inputs/prepared'
    bind(old/'COMPLETE.json',manifest['code_sha256']['prepared/COMPLETE.json'])
    previous=read(old/'COMPLETE.json')
    assert previous['records']==64 and previous['actual_O_captures_verified']==64
    assert not previous['selection_used_terminal_outcomes']
    bind(old/'enrollment.csv',previous['outputs_sha256']['enrollment.csv'])
    with (old/'enrollment.csv').open() as f:enrollment=list(csv.DictReader(f))
    assert len(enrollment)==64 and all(int(r['current_pass'])==0 for r in enrollment)
    with (folder/'enrollment.csv').open('xb') as f:f.write((old/'enrollment.csv').read_bytes())
    outputs={'enrollment.csv':sha(folder/'enrollment.csv')}
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        name=f'cases_{block:06d}.npz'
        bind(old/name,previous['outputs_sha256'][name])
        data=arrays(old/name,previous['outputs_sha256'][name])
        assert len(data['founders'])==n and int(data['block'])==block
        assert data['packets'].shape==(n,3,4096)
        assert (data['masks'].sum(axis=(-2,-1))==24).all()
        packets=four_packets(data['packets'],data['masks'])
        fresh=new_masks(cfg,block,data['founders'],data['recipients'],cfg['replicates'])
        old_masks=np.repeat(data['masks'][:,None],len(cfg['replicates']),axis=1)
        masks=np.stack((old_masks,fresh))
        assert not (masks & PORTS.any(axis=0)).any()
        assert (masks.sum(axis=(-2,-1))==24).all()
        actual=decode(packets)
        equal(actual[:,0]*available(data['masks']),actual[:,2]*available(data['masks']),'erasure masked identity')
        assert not (actual[:,1]*(~available(data['masks']))).any(),'Outgoing incident edge survived original injury'
        observed=diagnostics(packets,masks,data['founders'],cfg['transfer_steps'])
        for key in observed:
            equal(observed[key][0,:,0],observed[key][0,:,2],'masked diagnostic erasure identity')
            np.testing.assert_allclose(observed[key][0,:,:2,0],data[key][:,:2],rtol=0,atol=2e-14)
        values={k:data[k] for k in ('block','founders','recipients','histories','original_end','original_mean_ports','original_birth')}
        values.update(packets=packets,original_masks=data['masks'],masks=masks,replicates=np.array(cfg['replicates']),
                      original_mask_overlap=(fresh & old_masks).sum(axis=(-2,-1)),**observed)
        outputs[name]=save_arrays(folder/name,values)
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=64,blocks=8,new_native_outcomes=0,
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','reader.py','prepare.py','diagnostics_core.py')},
        sources_sha256=bindings,outputs_sha256=outputs,all_prior_cases_retained=True))
    print('Prepared 64 cases, original and fresh masks, four packets and unchanged diagnostics; no native outcomes.',flush=True)


if __name__=='__main__':prepare(read(ROOT/'config.json'))
