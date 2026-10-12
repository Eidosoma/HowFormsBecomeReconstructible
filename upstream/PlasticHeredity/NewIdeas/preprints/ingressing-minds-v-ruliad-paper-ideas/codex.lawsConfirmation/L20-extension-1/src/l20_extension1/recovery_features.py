"""D150 saved diagnostics only: fixed seven starting and six recovery features."""
from pathlib import Path
import numpy as np
from laws_confirmation import l15_repair_speed_run as io

ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
WS=Path(__file__).resolve().parents[2]
DEV='l20_extension1_development_v1_attempt1';HELD='l20_extension1_heldout_v1_attempt1'
REPEATED='l20_extension1_repeated_futures_v1_attempt1'
SPECS=tuple([('d135',i) for i in range(75000,75008)]+[('d140',i) for i in range(78000,78008)]+
            [('former_test',i) for i in range(90000,90016)])
CASES=((0,'translated'),(0,'aligned'),(1,'translated'),(1,'aligned'))
MODELS=('starting','passive_endpoint','challenge_endpoint','passive_recovery','challenge_recovery')
INITIAL=('own_best','best_margin','guide_margin','canonical_margin','own_axis_rms','alternative_axis_rms','residual_rms')
ENDPOINT=('own_best','best_margin','guide_margin','canonical_margin','preference','V_rms')
RECOVERY=('read_own','read_alternative','early_write_own','early_write_alternative','late_write_own','late_write_alternative')
y,x=np.indices((16,16))
TARGETS=np.stack((np.where(y<8,1.,-1.),np.where(x%8<4,1.,-1.)))
BANK=np.stack([np.roll(TARGETS[0],i,axis=0) for i in range(16)]+
              [np.roll(TARGETS[1],i,axis=1) for i in range(8)]).reshape(24,256)
ALLOWED=('founder_packets','initial_features','diagnostic_features','routed','outgoing','terminal_packet',
         'read_states','write_states','terminal_states','guide','scores')


def paths(spec,disposable=False):
    if disposable:
        if spec not in (('disposable_dev',514240),('disposable_test',514240)):raise ValueError('declared disposable')
        run=DEV if spec[0]=='disposable_dev' else HELD
        stem='disposable_514240' if run==DEV else 'diagnostic_514240'
        directory=ROOT/'tmp'/(run+'_benchmark')
    else:
        if spec not in SPECS:raise ValueError('declared 32-block development panel only')
        run=HELD if spec[0]=='former_test' else DEV
        stem=f'diagnostic_{spec[1]}' if run==HELD else f'{spec[0]}_{spec[1]}'
        directory=ROOT/'outputs'/run
    return directory/(stem+'.npz'),directory/(stem+'.json')


def diagnostic(spec,disposable=False):
    a,b=paths(spec,disposable);meta=io.read_json(b)
    with np.load(a,allow_pickle=False) as opened:
        raw={k:opened[k] for k in ALLOWED}
    assert meta['index']==spec[1] and len(meta['lives'])==4
    for l,m in enumerate(meta['lives']):
        assert m['life']==l and m['index']==spec[1] and m['cases']==[list(c) for c in CASES]
        assert m['branches']==['U0','U1','C1'] and not m['diagnostic_to_lineage'] and not m['predictor_has_parent_state']
        expected_host=spec[1]-2000 if spec[0]=='d135' else spec[1]
        assert m['host']['index']==expected_host
    for v in raw.values():v.setflags(write=False)
    return raw,meta


def decode(value):
    value=np.asarray(value)
    if value.dtype!=np.uint8 or value.shape[-1]!=2048:raise ValueError('ordinary carrier bytes required')
    return np.frombuffer(value.tobytes(),'<f8').reshape(value.shape[:-1]+(16,16))


def best(value,role):
    value=np.asarray(value)
    if value.shape[-2:]!=(16,16) or not np.isfinite(value).all() or role not in (0,1):raise ValueError('finite field/role')
    z=value-value.mean(axis=(-2,-1),keepdims=True);scale=np.sqrt(np.mean(z*z,axis=(-2,-1)))
    cov=(z.reshape(-1,256)@BANK.T/256).reshape(value.shape[:-2]+(24,))
    score=np.divide(cov,scale[...,None],out=np.zeros_like(cov),where=scale[...,None]!=0)
    both=np.stack((score[...,:16].max(axis=-1),score[...,16:].max(axis=-1)),-1)
    return both[...,[role,1-role]]


def axis_rms(value,role):
    z=value-value.mean(axis=(-2,-1),keepdims=True)
    row=z.mean(axis=-1,keepdims=True);col=z.mean(axis=-2,keepdims=True);res=z-row-col
    rms=lambda a:np.sqrt(np.mean(a*a,axis=(-2,-1)))
    return np.stack((rms(row) if role==0 else rms(col),rms(col) if role==0 else rms(row),rms(res)),-1)


def preference(v,role):
    strong=abs(v)>.2
    own=((v>0)==(TARGETS[role]>0))&strong;alt=((v>0)==(TARGETS[1-role]>0))&strong
    return (own.sum(axis=(-2,-1))-alt.sum(axis=(-2,-1)))/256


def extract(raw):
    if set(raw)!=set(ALLOWED):raise ValueError('only declared diagnostic measurements may enter feature extraction')
    assert raw['initial_features'].shape==(4,4,4) and raw['diagnostic_features'].shape==(4,4,3,6)
    assert raw['read_states'].shape==(4,4,3,5,3,16,16)
    assert raw['write_states'].shape==(4,4,3,4,4,16,16)
    assert raw['terminal_states'].shape==(4,4,3,4,3,16,16)
    assert all(np.isfinite(v).all() for v in raw.values())
    start=np.empty((4,4,7));stages=np.empty((4,4,3,4,2))
    for ci,(role,_) in enumerate(CASES):
        start[:,ci,:4]=raw['initial_features'][:,ci]
        start[:,ci,4:]=axis_rms(decode(raw['founder_packets'][:,role]),role)
        np.testing.assert_array_equal(raw['write_states'][:,ci,:,0,:3],raw['read_states'][:,ci,:,-1])
        fields=(decode(raw['routed'][:,ci]),raw['read_states'][:,ci,:,-1,2],
                raw['write_states'][:,ci,:,2,2],raw['write_states'][:,ci,:,3,2])
        for j,f in enumerate(fields):stages[:,ci,:,j]=best(f,role)
    recovery=np.diff(stages,axis=-2).reshape(4,4,3,6)
    return dict(start=start,endpoint=raw['diagnostic_features'].copy(),recovery=recovery,stages=stages)


def assemble(data):
    a,b,c=data['start'],data['endpoint'],data['recovery']
    if a.shape[-1]!=7 or b.shape!=a.shape[:-1]+(3,6) or c.shape!=b.shape:raise ValueError('declared complete features')
    p=np.concatenate((a,b[...,0,:],b[...,1,:]),axis=-1)
    q=np.concatenate((a,b[...,0,:],b[...,2,:]),axis=-1)
    return dict(starting=a,passive_endpoint=p,challenge_endpoint=q,
        passive_recovery=np.concatenate((p,c[...,0,:],c[...,1,:]),axis=-1),
        challenge_recovery=np.concatenate((q,c[...,0,:],c[...,2,:]),axis=-1))


def labels(spec,disposable=False):
    # Deliberately separate from diagnostic() / extract(): actual outcomes are labels only.
    if spec[0] in ('d135','d140','disposable_dev'):
        a,_=paths(spec,disposable)
        with np.load(a,allow_pickle=False) as opened:result=opened['outcomes'].copy()
    else:
        if spec not in SPECS and not (disposable and spec==('disposable_test',514240)):raise ValueError('declared block')
        directory=ROOT/('tmp' if disposable else 'outputs')/(HELD+('_benchmark' if disposable else ''))
        meta=io.read_json(directory/f'lineage_{spec[1]}.json')
        with np.load(directory/f'lineage_{spec[1]}.npz',allow_pickle=False) as opened:
            values=opened['terminal_values'];states=opened['terminal_states']
        result=np.empty((4,4))
        for l in range(4):
            for ci,(role,kind) in enumerate(CASES):
                pi=meta['lives'][l]['probes'].index([role,kind]);v=values[l,pi,-1]
                result[l,ci]=v[0]-v[1]
                assert result[l,ci]==preference(states[l,pi,-1,0],role)
    assert result.shape==(4,4) and np.isfinite(result).all() and np.max(abs(result))<=1
    return result


def futures(index):
    if type(index) is not int or index not in range(90000,90016):raise ValueError('only saved D142 cases')
    directory=ROOT/'outputs'/REPEATED
    with np.load(directory/f'block_{index}.npz',allow_pickle=False) as opened:
        v=opened['terminal_values'];states=opened['terminal_states']
    result=(v[...,-1,0]-v[...,-1,1]).transpose(0,2,1).copy()
    assert result.shape==(4,4,4)
    for ci,(role,_) in enumerate(CASES):np.testing.assert_array_equal(result[:,ci],preference(states[:,:,ci,-1,0],role))
    return result
