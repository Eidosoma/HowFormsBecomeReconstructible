"""Known reconstruction, information limits, numerical behavior and native checks."""
import copy
import inspect
import numpy as np
import pytest
import audit_reader
import audit_repair
from common import ROOT,read,equal
from reader import PORTS,available,read_fixed,stream
from repair import recipient_repair,reference_records,imputed_magnitude
from prepare import checked_repair

OPTIONS=dict(starts=16,maximum_sweeps=64,seed=2026101004)


def test_connected_balanced_record_recovers_a_missing_edge():
    rng=np.random.default_rng(8921)
    signs=1-2*rng.integers(0,2,(16,16));signs[PORTS[0]]=1
    original=np.stack((signs*np.roll(signs,-1,1),signs*np.roll(signs,-1,0))).astype(float)
    outgoing=original.copy();outgoing[0,5,5]=0.
    repaired,result,magnitude=checked_repair(outgoing,OPTIONS)
    equal(repaired,original,'known balanced reconstruction')
    assert magnitude==1 and result['cost']==0


def test_erasure_does_not_recover_unknown_history():
    zero=np.zeros((2,16,16));repaired,solution,m=recipient_repair(zero,OPTIONS)
    equal(repaired,zero);assert m==0
    assert list(inspect.signature(recipient_repair).parameters)==['outgoing','options']
    mask=np.zeros((16,16),bool);mask[4:6,5:7]=True
    common=~available(mask);different=[]
    for history in (-1.,1.):
        incoming=np.full_like(zero,history)
        rows,_,_=reference_records(zero,incoming,common,common,solution,m,repaired,stream('synthetic',12))
        equal(rows[6],zero);equal(rows[7],zero)
        different.append(rows[3])
    assert not np.array_equal(*different)


def test_scale_behavior_and_tiny_observed_magnitudes():
    tiny=np.zeros((2,16,16));tiny.flat[:4]=[1e-300,-2e-300,9e-300,-10e-300]
    assert imputed_magnitude(tiny)==np.median([1e-300,2e-300,9e-300,10e-300])
    rng=np.random.default_rng(8943);outgoing=rng.uniform(-1,1,(2,16,16));outgoing[:,:,3:5]=0.
    a,sa,ma=recipient_repair(outgoing,OPTIONS);b,sb,mb=recipient_repair(outgoing*1024,OPTIONS)
    equal(sa['signs'],sb['signs']);equal(b,a*1024);assert mb==ma*1024
    equal(a[outgoing!=0],outgoing[outgoing!=0],'preserve observed weights')


def test_reference_controls_and_hidden_history_invariance():
    rng=np.random.default_rng(340014);incoming=rng.uniform(-1,1,(2,16,16))
    mask=np.zeros((16,16),bool);mask[4:6,5:7]=True
    outgoing=incoming*available(mask);outgoing[0,0,0]=0.
    unavailable=~available(mask);common=unavailable.copy();common[0]=False
    recipient,solution,magnitude=checked_repair(outgoing,OPTIONS)
    parts=['synthetic_controls',0,'shuffle',0,0,0]
    first=None
    for factor in (1.,-2.):
        historical=incoming*factor
        rows,_,_=reference_records(outgoing,historical,common,unavailable,solution,magnitude,recipient,stream(*parts))
        _,_,outside=audit_repair.check_case(rows,outgoing,historical,common,mask,solution['signs'],parts)
        assert outside==1
        assert rows[6,0,0,0]!=0 and rows[5,0,0,0]==0
        if first is not None:
            equal(rows[6],first[6]);equal(rows[7],first[7]);assert not np.array_equal(rows[4],first[4])
        first=rows.copy()
        rows[6,0,0,0]*=-1
        with pytest.raises(AssertionError):audit_repair.check_case(rows,outgoing,historical,common,mask,solution['signs'],parts)


def test_native_reader_flat_agreement_and_ordering():
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['budgets']=[40];cfg['settling_steps']=20
    rng=np.random.default_rng(5304);weights=rng.uniform(-1,1,(3,2,16,16));weights[2]=0
    packets=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(1,3,4096)
    mask=np.zeros((1,16,16),bool);mask[0,5:7,5:7]=True
    raw=read_fixed(packets,mask,np.array([0]),np.array([1]),[stream(cfg['random_namespace'],34000,'read',0)],cfg['reader'],[40],20)
    other=audit_reader.replay(packets[0],mask[0],0,1,34000,0,cfg)
    equal(raw['end'][:,0,:,0],other['end']);equal(raw['port_windows'][:,:,0,:,0],other['port_windows'])
    order=[2,0,1]
    reordered=read_fixed(packets[:,order],mask,np.array([0]),np.array([1]),[stream(cfg['random_namespace'],34000,'read',0)],cfg['reader'],[40],20)
    equal(reordered['end'],raw['end'][:,:,order])
    equal(raw['mean_ports'][0,0,2,0,0],raw['mean_ports'][0,0,2,0,1])
