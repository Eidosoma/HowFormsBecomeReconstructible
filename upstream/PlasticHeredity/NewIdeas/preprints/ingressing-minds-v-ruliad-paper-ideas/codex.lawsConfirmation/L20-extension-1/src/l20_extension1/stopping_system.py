"""D147: same-history R1000/R1300 packets, fixed matched fresh readers."""
from copy import deepcopy
from dataclasses import asdict
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from . import phase_budget_system as source

old, dev = source.old, source.dev
ROOT, CONFIG = source.ROOT, source.CONFIG
SOURCE_RUN = 'l20_extension1_phase_budget_v1_attempt1'
SOURCE_COMPLETE_SHA = '3d057c9123cf3a10d6068c356dae6b4632834c9da4f87a88f431d8ce2f5789e0'
TAG = 'l20-extension1-stopping-time-v1'
PHYSICS_TAG = 'l20-extension1-phase-budget-v1'
BLOCKS = tuple(range(93000,93016))
DISPOSABLE = 514246
STOPS = (1000,1300)
KINDS = ('intact','copy','read_off','write_off')
CASES = tuple((r,t,k) for r in (0,1) for t in STOPS for k in KINDS)


def source_paths(index):
    source.validate(index,0)
    directory = ROOT/('tmp' if index==DISPOSABLE else 'outputs')/(SOURCE_RUN+('_benchmark' if index==DISPOSABLE else ''))
    return tuple(directory/f'block_{index}.{ext}' for ext in ('npz','json'))


def load_source(index):
    a,b = source_paths(index)
    raw,meta = io.load_npz(a),io.read_json(b)
    assert meta['index']==index and meta['config']==asdict(CONFIG) and len(meta['lives'])==4
    for value in raw.values():
        assert value.shape[0]==4
        value.setflags(write=False)
    return raw,meta


def source_kind(kind):
    if kind not in KINDS: raise ValueError('declared control required')
    return 'write'+('' if kind=='intact' else '_'+kind)


def reuse_kind(stop,kind,generation):
    if type(stop) is not int or stop not in STOPS or kind not in KINDS or type(generation) is not int or generation not in (1,2,3):
        raise ValueError('declared stop/control/generation required')
    if stop==1300 or kind in ('copy','write_off'): return source_kind(kind)
    if kind=='read_off': return 'base_read_off'
    return 'base' if generation==1 else None


def validate_bridges(raw):
    """No dynamics: require exact source identities before permitting endpoint reuse."""
    for role in (0,1):
        for kind in ('intact','read_off'):
            suffix='' if kind=='intact' else '_read_off'
            bi=source.CASES.index((role,'base'+suffix));wi=source.CASES.index((role,'write'+suffix))
            generations=(0,) if kind=='intact' else range(3)
            for gi in generations:
                np.testing.assert_array_equal(raw['read_states'][:,bi,gi],raw['read_states'][:,wi,gi])
                for bs,ws in ((0,0),(1,1),(2,2),(4,3)):
                    np.testing.assert_array_equal(raw['write_states'][:,bi,gi,bs],raw['write_states'][:,wi,gi,ws])
        for kind in ('copy','write_off'):
            bi=source.CASES.index((role,'base_'+kind));wi=source.CASES.index((role,'write_'+kind))
            for key in ('outgoing','terminal_packet','terminal_states'):
                np.testing.assert_array_equal(raw[key][:,bi],raw[key][:,wi])


def emitted(raw,noise,role,stop,kind,generation):
    reuse_kind(stop,kind,generation)
    ci=source.CASES.index((role,source_kind(kind)))
    if kind=='copy': return raw['founder_packets'][role].tobytes()
    if kind=='write_off': return bytes(2048)
    return old.encode(old.record(raw['write_states'][noise,ci,generation-1,STOPS.index(stop)+3,2]))


def readout(packet,index,life,noise,generation):
    """Only bytes/public parameters enter; same D146 assay streams, no source state."""
    return source.assay(packet,old.context(index),index,life,noise,generation)


def simulate_life(index,life,raw,source_meta,order=CASES):
    source.validate(index,life)
    assert (source_meta['index'],source_meta['life'])==(index,life)
    if len(order)!=16 or set(order)!=set(CASES): raise ValueError('complete condition panel required')
    validate_bridges(raw)
    guide=raw['guide']; dev.validate_guide(guide)
    trials=[]; trial_meta=[]
    for noise in (0,1):
        paths={}; entries={}
        for role,stop,kind in order:
            rows=[]; history=[]
            for generation in (1,2,3):
                packet=emitted(raw,noise,role,stop,kind,generation)
                routed,scores,selection=old.route(packet,'learned',guide)
                reused=reuse_kind(stop,kind,generation)
                if reused is None:
                    terminal,reader=readout(routed,index,life,noise,generation)
                else:
                    ci=source.CASES.index((role,reused)); gi=generation-1
                    assert packet==raw['outgoing'][noise,ci,gi].tobytes()
                    assert routed==raw['terminal_packet'][noise,ci,gi].tobytes()
                    np.testing.assert_array_equal(scores,raw['scores'][noise,ci,gi,1])
                    terminal=raw['terminal_states'][noise,ci,gi].copy()
                    entry=source_meta['trials'][noise]['paths'][ci]['generations'][gi]
                    assert selection==entry['terminal_selector']
                    reader=deepcopy(entry['terminal_reader'])
                rows.append(dict(packet=np.frombuffer(packet,np.uint8),terminal_packet=np.frombuffer(routed,np.uint8),
                    scores=scores,terminal_states=terminal,terminal_values=source.observations(terminal,role),
                    record_values=dev.record_features(packet,role,guide)))
                history.append(dict(role=role,stop=stop,kind=kind,generation=generation,
                    snapshot_kind=source_kind(kind),write_checkpoint=STOPS.index(stop)+3,
                    endpoint_source_kind=reused,new_assay=reused is None,terminal_selector=selection,
                    terminal_reader=reader,assay_steps=300,carrier_bytes=2048,assay_enters_lineage=False))
            paths[role,stop,kind]={k:np.stack([row[k] for row in rows]) for k in rows[0]}
            entries[role,stop,kind]=history
        trials.append({k:np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]})
        trial_meta.append([entries[c] for c in CASES])
    result={k:np.stack([trial[k] for trial in trials]) for k in trials[0]}
    result.update(guide=guide.copy(),founder_packets=raw['founder_packets'].copy())
    meta=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CONFIG),cases=[list(c) for c in CASES],host=deepcopy(source_meta['host']),
        cells=trial_meta,new_assays=8,labelled_cells=96,new_founders=0,new_upstream_dynamics=0,
        same_extended_history=True,new_independent_noise=False,guide_refitted=False,
        source_state_given_to_reader=False,assay_enters_lineage=False)
    return result,meta
