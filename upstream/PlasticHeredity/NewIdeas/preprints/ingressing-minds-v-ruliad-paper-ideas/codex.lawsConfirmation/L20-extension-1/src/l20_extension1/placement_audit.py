"""Independent D148 shifts, exact aliases, packet-only readers and metrics."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import audit as metrics

prior=old.checker();physics=prior.physics;CFG=old.CONFIG
TAG='l20-extension1-packet-placement-v1';PHYSICS_TAG='l20-extension1-phase-budget-v1'
SOURCE_RUN='l20_extension1_stopping_time_v1_attempt1'
GUIDE='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
KINDS=('intact','copy','read_off','write_off')
CASES=tuple((r,p,a,k) for r in (0,1) for p in (1000,1300) for a in (1000,1300) for k in KINDS)


def source_index(role,stop,kind):
    return role*8+(0 if stop==1000 else 4)+KINDS.index(kind)


def shifted(packet,shift):
    # Explicit source-coordinate lookup, independent of production np.roll.
    y,x=map(int,shift);f=prior.unpack(packet)
    return prior.packet(f[(np.arange(16)[:,None]+y)%16,(np.arange(16)[None,:]+x)%16])


def cell(source,source_meta,n,role,pstop,astop,kind,g):
    pi=source_index(role,pstop,kind);ai=source_index(role,astop,kind);gi=g-1
    packet=source['packet'][n,pi,gi].tobytes();donor=source['packet'][n,ai,gi].tobytes()
    natural,scores,selection=prior.prior.select(packet,source['guide'])
    _,_,address=prior.prior.select(donor,source['guide'])
    assert source['terminal_packet'][n,pi,gi].tobytes()==natural
    np.testing.assert_allclose(source['scores'][n,pi,gi],scores,atol=1e-12,rtol=0)
    physics.nested(source_meta['cells'][n][pi][gi]['terminal_selector'],selection)
    physics.nested(source_meta['cells'][n][ai][gi]['terminal_selector'],address)
    shift=address['chosen_forward_shift'];routed=shifted(packet,shift);reuse=routed==natural
    mode='natural_diagonal' if pstop==astop else 'identical_routed_bytes' if reuse else 'new_assay'
    assert reuse or pstop!=astop
    spec=dict(role=role,packet_stop=pstop,address_stop=astop,kind=kind,generation=g,recipient_case=pi,
        donor_case=ai,forward_shift=list(shift),packet_sha256=prior.sha(packet),donor_sha256=prior.sha(donor),
        routed_sha256=prior.sha(routed),natural_routed_sha256=prior.sha(natural),source_mode=mode,new_assay=not reuse)
    return packet,routed,spec,selection,address


def block_plan(index,raw,meta):
    cells=[]
    for life in range(4):
        source={k:v[life] for k,v in raw.items()};entry=meta['lives'][life]
        cells.append([[[cell(source,entry,n,r,p,a,k,g)[2] for g in (1,2,3)] for r,p,a,k in CASES] for n in (0,1)])
    new=sum(c['new_assay'] for l in cells for n in l for case in n for c in case)
    return dict(index=index,cells=cells,labelled_cells=768,natural_diagonals=384,new_assays=new,reused_labels=768-new)


def measures(packet,routed,role,guide):
    rec=metrics.record_features(packet,role,guide)
    best=metrics.corr(prior.unpack(packet),prior.prior.targets()).max(axis=(1,2))
    f=prior.unpack(routed);z=f-np.mean(f);scale=np.sqrt(np.sum(z*z)/256)
    canon=[float(np.sum(z*prior.prior.targets()[r])/(256*scale)) if scale else 0. for r in (role,1-role)]
    return np.array([rec[0],rec[1],rec[2],best[1-role],*canon,canon[0]-canon[1]])


def check_life(raw,meta,source,source_meta,replay=False):
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(93000,93016),514246)
    assert type(life) is int and life in range(4) and (source_meta['index'],source_meta['life'])==(index,life)
    shapes=dict(packet=(2,32,3,2048),terminal_packet=(2,32,3,2048),shift=(2,32,3,2),
        terminal_states=(2,32,3,4,3,16,16),terminal_values=(2,32,3,4,2),record_values=(2,32,3,7),
        guide=(2,16,16),founder_packets=(2,2048))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('packet','terminal_packet','founder_packets') else np.int64 if k=='shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    for key in ('guide','founder_packets'):np.testing.assert_array_equal(raw[key],source[key])
    assert prior.sha(raw['guide'].astype('<f8').tobytes())==GUIDE
    tissue,ladder,bp=physics.parameters(meta['host']);assert meta['host']['index']==index
    trials=[];new=0;terminal_max=measurement_max=0.
    for n in (0,1):
        entries=[]
        for ci,(role,pstop,astop,kind) in enumerate(CASES):
            cells=[]
            for gi in range(3):
                g=gi+1
                packet,routed,spec,selection,address=cell(source,source_meta,n,role,pstop,astop,kind,g)
                assert raw['packet'][n,ci,gi].tobytes()==packet
                assert raw['terminal_packet'][n,ci,gi].tobytes()==routed
                np.testing.assert_array_equal(raw['shift'][n,ci,gi],spec['forward_shift'])
                np.testing.assert_array_equal(np.sort(prior.unpack(packet).ravel()),np.sort(prior.unpack(routed).ravel()))
                random=lambda p:physics.generator(PHYSICS_TAG,index,life,f'noise{n}:g{g}:terminal_{p}')
                states,reader=prior.read_trace(routed,tissue,ladder,bp,random('birth'),random('read'),CFG,
                    times=(0,1,100,300),replay=replay and spec['new_assay'])
                np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi,0],states[0])
                if spec['new_assay']:
                    new+=1
                    assert kind in ('intact','read_off')
                    if replay:terminal_max=max(terminal_max,physics.compare(raw['terminal_states'][n,ci,gi],states))
                else:
                    pi=spec['recipient_case']
                    np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi],source['terminal_states'][n,pi,gi])
                    physics.nested(reader,source_meta['cells'][n][pi][gi]['terminal_reader'])
                rec=measures(packet,routed,role,raw['guide'])
                values=np.array([[metrics.terminal_features(s[0],role)[0],metrics.corr(s[2],prior.prior.targets())[role].max()]
                    for s in raw['terminal_states'][n,ci,gi]])
                for k,x in (('record_values',rec),('terminal_values',values)):
                    np.testing.assert_allclose(raw[k][n,ci,gi],x,atol=1e-12,rtol=0)
                    measurement_max=max(measurement_max,float(abs(raw[k][n,ci,gi]-x).max()))
                cells.append(dict(**spec,natural_selector=selection,address_selector=address,terminal_reader=reader,
                    assay_steps=300,carrier_bytes=2048,assay_enters_lineage=False))
            entries.append(cells)
        trials.append(entries)
    expected=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CFG),cases=[list(c) for c in CASES],host=source_meta['host'],cells=trials,
        new_assays=new,reused_labels=192-new,labelled_cells=192,natural_diagonals=96,new_founders=0,
        new_upstream_dynamics=0,same_extended_history=True,new_independent_noise=False,guide_refitted=False,
        source_state_given_to_reader=False,assay_enters_lineage=False,placement_supplied_by_analyst=True)
    physics.nested({k:v for k,v in meta.items() if k!='replay'},expected)
    for ci in range(32):np.testing.assert_array_equal(raw['terminal_states'][:,ci,:,0],raw['terminal_states'][:,0,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['terminal_states'][1,0,0,0])
    for gi in (1,2):assert not np.array_equal(raw['terminal_states'][0,0,gi,0],raw['terminal_states'][0,0,gi-1,0])
    return dict(labelled_cells=192,natural_diagonals=96,new_assays=new,reused_labels=192-new,
        replayed_new_assays=new if replay else 0,replayed_existing_assays=0,new_founders=0,new_upstream_dynamics=0,
        terminal_max_abs=terminal_max,measurement_max_abs=measurement_max,full_new_dynamics_replayed=bool(replay))
