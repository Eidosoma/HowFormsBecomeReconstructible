"""D101: matched-time E65 broadcast withdrawal; no target in free dynamics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

from . import l15_repair_speed as native
from .io import canonical_digest

WS, ORIGIN = native.WS, native.ORIGIN
RUN_ID = 'l19_broadcast_withdrawal_v1_attempt1'
CONTROL_ID = 'l19_broadcast_withdrawal_v1_source_controls_attempt1'
TAG = 'l19-broadcast-withdrawal-v1'
TISSUES = tuple(range(46000,46008))
DISPOSABLE = 514201
ARMS = ('continued','withdrawn','wrong','rescue')
FIELDS = ('V','ema','R')
METRICS = ('body_founder_fidelity','body_wrong_fidelity','reference_founder_sign',
    'body_target_mae','reference_target_mae','vr_mae','body_mean','reference_mean',
    'body_rms','reference_rms','body_amp_fraction','parent_fidelity',
    'regrown_correct','regrown_total','regrown_parent_correct')
PACKAGES = native.PACKAGES+('teaching',)
SCIENCE = ('src/laws_confirmation/l19_broadcast_withdrawal.py',
    'src/laws_confirmation/l19_broadcast_withdrawal_run.py',
    'scripts/audit_l19_broadcast_withdrawal_outputs.py',
    'tests/test_l19_broadcast_withdrawal.py','scripts/run_l19_broadcast_withdrawal.sh',
    'protocols/L19_BROADCAST_WITHDRAWAL_V1.md')
SOURCE_DIGEST = '1f30524f09da9001192f2c9a6b559f63f888c41a14e7a2a93a0a18f72c961ee4'


@dataclass(frozen=True)
class Config:
    lives: int = 2
    settle: int = 620
    training_cycles: int = 3
    cycles: int = 6
    primary_cycle: int = 3
    rescue_cycle: int = 4
    teaching: int = 500
    free: int = 1000
    amplitude: float = 1.2
    amp_threshold: float = .2
    shift: int = 8

    def __post_init__(self):
        for key in ('lives','settle','training_cycles','cycles','primary_cycle',
                    'rescue_cycle','teaching','free','shift'):
            if type(getattr(self,key)) is not int or getattr(self,key) <= 0:
                raise ValueError('positive integer required: '+key)
        if not 3 <= self.primary_cycle < self.rescue_cycle <= self.cycles:
            raise ValueError('at least three untreated boundaries before rescue')
        if not 0 < self.shift < 16:
            raise ValueError('nontrivial in-bounds periodic shift')
        if not (np.isfinite(self.amplitude) and 0 < self.amplitude <= 2
                and np.isfinite(self.amp_threshold) and 0 < self.amp_threshold < self.amplitude):
            raise ValueError('finite physical amplitude and lower observer threshold required')


CONFIG = Config()


def api():
    a = native.api()
    directory = str(ORIGIN/'teaching/src')
    if directory not in sys.path:
        sys.path.insert(0,directory)
    from teaching import pipeline as teaching
    from teaching.config import TeachConfig
    from voltage_web.engine import make_thresholds
    return a | dict(teaching=teaching, TeachConfig=TeachConfig, make_thresholds=make_thresholds)


def context(index):
    ctx = native.context(index)
    ctx['api'] = api()
    return ctx


def rng(index,life,phase):
    key=hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16],'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d101_independent_checker',WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evolve(state,theta,ctx,random,steps,teacher=None,amplitude=1.2):
    """No observer/ancestral target argument; teacher None is a free window."""
    v,ema,ref = (x[None].copy() for x in state)
    if teacher is not None:
        if (teacher.shape != (16,16) or teacher.dtype != np.float64
                or not np.all(np.isin(teacher,(-1.,1.)))):
            raise ValueError('full-field sign teacher required; broadcasting forbidden')
        hold = amplitude*teacher[None]
    for _ in range(steps):
        if teacher is not None:
            v = hold.copy()
        v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],
            ctx['ladder'],ctx['bp'],'T',random)
    return np.stack((v[0],ema[0],ref[0]))


def cycle(state,theta,ctx,random,teacher,cfg):
    v,ref,fresh = ctx['api']['teaching'].fission_with_mask(
        state[0][None],state[2][None],ctx['tissue'],random)
    birth = np.stack((v[0],v[0],ref[0]))
    release = evolve(birth,theta,ctx,random,cfg.teaching,teacher,cfg.amplitude)
    final = evolve(release,theta,ctx,random,cfg.free)
    return np.stack((birth,release,final)),fresh[0]


def schedule(arm,ancestor,cfg=CONFIG):
    if arm not in ARMS:
        raise ValueError('undeclared branch')
    if arm=='withdrawn':
        return (None,)*cfg.cycles
    wrong = np.roll(ancestor,cfg.shift,axis=-1)
    return tuple(None if arm=='withdrawn' or (arm=='rescue' and c<cfg.rescue_cycle)
                 else wrong.copy() if arm=='wrong' else ancestor.copy()
                 for c in range(1,cfg.cycles+1))


def branch(initial,theta,ctx,index,life,teachers,cfg=CONFIG):
    if len(teachers) != cfg.cycles:
        raise ValueError('one explicit schedule entry per boundary required')
    saved, fresh, digests = [initial.copy()],[],[]
    state = initial.copy()
    for c,teacher in enumerate(teachers,1):
        random = rng(index,life,f'branch:{c}')
        phases,mask = cycle(state,theta,ctx,random,teacher,cfg)
        saved.extend(phases); fresh.append(mask)
        state = phases[-1]
        digests.append(canonical_digest(random.bit_generator.state))
    return np.stack(saved),np.stack(fresh),digests


def measure(states,ancestor,fresh,cfg=CONFIG):
    if (states.ndim!=5 or states.shape[1:]!=(3*cfg.cycles+1,3,16,16)
            or ancestor.shape!=(16,16) or fresh.shape!=(cfg.cycles,16,16)
            or fresh.dtype!=np.bool_ or not np.isfinite(states).all()
            or not np.all(np.isin(ancestor,(-1.,1.)))):
        raise ValueError('full finite states/target and paired masks required')
    ends = states[:,::3]
    v,ref = ends[:,:,0],ends[:,:,2]
    parent = np.concatenate((v[:,:1],v[:,:-1]),axis=1)
    amp = abs(v)>cfg.amp_threshold
    correct = ((v>0)==(ancestor>0)) & amp
    own = ((v>0)==(parent>0)) & amp
    wrong = np.roll(ancestor,cfg.shift,axis=-1)
    counts = np.concatenate((np.zeros((1,16,16),dtype=np.int64),np.cumsum(fresh,axis=0)))
    mask = counts>=2
    sums = lambda x: np.asarray(x.sum(axis=(-2,-1)),dtype=np.float64)
    means = lambda x: x.mean(axis=(-2,-1))
    return np.stack((means(correct),means(((v>0)==(wrong>0)) & amp),
        means((ref>0)==(ancestor>0)),means(abs(v-cfg.amplitude*ancestor)),
        means(abs(ref-cfg.amplitude*ancestor)),means(abs(v-ref)),means(v),means(ref),
        np.sqrt(means(v*v)),np.sqrt(means(ref*ref)),means(amp),means(own),
        sums(correct & mask),np.broadcast_to(sums(mask),v.shape[:2]),sums(own & mask)),axis=-1)


def simulate_life(index,life,cfg=CONFIG,arms=ARMS):
    if type(life) is not int or not 0<=life<cfg.lives or any(a not in ARMS for a in arms):
        raise ValueError('declared life/arms required')
    ctx = context(index); a=ctx['api']
    random = rng(index,life,'founder')
    v,ema,ref,theta,_ = a['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False)
    founder = np.stack((v[0],ema[0],ref[0]))
    ancestor = np.sign(v[0]); ancestor[ancestor==0]=1.
    training, training_fresh, training_rng = [founder.copy()],[],[]
    founder_rng = canonical_digest(random.bit_generator.state)
    state = founder.copy()
    for c in range(1,cfg.training_cycles+1):
        random = rng(index,life,f'training:{c}')
        phases,mask = cycle(state,theta,ctx,random,ancestor,cfg)
        state = phases[-1]
        training.append(state); training_fresh.append(mask)
        training_rng.append(canonical_digest(random.bit_generator.state))
    outcomes = [branch(state,theta,ctx,index,life,schedule(arm,ancestor,cfg),cfg) for arm in arms]
    for row in outcomes[1:]:
        np.testing.assert_array_equal(row[1],outcomes[0][1])
    states = np.stack([row[0] for row in outcomes]); fresh=outcomes[0][1]
    raw = dict(theta=theta,ancestor=ancestor,training=np.stack(training),
        training_fresh=np.stack(training_fresh),states=states,fresh=fresh,
        values=measure(states,ancestor,fresh,cfg))
    meta = dict(index=index,life=life,config=asdict(cfg),arms=list(arms),
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        founder_rng=founder_rng,training_rng=training_rng,
        branch_rng=[row[2] for row in outcomes],theta_writable=theta.flags.writeable)
    return raw,meta


def execute_block(index,cfg=CONFIG):
    records,rows=[],[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,cfg)
        meta['replay']=check.check_life(raw,meta,cfg)
        alias,mask,digests=branch(raw['training'][-1],raw['theta'],context(index),
            index,life,(None,)*cfg.cycles,cfg)
        np.testing.assert_array_equal(alias,raw['states'][1])
        np.testing.assert_array_equal(mask,raw['fresh'])
        assert digests==meta['branch_rng'][1]
        meta['exact_alias_branches']=1
        rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8:
        raise ValueError('eight complete tissue blocks required')
    values=np.stack([b['values'] for b in blocks])
    if values.shape!=(8,cfg.lives,4,cfg.cycles+1,len(METRICS)) or not np.isfinite(values).all():
        raise ValueError('complete finite paired measurements required')
    resamples=rng(0,0,'bootstrap').integers(0,8,(10000,8))
    stats=lambda v:native.contrast_stats(v,resamples)
    contrasts=[]
    for c in (cfg.primary_cycle,cfg.cycles):
        den=values[:,:,:,c,13]
        if np.any(den<64) or not np.array_equal(den, np.repeat(den[:,:,:1],4,axis=2)):
            raise ValueError('paired nonempty regrowth denominators required')
        for observer,score in (('regrown',values[:,:,:,c,12]/den),('whole',values[:,:,:,c,0])):
            for name,left,right in (('continued_minus_withdrawn',0,1),
                                    ('continued_minus_wrong',0,2),('rescue_minus_withdrawn',3,1)):
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,left]-score[:,:,right])))
    primary=next(x for x in contrasts if x['cycle']==cfg.primary_cycle and x['observer']=='regrown'
                 and x['name']=='continued_minus_withdrawn')
    trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            entry=dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den))
            trajectories.append(entry)
    return dict(schema='l19_broadcast_withdrawal_summary_v1',tissues=list(TISSUES),
        arms=list(ARMS),metrics=list(METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),primary=primary,contrasts=contrasts,
        trajectories=trajectories,training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        target_disagreement=[[(b['ancestor'][l]!=np.roll(b['ancestor'][l],cfg.shift,-1)).mean().item()
                             for l in range(cfg.lives)] for b in blocks],
        label=('CONTINUED_BROADCAST_ADVANTAGE' if primary['pointwise_block_bootstrap_95'][0]>0
               else 'NO_QUALIFIED_CONTINUED_ADVANTAGE'),blocks=8,lives_per_block=cfg.lives,
        secondary_intervals_multiplicity_adjusted=False,absolute_fidelity_gate=None)


def source_control(index,config=None):
    a=api(); old=a['teaching']; config=config or a['TeachConfig']()
    free_fn,fission_fn=old._free,old.fission_with_mask
    saved,masks,digests=[],[],[]
    def free(*args,**kw):
        result=free_fn(*args,**kw)
        saved.append(np.stack(result)); digests.append(canonical_digest(args[7].bit_generator.state))
        return result
    def fission(*args,**kw):
        result=fission_fn(*args,**kw); masks.append(result[2]); return result
    try:
        old._free,old.fission_with_mask=free,fission
        result=old.teach_lineage(config,index,'broadcast',500)
    finally:
        old._free,old.fission_with_mask=free_fn,fission_fn
    ctx=context(index)
    ancestor=np.sign(saved[0][0]); ancestor[ancestor==0]=1.
    raw=dict(theta=a['make_thresholds'](ctx['tissue']),states=np.stack(saved),
             ancestor=ancestor,fresh=np.stack(masks))
    meta=dict(index=index,config=asdict(config),result=result,rng=digests,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    meta['replay']=checker().check_source(raw,meta)
    return raw,meta


def contract():
    return dict(schema='l19_broadcast_withdrawal_v1',decision='D101',law='L19',
        run_id=RUN_ID,control_id=CONTROL_ID,config=asdict(CONFIG),tissues=list(TISSUES),
        disposable=DISPOSABLE,seed_tag=TAG,arms=list(ARMS),fields=list(FIELDS),metrics=list(METRICS),
        primary='continued-minus-withdrawn qualified founder fidelity, regrown>=2 since branch, cycle3',
        independent_unit='eight equal tissue blocks, two lives each',bootstrap_resamples=10000,
        wrong_teacher='periodic eight-column translation; no outcome-based target replacement',
        fresh_branches=64,independent_life_replays=16,exact_alias_branches=16,
        source_jobs=4,source_futures_per_job=8,source_outcomes_known=True,
        theta='native fixed unprojected',boundary='half V, whole R; EMA reset',
        state_atol=1e-10,metrics_atol=1e-12,exact_signs=True,
        absolute_fidelity_gate=None,automatic_retry=False,automatic_follow_on=False,
        biological_or_unique_architecture_or_carrier_only_claim=False)
