"""D138: retained D137 correction persistence; static audit, no new dynamics."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
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
RUN_ID='l20_handoff_persistence_audit_v1_attempt1'
SOURCE_RUN='l20_reference_handoff_v1_attempt1'
SOURCE_COMPLETE='1deb0c68b262fcaf2db36a851a4917b488ff1b5c31eac571a6032574a2d8f199'
GUIDE_SHA='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
SCIENCE=('scripts/audit_l20_handoff_persistence.py','tests/test_l20_handoff_persistence.py',
    'scripts/run_l20_handoff_persistence.sh','protocols/L20_HANDOFF_PERSISTENCE_AUDIT_V1.md')
INDICES=tuple(range(76000,76008));DISPOSABLE=514237
MODES=('reference','matched','history','dose')
CASES=tuple((r,m) for r in (0,1) for m in MODES)
KINDS=MODES+tuple(m+'_'+k for k in ('pre_shuffle','post_shuffle','off','wrong') for m in MODES)+('ideal','zero')
PROBES=tuple((r,k) for r in (0,1) for k in KINDS)
PAIRS=(('matched','reference'),('history','dose'),('history','reference'),('dose','reference'),('matched','history'))
WRITE_TIMES=(0,1,300,1000);READ_TIMES=(0,1,100,300)
LABELS=tuple((g,phase,t,f) for g in (1,2,3) for phase,t,f in
    [('write',t,f) for t in WRITE_TIMES for f in ('V','EMA','R','theta')]+
    [('packet',0,f) for f in ('raw','routed')]+
    [('read',t,f) for t in READ_TIMES for f in ('V','EMA','R')])
PACKET_POSITIONS=tuple(i for i,x in enumerate(LABELS) if x[1]=='packet')
READ_KEYS=('targets','guide','source_starts','source_shifts','source_births','direct_birth','histories','handoff_starts',
    'source_states','written_fields','permutations','inputs','packets','scores','states','values')
BETA=.998**300;ATOL=1e-12;BUDGET=128*1024**2
OUTPUTS=('INPUTS.json','features.npz','summary.json','verification.json')
DETACHED_ENV='L20_HANDOFF_PERSISTENCE_DETACHED_LOG'
spec=importlib.util.spec_from_file_location('d138_static_prior',WS/'scripts/audit_l20_serial_fidelity.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
targets,encode,decode,project,move=prior.targets,prior.encode,prior.decode,prior.project,prior.move
normalize,correlations,fft_correlations=prior.normalize,prior.correlations,prior.fft_correlations
field_features,check_features,select,nested=prior.field_features,prior.check_features,prior.select,prior.nested
METRICS=prior.METRICS
DELTA_METRICS=('canonical_own','best_own','best_other','family_margin','best_mse','address_gap','qualified_preference')
DISTANCES=('raw_rms','standardized_rms','correlation','mean_delta','std_delta','identical','both_constant','one_constant')
OBSERVERS=('own_qualified','other_qualified','own_sign','other_sign')

def io_helpers():return prior.io_helpers()

def load_panel(index,root=DEFAULT_EXTERNAL_ROOT):
    if type(index) is not int or index not in INDICES+(DISPOSABLE,):raise ValueError('retained source identity required')
    d=root/('tmp' if index==DISPOSABLE else 'outputs')/(SOURCE_RUN+'_benchmark' if index==DISPOSABLE else SOURCE_RUN)
    with np.load(d/f'block_{index}.npz',allow_pickle=False) as z:raw={k:z[k] for k in READ_KEYS}
    meta=json.loads((d/f'block_{index}.json').read_text())
    validate_panel(index,raw,meta);return raw,meta

def validate_panel(index,raw,meta):
    assert type(index) is int and index in INDICES+(DISPOSABLE,) and meta['index']==index
    assert set(raw)==set(READ_KEYS) and set(meta)=={'index','config','source_sha256','lives'}
    cfg=dict(lives=4,steps=300,norm=.3,amp_threshold=.2)
    nested(meta['config'],cfg);assert len(meta['lives'])==4
    shapes=dict(targets=(4,2,16,16),guide=(4,2,16,16),source_starts=(4,2,3,3,16,16),
        source_shifts=(4,3,2),source_births=(4,2,3,16,16),direct_birth=(4,2,3,16,16),
        histories=(4,2,3,16,16),handoff_starts=(4,2,3,4,3,16,16),
        source_states=(4,2,3,4,4,4,16,16),written_fields=(4,2,3,4,16,16),
        permutations=(4,2,3,256),inputs=(4,44,3,2048),packets=(4,44,3,2048),
        scores=(4,44,3,2,16,16),states=(4,44,3,4,3,16,16),values=(4,44,3,4,12))
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('inputs','packets') else np.int64 if k in ('source_shifts','permutations') else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    for life,m in enumerate(meta['lives']):
        assert m['index']==index and m['life']==life and m['tag']=='l20-reference-handoff-v1' and m['beta']==BETA
        assert m['source_index']==(514235 if index==DISPOSABLE else index-1000)
        assert m['writer_index']==(514232 if index==DISPOSABLE else index-3000)
        nested(m['config'],cfg);nested(m['cases'],[list(c) for c in PROBES]);nested(m['modes'],list(MODES))
        assert m['times']==list(READ_TIMES) and m['source_times']==list(WRITE_TIMES)
        assert m['guide_sha256']==hashlib.sha256(raw['guide'][life].astype('<f8').tobytes()).hexdigest()==GUIDE_SHA
        np.testing.assert_array_equal(raw['targets'][life],targets())
        for k in ('source_noise_reused','source_starts_reused','reference_exact_replay'):assert m[k] is True
        for k in ('fresh_founders','new_renewal_cohort','guide_refitted','latent_theta_transmitted','target_labels_in_writer'):assert m[k] is False
        assert m['writer_rule']=='project(tanh(R_final), .3)' and m['writer_inputs']==['R_final']
        assert (m['packet_bytes'],m['public_guide_bytes'])==(2048,4096)
        replay=m['replay'];assert replay['full_life_replay'] is True
        assert (replay['known_source_writers'],replay['new_handoff_writers'],replay['reader_paths'],replay['selector_decisions'])==(6,18,132,120)

def packet_fields(raw):
    return np.stack([raw[k].copy().view('<f8').reshape(4,44,3,16,16) for k in ('inputs','packets')],axis=3)

def fields_panel(raw):
    packets=packet_fields(raw);columns=[]
    for g,phase,t,f in LABELS:
        if phase=='write':
            ti,fi=WRITE_TIMES.index(t),('V','EMA','R','theta').index(f)
            value=np.stack([raw['source_states'][:,r,g-1,MODES.index(m),ti,fi] for r,m in CASES],axis=1)
        elif phase=='read':
            ti,fi=READ_TIMES.index(t),('V','EMA','R').index(f)
            value=raw['states'][:,[PROBES.index(c) for c in CASES],g-1,ti,fi]
        else:value=packets[:,[PROBES.index(c) for c in CASES],g-1,('raw','routed').index(f)]
        columns.append(value)
    a=np.stack(columns,axis=2);assert a.shape==(4,8,90,16,16);return a

def check_lineage(raw,meta):
    maximum=first=handoff_error=0.;selectors=aliases=0
    families=np.full((4,44,3),-2,dtype=np.int64)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for life,m in enumerate(meta['lives']):
        for role in (0,1):
            for g in range(3):
                ref=raw['source_starts'][life,role,g,2];birth=raw['source_births'][life,role,g]
                direct=BETA*birth;history=ref-direct
                np.testing.assert_array_equal(raw['direct_birth'][life,role,g],direct)
                np.testing.assert_array_equal(raw['histories'][life,role,g],history)
                assert min(ref.std(),history.std())>1e-9
                handoff_error=max(handoff_error,float(abs(history+direct-ref).max()))
                refs=(ref,(history-history.mean())*(ref.std()/history.std())+ref.mean(),
                    history,(ref-ref.mean())*(history.std()/ref.std())+history.mean())
                writers=m['writers'][role][g]
                assert len(writers)==4 and len({w['noise_rng'] for w in writers})==1
                for mi in range(4):
                    h=raw['source_starts'][life,role,g].copy();h[2]=refs[mi]
                    np.testing.assert_array_equal(raw['handoff_starts'][life,role,g,mi],h)
                    path=raw['source_states'][life,role,g,mi]
                    np.testing.assert_array_equal(path[0],np.concatenate((h,np.zeros((1,16,16)))))
                    field=project(np.tanh(path[-1,2]))
                    np.testing.assert_array_equal(raw['written_fields'][life,role,g,mi],field)
                    first=max(first,float(abs(path[1,3]-project(np.tanh(path[1,2]))).max()))
                    np.testing.assert_allclose(path[1:,3].mean(axis=(1,2)),0,rtol=0,atol=ATOL)
                    np.testing.assert_allclose(path[1:,3].std(axis=(1,2)),.3,rtol=0,atol=ATOL)
                    w=writers[mi]
                    assert w['mode']=='aligned' and w['theta_start_zero'] is True and w['theta_writing'] is True
                    assert (w['gain'],w['rho'],w['lam'],w['sigma'])==(.2,.002,.001,.3)
                    assert w['shift']==raw['source_shifts'][life,g].tolist()
                    assert all(w[k] is False for k in ('incoming_packet_access','guide_access','target_labels'))
        for ci,(role,kind) in enumerate(PROBES):
            for g in range(3):
                perm=raw['permutations'][life,role,g]
                key=hashlib.sha256(f'l20-reference-handoff-v1:{m["index"]}:{life}:g{g+1}:shuffle:{role}'.encode()).digest()
                expected_perm=np.random.Generator(np.random.PCG64(int.from_bytes(key[:16],'little'))).permutation(256)
                np.testing.assert_array_equal(perm,expected_perm)
                shuffle=lambda b:encode(decode(b).ravel()[perm].reshape(16,16))
                if kind in ('ideal','zero'):
                    incoming=encode(project(np.tanh(1.5*targets()[role]))) if kind=='ideal' else bytes(2048)
                    delivered=incoming;scores=np.zeros((2,16,16));entry=None
                else:
                    mi=next(i for i,arm in enumerate(MODES) if kind==arm or kind.startswith(arm+'_'))
                    rr=1-role if kind.endswith('_wrong') else role
                    incoming=encode(raw['written_fields'][life,rr,g,mi])
                    if kind.endswith('_pre_shuffle'):incoming=shuffle(incoming)
                    delivered,scores,entry=select(incoming,raw['guide'][life]);selectors+=1
                    families[life,ci,g]=entry['inferred_family']
                    if kind.endswith('_post_shuffle'):delivered=shuffle(delivered)
                assert raw['inputs'][life,ci,g].tobytes()==incoming
                assert raw['packets'][life,ci,g].tobytes()==delivered
                nested(m['selectors'][ci][g],entry)
                maximum=max(maximum,float(abs(scores-raw['scores'][life,ci,g]).max()))
                rm=m['readers'][ci][g]
                assert rm['input_sha256']==sha(delivered) and rm['enabled']==(not kind.endswith('_off'))
                assert rm['writing'] is False and rm['gain']==0. and rm['target_labels'] is False
                assert rm['packet_bytes']==2048 and rm['backup_sha256'] is None and rm['extra_backup_bytes']==0
                birth=raw['states'][life,ci,g,0]
                for field in range(3):np.testing.assert_array_equal(birth[field],raw['states'][life,0,g,0,0])
        for role in (0,1):
            for arm in MODES:
                for a,b in (((role,arm+'_off'),(role,'zero')),((role,arm+'_wrong'),(1-role,arm))):
                    np.testing.assert_array_equal(raw['states'][life,PROBES.index(a)],raw['states'][life,PROBES.index(b)])
                    aliases+=3
        np.testing.assert_array_equal(raw['states'][life,PROBES.index((0,'zero'))],raw['states'][life,PROBES.index((1,'zero'))]);aliases+=3
    assert selectors==480 and aliases==204 and max(maximum,first,handoff_error)<=ATOL
    v=raw['states'][...,0,:,:]
    role=np.asarray([r for r,_ in PROBES])
    own=(v>0)==(targets()[role][None,:,None,None]>0)
    other=(v>0)==(targets()[1-role][None,:,None,None]>0)
    values=np.stack(((own&(abs(v)>.2)).mean(axis=(-2,-1)),(other&(abs(v)>.2)).mean(axis=(-2,-1)),
        own.mean(axis=(-2,-1)),other.mean(axis=(-2,-1))),axis=-1)
    np.testing.assert_array_equal(values,raw['values'][...,:4])
    return families,values,dict(selector_decisions=selectors,selector_max_abs=maximum,first_projection_max_abs=first,
        handoff_max_abs=handoff_error,source_observer_max_abs=0.,record_reconstructions=96,erased_writer_births=96,
        exact_reader_aliases=aliases,packet_lineage=True)

def pair_distance(left,right):
    if left.shape!=right.shape:raise ValueError('paired same-shape fields required')
    x,sx=normalize(left);y,sy=normalize(right)
    return np.stack((np.sqrt(((left-right)**2).mean(axis=(1,2))),np.sqrt(((x-y)**2).mean(axis=(1,2))),
        (x*y).mean(axis=(1,2)),left.mean(axis=(1,2))-right.mean(axis=(1,2)),sx-sy,
        (left==right).all(axis=(1,2)).astype(float),((sx==0)&(sy==0)).astype(float),
        ((sx==0)^(sy==0)).astype(float)),axis=1)

def check_distance(left,right,actual):
    assert actual.shape==(len(left),8) and np.isfinite(actual).all()
    def standard(a):
        c=a-np.mean(a,axis=(1,2),keepdims=True);res=c-c.mean(axis=(1,2),keepdims=True)
        sd=np.sqrt((res*res).mean(axis=(1,2)))
        q=np.zeros_like(c);np.divide(c,sd[:,None,None],out=q,where=sd[:,None,None]!=0)
        return q,sd
    a,sa=standard(left);b,sb=standard(right);d=left-right
    expected=np.stack((np.linalg.norm(d.reshape(len(left),-1),axis=1)/16,
        np.linalg.norm((a-b).reshape(len(left),-1),axis=1)/16,np.sum(a*b,axis=(1,2))/256,
        np.sum(left,axis=(1,2))/256-np.sum(right,axis=(1,2))/256,sa-sb,
        np.count_nonzero(d,axis=(1,2))==0,(sa==0)&(sb==0),(sa==0)^(sb==0)),axis=1)
    error=float(abs(actual-expected).max());assert error<=ATOL;return error

def analyze_panel(index,raw,meta):
    validate_panel(index,raw,meta);families,observers,proof=check_lineage(raw,meta)
    focused=fields_panel(raw);packets=packet_fields(raw)
    def extract(fields,roles):
        flat=fields.reshape(-1,16,16);rs=np.broadcast_to(roles,fields.shape[:-2]).ravel().copy()
        scores=correlations(flat,targets());other=fft_correlations(flat,targets())
        error=float(abs(scores-other).max());assert error<=ATOL
        features=field_features(flat,rs,scores);checked=check_features(flat,rs,other,features)
        return features.reshape(fields.shape[:-2]+(21,)),scores.reshape(fields.shape[:-2]+(2,16,16)),error,checked
    features,_,error,ferror=extract(focused,np.repeat(np.arange(2,dtype=np.int64),4)[None,:,None])
    pf,ps,error2,ferror2=extract(packets,np.repeat(np.arange(2,dtype=np.int64),22)[None,:,None,None])
    distances=[];derror=0.
    for role in (0,1):
        rows=[]
        for left,right in PAIRS:
            a=focused[:,CASES.index((role,left))].reshape(-1,16,16)
            b=focused[:,CASES.index((role,right))].reshape(-1,16,16)
            d=pair_distance(a,b);derror=max(derror,check_distance(a,b,d));rows.append(d.reshape(4,90,8))
        distances.append(np.stack(rows,axis=1))
    distances=np.stack(distances,axis=1)
    invariance=0.
    stable=[METRICS.index(k) for k in ('mean','std','row_power','column_power','best_own','best_other','family_margin','best_mse')]
    for pi,(_,kind) in enumerate(PROBES):
        if not kind.endswith('_post_shuffle'):
            invariance=max(invariance,float(abs(pf[:,pi,:,0][:,:,stable]-pf[:,pi,:,1][:,:,stable]).max()))
    assert invariance<=ATOL
    for ci,c in enumerate(CASES):
        for g in (1,2,3):
            for si,k in enumerate(('raw','routed')):
                np.testing.assert_allclose(features[:,ci,LABELS.index((g,'packet',0,k))],pf[:,PROBES.index(c),g-1,si],atol=ATOL,rtol=0)
    proof.update(index=index,fields=2880,packet_fields=1056,unique_fields=3744,feature_evaluations=3936,
        correlation_max_abs=max(error,error2),feature_max_abs=max(ferror,ferror2),distance_max_abs=derror,
        route_invariance_max_abs=invariance,new_trajectories=0)
    return dict(features=features,packet_features=pf,packet_scores=ps,selector_families=families,
        distances=distances,reader_observers=observers),proof

def aggregate(a,signed=False):
    assert a.shape==(8,4) and np.isfinite(a).all();blocks=a.mean(axis=1)
    result=dict(mean=float(a.mean()),minimum=float(a.min()),maximum=float(a.max()),block_means=blocks.tolist())
    if signed:result.update(life_values=a.tolist(),life_positive=int((a>ATOL).sum()),life_negative=int((a<-ATOL).sum()),
        life_tied=int((abs(a)<=ATOL).sum()),block_positive=int((blocks>ATOL).sum()),block_negative=int((blocks<-ATOL).sum()),
        block_tied=int((abs(blocks)<=ATOL).sum()),numerical_zero_atol=ATOL)
    return result

def trace_labels(g):
    return tuple((g,'write',t,'R') for t in WRITE_TIMES)+((g,'packet',0,'raw'),(g,'packet',0,'routed'),(g,'read',300,'V'))

def summarize(arrays,proofs):
    f=arrays['features'];pf=arrays['packet_features'];d=arrays['distances'];obs=arrays['reader_observers']
    assert f.shape==(8,4,8,90,21) and d.shape==(8,4,2,5,90,8)
    groups=[];packets=[];paired=[];segments=[];readouts=[];paths=[];selections=[]
    stat=lambda a,metrics,signed:{k:aggregate(a[:,:,j],signed) for j,k in enumerate(metrics)}
    for ci,(role,mode) in enumerate(CASES):
        for fi,label in enumerate(LABELS):
            groups.append(dict(role=role,mode=mode,checkpoint=list(label),statistics=stat(f[:,:,ci,fi],METRICS,False)))
    for pi,(role,kind) in enumerate(PROBES):
        for g in range(3):
            family=arrays['selector_families'][:,:,pi,g]
            counts=lambda x:{str(k):int((x==k).sum()) for k in (-2,-1,0,1)}
            selections.append(dict(role=role,kind=kind,generation=g+1,counts=counts(family),
                block_counts=[counts(x) for x in family]))
            for si,position in enumerate(('raw','routed')):
                packets.append(dict(role=role,kind=kind,generation=g+1,position=position,
                    statistics=stat(pf[:,:,pi,g,si],METRICS,False)))
            readouts.append(dict(role=role,kind=kind,generation=g+1,step=300,
                statistics=stat(obs[:,:,pi,g,-1],OBSERVERS,False)))
    cols=[METRICS.index(k) for k in DELTA_METRICS]
    for role in (0,1):
        for pair,(left,right) in enumerate(PAIRS):
            li,ri=CASES.index((role,left)),CASES.index((role,right))
            diff=f[:,:,li]-f[:,:,ri]
            for fi,label in enumerate(LABELS):
                paired.append(dict(role=role,left=left,right=right,checkpoint=list(label),
                    statistics=stat(diff[:,:,fi][:,:,cols],DELTA_METRICS,True),
                    distances=stat(d[:,:,role,pair,fi],DISTANCES,True)))
            for g in (1,2,3):
                points=trace_labels(g);ids=[LABELS.index(x) for x in points]
                for ai,bi in tuple(zip(ids[:-1],ids[1:]))+((ids[0],ids[-1]),):
                    segments.append(dict(role=role,left=left,right=right,generation=g,start=list(LABELS[ai]),end=list(LABELS[bi]),
                        statistics=stat((diff[:,:,bi]-diff[:,:,ai])[:,:,cols],DELTA_METRICS,True)))
                np.testing.assert_allclose(sum(diff[:,:,ids[j+1]]-diff[:,:,ids[j]] for j in range(6)),
                    diff[:,:,ids[-1]]-diff[:,:,ids[0]],rtol=0,atol=ATOL)
        li,ri=CASES.index((role,'matched')),CASES.index((role,'reference'))
        for g in (1,2,3):
            for block,index in enumerate(INDICES):
                for life in range(4):
                    rows=[]
                    for label in trace_labels(g):
                        fi=LABELS.index(label)
                        rows.append(dict(checkpoint=list(label),
                            reference={k:float(f[block,life,ri,fi,METRICS.index(k)]) for k in DELTA_METRICS},
                            matched={k:float(f[block,life,li,fi,METRICS.index(k)]) for k in DELTA_METRICS},
                            distance={k:float(d[block,life,role,0,fi,j]) for j,k in enumerate(DISTANCES)}))
                    paths.append(dict(index=index,life=life,role=role,source_stage=g,checkpoints=rows))
    return dict(schema='l20_handoff_persistence_audit_v1',decision='D138',status='DESCRIPTIVE_AUDIT_COMPLETE',
        source_run=SOURCE_RUN,post_hoc=True,independent_confirmation=False,new_trajectories=0,new_reader_paths=0,
        fitted_decoder=False,static_analyst_template_access=True,reader_rescue_demonstrated=False,
        blocks=8,lives_per_block=4,fields=23040,packet_fields=8448,unique_fields=29952,feature_evaluations=31488,
        overlapping_packet_fields=1536,packet_correlations=4325376,checked_selectors=3840,
        metrics=list(METRICS),paired_metrics=list(DELTA_METRICS),distance_metrics=list(DISTANCES),observer_metrics=list(OBSERVERS),
        cases=[list(x) for x in CASES],probes=[list(x) for x in PROBES],pairs=[list(x) for x in PAIRS],checkpoints=[list(x) for x in LABELS],
        tie_atol=ATOL,intervals=None,qualification_gate=None,causal_stage_allocation=False,serial_lineage=False,
        groups=groups,packet_groups=packets,paired_checkpoints=paired,paired_segments=segments,readouts=readouts,correction_paths=paths,selections=selections,
        check_maxima={k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith('_max_abs')},
        source_verdict='REFERENCE_HANDOFF_EFFECT_UNRESOLVED',source_verdict_unchanged=True,law_status='MIXED',automatic_successor=False,
        limitations=['static target fit is not reader performance','small state distance is not proof of equivalent function',
            'constant-field correlations are zero with explicit flags, not perfect matches',
            'checkpoint changes are descriptive, not causal loss fractions or unsaved transition times',
            'three saved source stages are separate interventions, not a corrected serial lineage',
            'archived birth state and fixed supplied patterns/public guide remain analyst assistance'])

def check_summary(summary,arrays,proofs):
    """Restated indices/arithmetic, without calling any summary/aggregation helper."""
    expected_shapes=dict(features=(8,4,8,90,21),packet_features=(8,4,44,3,2,21),packet_scores=(8,4,44,3,2,2,16,16),
        selector_families=(8,4,44,3),distances=(8,4,2,5,90,8),reader_observers=(8,4,44,3,4,4))
    assert set(arrays)==set(expected_shapes) and [x['index'] for x in proofs]==list(INDICES)
    for key,shape in expected_shapes.items():assert arrays[key].shape==shape and np.isfinite(arrays[key]).all()
    assert np.isin(arrays['selector_families'],(-2,-1,0,1)).all()
    f=arrays['features'];pf=arrays['packet_features'];dist=arrays['distances'];obs=arrays['reader_observers']
    fixed=dict(schema='l20_handoff_persistence_audit_v1',decision='D138',status='DESCRIPTIVE_AUDIT_COMPLETE',
        source_run=SOURCE_RUN,post_hoc=True,independent_confirmation=False,new_trajectories=0,new_reader_paths=0,
        fitted_decoder=False,static_analyst_template_access=True,reader_rescue_demonstrated=False,
        blocks=8,lives_per_block=4,fields=23040,packet_fields=8448,unique_fields=29952,feature_evaluations=31488,
        overlapping_packet_fields=1536,packet_correlations=4325376,checked_selectors=3840,
        metrics=list(METRICS),paired_metrics=list(DELTA_METRICS),distance_metrics=list(DISTANCES),observer_metrics=list(OBSERVERS),
        cases=[list(x) for x in CASES],probes=[list(x) for x in PROBES],pairs=[list(x) for x in PAIRS],checkpoints=[list(x) for x in LABELS],
        tie_atol=ATOL,intervals=None,qualification_gate=None,causal_stage_allocation=False,serial_lineage=False,
        check_maxima={k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith('_max_abs')},
        source_verdict='REFERENCE_HANDOFF_EFFECT_UNRESOLVED',source_verdict_unchanged=True,law_status='MIXED',automatic_successor=False,
        limitations=['static target fit is not reader performance','small state distance is not proof of equivalent function',
            'constant-field correlations are zero with explicit flags, not perfect matches',
            'checkpoint changes are descriptive, not causal loss fractions or unsaved transition times',
            'three saved source stages are separate interventions, not a corrected serial lineage',
            'archived birth state and fixed supplied patterns/public guide remain analyst assistance'])
    assert set(summary)==set(fixed)|{'groups','packet_groups','paired_checkpoints','paired_segments','readouts','correction_paths','selections'}
    for key,value in fixed.items():nested(summary[key],value)
    def stats(a,signed=False):
        assert a.shape==(8,4);rows=a.tolist();flat=[x for row in rows for x in row];means=[sum(row)/4 for row in rows]
        result=dict(mean=sum(means)/8,minimum=min(flat),maximum=max(flat),block_means=means)
        if signed:result.update(life_values=rows,life_positive=sum(x>ATOL for x in flat),life_negative=sum(x<-ATOL for x in flat),
            life_tied=sum(abs(x)<=ATOL for x in flat),block_positive=sum(x>ATOL for x in means),block_negative=sum(x<-ATOL for x in means),
            block_tied=sum(abs(x)<=ATOL for x in means),numerical_zero_atol=ATOL)
        return result
    def check_row(row,header,a,metrics=METRICS,signed=False,extra=None):
        assert set(row)==set(header)|{'statistics'}|({'distances'} if extra is not None else set())
        for key,value in header.items():nested(row[key],value)
        assert set(row['statistics'])==set(metrics)
        for j,k in enumerate(metrics):nested(row['statistics'][k],stats(a[:,:,j],signed))
        if extra is not None:
            assert set(row['distances'])==set(DISTANCES)
            for j,k in enumerate(DISTANCES):nested(row['distances'][k],stats(extra[:,:,j],True))
    assert len(summary['groups'])==720 and len(summary['packet_groups'])==264 and len(summary['readouts'])==132
    for ci,(role,mode) in enumerate(CASES):
        for fi,label in enumerate(LABELS):
            check_row(summary['groups'][ci*90+fi],dict(role=role,mode=mode,checkpoint=list(label)),f[:,:,ci,fi])
    for pi,(role,kind) in enumerate(PROBES):
        for gi in range(3):
            for si,position in enumerate(('raw','routed')):
                check_row(summary['packet_groups'][(pi*3+gi)*2+si],dict(role=role,kind=kind,generation=gi+1,position=position),pf[:,:,pi,gi,si])
            check_row(summary['readouts'][pi*3+gi],dict(role=role,kind=kind,generation=gi+1,step=300),obs[:,:,pi,gi,-1],OBSERVERS)
            family=arrays['selector_families'][:,:,pi,gi]
            counts=lambda a:{str(k):int(np.count_nonzero(a==k)) for k in (-2,-1,0,1)}
            nested(summary['selections'][pi*3+gi],dict(role=role,kind=kind,generation=gi+1,counts=counts(family),
                block_counts=[counts(a) for a in family]))
    assert len(summary['selections'])==132 and len(summary['paired_checkpoints'])==900 and len(summary['paired_segments'])==210
    cols=[METRICS.index(k) for k in DELTA_METRICS]
    def points(g):return ((g,'write',0,'R'),(g,'write',1,'R'),(g,'write',300,'R'),(g,'write',1000,'R'),
        (g,'packet',0,'raw'),(g,'packet',0,'routed'),(g,'read',300,'V'))
    for role in (0,1):
        for pair,(left,right) in enumerate(PAIRS):
            li,ri=CASES.index((role,left)),CASES.index((role,right));base=role*5+pair
            difference=f[:,:,li]-f[:,:,ri]
            for fi,label in enumerate(LABELS):
                check_row(summary['paired_checkpoints'][base*90+fi],
                    dict(role=role,left=left,right=right,checkpoint=list(label)),
                    difference[:,:,fi][:,:,cols],DELTA_METRICS,True,dist[:,:,role,pair,fi])
            for gi in range(3):
                ids=[LABELS.index(x) for x in points(gi+1)]
                edges=list(zip(ids[:-1],ids[1:]))+[(ids[0],ids[-1])]
                for ei,(ai,bi) in enumerate(edges):
                    check_row(summary['paired_segments'][base*21+gi*7+ei],
                        dict(role=role,left=left,right=right,generation=gi+1,start=list(LABELS[ai]),end=list(LABELS[bi])),
                        (difference[:,:,bi]-difference[:,:,ai])[:,:,cols],DELTA_METRICS,True)
                np.testing.assert_allclose(sum(difference[:,:,ids[j+1]]-difference[:,:,ids[j]] for j in range(6)),
                    difference[:,:,ids[-1]]-difference[:,:,ids[0]],rtol=0,atol=ATOL)
    assert len(summary['correction_paths'])==192
    for role in (0,1):
        ri,mi=CASES.index((role,'reference')),CASES.index((role,'matched'))
        for gi in range(3):
            for bi,index in enumerate(INDICES):
                for life in range(4):
                    path=summary['correction_paths'][role*96+gi*32+bi*4+life]
                    assert set(path)=={'index','life','role','source_stage','checkpoints'}
                    assert (path['index'],path['life'],path['role'],path['source_stage'])==(index,life,role,gi+1)
                    assert len(path['checkpoints'])==7
                    for row,label in zip(path['checkpoints'],points(gi+1)):
                        fi=LABELS.index(label)
                        expected=dict(checkpoint=list(label),
                            reference={k:float(f[bi,life,ri,fi,METRICS.index(k)]) for k in DELTA_METRICS},
                            matched={k:float(f[bi,life,mi,fi,METRICS.index(k)]) for k in DELTA_METRICS},
                            distance={k:float(dist[bi,life,role,0,fi,j]) for j,k in enumerate(DISTANCES)})
                        nested(row,expected)
    return True

def analyze(root):
    panels=[];proofs=[]
    for index in INDICES:
        arrays,proof=analyze_panel(index,*load_panel(index,root));panels.append(arrays);proofs.append(proof)
    arrays={k:np.stack([a[k] for a in panels]) for k in panels[0]}
    summary=summarize(arrays,proofs);assert check_summary(summary,arrays,proofs)
    return arrays,summary,proofs


def source_inputs(root):
    """Flat sealed source closure; imports no simulator and runs no ancestor."""
    u,_=io_helpers();run=root/'runs'/SOURCE_RUN;out=root/'outputs'/SOURCE_RUN
    assert sha256_file(run/'COMPLETE.json')==SOURCE_COMPLETE
    complete,manifest=u.read_json(run/'COMPLETE.json'),u.read_json(run/'MANIFEST.json')
    assert complete['status']=='COMPLETE' and u.read_json(run/'STATUS.json')==complete
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert manifest['environment']==environment_manifest() and sha256_file(run/'MANIFEST.json')==complete['manifest_sha256']
    inputs=[Path(x) for x in manifest['input_sha256']];outputs=[Path(x) for x in complete['output_sha256']]
    assert len(inputs)==967 and len(outputs)==19
    assert u.hashes(inputs)==manifest['input_sha256'] and u.hashes(outputs)==complete['output_sha256']
    assert sha256_file(out/'output_hashes.sha256')==complete['hash_file_sha256']
    assert (out/'output_hashes.sha256').read_text()==u.hash_text(complete['output_sha256'])
    assert {str(x) for x in out.iterdir()}==set(complete['output_sha256'])|{str(out/'output_hashes.sha256')}
    paths=inputs+outputs+[run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]
    paths += [out/'output_hashes.sha256',WS/'reviews/L20_REFERENCE_HANDOFF_2026-09-16.md',*[WS/n for n in SCIENCE]]
    return sorted(set(paths))


def test_report(path,root):
    u,_=io_helpers();path=u.require_beneath(path,root/'logs')
    assert path.name.startswith('d138_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    current=[c for c in cases if c.get('classname','').endswith('test_l20_handoff_persistence')]
    names={c.get('name','').split('[',1)[0] for c in current}
    assert len(current)>=50 and {'test_disposable_panel','test_field_coverage','test_no_dynamics','test_source_hashes',
        'test_summary','test_external_roundtrip','test_resource_guards','test_reservation_guard','test_long_forecast_guard',
        'test_detachment_guard','test_corruption','test_lineage_corruption','test_distances','test_distance_corruption',
        'test_independent_distances','test_independent_summary','test_summary_corruption','test_affine_handoff',
        'test_constant_distance','test_fresh_process_saved_panel','test_prior_disposable_bridge','test_paired_segments',
        'test_control_exceptions'}<=names
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
    return dict(passes=True,fields=23040,packet_fields=8448,unique_fields=29952,correlations=4325376,selectors=3840,
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
