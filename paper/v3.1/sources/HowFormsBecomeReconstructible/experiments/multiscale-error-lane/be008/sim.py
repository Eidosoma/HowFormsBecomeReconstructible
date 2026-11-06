"""BE008's tissue: BE006's (be006.sim.run, unchanged), with BE008's clocks passed as its per-arm params and BE008's
windows. Every arm is a signal arm (the dial, or 'never': the same tissue with the signal never on); branches are
arm-major and paired within a case (the same event and noise draws; each arm's bond noise cut from the same standard
normal per bond, so a quieter arm's flips are a subset of a noisier arm's).
"""
from __future__ import annotations

from be006 import sim as B6S
from be006.sim import ENDS, event, footprint, new_state, patch, prepare, sig_targets  # noqa: F401  (BE006's, unchanged)

from . import design as D


def run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, tag=D.TAG,
        window=None, on_window=None, params=None, observe=None):
    """One run of be006.sim.run with BE008's clocks (params default D.SIGNAL_ARMS) and window (D.run_window)."""
    window = D.run_window(situation, size, delay, arms) if window is None else window
    return B6S.run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, reads, gain=gain, tag=tag,
                   window=window, on_window=on_window, params=D.SIGNAL_ARMS if params is None else params, observe=observe)
