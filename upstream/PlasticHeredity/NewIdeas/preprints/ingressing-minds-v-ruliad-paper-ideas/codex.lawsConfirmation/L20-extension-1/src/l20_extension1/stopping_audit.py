"""Independent D147 packet construction, exact reuse, readers and measurements."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import audit as metrics

prior=old.checker(); physics=prior.physics
CFG=old.CONFIG
TAG='l20-extension1-stopping-time-v1'
PHYSICS_TAG='l20-extension1-phase-budget-v1'
SOURCE_RUN='l20_extension1_phase_budget_v1_attempt1'
GUIDE='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
KINDS=('intact','copy','read_off','write_off')
CASES=tuple((r,t,k) for r in (0,1) for t in (1000,1300) for k in KINDS)


def endpoint_kind(stop,kind,generation):
    if kind=='copy': return 'write_copy'
    if kind=='write_off': return 'write_write_off'
    if stop==1300: return 'write' if kind=='intact' else 'write_read_off'
    if kind=='read_off': return 'base_read_off'
    return 'base' if generation==1 else None


def index_of(role,kind):
    names=('base','base_copy','base_read_off','base_write_off','read','read_copy',
        'read_read_off','read_write_off','write','write_copy','write_read_off','write_write_off')
    return role*12+names.index(kind)


def source_bridges(source):
    for role in (0,1):
        for offset,generations in ((0,(0,)),(2,range(3))):
            bi=role*12+offset;wi=bi+8
            for gi in generations:
                np.testing.assert_array_equal(source['read_states'][:,bi,gi],source['read_states'][:,wi,gi])
                for a,b in ((0,0),(1,1),(2,2),(4,3)):
                    np.testing.assert_array_equal(source['write_states'][:,bi,gi,a],source['write_states'][:,wi,gi,b])
        for offset in (1,3):
            for key in ('outgoing','terminal_packet','terminal_states'):
                np.testing.assert_array_equal(source[key][:,role*12+offset],source[key][:,role*12+offset+8])


def check_life(raw,meta,source,source_meta,replay=False):
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(93000,93016),514246)
    assert type(life) is int and life in range(4) and (source_meta['index'],source_meta['life'])==(index,life)
    source_bridges(source)
    shapes=dict(packet=(2,16,3,2048),terminal_packet=(2,16,3,2048),scores=(2,16,3,2,16,16),
        terminal_states=(2,16,3,4,3,16,16),terminal_values=(2,16,3,4,2),record_values=(2,16,3,4),
        founder_packets=(2,2048),guide=(2,16,16))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('packet','terminal_packet','founder_packets') else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    guide=raw['guide']; assert prior.sha(guide.astype('<f8').tobytes())==GUIDE
    for k in ('guide','founder_packets'): np.testing.assert_array_equal(raw[k],source[k])
    tissue,ladder,bp=physics.parameters(meta['host'])
    assert meta['host']['index']==index and (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    trials=[]; new=0; terminal_max=selector_max=measurement_max=0.
    for n in (0,1):
        entries=[]
        for ci,(role,stop,kind) in enumerate(CASES):
            history=[]
            for gi in range(3):
                g=gi+1; snapshot_kind='write'+('' if kind=='intact' else '_'+kind)
                si=index_of(role,snapshot_kind); checkpoint=3 if stop==1000 else 4
                if kind=='copy': packet=source['founder_packets'][role].tobytes()
                elif kind=='write_off': packet=bytes(2048)
                else:
                    ref=source['write_states'][n,si,gi,checkpoint,2]
                    assert np.tanh(ref).std()>1e-9
                    packet=prior.packet(prior.project(np.tanh(ref)))
                assert raw['packet'][n,ci,gi].tobytes()==packet
                routed,scores,selection=prior.prior.select(packet,guide)
                assert raw['terminal_packet'][n,ci,gi].tobytes()==routed
                np.testing.assert_allclose(raw['scores'][n,ci,gi],scores,atol=1e-12,rtol=0)
                selector_max=max(selector_max,float(abs(raw['scores'][n,ci,gi]-scores).max()))
                reused=endpoint_kind(stop,kind,g)
                random=lambda p:physics.generator(PHYSICS_TAG,index,life,f'noise{n}:g{g}:terminal_{p}')
                states,reader=prior.read_trace(routed,tissue,ladder,bp,random('birth'),random('read'),
                    CFG,times=(0,1,100,300),replay=replay and reused is None)
                np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi,0],states[0])
                if reused is None:
                    new+=1
                    if replay: terminal_max=max(terminal_max,physics.compare(raw['terminal_states'][n,ci,gi],states))
                else:
                    ei=index_of(role,reused)
                    assert source['outgoing'][n,ei,gi].tobytes()==packet
                    assert source['terminal_packet'][n,ei,gi].tobytes()==routed
                    np.testing.assert_array_equal(raw['terminal_states'][n,ci,gi],source['terminal_states'][n,ei,gi])
                    original=source_meta['trials'][n]['paths'][ei]['generations'][gi]
                    physics.nested(original['terminal_reader'],reader)
                    physics.nested(original['terminal_selector'],selection)
                # A fixed fresh assay, not a warmed source body or inherited state.
                assert not np.array_equal(states[0],source['read_states'][n,si,gi,0])
                values=np.array([[metrics.terminal_features(s[0],role)[0],
                    metrics.corr(s[2],prior.prior.targets())[role].max()] for s in raw['terminal_states'][n,ci,gi]])
                rec=metrics.record_features(packet,role,guide)
                for k,expected in (('terminal_values',values),('record_values',rec)):
                    np.testing.assert_allclose(raw[k][n,ci,gi],expected,atol=1e-12,rtol=0)
                    measurement_max=max(measurement_max,float(abs(raw[k][n,ci,gi]-expected).max()))
                history.append(dict(role=role,stop=stop,kind=kind,generation=g,snapshot_kind=snapshot_kind,
                    write_checkpoint=checkpoint,endpoint_source_kind=reused,new_assay=reused is None,
                    terminal_selector=selection,terminal_reader=reader,assay_steps=300,carrier_bytes=2048,
                    assay_enters_lineage=False))
            entries.append(history)
        trials.append(entries)
    expected=dict(index=index,life=life,tag=TAG,physics_namespace=PHYSICS_TAG,source_run=SOURCE_RUN,
        config=asdict(CFG),cases=[list(c) for c in CASES],host=source_meta['host'],cells=trials,
        new_assays=8,labelled_cells=96,new_founders=0,new_upstream_dynamics=0,same_extended_history=True,
        new_independent_noise=False,guide_refitted=False,source_state_given_to_reader=False,assay_enters_lineage=False)
    actual={k:v for k,v in meta.items() if k!='replay'}
    physics.nested(actual,expected)
    for ci in range(16):
        np.testing.assert_array_equal(raw['terminal_states'][:,ci,:,0],raw['terminal_states'][:,0,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['terminal_states'][1,0,0,0])
    for gi in (1,2): assert not np.array_equal(raw['terminal_states'][0,0,gi,0],raw['terminal_states'][0,0,gi-1,0])
    assert new==8
    return dict(labelled_cells=96,new_assays=8,reused_labels=88,new_founders=0,new_upstream_dynamics=0,
        replayed_new_assays=8 if replay else 0,replayed_existing_assays=0,
        terminal_max_abs=terminal_max,selector_max_abs=selector_max,measurement_max_abs=measurement_max,
        full_new_dynamics_replayed=bool(replay))
