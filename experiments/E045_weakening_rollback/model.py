"""Targeted last-write rollback, with an equal-count randomized comparator."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E023_receiver_compensation import model as receiver
from E031_renewal_durability import evidence
import numpy as np

base, CFG, Cycle = receiver.base, receiver.CFG, receiver.Cycle
VARIANTS = ('original', 'targeted_rollback', 'random_rollback')
HORIZONS = (24, 32)
RECEIVERS = ('fixed_four', 'local_strength')
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
# The receiving implementation returns all fixed-four panels, then normalized.
PANELS = tuple((h, v, r) for h in HORIZONS for r in RECEIVERS for v in VARIANTS)
SELECTION_FIELDS = ('target_edges', 'pool_edges', 'random_edges', 'overlap_edges',
                    'target_sign_restores', 'random_sign_restores',
                    'target_absolute_gain', 'random_absolute_gain')


def construct(incoming, outgoing, renewal_mask, block, horizon):
    """No terminal outcome enters selection. All edits restore exact old values."""
    old, new = base.decode(incoming), base.decode(outgoing)
    assert old.shape == new.shape and old.shape[:1] == (4,)
    assert renewal_mask.dtype == np.dtype(bool) and renewal_mask.shape == old.shape[:2]+(16, 16)
    alive = ~renewal_mask
    available = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    assert not np.any(new[~available])
    target = available & (abs(old) > .5) & (abs(new) <= .5)
    pool = available & (abs(old) > .5) & (old != new)
    assert not np.any(target & ~pool)
    selected = np.zeros_like(target)
    permutations = np.empty(old.shape[:2]+(512,), dtype=np.int64)
    for f in range(4):
        for r in range(old.shape[1]):
            order = rng('E045', block, 'rollback', horizon, f, r).permutation(512)
            permutations[f, r] = order
            eligible = order[pool[f, r].ravel()[order]]
            count = int(target[f, r].sum())
            selected[f, r].ravel()[eligible[:count]] = True
    packets = np.stack((outgoing, base.encode(np.where(target, old, new)),
                        base.encode(np.where(selected, old, new))))
    reduce_axes = (-3, -2, -1)
    sign_change = np.sign(old) != np.sign(new)
    absolute_gain = abs(old)-abs(new)
    counts = np.stack([m.sum(axis=reduce_axes) for m in
        (target, pool, selected, target & selected, target & sign_change, selected & sign_change)]
        + [(absolute_gain*m).sum(axis=reduce_axes) for m in (target, selected)], axis=-1)
    assert np.array_equal(counts[..., 0], counts[..., 2])
    return dict(incoming=incoming.copy(), outgoing=outgoing.copy(), renewal_mask=renewal_mask.copy(),
                available=available, target=target, pool=pool, selected=selected,
                permutations=permutations, packets=packets, counts=counts)


def assay(records, block, horizon, cfg, cycle):
    assert records.shape == (3, 4, cfg.recipients, 4096)
    assert cycle.generations == 32 and 2*cycle.settling_steps == cycle.read_steps
    before = records.copy()
    raw = receiver.assay(records, block, horizon, cfg, cycle)
    np.testing.assert_array_equal(records, before)
    return raw


def score(mean_ports, cfg):
    return evidence.score_mean(mean_ports, cfg, receiver.RULES, receiver.CUES)
