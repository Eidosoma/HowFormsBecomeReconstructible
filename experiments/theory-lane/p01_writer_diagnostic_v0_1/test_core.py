import numpy as np
import core


def dense(weights):
    side = weights.shape[-1]
    matrix = np.zeros((side*side, side*side))
    for y in range(side):
        for x in range(side):
            i = y*side+x
            for plane, yy, xx in [(0, y, (x+1)%side), (1, (y+1)%side, x)]:
                j = yy*side+xx
                matrix[i,j] = matrix[j,i] = weights[plane,y,x]
    den = np.abs(matrix).sum(axis=1)
    return np.divide(matrix, den[:,None], out=np.zeros_like(matrix), where=den[:,None]>0)


def test_reader_matches_explicit_graph():
    rng = np.random.default_rng(29)
    for _ in range(12):
        w = rng.normal(size=(2,4,4))
        w[rng.random(w.shape)<.25] = 0
        value = rng.normal(size=(4,4))
        np.testing.assert_allclose(core.apply_rows(core.normalized(w),value).ravel(),dense(w)@value.ravel(),atol=1e-14)


def test_cue_propagation_matches_dense_paths():
    rng = np.random.default_rng(19)
    w = rng.normal(size=(2,4,4))
    port = np.zeros((4,4),bool);port[0,0]=True
    matrix = dense(w)
    for n in (0,1,2,7,64):
        value = np.zeros(16);value[0]=1
        for _ in range(n):
            value = matrix@value;value[0]=1
        np.testing.assert_allclose(core.cue_transfer(core.normalized(w),port,n).ravel(),value,atol=1e-14)


def test_contrast_gauge_and_coactivity_identity():
    rng = np.random.default_rng(39)
    body = rng.normal(size=(1,2,4,4))
    available = np.ones((1,2,4,4),bool)
    pair = core.writer_pair(body,available)
    for plane,axis in [(0,-1),(1,-2)]:
        np.testing.assert_allclose(pair['c'][:,plane],pair['q'][:,plane]+pair['common']*np.roll(pair['common'],-1,axis),atol=1e-14)
    sign = np.sign(pair['d'])
    value = rng.normal(size=(1,4,4))
    lhs = sign*core.apply_rows(core.normalized(pair['q']),value)
    rhs = core.apply_rows(core.normalized(np.abs(pair['q'])),sign*value)
    np.testing.assert_allclose(lhs,rhs,atol=1e-14)


def test_mask_and_zero_rows():
    mask=np.zeros((1,4,4),bool);mask[:,1,1]=True
    w=core.available_edges(mask).astype(float)
    assert core.incident(w)[0,1,1]==0
    rows=core.normalized(np.zeros_like(w))
    assert not rows.any()
    ports=np.zeros((3,4,4),bool);ports[0,0,0]=True;ports[1,2,2]=True;ports[2,3,3]=True
    vals,_=core.features(np.zeros((1,2,4,4)),mask,ports,np.ones(1),steps=2)
    assert vals['exact_unsigned_access'][0]==0
    assert vals['exact_zero_denominator_fraction'][0]==1


def test_strict_native_score_and_opposite_rule():
    ports=np.array([[[.25,-1],[-1,1]], [[-1,1],[1,-1]]],float)
    margin,passed,_=core.score_ports(ports,np.array([1.,-1.]))
    assert margin.tolist()==[.25,1.]
    assert passed.tolist()==[False,True]
