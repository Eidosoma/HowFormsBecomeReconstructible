"""Fresh random tapes, original own-source preparation, unchanged H083 reader."""
import hashlib
import json
import numpy as np
from h081 import model as old
from h083 import model as pair

SEED,NETWORKS,ENGINEERING=84084,192,4
N,R,NY=old.N,old.R,old.NY
STARTS,GAPS,BASELINES=pair.STARTS,pair.GAPS,pair.BASELINES


def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','confirmation') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='confirmation':assert block<NETWORKS
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))


def tapes(cohort,block):
    gen=rng(cohort,block,'responses');y=np.full((8,NY),-1,dtype=np.int8)
    for row in y:row[gen.permutation(NY)[:NY//2]]=1
    out=dict(responses=y,birth=rng(cohort,block,'birth').choice([-1,1],size=(R,N)).astype(np.int8))
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([gen.permutation(N) for _ in range(count)])
    return out


def tape_digest(tape):
    digest=hashlib.sha256()
    for key,value in sorted(tape.items()):
        digest.update(json.dumps([key,value.dtype.str,value.shape],separators=(',',':')).encode())
        digest.update(value.tobytes(order='C'))
    return digest.hexdigest()


def source_prefix(start,gap):
    return f'delayed_d{gap}_own_read8_' if start=='delayed' else old.prefix(start,gap,'own')


def source(tape):
    raw={key:value.copy() for key,value in tape.items()}
    raw['training_inputs']=old.X.copy();raw['history_own']=old.history('own')
    learned=old.acquire(dict(observed_inputs=old.X,observed_outputs=raw['responses']))
    raw.update({'source_'+key:value[None].copy() for key,value in learned.items()})
    record=learned['J_projection'];initial=np.broadcast_to(raw['birth'][None],(8,R,N)).copy()
    context=old.constant_segment(dict(record=record,state=initial,orders=raw['orders_context'],
        clamp_indices=old.CONTEXT,clamp_values=old.X[:,None,:32],active_sweeps=4))
    for gap in GAPS:
        rest=old.constant_segment(dict(record=record,state=context['final'],orders=raw['orders_gap'][:gap],
            clamp_indices=np.asarray([],dtype=int),clamp_values=np.empty((8,1,0),dtype=np.int8),active_sweeps=gap))
        for phase,data in (('context',context),('gap',rest)):
            raw.update({f'd{gap}_own_{phase}_'+key:value.copy() for key,value in data.items()})
        for horizon in (0,1,8):
            saved=old.segment(dict(record=record,state=rest['final'],orders=raw['orders_query'],
                clamp_indices=old.QUERY,clamp_values=old.X[:,None,32:],active_sweeps=horizon,
                feedback=old.FEEDBACK['delayed']))
            raw.update({f'delayed_d{gap}_own_read{horizon}_'+key:value for key,value in saved.items()})
        saved=old.intervene(dict(record=record,state=rest['final'],orders=raw['orders_query'],
            clamp_indices=old.QUERY,clamp_values=old.X[:,None,32:],policy='cue_hysteresis'))
        raw.update({source_prefix('cue_hysteresis',gap)+key:value for key,value in saved.items()})
    for method in BASELINES:
        result=old.baseline(old.packet_for_baseline(raw,'own',method))
        raw.update({f'baseline_own_{method}_'+key:value for key,value in result.items()})
    return raw


def reader_source(raw):
    data=dict(record=raw['source_J_projection'][0].copy(),target=raw['responses'].copy(),
        inputs=raw['training_inputs'].copy(),orders=raw['orders_query'].copy())
    for method in BASELINES:data['baseline_'+method]=raw[f'baseline_own_{method}_final'].copy()
    for gap in GAPS:
        for h in (0,1):data[f'd{gap}_read{h}_final']=raw[f'delayed_d{gap}_own_read{h}_final'].copy()
        for start in STARTS:
            for key in ('trace','conditional_fixed','nominal_conditional_fixed'):
                data[f'{start}_d{gap}_'+key]=raw[source_prefix(start,gap)+key].copy()
    return data


def run(cohort,block):
    raw=source(tapes(cohort,block));data=pair.run(reader_source(raw))
    return raw,data
