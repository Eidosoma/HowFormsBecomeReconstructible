"""Artificial outcomes exercise the full report, failure logic and verification."""
import json
import numpy as np
import pytest
from common import ROOT,arrays,read,save_arrays,write
from reader import PORTS
from analyze import analyze,render
from verify import verify


def test_artificial_failed_forecast_and_full_reporting(tmp_path):
    cfg=read(ROOT/'config.json')
    for bi,block in enumerate(cfg['blocks']):
        d=arrays(ROOT/'prepared'/f'cases_{block:06d}.npz');n=len(d['founders'])
        raw={}
        for prefix,reps in (('',cfg['replicates']),('control_',[0])):
            mu=np.zeros((n,9,len(reps),2,2))
            for case in range(n):
                rule=1 if d['founders'][case]%2==0 else -1
                for vi in range(8):
                    for ri,rep in enumerate(reps):
                        choice=1 if prefix and vi>=1 else vi
                        mod=(case+rep+bi)%4
                        good=mod<({0:3,1:1,2:3,3:3,4:2,5:1,6:1,7:3}[choice])
                        opposite=(not good) and (case+rep+choice+bi)%11==0
                        value=.5 if good else -.5 if opposite else 0.
                        mu[case,vi,ri]=value*rule*np.array([[1.,-1.],[-1.,1.]])
            windows=np.repeat(mu[None],32,axis=0)
            mu=windows.mean(axis=0)
            end=np.zeros((n,9,len(reps),2,16,16))
            end[...,PORTS[0]]=np.array([1.,-1.]).reshape(1,1,1,2,1)
            for p in (1,2):end[...,PORTS[p]]=mu[...,p-1,None]
            aligned=mu*np.where(d['founders']%2==0,1.,-1.)[:,None,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
            margin=aligned.min(axis=(-2,-1));opposite=-aligned.max(axis=(-2,-1))
            raw.update({prefix+k:v for k,v in dict(birth=np.repeat(d['original_birth'][:,None],len(reps),axis=1),
                port_windows=windows,mean_ports=mu,end=end,min_margin=margin,opposite_margin=opposite,
                both_pass=margin>.25,opposite_pass=opposite>.25).items()})
        raw['budgets']=np.array(cfg['budgets'])
        digest=save_arrays(tmp_path/f'reads_{block:06d}.npz',dict(**d,**raw))
        write(tmp_path/f'worker_{block:06d}.json',dict(status='COMPLETE',fixture_only=True,
            original_native_replay_byte_equal=True,output_sha256=digest))
    a=analyze(tmp_path,cfg)
    assert a['intended_effects']['mean_alignment_effect']['mean']<0
    assert not a['primary_direction_observed']
    assert a['rate_summaries']['fresh']['same_unaligned']['opposite']['successes']>0
    checked=verify(tmp_path,cfg,check_sources=False,check_dynamics=False)
    assert checked['status']=='PASS' and checked['native_audit_contexts']==0
    render(tmp_path,cfg)
    report=(tmp_path/'REPORT.md').read_text()
    assert 'The primary directional forecast failed.' in report and 'completion' in report
    a['primary_direction_observed']=True
    (tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,check_sources=False,check_dynamics=False)
    a['primary_direction_observed']=False
    (tmp_path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
