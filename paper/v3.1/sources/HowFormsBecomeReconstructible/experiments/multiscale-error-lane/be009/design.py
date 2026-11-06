"""BE009: does spread in the execution time give a graded decline?

BE007's tissue (BE006's clock SL: the arbiter and every other bond relearning at 3e-4 per update, the bond noise scaled
with it, a commitment of 15,000 updates; be007.sim's arithmetic, re-implemented in be009.sim with execution generalised
and checked bit for bit against be007.sim.run), at read gain 0.2 on BE001's twelve unit-body pairs. BE007 found that
executing the tissue's default decision (commit, in the signal's footprint: the patch dilated by 2) at update tau_x
closes a late signal's window as a step: the full effect before tau_x, none after. Planarian blockade declines
gradually: octanol works best within 3-6 h, keeps under 60 % of its effect after 12 h and none later.

The change: the execution time is drawn, log-normal with median 3,600 updates (12 h at 300 updates an hour) and
coefficient of variation 0.4 (sigma of log tau_x = 0.38525), rounded to whole updates:
  between cases  each case (BE001's case: block, message, parent) draws one tau_x for its whole footprint
  between cells  each footprint cell of each case draws its own tau_x
At update tau_x a footprint cell not committed and with a confident record commits to its record's sign (be007's commit:
the decision state set to 1, the trusted sign to the record's; a later trigger refreshes it but cannot flip it). The
draws are addressed by the run's tag, the case and the stream ('tau-x', 'case' or 'cell'), never by an arm, so a case
has the same tau_x (or map) in every run and in its dial and never arms; the two spreads are drawn independently with
the same marginal.

Clocks (each run as a signal arm 'dial-X', BE004's dial with no hold, and a no-signal arm 'never-X'; all at SL's rates):
  SL    no execution (BE007's SL, the reference for the natural decline)
  C12   commit at tau_x = 3,600 for every case and cell (BE007's C12, the bridge: equal to be007.sim's C12 bit for bit)
  CASE  commit at each case's own tau_x
  CELL  commit at each footprint cell's own tau_x
Runs (event, patch side 4, delay D; the signal on at D + 1 to D + 1,000):
  memory4@0   a 4 x 4 memory damage and the prompt signal: every clock's dial and never arm (window 11,200)
  memory4@D   the same damage with the signal D late, D = 900, 1,800, 2,700, 3,600, 4,500, 5,400, 7,200 updates (3, 6,
              9, 12, 15, 18, 24 h): every clock's dial (window D + 4,000)
Every late signal is read at D + 4,000 (equal elapsed time with the prompt signal's read at 4,000), where memory4@0's
never arms are read too; every run reads the patch's record every 100 updates (the trace).
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from be007 import design as B7
from dl001 import design as DL
from mse.native import address

TAG = "mse-be009"
PROBE_TAG = "mse-p37"
STUDY = "BE009"
PROBE_BLOCKS = (900548, 900552)
IDENTITIES = {"preflight": (900552, 900554), "development": (910460, 910476)}
DEBUG_BLOCKS = (900554, 900556)  # the engine reserves 900000-900999 for engineering; 900548-900555 checked free (the lead)
PURPOSE = B7.PURPOSE

SIDE, SIGMA, CHUNK = B7.SIDE, B7.SIGMA, B7.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B7.EPS, B7.KR, B7.SIGMA_R, B7.KC, B7.STRENGTH0, B7.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B7.KILL_SD, B7.DENSITY, B7.VMIN, B7.PULL, B7.RATE
BODIES, PATTERNS, THETAS = B7.BODIES, B7.PATTERNS, B7.THETAS
MESSAGES, PARENTS, NCASE = B7.MESSAGES, B7.PARENTS, B7.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B7.GAIN, B7.KAPPA, B7.G_LEAK, B7.TAU, B7.S_MIN
SIG = B7.SIG
TAU_M, ETA_CAL, TAU_LONG = B7.TAU_M, B7.ETA_CAL, B7.TAU_LONG
SL = B7.SL                                                      # eta_a = eta = 3e-4, rate scaled, tau_c = 15,000
T_STAR = B7.T_STAR                                              # 1,958.99 updates, 6.53 h
hours = B7.hours

TX_MEDIAN = 12 * TAU_M                                          # 3,600 updates, 12 h: BE007's C12
TX_CV = 0.4
TX_SIGMA = math.sqrt(math.log(1.0 + TX_CV ** 2))                # 0.38525


def clock(form=None, tau_x=None, spread=None):
    return dict(SL, form=form, tau_x=tau_x, spread=spread)


CLOCKS = {"SL": clock(), "C12": clock("commit", TX_MEDIAN), "CASE": clock("commit", TX_MEDIAN, "case"),
          "CELL": clock("commit", TX_MEDIAN, "cell")}
SIGNAL_ARMS = {}
for _c, _p in CLOCKS.items():
    SIGNAL_ARMS[f"dial-{_c}"] = dict(_p, never=False)
    SIGNAL_ARMS[f"never-{_c}"] = dict(_p, never=True)
ARMS = tuple(SIGNAL_ARMS)
DIALS = tuple(f"dial-{c}" for c in CLOCKS)
SPREAD = ("CASE", "CELL")

HOURS = (3, 6, 9, 12, 15, 18, 24)
DELAYS = tuple(h * TAU_M for h in HOURS)                        # 900, 1,800, 2,700, 3,600, 4,500, 5,400, 7,200
AFTER = 4000                                                    # every late signal read at D + 4,000; the prompt's at 4,000
WINDOW_0 = DELAYS[-1] + AFTER                                   # 11,200
READS = (500, 1000, 2000, 3000, 4000, 6000, 8000, 10000)
TRACE = 100


def tx_draws(tag, cases, spread):
    """tau_x per case ('case': (k,)) or per cell ('cell': (k, SIDE, SIDE)), whole updates, addressed by tag, case, stream."""
    if spread == "case":
        z = np.array([address(tag, *c.key(), "tau-x", "case").standard_normal() for c in cases])
    elif spread == "cell":
        z = np.stack([address(tag, *c.key(), "tau-x", "cell").standard_normal((SIDE, SIDE)) for c in cases])
    else:
        raise ValueError(spread)
    return np.maximum(1, np.rint(TX_MEDIAN * np.exp(TX_SIGMA * z))).astype(np.int64)


def tx_map(prm, cases, tag):
    """The arm's execution update for every branch and cell, (k, SIDE, SIDE), or None with no execution."""
    if prm["form"] is None:
        return None
    k = len(cases)
    if prm["spread"] is None:
        return np.full((k, SIDE, SIDE), prm["tau_x"], np.int64)
    x = tx_draws(tag, cases, prm["spread"])
    return np.broadcast_to(x[:, None, None], (k, SIDE, SIDE)).copy() if prm["spread"] == "case" else x


def survival(d):
    """The population share of execution times after a signal that starts at update d + 1: P(tau_x >= d + 2)."""
    return 0.5 * math.erfc(math.log((d + 1.5) / TX_MEDIAN) / (TX_SIGMA * math.sqrt(2.0)))


def run_name(situation, size, delay_, arms=None):
    return f"{situation}{size}@{delay_}"


def run_window(situation, size, delay_, arms=None):
    return WINDOW_0 if (situation == "memory" and delay_ == 0) else delay_ + AFTER


def run_reads(situation, size, delay_, arms=None):
    w = run_window(situation, size, delay_, arms)
    extra = {d + AFTER for d in DELAYS} if (situation == "memory" and delay_ == 0) else {delay_ + AFTER}
    return tuple(sorted({t for t in READS if t <= w} | extra))


def on_window(situation, size, delay_, arms=None):
    """(first, last) update with the signal on."""
    return delay_ + 1, delay_ + SIG["duration"]


RUNS = (("memory", 4, 0, ARMS),
        *(("memory", 4, d, DIALS) for d in DELAYS))
RUNNAMES = tuple(run_name(*x) for x in RUNS)


def where(c, d):
    """(run name, arm) of clock c's dial d updates late."""
    return run_name("memory", 4, d), f"dial-{c}"


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


unit_name, parse_unit, UNITS = B7.unit_name, B7.parse_unit, B7.UNITS


def tasks():
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "be007": "be007.sim's arithmetic for clocks SL and C12, re-implemented in be009.sim with tau_x per branch and cell",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN, "sig": SIG,
            "tau_m": TAU_M, "eta_cal": ETA_CAL, "tau_long": TAU_LONG, "t_star": T_STAR, "tx_median": TX_MEDIAN,
            "tx_cv": TX_CV, "tx_sigma": TX_SIGMA, "tx_streams": {"case": ["tau-x", "case"], "cell": ["tau-x", "cell"]},
            "clocks": CLOCKS, "signal_arms": SIGNAL_ARMS, "arms": ARMS, "hours": HOURS, "delays": DELAYS,
            "after": AFTER, "window_0": WINDOW_0, "runs": RUNS,
            "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006", "be007", "be009")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be009.design  ->  be009/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be009" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
