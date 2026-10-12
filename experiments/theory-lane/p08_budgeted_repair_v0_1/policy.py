"""Online scheduling: incoming record, quota and clock only; no outcomes."""
import time
import numpy as np
from reader import stream
import warning


def select(incoming,spent,block,generation,cfg,model):
    assert incoming.shape==(4,16,4096) and spent.shape==(4,16)
    before=np.array(cfg['repair_budgets'])[:,None]-spent
    assert (before>=0).all()
    applied=np.zeros((4,16),bool);remaining_steps=33-generation
    detail=dict(quota_before=before.copy(),warning_features=np.zeros((16,6)),warning_risk=np.zeros(16),
        warning_percentile=np.zeros(16),warning_tie_uniform=np.zeros(16),warning_reason=np.ones(16,int),
        diagnostic_cpu_seconds=np.zeros((4,16)),warning_feature_valid=np.full(16,generation>15,bool))
    if generation==15:
        assert not spent.any();applied[:]=True
    else:
        t=time.process_time()
        x=warning.features(incoming[0]);risk=warning.predict(model['model'],x)
        calibration=np.array(model['calibration_sorted_scores'])
        ties=np.array([stream(cfg['policy_namespace'],block,'tie',case,generation).random() for case in range(16)])
        left=np.searchsorted(calibration,risk,side='left');right=np.searchsorted(calibration,risk,side='right')
        percentile=(left+ties*(right-left))/len(calibration)
        decision=percentile>=1-before[0]/remaining_steps
        decision=np.where(before[0]==remaining_steps,True,np.where(before[0]==0,False,decision))
        applied[0]=decision
        detail.update(warning_features=x,warning_risk=risk,warning_percentile=percentile,warning_tie_uniform=ties,
            warning_reason=np.where(before[0]==0,4,np.where(before[0]==remaining_steps,2,3)))
        detail['diagnostic_cpu_seconds'][0]=(time.process_time()-t)/16
        applied[1]=(generation-15)%2==0
        for case in range(16):
            schedule=stream(cfg['policy_namespace'],block,'random_schedule',case).choice(np.arange(16,33),8,replace=False)
            applied[2,case]=generation in schedule
        applied[3]=True
    assert (applied<=before).all()
    return applied,detail
