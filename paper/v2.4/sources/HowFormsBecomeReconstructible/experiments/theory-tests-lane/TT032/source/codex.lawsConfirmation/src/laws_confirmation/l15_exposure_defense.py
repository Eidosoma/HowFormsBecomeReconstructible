"""D098: equal-body readout of R after brief/sustained template exposure."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.util

import numpy as np

from . import l15_repair_speed as base
from .io import canonical_digest

WS = base.WS
RUN_ID = 'l15_exposure_defense_v1_attempt1'
QUAL_ID = 'l15_exposure_defense_v1_qualification_attempt1'
TAG = 'l15-exposure-defense-v1'
TISSUES, QUAL_TISSUES = tuple(range(44000,44008)), tuple(range(44080,44088))
DISPOSABLE = 514198
HISTORIES = tuple((schedule,writing) for schedule in ('none','brief','sustained') for writing in (True,False))
NATURAL = tuple(f'{s}_{"live" if w else "held"}' for s,w in HISTORIES)
CONTROLS = ('known_new','known_old','erased')
RECORDS = NATURAL+CONTROLS
GAINS = (.2,0.)
REGIONS = ('conflict','whole')
METRICS = ('V_new_sign','V_old_sign','R_new_sign','R_old_sign','V_new_mae','V_old_mae',
           'R_new_mae','R_old_mae','VR_mae','R_rms','V_mean','abs_V_ge_2')
SCIENCE = ('src/laws_confirmation/l15_exposure_defense.py',
           'src/laws_confirmation/l15_exposure_defense_run.py',
           'scripts/audit_l15_exposure_defense_outputs.py',
           'tests/test_l15_exposure_defense.py',
           'scripts/run_l15_exposure_defense.sh','protocols/L15_EXPOSURE_DEFENSE_V1.md')


@dataclass(frozen=True)
class Config:
    lives: int = 2
    settle: int = 120
    exposure: int = 1000
    brief: int = 20
    exposure_times: tuple = (0,1,20,500,980,981,1000)
    release: int = 200
    release_times: tuple = (0,1,20,80,200)
    response: int = 80
    response_times: tuple = (0,1,20,80)
    amplitude: float = 1.2
    pulse: float = .8

    def __post_init__(self):
        for key in ('lives','settle','exposure','brief','release','response'):
            if type(getattr(self,key)) is not int or getattr(self,key) <= 0:
                raise ValueError('positive integer counts required')
        if self.brief >= self.exposure:
            raise ValueError('brief exposure must be strictly shorter')
        for times, end in ((self.exposure_times,self.exposure),(self.release_times,self.release),
                           (self.response_times,self.response)):
            if (not isinstance(times,tuple) or len(times)<2 or any(type(t) is not int for t in times)
                    or tuple(sorted(set(times))) != times or times[:2] != (0,1) or times[-1] != end):
                raise ValueError('ordered snapshots including 0/1/endpoint required')
        if self.exposure-self.brief not in self.exposure_times or self.exposure-self.brief+1 not in self.exposure_times:
            raise ValueError('snapshot both sides of brief-exposure onset')
        if not (np.isfinite(self.amplitude) and 0 < self.amplitude < 2
                and np.isfinite(self.pulse) and 0 < self.pulse < 2):
            raise ValueError('finite in-range template and pulse amplitudes required')


CONFIG = Config()


def rng(index,life,phase):
    value = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(value[:16],'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d098_independent_checker',WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def targets(ctx,cfg=CONFIG):
    from voltage_web.engine import launch_pattern
    return cfg.amplitude*np.stack([launch_pattern(i,ctx['tissue']) for i in (0,1)])


def encode(record):
    if not isinstance(record,np.ndarray) or record.shape!=(16,16) or record.dtype!=np.float64 or not np.isfinite(record).all():
        raise ValueError('one finite float64 R field required')
    return record.astype('<f8',copy=False).tobytes()


def decode(packet):
    if not isinstance(packet,bytes) or len(packet)!=2048:
        raise ValueError('only a 2048-byte immutable R packet is accepted')
    record = np.frombuffer(packet,dtype='<f8').reshape(16,16)
    if not np.isfinite(record).all():
        raise ValueError('nonfinite R packet')
    return record


def exposure(ctx,settled,theta,templates,life,history,cfg=CONFIG):
    if history not in HISTORIES:
        raise ValueError('undeclared exposure history')
    schedule,writing = history
    v,ema,ref = [x[None].copy() for x in settled]
    random = rng(ctx['index'],life,'exposure')
    bp = replace(ctx['bp'],rho=.002 if writing else 0.)
    saved = [settled.copy()]
    for t in range(1,cfg.exposure+1):
        new = schedule=='sustained' or (schedule=='brief' and t>cfg.exposure-cfg.brief)
        v = templates[int(new)][None].copy()
        v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],ctx['ladder'],bp,'T',random)
        if t in cfg.exposure_times:
            saved.append(np.stack((v[0],ema[0],ref[0])))
    return np.stack(saved),canonical_digest(random.bit_generator.state)


def readout(index,packet,life,gain,cfg=CONFIG):
    """No history/record label or exposure V/EMA is accepted by this reader."""
    if type(life) is not int or not 0<=life<cfg.lives or type(gain) is bool or gain not in GAINS:
        raise ValueError('undeclared reader gain')
    ctx = base.context(index); templates = targets(ctx,cfg)
    from voltage_web.engine import make_thresholds
    theta = make_thresholds(ctx['tissue']); theta.setflags(write=False)
    ref = decode(packet)[None].copy()
    v = templates[1][None].copy(); ema = v.copy()
    random = rng(ctx['index'],life,'release')
    bp = replace(ctx['bp'],c_m=gain)
    prefix = [np.stack((v[0],ema[0],ref[0]))]
    for t in range(1,cfg.release+1):
        v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],ctx['ladder'],bp,'T',random)
        if t in cfg.release_times:
            prefix.append(np.stack((v[0],ema[0],ref[0])))
    before = (v.copy(),ref.copy())
    release_rng = canonical_digest(random.bit_generator.state)
    conflict = (templates[0]>0)!=(templates[1]>0)
    shift = cfg.pulse*np.sign(templates[0])*conflict
    branches, digests = [],[]
    for challenged in (True,False):
        v,ref = (x.copy() for x in before)
        if challenged:
            v = v+shift[None]
        ema = v.copy()
        saved = [*prefix,np.stack((v[0],ema[0],ref[0]))]
        random = rng(ctx['index'],life,'response')
        for t in range(1,cfg.response+1):
            v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],ctx['ladder'],bp,'T',random)
            if t in cfg.response_times:
                saved.append(np.stack((v[0],ema[0],ref[0])))
        branches.append(np.stack(saved)); digests.append(canonical_digest(random.bit_generator.state))
    return np.stack(branches),dict(packet_sha256=hashlib.sha256(packet).hexdigest(),
        release_rng=release_rng,response_rng=digests)


def measure(states,templates):
    # Any leading axes,field,row,column -> leading axes,region,metric.
    v,ref = states[...,0,:,:],states[...,2,:,:]
    masks = ((templates[0]>0)!=(templates[1]>0),np.ones((16,16),bool))
    scores = []
    for mask in masks:
        body,r,old,new = v[...,mask],ref[...,mask],templates[0,mask],templates[1,mask]
        scores.append(np.stack((((body>0)==(new>0)).mean(axis=-1),
            ((body>0)==(old>0)).mean(axis=-1),((r>0)==(new>0)).mean(axis=-1),
            ((r>0)==(old>0)).mean(axis=-1),abs(body-new).mean(axis=-1),abs(body-old).mean(axis=-1),
            abs(r-new).mean(axis=-1),abs(r-old).mean(axis=-1),abs(body-r).mean(axis=-1),
            np.sqrt(np.square(r).mean(axis=-1)),body.mean(axis=-1),(abs(body)>=2).mean(axis=-1)),axis=-1))
    return np.stack(scores,axis=-2)


def simulate_life(index,life,qualification=False,cfg=CONFIG):
    if type(life) is not int or not 0<=life<cfg.lives or type(qualification) is not bool:
        raise ValueError('declared life and Boolean phase required')
    ctx = base.context(index); templates = targets(ctx,cfg)
    random = rng(index,life,'settle')
    v,ema,ref,theta,_ = ctx['api']['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False); settled = np.stack((v[0],ema[0],ref[0]))
    histories = [] if qualification else [exposure(ctx,settled,theta,templates,life,h,cfg) for h in HISTORIES]
    trace = np.stack([x[0] for x in histories]) if histories else np.empty((0,len(cfg.exposure_times),3,16,16))
    known = np.stack((templates[1],templates[0],np.zeros((16,16))))
    records = known if qualification else np.concatenate((trace[:,-1,2],known))
    reads,read_meta = [],[]
    for record in records:
        outcomes = [readout(index,encode(record),life,g,cfg) for g in GAINS]
        reads.append(np.stack([o[0] for o in outcomes])); read_meta.append([o[1] for o in outcomes])
    states = np.stack(reads)
    raw = dict(theta=theta,targets=templates,conflict=(templates[0]>0)!=(templates[1]>0),
        settled=settled,exposures=trace,records=records,readouts=states,values=measure(states,templates),
        exposure_values=measure(trace,templates))
    meta = dict(index=index,life=life,qualification=qualification,config=asdict(cfg),
        records=list(CONTROLS if qualification else RECORDS),
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        settle_rng=canonical_digest(random.bit_generator.state),exposure_rng=[x[1] for x in histories],
        readouts=read_meta,theta_writable=theta.flags.writeable)
    return raw,meta


def execute_block(index,qualification=False,cfg=CONFIG):
    rows,records = [],[]; check = checker()
    for life in range(cfg.lives):
        raw,meta = simulate_life(index,life,qualification,cfg)
        meta['replay'] = check.check_life(raw,meta,cfg)
        ids = (0,1,0) if qualification else (4,2,4)
        for rec in ids:
            alias,digests = readout(index,encode(raw['records'][rec]),life,.2,cfg)
            np.testing.assert_array_equal(alias,raw['readouts'][rec,0])
            assert digests == meta['readouts'][rec][0]
        meta['exact_alias_futures'] = 6
        rows.append(raw); records.append(meta)
    return {key:np.stack([r[key] for r in rows]) for key in rows[0]},dict(
        index=index,qualification=qualification,config=asdict(cfg),lives=records)


def qualification_rules(values,cfg=CONFIG):
    # block,life,record,reader,challenge,stage,region,metric
    pre,instant = len(cfg.release_times)-1,len(cfg.release_times)
    new_pre,new_post = values[:,:,0,0,0,pre,0,0],values[:,:,0,0,0,-1,0,0]
    delta_pre = new_pre-values[:,:,1,0,0,pre,0,0]
    delta_post = new_post-values[:,:,1,0,0,-1,0,0]
    drop = new_pre-values[:,:,0,0,0,instant,0,0]
    rebound = new_post-values[:,:,0,0,0,instant,0,0]
    named = dict(new_pre=new_pre,new_post=new_post,content_pre=delta_pre,content_post=delta_post,
                 challenge_drop=drop,rebound=rebound)
    gates = dict(new_pre_mean=bool(new_pre.mean()>=.8),new_post_mean=bool(new_post.mean()>=.8),
        new_pre_every_tissue=bool(np.all(new_pre.mean(axis=1)>=.75)),
        new_post_every_tissue=bool(np.all(new_post.mean(axis=1)>=.75)),
        content_pre_every_tissue=bool(np.all(delta_pre.mean(axis=1)>.2)),
        content_post_every_tissue=bool(np.all(delta_post.mean(axis=1)>.2)),
        challenge_mean=bool(drop.mean()>=.10),challenge_every_tissue=bool(np.all(drop.mean(axis=1)>=.05)),
        rebound_mean=bool(rebound.mean()>=.10),rebound_every_tissue=bool(np.all(rebound.mean(axis=1)>=.05)))
    return named,gates


def summarize(blocks,qualification=False,cfg=CONFIG):
    nrec = 3 if qualification else 9
    if len(blocks)!=8:
        raise ValueError('all eight blocks required')
    values = np.stack([r['values'] for r in blocks])
    expected = (8,cfg.lives,nrec,2,2,len(cfg.release_times)+len(cfg.response_times),2,len(METRICS))
    if values.shape!=expected or not np.isfinite(values).all():
        raise ValueError('complete finite paired endpoint table required')
    draws = rng(0,0,'qualification_bootstrap' if qualification else 'main_bootstrap').integers(0,8,(10000,8))
    def stats(x): return base.contrast_stats(x,draws)
    common = dict(schema='l15_exposure_defense_summary_v1',qualification=qualification,
        tissues=list(QUAL_TISSUES if qualification else TISSUES),lives_per_block=cfg.lives,
        records=list(CONTROLS if qualification else RECORDS),gains=list(GAINS),challenges=[True,False],
        stages=[f'release_{t}' for t in cfg.release_times]+[f'response_{t}' for t in cfg.response_times],
        regions=list(REGIONS),metrics=list(METRICS),means_axes='record,reader,challenge,stage,region,metric',
        cell_means=values.mean(axis=(0,1)).tolist(),futures=8*cfg.lives*nrec*4,
        multiplicity_adjusted=False)
    if qualification:
        named,gates = qualification_rules(values,cfg)
        return common | dict(qualified=all(gates.values()),gates=gates,
                             endpoints={name:stats(x) for name,x in named.items()})
    contrasts = []
    def cell(rec,stage,reader=0,challenge=0,metric=0):
        return values[:,:,rec,reader,challenge,stage,0,metric]
    pre,instant = len(cfg.release_times)-1,len(cfg.release_times)
    for label,stage in (('release',pre),('response',-1)):
        long,brief = cell(4,stage),cell(2,stage)
        for name,x in (
            ('duration_writing_interaction',(long-brief)-(cell(5,stage)-cell(3,stage))),
            ('live_duration',long-brief),('sustained_writing',long-cell(5,stage)),
            ('brief_minus_none',brief-cell(0,stage)),('sustained_reading',long-cell(4,stage,reader=1)),
            ('sustained_minus_erased',long-cell(8,stage)),('known_new_minus_erased',cell(6,stage)-cell(8,stage)),
            ('known_content',cell(6,stage)-cell(7,stage))):
            contrasts.append(dict(name=name,endpoint=label,**stats(x)))
    contrasts += [dict(name='sustained_challenge_cost',endpoint='response',
                      **stats(cell(4,-1)-cell(4,-1,challenge=1))),
                  dict(name='sustained_rebound',endpoint='response',**stats(cell(4,-1)-cell(4,instant)))]
    primary = next(x for x in contrasts if x['name']=='duration_writing_interaction' and x['endpoint']=='response')
    endpoints = dict(brief_old_pre=stats(cell(2,pre,metric=1)),brief_old_post=stats(cell(2,-1,metric=1)),
        sustained_new_pre=stats(cell(4,pre)),sustained_new_post=stats(cell(4,-1)),
        sustained_incoming_R_new=stats(cell(4,0,metric=2)),
        sustained_challenge_drop=stats(cell(4,pre)-cell(4,instant)),
        sustained_rebound=stats(cell(4,-1)-cell(4,instant)))
    criteria = {name: value['mean']>=.8 for name,value in endpoints.items()
                if name not in ('sustained_challenge_drop','sustained_rebound')}
    criteria.update(primary_positive_interval=primary['pointwise_block_bootstrap_95'][0]>0,
        primary_consistency=primary['block_positive']>=6,
        challenge_measurable=endpoints['sustained_challenge_drop']['mean']>=.10,
        rebound_measurable=endpoints['sustained_rebound']['mean']>=.10)
    return common | dict(primary=primary,contrasts=contrasts,endpoints=endpoints,
        behavioral_criteria=criteria,bounded_pattern_supported=all(criteria.values()))


def contract():
    return dict(schema='l15_exposure_defense_v1',decision='D098',law='L15',run_id=RUN_ID,
        qualification_id=QUAL_ID,config=asdict(CONFIG),tissues=list(TISSUES),qualification_tissues=list(QUAL_TISSUES),
        disposable=DISPOSABLE,seed_tag=TAG,records=list(RECORDS),qualification_records=list(CONTROLS),
        metrics=list(METRICS),regions=list(REGIONS),gains=list(GAINS),challenge_order=[True,False],
        main_futures=576,qualification_futures=192,alias_futures_per_phase=96,
        theta='native fixed unprojected',record_bytes=2048,history_carried_to_matched_readout=['R'],
        readout_rho=.002,exposure_rates=[.002,0.],new_rate_sweep=False,
        primary='(sustained_live-brief_live)-(sustained_held-brief_held), new-sign conflict fidelity, active reader, response80',
        qualification_gates=dict(mean_fidelity=.8,min_tissue_fidelity=.75,min_tissue_content_strict=.2,
            mean_challenge_loss=.10,min_tissue_challenge_loss=.05,mean_rebound=.10,min_tissue_rebound=.05),
        full_independent_replay=True,state_atol=1e-10,metric_atol=1e-12,exact_signs=True,
        uncertainty='10000 equal-whole-tissue percentile bootstrap pointwise 95',
        no_universal_biological_or_heredity_claim=True,automatic_retry=False,automatic_follow_on=False)
