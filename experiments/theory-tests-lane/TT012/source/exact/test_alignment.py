import itertools
import numpy as np
import pytest
from alignment import align, ambiguity, grid_edges, hybrid, parity
from gf2 import ambiguity_rank, constraint_rows, eliminate


def test_cycle_and_port_obstructions():
    u = np.array([0,1,2]); v = np.array([1,2,0])
    assert parity(3,u,v,[0,1,1])['ok']
    assert not parity(3,u,v,[0,1,0])['ok']
    result = parity(3,u,v,[0,1,1],[0,2])
    assert not result['ok'] and result['witness']


def test_isolated_damage_has_harmless_freedom():
    u = np.array([0,1,2]); v = np.array([1,2,0])
    keep = np.array([1,0,0],bool); backup = ~keep
    solved = parity(3,u[keep],v[keep],[0],[0,1])
    assert len(solved['free_components']) == 1
    assert ambiguity(3,u,v,keep,backup,solved,[0,1])['dimension'] == 0
    assert ambiguity_rank(3,u,v,keep,backup,keep,[0,1]) == 0


def test_missing_overlap_can_create_real_ambiguity():
    # No donor edge on the kept 0--1 edge. Flipping node 1 changes the backup
    # 1--2 edge's port-to-port parity, which cannot be gauged away with 0,2 fixed.
    u = np.array([0,1]); v = np.array([1,2])
    keep = np.array([1,0],bool); backup = ~keep
    overlap = np.array([0,0],bool)
    solved = parity(3,u[overlap],v[overlap],[],[0,2])
    assert ambiguity(3,u,v,keep,backup,solved,[0,2])['dimension'] == 1
    assert ambiguity_rank(3,u,v,keep,backup,overlap,[0,2]) == 1


def test_small_graph_solvers_against_enumeration():
    rng = np.random.default_rng(19171)
    checked = 0
    for n in range(1,7):
        all_edges = list(itertools.combinations(range(n),2))
        for _ in range(80):
            selected = [edge for edge in all_edges if rng.random()<.55]
            u = np.array([a for a,b in selected],int); v = np.array([b for a,b in selected],int)
            rhs = rng.integers(0,2,len(selected)); pins = np.flatnonzero(rng.random(n)<.35)
            brute = [np.array(x) for x in itertools.product((0,1),repeat=n)
                     if all(x[p]==0 for p in pins) and all((x[a]^x[b])==r for a,b,r in zip(u,v,rhs))]
            forest = parity(n,u,v,rhs,pins)
            elimination = eliminate(n,constraint_rows(u,v,pins),list(rhs)+[0]*len(pins))
            assert forest['ok'] == elimination['ok'] == bool(brute)
            assert forest['rank'] == elimination['rank']
            if brute:
                assert len(brute) == 2**len(forest['free_components'])
                assert any(np.array_equal(x,forest['bits']) for x in brute)
            checked += 1
    assert checked == 480


def test_random_ambiguity_ranks():
    rng = np.random.default_rng(839201)
    for n in range(2,8):
        u,v = np.array(list(itertools.combinations(range(n),2))).T
        for _ in range(30):
            role = rng.integers(0,3,len(u))
            keep,backup = role==1,role==2
            overlap = keep & (rng.random(len(u))<.7)
            pins = np.flatnonzero(rng.random(n)<.4)
            solved = parity(n,u[overlap],v[overlap],np.zeros(overlap.sum(),int),pins)
            a = ambiguity(n,u,v,keep,backup,solved,pins)['dimension']
            b = ambiguity_rank(n,u,v,keep,backup,overlap,pins)
            assert a == b


def test_alignment_api_does_not_accept_hidden_backup_signs():
    import inspect
    assert list(inspect.signature(align).parameters) == ['outgoing','donor','pins']
    rng = np.random.default_rng(2142)
    outgoing = rng.choice([-1.,1.],(2,16,16))
    outgoing[:,4:6,:] = 0
    donor = outgoing.copy(); donor[outgoing==0] = 1
    before = align(outgoing,donor,[0])['pinned']
    common = outgoing==0
    for _ in range(10):
        hidden = rng.choice([-1.,1.],outgoing.shape)
        hybrid(outgoing,donor,common,abs(hidden),before['bits'])
        after = align(outgoing,donor,[0])['pinned']
        assert np.array_equal(before['bits'],after['bits'])


def test_periodic_edges_match_array_convention():
    u,v = grid_edges(); nodes = np.arange(256).reshape(16,16)
    assert np.array_equal(nodes.ravel()[v[:256]].reshape(16,16),np.roll(nodes,-1,1))
    assert np.array_equal(nodes.ravel()[v[256:]].reshape(16,16),np.roll(nodes,-1,0))
