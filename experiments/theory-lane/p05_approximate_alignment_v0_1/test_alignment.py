import copy
import itertools
import numpy as np
from common import ROOT,read
from optimizer import influence,align,complete,solve,cost
from reader import PORTS,available,stream,read_fixed
from prepare import solve_records
import audit_optimizer
import audit_reader

OPTIONS=read(ROOT/'config.json')['optimizer']


def test_tiny_weights_preserve_normalized_influence():
    for magnitude in (1.,1e-100,1e-320):
        w=np.full((2,16,16),magnitude)
        assert np.array_equal(influence(w),np.full_like(w,.25))
    assert not influence(np.zeros((2,16,16))).any()


def test_known_balanced_alignment_is_recovered():
    rng=np.random.default_rng(3902);g=1-2*rng.integers(0,2,(16,16));g[PORTS.any(axis=0)]=1
    o=rng.uniform(.1,1,(2,16,16))
    d=o*np.stack((g*np.roll(g,-1,1),g*np.roll(g,-1,0)))
    answer=align(o,d,OPTIONS)
    assert answer['cost']==0 and np.array_equal(answer['signs'],g)


def test_frustrated_square_matches_enumerated_optimum():
    j=np.zeros((2,16,16));j.flat[[0,16,256,257]]=[1.,1.,1.,-.1]
    answer=solve(j,[0],OPTIONS)
    options=[]
    for bits in itertools.product((-1,1),repeat=3):
        g=np.ones((16,16),np.int8);g.flat[[1,16,17]]=bits;options.append(cost(g,j))
    assert answer['cost']==min(options)==.1


def test_zero_problem_has_deterministic_ties():
    answer=solve(np.zeros((2,16,16)),[0,3],OPTIONS)
    assert answer['winner']==0 and answer['sweeps']==1 and answer['cost']==0
    assert np.all(answer['signs']==1)


def test_bounded_search_and_independent_solver():
    options=dict(OPTIONS,maximum_sweeps=1)
    rng=np.random.default_rng(8394);j=rng.uniform(-1,1,(2,16,16))
    a=solve(j,[0,31,48],options);b=audit_optimizer.solve(j,[0,31,48],options)
    assert a['sweeps']==b['sweeps']==1 and a['cost']<=a['initial_cost']
    for key in ('signs','candidate_costs','final_improvable_nodes'):assert np.array_equal(a[key],b[key])


def test_independent_preparation_with_missing_donor_edges():
    rng=np.random.default_rng(3243);o=rng.uniform(-1,1,(2,16,16));d=rng.uniform(-1,1,(2,2,16,16))
    mask=np.zeros((16,16),bool);mask[5:7,5:7]=True;o*=available(mask)
    d[0,:,8:10,:]=0;d[1,:,2:4,:]=0
    result=solve_records(o,d,OPTIONS)
    assert len(result)==3
    assert all(x['cost']<=x['initial_cost'] for x in result)


def test_alignment_ignores_unobserved_signs_and_donor_magnitude():
    rng=np.random.default_rng(90213);o=rng.uniform(-1,1,(2,16,16));o[:,:,2:4]=0
    d=rng.choice([-1.,1.],(2,16,16));a=align(o,d,OPTIONS)
    changed=d*rng.uniform(.01,10,d.shape);changed[o==0]*=-1
    b=align(o,changed,OPTIONS)
    assert np.array_equal(a['signs'],b['signs']) and np.array_equal(a['candidate_costs'],b['candidate_costs'])
    import inspect
    assert list(inspect.signature(align).parameters)==['outgoing','donor','options']
    assert list(inspect.signature(complete).parameters)==['outgoing','options']


def test_native_reader_flat_agreement_and_ordering():
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['budgets']=[40];cfg['settling_steps']=20
    rng=np.random.default_rng(5304);weights=rng.uniform(-1,1,(3,2,16,16));weights[2]=0
    packets=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(1,3,4096)
    mask=np.zeros((1,16,16),bool);mask[0,5:7,5:7]=True
    raw=read_fixed(packets,mask,np.array([0]),np.array([1]),[stream(cfg['random_namespace'],34000,'read',0)],cfg['reader'],[40],20)
    other=audit_reader.replay(packets[0],mask[0],0,1,34000,0,cfg)
    assert np.array_equal(raw['end'][:,0,:,0],other['end'])
    assert np.array_equal(raw['port_windows'][:,:,0,:,0],other['port_windows'])
    order=[2,0,1]
    reordered=read_fixed(packets[:,order],mask,np.array([0]),np.array([1]),[stream(cfg['random_namespace'],34000,'read',0)],cfg['reader'],[40],20)
    assert np.array_equal(reordered['end'],raw['end'][:,:,order])
    assert np.array_equal(raw['mean_ports'][0,0,2,0,0],raw['mean_ports'][0,0,2,0,1])
