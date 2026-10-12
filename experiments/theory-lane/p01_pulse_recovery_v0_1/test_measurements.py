"""Independent graph checks for the recovery metrics and causal timing."""
import numpy as np
import extract

CFG = extract.read(extract.HERE / 'config.json')
CORE = extract.load_core(CFG)


def dense(weights):
    side = weights.shape[-1]
    matrix = np.zeros((side*side, side*side))
    for y in range(side):
        for x in range(side):
            i = y*side+x
            for plane, yy, xx in ((0, y, (x+1) % side), (1, (y+1) % side, x)):
                j = yy*side+xx
                matrix[i, j] = matrix[j, i] = weights[plane, y, x]
    mass = abs(matrix).sum(axis=1)
    return np.divide(matrix, mass[:, None], out=np.zeros_like(matrix), where=mass[:, None] > 0)


def test_relative_weights_and_zero_rows():
    rng = np.random.default_rng(817)
    a = rng.normal(size=(2, 5, 5))
    b = rng.normal(size=(2, 5, 5))
    rows_a, rows_b = CORE.normalized(a), CORE.normalized(b)
    np.testing.assert_allclose(abs(rows_a-rows_b).sum(axis=0).ravel(), abs(dense(a)-dense(b)).sum(axis=1), atol=1e-14)
    np.testing.assert_allclose(CORE.normalized(17*a), rows_a, atol=1e-14)
    assert not CORE.normalized(np.zeros_like(a)).any()


def test_signed_and_unsigned_transfer_against_dense_graph():
    rng = np.random.default_rng(912)
    weights = rng.normal(size=(2, 5, 5))
    port = np.zeros((5, 5), bool)
    port[1, 2] = True
    for w in (weights, abs(weights)):
        matrix = dense(w)
        values = np.zeros(25)
        values[7] = 1
        for _ in range(64):
            values = matrix @ values
            values[7] = 1
        np.testing.assert_allclose(CORE.cue_transfer(CORE.normalized(w), port, 64).ravel(), values, atol=1e-14)


def test_native_threshold_and_founder_direction():
    values = np.array([[[.25, -1.], [-1., 1.]], [[-1., 1.], [1., -1.]]])
    margin, passed, _ = CORE.score_ports(values, np.array([1., -1.]), .25)
    assert margin.tolist() == [.25, 1.] and passed.tolist() == [False, True]


def test_same_body_action_is_distinct_from_history_distance():
    # An unchanged writer on a changed body can have zero local action distance
    # but a nonzero distance from the original history.
    rng = np.random.default_rng(71)
    body = rng.normal(size=(2, 2, 5, 5))
    available = np.ones((2, 2, 5, 5), bool)
    original = CORE.writer_pair(body, available)['exact']
    rows = CORE.normalized(original)
    assert not abs(rows-CORE.normalized(original)).any()
    assert abs(rows[0]-rows[1]).sum() > 0
