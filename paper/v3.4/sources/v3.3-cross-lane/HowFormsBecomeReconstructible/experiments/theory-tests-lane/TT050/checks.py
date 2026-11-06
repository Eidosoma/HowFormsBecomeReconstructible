"""Independent construction checks and excluded-source physics bridge."""
from study import *
from interventions import construct, control_one, graph, EDGES, PORTS
from instrument import traverse

def controls(packets,eligible,prepared,meta):
    raw=native.independent.legacy.unpack(packets[:4])
    v=native.independent.legacy.unpack(prepared).reshape(len(ARMS),*raw.shape)
    assert v[0].tobytes()==raw.tobytes()
    expected=raw.copy();expected[eligible]=0.;assert v[1].tobytes()==expected.tobytes()
    for loc in np.ndindex(raw.shape[:3]):
        w=raw[loc].reshape(512);e=eligible[loc].reshape(512);p=expected[loc].reshape(512)
        r=meta['retained_R'][loc].reshape(512);s=meta['retained_S'][loc].reshape(512)
        # A component-label merge, independent of union-find path compression.
        labels=traverse(p.reshape(2,16,16))[1].copy();rr=np.zeros(512,bool)
        before_count=len(set(labels))
        for edge in np.flatnonzero(e):
            a,b=EDGES[edge];ca,cb=int(labels[a]),int(labels[b])
            if ca!=cb:rr[edge]=True;labels[labels==max(ca,cb)]=min(ca,cb)
        assert rr.tobytes()==r.tobytes()
        assert before_count-len(set(traverse(w.reshape(2,16,16))[1]))==r.sum()
        assert not (r&~e).any() and not (s&~e).any() and r.sum()==s.sum()
        assert labels.tobytes()==traverse(w.reshape(2,16,16))[1].tobytes()
        assert graph(v[(ARMS.index('C'),)+loc])[1].tobytes()==labels.tobytes()
        targets=meta['forced_isolated'][loc].reshape(256)
        if meta['feasible'][loc]:
            assert targets.any() and (graph(v[(ARMS.index('L'),)+loc])[0][targets]==0).all()
        else:assert not targets.any() and r.tobytes()==s.tobytes()
        donor=meta['donor_at_S'][loc];assert (donor[~s]==-1).all()
        assert sorted(donor[s].tolist())==np.flatnonzero(r).tolist()
        for j,name in enumerate(ARMS):
            a=v[(j,)+loc].reshape(512)
            assert a[~e].tobytes()==p[~e].tobytes(),name
            if name in ('I','P'):continue
            sites=r if name.startswith('C') else s
            expected_a=p.copy()
            for edge in np.flatnonzero(sites):
                d=edge if name.startswith('C') or name=='L_native' else int(donor[edge])
                value=float(w[d]);value=-value if 'flip' in name else value
                value=value/4 if 'low' in name else value;expected_a[edge]=value
            assert expected_a.tobytes()==a.tobytes(),name
            assert (a[sites]!=0).all(),f'{name}: magnitude scaling changed support'
        for suffix in ('','_flip','_low','_flip_low'):
            a=v[(ARMS.index('C'+suffix),)+loc].reshape(512)[r]
            b=v[(ARMS.index('L'+suffix),)+loc].reshape(512)[s]
            assert np.sort(a).tobytes()==np.sort(b).tobytes()
        for location in ('C','L'):
            for suffix in ('','_low'):
                a=v[(ARMS.index(location+suffix),)+loc]
                b=v[(ARMS.index(location+'_flip'+suffix),)+loc]
                assert abs(a).tobytes()==abs(b).tobytes()
                assert native.old.coupling(a)[0].tobytes()==native.old.coupling(b)[0].tobytes()
    return dict(records=int(np.prod(raw.shape[:3])),feasible=int(meta['feasible'].sum()),all_retained=True)

def capture(writer,e,extras):
    w=native.independent.legacy.unpack(writer['outgoing']).reshape(len(ARMS),4,*e.shape[1:])
    ordinary=writer['ordinary'].reshape(w.shape)
    result=[]
    for name in ('P','C'):
        i=ARMS.index(name);h=w[i];o=h.copy();s=h.copy();m=h.copy()
        for loc in np.ndindex(h.shape):
            if e[loc]:
                val=float(ordinary[i][loc]);o[loc]=val
                s[loc]=np.copysign(abs(float(h[loc])),val)
                m[loc]=np.copysign(abs(val),float(h[loc]))
        result.extend((o,s,m))
    expected=native.independent.legacy.pack(np.concatenate(result))
    assert extras.tobytes()==expected.tobytes()

def fixtures():
    cases=[]
    # Empty graph and empty selection; no silently manufactured intervention.
    cases.append((np.zeros((2,16,16)),np.zeros((2,16,16),bool)))
    full=np.ones((2,16,16));empty=np.zeros_like(full,bool);cases.append((full,empty))
    # Two isolated cells allow concentrating an equal number of retained edges.
    cell=100;spokes=np.any(np.isin(EDGES,[cell,110]),axis=1).reshape(2,16,16)
    cases.append((full.copy(),spokes))
    # Single indispensable edge: no equal-count isolation-leaving match exists.
    single=np.zeros_like(full);single[0,6,4]=-2.;cases.append((single,single!=0))
    # Disconnected islands, signed zeros and heterogeneous strength.
    varied=np.arange(1.,513.).reshape(2,16,16)/512;varied[::2]*=-1
    varied[1,0,0]=-0.;chosen=np.any(np.isin(EDGES,[100,110,120]),axis=1).reshape(2,16,16)
    cases.append((varied,chosen))
    for w,e in cases:
        input_w=np.broadcast_to(w,(4,4,1,2,16,16)).copy();eligible=np.broadcast_to(e,input_w.shape).copy()
        packet=native.base.encode(input_w);p,meta=construct(packet,eligible);controls(packet,eligible,p,meta)
    x,meta=control_one(*cases[2]);assert meta['feasible']
    assert (graph(x[ARMS.index('C')])[0]>0).all()
    assert graph(x[ARMS.index('L')])[0][cell]==0
    assert not control_one(*cases[3])[1]['feasible']
    return dict(status='PASS',graph_fixtures=len(cases),construction_audit=True)

def bridge():
    inter,old_writer=source(900041,True)
    cfg=dict(CONFIG,recipients=1);steps=dict(read_steps=512,settling_steps=256)
    got=native.checked_body(inter['packets'],900041,cfg,steps,
        ('E077',900041,'develop',1),('develop_injury',1),tolerance=0.)
    for key in ('incoming','outgoing','end','late_ports','mean_ports','masks','denominator','coupling','ordinary','contrast','fallback'):
        assert got[key].tobytes()==old_writer[key].tobytes(),key
    return dict(status='PASS',source=900041,recipients=1,steps=512,legacy_arrays=11,independent_replay=True)

if __name__=='__main__':
    import time
    start=time.monotonic();out=dict(fixtures=fixtures(),bridge=bridge(),seconds=time.monotonic()-start)
    write(ROOT/'PREFLIGHT_CHECKS.json',out);print(json.dumps(out))

