"""Rollback after first failure; read the matched next rebuilding body."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E022_reader_compensation import model as renewal
import numpy as np

base, Cycle = renewal.base, renewal.Cycle
VARIANTS = ('original', 'targeted_rollback', 'random_rollback')
FIELDS = ('target_edges', 'pool_edges', 'random_edges', 'overlap_edges',
          'target_sign_restores', 'random_sign_restores', 'target_absolute_gain', 'random_absolute_gain')


def first_failures(correct):
    assert correct.ndim == 4 and correct.shape[:2] == (32, 4) and correct.shape[-1] == 2
    assert correct.dtype == np.dtype(bool)
    failed = ~correct.all(axis=-1)
    first = np.where(failed.any(axis=0), failed.argmax(axis=0)+1, 0)
    fr = np.argwhere((first > 0) & (first < 32))
    cases = np.column_stack((fr, first[fr[:, 0], fr[:, 1]]))
    return first.astype(np.int64), cases.astype(np.int64)


def construct(incoming, outgoing, dead, index, block):
    old, new = base.decode(incoming), base.decode(outgoing)
    assert old.shape == new.shape == (len(index), 2, 16, 16)
    assert dead.dtype == np.dtype(bool) and dead.shape == (len(index), 16, 16)
    available = renewal.surviving_edges(dead)
    assert not np.any(new[~available])
    target = available & (abs(old) > .5) & (abs(new) <= .5)
    pool = available & (abs(old) > .5) & (old != new)
    selected = np.zeros_like(target)
    orders = np.empty((len(index), 512), np.int64)
    for c, (f, r, g) in enumerate(index.tolist()):
        orders[c] = rng('E047', block, 'rollback', g, f, r).permutation(512)
        eligible = orders[c][pool[c].ravel()[orders[c]]]
        selected[c].ravel()[eligible[:int(target[c].sum())]] = True
    packets = np.stack((outgoing, base.encode(np.where(target, old, new)),
                        base.encode(np.where(selected, old, new))))
    sign = np.sign(old) != np.sign(new)
    gain = abs(old)-abs(new)
    counts = np.stack([m.sum(axis=(-3, -2, -1)) for m in
        (target, pool, selected, target & selected, target & sign, selected & sign)]
        + [(gain*m).sum(axis=(-3, -2, -1)) for m in (target, selected)], axis=-1)
    np.testing.assert_array_equal(counts[:, 0], counts[:, 2])
    return dict(incoming=incoming, outgoing=outgoing, renewal_mask=dead,
        index=index, available=available, target=target, pool=pool, selected=selected,
        permutations=orders, packets=packets, counts=counts)


def matched_inputs(index, block, cfg, cycle):
    """Draw the full original streams before selecting cases, including omitted cases."""
    count = len(index)
    noise = np.empty((cycle.read_steps+1, count, 16, 16))
    masks = np.empty((count, 16, 16), bool)
    for g in np.unique(index[:, 2]+1).tolist():
        selected = np.flatnonzero(index[:, 2]+1 == g)
        f, r = index[selected, 0], index[selected, 1]
        raw = rng('E022', block, 'develop', g).standard_normal((cycle.read_steps+1, 2, cfg.recipients, 16, 16))
        noise[:, selected] = raw[:, f//2, r]
        masks[selected] = base.damage_masks(block, f'E022_renewal_g{g}', cfg)[f, r, 1]
    return masks, noise


def read(packets, index, block, cfg, cycle):
    assert packets.shape == (3, len(index), 4096)
    assert cycle.generations == 32 and 2*cycle.settling_steps == cycle.read_steps
    before = packets.copy()
    masks, draws = matched_inputs(index, block, cfg, cycle)
    effective = base.decode(packets)*renewal.surviving_edges(masks)[None]
    denom = renewal.incident_sum(abs(effective))
    birth = cfg.birth_sd*draws[0]
    v = np.broadcast_to(birth[None, :, None], (3, len(index), 2, 16, 16)).copy()
    alive = (~masks)[None, :, None]
    cue = base.CUES.reshape(1, 1, 2, 1)
    v *= alive
    v[..., base.PORTS[0]] = cue
    trace = []
    for t in range(cycle.read_steps):
        v = renewal.compensated_step(v, effective[:, :, None], denom[:, :, None],
            draws[t+1][None, :, None], cfg, amplification=t >= cycle.settling_steps)
        v *= alive
        v[..., base.PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack([v[..., p].mean(axis=-1) for p in base.PORTS[1:]], axis=-1))
    np.testing.assert_array_equal(packets, before)
    trace = np.asarray(trace)
    return dict(masks=masks, effective_packets=base.encode(effective), denominator=denom,
                birth=birth, end=v, late_ports=trace, mean_ports=trace.mean(axis=0))


def score(values, index, cfg):
    target = base.RULES[index[:, 0]][None, :, None]*base.CUES[None, None, :]
    a, b = values[..., 0]*target, -values[..., 1]*target
    return dict(correct=(a > cfg.margin) & (b > cfg.margin), margin=np.minimum(a, b), ports=values)
