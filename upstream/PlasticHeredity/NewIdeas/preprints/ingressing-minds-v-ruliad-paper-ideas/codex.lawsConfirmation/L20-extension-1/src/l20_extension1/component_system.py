"""D149: norm/own-axis preserving attenuation and two equal-distance shams."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from . import placement_system as source
from . import placement_review as fields

old,dev=source.old,source.dev
ROOT,CONFIG=source.ROOT,source.CONFIG
SOURCE_RUN='l20_extension1_packet_placement_v1_attempt1'
SOURCE_COMPLETE_SHA='22f89ccdf1fedf056d3078fef93b57a490d9941abcec911286911e1d67ca8946'
TAG='l20-extension1-competing-component-v1'
PHYSICS_TAG='l20-extension1-phase-budget-v1'
BLOCKS=tuple(range(93000,93016));DISPOSABLE=514246
KINDS=('intact','copy','read_off','write_off')
EDITS=('untouched','attenuate','sham_plus','sham_minus')
CASES=tuple((r,e,k) for r in (0,1) for e in EDITS for k in KINDS)
RECORD_NAMES=('mean','rms','own_axis_rms','competing_axis_rms','residual_rms','edit_rms',
              'canonical_own','canonical_alternative','best_own','best_alternative')


def validate(index,life):
    if type(index) is not int or index not in BLOCKS+(DISPOSABLE,) or type(life) is not int or life not in range(4):
        raise ValueError('declared block and life required')


def source_paths(index):
    validate(index,0)
    directory=ROOT/('tmp' if index==DISPOSABLE else 'outputs')/(SOURCE_RUN+('_benchmark' if index==DISPOSABLE else ''))
    return tuple(directory/f'block_{index}.{ext}' for ext in ('npz','json'))


def load_source(index):
    a,b=source_paths(index);raw,meta=io.load_npz(a),io.read_json(b)
    assert meta['index']==index and meta['config']==asdict(CONFIG) and len(meta['lives'])==4
    for v in raw.values():
        assert v.shape[0]==4
        v.setflags(write=False)
    return raw,meta


def rms(x):return float(np.sqrt(np.mean(x*x)))


def parts(field,role):
    if type(role) is not int or role not in (0,1):raise ValueError('declared family required')
    mu=float(field.mean());z=field-mu
    row=np.broadcast_to(z.mean(axis=1)[:,None],(16,16))
    col=np.broadcast_to(z.mean(axis=0)[None,:],(16,16))
    return mu,(row if role==0 else col),(col if role==0 else row),z-row-col


def edit_packets(packet,role):
    f=old.decode(packet);mu,o,c,r=parts(f,role);C,R=rms(c),rms(r)
    degenerate=min(C,R)<=1e-12*max(1.,rms(f-mu))
    if degenerate:return {e:packet for e in EDITS},dict(degenerate=True,dose_rms=0.,competing_scale=1.,q_seed=-1)
    d=.5*min(C,R);theta=2*np.arcsin(d/(2*np.hypot(C,R)))
    cnew=C*np.cos(theta)-R*np.sin(theta);rnew=R*np.cos(theta)+C*np.sin(theta)
    beta=2*np.arcsin(d/(2*R));unit=r/R
    h0=np.where(np.arange(16)<8,1.,-1.);h1=np.where(np.arange(16)%8<4,1.,-1.)
    for qi,h in enumerate((h0,h1)):
        seed=np.outer(h,h0);q=seed-np.mean(seed*unit)*unit;qn=rms(q)
        if qn>=.5:break
    else:raise AssertionError('two orthogonal Walsh seeds must supply a direction')
    q=q/qn
    values=dict(untouched=packet,attenuate=old.encode(mu+o+(cnew/C)*c+(rnew/R)*r),
        sham_plus=old.encode(mu+o+c+np.cos(beta)*r+R*np.sin(beta)*q),
        sham_minus=old.encode(mu+o+c+np.cos(beta)*r-R*np.sin(beta)*q))
    return values,dict(degenerate=False,dose_rms=d,competing_scale=float(cnew/C),q_seed=qi)


def cell(raw,meta,n,role,edit,kind,g):
    if type(role) is not int or (role,edit,kind) not in CASES or type(n) is not int or n not in (0,1) or type(g) is not int or g not in (1,2,3):
        raise ValueError('complete declared cell required')
    si=source.CASES.index((role,1300,1300,kind));gi=g-1
    packet=raw['terminal_packet'][n,si,gi].tobytes();edited,detail=edit_packets(packet,role)
    candidate=edited[edit];reuse=candidate==packet
    spec=dict(role=role,edit=edit,kind=kind,generation=g,source_case=si,
        forward_shift=raw['shift'][n,si,gi].tolist(),source_sha256=hashlib.sha256(packet).hexdigest(),
        edited_sha256=hashlib.sha256(candidate).hexdigest(),new_assay=not reuse,
        source_mode='untouched' if edit=='untouched' else 'identical_bytes' if reuse else 'new_assay',**detail)
    return packet,candidate,spec


def block_plan(index,raw=None,meta=None):
    if raw is None:raw,meta=load_source(index)
    from . import component_audit as checker
    lives=[]
    for l in range(4):
        src={k:v[l] for k,v in raw.items()};entry=meta['lives'][l];trials=[]
        for n in (0,1):
            cases=[]
            for role,edit,kind in CASES:
                generations=[]
                for g in (1,2,3):
                    p,q,s=cell(src,entry,n,role,edit,kind,g)
                    checker.check_candidate(q,s,src,entry,n,role,edit,kind,g)
                    generations.append(s)
                cases.append(generations)
            trials.append(cases)
        lives.append(trials)
    new=sum(s['new_assay'] for l in lives for n in l for c in n for s in c)
    return dict(index=index,cells=lives,labelled_cells=768,untouched=192,new_assays=new,reused_labels=768-new)


def record_values(packet,original,role):
    f=old.decode(packet);mu,o,c,r=parts(f,role);z=f-mu;scale=rms(z)
    canon=[float(np.mean(z*t)/scale) if scale else 0. for t in dev.targets()[[role,1-role]]]
    best=fields.measure(f,role)[6:8]
    return np.array([mu,rms(f),rms(o),rms(c),rms(r),rms(f-old.decode(original)),*canon,*best])


def observation(states,role):
    t=dev.targets();result=[]
    for v,m,r in states:
        best=fields.measure(r,role)[6:8]
        result.append([dev.terminal_features(v,role)[0],*best,float(np.mean(v*(t[role]-t[1-role]))/2)])
    return np.asarray(result,np.float64)


def readout(packet,index,life,noise,generation):return source.readout(packet,index,life,noise,generation)


def simulate_life(index,life,raw,source_meta,order=CASES):
    validate(index,life)
    assert (source_meta['index'],source_meta['life'])==(index,life)
    if len(order)!=32 or set(order)!=set(CASES):raise ValueError('complete edit/control panel required')
    dev.validate_guide(raw['guide']);trials=[];entries=[];new=0
    for n in (0,1):
        paths={};history={}
        for role,edit,kind in order:
            rows=[];cells=[]
            for g in (1,2,3):
                packet,candidate,spec=cell(raw,source_meta,n,role,edit,kind,g);si=spec['source_case'];gi=g-1
                if spec['new_assay']:
                    terminal,reader=readout(candidate,index,life,n,g);new+=1
                else:
                    terminal=raw['terminal_states'][n,si,gi].copy()
                    reader=deepcopy(source_meta['cells'][n][si][gi]['terminal_reader'])
                rows.append(dict(packet=np.frombuffer(packet,np.uint8),terminal_packet=np.frombuffer(candidate,np.uint8),
                    shift=np.asarray(spec['forward_shift'],np.int64),terminal_states=terminal,
                    terminal_values=observation(terminal,role),record_values=record_values(candidate,packet,role)))
                cells.append(dict(**spec,terminal_reader=reader,assay_steps=300,carrier_bytes=2048,assay_enters_lineage=False))
            paths[role,edit,kind]={k:np.stack([v[k] for v in rows]) for k in rows[0]};history[role,edit,kind]=cells
        trials.append({k:np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]})
        entries.append([history[c] for c in CASES])
    result={k:np.stack([v[k] for v in trials]) for k in trials[0]}
    result.update(guide=raw['guide'].copy(),founder_packets=raw['founder_packets'].copy())
    meta=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CONFIG),cases=[list(c) for c in CASES],host=deepcopy(source_meta['host']),cells=entries,
        new_assays=new,reused_labels=192-new,labelled_cells=192,untouched=48,new_founders=0,
        new_upstream_dynamics=0,same_extended_history=True,new_independent_noise=False,guide_refitted=False,
        source_state_given_to_reader=False,assay_enters_lineage=False,analyst_supplied_edit=True,rerouted_after_edit=False)
    return result,meta
