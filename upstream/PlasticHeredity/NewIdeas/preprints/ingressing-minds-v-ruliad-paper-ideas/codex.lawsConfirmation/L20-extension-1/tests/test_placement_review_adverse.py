"""Supplemental pre-main branch coverage; frozen review science unchanged."""
import copy
import numpy as np
import pytest
from l20_extension1 import placement_review as p,placement_review_check as c,placement_review_run as run


@pytest.fixture(scope='module')
def adverse():
    raw=run.raw_block(run.DISPOSABLE)
    ci=p.CASES.index((1,1000,1000,'intact'))
    # Synthetic, saved-state-only input; no physics call or source-file edit.
    raw['terminal_states'][0,0,ci,1,-1,0]=0
    raw['terminal_values'][0,0,ci,1,-1,0]=0
    value=p.extract(raw);c.check_block(value,raw)
    original=run.original();summary=p.summarize([value]*16,original,(run.DISPOSABLE,)*16,True)
    c.check_summary(summary,[value]*16,original,(run.DISPOSABLE,)*16,True)
    assert len(summary['adverse_intact'])==16
    return value,original,summary


def test_adverse_zero_is_retained(adverse):
    _,_,summary=adverse
    for r in summary['adverse_intact']:
        assert (r['index'],r['life'],r['noise'],r['role'],r['generation'])==(run.DISPOSABLE,0,0,1,2)
        assert r['preferences'][0]==0
        assert np.shape(r['fields'])==(4,4,3,15)
        assert np.shape(r['counts'])==(4,4,3)
        assert np.shape(r['records'])==(4,2,15)
        assert np.shape(r['transitions'])==(5,4,3,3)


@pytest.mark.parametrize('key',['preferences','counts','fields','records','transitions'])
def test_adverse_corruption(adverse,key):
    value,original,summary=adverse;changed=copy.deepcopy(summary)
    a=np.array(changed['adverse_intact'][0][key]);a.flat[-1]+=1
    changed['adverse_intact'][0][key]=a.tolist()
    with pytest.raises(AssertionError):c.check_summary(changed,[value]*16,original,(run.DISPOSABLE,)*16,True)


@pytest.mark.parametrize('operation',['drop','duplicate','wrong_identity'])
def test_adverse_inventory(adverse,operation):
    value,original,summary=adverse;changed=copy.deepcopy(summary)
    if operation=='drop':changed['adverse_intact'].pop()
    elif operation=='duplicate':changed['adverse_intact'].append(changed['adverse_intact'][0])
    else:changed['adverse_intact'][0]['life']=3
    with pytest.raises(AssertionError):c.check_summary(changed,[value]*16,original,(run.DISPOSABLE,)*16,True)
