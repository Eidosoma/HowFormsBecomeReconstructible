"""NP002's tissue: NP001's (np001.sim.stage1 and np001.sim.successor, unchanged and imported; through them LR002's
relations, DL001's bodies and DL002's acquisition), with conflicts built from any two of NP001's patterns.

A conflict unit takes the body, its moving average and theta from the acquisition of PAIRS[unit][0] and the record and
the history from that of PAIRS[unit][1]; every acquisition is np001.sim.prepare's (DL002's tag, birth, settle, teach and
release noise), so the two share their noise and differ only in the template taught. T is the record's template (the
history), T0 the body's initial one. For C4sK this equals np001.sim.prepare('C4sK') bit for bit (checks Q3).
"""
from __future__ import annotations

import numpy as np

from dl002 import design as D2
from np001 import sim as N1S

from . import design as D

ENDS1, ENDS2 = N1S.ENDS1, N1S.ENDS2
stage1, successor = N1S.stage1, N1S.successor


def prepare(unit, block, purpose):
    """The body (V0, ema0, theta) from the first pattern's acquisition, the record R0 and history T from the second's."""
    bp, rp = D.PAIRS[unit]
    cases, V0, ema0, _, th, _ = N1S.prepare(bp, block, purpose)
    _, _, _, R0, _, T = N1S.prepare(rp, block, purpose)
    return cases, V0, ema0, R0, th, T


def initial(unit, cases, block):
    """T0: the body's initial template (the first pattern's)."""
    return np.stack([D2.AMPLITUDE * N1S.template(D.PAIRS[unit][0], c.message, block) for c in cases])


def preference(align, align_b, unit):
    """(alignment with the record's pattern - alignment with the body's initial one) / (1 - a0): +1 at the record's
    pattern, -1 at the body's initial pattern; a0 is the two templates' sign agreement (design.A0, checked in Q7)."""
    return (np.asarray(align) - np.asarray(align_b)) / (1.0 - D.A0[unit])
