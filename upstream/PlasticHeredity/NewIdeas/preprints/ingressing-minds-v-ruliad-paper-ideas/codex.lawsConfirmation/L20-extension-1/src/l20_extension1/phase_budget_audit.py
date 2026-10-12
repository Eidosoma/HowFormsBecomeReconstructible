"""Independent D146 timed-prefix, byte-continuity and full physics checks."""
from dataclasses import asdict, dataclass
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import audit as metrics

prior=old.checker(); physics=prior.physics
TAG='l20-extension1-phase-budget-v1'
TIMINGS={'base':(300,1000),'read':(600,1000),'write':(300,1300)}
KINDS=tuple(t+s for t in ('base','read','write') for s in ('','_copy','_read_off','_write_off'))
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
CFG=old.CONFIG

@dataclass(frozen=True)
class CheckConfig(old.Config):
    @property
    def read_times(self):
        return (0,1,100,101,300,600) if self.steps==600 else (0,1,100,101,200,300)
    @property
    def source_times(self):
        return (0,1,300,1000,1300) if self.source_steps==1300 else (0,1,300,500,1000)

def phase_config(kind):
    assert kind in KINDS
    r,w=TIMINGS[kind.split('_')[0]]
    return CheckConfig(steps=r,source_steps=w)

GUIDE='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'


def geometry(role,shift):
    dy,dx=map(int,shift)
    return 4-min(dy,16-dy) if role==0 else 4-2*min(dx%8,8-dx%8)


def address(index,life,noise,role,kind,generation):
    assert kind in KINDS
    offsets=[(y,x) for y in range(16) for x in range(16)
        if (y or x) and geometry(role,(y,x))==4]
    random=physics.generator(TAG,index,life,f'address:noise{noise}:role{role}:q4:g{generation}')
    return np.array(offsets[int(random.integers(len(offsets)))],np.int64)


def observations(states,role):
    targets=prior.prior.targets()
    return np.array([[metrics.terminal_features(s[0],role)[0],
        metrics.corr(s[2],targets)[role].max()] for s in states])


def check_trial(raw,meta,founders,guide,host,replay):
    index,life,noise=meta['index'],meta['life'],meta['noise']
    assert type(index) is int and index in (*range(93000,93016),514246)
    assert type(life) is int and life in range(4) and type(noise) is int and noise in (0,1)
    shapes=dict(incoming=(24,3,2048),routed=(24,3,2048),outgoing=(24,3,2048),terminal_packet=(24,3,2048),
        read_states=(24,3,6,3,16,16),write_states=(24,3,5,4,16,16),terminal_states=(24,3,4,3,16,16),
        shift=(24,3,2),scores=(24,3,2,2,16,16),read_values=(24,3,6,2),write_values=(24,3,5,2),
        terminal_values=(24,3,4,2),record_values=(24,3,2))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('incoming','routed','outgoing','terminal_packet') else np.int64 if k=='shift' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all(),k
    assert prior.sha(guide.astype('<f8').tobytes())==GUIDE
    tissue,ladder,bp=physics.parameters(host)
    assert (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    rmax=wmax=tmax=smax=vmax=0.; entries=[]
    for ci,(role,kind) in enumerate(CASES):
        cfg=phase_config(kind)
        incoming=founders[role].tobytes(); generations=[]
        for gi in range(3):
            g=gi+1
            random=lambda phase:physics.generator(TAG,index,life,f'noise{noise}:g{g}:{phase}')
            assert raw['incoming'][ci,gi].tobytes()==incoming
            if gi:np.testing.assert_array_equal(raw['incoming'][ci,gi],raw['outgoing'][ci,gi-1])
            routed,scores,selection=prior.prior.select(incoming,guide)
            assert raw['routed'][ci,gi].tobytes()==routed
            np.testing.assert_allclose(raw['scores'][ci,gi,0],scores,atol=1e-12,rtol=0)
            smax=max(smax,float(abs(raw['scores'][ci,gi,0]-scores).max()))
            enabled_read=not kind.endswith('_read_off')
            reads,rm=prior.read_trace(routed,tissue,ladder,bp,random('birth'),random('read'),cfg,enabled_read,replay=replay)
            np.testing.assert_array_equal(raw['read_states'][ci,gi,0],reads[0])
            if replay:rmax=max(rmax,physics.compare(raw['read_states'][ci,gi],reads))
            shift=address(index,life,noise,role,kind,g)
            np.testing.assert_array_equal(raw['shift'][ci,gi],shift)
            assert np.any(shift) and geometry(role,shift)==4
            mode='translated'
            enabled_write=not kind.endswith(('_copy','_write_off'))
            start=raw['read_states'][ci,gi,-1]
            writes,wm=prior.write_trace(start,tissue,ladder,random('write'),mode,shift,cfg,enabled_write,replay=replay)
            np.testing.assert_array_equal(raw['write_states'][ci,gi,0],np.concatenate((start,np.zeros((1,16,16)))))
            if replay:wmax=max(wmax,physics.compare(raw['write_states'][ci,gi],writes))
            ref=raw['write_states'][ci,gi,-1,2]
            if enabled_write:assert np.tanh(ref).std()>1e-9
            output=incoming if kind.endswith('_copy') else bytes(2048) if kind.endswith('_write_off') else prior.packet(prior.project(np.tanh(ref)))
            assert raw['outgoing'][ci,gi].tobytes()==output
            packet,scores,last_selection=prior.prior.select(output,guide)
            assert raw['terminal_packet'][ci,gi].tobytes()==packet
            np.testing.assert_allclose(raw['scores'][ci,gi,1],scores,atol=1e-12,rtol=0)
            smax=max(smax,float(abs(raw['scores'][ci,gi,1]-scores).max()))
            terminal,tm=prior.read_trace(packet,tissue,ladder,bp,random('terminal_birth'),random('terminal_read'),
                CFG,times=CFG.times,replay=replay)
            np.testing.assert_array_equal(raw['terminal_states'][ci,gi,0],terminal[0])
            assert not np.array_equal(raw['terminal_states'][ci,gi,0],raw['read_states'][ci,gi,0])
            if gi:
                assert not np.array_equal(raw['read_states'][ci,gi,0],raw['read_states'][ci,gi-1,0])
                assert not np.array_equal(raw['read_states'][ci,gi,0],raw['terminal_states'][ci,gi-1,0])
            if replay:tmax=max(tmax,physics.compare(raw['terminal_states'][ci,gi],terminal))
            for phase in ('read','write','terminal'):
                values=observations(raw[phase+'_states'][ci,gi],role)
                np.testing.assert_allclose(raw[phase+'_values'][ci,gi],values,atol=1e-12,rtol=0)
                vmax=max(vmax,float(abs(raw[phase+'_values'][ci,gi]-values).max()))
            values=np.array([metrics.corr(prior.unpack(p),prior.prior.targets())[role].max() for p in (incoming,output)])
            np.testing.assert_allclose(raw['record_values'][ci,gi],values,atol=1e-12,rtol=0)
            vmax=max(vmax,float(abs(raw['record_values'][ci,gi]-values).max()))
            generations.append(dict(generation=g,role=role,kind=kind,phase_config=asdict(cfg),
                read_times=list(cfg.read_times),write_times=list(cfg.source_times),assay_steps=300,
                selector=selection,reader=rm,writer=wm,
                terminal_selector=last_selection,terminal_reader=tm,erased_before_writing=True,
                inherited_bytes=2048,assay_enters_lineage=False))
            incoming=output
        entries.append(dict(role=role,kind=kind,generations=generations))
    expected=dict(index=index,life=life,noise=noise,tag=TAG,config=asdict(CFG),cases=[list(c) for c in CASES],
        paths=entries,timings={k:list(v) for k,v in TIMINGS.items()},guide_sha256=GUIDE,generations=3,record_bytes=2048,public_guide_bytes=4096,parent_state_access=False,
        family_supplied_to_address_rule=True,writer_receives_target_labels=False,terminal_is_fresh=True,
        assay_enters_lineage=False,guide_refitted=False)
    physics.nested(meta,expected)
    for role in (0,1):
        base=CASES.index((role,'base')); basecfg=phase_config('base')
        for ci,(r,kind) in enumerate(CASES):
            if r!=role:continue
            cfg=phase_config(kind)
            for phase in ('read','terminal'):
                np.testing.assert_array_equal(raw[phase+'_states'][ci,:,0],raw[phase+'_states'][base,:,0])
            np.testing.assert_array_equal(raw['shift'][ci],raw['shift'][base])
            if not kind.endswith('_read_off'):
                for t in set(cfg.read_times)&set(basecfg.read_times):
                    np.testing.assert_array_equal(raw['read_states'][ci,0,cfg.read_times.index(t)],
                        raw['read_states'][base,0,basecfg.read_times.index(t)])
        # Only G1 base/write intact starts are identical. Later records diverge.
        wi=CASES.index((role,'write')); wcfg=phase_config('write')
        for t in set(basecfg.source_times)&set(wcfg.source_times):
            np.testing.assert_array_equal(raw['write_states'][base,0,basecfg.source_times.index(t)],
                raw['write_states'][wi,0,wcfg.source_times.index(t)])
        for suffix in ('_copy','_write_off'):
            original=CASES.index((role,'base'+suffix))
            for timing in ('read','write'):
                ci=CASES.index((role,timing+suffix))
                for k in ('incoming','outgoing','terminal_packet','terminal_states'):
                    np.testing.assert_array_equal(raw[k][ci],raw[k][original])
        # An extended disabled reader shares the zero-input trajectory prefix.
        bi=CASES.index((role,'base_read_off')); ri=CASES.index((role,'read_read_off'))
        rcfg=phase_config('read')
        for t in set(basecfg.read_times)&set(rcfg.read_times):
            np.testing.assert_array_equal(raw['read_states'][bi,:,basecfg.read_times.index(t)],
                raw['read_states'][ri,:,rcfg.read_times.index(t)])
    return dict(lineages=24,paths=72,enabled_rewrites=36,reader_paths=144,selectors=144,
        reader_max_abs=rmax,writer_max_abs=wmax,terminal_max_abs=tmax,selector_max_abs=smax,
        measurement_max_abs=vmax,full_dynamics_replayed=bool(replay))


def check_life(raw,meta,replay=False):
    assert set(meta) in ({'index','life','tag','config','founder','trials','host'},
        {'index','life','tag','config','founder','trials','host','replay'})
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(93000,93016),514246) and type(life) is int and life in range(4)
    assert meta['tag']==TAG and meta['host']['index']==index
    assert meta['founder']['index']==index and meta['founder']['life']==life and len(meta['trials'])==2
    physics.nested(meta['config'],asdict(CFG))
    for k in ('tissue','ladder','blueprint'):physics.nested(meta['host'][k],meta['founder'][k])
    assert set(meta['host'])=={'index','tissue','ladder','blueprint'}
    assert {k for k in raw if k.startswith('f_')}=={'f_'+k for k in prior.SOURCE_KEYS}
    source={k:raw['f_'+k] for k in prior.SOURCE_KEYS}
    fp=prior.check_founders(source,meta['founder'],CFG,replay,tag=TAG)
    founders=raw['founder_packets'];guide=raw['guide']
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
        assert not np.array_equal(raw[phase+'_states'][0,0,0,0],raw[phase+'_states'][1,0,0,0])
    return dict(lineages=48,paths=144,enabled_rewrites=72,reader_paths=288,selectors=288,founder_acquisitions=2,
        **fp,**{k:max(p[k] for p in proofs) for k in proofs[0] if k.endswith('_max_abs')},full_dynamics_replayed=bool(replay))
