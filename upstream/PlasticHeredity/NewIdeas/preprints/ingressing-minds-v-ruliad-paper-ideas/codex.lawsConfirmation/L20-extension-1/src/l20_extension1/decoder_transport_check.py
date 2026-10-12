"""D165 independent standardized forward replay and direct-loss checks."""
import numpy as np
from . import asymmetry as a, asymmetry_check as old, decoder_transport as m

close = old.close


def forecasts(rules, features, p, raw, heldout_ids=None):
    assert set(p) == set(raw) == set(a.OBSERVERS)
    n = len(features['start']); maximum = 0.
    for name in a.OBSERVERS:
        x = old.matrix(features,name)
        for b, rule in enumerate(rules):
            if heldout_ids is not None:
                assert heldout_ids.tolist() == [r['validation_block'] for r in rules]
                assert len(heldout_ids) == n and int(heldout_ids[b]) not in rule['training_blocks']
                values = x[b:b+1]
            else:values = x
            for ai in range(3):
                want = old.forward(rule['models'][name][ai],values)
                got = raw[name][b,ai] if heldout_ids is None else raw[name][ai,b:b+1]
                clipped = p[name][b,ai] if heldout_ids is None else p[name][ai,b:b+1]
                assert want.shape == got.shape == clipped.shape
                close(got,want,2e-10);close(clipped,np.clip(want,-1,1),2e-10)
                assert np.array_equal(clipped,np.clip(got,-1,1))
                maximum = max(maximum,float(np.max(abs(got-want))))
    return dict(passes=True,max_forward_difference=maximum,
                forecast_values=51*16*n*(len(rules) if heldout_ids is None else 1))


def reduced(row, value):
    n = len(value); blocks = np.sum(value,axis=(1,2,3))/64; futures = np.sum(value,axis=(0,1,2))/(16*n)
    close(row['overall'],np.sum(value)/(64*n));close(row['blocks'],blocks)
    close(row['groups'],np.sum(value,axis=(0,1,3))/(16*n));close(row['futures'],futures)
    if n==1:assert row['omit_founder'] is None
    else:close(row['omit_founder'],[np.delete(blocks,i).mean() for i in range(n)])
    close(row['omit_future'],[np.delete(futures,i).mean() for i in range(4)])


def direct_losses(p,y):
    """Expanded squared error, one calibration at a time; never ensemble."""
    result = {}
    for name in a.OBSERVERS:
        rows = []
        for ai in range(3):
            total = np.zeros_like(y)
            for prediction in p[name][:,ai]:
                v = prediction[...,None]
                total += v*v-2*v*y+y*y
            rows.append(total/len(p[name]))
        result[name] = np.stack(rows)
    return result


def weighted(losses,name,ai):
    return sum(w*losses[k][ai] for k,w in old.weighted(name))


def contrast(row,c,r):
    reduced(row,r-c);close([row['candidate_mse'],row['reference_mse']],[c.mean(),r.mean()])
    if r.mean():close(row['relative_gain_percent'],100*(r-c).mean()/r.mean(),1e-8)
    else:assert row['relative_gain_percent'] is None


def panel(s,p,raw,y,ids):
    nr=m.validate(p,raw,y,ids);n=len(ids)
    assert s['ids']==ids.tolist() and s['founders']==n and s['cases']==16*n and s['futures']==4
    assert s['calibrations']==nr and s['forecast_instances_per_observer_alpha']==nr*16*n
    assert s['calibration_averaging']=='loss_not_prediction'
    losses=direct_losses(p,y)
    assert set(s['absolute'])==set(a.OBSERVERS)
    for name in a.OBSERVERS:
        assert len(s['absolute'][name])==3
        for ai,alpha in enumerate(a.ALPHAS):
            row=s['absolute'][name][ai];error=p[name][:,ai,...,None]-y;cell=losses[name][ai]
            assert row['alpha']==alpha and row['clipped']==np.count_nonzero(p[name][:,ai]!=raw[name][:,ai])
            close([row['mse'],row['rmse_points'],row['mae_points'],row['bias_points']],
                [cell.sum()/(64*n),100*np.sqrt(cell.sum()/(64*n)),100*abs(error).sum()/(nr*64*n),100*error.sum()/(nr*64*n)])
            close(row['blocks'],cell.sum((1,2,3))/64);close(row['groups'],cell.sum((0,1,3))/(16*n))
            close(row['futures'],cell.sum((0,1,2))/(16*n))
    assert len(s['comparisons'])==277
    for row,spec in zip(s['comparisons'],a.specifications()):
        assert all(row[k]==v for k,v in spec.items())
        contrast(row,weighted(losses,spec['candidate'],a.ALPHAS.index(spec['candidate_alpha'])),
                      weighted(losses,spec['reference'],a.ALPHAS.index(spec['reference_alpha'])))
    close(s['within_future_variance'],np.sum((y-y.mean(-1,keepdims=True))**2)/(64*n))
    return losses


def source_bridge(s,prior,p,raw,y,ids):
    proof=old.check_cohort(prior,p,raw,y,ids)
    for name in a.OBSERVERS:
        for row,original in zip(s['absolute'][name],prior['absolute'][name]):
            for key in ('mse','rmse_points','mae_points','bias_points','clipped','blocks','groups','futures'):
                close(row[key],original[key])
    for row,original in zip(s['comparisons'],prior['comparisons']):
        for key in ('candidate_mse','reference_mse'):close(row[key],original[key])
        for key in ('overall','blocks','groups','futures','omit_founder','omit_future'):
            close(row[key],np.asarray(original[key])[...,-1])
    return proof


def summary(s,p,raw,dev,full,prior):
    dp,dr,dy,di=dev;fp,fr,py,pi=full;n=len(di)
    assert s['schema']=='d165_decoder_transport_v1'
    for key in ('new_fits','new_dynamics','new_diagnostic_cycles','new_founders'):assert s[key]==0
    assert s['new_forecasts']==51*n*16*len(pi) and s['saved_rules']==15*n
    assert s['reconstructed_development_forecasts']==51*16*n
    assert s['post_test_explanation'] is s['source_primary_unchanged'] is True
    assert s['prospective_evidence'] is s['confidence_intervals'] is s['automatic_successor'] is False
    assert set(s['cohorts'])=={'development','pilot','full16_pilot'}
    panel(s['cohorts']['development'],m.single(dp),m.single(dr),dy,di)
    pl=panel(s['cohorts']['pilot'],p,raw,py,pi)
    fl=panel(s['cohorts']['full16_pilot'],m.single(fp),m.single(fr),py,pi)
    assert len(s['calibrations'])==n
    for b,fold in enumerate(s['calibrations']):
        assert fold['validation_block']==int(di[b]) and fold['training_blocks']==di[di!=di[b]].tolist()
        panel(fold['development'],{k:v[None,:,b:b+1] for k,v in dp.items()},
              {k:v[None,:,b:b+1] for k,v in dr.items()},dy[b:b+1],di[b:b+1])
        panel(fold['pilot'],{k:v[b:b+1] for k,v in p.items()},{k:v[b:b+1] for k,v in raw.items()},py,pi)
    expected=[(k,ai) for k in a.OBSERVERS+tuple(e+':mean_sham_loss' for e in a.ENCODINGS) for ai in range(3)]
    assert len(s['transport_vs_full16'])==len(expected)==60
    for row,(name,ai) in zip(s['transport_vs_full16'],expected):
        assert (row['observer'],row['alpha'])==(name,a.ALPHAS[ai])
        contrast(row,weighted(pl,name,ai),weighted(fl,name,ai))
    assert len(s['cohort_gain_changes'])==277
    for j,(row,spec) in enumerate(zip(s['cohort_gain_changes'],a.specifications())):
        assert all(row[k]==v for k,v in spec.items())
        values=[f['pilot']['comparisons'][j]['overall']-f['development']['comparisons'][j]['overall'] for f in s['calibrations']]
        close(row['calibrations'],values);close(row['pilot_minus_development_gain'],np.mean(values))
        close(row['pilot_minus_development_gain'],s['cohorts']['pilot']['comparisons'][j]['overall']-
              s['cohorts']['development']['comparisons'][j]['overall'])
    bridges={}
    for name,cohort,args in [('development','development',dev),('pilot','full16_pilot',full)]:
        bridges[name]=source_bridge(s['cohorts'][cohort],prior['cohorts'][name]['scores'],*args)
    return dict(passes=True,score_panels=3+2*n,comparisons_per_panel=277,absolute_per_panel=51,
                transport_vs_full16=60,cohort_gain_changes=277,source_bridges=bridges,
                independent_pilot_founders=len(pi),independent_calibration_repetitions=False)
