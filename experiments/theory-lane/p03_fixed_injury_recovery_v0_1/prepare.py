"""Enroll all previously observed generation-14 failures; no new dynamics."""
import csv
import importlib.util

import numpy as np

from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,validate,write
from reader import PORTS,available,decode


def prepare(cfg):
    validate(cfg)
    folder=ROOT/'prepared'
    folder.mkdir(exist_ok=False)
    bindings={}

    def bind(path,digest):
        assert sha(path)==digest,str(path)
        bindings[str(path.resolve())]=digest

    p02=(ROOT/cfg['p02_source']).resolve()
    bind(p02/'COMPLETE.json',cfg['p02_complete_sha256'])
    done=read(p02/'COMPLETE.json')
    bind(p02/'FINAL_SNAPSHOT.json',done['final_snapshot_sha256'])
    bind(p02/'results/records.csv',cfg['records_sha256'])
    assert read(p02/'FINAL_SNAPSHOT.json')['files_sha256']['results/records.csv']==cfg['records_sha256']
    with (p02/'results/records.csv').open() as f:
        all_rows=list(csv.DictReader(f))
    assert len(all_rows)==512
    selected=[r for r in all_rows if int(r['current_pass'])==0]
    assert len(selected)==cfg['enrollment_count']
    keys=[(r['block'],r['history'],r['founder'],r['recipient']) for r in selected]
    assert len(set(keys))==64
    runs,complete={},{}
    for label in ('spacing','pulse'):
        path=(ROOT/cfg[label+'_run']).resolve()
        runs[label]=path
        bind(path/'COMPLETE.json',cfg[label+'_complete_sha256'])
        source=read(path/'COMPLETE.json')
        assert source['status']=='COMPLETE' and source['native_replay_passed']
        assert source['blocks_completed']==cfg['blocks']
        complete[label]=source['outputs_sha256']
        bind(path/'manifest.json',complete[label]['manifest.json'])
        native_cfg=read(path/'manifest.json')['config']
        assert native_cfg['config']['dt']==cfg['reader']['dt']
        assert native_cfg['cycle']['settling_steps']==cfg['settling_steps']
        assert native_cfg['cycle']['read_steps']==cfg['primary_budget']
    path=(ROOT/cfg['core_source']).resolve()
    bind(path,cfg['core_sha256'])
    spec=importlib.util.spec_from_file_location('checked_core',path)
    core=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    enrolled=[]
    output_hashes={}
    for bi,block in enumerate(cfg['blocks']):
        group=[r for r in selected if int(r['block'])==block]
        assert len(group)==cfg['cases_per_block'][bi]
        raw={}
        for label in ('spacing','pulse'):
            for g in (13,14):
                name=f'boundary_{block:06d}_g{g}.npz'
                bind(runs[label]/name,complete[label][name])
                raw[label,g]=arrays(runs[label]/name,complete[label][name])
        equal(raw['spacing',14]['masks'],raw['pulse',14]['masks'],'source mask identity')
        equal(raw['spacing',14]['birth'],raw['pulse',14]['birth'],'source reset identity')
        for g in (13,14):
            for field in ('outgoing','end','mean_ports'):
                equal(raw['spacing',g][field][0],raw['pulse',g][field][0],'source original identity')
        packets,masks,ends,means,births,founders,recipients,histories=[],[],[],[],[],[],[],[]
        for r in group:
            assert int(r['generation'])==14 and float(r['current_margin'])<=cfg['reader']['margin']
            hi=cfg['histories'].index(r['history'])
            label,ri=('pulse',2) if hi==1 else ('spacing',{0:0,2:1,3:2}[hi])
            f,rec=int(r['founder']),int(r['recipient'])
            incoming=raw[label,13]['outgoing'][ri,f,rec]
            outgoing=raw[label,14]['outgoing'][ri,f,rec]
            packets.append(np.stack((incoming,outgoing,np.zeros_like(incoming))))
            masks.append(raw[label,14]['masks'][f,rec])
            ends.append(raw[label,14]['end'][ri,f,rec])
            means.append(raw[label,14]['mean_ports'][ri,f,rec])
            births.append(raw[label,14]['birth'][f,rec])
            founders.append(f);recipients.append(rec);histories.append(hi)
        packets=np.stack(packets)
        masks=np.stack(masks)
        body=np.stack(ends)
        assert (masks.sum(axis=(-2,-1))==24).all() and not (masks & PORTS.any(axis=0)).any()
        outgoing=core.writer_pair(body,core.available_edges(masks))['exact']
        expected=np.ascontiguousarray(outgoing,dtype='<f8').view(np.uint8).reshape(len(group),4096)
        equal(expected,packets[:,1],'independent O recapture')
        effective=decode(packets)*available(masks)[:,None]
        normalized=core.normalized(effective)
        signed_field=core.cue_transfer(normalized,PORTS[0],cfg['transfer_steps'])
        unsigned_field=core.cue_transfer(abs(normalized),PORTS[0],cfg['transfer_steps'])
        rules=np.where(np.array(founders)%2==0,1.,-1.)
        signed=core.minimum_task_transfer(signed_field,PORTS,rules[:,None])
        unsigned=np.minimum(unsigned_field[...,PORTS[1]].mean(axis=-1),unsigned_field[...,PORTS[2]].mean(axis=-1))
        for i,r in enumerate(group):
            assert abs(signed[i,1]-float(r['signed_transfer']))<2e-14
            assert abs(unsigned[i,1]-float(r['unsigned_access']))<2e-14
            enrolled.append(dict(block=block,local_case=i,history=r['history'],founder=founders[i],recipient=recipients[i],
                current_margin=float(r['current_margin']),current_pass=0,
                incoming_signed=float(signed[i,0]),outgoing_signed=float(signed[i,1]),
                incoming_unsigned=float(unsigned[i,0]),outgoing_unsigned=float(unsigned[i,1])))
        name=f'cases_{block:06d}.npz'
        output_hashes[name]=save_arrays(folder/name,dict(block=np.array(block),packets=packets,masks=masks,
            original_end=body,original_mean_ports=np.stack(means),original_birth=np.stack(births),
            founders=np.array(founders),recipients=np.array(recipients),histories=np.array(histories),
            signed_transfer=signed,unsigned_access=unsigned))
    with (folder/'enrollment.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(enrolled[0]));writer.writeheader();writer.writerows(enrolled)
    output_hashes['enrollment.csv']=sha(folder/'enrollment.csv')
    write(folder/'COMPLETE.json',dict(status='COMPLETE',created_at_utc=stamp(),records=len(enrolled),
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','reader.py','prepare.py')},
        sources_sha256=bindings,outputs_sha256=output_hashes,selection_used_terminal_outcomes=False,
        actual_O_captures_verified=64,new_native_reads=0))
    print(f'Prepared {len(enrolled)} failed cases with verified incoming/outgoing packets and fixed injury.')


if __name__=='__main__':
    prepare(read(ROOT/'config.json'))
