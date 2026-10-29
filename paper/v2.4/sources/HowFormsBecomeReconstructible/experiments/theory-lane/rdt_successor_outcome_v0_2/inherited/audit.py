"""Separate flat-index cycle replay and sparse transfer check.

The equations are independently written here. This is an implementation check
inside the same research programme, not external scientific replication.
"""
import numpy as np
from scipy.sparse import coo_matrix

INDEX = np.arange(256).reshape(16, 16)
RIGHT = np.array([16*y + (x+1) % 16 for y in range(16) for x in range(16)])
LEFT = np.array([16*y + (x-1) % 16 for y in range(16) for x in range(16)])
DOWN = np.array([16*((y+1) % 16) + x for y in range(16) for x in range(16)])
UP = np.array([16*((y-1) % 16) + x for y in range(16) for x in range(16)])
PORTS = [np.array([16*y+x for y in range(yy, yy+2) for x in range(xx, xx+2)])
         for yy, xx in [(7, 1), (3, 10), (11, 10)]]


def read_write(weights, mask, birth, noise, cfg, beta):
    count = len(weights)
    dead = mask.ravel()
    h = weights[:, 0].reshape(count, 256) * ((~dead) & (~dead[RIGHT]))
    v = weights[:, 1].reshape(count, 256) * ((~dead) & (~dead[DOWN]))
    denom = abs(h) + abs(h[:, LEFT]) + abs(v) + abs(v[:, UP])
    value = np.repeat(birth.reshape(1, 2, 256), count, axis=0)
    value *= ~dead
    value[:, :, PORTS[0]] = np.array([1., -1.])[None, :, None]
    late = []
    for t in range(cfg['read_steps']):
        incoming = (h[:, None] * value[:, :, RIGHT] + h[:, None, LEFT] * value[:, :, LEFT]
                    + v[:, None] * value[:, :, DOWN] + v[:, None, UP] * value[:, :, UP])
        local = np.divide(incoming, denom[:, None], out=np.zeros_like(incoming), where=denom[:, None] > 0)
        self_force = value - value**3 if t >= cfg['settling_steps'] else -value**3
        value = np.clip(value + cfg['dt'] * (self_force + 2 * (local - value))
                        + cfg['noise'] * noise[t].reshape(2, 256), -2., 2.)
        value *= ~dead
        value[:, :, PORTS[0]] = np.array([1., -1.])[None, :, None]
        if t >= cfg['read_steps'] - cfg['observe_steps']:
            late.append(np.stack([value[:, :, p].mean(axis=-1) for p in PORTS[1:]], axis=-1))
    encoded_body = np.tanh(beta * value)
    difference = (encoded_body[:, 0] - encoded_body[:, 1]) / 2
    outgoing = []
    for neighbor in [RIGHT, DOWN]:
        contrast = difference * difference[:, neighbor]
        ordinary = (encoded_body[:, 0] * encoded_body[:, 0, neighbor]
                    + encoded_body[:, 1] * encoded_body[:, 1, neighbor]) / 2
        available = (~dead) & (~dead[neighbor])
        outgoing.append(np.where(available, np.where(contrast == 0., ordinary, contrast), 0.))
    return dict(end=value.reshape(count, 2, 16, 16), windows=np.stack(late),
                outgoing=np.stack(outgoing, axis=1).reshape(count, 2, 16, 16))


def transfer(weights, rule):
    result = []
    for w in weights.reshape(-1, 2, 16, 16):
        rows, cols, values = [], [], []
        for plane, neighbor in enumerate([RIGHT, DOWN]):
            for a in range(256):
                b = int(neighbor[a])
                rows.extend([a, b]); cols.extend([b, a])
                values.extend([w[plane].ravel()[a]] * 2)
        matrix = coo_matrix((values, (rows, cols)), shape=(256, 256)).tocsr()
        den = np.repeat(np.asarray(abs(matrix).sum(axis=1)).ravel(), np.diff(matrix.indptr))
        matrix.data = np.divide(matrix.data, den, out=np.zeros_like(matrix.data), where=den > 0)
        scores = []
        for kind, op in enumerate([matrix, abs(matrix)]):
            value = np.zeros(256); value[PORTS[0]] = 1.
            for _ in range(64):
                value = op @ value; value[PORTS[0]] = 1.
            a, b = [float(value[p].mean()) for p in PORTS[1:]]
            scores.append(min(rule*a, -rule*b) if kind == 0 else min(a, b))
        result.append(scores)
    return np.array(result).reshape(*weights.shape[:-3], 2)
