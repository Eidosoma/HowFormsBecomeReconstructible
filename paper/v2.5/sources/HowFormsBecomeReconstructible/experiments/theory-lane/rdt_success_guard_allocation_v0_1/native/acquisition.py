"""Fresh matched acquisition to g14; no generation-15 or terminal outcomes."""
from contextlib import contextmanager
import hashlib
import json
import time

import numpy as np

from bridge import P, e, audit, ev

HISTORIES = P['acquisition']['histories']
NATIVE_STREAM = e.native.stream


def stream(stage, tag, *parts, legacy=False):
    if legacy:
        return NATIVE_STREAM(tag, *parts)
    return NATIVE_STREAM(P['acquisition']['namespace'], stage, tag, *parts)


@contextmanager
def native_stream(stage, legacy=False):
    old = e.native.stream
    e.native.stream = lambda tag, *parts: stream(stage, tag, *parts, legacy=legacy)
    try:
        yield
    finally:
        e.native.stream = old


def teacher(block, stage, legacy=False):
    """E016 consistent teaching: coordinated opposite-cue birth and noise."""
    cfg = P['acquisition']['config']; total = np.zeros((4, 2, 16, 16))
    births, ends, captures = [], [], []
    for cue, polarity in [(1., 1.), (-1., -1.)]:
        random = stream(stage, 'E016', block, 'teach', 0, legacy=legacy)
        birth = polarity*cfg['birth_sd']*np.repeat(random.standard_normal((2,16,16)), 2, axis=0)
        value = birth.copy(); targets = np.stack((np.full(4,cue),e.native.RULES*cue,-e.native.RULES*cue),axis=1)
        for p in range(3): value[:,e.PORTS[p]] = targets[:,p,None]
        late = []
        for t in range(cfg['teach_steps']):
            noise = polarity*np.repeat(random.standard_normal((2,16,16)),2,axis=0)
            drift = value-value**3+cfg['teacher_gain']*(e.native.neighbors(value,np.ones((2,16,16)))/4.-value)
            value = np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)
            for p in range(3): value[:,e.PORTS[p]] = targets[:,p,None]
            if t >= cfg['teach_steps']-cfg['capture_steps']:
                late.append(value.copy())
                x = np.tanh(cfg['writer_beta']*value)
                total += np.stack((x*np.roll(x,-1,-1),x*np.roll(x,-1,-2)),axis=-3)
        births.append(birth); ends.append(value); captures.append(np.stack(late))
    weights = total/(2*cfg['capture_steps'])
    return dict(birth=np.stack(births),end=np.stack(ends),capture=np.stack(captures),
                weights=weights,acquired=e.native.encode(weights))


def check_teacher(raw, block, stage, legacy=False):
    """Separate flattened-neighbor replay of both coordinated teaching episodes."""
    cfg=P['acquisition']['config']; total=np.zeros((4,2,256))
    for c,polarity in enumerate((1.,-1.)):
        random=stream(stage,'E016',block,'teach',0,legacy=legacy)
        value=polarity*cfg['birth_sd']*np.repeat(random.standard_normal((2,256)),2,axis=0)
        assert np.array_equal(value.reshape(4,16,16),raw['birth'][c])
        targets=np.stack((np.full(4,polarity),e.native.RULES*polarity,-e.native.RULES*polarity),axis=1)
        for p in range(3):value[:,audit.PORTS[p]]=targets[:,p,None]
        for t in range(cfg['teach_steps']):
            noise=polarity*np.repeat(random.standard_normal((2,256)),2,axis=0)
            neighbors=value[:,audit.RIGHT]+value[:,audit.LEFT]+value[:,audit.DOWN]+value[:,audit.UP]
            force=value-value**3+cfg['teacher_gain']*(neighbors/4.-value)
            value=np.clip(value+cfg['dt']*force+cfg['noise']*noise,-2.,2.)
            for p in range(3):value[:,audit.PORTS[p]]=targets[:,p,None]
            if t >= cfg['teach_steps']-cfg['capture_steps']:
                index=t-(cfg['teach_steps']-cfg['capture_steps'])
                assert np.array_equal(value.reshape(4,16,16),raw['capture'][c,index])
                x=np.tanh(cfg['writer_beta']*value)
                total+=np.stack((x*x[:,audit.RIGHT],x*x[:,audit.DOWN]),axis=1)
        assert np.array_equal(value.reshape(4,16,16),raw['end'][c])
    assert np.array_equal((total/(2*cfg['capture_steps'])).reshape(4,2,16,16),raw['weights'])
    return dict(teaching_episodes_replayed=2,byte_exact=True)


def policies(generation):
    if not 1 <= generation <= 14:
        raise ValueError('Fresh precision acquisition stops at generation 14')
    return ['tolerance_rewrite' if generation in P['acquisition']['tolerance_generations'][h]
            else 'exact_rewrite' for h in HISTORIES]


def check_step(incoming, raw, block, generation, stage, legacy=False):
    cfg=P['acquisition']['config']; reader=P['reader']; shape=(2,cfg['recipients'],16,16)
    random=stream(stage,'E022',block,'develop',generation,legacy=legacy)
    z=random.standard_normal(shape)[0,0]
    birth=cfg['birth_sd']*np.stack([z,z])
    assert np.array_equal(birth,raw['birth'][0,0])
    noises=[]
    for _ in range(reader['read_steps']):
        z=random.standard_normal(shape)[0,0];noises.append(np.stack([z,z]))
    flat=audit.read_write(e.native.decode(incoming[:,0,0]),raw['masks'][0,0],birth,
                          np.stack(noises),reader,cfg['writer_beta'])
    assert np.array_equal(flat['end'],raw['end'][:,0,0])
    assert np.array_equal(flat['windows'].mean(axis=0),raw['mean_ports'][:,0,0])
    pair=e.diagnostic.writer_pair(flat['end'],e.native.available_edges(raw['masks'][0,0]),
                                  beta=cfg['writer_beta'],tolerance=1e-4)
    out=np.stack([pair['tolerance' if name=='tolerance_rewrite' else 'exact'][i]
                  for i,name in enumerate(policies(generation))])
    assert np.array_equal(out,e.native.decode(raw['outgoing'][:,0,0]))
    return dict(generation=generation,founder=0,recipient=0,flat_native_reads=4,byte_exact=True)


def boundary_records(block, raw):
    result=[]
    for h,history in enumerate(HISTORIES):
        for founder in range(4):
            rule=1 if founder%2==0 else -1
            for recipient in range(4):
                packet=e.native.decode(raw['outgoing'][h,founder,recipient])
                aligned=raw['mean_ports'][h,founder,recipient]*rule*np.array([[1.,-1.],[-1.,1.]])
                signed,unsigned=e.transfer(packet,rule)
                independent=audit.transfer(packet,rule)
                assert np.allclose([signed,unsigned],independent,rtol=0,atol=1e-12)
                boundary=np.r_[aligned.ravel(),aligned.min(),float(aligned.min()>.25),unsigned,
                               [float(h==j) for j in (1,2,3)],signed]
                key=[block,history,founder,recipient]
                rank=hashlib.sha256(json.dumps([P['selection']['namespace'],*key],separators=(',',':')).encode()).hexdigest()
                result.append(dict(key=key,block=block,history=history,founder=founder,recipient=recipient,
                    rule=rule,current_pass=int(boundary[5]),boundary=boundary.tolist(),selection_hash=rank,
                    packet_sha256=hashlib.sha256(packet.tobytes()).hexdigest()))
    return result


def select(rows):
    """Boundary-only selection; no prediction, probe or future outcome is used."""
    selected=[]
    for block in sorted({r['block'] for r in rows}):
        for c in (0,1):
            group=sorted([r for r in rows if r['block']==block and r['current_pass']==c],key=lambda r:r['selection_hash'])
            by_rule=[[r for r in group if r['rule']==rule] for rule in (-1,1)]
            selected.extend([v[0] for v in by_rule] if all(by_rule) else group[:2])
    return selected


def acquire(block,stage,folder,deadline,legacy=False):
    start=time.monotonic();cfg=P['acquisition']['config'];cycle=P['acquisition']['cycle']
    taught=teacher(block,stage,legacy);teaching=check_teacher(taught,block,stage,legacy)
    ev.save(folder/f'teaching_{block:06d}.npz',taught)
    packets=np.repeat(np.repeat(taught['acquired'][None,:,None],4,axis=0),4,axis=2)
    audits=[];native_reads=0
    with native_stream(stage,legacy):
        for generation in range(1,15):
            deadline.check()
            raw=e.native.rebuild(packets,block,generation,policies(generation),cfg,cycle,1e-4)
            if generation in (1,3,14):audits.append(check_step(packets,raw,block,generation,stage,legacy))
            ev.save(folder/f'boundary_{block:06d}_g{generation:02d}.npz',raw)
            packets=raw['outgoing'];native_reads+=64
    rows=boundary_records(block,raw)
    receipt=dict(block=block,stage=stage,legacy_validation_only=legacy,teaching=teaching,audits=audits,
                 native_reads=native_reads,flat_native_reads=12,wall_seconds=time.monotonic()-start,
                 max_generation=14,new_future_outcomes=0)
    ev.write(folder/f'acquisition_{block:06d}.json',receipt)
    return raw,rows,receipt
