"""Capture extension of the unmodified independently qualified TT019 kernel."""
import numpy as np

import tt019_reference as old

KEYS = old.KEYS
exact = old.exact
fresh_read = old.fresh_read
record_scores = old.record_scores
scores = old.scores
parent = old.parent
source_boundary = old.source_boundary


def initial(built, original, spec, observed):
    base=spec.base
    body=built['body_'+base.body] if base.reset=='zero' else original['kept_V' if base.body=='own' else 'scrambled_V']
    expected=dict(V=body,ema=np.zeros_like(body) if base.reset=='zero' else body,
                  R=body if spec.capture else np.zeros_like(body),theta=built[base.packet])
    assert set(observed)==set(KEYS)
    for key in KEYS:exact(observed[key],expected[key],'declared capture start '+key)
    return True


def repairs(context,state,index,spec,raw,metadata):
    if not spec.capture:return old.repairs(context,state,index,spec.base,raw,metadata)
    assert set(context)=={'config','tissue','ladder','bp'} and set(state)==set(KEYS)
    exact(state['R'],state['V'],'capture must be this injured body')
    exact(state['ema'],np.zeros_like(state['V']),'zero capture ema')
    cfg,s=context['config'],spec.base
    rng=old.Coupled(old.REPAIR_TAG,index,'repair',cfg.replicates)
    current={k:v.copy() for k,v in state.items()}
    average_on=s.reader=='fixed' and s.write
    running=state['V'].copy();averaged=state['theta'].copy()
    expected={f's{t}_{k}' for t in cfg.times for k in KEYS}
    if average_on:expected|={f'a{t}_{k}' for t in cfg.times for k in ('mean','theta')}
    assert set(raw)==expected
    checked=0;maximum=0.
    for t in range(cfg.sweeps+1):
        if t:
            applied=current['theta'] if s.reader=='live' else state['theta']
            current=old.advance(current,applied,context['tissue'],context['ladder'],context['bp'],
                                cfg,rng,s.write,s.reference_write)
            if average_on:
                # Count the birth observation, without making a birth write.
                running+=(current['V']-running)/(t+1)
                averaged=old.project((1-cfg.lam)*averaged+cfg.lam*np.tanh(running),cfg.norm)
        if t in cfg.times:
            for key in KEYS:
                exact(raw[f's{t}_{key}'],current[key],f'capture {t} {key}');checked+=1
            if average_on:
                for key,array in (('mean',running),('theta',averaged)):
                    value=raw[f'a{t}_{key}'];assert value.dtype==array.dtype and value.shape==array.shape
                    error=float(np.max(np.abs(value-array)))
                    assert error<=2e-12,(t,key,error);maximum=max(maximum,error)
    assert metadata['rng_final']==rng.digest()
    assert metadata['birth_capture_observations']==1
    assert metadata['body_observations_available_per_record']==cfg.sweeps+1
    assert metadata['observations_per_record']==(cfg.sweeps+1 if average_on else 0)
    assert metadata['reference_held']==(not s.reference_write)
    return dict(native_arrays=checked,max_native_error=0.,max_average_error=maximum,rng_match=True)
