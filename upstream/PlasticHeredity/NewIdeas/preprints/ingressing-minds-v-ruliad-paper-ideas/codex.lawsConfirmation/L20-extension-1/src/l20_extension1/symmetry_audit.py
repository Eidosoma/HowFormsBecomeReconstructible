"""Independent D144 geometry selection, source/cycle replay, FFT and reset checks."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import audit as metrics

prior=old.checker(); physics=prior.physics
TAG='l20-extension1-compatible-feedback-v1'
LEVELS=((-4,-3,-2,-1,0,1,2,3,4),(-4,-2,0,2,4))
CASES=tuple((r,k) for r in (0,1) for k in ('zero',)+tuple('q'+str(i) for i in LEVELS[r])+('copy','read_off','write_off'))
CFG=old.CONFIG
GUIDE='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'


def geometry(role,shift):
    dy,dx=map(int,shift)
    return 4-min(dy,16-dy) if role==0 else 4-2*min(dx%8,8-dx%8)


def address(index,life,noise,role,kind):
    if not kind.startswith('q'): return np.zeros(2,np.int64)
    offsets=[(y,x) for y in range(16) for x in range(16) if (y or x) and geometry(role,(y,x))==int(kind[1:])]
    random=physics.generator(TAG,index,life,f'address:noise{noise}:role{role}:{kind}')
    return np.array(offsets[int(random.integers(len(offsets)))],np.int64)


def observations(states,role):
    targets=prior.prior.targets()
    return np.array([[metrics.terminal_features(s[0],role)[0],metrics.corr(s[2],targets)[role].max()] for s in states])


def check_trial(raw,meta,founders,guide,host,replay):
    index,life,noise=meta['index'],meta['life'],meta['noise']
    assert type(index) is int and index in (*range(91000,91016),514244)
    assert type(life) is int and life in range(4) and type(noise) is int and noise in (0,1)
    shapes=dict(incoming=(22,2048),routed=(22,2048),outgoing=(22,2048),terminal_packet=(22,2048),
        read_states=(22,5,3,16,16),write_states=(22,4,4,16,16),terminal_states=(22,4,3,16,16),
        shift=(22,2),scores=(22,2,2,16,16),read_values=(22,5,2),write_values=(22,4,2),
        terminal_values=(22,4,2),record_values=(22,2))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('incoming','routed','outgoing','terminal_packet') else np.int64 if k=='shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    assert prior.sha(guide.astype('<f8').tobytes())==GUIDE
    tissue,ladder,bp=physics.parameters(host)
    assert (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    random=lambda phase:physics.generator(TAG,index,life,f'noise{noise}:{phase}')
    rmax=wmax=tmax=smax=vmax=0.; entries=[]
    for ci,(role,kind) in enumerate(CASES):
        incoming=founders[role].tobytes(); assert raw['incoming'][ci].tobytes()==incoming
        routed,scores,selection=prior.prior.select(incoming,guide)
        assert raw['routed'][ci].tobytes()==routed
        np.testing.assert_allclose(raw['scores'][ci,0],scores,atol=1e-12,rtol=0)
        smax=max(smax,float(abs(raw['scores'][ci,0]-scores).max()))
        reads,rm=prior.read_trace(routed,tissue,ladder,bp,random('birth'),random('read'),CFG,kind!='read_off',replay=replay)
        np.testing.assert_array_equal(raw['read_states'][ci,0],reads[0])
        if replay:rmax=max(rmax,physics.compare(raw['read_states'][ci],reads))
        shift=address(index,life,noise,role,kind); np.testing.assert_array_equal(raw['shift'][ci],shift)
        if kind.startswith('q'):assert np.any(shift) and geometry(role,shift)==int(kind[1:])
        mode='translated' if kind.startswith('q') else 'aligned'; start=raw['read_states'][ci,-1]
        writes,wm=prior.write_trace(start,tissue,ladder,random('write'),mode,shift,CFG,kind not in ('copy','write_off'),replay=replay)
        np.testing.assert_array_equal(raw['write_states'][ci,0],np.concatenate((start,np.zeros((1,16,16)))))
        if replay:wmax=max(wmax,physics.compare(raw['write_states'][ci],writes))
        ref=raw['write_states'][ci,-1,2]
        if kind not in ('copy','write_off'):assert np.tanh(ref).std()>1e-9
        output=incoming if kind=='copy' else bytes(2048) if kind=='write_off' else prior.packet(prior.project(np.tanh(ref)))
        assert raw['outgoing'][ci].tobytes()==output
        packet,scores,last_selection=prior.prior.select(output,guide)
        assert raw['terminal_packet'][ci].tobytes()==packet
        np.testing.assert_allclose(raw['scores'][ci,1],scores,atol=1e-12,rtol=0)
        smax=max(smax,float(abs(raw['scores'][ci,1]-scores).max()))
        terminal,tm=prior.read_trace(packet,tissue,ladder,bp,random('terminal_birth'),random('terminal_read'),CFG,times=CFG.times,replay=replay)
        np.testing.assert_array_equal(raw['terminal_states'][ci,0],terminal[0])
        assert not np.array_equal(raw['terminal_states'][ci,0],raw['read_states'][ci,0])
        if replay:tmax=max(tmax,physics.compare(raw['terminal_states'][ci],terminal))
        for phase in ('read','write','terminal'):
            values=observations(raw[phase+'_states'][ci],role)
            np.testing.assert_allclose(raw[phase+'_values'][ci],values,atol=1e-12,rtol=0)
            vmax=max(vmax,float(abs(raw[phase+'_values'][ci]-values).max()))
        values=np.array([metrics.corr(prior.unpack(p),prior.prior.targets())[role].max() for p in (incoming,output)])
        np.testing.assert_allclose(raw['record_values'][ci],values,atol=1e-12,rtol=0)
        vmax=max(vmax,float(abs(raw['record_values'][ci]-values).max()))
        entries.append(dict(role=role,kind=kind,selector=selection,reader=rm,writer=wm,
            terminal_selector=last_selection,terminal_reader=tm))
    expected=dict(index=index,life=life,noise=noise,tag=TAG,config=asdict(CFG),cases=[list(c) for c in CASES],
        paths=entries,guide_sha256=GUIDE,record_bytes=2048,public_guide_bytes=4096,parent_state_access=False,
        family_supplied_to_address_rule=True,writer_receives_target_labels=False,terminal_is_fresh=True,guide_refitted=False)
    physics.nested(meta,expected)
    for role in (0,1):
        base=CASES.index((role,'zero'))
        for ci,(r,kind) in enumerate(CASES):
            if r!=role:continue
            np.testing.assert_array_equal(raw['terminal_states'][ci,0],raw['terminal_states'][base,0])
            if kind!='read_off':np.testing.assert_array_equal(raw['read_states'][ci],raw['read_states'][base])
            if kind=='zero' or kind.startswith('q'):
                np.testing.assert_array_equal(raw['write_states'][ci,:2],raw['write_states'][base,:2])
    return dict(paths=22,enabled_rewrites=18,reader_paths=44,selectors=44,
        reader_max_abs=rmax,writer_max_abs=wmax,terminal_max_abs=tmax,selector_max_abs=smax,
        measurement_max_abs=vmax,full_dynamics_replayed=bool(replay))


def check_life(raw,meta,replay=False):
    assert set(meta) in ({'index','life','tag','config','founder','trials','host'},
        {'index','life','tag','config','founder','trials','host','replay'})
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(91000,91016),514244) and type(life) is int and life in range(4)
    assert meta['tag']==TAG and meta['host']['index']==index
    assert meta['founder']['index']==index and meta['founder']['life']==life and len(meta['trials'])==2
    physics.nested(meta['config'],asdict(CFG))
    for k in ('tissue','ladder','blueprint'):physics.nested(meta['host'][k],meta['founder'][k])
    assert set(meta['host'])=={'index','tissue','ladder','blueprint'}
    assert {k for k in raw if k.startswith('f_')}=={'f_'+k for k in prior.SOURCE_KEYS}
    source={k:raw['f_'+k] for k in prior.SOURCE_KEYS}
    fp=prior.check_founders(source,meta['founder'],CFG,replay,tag=TAG)
    founders=raw['founder_packets']; guide=raw['guide']
    assert founders.shape==(2,2048) and founders.dtype==np.uint8 and guide.shape==(2,16,16) and guide.dtype==np.float64
    assert prior.sha(guide.astype('<f8').tobytes())==GUIDE
    for r in (0,1):assert founders[r].tobytes()==prior.packet(source['written_fields'][r,0])
    trial_keys={k for k in raw if not k.startswith('f_') and k not in ('founder_packets','guide')}
    proofs=[]
    for n in (0,1):
        assert (meta['trials'][n]['index'],meta['trials'][n]['life'],meta['trials'][n]['noise'])==(index,life,n)
        proofs.append(check_trial({k:raw[k][n] for k in trial_keys},meta['trials'][n],founders,guide,meta['host'],replay))
    assert all(raw[k].shape[0]==2 for k in trial_keys)
    for phase in ('read','terminal'):
        assert not np.array_equal(raw[phase+'_states'][0,0,0],raw[phase+'_states'][1,0,0])
    return dict(paths=44,enabled_rewrites=36,reader_paths=88,selectors=88,founder_acquisitions=2,
        **fp,**{k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith('_max_abs')},full_dynamics_replayed=bool(replay))
