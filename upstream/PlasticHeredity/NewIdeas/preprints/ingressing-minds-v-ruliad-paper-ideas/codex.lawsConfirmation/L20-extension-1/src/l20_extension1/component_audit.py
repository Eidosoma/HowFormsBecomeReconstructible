"""Independent algebra, invariants, saved metrics and full D149 reader replay."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import audit as metrics

prior=old.checker();physics=prior.physics;CFG=old.CONFIG
TAG='l20-extension1-competing-component-v1';PHYSICS_TAG='l20-extension1-phase-budget-v1'
SOURCE_RUN='l20_extension1_packet_placement_v1_attempt1'
KINDS=('intact','copy','read_off','write_off')
EDITS=('untouched','attenuate','sham_plus','sham_minus')
CASES=tuple((r,e,k) for r in (0,1) for e in EDITS for k in KINDS)


def decompose(f,role):
    mean=float(np.sum(f)/256);z=f-mean
    row=np.sum(z,axis=1)[:,None]/16;col=np.sum(z,axis=0)[None,:]/16
    own=np.broadcast_to((row,col)[role],(16,16));comp=np.broadcast_to((col,row)[role],(16,16))
    return mean,own,comp,z-row-col


def norm(f):return float(np.sqrt(np.sum(f*f)/256))


def expected_edit(packet,role,edit):
    f=prior.unpack(packet);mu,own,comp,res=decompose(f,role);C,R=norm(comp),norm(res)
    degenerate=min(C,R)<=1e-12*max(1.,norm(f-mu))
    if degenerate:return f.copy(),dict(degenerate=True,dose_rms=0.,competing_scale=1.,q_seed=-1)
    distance=min(C,R)/2;h2=C*C+R*R
    # Algebraic cosine/sine, not the production inverse-trigonometric path.
    ct=1-distance*distance/(2*h2);st=distance/np.sqrt(h2)*np.sqrt(1-distance*distance/(4*h2))
    cs=1-distance*distance/(2*R*R);ss=distance/R*np.sqrt(1-distance*distance/(4*R*R))
    small=np.array([1.]*8+[-1.]*8);other=np.array(([1.]*4+[-1.]*4)*2)
    for qi,vec in enumerate((small,other)):
        q=np.multiply.outer(vec,small)-np.sum(np.multiply.outer(vec,small)*res)/(256*R*R)*res
        size=norm(q)
        if size>=.5:break
    else:raise AssertionError('independent orthogonal seed failure')
    q/=size;scale=(C*ct-R*st)/C
    if edit=='untouched':result=f.copy()
    elif edit=='attenuate':result=mu+own+scale*comp+(R*ct+C*st)/R*res
    elif edit in ('sham_plus','sham_minus'):
        result=mu+own+comp+cs*res+(1 if edit=='sham_plus' else -1)*R*ss*q
    else:raise ValueError('declared edit required')
    return result,dict(degenerate=False,dose_rms=distance,competing_scale=float(scale),q_seed=qi)


def invariants(original,candidate,role,edit,detail):
    f,g=prior.unpack(original),prior.unpack(candidate)
    a,o,c,r=decompose(f,role);b,p,d,s=decompose(g,role)
    close=lambda x,y:np.testing.assert_allclose(x,y,atol=1e-12,rtol=0)
    close(a,b);close(norm(f),norm(g));close(o,p)
    close(norm(g-f),0. if edit=='untouched' else detail['dose_rms'])
    if detail['degenerate'] or edit=='untouched':assert candidate==original
    elif edit=='attenuate':
        close(d,detail['competing_scale']*c)
        assert 0.<detail['competing_scale']<1. and norm(s)>norm(r)
        close(s/norm(s),r/norm(r))
    else:close(c,d);close(norm(r),norm(s))
    return dict(mean_error=abs(a-b),rms_error=abs(norm(f)-norm(g)),own_axis_error=float(abs(o-p).max()),
        dose_error=abs(norm(g-f)-(0. if edit=='untouched' else detail['dose_rms'])))


def check_candidate(candidate,spec,source,source_meta,n,role,edit,kind,g):
    si=role*16+12+KINDS.index(kind);gi=g-1
    original=source['terminal_packet'][n,si,gi].tobytes()
    expected,detail=expected_edit(original,role,edit)
    np.testing.assert_allclose(prior.unpack(candidate),expected,atol=1e-12,rtol=0)
    error=invariants(original,candidate,role,edit,detail)
    reuse=candidate==original
    expected_spec=dict(role=role,edit=edit,kind=kind,generation=g,source_case=si,
        forward_shift=source['shift'][n,si,gi].tolist(),source_sha256=prior.sha(original),
        edited_sha256=prior.sha(candidate),new_assay=not reuse,
        source_mode='untouched' if edit=='untouched' else 'identical_bytes' if reuse else 'new_assay',**detail)
    physics.nested(spec,expected_spec)
    assert source_meta['cells'][n][si][gi]['forward_shift']==spec['forward_shift']
    return original,error


def measures(packet,original,role):
    f=prior.unpack(packet);mean,own,comp,res=decompose(f,role);z=f-mean;scale=norm(z)
    templates=prior.prior.targets();best=metrics.corr(f,templates).max(axis=(1,2))
    canon=[float(np.sum(z*templates[k])/(256*scale)) if scale else 0. for k in (role,1-role)]
    return np.array([mean,norm(f),norm(own),norm(comp),norm(res),norm(f-prior.unpack(original)),*canon,best[role],best[1-role]])


def observations(states,role):
    templates=prior.prior.targets();rows=[]
    for v,m,r in states:
        corr=metrics.corr(r,templates).max(axis=(1,2))
        rows.append([metrics.terminal_features(v,role)[0],corr[role],corr[1-role],
            float(np.sum(v*templates[role])-np.sum(v*templates[1-role]))/512])
    return np.asarray(rows,np.float64)


def check_life(raw,meta,source,source_meta,replay=False):
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(93000,93016),514246)
    assert type(life) is int and life in range(4) and (source_meta['index'],source_meta['life'])==(index,life)
    shapes=dict(packet=(2,32,3,2048),terminal_packet=(2,32,3,2048),shift=(2,32,3,2),
        terminal_states=(2,32,3,4,3,16,16),terminal_values=(2,32,3,4,4),record_values=(2,32,3,10),
        guide=(2,16,16),founder_packets=(2,2048))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('packet','terminal_packet','founder_packets') else np.int64 if k=='shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    for k in ('guide','founder_packets'):np.testing.assert_array_equal(raw[k],source[k])
    assert prior.sha(raw['guide'].astype('<f8').tobytes())==old.GUIDE_SHA256
    assert meta['host']==source_meta['host'] and meta['host']['index']==index
    tissue,ladder,bp=physics.parameters(meta['host']);new=0;terminal_max=measurement_max=invariant_max=0.
    trials=[]
    for n in (0,1):
        cases=[]
        for ci,(role,edit,kind) in enumerate(CASES):
            cells=[]
            for gi in range(3):
                g=gi+1;entry=meta['cells'][n][ci][gi]
                spec={k:v for k,v in entry.items() if k not in ('terminal_reader','assay_steps','carrier_bytes','assay_enters_lineage')}
                packet=raw['terminal_packet'][n,ci,gi].tobytes()
                original,error=check_candidate(packet,spec,source,source_meta,n,role,edit,kind,g)
                invariant_max=max(invariant_max,*error.values());si=spec['source_case']
                assert raw['packet'][n,ci,gi].tobytes()==original
                np.testing.assert_array_equal(raw['shift'][n,ci,gi],spec['forward_shift'])
                random=lambda p:physics.generator(PHYSICS_TAG,index,life,f'noise{n}:g{g}:terminal_{p}')
                states,reader=prior.read_trace(packet,tissue,ladder,bp,random('birth'),random('read'),CFG,
                    times=(0,1,100,300),replay=replay and spec['new_assay'])
                np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi,0],states[0])
                if spec['new_assay']:
                    new+=1
                    if replay:terminal_max=max(terminal_max,physics.compare(raw['terminal_states'][n,ci,gi],states))
                else:
                    np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi],source['terminal_states'][n,si,gi])
                    physics.nested(reader,source_meta['cells'][n][si][gi]['terminal_reader'])
                for k,v in (('record_values',measures(packet,original,role)),
                            ('terminal_values',observations(raw['terminal_states'][n,ci,gi],role))):
                    np.testing.assert_allclose(raw[k][n,ci,gi],v,atol=1e-12,rtol=0)
                    measurement_max=max(measurement_max,float(abs(raw[k][n,ci,gi]-v).max()))
                cells.append(dict(**spec,terminal_reader=reader,assay_steps=300,carrier_bytes=2048,assay_enters_lineage=False))
            cases.append(cells)
        trials.append(cases)
    expected=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CFG),cases=[list(c) for c in CASES],host=source_meta['host'],cells=trials,
        new_assays=new,reused_labels=192-new,labelled_cells=192,untouched=48,new_founders=0,
        new_upstream_dynamics=0,same_extended_history=True,new_independent_noise=False,guide_refitted=False,
        source_state_given_to_reader=False,assay_enters_lineage=False,analyst_supplied_edit=True,rerouted_after_edit=False)
    physics.nested({k:v for k,v in meta.items() if k!='replay'},expected)
    for ci in range(32):np.testing.assert_array_equal(raw['terminal_states'][:,ci,:,0],raw['terminal_states'][:,0,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['terminal_states'][1,0,0,0])
    for gi in (1,2):assert not np.array_equal(raw['terminal_states'][0,0,gi,0],raw['terminal_states'][0,0,gi-1,0])
    return dict(labelled_cells=192,untouched=48,new_assays=new,reused_labels=192-new,
        replayed_new_assays=new if replay else 0,replayed_existing_assays=0,new_founders=0,new_upstream_dynamics=0,
        terminal_max_abs=terminal_max,measurement_max_abs=measurement_max,invariant_max_abs=invariant_max,
        full_new_dynamics_replayed=bool(replay))
