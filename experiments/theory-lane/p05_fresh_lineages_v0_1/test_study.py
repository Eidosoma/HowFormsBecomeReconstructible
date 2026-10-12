"""Acquisition, fixed construction, stratification and failed-report fixtures."""
import copy
import json
import numpy as np
import pytest
import acquire
import audit_acquire
from audit_cohort import check_records
from common import ROOT,read,arrays,equal,save_arrays,write
from cohort import construct
from reader import decode,PORTS
from analyze import summary,analyze,render
from verify import check_summary,verify


def test_independent_teaching_with_nontrivial_short_capture():
    cfg=copy.deepcopy(read(ROOT/'config.json')['development_config']);cfg.update(teach_steps=24,capture_steps=8)
    a=acquire.teach('test_only_teaching',cfg);b=audit_acquire.teach('test_only_teaching',cfg)
    for k,value in a.items():equal(value,b[k],k)
    assert np.any(a['weights']<0) and np.any(a['weights']>0)


def test_frozen_repair_and_independent_record_reconstruction():
    cfg=read(ROOT/'config.json');known=arrays(ROOT/'known/native_controls.npz')
    d=construct(decode(known['outgoing'].reshape(16,4096)),cfg['blocks'][0],cfg)
    check_records(d,cfg['blocks'][0],cfg)
    assert np.all(d['missing_edge_counts']>0)
    changed=d['packets'].copy();changed[0,1,11]^=1;d['packets']=changed
    with pytest.raises(AssertionError):check_records(d,cfg['blocks'][0],cfg)


def test_history_stratification_preserves_fixed_mixture():
    cfg=read(ROOT/'config.json');values=np.tile([.0,.25,.5,.75],4)
    s=summary(values,cfg);assert s['mean']==.375
    assert s['descriptive_stratified_block_bootstrap_95']==[.375,.375]
    check_summary(s,values,cfg)
    s['descriptive_stratified_block_bootstrap_95']=[0.,1.]
    with pytest.raises(AssertionError):check_summary(s,values,cfg)


def test_artificial_failed_primary_empty_subgroup_and_tamper(tmp_path):
    cfg=read(ROOT/'config.json')
    # Artificial graph, never a scientific new lineage. A zero edge is repaired.
    outgoing=np.ones((16,2,16,16));outgoing[:,0,0,0]=0.
    for bi,b in enumerate(cfg['blocks']):
        d=construct(outgoing,b,cfg,independent=False);d['pre_repair_pass']=np.ones(16,bool)
        mu=np.zeros((16,4,8,2,2))
        for case in range(16):
            rule=1 if case//4%2==0 else -1
            for vi in range(3):
                for rep in range(8):
                    good=(case+rep+bi)%4<[3,1,2][vi]
                    opposite=(not good) and (case+rep+vi)%7==0
                    mu[case,vi,rep]=(.5 if good else -.5 if opposite else 0.)*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(mu[None],32,axis=0);mu=windows.mean(axis=0)
        end=np.zeros((16,4,8,2,16,16));end[...,PORTS[0]]=np.array([1.,-1.]).reshape(1,1,1,2,1)
        for port in (1,2):end[...,PORTS[port]]=mu[...,port-1,None]
        aligned=mu*np.repeat([1.,-1.,1.,-1.],4)[:,None,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
        margin=aligned.min(axis=(-2,-1));om=-aligned.max(axis=(-2,-1))
        d.update(birth=np.zeros((16,8,2,16,16)),end=end,port_windows=windows,mean_ports=mu,min_margin=margin,
            opposite_margin=om,both_pass=margin>.25,opposite_pass=om>.25)
        digest=save_arrays(tmp_path/f'reads_{b:06d}.npz',d)
        write(tmp_path/f'worker_{b:06d}.json',dict(status='COMPLETE',fixture_only=True,reads_sha256=digest))
    a=analyze(tmp_path,cfg)
    assert a['contrasts']['completion_minus_outgoing']['mean']==-.5 and not a['primary_direction_observed']
    assert a['body_subgroups']['body_fail']['records']==0 and a['body_subgroups']['body_fail']['rates']['outgoing'] is None
    assert a['rates']['recipient_completion']['opposite']['successes']>0
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    render(tmp_path,cfg);assert 'The primary directional forecast failed.' in (tmp_path/'REPORT.md').read_text()
    a['primary_direction_observed']=True;(tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
    a['primary_direction_observed']=False;(tmp_path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
