"""Five current-read policies, with explicit persistent single-rewrite memory."""
import numpy as np


def classify(windows, rules):
    x = np.asarray(windows); rules = np.asarray(rules)
    if x.ndim != 5 or x.shape[2:] != (5, 2, 2) or len(x) != len(rules) or not np.isin(rules, [-1, 1]).all():
        raise ValueError('Packet x frame x five policies x cue x port required')
    if not np.isfinite(x).all():
        raise ValueError('Finite native windows required')
    aligned = x.mean(axis=1) * rules[:, None, None, None] * np.array([[1., -1.], [-1., 1.]])
    correct = aligned.min(axis=(-2, -1)) > .25
    opposite = aligned.max(axis=(-2, -1)) < -.25
    return correct.astype(np.uint8), correct.astype(np.int8) - opposite.astype(np.int8), aligned


def actions(passed, order, used, generation):
    y = np.asarray(passed); rank = np.asarray(order); used = np.asarray(used)
    if y.shape != (4, 5) or not np.isin(y, [0, 1]).all():
        raise ValueError('Four packets by five binary outcomes required')
    if rank.shape != (4,) or rank.dtype.kind not in 'iu' or sorted(rank.tolist()) != [0, 1, 2, 3]:
        raise ValueError('Uniform permutation input required')
    if used.shape != (4,) or used.dtype != np.bool_:
        raise ValueError('One persistent boolean per packet required')
    if generation not in range(15, 34):
        raise ValueError('Undeclared generation')
    result = np.zeros((4, 5), bool)
    if generation < 33:
        result[:, 0] = True
        result[:, 2] = y[:, 2] == 1
        result[rank[:int(result[:, 2].sum())], 1] = True
        result[:, 4] = (y[:, 4] == 1) & ~used
    return result


def advance(incoming, outgoing, passed, order, used, generation):
    if incoming.shape != outgoing.shape or incoming.shape != (4, 5, 2, 16, 16):
        raise ValueError('Four groups of five native packets required')
    action = actions(passed, order, used, generation)
    after = np.where(action[:, :, None, None, None], outgoing, incoming).copy()
    next_used = np.asarray(used).copy() | action[:, 4]
    return after, action, next_used
