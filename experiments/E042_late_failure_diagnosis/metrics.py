"""Measurements of saved E041 records and responses; no simulated dynamics."""
import hashlib
import json
import numpy as np
from E032_renewal_failure_diagnosis import metrics as prior

CONDITIONS = ('standard_preserve','standard_rewrite','bridge_preserve','bridge_rewrite',
    'contrast_preserve','bridge_read_blocked','bridge_write_blocked','protected_copy','masked_copy',
    'bridge_rewrite_read_blocked','bridge_rewrite_write_blocked')
ACTIVE = (0,1,2,3,4,5,6,9,10)
GRAPH_CONDITIONS = (0,1,2,3)
HORIZONS = (0,1,3,8,16,24,32)
DAMAGE = ('intact','scattered','square')
PACKET_FIELDS, OUTPUT_FIELDS, TRANSITION_FIELDS = prior.PACKET_FIELDS, prior.OUTPUT_FIELDS, prior.TRANSITION_FIELDS
GRAPH_FIELDS = ('nonzero_output_fraction','nonzero_all_outputs','strong_output_fraction','strong_all_outputs')
REPAIR_FIELDS = ('available','returning','returning_nonzero','returning_strong','returning_abs_sum',
    'available_weak_nonzero','weak_promoted','weak_erased','available_zero','zero_restored','zero_promoted',
    'zero_abs_sum','young_weak','young_promoted','young_erased','young_abs_before','young_abs_after')
RATIOS = {'returning_nonzero_rate':(2,1),'returning_strong_rate':(3,1),'returning_mean_abs':(4,1),
    'weak_promotion_rate':(6,5),'weak_erasure_rate':(7,5),'zero_restoration_rate':(9,8),
    'zero_promotion_rate':(10,8),'zero_mean_abs':(11,8),'young_promotion_rate':(13,12),
    'young_erasure_rate':(14,12),'young_mean_abs_before':(15,12),'young_mean_abs_after':(16,12)}
JOINT_FIELDS = ('intact_and_scattered_success','intact_success_scattered_failure',
    'intact_failure_scattered_success','intact_and_scattered_failure',
    'scattered_failure_square_success','scattered_failure_other_terminal_success',
    'all_terminal_failed','scattered_failure_current_body_success','intact_failure_current_body_success',
    'scattered_failure_next_body_success','scattered_failure_next_body_observed')
FIELDS = dict(packet=PACKET_FIELDS,repair=REPAIR_FIELDS,body=OUTPUT_FIELDS,terminal=OUTPUT_FIELDS,
    graph=GRAPH_FIELDS,transitions=TRANSITION_FIELDS,terminal_transitions=TRANSITION_FIELDS,joint=JOINT_FIELDS)


def load(source,name,complete):
    path=source/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==complete['outputs_sha256'][name], name
    with np.load(path,allow_pickle=False) as z: data={k:z[k] for k in z.files}
    if '__index__' in data:
        meta=json.loads(data.pop('__index__').tobytes())
        assert meta['format'] in ('E031_compact_v1','E041_source_v1')
        assert set(data)==set(meta['retained'])
        for key,v in data.items():
            assert meta['arrays'][key]==dict(shape=list(v.shape),dtype=v.dtype.str,
                sha256=hashlib.sha256(v.tobytes(order='C')).hexdigest()),(name,key)
    assert all(np.isfinite(x).all() for x in data.values())
    return data


def repair(old,new,live,last_live,last_return):
    returning=live & ~last_live
    weak=live & (old!=0) & (abs(old)<=.5)
    zero=live & (old==0); young=weak & last_return
    values=(live,returning,returning&(new!=0),returning&(abs(new)>.5),returning*abs(new),
        weak,weak&(abs(new)>.5),weak&(new==0),zero,zero&(new!=0),zero&(abs(new)>.5),zero*abs(new),
        young,young&(abs(new)>.5),young&(new==0),young*abs(old),young*abs(new))
    return np.stack([x.sum(axis=(-3,-2,-1)) for x in values],axis=-1).astype(float),returning


def graph(weights):
    return np.concatenate([prior.graph_features((abs(weights)>threshold).astype(float))
        for threshold in (0.,.5)],axis=-1)


def joint(terminal,body):
    rows=[]
    for i,h in enumerate(HORIZONS[1:],1):
        success=terminal[i,list(ACTIVE),...,0].astype(bool)
        intact,scatter,square=[success[...,d] for d in range(3)]
        current=body[h-1,...,0].astype(bool)
        nxt=body[h,...,0].astype(bool) if h<32 else np.zeros_like(current)
        rows.append(np.stack((intact&scatter,intact&~scatter,~intact&scatter,~intact&~scatter,
            ~scatter&square,~scatter&(intact|square),~(intact|scatter|square),~scatter&current,
            ~intact&current,~scatter&nxt,~scatter&(h<32)),axis=-1))
    return np.asarray(rows,dtype=float)


def extract(source,block,complete):
    acquired=load(source,f'source_{block:06d}.npz',complete)['acquired'][1]
    first=load(source,f'boundary_{block:06d}_g1.npz',complete)
    R=first['outgoing'].shape[2]
    original=np.repeat(prior.decode(acquired)[:,None],R,axis=1)
    old=np.repeat(original[None],11,axis=0)
    live=np.ones_like(old,bool); returned=np.zeros_like(live)
    packet=[prior.packet_features(old,old,original,live,True)]
    packets={0:old[list(GRAPH_CONDITIONS)].copy()}; repairs=[]; bodies=[]
    for g in range(1,33):
        raw=first if g==1 else load(source,f'boundary_{block:06d}_g{g}.npz',complete)
        new=prior.decode(raw['outgoing']); previous_live=live
        live=np.broadcast_to(prior.available(raw['renewal_mask']),new.shape).copy();live[7]=True
        packet.append(prior.packet_features(old,new,original,live))
        r,new_return=repair(old,new,live,previous_live,returned);repairs.append(r)
        bodies.append(prior.output_features(raw['developed_mean_ports'],prior.RULES[None,:,None]))
        for j,c in enumerate(ACTIVE):
            held=live[c]&(abs(old[c])>.5) if c in (0,2,4,5,6) else np.zeros_like(live[c])
            np.testing.assert_array_equal(raw['retained_edges'][j],held)
            np.testing.assert_array_equal(raw['eligible_edges'][j],live[c]&~held)
        if g in HORIZONS:packets[g]=new[list(GRAPH_CONDITIONS)].copy()
        old,returned=new,new_return
    bodies=np.stack(bodies); terminals=[]; graphs=[]
    for h in HORIZONS:
        raw=load(source,f'assay_{block:06d}_h{h}.npz',complete)
        n=1 if h==0 else 11
        ports=raw['mean_ports'][n:,:,:,:,:,0,:].transpose(0,1,2,4,3,5)
        if h==0:ports=ports.repeat(11,axis=0)
        terminals.append(prior.output_features(ports,prior.RULES[None,:,None,None]))
        effective=packets[h][:,:,:,None]*prior.available(raw['masks'])[None]
        graphs.append(graph(effective))
    terminal=np.stack(terminals)
    return dict(packet=np.stack(packet),repair=np.stack(repairs),body=bodies,terminal=terminal,
        graph=np.stack(graphs),transitions=prior.transitions(bodies[...,0]),
        terminal_transitions=prior.transitions(terminal[...,0]),joint=joint(terminal,bodies))
