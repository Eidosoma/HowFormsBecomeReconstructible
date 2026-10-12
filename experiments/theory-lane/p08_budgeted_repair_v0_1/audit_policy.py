"""Audit quotas and all online decisions without importing the policy module."""
import hashlib
import json
import numpy as np
import audit_warning
from common import equal


def random(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def audit_policy(d,block,cfg,model):
    remaining=np.repeat(np.array([9,9,9,18])[:,None],16,axis=1)
    scheduled=[set(random([cfg['policy_namespace'],block,'random_schedule',case]).choice(np.arange(16,33),8,replace=False).tolist())|{15} for case in range(16)]
    calibration=np.array(model['calibration_sorted_scores'])
    for gi,g in enumerate(cfg['generations']):
        equal(remaining,d['quota_before'][gi],'remaining budgets before current read')
        valid=np.full(16,g>15,bool);equal(valid,d['warning_feature_valid'][gi],'warning feature timing')
        if g>15:
            features=audit_warning.features(d['incoming'][gi,0])
            np.testing.assert_allclose(features,d['warning_features'][gi],rtol=2e-13,atol=2e-15)
            risk=audit_warning.risk(model['model'],features)
            np.testing.assert_allclose(risk,d['warning_risk'][gi],rtol=2e-12,atol=1e-14)
        else:
            for k in ('warning_features','warning_risk','warning_percentile','warning_tie_uniform'):
                assert not d[k][gi].any(),k
        for case in range(16):
            if g==15:warning=True;reason=1
            else:
                u=float(random([cfg['policy_namespace'],block,'tie',case,g]).random())
                assert u==d['warning_tie_uniform'][gi,case]
                # Stored floating-point risk is independently verified above; threshold counts are exact.
                score=d['warning_risk'][gi,case]
                less=np.count_nonzero(calibration<score);same=np.count_nonzero(calibration==score)
                percentile=(less+u*same)/len(calibration)
                assert percentile==d['warning_percentile'][gi,case]
                quota=int(remaining[0,case]);steps=33-g
                reason=4 if quota==0 else 2 if quota==steps else 3
                warning=False if quota==0 else True if quota==steps else percentile>=1-quota/steps
            assert d['warning_reason'][gi,case]==reason
            expected=[warning,g in range(15,33,2),g in scheduled[case],True]
            assert d['applied'][gi,:,case].tolist()==expected
        assert (d['diagnostic_cpu_seconds'][gi]>=0).all()
        assert not d['diagnostic_cpu_seconds'][gi,1:].any()
        if g==15:assert not d['diagnostic_cpu_seconds'][gi].any()
        remaining-=d['applied'][gi]
        assert (remaining>=0).all() and (remaining<=32-g).all()
    assert not remaining.any()
