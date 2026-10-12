"""Four fixed receiving schedules for unchanged saved maturing packets."""
from dataclasses import replace
from E023_receiver_compensation import model as receiver
from E031_renewal_durability import evidence
import numpy as np

CFG, Cycle = receiver.CFG, receiver.Cycle
base = receiver.base
TIMINGS = ('original', 'delayed_same_duration', 'extra_time', 'delayed_extra_time')
HORIZONS = (8, 16)
RECEIVERS = ('fixed_four', 'local_strength')
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
PANELS = tuple((h, t, r) for h in HORIZONS for t in TIMINGS for r in RECEIVERS)


def schedules(cycle, factor=4):
    assert factor in (2, 4)
    delayed = factor*cycle.settling_steps
    assert delayed < cycle.read_steps
    extended = cycle.read_steps+delayed-cycle.settling_steps
    return tuple(replace(cycle, settling_steps=s, read_steps=t) for s, t in (
        (cycle.settling_steps, cycle.read_steps), (delayed, cycle.read_steps),
        (cycle.settling_steps, extended), (delayed, extended)))


def assay(record, block, horizon, cfg, cycle):
    before = record.copy()
    raw = receiver.assay(record[None], block, horizon, cfg, cycle)
    np.testing.assert_array_equal(record, before)
    return raw


def score(mean_ports, cfg):
    return evidence.score_mean(mean_ports, cfg, receiver.RULES, receiver.CUES)
