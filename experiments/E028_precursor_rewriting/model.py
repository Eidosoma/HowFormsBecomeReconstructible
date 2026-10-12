"""Paired generation-three reading and writing interventions on saved histories."""
from dataclasses import replace
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E023_receiver_compensation import model as receiver
import numpy as np

base, renewal = receiver.base, receiver.renewal
CFG, Cycle = receiver.CFG, receiver.Cycle
CYCLE = replace(receiver.CYCLE, generations=3)
assay, score = receiver.assay, receiver.score
receiver_denominators = receiver.receiver_denominators
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
PORTS, RULES, CUES, RECEIVERS = receiver.PORTS, receiver.RULES, receiver.CUES, receiver.RECEIVERS
READS = ('kept', 'erased')
CONDITIONS = ('kept_refreshed', 'kept_frozen', 'erased_refreshed', 'erased_frozen')
PANELS = tuple((name, reader) for reader in RECEIVERS for name in CONDITIONS)
STRENGTH_FIELDS = ('target_count', 'incoming_nonzero', 'incoming_mean_abs', 'incoming_strong',
                   'kept_mean_abs', 'kept_strong', 'erased_mean_abs', 'erased_strong')


def target_edges(renewal_masks):
    """All g1-erased, g2-available, g3-available edges, independent of weights."""
    assert renewal_masks.shape[0] == 3 and renewal_masks.dtype == bool
    available = renewal.surviving_edges(renewal_masks)
    return available, ~available[0] & available[1] & available[2]


def develop(packets, masks, block, cfg=CFG, cycle=CYCLE):
    assert packets.shape == (2, 4, cfg.recipients, 4096)
    assert masks.shape == (2, 4, cfg.recipients, 16, 16)
    decoded = base.decode(packets)
    denominator = renewal.incident_sum(np.abs(decoded))
    weights = decoded[:, :, :, None]
    stream = rng('E022', block, 'develop', 3)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (2, 4, cfg.recipients, 2, 16, 16)).copy()
    active = (~masks)[:, :, :, None]
    v *= active
    cue = CUES.reshape(1, 1, 1, 2, 1)
    v[..., PORTS[0]] = cue
    trace = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = renewal.compensated_step(v, weights, denominator[:, :, :, None], noise, cfg,
                                     amplification=t >= cycle.settling_steps)
        v *= active
        v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    return dict(birth=birth, read_denominators=denominator, developed_end=v, developed_late_ports=np.stack(trace))


def write_from_activity(body, masks, block, cfg=CFG, cycle=CYCLE):
    """Unchanged immediate local capture; holding states retained for replay."""
    stream = rng('E022', block, 'write', 3)
    v = body.copy()
    computed = renewal.capture_from_activity(v, cfg)
    active = (~masks)[:, :, :, None]
    scaffold = renewal.surviving_edges(masks)[:, :, :, None].astype(float)
    cue = CUES.reshape(1, 1, 1, 2, 1)
    states = []
    for _ in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue
        states.append(v.copy())
    return dict(computed_packets=computed, write_states=np.stack(states), write_end=v)


def construct(incoming, computed, target, current):
    """Freeze only target coordinates to their saved g2 values after capture."""
    old, fresh = base.decode(incoming), base.decode(computed)
    assert fresh.shape == (2, *old.shape) and target.shape == old.shape
    assert not (target & ~current).any() and not fresh[:, ~current].any()
    weights = fresh[[0, 0, 1, 1]].copy()
    for branch in (1, 3):
        weights[branch][target] = old[target]
    assert not weights[:, ~current].any()
    return base.encode(weights)


def boundary(incoming, renewal_masks, block, cfg=CFG, cycle=CYCLE):
    available, target = target_edges(renewal_masks)
    masks = np.repeat(renewal_masks[2][None], 2, axis=0)
    effective = np.repeat((base.decode(incoming)*available[2])[None], 2, axis=0)
    effective[1][target] = 0.
    packets = base.encode(effective)
    saved_packets = packets.copy()
    developed = develop(packets, masks, block, cfg, cycle)
    packets.fill(0)
    written = write_from_activity(developed['developed_end'], masks, block, cfg, cycle)
    records = construct(incoming, written['computed_packets'], target, available[2])
    return dict(incoming=incoming.copy(), renewal_masks=renewal_masks.copy(), available=available,
        target=target, body_masks=masks, read_packets=saved_packets, erased_packets=packets,
        records=records, **developed, **written)


def body_score(trace, cfg=CFG):
    values = trace.mean(axis=0)
    desired = RULES.reshape(1, 4, 1, 1)*CUES.reshape(1, 1, 1, 2)
    a, b = desired*values[..., 0], -desired*values[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), values


def strength_rows(raw):
    old, fresh, target = base.decode(raw['incoming']), base.decode(raw['computed_packets']), raw['target']
    rows = []
    for f in range(4):
        for r in range(old.shape[1]):
            t = target[f, r]; count = int(t.sum())
            values = [np.abs(w[t]) for w in (old[f, r], fresh[0, f, r], fresh[1, f, r])]
            row = dict(founder=f, lineage=r, target_count=count, incoming_nonzero=int(np.count_nonzero(values[0])))
            for label, v in zip(('incoming', 'kept', 'erased'), values):
                row[label+'_mean_abs'] = float(v.mean()) if count else 0.
                row[label+'_strong'] = int((v > .5).sum())
            rows.append(row)
    return rows


def check_boundary(raw, source):
    np.testing.assert_array_equal(raw['incoming'], source['incoming'][2])
    np.testing.assert_array_equal(raw['renewal_masks'][2], source['renewal_mask'])
    np.testing.assert_array_equal(raw['birth'], source['birth'])
    for key in ('body_masks', 'read_packets', 'read_denominators', 'developed_end', 'computed_packets', 'write_end'):
        np.testing.assert_array_equal(raw[key][0], source[key][2])
    for key in ('developed_late_ports', 'write_states'):
        np.testing.assert_array_equal(raw[key][:, 0], source[key][:, 2])
    np.testing.assert_array_equal(raw['records'][0], source['outgoing'][2])


def check_endpoints(raw, source):
    for key in ('permutations', 'masks', 'birth'):
        np.testing.assert_array_equal(raw[key], source[key])
    np.testing.assert_array_equal(raw['packets'][0], source['packets'][2])
    for key in ('receiver_denominators', 'end', 'late_mean'):
        np.testing.assert_array_equal(raw[key][[0, 4]], source[key][[2, 10]])
    np.testing.assert_array_equal(raw['late_ports'][:, [0, 4]], source['late_ports'][:, [2, 10]])
