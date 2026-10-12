"""Construct hybrid records and freeze forecasts without new native outcomes."""
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


def make_packets(base,original_masks,histories,founders,recipients,block,cfg):
    assert base.shape==(len(founders),4,4096)
    weight=decode(base);a=available(original_masks)
    np.testing.assert_array_equal(weight[:,2],weight[:,0]*a)
    assert not (weight[:,1]*(~a)).any() and not weight[:,3].any()
    hybrid=np.where(a,weight[:,1],weight[:,0])
    scrambled=hybrid.copy();counts=[];changes=[]
    for i,(history,founder,recipient) in enumerate(zip(histories,founders,recipients)):
        indices=np.flatnonzero(((~a[i]) & (weight[i,0]!=0)).ravel())
        signs=np.sign(weight[i,0].ravel()[indices])
        rng=stream(cfg['random_namespace'],int(block),'backup_signs',int(history),int(founder),int(recipient))
        permuted=rng.permutation(signs)
        scrambled[i].ravel()[indices]=abs(weight[i,0].ravel()[indices])*permuted
        counts.append(len(indices));changes.append(int((signs!=permuted).sum()))
    values=np.stack((weight[:,0],weight[:,1],weight[:,2],hybrid,scrambled,weight[:,3]),axis=1)
    packets=np.ascontiguousarray(values,dtype='<f8').view(np.uint8).reshape(len(base),6,4096)
    equal(packets[:,0],base[:,0],'incoming bytes')
    equal(packets[:,1],base[:,1],'outgoing bytes')
    equal(packets[:,2],base[:,2],'erasure-only bytes')
    equal(abs(hybrid),abs(scrambled),'hybrid magnitude identity')
    return dict(packets=packets,backup_nonzero_count=np.array(counts),backup_sign_changes=np.array(changes))


def diagnostics(packets,masks,founders,steps):
    weights=decode(packets)[None,:,:,None]*available(masks)[:,:,None]
    rows=core.normalized(weights)
    signed=core.cue_transfer(rows,PORTS[0],steps)
    unsigned=core.cue_transfer(abs(rows),PORTS[0],steps)
    rules=np.where(founders%2==0,1.,-1.)[None,:,None,None]
    return dict(signed_transfer=core.minimum_task_transfer(signed,PORTS,rules),
        unsigned_access=np.minimum(unsigned[...,PORTS[1]].mean(axis=-1),unsigned[...,PORTS[2]].mean(axis=-1)))


def forecasts_from_prior(prior,cfg):
    rates=prior['rate_summaries']['fresh'];by_block={}
    for b in cfg['blocks']:
        i,o,d=[float(rates[v]['by_block'][str(b)]) for v in ('incoming','outgoing','erasure_only')]
        forecast=o+i-d
        assert 0<=forecast<=1,'Frozen block forecast outside probability range; do not clip'
        by_block[str(b)]=dict(additive=forecast,incoming_reference=i,outgoing_reference=o,erasure_reference=d)
    mean=float(np.mean([v['additive'] for v in by_block.values()]))
    assert abs(mean-cfg['advertised_additive_forecast'])<2e-14
    return dict(status='FROZEN_FROM_EXPOSED_PRIOR_RESULTS',source_analysis_sha256=cfg['source_analysis_sha256'],
        formula='prior outgoing + prior incoming - prior erasure_only',by_block=by_block,
        additive_equal_block_mean=mean,clipped=False,fitted_parameters=0,
        forecast_rules=['additive','incoming_reference','outgoing_reference'])


def prepare(cfg):
    validate(cfg);folder=ROOT/'prepared';folder.mkdir(exist_ok=False)
    run=(ROOT/cfg['source_run']).resolve();bindings={}
    def bind(path,digest):
        assert sha(path)==digest,str(path)
        bindings[str(path)]=digest
    bind(run/'COMPLETE.json',cfg['source_complete_sha256'])
    complete=read(run/'COMPLETE.json')
    assert complete['status']=='COMPLETE' and complete['independent_verification_passed']
    bind(run/'manifest.json',complete['outputs_sha256']['manifest.json'])
    bind(run/'analysis.json',cfg['source_analysis_sha256'])
    assert complete['outputs_sha256']['analysis.json']==cfg['source_analysis_sha256']
    manifest=read(run/'manifest.json');previous=run/'inputs/prepared'
    bind(previous/'COMPLETE.json',manifest['files_sha256']['prepared/COMPLETE.json'])
    prior_prepared=read(previous/'COMPLETE.json')
    assert prior_prepared['records']==64 and prior_prepared['all_prior_cases_retained']
    bind(previous/'enrollment.csv',prior_prepared['outputs_sha256']['enrollment.csv'])
    with (previous/'enrollment.csv').open() as f:enrollment=list(csv.DictReader(f))
    assert len(enrollment)==64 and all(int(r['current_pass'])==0 for r in enrollment)
    with (folder/'enrollment.csv').open('xb') as f:f.write((previous/'enrollment.csv').read_bytes())
    with (folder/'source_analysis.json').open('xb') as f:f.write((run/'analysis.json').read_bytes())
    forecast=forecasts_from_prior(read(run/'analysis.json'),cfg)
    write(folder/'forecasts.json',forecast)
    outputs={name:sha(folder/name) for name in ('enrollment.csv','source_analysis.json','forecasts.json')}
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        name=f'cases_{block:06d}.npz';bind(previous/name,prior_prepared['outputs_sha256'][name])
        old=arrays(previous/name,prior_prepared['outputs_sha256'][name])
        assert len(old['founders'])==n and int(old['block'])==block
        records=make_packets(old['packets'],old['original_masks'],old['histories'],old['founders'],old['recipients'],block,cfg)
        fresh=new_masks(cfg,block,old['founders'],old['recipients'],cfg['replicates'])
        original=np.repeat(old['original_masks'][:,None],len(cfg['replicates']),axis=1)
        masks=np.stack((original,fresh))
        features=diagnostics(records['packets'],masks,old['founders'],cfg['transfer_steps'])
        for key,values in features.items():
            equal(values[0,:,0],values[0,:,2],'original incoming/erasure diagnostic identity')
            for v in (3,4):equal(values[0,:,1],values[0,:,v],'original hybrid diagnostic identity')
            np.testing.assert_allclose(values[0,:,:3,0],old[key][0,:,:3,0],rtol=0,atol=2e-14)
        equal(features['unsigned_access'][:,:,3],features['unsigned_access'][:,:,4],'all-mask unsigned hybrid identity')
        values={k:old[k] for k in ('block','founders','recipients','histories','original_masks','original_end','original_mean_ports','original_birth')}
        values.update(**records,**features,masks=masks,replicates=np.array(cfg['replicates']),
            original_mask_overlap=(fresh & original).sum(axis=(-2,-1)))
        outputs[name]=save_arrays(folder/name,values)
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=64,blocks=8,new_native_outcomes=0,
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','reader.py','prepare.py','diagnostics_core.py')},
        sources_sha256=bindings,outputs_sha256=outputs,all_prior_cases_retained=True,
        frozen_additive_forecast=forecast['additive_equal_block_mean'],permutations_selected_using_outcomes=False))
    print(f'Prepared 64 cases and six records. Frozen additive forecast: {100*forecast["additive_equal_block_mean"]:.8f}%. No native outcomes generated.',flush=True)


if __name__=='__main__':prepare(read(ROOT/'config.json'))
