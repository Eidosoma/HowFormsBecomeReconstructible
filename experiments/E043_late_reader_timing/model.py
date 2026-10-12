"""Three fixed receiving schedules for saved E041 full bridge-rewrite packets."""
from dataclasses import replace
from E023_receiver_compensation import model as receiver
from E031_renewal_durability import evidence
import numpy as np

CFG, Cycle = receiver.CFG, receiver.Cycle
base = receiver.base
TIMINGS = ('original', 'extra_time', 'delayed_extra_time')
HORIZONS = (24, 32)
RECEIVERS = ('fixed_four', 'local_strength')
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
PANELS = tuple((h, t, r) for h in HORIZONS for t in TIMINGS for r in RECEIVERS)


def schedules(cycle, factor=3):
    assert factor == 3 and cycle.generations == 32
    assert 2*cycle.settling_steps == cycle.read_steps
    delayed = factor*cycle.settling_steps
    extended = cycle.read_steps+delayed-cycle.settling_steps
    return tuple(replace(cycle, settling_steps=s, read_steps=t) for s, t in (
        (cycle.settling_steps, cycle.read_steps), (cycle.settling_steps, extended),
        (delayed, extended)))


def assay(record, block, horizon, cfg, cycle):
    before = record.copy()
    raw = receiver.assay(record[None], block, horizon, cfg, cycle)
    np.testing.assert_array_equal(record, before)
    return raw


def score(mean_ports, cfg):
    return evidence.score_mean(mean_ports, cfg, receiver.RULES, receiver.CUES)
