"""D098 independent schedules, transfers, endpoints, qualification and pooling.

Reuses only D097's separately restated, calibrated step/initialization and
strict comparison helpers. No new production trajectory/metric/summary call.
"""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l15_repair_speed as prior
from laws_confirmation.io import canonical_digest

OLD = prior.checker()
TAG = 'l15-exposure-defense-v1'
RECORDS = ('none_live','none_held','brief_live','brief_held','sustained_live','sustained_held',
           'known_new','known_old','erased')
METRICS = ('V_new_sign','V_old_sign','R_new_sign','R_old_sign','V_new_mae','V_old_mae',
           'R_new_mae','R_old_mae','VR_mae','R_rms','V_mean','abs_V_ge_2')


def templates(cfg):
    old = np.full((16,16),-cfg.amplitude); old[:,:8] = cfg.amplitude
    new = np.full((16,16),-cfg.amplitude); new[:8,:] = cfg.amplitude
    return np.stack((old,new))


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
    for challenge in (True,False):
        v,ref = (a.copy() for a in endpoint)
        if challenge:
            change = np.zeros((16,16)); change[mask] = cfg.pulse*np.where(targets[0,mask]>0,1.,-1.)
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
    x = raw['readouts']; n = x.shape[0]; boundary = len(cfg.release_times)
    for rec in range(n):
        for gain in range(2):
            np.testing.assert_array_equal(x[rec,gain,0,:boundary],x[rec,gain,1,:boundary])
            np.testing.assert_array_equal(x[rec,gain,0,boundary,2],x[rec,gain,1,boundary,2])
            np.testing.assert_array_equal(x[rec,gain,0,boundary,2],x[rec,gain,0,boundary-1,2])
            np.testing.assert_array_equal(x[rec,gain,:,0,:2],x[0,0,:,0,:2])
        np.testing.assert_array_equal(x[rec,1,:,:,:2],x[0,1,:,:,:2])
    if not qualification:
        for rec in (3,5):
            np.testing.assert_array_equal(raw['records'][rec],raw['settled'][2])
            np.testing.assert_array_equal(x[rec],x[1])
        np.testing.assert_array_equal(raw['records'][1],raw['settled'][2])
    return True


def check_life(raw,meta,cfg):
    assert set(raw)=={'theta','targets','conflict','settled','exposures','records','readouts','values','exposure_values'}
    OLD.nested(meta['config'],asdict(cfg))
    qualification = meta['qualification']; assert type(qualification) is bool
    index,life = meta['index'],meta['life']; assert type(life) is int and 0<=life<cfg.lives
    assert meta['theta_writable'] is False
    names = RECORDS[6:] if qualification else RECORDS
    OLD.nested(meta['records'],list(names))
    tissue,ladder,_ = OLD.parameters(meta)
    target = templates(cfg); error = OLD.compare(raw['targets'],target)
    conflict = (target[0]>0)!=(target[1]>0)
    assert raw['conflict'].dtype==bool and raw['conflict'].shape==(16,16) and raw['conflict'].sum()==128
    np.testing.assert_array_equal(raw['conflict'],conflict)
    stream = random(index,life,'settle')
    settled,theta = OLD.settle(tissue,ladder,stream,1,cfg.settle)
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
    assert raw['readouts'].shape==(len(names),2,2,len(cfg.release_times)+len(cfg.response_times),3,16,16)
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
                exposure_histories=len(histories),readout_futures=len(names)*4)


def check_block(raw,meta,cfg,replay=True):
    qualification = meta['qualification']; assert type(qualification) is bool
    nh,nr = (0,3) if qualification else (6,9)
    OLD.nested(meta['config'],asdict(cfg)); assert len(meta['lives'])==cfg.lives
    shapes = dict(theta=(cfg.lives,16,16),targets=(cfg.lives,2,16,16),conflict=(cfg.lives,16,16),
        settled=(cfg.lives,3,16,16),exposures=(cfg.lives,nh,len(cfg.exposure_times),3,16,16),
        records=(cfg.lives,nr,16,16),readouts=(cfg.lives,nr,2,2,len(cfg.release_times)+len(cfg.response_times),3,16,16),
        values=(cfg.lives,nr,2,2,len(cfg.release_times)+len(cfg.response_times),2,12),
        exposure_values=(cfg.lives,nh,len(cfg.exposure_times),2,12))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape and raw[key].dtype==(bool if key=='conflict' else np.float64)
        assert np.isfinite(raw[key]).all()
    for life,record in enumerate(meta['lives']):
        assert type(record['life']) is int and record['life']==life and record['index']==meta['index']
        assert record['qualification'] is qualification and record['exact_alias_futures']==6
        piece = {k:v[life] for k,v in raw.items()}
        if replay:
            OLD.nested(record['replay'],check_life(piece,record,cfg))
        else:
            check_metrics(piece); aliases(piece,qualification,cfg)
            assert record['replay']['full_life_replay'] is True and 0<=record['replay']['max_abs']<=1e-10
    return True


def check_summary(summary,blocks,qualification,cfg):
    assert len(blocks)==8
    values = np.asarray([[metrics(b['readouts'][l],b['targets'][l]) for l in range(cfg.lives)] for b in blocks])
    nr = 3 if qualification else 9
    assert values.shape==(8,cfg.lives,nr,2,2,len(cfg.release_times)+len(cfg.response_times),2,12)
    draws = random(0,0,'qualification_bootstrap' if qualification else 'main_bootstrap').integers(0,8,(10000,8))
    def stats(lives):
        blocks = np.array([sum(row)/len(row) for row in lives])
        result = dict(mean=float(blocks.mean()),block_means=blocks.tolist(),life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(blocks[draws].mean(axis=1),(.025,.975)).tolist())
        for prefix,x in (('block_',blocks),('life_',lives)):
            result.update({prefix+'positive':int(np.count_nonzero(x>1e-12)),
                prefix+'negative':int(np.count_nonzero(x< -1e-12)),prefix+'tied':int(np.count_nonzero(abs(x)<=1e-12))})
        return result
    expected = dict(schema='l15_exposure_defense_summary_v1',qualification=qualification,
        tissues=list(range(44080,44088) if qualification else range(44000,44008)),lives_per_block=cfg.lives,
        records=list(RECORDS[6:] if qualification else RECORDS),gains=[.2,0.],challenges=[True,False],
        stages=[f'release_{t}' for t in cfg.release_times]+[f'response_{t}' for t in cfg.response_times],
        regions=['conflict','whole'],metrics=list(METRICS),means_axes='record,reader,challenge,stage,region,metric',
        cell_means=values.mean(axis=(0,1)).tolist(),futures=8*cfg.lives*nr*4,multiplicity_adjusted=False)
    pre,instant = len(cfg.release_times)-1,len(cfg.release_times)
    def cell(record,stage,gain=0,challenge=0,metric=0):
        return values[:,:,record,gain,challenge,stage,0,metric]
    if qualification:
        endpoints = dict(new_pre=cell(0,pre),new_post=cell(0,-1),content_pre=cell(0,pre)-cell(1,pre),
            content_post=cell(0,-1)-cell(1,-1),challenge_drop=cell(0,pre)-cell(0,instant),
            rebound=cell(0,-1)-cell(0,instant))
        ep = {name:stats(x) for name,x in endpoints.items()}
        gates = dict(new_pre_mean=ep['new_pre']['mean']>=.8,new_post_mean=ep['new_post']['mean']>=.8,
            new_pre_every_tissue=min(ep['new_pre']['block_means'])>=.75,
            new_post_every_tissue=min(ep['new_post']['block_means'])>=.75,
            content_pre_every_tissue=min(ep['content_pre']['block_means'])>.2,
            content_post_every_tissue=min(ep['content_post']['block_means'])>.2,
            challenge_mean=ep['challenge_drop']['mean']>=.10,
            challenge_every_tissue=min(ep['challenge_drop']['block_means'])>=.05,
            rebound_mean=ep['rebound']['mean']>=.10,rebound_every_tissue=min(ep['rebound']['block_means'])>=.05)
        expected.update(qualified=all(gates.values()),gates=gates,endpoints=ep)
    else:
        contrasts = []
        for endpoint,stage in (('release',pre),('response',-1)):
            long,brief = cell(4,stage),cell(2,stage)
            terms = (('duration_writing_interaction',long-brief-cell(5,stage)+cell(3,stage)),
                ('live_duration',long-brief),('sustained_writing',long-cell(5,stage)),
                ('brief_minus_none',brief-cell(0,stage)),('sustained_reading',long-cell(4,stage,gain=1)),
                ('sustained_minus_erased',long-cell(8,stage)),('known_new_minus_erased',cell(6,stage)-cell(8,stage)),
                ('known_content',cell(6,stage)-cell(7,stage)))
            for name,lives in terms:
                contrasts.append(dict(name=name,endpoint=endpoint,**stats(lives)))
        contrasts.append(dict(name='sustained_challenge_cost',endpoint='response',
                              **stats(cell(4,-1)-cell(4,-1,challenge=1))))
        contrasts.append(dict(name='sustained_rebound',endpoint='response',**stats(cell(4,-1)-cell(4,instant))))
        primary = next(c for c in contrasts if c['name']=='duration_writing_interaction' and c['endpoint']=='response')
        endpoints = dict(brief_old_pre=stats(cell(2,pre,metric=1)),brief_old_post=stats(cell(2,-1,metric=1)),
            sustained_new_pre=stats(cell(4,pre)),sustained_new_post=stats(cell(4,-1)),
            sustained_incoming_R_new=stats(cell(4,0,metric=2)),
            sustained_challenge_drop=stats(cell(4,pre)-cell(4,instant)),
            sustained_rebound=stats(cell(4,-1)-cell(4,instant)))
        criteria = {name:ep['mean']>=.8 for name,ep in endpoints.items()
                    if name not in ('sustained_challenge_drop','sustained_rebound')}
        criteria.update(primary_positive_interval=primary['pointwise_block_bootstrap_95'][0]>0,
            primary_consistency=primary['block_positive']>=6,
            challenge_measurable=endpoints['sustained_challenge_drop']['mean']>=.10,
            rebound_measurable=endpoints['sustained_rebound']['mean']>=.10)
        expected.update(primary=primary,contrasts=contrasts,endpoints=endpoints,
            behavioral_criteria=criteria,bounded_pattern_supported=all(criteria.values()))
    OLD.nested(summary,expected)
    return True


if __name__=='__main__':
    from laws_confirmation.l15_exposure_defense_run import main
    main(default_command='audit')
