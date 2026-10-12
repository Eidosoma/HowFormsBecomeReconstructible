"""D133: post-hoc fidelity localization from frozen D132 bytes/states; no dynamics."""
from __future__ import annotations
import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT,environment_manifest,git_head,sha256_file,utc_now

WS=Path(__file__).resolve().parents[1]
RUN_ID='l20_renewal_fidelity_audit_v1_attempt1'
SOURCE_RUN='l20_guide_renewal_v1_attempt1'
SOURCE_COMPLETE='aed770e0ba159edd27c099485c0cd4d5d3b8fd0ac06428cc864ed371b7b8fa7f'
GUIDE_SHA='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
SCIENCE=('scripts/audit_l20_renewal_fidelity.py','tests/test_l20_renewal_fidelity.py',
    'scripts/run_l20_renewal_fidelity.sh','protocols/L20_RENEWAL_FIDELITY_AUDIT_V1.md')
KINDS=('learned','native','supplied','aligned','copy','read_off','write_off','wrong','lesion','rescue','wrong_guide')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+('learned_shuffle','shuffle_learned','ideal','ideal_shifted','ideal_learned','zero'))
INDICES=tuple(range(73000,73008));DISPOSABLE=514232
READ_TIMES=(0,1,100,101,300);WRITE_TIMES=(0,1,300,1000);TERMINAL_TIMES=(0,1,100,300)
ATOL=1e-12;BUDGET=128*1024**2
OUTPUTS=('INPUTS.json','features.npz','summary.json','verification.json')
DETACHED_ENV='L20_RENEWAL_FIDELITY_DETACHED_LOG'
METRICS=('mean','std','row_power','column_power','canonical_own','canonical_other','best_own','best_other',
    'family_margin','ideal_family','own_optima','canonical_mse','best_mse','address_gap','own_sign','other_sign',
    'sign_preference','own_qualified','other_qualified','qualified_preference','constant')
LABELS=tuple((g,phase,t,field) for g in (1,2,3) for phase,t,field in
    [('packet',0,k) for k in ('incoming','routed','outgoing')]+
    [('read',t,f) for t in READ_TIMES for f in ('V','R')]+
    [('write',t,f) for t in WRITE_TIMES for f in ('V','R','theta')])+tuple(
    (4,phase,t,field) for phase,t,field in [('packet',0,'incoming'),('packet',0,'routed')]+
    [('read',t,f) for t in TERMINAL_TIMES for f in ('V','R')])
PACKET_POSITIONS=tuple(i for i,x in enumerate(LABELS) if x[1]=='packet')
READ_KEYS=('targets','guide','written_fields','lesion_permutations','incoming','routed','backup_routed','outgoing',
    'generation_read_states','generation_write_states','generation_scores','terminal_inputs','terminal_packets',
    'terminal_scores','terminal_states','values','terminal_values')


def io_helpers():
    from laws_confirmation import l15_repair_speed_run as u
    from laws_confirmation.l16_body_content_run import preflight
    return u,preflight


def targets():
    y,x=np.indices((16,16))
    return np.stack((np.where(y<8,1.,-1.),np.where((x//4)%2==0,1.,-1.)))


def encode(field):
    if not isinstance(field,np.ndarray) or field.shape!=(16,16) or field.dtype!=np.float64 or not np.isfinite(field).all():
        raise ValueError('finite float64 field required')
    return field.astype('<f8').tobytes()


def decode(b):
    if type(b) is not bytes or len(b)!=2048:raise ValueError('2048 bytes only')
    a=np.frombuffer(b,'<f8').reshape(16,16).copy()
    if not np.isfinite(a).all():raise ValueError('finite packet required')
    return a


def project(a):
    centered=a-np.mean(a);return centered*(.3/max(float(np.std(centered)),1e-9))


def move(a,shift,inverse=False):
    y,x=np.indices((16,16));dy,dx=map(int,shift)
    sign=1 if inverse else -1
    return a[(y+sign*dy)%16,(x+sign*dx)%16]


@lru_cache(maxsize=4)
def bank(serialized):
    if type(serialized) is not bytes or len(serialized)!=4096:raise ValueError('two template fields required')
    template=np.frombuffer(serialized,'<f8').reshape(2,16,16).copy()
    if not np.isfinite(template).all() or np.any(template.std(axis=(1,2))<=1e-9):raise ValueError('nondegenerate templates required')
    template-=template.mean(axis=(1,2),keepdims=True);template/=template.std(axis=(1,2),keepdims=True)
    result=np.stack([[move(t,divmod(i,16)) for i in range(256)] for t in template]).reshape(512,256)
    result.setflags(write=False);return result


def normalize(fields):
    if not isinstance(fields,np.ndarray) or fields.ndim!=3 or fields.shape[1:]!=(16,16) or fields.dtype!=np.float64 or not np.isfinite(fields).all():
        raise ValueError('finite batch of float64 fields required')
    centered=fields-fields.mean(axis=(1,2),keepdims=True);scale=centered.std(axis=(1,2))
    if not np.isfinite(scale).all():raise ValueError('finite scale required')
    q=np.divide(centered,scale[:,None,None],out=np.zeros_like(centered),where=scale[:,None,None]!=0)
    return q,scale


def correlations(fields,template):
    q,_=normalize(fields)
    return (q.reshape(len(fields),256)@bank(template.astype('<f8').tobytes()).T/256).reshape(-1,2,16,16)


def fft_correlations(fields,template):
    # Independent normalization and circular-correlation implementation.
    centered=fields-np.mean(fields,axis=(-2,-1),keepdims=True)
    residual=centered-np.mean(centered,axis=(-2,-1),keepdims=True)
    scale=np.sqrt(np.mean(residual*residual,axis=(-2,-1)))
    t=template-np.mean(template,axis=(-2,-1),keepdims=True)
    residual_t=t-np.mean(t,axis=(-2,-1),keepdims=True)
    t=t/np.sqrt(np.mean(residual_t*residual_t,axis=(-2,-1),keepdims=True))
    fft=np.fft.fft2(centered,axes=(-2,-1))[:,None]*np.conj(np.fft.fft2(t,axes=(-2,-1)))[None]
    result=np.fft.ifft2(fft,axes=(-2,-1)).real
    return np.divide(result,256*scale[:,None,None,None],out=np.zeros_like(result),where=scale[:,None,None,None]!=0)


def field_features(fields,roles,scores):
    if roles.shape!=(len(fields),) or roles.dtype!=np.int64 or not np.isin(roles,(0,1)).all():raise ValueError('declared scoring roles required')
    if scores.shape!=(len(fields),2,16,16) or not np.isfinite(scores).all():raise ValueError('complete scores required')
    q,scale=normalize(fields);ix=np.arange(len(fields));other=1-roles
    canonical=scores[:,:,0,0];best=scores.max(axis=(-2,-1));a=best[ix,roles];b=best[ix,other]
    family=np.where(abs(best[:,0]-best[:,1])<=ATOL,-1,np.argmax(best,axis=1))
    ts=targets()>0;sign=fields>0;nonconstant=(scale!=0).astype(float)
    own=np.mean(sign==ts[roles],axis=(1,2));alt=np.mean(sign==ts[other],axis=(1,2));amp=abs(fields)>.2
    oq=np.mean((sign==ts[roles])&amp,axis=(1,2));aq=np.mean((sign==ts[other])&amp,axis=(1,2))
    canonical_mse=nonconstant+1-2*canonical[ix,roles];best_mse=nonconstant+1-2*a
    return np.stack((fields.mean(axis=(1,2)),scale,np.mean(q.mean(axis=2)**2,axis=1),np.mean(q.mean(axis=1)**2,axis=1),
        canonical[ix,roles],canonical[ix,other],a,b,a-b,family,
        np.sum(abs(scores[ix,roles]-a[:,None,None])<=ATOL,axis=(1,2)),canonical_mse,best_mse,
        2*(a-canonical[ix,roles]),own,alt,own-alt,oq,aq,oq-aq,1-nonconstant),axis=1)


def check_features(fields,roles,scores,features):
    # Restated direct mismatch and observer calculations, independent of field_features.
    assert features.shape==(len(fields),len(METRICS)) and np.isfinite(features).all()
    ix=np.arange(len(fields));center=fields-fields.mean(axis=(1,2),keepdims=True)
    residual=center-center.mean(axis=(1,2),keepdims=True)
    sd=np.sqrt((residual**2).mean(axis=(1,2)))
    q=np.divide(center,sd[:,None,None],out=np.zeros_like(center),where=sd[:,None,None]!=0)
    y,x=np.indices((16,16));ts=np.stack((2.*(y<8)-1.,2.*((x//4)%2==0)-1.))
    c=np.mean(q*ts[roles],axis=(1,2));own=scores[ix,roles];best=own.max(axis=(1,2))
    other=scores[ix,1-roles].max(axis=(1,2));maxima=scores.max(axis=(2,3))
    family=np.where(abs(maxima[:,0]-maxima[:,1])<=ATOL,-1,(maxima[:,1]>maxima[:,0]).astype(int))
    expected_mse=np.mean((q-ts[roles])**2,axis=(1,2))
    m=lambda name:features[:,METRICS.index(name)]
    checks=[abs(m('mean')-fields.mean(axis=(1,2))).max(),abs(m('std')-sd).max(),
        abs(m('canonical_own')-c).max(),abs(m('canonical_mse')-expected_mse).max(),
        abs(m('best_mse')-((sd!=0)+1.-2*best)).max(),
        abs(m('canonical_mse')-m('best_mse')-m('address_gap')).max(),
        abs(m('canonical_other')-np.mean(q*ts[1-roles],axis=(1,2))).max(),
        abs(m('best_own')-best).max(),abs(m('best_other')-other).max(),
        abs(m('family_margin')-(best-other)).max(),abs(m('ideal_family')-family).max(),
        abs(m('own_optima')-np.sum(abs(own-best[:,None,None])<=ATOL,axis=(1,2))).max(),
        abs(m('row_power')-np.mean(np.mean(q,axis=2)**2,axis=1)).max(),
        abs(m('column_power')-np.mean(np.mean(q,axis=1)**2,axis=1)).max(),
        abs(m('constant')-(sd==0)).max()]
    for name,target in (('own',ts[roles]),('other',ts[1-roles])):
        mask=((fields>0)&(target>0))|((fields<=0)&(target<0))
        checks.extend([abs(m(name+'_sign')-mask.mean(axis=(1,2))).max(),
            abs(m(name+'_qualified')-(mask&(abs(fields)>.2)).mean(axis=(1,2))).max()])
    for name in ('sign','qualified'):checks.append(abs(m(name+'_preference')-(m('own_'+name)-m('other_'+name))).max())
    maximum=float(max(checks));assert maximum<=ATOL
    assert np.all(m('address_gap')>=-ATOL) and np.all(m('best_mse')>=-ATOL)
    return maximum


def select(b,template):
    scores=fft_correlations(decode(b)[None],template)[0]
    maxima=scores.max(axis=(1,2));tie=bool(abs(maxima[0]-maxima[1])<=ATOL)
    family=-1 if tie else int(np.argmax(maxima));shift=np.zeros(2,dtype=np.int64)
    mask=abs(scores-scores.max())<=ATOL
    if not tie:
        mask=np.zeros_like(scores,dtype=bool);mask[family]=abs(scores[family]-maxima[family])<=ATOL
        shift=np.argwhere(mask[family])[0].astype(np.int64)
    out=encode(move(decode(b),shift,True));sha=lambda x:hashlib.sha256(x).hexdigest()
    return out,scores,dict(input_sha256=sha(b),output_sha256=sha(out),guide_sha256=sha(template.astype('<f8').tobytes()),
        inferred_family=family,chosen_forward_shift=shift.tolist(),family_maxima=maxima.tolist(),family_tie=tie,
        candidate_count=int(mask.sum()),candidate_mask_sha256=sha(mask.tobytes()),
        rule='family tie: identity abstention; otherwise lexicographically first maximizing shift, then inverse',
        tie_atol=ATOL,inputs=['packet_bytes','frozen_guide_bytes'],target_label_access=False,
        historical_shift_access=False,source_state_access=False,outcome_access=False,record_reprojected=False)


def nested(actual,expected):
    if isinstance(expected,dict):
        assert set(actual)==set(expected)
        for k in expected:nested(actual[k],expected[k])
    elif isinstance(expected,list):
        assert isinstance(actual,list) and len(actual)==len(expected)
        for a,b in zip(actual,expected):nested(a,b)
    elif type(expected) is float:
        assert type(actual) in (int,float) and np.isfinite(actual) and abs(actual-expected)<=ATOL
    else:assert type(actual) is type(expected) and actual==expected


def load_panel(index,root=DEFAULT_EXTERNAL_ROOT):
    if type(index) is not int or index not in INDICES+(DISPOSABLE,):raise ValueError('retained source identity required')
    d=root/('tmp' if index==DISPOSABLE else 'outputs')/(SOURCE_RUN+'_benchmark' if index==DISPOSABLE else SOURCE_RUN)
    with np.load(d/f'block_{index}.npz',allow_pickle=False) as saved:raw={k:saved[k] for k in READ_KEYS}
    meta=json.loads((d/f'block_{index}.json').read_text())
    validate_panel(index,raw,meta)
    return raw,meta


def validate_panel(index,raw,meta):
    assert type(index) is int and index in INDICES+(DISPOSABLE,) and meta['index']==index
    assert set(raw)==set(READ_KEYS) and len(meta['lives'])==4
    shapes=dict(targets=(4,2,16,16),guide=(4,2,16,16),written_fields=(4,2,2,16,16),lesion_permutations=(4,2,256),
        incoming=(4,22,3,2048),routed=(4,22,3,2048),backup_routed=(4,22,3,2048),outgoing=(4,22,3,2048),
        generation_read_states=(4,22,3,5,3,16,16),generation_write_states=(4,22,3,4,4,16,16),
        generation_scores=(4,22,3,2,2,16,16),terminal_inputs=(4,34,2048),terminal_packets=(4,34,2048),
        terminal_scores=(4,34,2,16,16),terminal_states=(4,34,4,3,16,16),values=(4,22,3,5,12),terminal_values=(4,34,4,12))
    bytekeys={'incoming','routed','backup_routed','outgoing','terminal_inputs','terminal_packets'}
    for k,shape in shapes.items():
        dtype=np.uint8 if k in bytekeys else np.int64 if k=='lesion_permutations' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    for life in range(4):
        np.testing.assert_array_equal(raw['targets'][life],targets())
        assert hashlib.sha256(raw['guide'][life].astype('<f8').tobytes()).hexdigest()==GUIDE_SHA
        row=meta['lives'][life];assert row['index']==index and row['life']==life
        nested(row['cases'],[list(c) for c in CASES]);nested(row['probes'],[list(c) for c in PROBES])
        assert row['read_times']==list(READ_TIMES) and row['source_times']==list(WRITE_TIMES) and row['times']==list(TERMINAL_TIMES)


def fields_panel(raw):
    packets=lambda key:raw[key].copy().view('<f8').reshape(raw[key].shape[:-1]+(16,16))
    inc,routed,out=map(packets,('incoming','routed','outgoing'))
    mapping=[PROBES.index(c) for c in CASES]
    terminal_in=packets('terminal_inputs')[:,mapping];terminal_out=packets('terminal_packets')[:,mapping]
    cols=[]
    for g in range(3):
        cols.extend((inc[:,:,g],routed[:,:,g],out[:,:,g]))
        for ti in range(5):
            for si in (0,2):cols.append(raw['generation_read_states'][:,:,g,ti,si])
        for ti in range(4):
            for si in (0,2,3):cols.append(raw['generation_write_states'][:,:,g,ti,si])
    cols.extend((terminal_in,terminal_out))
    for ti in range(4):
        for si in (0,2):cols.append(raw['terminal_states'][:,mapping,ti,si])
    result=np.stack(cols,axis=2);assert result.shape==(4,22,85,16,16)
    return result


def check_routes_and_lineage(raw,meta):
    maximum=first=0.;decisions=rewrites=0
    families=np.full((4,22,4),-2,dtype=np.int64)
    for life,row in enumerate(meta['lives']):
        guide=raw['guide'][life];priors={'supplied':targets(),'wrong_guide':np.stack([move(t,(3,5)) for t in guide])}
        for ci,(role,kind) in enumerate(CASES):
            r=1-role if kind=='wrong' else role;mi=1 if kind=='aligned' else 0
            original=encode(raw['written_fields'][life,r,mi])
            if kind in ('lesion','rescue'):
                permutation=raw['lesion_permutations'][life,role]
                np.testing.assert_array_equal(np.sort(permutation),np.arange(256))
                original=encode(decode(original).ravel()[permutation].reshape(16,16))
            incoming=original
            for gi in range(3):
                assert raw['incoming'][life,ci,gi].tobytes()==incoming
                start=raw['generation_read_states'][life,ci,gi,-1]
                np.testing.assert_array_equal(raw['generation_write_states'][life,ci,gi,0],np.concatenate((start,np.zeros((1,16,16)))))
                rm=row['generations'][ci][gi]
                actual=raw['routed'][life,ci,gi].tobytes()
                if kind in ('native','aligned'):
                    assert actual==incoming and rm['selector'] is None
                    assert not raw['generation_scores'][life,ci,gi,0].any()
                else:
                    expected,scores,selection=select(incoming,priors.get(kind,guide))
                    assert actual==expected;nested(rm['selector'],selection)
                    maximum=max(maximum,float(abs(scores-raw['generation_scores'][life,ci,gi,0]).max()))
                    families[life,ci,gi]=selection['inferred_family'];decisions+=1
                if kind=='rescue' and gi==0:
                    backup=encode(raw['written_fields'][life,role,0]);expected,scores,selection=select(backup,guide)
                    assert raw['backup_routed'][life,ci,gi].tobytes()==expected;nested(rm['backup_selector'],selection)
                    maximum=max(maximum,float(abs(scores-raw['generation_scores'][life,ci,gi,1]).max()));decisions+=1
                else:
                    assert not raw['backup_routed'][life,ci,gi].any() and not raw['generation_scores'][life,ci,gi,1].any()
                    assert rm['backup_selector'] is None
                if kind=='copy':expected=incoming
                elif kind=='write_off':expected=bytes(2048)
                else:
                    path=raw['generation_write_states'][life,ci,gi]
                    expected=encode(project(np.tanh(path[-1,2])))
                    first=max(first,float(abs(path[1,3]-project(np.tanh(path[1,2]))).max()));rewrites+=1
                outgoing=raw['outgoing'][life,ci,gi].tobytes();assert outgoing==expected
                assert rm['input_sha256']==hashlib.sha256(incoming).hexdigest()
                assert rm['output_sha256']==hashlib.sha256(outgoing).hexdigest()
                incoming=outgoing
            pi=PROBES.index((role,kind));assert raw['terminal_inputs'][life,pi].tobytes()==incoming
            delivered=raw['terminal_packets'][life,pi].tobytes();selection=row['terminal'][pi]['selector']
            if kind in ('native','aligned'):
                assert delivered==incoming and selection is None and not raw['terminal_scores'][life,pi].any()
            else:
                expected,scores,entry=select(incoming,priors.get(kind,guide));assert delivered==expected;nested(selection,entry)
                maximum=max(maximum,float(abs(scores-raw['terminal_scores'][life,pi]).max()))
                families[life,ci,3]=entry['inferred_family'];decisions+=1
    assert decisions==296 and rewrites==216 and maximum<=ATOL and first<=ATOL
    return families,dict(selector_decisions=decisions,selector_max_abs=maximum,record_reconstructions=rewrites,
        first_projection_max_abs=first,erased_writer_births=264,packet_lineage=True)


def check_source_observers(raw):
    maximum=0.
    for key,valuekey,cases in (('generation_read_states','values',CASES),('terminal_states','terminal_values',PROBES)):
        for ci,(role,_) in enumerate(cases):
            v=raw[key][:,ci,...,0,:,:];own=(v>0)==(targets()[role]>0);alt=(v>0)==(targets()[1-role]>0)
            expected=np.stack((np.mean(own&(abs(v)>.2),axis=(-2,-1)),np.mean(alt&(abs(v)>.2),axis=(-2,-1)),
                np.mean(own,axis=(-2,-1)),np.mean(alt,axis=(-2,-1))),axis=-1)
            maximum=max(maximum,float(abs(expected-raw[valuekey][:,ci,...,:4]).max()))
    assert maximum==0.;return maximum


def analyze_panel(index,raw,meta):
    validate_panel(index,raw,meta)
    fields=fields_panel(raw);flat=fields.reshape(-1,16,16)
    scores=correlations(flat,targets());independent=fft_correlations(flat,targets())
    error=float(abs(scores-independent).max());assert error<=ATOL
    roles=np.broadcast_to(np.repeat(np.arange(2,dtype=np.int64),11)[None,:,None],(4,22,85)).ravel().copy()
    features=field_features(flat,roles,scores);ferror=check_features(flat,roles,independent,features)
    features=features.reshape(4,22,85,len(METRICS));scores=scores.reshape(4,22,85,2,16,16)
    invariance=0.
    for g in (1,2,3,4):
        a=LABELS.index((g,'packet',0,'incoming'));b=LABELS.index((g,'packet',0,'routed'))
        cols=[METRICS.index(k) for k in ('mean','std','row_power','column_power','best_own','best_other','family_margin','best_mse')]
        invariance=max(invariance,float(abs(features[:,:,a,cols]-features[:,:,b,cols]).max()))
    assert invariance<=ATOL
    families,proof=check_routes_and_lineage(raw,meta)
    proof.update(index=index,fields=len(flat),packet_fields=968,correlation_max_abs=error,feature_max_abs=ferror,
        route_invariance_max_abs=invariance,source_observer_max_abs=check_source_observers(raw),new_trajectories=0)
    return dict(features=features,packet_scores=scores[:,:,PACKET_POSITIONS].copy(),selector_families=families),proof


def aggregate(a):
    assert a.shape[0]==8 and np.isfinite(a).all()
    blocks=a.mean(axis=1)
    return dict(mean=float(a.mean()),minimum=float(a.min()),maximum=float(a.max()),block_means=blocks.tolist())


def summarize(arrays,proofs):
    features=arrays['features'];families=arrays['selector_families']
    assert set(arrays)=={'features','packet_scores','selector_families'}
    assert features.shape==(8,4,22,85,21) and arrays['packet_scores'].shape==(8,4,22,11,2,16,16)
    assert families.shape==(8,4,22,4) and [p['index'] for p in proofs]==list(INDICES)
    groups=[]
    for ci,(role,kind) in enumerate(CASES):
        for fi,(generation,phase,step,field) in enumerate(LABELS):
            values=features[:,:,ci,fi]
            groups.append(dict(role=role,kind=kind,generation=generation,phase=phase,step=step,field=field,
                statistics={k:aggregate(values[:,:,i]) for i,k in enumerate(METRICS)}))
    changes=[]
    for ci,(role,kind) in enumerate(CASES):
        for g in (1,2,3):
            edges=[('routing',(g,'packet',0,'incoming'),(g,'packet',0,'routed')),
                ('write_R_start_to_1',(g,'write',0,'R'),(g,'write',1,'R')),
                ('write_R_1_to_300',(g,'write',1,'R'),(g,'write',300,'R')),
                ('write_R_300_to_1000',(g,'write',300,'R'),(g,'write',1000,'R')),
                ('read_R_100_to_300',(g,'read',100,'R'),(g,'read',300,'R')),
                ('read_V_100_to_300',(g,'read',100,'V'),(g,'read',300,'V'))]
            for name,start,end in edges:
                delta=features[:,:,ci,LABELS.index(end)]-features[:,:,ci,LABELS.index(start)]
                changes.append(dict(role=role,kind=kind,generation=g,segment=name,statistics={k:aggregate(delta[:,:,METRICS.index(k)])
                    for k in ('canonical_own','best_own','family_margin','best_mse','address_gap','qualified_preference')}))
    selections=[]
    for ci,(role,kind) in enumerate(CASES):
        for g in range(4):
            observed=families[:,:,ci,g]
            selections.append(dict(role=role,kind=kind,generation=g+1,counts={str(k):int((observed==k).sum()) for k in (-2,-1,0,1)},
                block_counts=[{str(k):int((row==k).sum()) for k in (-2,-1,0,1)} for row in observed]))
    lineage=[];ci=CASES.index((1,'learned'))
    # Descriptive chronology, all 32 B lineages, never conditioned/excluded by failure.
    chronological=[]
    for g in (1,2,3,4):
        chronological.extend(i for i,x in enumerate(LABELS) if x[0]==g and x[3]!='outgoing')
        if g<4:chronological.append(LABELS.index((g,'packet',0,'outgoing')))
    for bi,index in enumerate(INDICES):
        for life in range(4):
            sequence=[]
            for fi in chronological:
                row=features[bi,life,ci,fi]
                sequence.append(dict(checkpoint=list(LABELS[fi]),ideal_family=int(row[METRICS.index('ideal_family')]),
                    best_B=float(row[METRICS.index('best_own')]),best_A=float(row[METRICS.index('best_other')]),
                    canonical_B=float(row[METRICS.index('canonical_own')]),family_margin=float(row[METRICS.index('family_margin')])))
            # Separate representations. Never count random new births as loss of an established pattern.
            crossings={}
            for representation in ('packet','V','R','theta'):
                eligible=[x for x in sequence if x['checkpoint'][1]=='packet' and representation=='packet' or
                    x['checkpoint'][3]==representation and (x['checkpoint'][1]=='read' and x['checkpoint'][2]==300 or
                    x['checkpoint'][1]=='write' and x['checkpoint'][2]>0)]
                first=next((i for i,x in enumerate(eligible) if x['ideal_family']==0),None)
                crossings[representation]=dict(first_A_dominant=None if first is None else eligible[first]['checkpoint'],
                    previous_same_representation=None if first in (None,0) else eligible[first-1]['checkpoint'])
            lineage.append(dict(index=index,life=life,actual_families=families[bi,life,ci].tolist(),
                first_A_dominance_by_representation=crossings,chronology=sequence))
    return dict(schema='l20_renewal_fidelity_audit_v1',decision='D133',status='DESCRIPTIVE_AUDIT_COMPLETE',
        source_run=SOURCE_RUN,post_hoc=True,independent_confirmation=False,new_trajectories=0,new_reader_paths=0,
        fitted_decoder=False,static_analyst_template_access=True,reader_rescue_demonstrated=False,
        blocks=8,lives_per_block=4,fields=59840,packet_fields=7744,packet_correlations=3964928,
        checked_chain_and_backup_selectors=2368,original_extra_probe_selectors_not_rechecked=128,
        metrics=list(METRICS),cases=[list(x) for x in CASES],checkpoints=[list(x) for x in LABELS],
        packet_positions=list(PACKET_POSITIONS),tie_atol=ATOL,intervals=None,qualification_gate=None,
        groups=groups,changes=changes,selections=selections,learned_B_lineages=lineage,
        check_maxima={k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith('_max_abs')},
        source_renewal_verdict_unchanged=True,law_status='MIXED',automatic_successor=False,
        limitations=['static best alignment is not functional reader rescue',
            'residual template deviation is not total information loss',
            'checkpoint chronology is not a causal intervention or exact unsaved transition time',
            'patterns, frame and one learned host guide remain supplied/fixed',
            'reference/body amplitudes are not interchangeable performance scores'])


def analyze(root):
    panels=[];proofs=[]
    for index in INDICES:
        arrays,proof=analyze_panel(index,*load_panel(index,root));panels.append(arrays);proofs.append(proof)
    arrays={k:np.stack([a[k] for a in panels]) for k in panels[0]}
    return arrays,summarize(arrays,proofs),proofs


def source_inputs(root):
    """Flat sealed source closure; imports no simulator and runs no ancestor."""
    u,_=io_helpers();run=root/'runs'/SOURCE_RUN;out=root/'outputs'/SOURCE_RUN
    assert sha256_file(run/'COMPLETE.json')==SOURCE_COMPLETE
    complete,manifest=u.read_json(run/'COMPLETE.json'),u.read_json(run/'MANIFEST.json')
    assert complete['status']=='COMPLETE' and u.read_json(run/'STATUS.json')==complete
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert manifest['environment']==environment_manifest() and sha256_file(run/'MANIFEST.json')==complete['manifest_sha256']
    inputs=[Path(x) for x in manifest['input_sha256']];outputs=[Path(x) for x in complete['output_sha256']]
    assert len(inputs)==840 and len(outputs)==19
    assert u.hashes(inputs)==manifest['input_sha256'] and u.hashes(outputs)==complete['output_sha256']
    assert sha256_file(out/'output_hashes.sha256')==complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text()==u.hash_text(complete['output_sha256'])
    assert {str(x) for x in out.iterdir()}==set(complete['output_sha256'])|{str(out/'output_hashes.sha256')}
    paths=inputs+outputs+[run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]
    paths += [out/'output_hashes.sha256',WS/'reviews/L20_GUIDE_RENEWAL_2026-09-16.md',*[WS/n for n in SCIENCE]]
    return sorted(set(paths))


def test_report(path,root):
    u,_=io_helpers();path=u.require_beneath(path,root/'logs')
    assert path.name.startswith('d133_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    current=[c for c in cases if c.get('classname','').endswith('test_l20_renewal_fidelity')]
    names={c.get('name','').split('[',1)[0] for c in current}
    assert len(current)>=50 and {'test_all_ideal_shifts','test_constant_convention','test_corruption',
        'test_independent_features','test_disposable_panel','test_no_dynamics','test_source_hashes',
        'test_summary','test_external_roundtrip','test_resource_guards','test_reservation_guard',
        'test_long_forecast_guard','test_selector_reconstruction','test_shape_and_address_decomposition',
        'test_field_coverage','test_lineage_corruption','test_detachment_guard'}<=names
    assert {c.get('name') for c in current if c.get('name','').startswith('test_all_ideal_shifts[')}=={
        f'test_all_ideal_shifts[{i}]' for i in range(256)}
    duration=max(float(c.get('time','0')) for c in current if c.get('name')=='test_disposable_panel')
    return dict(path=str(path),tests=len(cases),new_tests=len(current),failed=0,skipped=0,
        disposable_panel_seconds=duration,forecast_seconds=32*duration+120)


def inputs_checked(root,report):
    u,_=io_helpers();return u.hashes(source_inputs(root)+[report])


def execution_guard(root,required):
    if required and DETACHED_ENV not in os.environ:raise AssertionError('long audit requires detached execution')
    if DETACHED_ENV in os.environ:
        log=str(root/'logs'/f'{RUN_ID}.log')
        assert os.environ[DETACHED_ENV]==log and os.getpid()==os.getsid(0)
        assert os.readlink('/proc/self/fd/0')=='/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd))==log for fd in (1,2))


def saved_check(root,complete=True):
    u,preflight=io_helpers();preflight(root,False);directory=root/'outputs'/RUN_ID
    assert {p.name for p in directory.iterdir()}==set(OUTPUTS)|({'COMPLETE.json'} if complete else set())
    inputs=u.read_json(directory/'INPUTS.json');report=Path(inputs['test_proof']['path'])
    assert inputs['input_sha256']==inputs_checked(root,report)
    assert inputs['test_proof']==test_report(report,root) and inputs['environment']==environment_manifest()
    arrays=u.load_npz(directory/'features.npz');summary=u.read_json(directory/'summary.json');proofs=u.read_json(directory/'verification.json')
    expected,result,checks=analyze(root)
    assert set(arrays)==set(expected)
    for key in arrays:np.testing.assert_array_equal(arrays[key],expected[key])
    assert summary==result and proofs==checks
    if complete:
        marker=u.read_json(directory/'COMPLETE.json')
        assert marker['status']=='COMPLETE' and marker['new_trajectories']==0 and marker['automatic_successor'] is False
        assert marker['output_sha256']==u.hashes([directory/n for n in OUTPUTS])
        assert marker['output_bytes_without_sentinel']==sum((directory/n).stat().st_size for n in OUTPUTS)
        assert sum(p.stat().st_size for p in directory.iterdir())<BUDGET
    return dict(passes=True,fields=59840,packet_fields=7744,correlations=3964928,selectors=2368,
        input_hashes=len(inputs['input_sha256']),output_hashes=4 if complete else 0,
        check_maxima=summary['check_maxima'],new_trajectories=0,fitted_decoder=False)


def execute(root,report):
    u,preflight=io_helpers();preflight(root);proof=test_report(report,root)
    execution_guard(root,proof['forecast_seconds']>600)
    directory=root/'outputs'/RUN_ID
    if directory.exists():raise FileExistsError('single-use audit identity already exists')
    inputs=inputs_checked(root,report);directory.mkdir();start=time.monotonic()
    try:
        u.write_json(directory/'INPUTS.json',dict(started_utc=utc_now(),input_sha256=inputs,test_proof=proof,
            environment=environment_manifest(),git_head=git_head(WS),post_hoc=True,known_outcomes=True,
            new_trajectories=0,new_reader_paths=0,fitted_decoder=False,workers=1,cpu_affinity=preflight(root),
            output_budget=BUDGET,protocol=SCIENCE[-1],source_complete_sha256=SOURCE_COMPLETE,
            detached=DETACHED_ENV in os.environ,log=os.environ.get(DETACHED_ENV),pid=os.getpid()),root)
        arrays,summary,verification=analyze(root)
        u.write_npz(directory/'features.npz',arrays,root);u.write_json(directory/'summary.json',summary,root)
        u.write_json(directory/'verification.json',verification,root)
        checked=saved_check(root,False);size=sum(p.stat().st_size for p in directory.iterdir())
        assert size+65536<BUDGET and inputs==inputs_checked(root,report);preflight(root,False)
        complete=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            output_sha256=u.hashes([directory/n for n in OUTPUTS]),output_bytes_without_sentinel=size,
            new_trajectories=0,automatic_successor=False,saved_audit=checked)
        u.write_json(directory/'COMPLETE.json',complete,root)
        print(json.dumps({k:complete[k] for k in ('status','elapsed_seconds','output_bytes_without_sentinel','saved_audit')},indent=2),flush=True)
    except Exception as error:u.failure(directory,error,root);raise


def detach(root,report):
    u,preflight=io_helpers();preflight(root);test_report(report,root);inputs_checked(root,report)
    if (root/'outputs'/RUN_ID).exists():raise FileExistsError('single-use identity exists')
    (root/'tmp'/f'{RUN_ID}_launch.lock').mkdir();log=root/'logs'/f'{RUN_ID}.log'
    env=os.environ.copy();env[DETACHED_ENV]=str(log)
    command=[sys.executable,str(WS/SCIENCE[0]),'--external-root',str(root),'--execute','--test-report',str(report)]
    with log.open('xb') as handle:
        child=subprocess.Popen(command,cwd=WS,env=env,stdin=subprocess.DEVNULL,stdout=handle,
            stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',pid=child.pid,log=str(log),user_polls=True,automatic_polling=False)),flush=True)


def main():
    if sys.flags.optimize:raise RuntimeError('assertions must remain enabled')
    from laws_confirmation.io import external_root
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--external-root',type=Path,default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument('--test-report',type=Path);mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('execute','audit','detach'):mode.add_argument('--'+name,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    if (args.execute or args.detach)!=(args.test_report is not None):parser.error('--test-report required only for execute/detach')
    if args.execute:execute(root,args.test_report)
    elif args.detach:detach(root,args.test_report)
    else:print(json.dumps(saved_check(root),indent=2))


if __name__=='__main__':main()
