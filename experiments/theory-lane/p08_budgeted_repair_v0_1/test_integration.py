"""Short artificial dynamics exercise the full policy/audit interface, not the fresh cohort."""
import copy
import numpy as np
import pytest
from common import ROOT,read
import lineage_dynamics as dynamics
from serial import continue_block
from audit_serial import audit_block


def test_full_policy_to_independent_audit_and_capture_corruption():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    cfg['continuation_namespace']='P08_synthetic_integration_only'
    cfg['innovation_namespace']='P08_synthetic_integration_noise_only'
    cfg['policy_namespace']='P08_synthetic_integration_policy_only'
    cfg['history_by_block']={'0':0}
    model=read(ROOT/'development/MODEL.json')
    w=np.ones((16,2,16,16));w[:,0,0,0]=0
    initial=dynamics.encode(w);previous=np.zeros((16,16,16),bool)
    d=continue_block(initial,previous,0,cfg,model)
    result=audit_block(d,initial,previous,0,cfg,model)
    assert result['new_independent_optimizer_checks']==720
    assert result['independent_captures']==1152
    d['outgoing'][-1,2,5,17]^=1
    with pytest.raises(AssertionError):audit_block(d,initial,previous,0,cfg,model)
