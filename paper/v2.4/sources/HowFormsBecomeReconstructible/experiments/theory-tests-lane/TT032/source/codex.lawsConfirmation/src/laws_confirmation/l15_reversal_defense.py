"""D099: reversed old-pattern formation and symmetric reference defense."""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import importlib.util

import numpy as np

from . import l15_exposure_defense as previous
from .io import canonical_digest

base, WS = previous.base, previous.WS
Config, CONFIG = previous.Config, previous.CONFIG
encode, decode, measure = previous.encode, previous.decode, previous.measure
HISTORIES, RECORDS, CONTROLS = previous.HISTORIES, previous.RECORDS, previous.CONTROLS
METRICS, REGIONS, GAINS = previous.METRICS, previous.REGIONS, previous.GAINS
RUN_ID = 'l15_reversal_defense_v1_attempt1'
QUAL_ID = 'l15_reversal_defense_v1_qualification_attempt1'
TAG = 'l15-reversal-defense-v1'
TISSUES, QUAL_TISSUES = tuple(range(45000,45008)), tuple(range(45080,45088))
DISPOSABLE = 514199
DIRECTIONS = (0,1)
PULSES = ('toward_old','toward_new','sham')
SCIENCE = ('src/laws_confirmation/l15_reversal_defense.py',
           'src/laws_confirmation/l15_reversal_defense_run.py',
           'scripts/audit_l15_reversal_defense_outputs.py',
           'tests/test_l15_reversal_defense.py',
           'scripts/run_l15_reversal_defense.sh','protocols/L15_REVERSAL_DEFENSE_V1.md')


def direction_checked(direction):
    if type(direction) is not int or direction not in DIRECTIONS:
        raise ValueError('direction must be the public old recipe index, 0 or 1')
    return direction


def rng(index,life,phase):
    seed = hashlib.sha256(f'{TAG}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(seed[:16],'little')))


def checker():
    spec = importlib.util.spec_from_file_location('d099_independent_checker',WS/SCIENCE[2])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def targets(ctx,direction,cfg=CONFIG):
    direction_checked(direction)
    from voltage_web.engine import launch_pattern
    return cfg.amplitude*np.stack([launch_pattern(i,ctx['tissue']) for i in (direction,1-direction)])


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


def readout(index,packet,life,direction,gain,cfg=CONFIG):
    """Direction fixes the common body; no history/record label or body packet."""
    direction_checked(direction)
    if type(life) is not int or not 0<=life<cfg.lives or type(gain) is bool or gain not in GAINS:
        raise ValueError('undeclared life or reader gain')
    ctx = base.context(index); templates = targets(ctx,direction,cfg)
    from voltage_web.engine import make_thresholds
    theta = make_thresholds(ctx['tissue']); theta.setflags(write=False)
    ref = decode(packet)[None].copy()
    v = templates[1][None].copy(); ema = v.copy()
    random = rng(index,life,'release'); bp = replace(ctx['bp'],c_m=gain)
    prefix = [np.stack((v[0],ema[0],ref[0]))]
    for t in range(1,cfg.release+1):
        v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],ctx['ladder'],bp,'T',random)
        if t in cfg.release_times:
            prefix.append(np.stack((v[0],ema[0],ref[0])))
    before = (v.copy(),ref.copy()); release_rng = canonical_digest(random.bit_generator.state)
    conflict = (templates[0]>0)!=(templates[1]>0)
    branches,digests = [],[]
    for pulse in range(3):
        v,ref = (x.copy() for x in before)
        if pulse<2:
            v = v+(cfg.pulse*np.sign(templates[pulse])*conflict)[None]
        ema = v.copy(); saved = [*prefix,np.stack((v[0],ema[0],ref[0]))]
        random = rng(index,life,'response')
        for t in range(1,cfg.response+1):
            v,ema,ref = ctx['api']['blueprint_step'](v,ema,ref,theta,ctx['tissue'],ctx['ladder'],bp,'T',random)
            if t in cfg.response_times:
                saved.append(np.stack((v[0],ema[0],ref[0])))
        branches.append(np.stack(saved)); digests.append(canonical_digest(random.bit_generator.state))
    return np.stack(branches),dict(packet_sha256=hashlib.sha256(packet).hexdigest(),
        release_rng=release_rng,response_rng=digests)


def simulate_life(index,life,direction,qualification=False,cfg=CONFIG):
    direction_checked(direction)
    if type(life) is not int or not 0<=life<cfg.lives or type(qualification) is not bool:
        raise ValueError('declared life and Boolean phase required')
    ctx = base.context(index); templates = targets(ctx,direction,cfg)
    random = rng(index,life,'settle')
    v,ema,ref,theta,_ = ctx['api']['settle_with_blueprint'](
        ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle,seed_index=direction)
    theta.setflags(write=False); settled = np.stack((v[0],ema[0],ref[0]))
    histories = [] if qualification else [exposure(ctx,settled,theta,templates,life,h,cfg) for h in HISTORIES]
    trace = np.stack([x[0] for x in histories]) if histories else np.empty((0,len(cfg.exposure_times),3,16,16))
    known = np.stack((templates[1],templates[0],np.zeros((16,16))))
    records = known if qualification else np.concatenate((trace[:,-1,2],known))
    reads,read_meta = [],[]
    for record in records:
        outcomes = [readout(index,encode(record),life,direction,g,cfg) for g in GAINS]
        reads.append(np.stack([o[0] for o in outcomes])); read_meta.append([o[1] for o in outcomes])
    states = np.stack(reads)
    raw = dict(theta=theta,targets=templates,conflict=(templates[0]>0)!=(templates[1]>0),
        settled=settled,exposures=trace,records=records,readouts=states,values=measure(states,templates),
        exposure_values=measure(trace,templates))
    meta = dict(index=index,life=life,direction=direction,formation_seed_index=direction,
        qualification=qualification,config=asdict(cfg),records=list(CONTROLS if qualification else RECORDS),
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        settle_rng=canonical_digest(random.bit_generator.state),exposure_rng=[x[1] for x in histories],
        readouts=read_meta,theta_writable=theta.flags.writeable)
    return raw,meta


def execute_block(index,qualification=False,cfg=CONFIG):
    rows,metadata = [],[]; check = checker()
    for life in range(cfg.lives):
        directions,meta_dirs = [],[]
        for direction in DIRECTIONS:
            raw,meta = simulate_life(index,life,direction,qualification,cfg)
            meta['replay'] = check.check_life(raw,meta,cfg)
            for rec in ((0,1,0) if qualification else (4,2,4)):
                alias,digests = readout(index,encode(raw['records'][rec]),life,direction,.2,cfg)
                np.testing.assert_array_equal(alias,raw['readouts'][rec,0])
                assert digests==meta['readouts'][rec][0]
            meta['exact_alias_futures'] = 9
            directions.append(raw); meta_dirs.append(meta)
        rows.append({k:np.stack([r[k] for r in directions]) for k in directions[0]})
        metadata.append(dict(life=life,directions=meta_dirs))
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(
        index=index,qualification=qualification,config=asdict(cfg),lives=metadata)


def summarize(blocks,qualification=False,cfg=CONFIG):
    if type(qualification) is not bool or len(blocks)!=8:
        raise ValueError('Boolean phase and all eight blocks required')
    nr = 3 if qualification else 9
    values = np.stack([r['values'] for r in blocks])
    expected = (8,cfg.lives,2,nr,2,3,len(cfg.release_times)+len(cfg.response_times),2,12)
    if values.shape!=expected or not np.isfinite(values).all():
        raise ValueError('complete finite paired direction table required')
    draws = rng(0,0,'qualification_bootstrap' if qualification else 'main_bootstrap').integers(0,8,(10000,8))
    def stats(x): return base.contrast_stats(x,draws)
    def cell(d,r,t,g=0,pulse=0,metric=0): return values[:,:,d,r,g,pulse,t,0,metric]
    pre,instant = len(cfg.release_times)-1,len(cfg.release_times)
    common = dict(schema='l15_reversal_defense_summary_v1',qualification=qualification,
        tissues=list(QUAL_TISSUES if qualification else TISSUES),lives_per_block=cfg.lives,
        directions=[0,1],records=list(CONTROLS if qualification else RECORDS),gains=list(GAINS),pulses=list(PULSES),
        stages=[f'release_{t}' for t in cfg.release_times]+[f'response_{t}' for t in cfg.response_times],
        regions=list(REGIONS),metrics=list(METRICS),means_axes='direction,record,reader,pulse,stage,region,metric',
        cell_means=values.mean(axis=(0,1)).tolist(),futures=8*cfg.lives*nr*12,multiplicity_adjusted=False)
    endpoints,gates = {},{}
    if qualification:
        for d in DIRECTIONS:
            for target,r,other,pulse,m in (('new',0,1,0,0),('old',1,0,1,1)):
                prefix = f'd{d}_{target}_'
                a,b = cell(d,r,pre,pulse=pulse,metric=m),cell(d,r,-1,pulse=pulse,metric=m)
                at = cell(d,r,instant,pulse=pulse,metric=m)
                named = dict(pre=a,post=b,content_pre=a-cell(d,other,pre,pulse=pulse,metric=m),
                    content_post=b-cell(d,other,-1,pulse=pulse,metric=m),drop=a-at,rebound=b-at)
                ep = {n:stats(x) for n,x in named.items()}; endpoints.update({prefix+n:x for n,x in ep.items()})
                criteria = dict(pre_mean=a.mean()>=.8,post_mean=b.mean()>=.8,
                    pre_every_tissue=np.all(a.mean(1)>=.75),post_every_tissue=np.all(b.mean(1)>=.75),
                    content_pre_every_tissue=np.all(named['content_pre'].mean(1)>.2),
                    content_post_every_tissue=np.all(named['content_post'].mean(1)>.2),
                    drop_mean=named['drop'].mean()>=.1,drop_every_tissue=np.all(named['drop'].mean(1)>=.05),
                    rebound_mean=named['rebound'].mean()>=.1,rebound_every_tissue=np.all(named['rebound'].mean(1)>=.05))
                gates.update({prefix+n:bool(x) for n,x in criteria.items()})
        return common | dict(qualified=all(gates.values()),gates=gates,endpoints=endpoints)
    contrasts,duration = [],[]
    for d in DIRECTIONS:
        def interaction(t,pulse,g=0):
            return cell(d,4,t,g,pulse)-cell(d,2,t,g,pulse)-cell(d,5,t,g,pulse)+cell(d,3,t,g,pulse)
        x = (interaction(-1,0)+interaction(-1,1))/2; duration.append(x)
        contrasts.append(dict(direction=d,name='pulse_averaged_duration',**stats(x)))
        contrasts.append(dict(direction=d,name='reader_off_duration',**stats((interaction(-1,0,1)+interaction(-1,1,1))/2)))
        contrasts.append(dict(direction=d,name='release_duration',**stats(interaction(pre,0))))
        for pulse,name in enumerate(PULSES):
            contrasts.append(dict(direction=d,name='duration_'+name,**stats(interaction(-1,pulse))))
        def avg(r,g=0): return (cell(d,r,-1,g,0)+cell(d,r,-1,g,1))/2
        for name,x in (('sustained_writing',avg(4)-avg(5)),('sustained_reading',avg(4)-avg(4,1)),
                       ('brief_minus_none',avg(2)-avg(0)),('sustained_minus_erased',avg(4)-avg(8)),
                       ('known_new_minus_erased',avg(6)-avg(8)),('known_content',avg(6)-avg(7))):
            contrasts.append(dict(direction=d,name=name,**stats(x)))
        for label,r,pulse,m,rm in (('brief_old',2,1,1,3),('sustained_new',4,0,0,2)):
            prefix = f'd{d}_{label}_'
            a,b = cell(d,r,pre,pulse=pulse,metric=m),cell(d,r,-1,pulse=pulse,metric=m)
            at = cell(d,r,instant,pulse=pulse,metric=m)
            named = dict(pre=a,post=b,incoming_R=cell(d,r,0,metric=rm),drop=a-at,rebound=b-at,
                         challenge_cost=b-cell(d,r,-1,pulse=2,metric=m))
            for name,x in named.items():
                ep = stats(x)
                if name in ('pre','post','incoming_R'):
                    ep.update(tissues_ge_80=int(np.count_nonzero(x.mean(1)>=.8)),
                              lives_ge_80=int(np.count_nonzero(x>=.8)))
                endpoints[prefix+name] = ep
                if name!='challenge_cost': gates[prefix+name] = bool(x.mean()>=(.1 if name in ('drop','rebound') else .8))
        gates[f'd{d}_positive_tissues'] = stats(duration[-1])['block_positive']>=6
    dir_blocks = np.stack([x.mean(1) for x in duration],axis=1)
    means = dir_blocks.mean(0)
    primary = dict(name='minimum_direction_pulse_averaged_duration',mean=float(means.min()),
        direction_means=means.tolist(),
        pointwise_block_bootstrap_95=np.quantile(dir_blocks[draws].mean(1).min(1),(.025,.975)).tolist(),
        definition='minimum of direction cohort means, not mean of per-life minima')
    gates['primary_positive_interval'] = primary['pointwise_block_bootstrap_95'][0]>0
    return common | dict(primary=primary,direction_contrasts=[stats(x) for x in duration],contrasts=contrasts,
        direction_interaction=stats(duration[1]-duration[0]),equal_direction_mean=stats((duration[0]+duration[1])/2),
        endpoints=endpoints,behavioral_criteria=gates,bounded_pattern_supported=all(gates.values()))


def contract():
    return dict(schema='l15_reversal_defense_v1',decision='D099',law='L15',run_id=RUN_ID,qualification_id=QUAL_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),qualification_tissues=list(QUAL_TISSUES),disposable=DISPOSABLE,
        seed_tag=TAG,directions=[0,1],formation_seed_index='direction',records=list(RECORDS),
        qualification_records=list(CONTROLS),gains=list(GAINS),pulses=list(PULSES),metrics=list(METRICS),regions=list(REGIONS),
        main_futures=1728,qualification_futures=576,alias_futures_per_phase=288,paired_lives_per_phase=16,
        direction_life_replays_per_phase=32,record_bytes=2048,history_carried_to_matched_readout=['R'],
        primary='minimum direction mean of pulse-averaged duration-writing interaction at response80',
        qualification_gate_count=40,mean_fidelity_gate=.8,min_qualification_tissue_fidelity=.75,
        native_rho=.002,active_gain=.2,theta='native fixed unprojected',
        full_independent_replay=True,state_atol=1e-10,metric_atol=1e-12,exact_signs=True,
        uncertainty='10000 equal-whole-tissue paired percentile bootstrap pointwise 95',
        no_universal_biological_or_heredity_claim=True,automatic_retry=False,automatic_follow_on=False)
