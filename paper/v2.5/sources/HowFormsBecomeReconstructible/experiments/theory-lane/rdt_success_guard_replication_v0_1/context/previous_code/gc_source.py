"""Frozen target packets and genuinely disposable deterministic structures."""
import hashlib
import json
from gc_common import ROOT,P,np,native,ev,read,digest,byte_equal


def target(block):
    if block not in P['blocks']:raise ValueError('Unspecified target block')
    rows=[r for r in read(ROOT/'context/COHORT.json')['rows'] if r['block']==block]
    folder=ROOT/'context/founders'/f'b{block}'
    commit=read(folder/'COMMIT.json')
    raw=ev.load(folder/'boundary.npz',commit['sha256']['boundary.npz'])
    histories=read(ROOT/'native/protocol.json')['acquisition']['histories']
    packets=[]
    for row in rows:
        index=(histories.index(row['history']),row['founder'],row['recipient'])
        packet=native.decode(raw['outgoing'][index])
        if digest(packet)!=row['packet_sha256']:raise ValueError('Wrong source packet')
        aligned=raw['mean_ports'][index]*row['rule']*np.array([[1.,-1.],[-1.,1.]])
        if int(aligned.min()>.25)!=row['current_pass']:raise ValueError('Historical class mismatch')
        if not np.allclose(aligned.ravel(),row['boundary'][:4],rtol=0,atol=1e-12):
            raise ValueError('Saved historical expression changed')
        packets.append(packet)
    if len(rows)!=4 or [sum(r['current_pass']==c for r in rows) for c in (0,1)]!=[2,2]:
        raise ValueError('Complete balanced source block required')
    return rows,np.stack(packets)


def synthetic(block):
    if block not in P['qualification_blocks']:raise ValueError('Unspecified disposable block')
    packets=[];rows=[]
    for i,(h,rule) in enumerate([(0,1),(0,-1),(1,1),(1,-1)]):
        if i in (0,3):packet=np.zeros((2,16,16),np.float64)
        else:
            field=np.ones((16,16),np.float64)
            field[native.PORTS[1]]=rule;field[native.PORTS[2]]=-rule
            packet=np.stack([.9*field*np.roll(field,-1,axis=axis) for axis in (1,0)])
        key=[block,'disposable_guard',i,0]
        # Qualification intentionally audits the H=1 disconnected retention control.
        selection_hash=f'{3-i:064x}'
        rows.append(dict(key=key,block=block,history='disposable_guard',founder=i,recipient=0,
                         current_pass=h,rule=rule,selection_hash=selection_hash,packet_sha256=digest(packet)))
        packets.append(packet)
    return rows,np.stack(packets)


def load(stage,block):
    if stage=='qualification':return synthetic(block)
    if stage=='development':return target(block)
    raise ValueError('Unknown stage')
