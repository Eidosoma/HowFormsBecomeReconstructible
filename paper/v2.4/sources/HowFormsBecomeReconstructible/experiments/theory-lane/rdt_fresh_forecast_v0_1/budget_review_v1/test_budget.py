import math
import pytest
from budget_audit import cost,waves,completion_sum,completion_recursion,eligible_blocks,read,ROOT


def test_production_future_queue_uses54_waves():
    assert waves([(b,r) for b in range(108) for r in range(4)],8)==54
    assert math.ceil(108/8)*4==56
    assert waves(list(range(108)),8)==14
    assert waves(list(range(192)),8)==24


@pytest.mark.parametrize('n,k,p',[(192,108,.5),(192,108,.6),(192,108,.7),(216,108,.6),(10,4,0.),(10,4,1.)])
def test_binomial_tail_independent_recursion(n,k,p):
    assert completion_sum(n,k,p)==pytest.approx(completion_recursion(n,k,p),abs=2e-13)


def test_attempt_cap_preserves_positive_runtime_reserve():
    phase=read(ROOT/'inputs/TIMINGS.json')['conservative_retained_maxima_seconds']
    a=cost(192,108,4,8,phase);b=cost(200,108,4,8,phase);c=cost(216,108,4,8,phase)
    assert a['spare_within_six_hours_seconds']>300
    assert 0<b['spare_within_six_hours_seconds']<30
    assert c['forecast_seconds']>21600
    with pytest.raises(AssertionError):cost(193,108,4,8,phase)


def test_fixed_pilot_has_all1024_boundary_records():
    p=read(ROOT/'inputs/PRECISION_PROTOCOL.json');e=read(ROOT/'inputs/PRECISION_ENROLLMENT.json')
    assert eligible_blocks(p,e)['eligible_blocks']==16
    e['records'].pop()
    with pytest.raises(AssertionError):eligible_blocks(p,e)
