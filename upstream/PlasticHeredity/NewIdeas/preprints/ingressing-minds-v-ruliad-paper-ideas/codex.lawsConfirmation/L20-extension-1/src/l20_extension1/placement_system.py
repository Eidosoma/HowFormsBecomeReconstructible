"""D148: fixed packets crossed with the two guide-selected reader placements."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from . import stopping_system as source

old,dev=source.old,source.dev
ROOT,CONFIG=source.ROOT,source.CONFIG
SOURCE_RUN='l20_extension1_stopping_time_v1_attempt1'
SOURCE_COMPLETE_SHA='388c8d701d3b659586b8f092e62a62d92edb423f4055924a1169682072baf407'
TAG='l20-extension1-packet-placement-v1'
PHYSICS_TAG='l20-extension1-phase-budget-v1'
BLOCKS=tuple(range(93000,93016)); DISPOSABLE=514246
STOPS=(1000,1300); KINDS=('intact','copy','read_off','write_off')
CASES=tuple((r,p,a,k) for r in (0,1) for p in STOPS for a in STOPS for k in KINDS)


def source_paths(index):
    source.source.validate(index,0)
    directory=ROOT/('tmp' if index==DISPOSABLE else 'outputs')/(SOURCE_RUN+('_benchmark' if index==DISPOSABLE else ''))
    return tuple(directory/f'block_{index}.{ext}' for ext in ('npz','json'))


def load_source(index):
    a,b=source_paths(index);raw,meta=io.load_npz(a),io.read_json(b)
    assert meta['index']==index and meta['config']==asdict(CONFIG) and len(meta['lives'])==4
    for value in raw.values():
        assert value.shape[0]==4
        value.setflags(write=False)
    return raw,meta


def shift_packet(packet,shift):
    shift=np.asarray(shift)
    if shift.shape!=(2,) or shift.dtype!=np.int64 or np.any(shift<0) or np.any(shift>=16):
        raise ValueError('declared two-dimensional forward shift required')
    return old.encode(np.roll(old.decode(packet),tuple(-shift),(0,1)))


def cell(raw,meta,noise,role,packet_stop,address_stop,kind,generation):
    if (role,packet_stop,address_stop,kind) not in CASES or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared complete crossed cell required')
    if type(noise) is not int or noise not in (0,1):raise ValueError('two replicas only')
    pi=source.CASES.index((role,packet_stop,kind));ai=source.CASES.index((role,address_stop,kind));gi=generation-1
    packet=raw['packet'][noise,pi,gi].tobytes();donor=raw['packet'][noise,ai,gi].tobytes()
    natural,scores,selection=old.route(packet,'learned',raw['guide'])
    _,_,address=old.route(donor,'learned',raw['guide'])
    assert natural==raw['terminal_packet'][noise,pi,gi].tobytes()
    assert selection==meta['cells'][noise][pi][gi]['terminal_selector']
    assert address==meta['cells'][noise][ai][gi]['terminal_selector']
    np.testing.assert_array_equal(scores,raw['scores'][noise,pi,gi])
    shift=np.asarray(address['chosen_forward_shift'],np.int64)
    routed=shift_packet(packet,shift)
    reuse=routed==natural
    mode='natural_diagonal' if packet_stop==address_stop else 'identical_routed_bytes' if reuse else 'new_assay'
    assert reuse or packet_stop!=address_stop
    spec=dict(role=role,packet_stop=packet_stop,address_stop=address_stop,kind=kind,generation=generation,
        recipient_case=pi,donor_case=ai,forward_shift=shift.tolist(),packet_sha256=hashlib.sha256(packet).hexdigest(),
        donor_sha256=hashlib.sha256(donor).hexdigest(),routed_sha256=hashlib.sha256(routed).hexdigest(),
        natural_routed_sha256=hashlib.sha256(natural).hexdigest(),source_mode=mode,new_assay=not reuse)
    return packet,routed,spec,selection,address


def life_plan(raw,meta):
    return [[ [cell(raw,meta,n,r,p,a,k,g)[2] for g in (1,2,3)] for r,p,a,k in CASES] for n in (0,1)]


def block_plan(index,raw=None,meta=None):
    if raw is None:raw,meta=load_source(index)
    cells=[life_plan({k:v[l] for k,v in raw.items()},meta['lives'][l]) for l in range(4)]
    new=sum(c['new_assay'] for life in cells for trial in life for case in trial for c in case)
    assert 0<=new<=192
    return dict(index=index,cells=cells,labelled_cells=768,natural_diagonals=384,new_assays=new,reused_labels=768-new)


def canonical(packet,role):
    field=old.decode(packet);z=field-field.mean();scale=np.sqrt(np.mean(z*z))
    return np.array([np.mean(z*dev.targets()[r])/scale if scale else 0. for r in (role,1-role)],np.float64)


def readout(packet,index,life,noise,generation):
    return source.readout(packet,index,life,noise,generation)


def simulate_life(index,life,raw,source_meta,order=CASES):
    source.source.validate(index,life)
    assert (source_meta['index'],source_meta['life'])==(index,life)
    if len(order)!=32 or set(order)!=set(CASES):raise ValueError('complete crossed panel required')
    dev.validate_guide(raw['guide']);trials=[];entries=[];new=0
    for noise in (0,1):
        paths={};history={}
        for role,pstop,astop,kind in order:
            rows=[];cells=[]
            for generation in (1,2,3):
                packet,routed,spec,selection,address=cell(raw,source_meta,noise,role,pstop,astop,kind,generation)
                pi=spec['recipient_case'];gi=generation-1
                if spec['new_assay']:
                    terminal,reader=readout(routed,index,life,noise,generation);new+=1
                else:
                    terminal=raw['terminal_states'][noise,pi,gi].copy()
                    reader=deepcopy(source_meta['cells'][noise][pi][gi]['terminal_reader'])
                rec=dev.record_features(packet,role,raw['guide']);placed=canonical(routed,role)
                rows.append(dict(packet=np.frombuffer(packet,np.uint8),terminal_packet=np.frombuffer(routed,np.uint8),
                    shift=np.asarray(spec['forward_shift'],np.int64),terminal_states=terminal,
                    terminal_values=source.source.observations(terminal,role),
                    record_values=np.r_[rec[:3],rec[0]-rec[1],placed,placed[0]-placed[1]]))
                cells.append(dict(**spec,natural_selector=selection,address_selector=address,terminal_reader=reader,
                    assay_steps=300,carrier_bytes=2048,assay_enters_lineage=False))
            paths[role,pstop,astop,kind]={k:np.stack([r[k] for r in rows]) for k in rows[0]}
            history[role,pstop,astop,kind]=cells
        trials.append({k:np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]})
        entries.append([history[c] for c in CASES])
    result={k:np.stack([trial[k] for trial in trials]) for k in trials[0]}
    result.update(guide=raw['guide'].copy(),founder_packets=raw['founder_packets'].copy())
    meta=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CONFIG),cases=[list(c) for c in CASES],host=deepcopy(source_meta['host']),cells=entries,
        new_assays=new,reused_labels=192-new,labelled_cells=192,natural_diagonals=96,new_founders=0,
        new_upstream_dynamics=0,same_extended_history=True,new_independent_noise=False,guide_refitted=False,
        source_state_given_to_reader=False,assay_enters_lineage=False,placement_supplied_by_analyst=True)
    return result,meta
