"""D099 independent schedules, transfers, endpoints, qualification and pooling.

Reuses only D097's separately restated, calibrated step/initialization and
strict comparison helpers. No new production trajectory/metric/summary call.
"""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l15_repair_speed as prior
from laws_confirmation.io import canonical_digest

OLD = prior.checker()
TAG = 'l15-reversal-defense-v1'
RECORDS = ('none_live','none_held','brief_live','brief_held','sustained_live','sustained_held',
           'known_new','known_old','erased')
METRICS = ('V_new_sign','V_old_sign','R_new_sign','R_old_sign','V_new_mae','V_old_mae',
           'R_new_mae','R_old_mae','VR_mae','R_rms','V_mean','abs_V_ge_2')


def templates(cfg,direction):
    assert type(direction) is int and direction in (0,1)
    old = np.full((16,16),-cfg.amplitude); old[:,:8] = cfg.amplitude
    new = np.full((16,16),-cfg.amplitude); new[:8,:] = cfg.amplitude
    return np.stack((old,new) if direction==0 else (new,old))


def random(index,life,phase):
    return OLD.generator(TAG,index,life,phase)


def metrics(states,targets):
    masks = ((targets[0]>0)!=(targets[1]>0),np.ones((16,16),dtype=bool))
    scores = []
    for v,_,ref in states.reshape(-1,3,16,16):
        regions = []
        for mask in masks:
            b,r,o,n = v[mask],ref[mask],targets[0,mask],targets[1,mask]
            size = int(mask.sum())
            regions.append([np.count_nonzero((b>0)==(n>0))/size,
                np.count_nonzero((b>0)==(o>0))/size,np.count_nonzero((r>0)==(n>0))/size,
                np.count_nonzero((r>0)==(o>0))/size,abs(b-n).sum()/size,abs(b-o).sum()/size,
                abs(r-n).sum()/size,abs(r-o).sum()/size,abs(b-r).sum()/size,
                np.sqrt(np.dot(r,r)/size),b.sum()/size,np.count_nonzero(abs(b)>=2)/size])
        scores.append(regions)
    return np.asarray(scores,dtype=float).reshape(*states.shape[:-3],2,12)


def check_metrics(raw):
    for states,values in (('readouts','values'),('exposures','exposure_values')):
        actual,expected = raw[values],metrics(raw[states],raw['targets'])
        assert actual.shape==expected.shape and actual.dtype==np.float64 and np.isfinite(actual).all()
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
    return True


def replay_reader(record,meta,cfg,theta,targets,tissue,ladder,gain):
    index,life = meta['index'],meta['life']
    v = targets[1][None].copy(); ema = v.copy(); ref = record[None].copy()
    stream = random(index,life,'release')
    prefix = [np.stack((v[0],ema[0],ref[0]))]
    for t in range(1,cfg.release+1):
        v,ema,ref = OLD.step(v,ema,ref,theta,tissue,ladder,gain,.002,stream.standard_normal(v.shape))
        if t in cfg.release_times:
            prefix.append(np.stack((v[0],ema[0],ref[0])))
    release_rng = canonical_digest(stream.bit_generator.state)
    endpoint = (v.copy(),ref.copy()); branches = []; digests = []
    mask = (targets[0]>0)!=(targets[1]>0)
    for pulse in range(3):
        v,ref = (a.copy() for a in endpoint)
        if pulse<2:
            change = np.zeros((16,16)); change[mask] = cfg.pulse*np.where(targets[pulse,mask]>0,1.,-1.)
            v = v+change[None]
        ema = v.copy(); saved = [*prefix,np.stack((v[0],ema[0],ref[0]))]
        stream = random(index,life,'response')
        for t in range(1,cfg.response+1):
            v,ema,ref = OLD.step(v,ema,ref,theta,tissue,ladder,gain,.002,stream.standard_normal(v.shape))
            if t in cfg.response_times:
                saved.append(np.stack((v[0],ema[0],ref[0])))
        branches.append(np.stack(saved)); digests.append(canonical_digest(stream.bit_generator.state))
    packet = record.astype('<f8',copy=False).tobytes()
    return np.stack(branches),dict(packet_sha256=hashlib.sha256(packet).hexdigest(),
        release_rng=release_rng,response_rng=digests)


def aliases(raw,qualification,cfg):
    x = raw['readouts']; boundary = len(cfg.release_times)
    targets = raw['targets']; mask = raw['conflict']
    for rec in range(x.shape[0]):
        for gain in range(2):
            for pulse in range(3):
                np.testing.assert_array_equal(x[rec,gain,pulse,:boundary],x[rec,gain,0,:boundary])
                np.testing.assert_array_equal(x[rec,gain,pulse,boundary,2],x[rec,gain,0,boundary-1,2])
                np.testing.assert_array_equal(x[rec,gain,pulse,0,:2],x[0,0,0,0,:2])
                before = x[rec,gain,pulse,boundary-1,0]
                change = cfg.pulse*np.sign(targets[pulse])*mask if pulse<2 else 0.
                np.testing.assert_array_equal(x[rec,gain,pulse,boundary,0],before+change)
                np.testing.assert_array_equal(x[rec,gain,pulse,boundary,1],x[rec,gain,pulse,boundary,0])
        np.testing.assert_array_equal(x[rec,1,:,:,:2],x[0,1,:,:,:2])
    if not qualification:
        for rec in (1,3,5):
            np.testing.assert_array_equal(raw['records'][rec],raw['settled'][2])
            np.testing.assert_array_equal(x[rec],x[1])
    return True


def settle(tissue,ladder,stream,steps,direction):
    theta = tissue.threshold_spread*OLD.generator(tissue.tissue_tag,tissue.tissue_index).standard_normal((16,16))
    start = np.full((16,16),-1.)
    if direction==0: start[:,:8] = 1.
    else: start[:8,:] = 1.
    v = start[None].copy()+tissue.copy_jitter*stream.standard_normal((1,16,16))
    ema,ref = v.copy(),v.copy()
    for _ in range(steps):
        v,ema,ref = OLD.step(v,ema,ref,theta,tissue,ladder,.2,.002,stream.standard_normal(v.shape))
    return np.stack((v,ema,ref)),theta


def check_life(raw,meta,cfg):
    assert set(raw)=={'theta','targets','conflict','settled','exposures','records','readouts','values','exposure_values'}
    OLD.nested(meta['config'],asdict(cfg))
    qualification = meta['qualification']; assert type(qualification) is bool
    index,life = meta['index'],meta['life']; assert type(life) is int and 0<=life<cfg.lives
    assert meta['theta_writable'] is False
    names = RECORDS[6:] if qualification else RECORDS
    OLD.nested(meta['records'],list(names))
    tissue,ladder,_ = OLD.parameters(meta)
    direction = meta['direction']; assert type(direction) is int and direction in (0,1)
    assert type(meta['formation_seed_index']) is int and meta['formation_seed_index']==direction
    target = templates(cfg,direction); error = OLD.compare(raw['targets'],target)
    conflict = (target[0]>0)!=(target[1]>0)
    assert raw['conflict'].dtype==bool and raw['conflict'].shape==(16,16) and raw['conflict'].sum()==128
    np.testing.assert_array_equal(raw['conflict'],conflict)
    stream = random(index,life,'settle')
    settled,theta = settle(tissue,ladder,stream,cfg.settle,direction)
    error = max(error,OLD.compare(raw['settled'],settled[:,0]),OLD.compare(raw['theta'],theta))
    assert canonical_digest(stream.bit_generator.state)==meta['settle_rng']
    histories = []
    for schedule in (() if qualification else ('none','brief','sustained')):
        for writing in (True,False):
            v,ema,ref = (a.copy() for a in settled)
            saved = [settled[:,0].copy()]; stream = random(index,life,'exposure')
            for t in range(1,cfg.exposure+1):
                is_new = schedule=='sustained' or (schedule=='brief' and t>=cfg.exposure-cfg.brief+1)
                v = target[1 if is_new else 0][None].copy()
                v,ema,ref = OLD.step(v,ema,ref,theta,tissue,ladder,.2,.002 if writing else 0.,
                                    stream.standard_normal(v.shape))
                if t in cfg.exposure_times:
                    saved.append(np.stack((v[0],ema[0],ref[0])))
            assert canonical_digest(stream.bit_generator.state)==meta['exposure_rng'][len(histories)]
            histories.append(np.stack(saved))
    assert len(meta['exposure_rng'])==len(histories)
    trace = np.stack(histories) if histories else np.empty((0,len(cfg.exposure_times),3,16,16))
    error = max(error,OLD.compare(raw['exposures'],trace))
    known = np.stack((target[1],target[0],np.zeros((16,16))))
    records = known if qualification else np.concatenate((trace[:,-1,2],known))
    error = max(error,OLD.compare(raw['records'],records))
    assert raw['readouts'].shape==(len(names),2,3,len(cfg.release_times)+len(cfg.response_times),3,16,16)
    assert len(meta['readouts'])==len(names)
    for r,record in enumerate(records):
        assert len(meta['readouts'][r])==2
        for g,gain in enumerate((.2,0.)):
            states,expected_meta = replay_reader(record,meta,cfg,theta,target,tissue,ladder,gain)
            error = max(error,OLD.compare(raw['readouts'][r,g],states))
            OLD.nested(meta['readouts'][r][g],expected_meta)
    check_metrics(raw); aliases(raw,qualification,cfg)
    return dict(max_abs=error,full_life_replay=True,exact_signs=True,metrics_pass=True,
                body_matching=True,reader_off_aliases=True,held_writing_aliases=not qualification,
                exposure_histories=len(histories),readout_futures=len(names)*6)


def check_block(raw,meta,cfg,replay=True):
    qualification = meta['qualification']; assert type(qualification) is bool
    nh,nr = (0,3) if qualification else (6,9)
    OLD.nested(meta['config'],asdict(cfg)); assert len(meta['lives'])==cfg.lives
    prefix = (cfg.lives,2); nt = len(cfg.release_times)+len(cfg.response_times)
    shapes = dict(theta=prefix+(16,16),targets=prefix+(2,16,16),conflict=prefix+(16,16),
        settled=prefix+(3,16,16),exposures=prefix+(nh,len(cfg.exposure_times),3,16,16),
        records=prefix+(nr,16,16),readouts=prefix+(nr,2,3,nt,3,16,16),
        values=prefix+(nr,2,3,nt,2,12),exposure_values=prefix+(nh,len(cfg.exposure_times),2,12))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape and raw[key].dtype==(bool if key=='conflict' else np.float64)
        assert np.isfinite(raw[key]).all()
    for life,row in enumerate(meta['lives']):
        assert type(row['life']) is int and row['life']==life and len(row['directions'])==2
        np.testing.assert_array_equal(raw['theta'][life,0],raw['theta'][life,1])
        for direction,record in enumerate(row['directions']):
            assert type(record['life']) is int and record['life']==life and record['index']==meta['index']
            assert type(record['direction']) is int and record['direction']==direction
            assert record['qualification'] is qualification and record['exact_alias_futures']==9
            piece = {k:v[life,direction] for k,v in raw.items()}
            if replay:
                OLD.nested(record['replay'],check_life(piece,record,cfg))
            else:
                check_metrics(piece); aliases(piece,qualification,cfg)
                assert record['replay']['full_life_replay'] is True and 0<=record['replay']['max_abs']<=1e-10
        for key in ('settle_rng','exposure_rng'):
            assert row['directions'][0][key]==row['directions'][1][key]
    return True


def check_summary(summary,blocks,qualification,cfg):
    assert len(blocks)==8
    data = np.asarray([[[metrics(b['readouts'][l,d],b['targets'][l,d])
                        for d in (0,1)] for l in range(cfg.lives)] for b in blocks])
    nr = 3 if qualification else 9
    assert data.shape==(8,cfg.lives,2,nr,2,3,len(cfg.release_times)+len(cfg.response_times),2,12)
    draws = random(0,0,'qualification_bootstrap' if qualification else 'main_bootstrap').integers(0,8,(10000,8))
    def stats(x):
        tissue = np.array([sum(lives)/len(lives) for lives in x])
        result = dict(mean=float(sum(tissue)/8),block_means=tissue.tolist(),life_values=x.tolist(),
            pointwise_block_bootstrap_95=np.quantile(tissue[draws].mean(1),(.025,.975)).tolist())
        for prefix,values in (('block_',tissue),('life_',x)):
            result.update({prefix+'positive':int(np.count_nonzero(values>1e-12)),
                prefix+'negative':int(np.count_nonzero(values< -1e-12)),
                prefix+'tied':int(np.count_nonzero(abs(values)<=1e-12))})
        return result
    def at(direction,record,stage,pulse=0,metric=0,reader=0):
        return data[:,:,direction,record,reader,pulse,stage,0,metric]
    pre,instant = len(cfg.release_times)-1,len(cfg.release_times)
    expected = dict(schema='l15_reversal_defense_summary_v1',qualification=qualification,
        tissues=list(range(45080,45088) if qualification else range(45000,45008)),lives_per_block=cfg.lives,
        directions=[0,1],records=list(RECORDS[6:] if qualification else RECORDS),gains=[.2,0.],
        pulses=['toward_old','toward_new','sham'],
        stages=[f'release_{t}' for t in cfg.release_times]+[f'response_{t}' for t in cfg.response_times],
        regions=['conflict','whole'],metrics=list(METRICS),means_axes='direction,record,reader,pulse,stage,region,metric',
        cell_means=data.mean(axis=(0,1)).tolist(),futures=8*cfg.lives*nr*12,multiplicity_adjusted=False)
    ep,gates = {},{}
    if qualification:
        for direction in (0,1):
            for label,r,wrong,pulse,metric in (('new',0,1,0,0),('old',1,0,1,1)):
                prefix = f'd{direction}_{label}_'
                a=at(direction,r,pre,pulse,metric); b=at(direction,r,-1,pulse,metric)
                immediate=at(direction,r,instant,pulse,metric)
                terms=dict(pre=a,post=b,content_pre=a-at(direction,wrong,pre,pulse,metric),
                    content_post=b-at(direction,wrong,-1,pulse,metric),drop=a-immediate,rebound=b-immediate)
                rows={n:stats(x) for n,x in terms.items()}
                ep.update({prefix+n:v for n,v in rows.items()})
                for n in ('pre','post','drop','rebound'):
                    gate=.8 if n in ('pre','post') else .1
                    minimum=.75 if n in ('pre','post') else .05
                    gates[prefix+n+'_mean']=rows[n]['mean']>=gate
                    gates[prefix+n+'_every_tissue']=min(rows[n]['block_means'])>=minimum
                for n in ('content_pre','content_post'):
                    gates[prefix+n+'_every_tissue']=min(rows[n]['block_means'])>.2
        expected.update(qualified=all(gates.values()),gates=gates,endpoints=ep)
    else:
        contrasts=[]; changes=[]
        for direction in (0,1):
            def difference(stage,pulse,reader=0):
                active=at(direction,4,stage,pulse,reader=reader)-at(direction,2,stage,pulse,reader=reader)
                held=at(direction,5,stage,pulse,reader=reader)-at(direction,3,stage,pulse,reader=reader)
                return active-held
            paired=np.stack((difference(-1,0),difference(-1,1))).mean(0); changes.append(paired)
            terms=[('pulse_averaged_duration',paired),
                   ('reader_off_duration',np.stack((difference(-1,0,1),difference(-1,1,1))).mean(0)),
                   ('release_duration',difference(pre,0))]
            terms.extend(('duration_'+label,difference(-1,p)) for p,label in enumerate(('toward_old','toward_new','sham')))
            def average(record,reader=0):
                return np.stack([at(direction,record,-1,p,reader=reader) for p in (0,1)]).mean(0)
            terms.extend((('sustained_writing',average(4)-average(5)),('sustained_reading',average(4)-average(4,1)),
                          ('brief_minus_none',average(2)-average(0)),('sustained_minus_erased',average(4)-average(8)),
                          ('known_new_minus_erased',average(6)-average(8)),('known_content',average(6)-average(7))))
            contrasts.extend(dict(direction=direction,name=n,**stats(x)) for n,x in terms)
            for label,record,pulse,metric,refmetric in (('brief_old',2,1,1,3),('sustained_new',4,0,0,2)):
                prefix=f'd{direction}_{label}_'
                a=at(direction,record,pre,pulse,metric); b=at(direction,record,-1,pulse,metric)
                c=at(direction,record,instant,pulse,metric)
                named=dict(pre=a,post=b,incoming_R=at(direction,record,0,0,refmetric),drop=a-c,rebound=b-c,
                           challenge_cost=b-at(direction,record,-1,2,metric))
                for name,x in named.items():
                    row=stats(x)
                    if name in ('pre','post','incoming_R'):
                        row.update(tissues_ge_80=sum(t>=.8 for t in row['block_means']),
                                   lives_ge_80=sum(t>=.8 for life in row['life_values'] for t in life))
                    ep[prefix+name]=row
                    if name!='challenge_cost':
                        gates[prefix+name]=row['mean']>=(.1 if name in ('drop','rebound') else .8)
            gates[f'd{direction}_positive_tissues']=stats(paired)['block_positive']>=6
        direction_stats=[stats(x) for x in changes]
        block_matrix=np.array([x['block_means'] for x in direction_stats])
        means=[x['mean'] for x in direction_stats]
        boot=np.minimum(block_matrix[0,draws].mean(1),block_matrix[1,draws].mean(1))
        primary=dict(name='minimum_direction_pulse_averaged_duration',mean=min(means),direction_means=means,
            pointwise_block_bootstrap_95=np.quantile(boot,(.025,.975)).tolist(),
            definition='minimum of direction cohort means, not mean of per-life minima')
        gates['primary_positive_interval']=primary['pointwise_block_bootstrap_95'][0]>0
        expected.update(primary=primary,direction_contrasts=direction_stats,contrasts=contrasts,
            direction_interaction=stats(changes[1]-changes[0]),equal_direction_mean=stats((changes[0]+changes[1])/2),
            endpoints=ep,behavioral_criteria=gates,bounded_pattern_supported=all(gates.values()))
    OLD.nested(summary,expected)
    return True


if __name__=='__main__':
    from laws_confirmation.l15_reversal_defense_run import main
    main(default_command='audit')
