"""Synthetic-only D161 planning arithmetic; no simulation or model fitting."""
import copy
import inspect
import math

import numpy as np
import pytest

from l20_extension1 import confirmation_plan as p


def fixture():
    rng = np.random.default_rng(16120260920)
    y = rng.uniform(-.4, .7, size=(4, 4, 4, 4))
    names = ('starting', 'one_copy')+tuple(e+':'+c for e in ('separate','mean','tied') for c in p.CONDITIONS)
    pred = {k: rng.uniform(-.4, .7, size=(3, 4, 4, 4)) for k in names}
    return pred, y, np.arange(4, dtype=np.int64)


def test_complete_scalar_check():
    x,y,ids = fixture(); result = p.design(x,y,ids)
    assert p.check_design(result,x,y,ids)['passes']
    assert len(result['comparisons']) == 69
    assert result['new_lineages'] == result['new_fits'] == result['new_forecasts'] == 0


@pytest.mark.parametrize('scores,want', [([1,2,3],0),([3,1,2],1),([3,2,1],2),([1,1,1],2),([1,1+5e-13,3],1)])
def test_alpha_selection(scores,want):
    assert p.choose(scores) == want


@pytest.mark.parametrize('scores', [[1,2], [1,float('nan'),2], [-1,0,1]])
def test_alpha_invalid(scores):
    with pytest.raises(ValueError): p.choose(scores)


def test_primary_exchange_symmetry():
    x,y,ids = fixture(); a = p.design(x,y,ids)
    x[p.PRIMARY[0]], x[p.PRIMARY[1]] = x[p.PRIMARY[1]], x[p.PRIMARY[0]]
    b = p.design(x,y,ids)
    assert a['common_alpha'] == b['common_alpha']
    np.testing.assert_array_equal(a['symmetric_alpha_scores'], b['symmetric_alpha_scores'])


@pytest.mark.parametrize('sd', [0., .0001, .2])
def test_precision_formula(sd):
    assert p.width(sd,64,2) == 2*p.width(sd,64)
    assert math.isclose(p.width(sd,256), p.width(sd,64)/2)
    n = p.required(sd,.006,.0025,1.5)
    assert p.width(sd,n,1.5) <= .006*.0025+1e-16
    if n > 2: assert p.width(sd,n-1,1.5) > .006*.0025-1e-16


@pytest.mark.parametrize('args', [(-1,16,1), (1,1,1), (1,16,.5), (float('nan'),16,1), (1,16,float('inf'))])
def test_invalid_precision(args):
    with pytest.raises(ValueError): p.width(*args)


@pytest.mark.parametrize('args', [(1,0,.1), (1,1,0), (1,float('nan'),.1)])
def test_invalid_required(args):
    with pytest.raises(ValueError): p.required(*args)


def test_mean_control_is_loss_not_ensemble():
    x,y,ids = fixture(); losses = p.losses(x,y)
    ensemble = ((x['tied:sham_plus']+x['tied:sham_minus'])/2)[...,None]
    assert np.max(abs(losses['tied:mean_sham_loss']-(ensemble-y[None,...])**2)) > .01


def test_equal_future_and_mean_target_gain():
    x,y,ids = fixture(); result = p.design(x,y,ids)
    for row in result['comparisons']:
        c,r = row['candidate'],row['reference']
        if 'mean_sham_loss' in c: continue
        a=p.ALPHAS.index(row['alpha']); m=y.mean(-1)
        expected = ((x[r][a]-m)**2-(x[c][a]-m)**2).mean((1,2))
        np.testing.assert_allclose(row['block_gains'],expected,atol=1e-16,rtol=0)


def test_founder_permutation():
    x,y,ids=fixture(); order=[2,0,3,1]
    a=p.design(x,y,ids); b=p.design({k:v[:,order] for k,v in x.items()},y[order],ids[order])
    assert a['common_alpha']==b['common_alpha'] and a['proposed_founders']==b['proposed_founders']
    for u,v in zip(a['comparisons'],b['comparisons']):
        np.testing.assert_allclose(np.array(u['block_gains'])[order],v['block_gains'],atol=1e-16,rtol=0)


def test_repeat_permutation():
    x,y,ids=fixture(); a=p.design(x,y,ids); b=p.design(x,y[...,::-1],ids)
    assert a['common_alpha']==b['common_alpha']
    for u,v in zip(a['comparisons'],b['comparisons']):
        np.testing.assert_allclose(u['block_gains'],v['block_gains'],atol=1e-16,rtol=0)


def test_case_mean_before_founder_sd():
    x,y,ids=fixture(); r=p.design(x,y,ids)['comparisons'][0]
    loss=p.losses(x,y); delta=loss[r['reference']][0]-loss[r['candidate']][0]
    assert math.isclose(r['block_sd'],delta.mean((1,2,3)).std(ddof=1))
    assert not math.isclose(r['block_sd'],delta.std(ddof=1))


@pytest.mark.parametrize('kind',['nan','range','shape','missing','duplicate_ids'])
def test_input_contract(kind):
    x,y,ids=fixture()
    if kind=='nan': y[0,0,0,0]=np.nan
    elif kind=='range': x['starting'][0,0,0,0]=2
    elif kind=='shape': y=y[...,:3]
    elif kind=='missing': x.pop('tied:sham_plus')
    else: ids[:]=1
    with pytest.raises(ValueError): p.design(x,y,ids)


@pytest.mark.parametrize('field',['block_gains','block_sd','widths','common_alpha'])
def test_checker_detects_corruption(field):
    x,y,ids=fixture(); result=p.design(x,y,ids)
    if field=='block_gains': result['comparisons'][0][field][0] += .001
    elif field=='block_sd': result['comparisons'][0][field] += .001
    elif field=='widths': result['comparisons'][0][field][0]['absolute'] += .001
    else: result[field]=42
    with pytest.raises(AssertionError): p.check_design(result,x,y,ids)


def test_resource_accounting():
    t=[dict(status='COMPLETE',checked_block_seconds=100,uncompressed_block_bytes=1000),
       dict(status='COMPLETE',checked_block_seconds=80,uncompressed_block_bytes=400),
       dict(status='COMPLETE',checked_block_seconds=20,block_proof=dict(uncompressed_bytes=200))]
    r=p.resource_projection(t,128)
    assert r['historical_serial_block_seconds']==180
    assert r['projected_bytes']==2*128*1500+512*1024**2
    assert r['primary_future_outcomes']==8192 and r['diagnostic_cycles']==12288
    assert r['must_detach'] and not r['parallel_speedup_assumed']


def test_no_fits_or_dynamics_or_launch():
    source=inspect.getsource(p)
    for banned in ('.fit(', '.simulate_', '.generate_founders(', 'subprocess', 'ProcessPoolExecutor', 'Popen'):
        assert banned not in source


def test_no_source_mutation():
    x,y,ids=fixture(); original=copy.deepcopy((x,y,ids)); p.design(x,y,ids)
    for k in x: np.testing.assert_array_equal(x[k],original[0][k])
    np.testing.assert_array_equal(y,original[1]); np.testing.assert_array_equal(ids,original[2])
