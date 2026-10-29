"""Independent inclusive-window replay, pre/post hold checks and body scoring."""
import hashlib,json
import numpy as np
import physical_reference as ref

def address(index):
    material=json.dumps(['TT022_serial_capture_v1',index,0,1,'repair'],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:16],'little')

def repair(ctx,initial,window,raw,meta,body,replay):
    begin,end=window;cfg=ctx['config']
    assert type(begin) is int and type(end) is int
    assert (begin,end)==(0,0) or 1<=begin<=end<=cfg.sweeps
    assert set(initial)==set(ref.KEYS) and set(raw)=={f's{t}_{k}' for t in cfg.times for k in ref.KEYS}
    state={k:v.copy() for k,v in initial.items()}
    for k,v in state.items():
        assert v.shape==(16,16,16) and v.dtype==np.float64 and np.isfinite(v).all()
        ref.exact(raw['s0_'+k],v,'restored '+k)
    ref.exact(state['ema'],np.zeros_like(state['V']),'zero ema')
    ref.exact(state['R'],state['V']-ctx['tissue'].resting*.5,'uniform memory')
    expected=0 if begin==0 else end-begin+1
    assert (meta['write_start'],meta['write_end'])==(begin,end)
    assert meta['write_updates']==expected and meta['nonwriting_exact_checks']==cfg.sweeps-expected
    assert meta['total_updates']==cfg.sweeps and meta['carrier_bytes_per_record']==2048
    final=raw[f's{end}_theta']
    assert meta['final_theta_sha256']==hashlib.sha256(final.tobytes()).hexdigest()
    for t in cfg.times:
        if t<begin:ref.exact(raw[f's{t}_theta'],initial['theta'],'saved prewrite packet')
        if t>=end:ref.exact(raw[f's{t}_theta'],final,'saved postwrite packet')
    checked=0
    if replay:
        rng=ref.Coupled(ref.REPAIR_TAG,address(ctx['index']),'repair',cfg.replicates)
        writes=0
        for t in range(cfg.sweeps+1):
            if t:
                enabled=(begin!=0 and t>=begin and t<=end);writes+=int(enabled)
                state=ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],cfg,rng,enabled,True)
            if t in cfg.times:
                for k in ref.KEYS:ref.exact(raw[f's{t}_{k}'],state[k],f'independent {t} {k}');checked+=1
            if t<begin:ref.exact(state['theta'],initial['theta'],'every prewrite packet')
            if t>=end:ref.exact(state['theta'],final,'every postwrite packet')
        assert writes==expected and meta['rng_final']==rng.digest()
    ref.scores(ctx['codes'],dict(body,**{f's{cfg.sweeps}_V':raw[f's{cfg.sweeps}_V']}),ctx['readout'])
    return dict(native_arrays=checked,max_native_error=0.,rng_match=bool(replay))
