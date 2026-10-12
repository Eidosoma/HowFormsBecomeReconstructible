"""D118 synthetic algebra/source-graph tests; no experiment trajectories."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('d118_audit',Path(__file__).resolve().parents[1]/'scripts/audit_l20_reference_projection.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def target_pair():
    y,x=np.indices((16,16)); return np.stack([np.where(y<8,1.,-1.),np.where((x//4)%2==0,1.,-1.)])


def fixture(kind='rewrite'):
    random=np.random.default_rng(7118); targets=target_pair()
    birth=random.normal(0,.2,(4,16,16)); read=random.normal(0,.3,(4,16,16)); read[2]+=.4*targets[0]
    wb=read.copy(); wb[3]=m.projection(read[3])[0] if kind in ('copy','live') else np.zeros((16,16)); read[3]=wb[3]
    first=wb.copy(); first[0]=.8*targets[0]+random.normal(0,.1,(16,16))
    first[2]=wb[2]+.002*(first[0]-wb[2])
    first[3]=m.projection(.999*wb[3]+.001*np.tanh(first[2]))[0] if kind not in ('copy','write_off') else wb[3]
    return [birth,read,wb,first,first.copy(),targets,0,kind]


@pytest.mark.parametrize('seed',range(4))
def test_projection_matches_source(seed):
    x=np.random.default_rng(seed).normal(size=(16,16)); expected=m.prior.p.api()['original'].project_theta(x,.3)
    np.testing.assert_array_equal(m.projection(x)[0],expected)


@pytest.mark.parametrize('scale',(1e-7,.001,.1,2.))
def test_scale_invariance(scale):
    x=np.tanh(np.random.default_rng(0).normal(size=(16,16)))
    np.testing.assert_allclose(m.projection(scale*x)[0],m.projection(x)[0],rtol=0,atol=1e-14)


def test_floor_not_invariant():
    x=np.random.default_rng(0).normal(size=(16,16)); tiny=m.projection(1e-12*x)[0]
    assert tiny.std()<.001 and not np.allclose(tiny,m.projection(x)[0])
    np.testing.assert_array_equal(m.projection(np.ones((16,16)))[0],np.zeros((16,16)))


def test_nonzero_theta_rate_matters():
    a,b=target_pair(); theta=m.projection(a)[0]
    x=m.projection(.999*theta+.001*np.tanh(b))[0]
    y=m.projection(.9*theta+.1*np.tanh(b))[0]
    assert np.max(abs(x-y))>.01


def test_projection_permutation():
    r=np.random.default_rng(1); x=r.normal(size=(16,16)); perm=r.permutation(256)
    a=m.projection(x)[0].ravel()[perm]; b=m.projection(x.ravel()[perm].reshape(16,16))[0].ravel()
    np.testing.assert_allclose(a,b,atol=1e-14,rtol=0)
    np.testing.assert_array_equal(np.argsort(x.ravel()),np.argsort(m.projection(x)[0].ravel()))


def test_passive_ema_source_graph():
    result=m.passive_ema_check()
    assert result['passive_for_active_path'] and len(result['source_rows'])==3 and result['ablation_rollouts']==0


@pytest.mark.parametrize('kind',m.KINDS)
def test_reference_accounting(kind):
    args=fixture(kind); row=m.transition(*args)
    assert row['reference_error']==row['theta_error']==0.
    assert row['writing']==(kind not in ('copy','write_off'))
    assert row['erased']==(kind not in ('copy','live'))
    expected=m.score(args[1][2],args[-3],0)[2]
    assert abs(row['retained_birth_target_margin']+row['read_body_history_target_margin']-expected)<1e-14
    if kind not in ('copy','write_off'): assert row['rank_preserved'] and not row['projection_floor_active']


@pytest.mark.parametrize('which,field',((2,3),(2,0),(3,2),(3,3)))
def test_transition_corruption(which,field):
    args=fixture(); args[which][field,0,0]+=.1
    with pytest.raises(AssertionError): m.transition(*args)


def test_body_not_causal_fraction():
    args=fixture(); row=m.transition(*args)
    expected=(.002*args[3][0]).std()/(.998*args[2][2]).std()
    assert row['new_V_to_old_R_std_ratio']==expected
    assert .54<row['birth_reference_coefficient']<.56
    assert 'causal_fraction' not in row


def test_no_production_dynamics(monkeypatch):
    bad=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('no dynamics'))
    api=m.prior.p.api(); monkeypatch.setattr(api['original'],'cascade_step',bad)
    monkeypatch.setattr(m.prior.p,'descendant',bad)
    assert m.transition(*fixture())['theta_error']==0


@pytest.mark.parametrize('bad',(np.zeros((2,2)),np.zeros((16,16),np.float32),np.full((16,16),np.nan)))
def test_invalid_field(bad):
    with pytest.raises(ValueError): m.projection(bad)
