"""Independent D086 equation, boundary, metric and pooling checks.

Does not call the pilot's simulator, record builder, metric or summary code.
Public source parameters/initial threshold generator are shared deliberately;
the dynamics are restated here. The additional source bridge runs the actual
E70 one-cycle life with observation-only spies, restored in a finally block.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from laws_confirmation.io import canonical_digest, sha256_file

TAG = 'l24-descendant-pilot-v1'


def generator(index, parent, phase):
    value = hashlib.sha256(f'{TAG}:{index}:{parent}:{phase}'.encode()).digest()
    return np.random.default_rng(int.from_bytes(value[:16], 'little'))


def project(theta, norm):
    centered = theta - np.mean(theta, axis=(-2,-1), keepdims=True)
    return centered * (norm / np.maximum(np.std(centered, axis=(-2,-1), keepdims=True), 1e-9))


def step(v, ema, ref, theta, tissue, ladder, cm, rho, noise):
    neighbors = (np.roll(v,1,-2)+np.roll(v,-1,-2)+np.roll(v,1,-1)+np.roll(v,-1,-1))/4.
    drift = v-v**3+tissue.well_asym+theta+tissue.coupling*(neighbors-v)
    drift -= drift.mean(axis=(-2,-1),keepdims=True)
    perturbation = tissue.sigma*noise
    perturbation = perturbation-perturbation.mean(axis=(-2,-1),keepdims=True)
    v = np.clip(v+tissue.dt*drift+perturbation,-2.,2.)
    ema = (1-ladder.ema_rate)*ema+ladder.ema_rate*v
    if cm > 0:
        pull = cm*(ref-v)
        pull -= pull.mean(axis=(-2,-1),keepdims=True)
        v = np.clip(v+tissue.dt*pull,-2.,2.)
    ref = ref+rho*(v-ref)
    return v,ema,ref


def compare(actual, expected, atol=1e-10):
    assert actual.shape == expected.shape
    assert np.isfinite(actual).all() and np.isfinite(expected).all()
    np.testing.assert_allclose(actual,expected,rtol=0,atol=atol)
    np.testing.assert_array_equal(actual>0,expected>0)
    return float(np.max(np.abs(actual-expected)))


def source_bridge(raw, ctx, parent, damaged, meta):
    cfg,a,tissue = ctx['config'],ctx['api'],ctx['tissue']
    original = a['original']
    source_step,source_cut = original.blueprint_step,original.fission_with_mask
    stages = {}; count = 0; last_theta = None; cut_mask = None

    def pack(v,ema,ref,theta):
        return np.stack((v[0],ema[0],ref[0],theta[0]))

    def observing_step(v,ema,ref,theta,*args,**kwargs):
        nonlocal count,last_theta
        count += 1
        if count == 1: stages['birth'] = pack(v,ema,ref,theta)
        if count == cfg.settle+cfg.zap+1: stages['post_zap'] = pack(v,ema,ref,theta)
        result = source_step(v,ema,ref,theta,*args,**kwargs)
        last_theta = a['project_theta']((1-cfg.writer_rate)*theta+cfg.writer_rate*np.tanh(result[2]),cfg.norm)
        for tick,label in ((cfg.settle,'settled'),(cfg.settle+cfg.zap,'pre_zap'),
                           (cfg.settle+cfg.zap+1,'one_after_zap'),(cfg.settle+cfg.parent_steps,'final')):
            if count == tick: stages[label] = pack(*result,last_theta)
        return result

    def observing_cut(v,ref,*args,**kwargs):
        nonlocal cut_mask
        result = source_cut(v,ref,*args,**kwargs)
        cut_mask = result[2][0].copy()
        stages['post_fission'] = pack(result[0],result[0],result[1],last_theta)
        return result

    config = replace(a['WeismannConfig'](),cycles=1,settle_sweeps=cfg.settle,
        inter_fission=cfg.parent_steps,zap_at_fraction=cfg.zap/cfg.parent_steps,
        norm=cfg.norm,rho=4*cfg.writer_rate)
    assert int(config.zap_at_fraction*config.inter_fission) == cfg.zap
    random = generator(ctx['index'],parent,'parent')
    try:
        original.blueprint_step,original.fission_with_mask = observing_step,observing_cut
        result = original.life_fitness(config,tissue,ctx['ladder'],ctx['bp'],(.5,.5,.5),
                                        damaged,True,random)
    finally:
        original.blueprint_step,original.fission_with_mask = source_step,source_cut
    order = ('birth','settled','post_fission','pre_zap','post_zap','one_after_zap','final')
    assert set(stages) == set(order)
    np.testing.assert_array_equal(raw['states'],np.stack([stages[k] for k in order]))
    np.testing.assert_array_equal(raw['fresh'],cut_mask)
    assert result == meta['source_metrics']
    assert canonical_digest(random.bit_generator.state) == meta['rng_final']
    return dict(passed=True,source='weismann.pipeline.life_fitness',cycles=1,
                captured_stages=7,exact_states=True,exact_metrics=True,exact_rng=True)


def check_parent(raw, ctx, parent, damaged, meta):
    cfg,a,t = ctx['config'],ctx['api'],ctx['tissue']
    random = generator(ctx['index'],parent,'parent')
    theta = project(a['make_thresholds'](t)[None],cfg.norm)
    v = a['launch_pattern'](0,t)[None]+t.copy_jitter*random.standard_normal((1,16,16))
    ema,ref = v.copy(),v.copy(); states=[]

    def save(): states.append(np.stack((v[0],ema[0],ref[0],theta[0])))
    def advance():
        nonlocal v,ema,ref,theta
        v,ema,ref = step(v,ema,ref,theta,t,ctx['ladder'],ctx['bp'].c_m,ctx['bp'].rho,
                        random.standard_normal(v.shape))
        theta = project((1-cfg.writer_rate)*theta+cfg.writer_rate*np.tanh(ref),cfg.norm)

    save()
    for _ in range(cfg.settle): advance()
    save(); founder = np.sign(v[0])
    axis = int(random.integers(0,2,1)[0]); side = int(random.integers(0,2,1)[0])
    coordinates = np.indices((16,16)); kept = (coordinates[axis]//8 == side)
    v = np.where(kept[None],v,t.resting)+t.copy_jitter*random.standard_normal(v.shape)
    ref=ref.copy(); ema=v.copy(); save()
    zone = coordinates[1] >= 12
    for tick in range(cfg.parent_steps):
        if tick == cfg.zap:
            save()
            if damaged: v=np.where(zone[None],-v,v); ema=v.copy()
            save()
        advance()
        if tick == cfg.zap: save()
    save()
    error = compare(raw['states'],np.stack(states))
    for key,value in (('fresh',~kept),('founder',founder),('zone',zone)):
        np.testing.assert_array_equal(raw[key],value)
    fitness = float((((v[0]>0)==(founder>0)) & (abs(v[0])>.2))[~kept].mean())
    leak = float(((v[0]>0)==(-np.sign(states[3][0])>0))[zone].mean()) if damaged else None
    assert meta['source_metrics'] == dict(fitness=fitness,leak=leak)
    assert meta['rng_final'] == canonical_digest(random.bit_generator.state)
    bridge = source_bridge(raw,ctx,parent,damaged,meta)
    return dict(passed=True,replay_max_abs=error,source_bridge=bridge)


def check_records(records, targets, permutation, clean, damaged, ctx, parent):
    np.testing.assert_array_equal(clean['states'][:4],damaged['states'][:4])
    for key in ('fresh','founder','zone'): np.testing.assert_array_equal(clean[key],damaged[key])
    np.testing.assert_array_equal(clean['states'][3],clean['states'][4])
    np.testing.assert_array_equal(damaged['states'][3,2:],damaged['states'][4,2:])
    flip = np.where(clean['zone'],-clean['states'][3,0],clean['states'][3,0])
    np.testing.assert_array_equal(damaged['states'][4,0],flip)
    np.testing.assert_array_equal(damaged['states'][4,1],flip)
    good = np.where(clean['states'][3,0]>0,1.,-1.)
    bad = good.copy();bad[:,12:]*=-1
    np.testing.assert_array_equal(targets,np.stack((good,bad)))
    expected_permutation=generator(ctx['index'],parent,'shuffle').permutation(256)
    np.testing.assert_array_equal(permutation,expected_permutation)
    known_good,known_bad=project(np.tanh(1.5*good),ctx['config'].norm),project(np.tanh(1.5*bad),ctx['config'].norm)
    native=project(ctx['api']['make_thresholds'](ctx['tissue']),ctx['config'].norm)
    expected=np.stack((clean['states'][-1,3],damaged['states'][-1,3],np.zeros((16,16)),native,
        known_good,known_bad,known_bad.flatten()[expected_permutation].reshape(16,16),-known_bad))
    compare(records,expected,atol=1e-12)
    np.testing.assert_allclose(records.mean(axis=(-2,-1)),0,rtol=0,atol=1e-12)
    # Constant constructed targets legitimately project to zero, not norm .3.
    for i in (0,1,3): np.testing.assert_allclose(records[i].std(),ctx['config'].norm,rtol=0,atol=1e-12)
    return True


def check_descendants(raw, records, ctx, parent, reader, meta):
    cfg,t=ctx['config'],ctx['tissue']
    birth=.2*generator(ctx['index'],parent,'child_birth').standard_normal((cfg.draws,16,16))
    birth=birth-birth.mean(axis=(-2,-1),keepdims=True)
    v=np.broadcast_to(birth,(2,len(records),cfg.draws,16,16)).copy()
    ema=v.copy();ref=np.zeros_like(v)
    applied=np.zeros((2,len(records),1,16,16));applied[0,:,0]=records
    random=generator(ctx['index'],parent,'child_future');states=[]
    cm,rho=(ctx['bp'].c_m,ctx['bp'].rho) if reader==0 else (0.,0.)
    for tick in range(cfg.child_steps+1):
        if tick:
            noise=random.standard_normal((cfg.draws,16,16))
            v,ema,ref=step(v,ema,ref,applied,t,ctx['ladder'],cm,rho,noise)
        if tick in cfg.times: states.append(np.stack((v,ema,ref)))
    error=compare(raw,np.stack(states))
    assert meta['rng_final']==canonical_digest(random.bit_generator.state)
    assert meta['packet_sha256']==[hashlib.sha256(r.astype('<f8').tobytes()).hexdigest() for r in records]
    assert meta['packet_unchanged'] is True and meta['R_at_birth_zero'] is True
    assert meta['inherited_fields']==['theta']
    return error


def check_metrics(raw, targets, values):
    v=raw[:,0];expected=np.empty((*v.shape[:-2],3,8))
    selections=([r*16+c for r in range(16) for c in range(12,16)],
                [r*16+c for r in range(16) for c in range(12)],list(range(256)))
    for i,pixels in enumerate(selections):
        x=v.reshape((*v.shape[:-2],256))[...,pixels]
        good,bad=targets.reshape(2,256)[:,pixels]
        pieces=[np.sum((x>0)==(bad>0),axis=-1)/len(pixels),
            np.sum((x>0)==(good>0),axis=-1)/len(pixels),np.sum(x*bad,axis=-1)/len(pixels),
            np.sum((x-good)**2,axis=-1)/len(pixels),np.sum((x-bad)**2,axis=-1)/len(pixels),
            np.sum(x,axis=-1)/len(pixels),np.sqrt(np.sum(x*x,axis=-1)/len(pixels)),
            np.sum(abs(x)==2,axis=-1)/len(pixels)]
        expected[...,i,:]=np.stack(pieces,axis=-1)
    assert values.shape==expected.shape and np.isfinite(values).all()
    np.testing.assert_allclose(values,expected,rtol=0,atol=1e-12)
    return True


def check_aliases(payload):
    raw=payload['descendants']  # reader,time,field,onoff,record,draw,row,column
    np.testing.assert_array_equal(raw[0,0],raw[1,0])
    np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not np.any(raw[:,0,2]) and not np.any(raw[1,:,2])
    for record in range(raw.shape[4]):
        np.testing.assert_array_equal(raw[:,:,:,1,record],raw[:,:,:,1,0])
        np.testing.assert_array_equal(raw[:,0,:,0,record],raw[:,0,:,1,0])
    np.testing.assert_array_equal(raw[:,:,:,0,2],raw[:,:,:,1,2])
    values=payload['values']
    np.testing.assert_array_equal(values[...,0,0]+values[...,0,1],np.ones_like(values[...,0,0]))
    np.testing.assert_array_equal(values[...,1,0],values[...,1,1])
    np.testing.assert_array_equal(values[...,1,3],values[...,1,4])
    assert not np.shares_memory(payload['parent_states'],raw)
    return True


def check_summary(blocks, summary, focal):
    # Explicit block/parent/draw reductions independent of production axes.
    a=np.asarray(blocks)
    assert np.isfinite(a).all() and set(summary)=={'means'}
    expected=sum(np.sum(b,axis=(0,5)) for b in a)/(a.shape[0]*a.shape[1]*a.shape[6])
    np.testing.assert_allclose(summary['means'],expected,rtol=0,atol=1e-12)
    pairs=((5,4),(5,6),(5,7),(1,0))
    labels=('calibration_content_crossover','calibration_address','calibration_reversal','natural_damage_transmission')
    assert len(focal)==8
    resamples=generator(0,0,'block_bootstrap').integers(0,len(a),(10000,len(a)))
    for reader in range(2):
        for position,(plus,minus) in enumerate(pairs):
            row=focal[4*reader+position]
            assert row['reader']==('native_T','theta_only')[reader] and row['label']==labels[position]
            cases=np.array([[[b[p,reader,-1,0,plus,d,0,0]-b[p,reader,-1,0,minus,d,0,0]
                for d in range(a.shape[6])] for p in range(a.shape[1])] for b in a])
            means=np.array([np.sum(b)/b.size for b in cases])
            ci=np.percentile(np.sum(means[resamples],axis=1)/len(means),(2.5,97.5))
            np.testing.assert_allclose(row['pointwise_block_bootstrap_95'],ci,rtol=0,atol=1e-12)
            for name,value in (('mean',means.mean()),('minimum',min(means)),('maximum',max(means)),
                                ('block_means',means),('parent_means',cases.mean(axis=2))):
                np.testing.assert_allclose(row[name],value,rtol=0,atol=1e-12)
            for prefix,items in (('',means),('paired_',cases.ravel())):
                assert row[prefix+'positive']==int(np.count_nonzero(items>1e-12))
                assert row[prefix+'negative']==int(np.count_nonzero(items< -1e-12))
                assert row[prefix+'tied']==int(np.count_nonzero(abs(items)<=1e-12))
    return True


def check_hashes(path):
    seen=set()
    for line in Path(path).read_text().splitlines():
        digest,name=line.split('  ',1)
        assert name not in seen and sha256_file(Path(name))==digest,name
        seen.add(name)
    assert seen
    return len(seen)
