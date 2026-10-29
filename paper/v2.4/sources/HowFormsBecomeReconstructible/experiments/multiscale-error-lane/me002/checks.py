"""Qualification of ME002 on the preflight (engineering) shards; criteria fixed in advance.

python -m me002.checks --root PREFLIGHT_ROOT --cpus LIST   (writes frozen/qualification_receipt.json)

Q1  complete and finite: every task, arm, condition (or generation) and case present
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  legacy replay: identity routes (inactive, hold, reciprocal) equal legacy blueprint_step bit for
    bit, at couplings 1 and 2.5, and so does the fresh reader
Q4  independent replay: a plain per-site loop built on the design fixtures (operators.py), with its
    own event, clamp, sign-vote and arbiter code, reproduces eight branches (random onset with a burst
    and a later body injury, an aborted burst, an imposition, a region clamp, an equal-dose vote, a
    weak-coupling route, a founder-to-newborn chain with the developmental latch) and a fresh
    reading, within 1e-9
Q5  aliases exact: clamp_site under reference-only damage = hold under sham; every clamp = hold
    while R is intact; the oracle = hold where it never bursts; an arbiter = hold in every case where
    it never bursts; hold's final R = the post-injury copy; panels B, C, D and E agree bit for bit
    wherever they run the same arm, regime and condition
Q6  reanalysis: endpoints recomputed from saved states equal the saved ones; fresh endpoints
    recomputed by re-reading saved packets equal the saved ones
Q7  known-reference reader: target-packet minus zero-packet fresh sign >= 0.15 in every regime of
    panels A-E; primary regime: target fresh sign >= 0.75 and fresh qualified >= 0.65
Q8  perturbation efficacy: every injury slot has nonzero RMS exactly where its condition says;
    every imposition sets the body to the imposed pattern; in the primary regime some RMS-2 band
    lowers hold's v_qual or fQ_qual by >= 0.02 versus sham, for body and for reference damage
Q9  resources: forecast development wall <= 24 h on 16 workers, 16 x peak RSS <= 80% of available
    RAM, forecast bytes <= 80% of free disk
Q10 reader dry run: analyze.py completes on the preflight shards, scores every statement and keeps
    every git file at 256 KB or less
A secondary-regime failure of Q7 alone gives PASS_WITH_FLAGS (that regime's successor endpoints are
reported as reader-unqualified); any other failure gives FAIL and stops the campaign.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
LEGACY = LANE.parents[2] / "PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas"

import numpy as np  # noqa: E402

import operators as fixture  # noqa: E402  the design-record fixtures
from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from me002 import worker as W  # noqa: E402
from mse.assay import enrol, spread  # noqa: E402
from mse.native import NATIVE, address, center, thresholds  # noqa: E402

FROZEN = LANE / "me002" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 16


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def cidx(panel, name):
    return [c.name for c in D.PANELS[panel]["conditions"]].index(name)


# ---------------------------------------------------------------- independent scalar model
def op(level):
    return (lambda x: x.copy()) if level == "site" else (lambda x: fixture.spatial_operator(x, level))


def scalar_channel(spec):
    if spec is None:
        return None
    sl, so, al, ao, decision = spec
    assert tuple(so) == (0, 0) and tuple(ao) == (0, 0)
    s, a = op(sl), op(al)
    if decision == "linear":
        return lambda d: a(s(d))
    if decision == "sign":
        return lambda d: a(np.where(np.abs(s(d)) > 0.0, np.sign(s(d)), 0.0))
    raise ValueError(decision)


def scalar_step(V, ema, R, Q, theta, z, p, body, ref, gain, rate):
    drift = np.empty((16, 16))
    for i in range(16):
        for j in range(16):
            nb = (V[(i - 1) % 16, j] + V[(i + 1) % 16, j] + V[i, (j - 1) % 16] + V[i, (j + 1) % 16]) / 4.0
            drift[i, j] = V[i, j] - V[i, j] ** 3 + theta[i, j] + p.coupling * (nb - V[i, j])
    Vt = np.clip(V + p.dt * center(drift) + center(p.sigma * z), -2.0, 2.0)
    ema = (1 - p.ema_rate) * ema + p.ema_rate * Vt
    Vn = Vt if body is None else np.clip(Vt + p.dt * center(gain * body(R - Vt)), -2.0, 2.0)
    if ref is not None:
        R = R - rate * ref(R - Vn)
    return Vn, ema, R, Q + p.rho * (Vn - Q), Vt


class ScalarArbiter:
    """The burst rule restated for one case from REGISTRATION_ME002.md."""

    def __init__(self, tm, ts, trigger, W, abort, latch0):
        self.tm, self.ts, self.trigger, self.W, self.abort = tm, ts, trigger, W, abort
        self.latch, self.burst, self.refr = (latch0 if W > 0 else 0), 0, 0

    def decide(self, Vt, ema, R):
        m = float((op(self.trigger)(R - Vt) ** 2).mean())
        s = float((fixture.spatial_operator(Vt - ema, "region") ** 2).mean())
        if self.W > 0:
            self.latch = self.W if s > self.ts else max(self.latch - 1, 0)
        if self.abort and self.burst > 0 and s > self.ts:
            self.burst, self.refr = 0, D.REFRACTORY
        if m > self.tm and self.latch == 0 and self.burst == 0 and self.refr == 0:
            self.burst = D.BURST_UPDATES
        on = self.burst > 0
        ending = on and self.burst == 1
        self.burst = max(self.burst - 1, 0)
        self.refr = D.REFRACTORY if ending else max(self.refr - 1, 0)
        return (0.0, D.BURST_RATE) if on else (NATIVE.gain, 0.0)


def scalar_field(c, target, band, rms, *stream):
    x = fixture.error_bands(address(D.TAG, *c.key(), *stream, "damage", target, band).standard_normal((16, 16)))[band]
    return x * (rms / np.sqrt((x ** 2).mean()))


def scalar_acquire(name, block, ci):
    family, sigma, g = D.parse(name)
    p = sim.params(name)[1]
    c = enrol([block], D.MESSAGES, D.PARENTS, "engineering")[ci]
    th = thresholds(address(D.TAG, "theta", block), replace(p, threshold_spread=spread(D.TAG, block)))
    T = D.TEMPLATES[family][c.message]
    V = 0.2 * center(address(D.TAG, *c.key(), "birth").standard_normal((16, 16)))
    ema, R, Q = V.copy(), V.copy(), np.zeros((16, 16))
    site = scalar_channel(D.SITE)
    for stream, n in (("settle", D.SETTLE), ("teach", D.TEACH), ("release", D.RELEASE)):
        Z = address(D.TAG, *c.key(), stream).standard_normal((n, 16, 16))
        for t in range(n):
            if stream == "teach":
                V = T.copy()
            V, ema, R, Q, _ = scalar_step(V, ema, R, Q, th, Z[t], p, site, None if stream == "release" else site,
                                          p.gain, p.rho)
    return c, p, th, T, D.TEMPLATES[family][D.FOREIGN[c.message]], (V, ema, R)


def scalar_vote(V, R1, R2):
    """The two-record vote restated region by region."""
    R1, R2 = R1.copy(), R2.copy()
    for a in range(4):
        for b in range(4):
            sl = (slice(4 * a, 4 * a + 4), slice(4 * b, 4 * b + 4))
            if np.abs(R1[sl] - R2[sl]).max() > 0:
                if ((R2[sl] - V[sl]) ** 2).mean() < ((R1[sl] - V[sl]) ** 2).mean():
                    R1[sl] = R2[sl]
                else:
                    R2[sl] = R1[sl]
    return R1, R2


def scalar_life(arm, c, p, th, start, L, events, imposition, Z, calib, name, window, newborn=False, clamp_src=None):
    """One branch: events = [(t, dV, dR, dR2), each None or a field], imposition = (start, stop,
    pattern) or None."""
    V, ema, R = (x.copy() for x in start)
    R2 = R.copy() if arm.copies == 2 else None
    Q = np.zeros((16, 16))
    body, ref = scalar_channel(arm.body), scalar_channel(arm.reference)
    ctl = None
    if arm.control == "arbiter":
        tm, ts = W.thresholds(arm, name, window, calib, newborn)
        ctl = ScalarArbiter(tm, ts, arm.trigger, arm.latch, arm.abort, arm.latch if newborn else 0)
    gain, rate = p.gain, p.rho
    if arm.control == "matched":
        gain = calib["gains"][name][arm.name] * NATIVE.gain
    size = {"site": 1, "region": 4, "sheet": 8}.get(arm.clamp)
    backup = None if arm.clamp is None else (clamp_src.copy() if size == 1 else fixture.block_projection(clamp_src, size))
    for t in range(1, L + 1):
        for te, dV, dR, dR2 in events:
            if te == t:
                if dV is not None:
                    V = np.clip(V + dV, -2.0, 2.0)
                if dR is not None:
                    R = np.clip(R + dR, -2.0, 2.0)
                if dR2 is not None and R2 is not None:
                    R2 = np.clip(R2 + dR2, -2.0, 2.0)
        if imposition is not None and imposition[0] <= t < imposition[1]:
            V = imposition[2].copy()
        if R2 is not None:
            R, R2 = scalar_vote(V, R, R2)
        if backup is not None:
            R = backup.copy() if size == 1 else R + (backup - fixture.block_projection(R, size))
        if ctl is None:
            V, ema, R, Q, _ = scalar_step(V, ema, R, Q, th, Z[t - 1], p, body, ref, gain, rate if ref is not None else 0.0)
        else:
            # the decision reads V-tilde, so compute it first with a dry step, then the real one
            Vt = _vtilde(V, th, Z[t - 1], p)
            ema_next = (1 - p.ema_rate) * ema + p.ema_rate * Vt
            g_, r_ = ctl.decide(Vt, ema_next, R)
            V, ema, R, Q, _ = scalar_step(V, ema, R, Q, th, Z[t - 1], p, body, ref, g_, r_)
    return V, R, Q


def _vtilde(V, th, z, p):
    drift = np.empty((16, 16))
    for i in range(16):
        for j in range(16):
            nb = (V[(i - 1) % 16, j] + V[(i + 1) % 16, j] + V[i, (j - 1) % 16] + V[i, (j + 1) % 16]) / 4.0
            drift[i, j] = V[i, j] - V[i, j] ** 3 + th[i, j] + p.coupling * (nb - V[i, j])
    return np.clip(V + p.dt * center(drift) + center(p.sigma * z), -2.0, 2.0)


def scalar_window(panel, name, arm_name, cond_name, ci, calib):
    spec = D.PANELS[panel]
    L = spec["window"]
    c, p, th, T, Tf, start = scalar_acquire(name, BLOCK, ci)
    tau = 1 if spec["onset"] == "start" else int(address(D.TAG, *c.key(), "onset").integers(*D.ONSET))
    cond = next(x for x in spec["conditions"] if x.name == cond_name)
    events, imposition = [], None
    for ev in cond.events:
        if ev.kind == "impose":
            imposition = (tau, tau + ev.duration if ev.duration else L + 1, Tf)
            continue
        dV = scalar_field(c, "body", ev.band, ev.rms) if ev.target in ("body", "both") else None
        dR = scalar_field(c, "reference", ev.band, ev.rms) if ev.target in ("reference", "both", "reference2") else None
        dR2 = scalar_field(c, "reference2", ev.band, ev.rms) if ev.target == "reference2" else None
        events.append((tau + ev.delay, dV, dR, dR2))
    Z = address(D.TAG, *c.key(), "future").standard_normal((L, 16, 16))
    arm = D.ARM[panel][arm_name]
    return scalar_life(arm, c, p, th, start, L, events, imposition, Z, calib, name, L, clamp_src=start[2]), start


def scalar_chain(name, arm_name, env, ci, calib, generations=1):
    c, p, th, T, Tf, start = scalar_acquire(name, BLOCK, ci)
    arm = D.ARM["F"][arm_name]
    out, state = [], start
    for g in range(generations + 1):
        tau = int(address(D.TAG, *c.key(), "gen", g, "onset").integers(*D.GEN_ONSET))
        band = D.BANDS[int(address(D.TAG, *c.key(), "gen", g, "band").integers(3))]
        u = float(address(D.TAG, *c.key(), "gen", g, "loc").random())
        loc = "body" if u < 0.4 else ("reference" if u < 0.8 else "both")
        if env == "reference":
            loc = "reference"
        events = []
        if env != "none":
            dV = scalar_field(c, "body", band, 2.0, "gen", g) if loc in ("body", "both") else None
            dR = scalar_field(c, "reference", band, 2.0, "gen", g) if loc in ("reference", "both") else None
            events.append((tau, dV, dR, None))
        Z = address(D.TAG, *c.key(), "gen", g, "life").standard_normal((D.LIFE, 16, 16))
        V, R, Q = scalar_life(arm, c, p, th, state, D.LIFE, events, None, Z, calib, name, D.LIFE, newborn=g > 0)
        packet = R if arm.packets[0] == "R" else Q
        out.append((V, packet))
        nb = 0.2 * center(address(D.TAG, *c.key(), "gen", g + 1, "birth").standard_normal((16, 16)))
        state = (nb, nb.copy(), packet)
    return out


def scalar_reading(name, ci, packet):
    c, p, th, *_ = scalar_acquire(name, BLOCK, ci)
    V = 0.2 * center(address(D.TAG, *c.key(), "recipient", 0, "birth").standard_normal((16, 16)))
    ema, R, Q = V.copy(), packet.copy(), np.zeros((16, 16))
    Z = address(D.TAG, *c.key(), "recipient", 0, "read").standard_normal((D.READ_UPDATES, 16, 16))
    site = scalar_channel(D.SITE)
    for t in range(D.READ_UPDATES):
        V, ema, R, Q, _ = scalar_step(V, ema, R, Q, th, Z[t], p, site, None, p.gain, 0.0)
    return V


Q4_PICKS = (("A", D.regime("F0", 0.3), "arbiter", "ref-then-body-10", 0),
            ("A", D.regime("BL", 0.3), "arbiter_abort", "ref-then-body-10", 2),
            ("A", D.regime("F0", 0.3), "hold_site", "impose-300", 1),
            ("D", D.regime("IS", 0.3), "clamp_region", "reference-regional-2", 3),
            ("E", D.regime("F4", 0.3), "sign_sheet_site_eq", "sham", 4),
            ("B", D.regime("F0", 0.1, 0.25), "hold_region", "reference-fine-2", 5),
            ("C", D.regime("S4", 0.2), "arbiter_pooled", "reference-collective-2", 6),
            ("D", D.regime("F0", 0.3), "dual_vote", "both-collective-2", 0),
            ("D", D.regime("BL", 0.3), "dual_vote", "reference2-collective-2", 1))


# ---------------------------------------------------------------- legacy replay
class Draws:
    def __init__(self, Z):
        self.Z, self.t = Z, 0

    def standard_normal(self, shape):
        z = self.Z[self.t]
        assert z.shape == tuple(shape)
        self.t += 1
        return z


def legacy_replay(panel, name, raw, arms):
    sys.dont_write_bytecode = True
    for pkg in ("voltage_web", "ladder_web", "blueprint_web", "growing_web", "contract_bridge", "glider_test", "xeno_bridge"):
        sys.path.insert(0, str(LEGACY / pkg / "src"))
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step
    from ladder_web.config import LadderConfig
    from voltage_web.config import VoltageConfig
    family, p = sim.params(name)
    tissue, ladder = VoltageConfig(sigma=p.sigma, coupling=p.coupling), LadderConfig()
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    th = raw["theta"]
    L = D.PANELS[panel]["window"]
    Zf = sim.draws(cases, "future", updates=L)
    conds = D.PANELS[panel]["conditions"]
    k = len(cases)
    prog = sim.condition_program(conds, cases, np.ones(k, int), raw["foreign"], L)
    V1, R1 = prog.apply(1, np.tile(raw["s0/V"], (len(conds), 1, 1)), np.tile(raw["s0/R"], (len(conds), 1, 1)))
    results = {}
    for arm, (c_m, rho) in arms.items():
        bp = BlueprintConfig() if rho is None else BlueprintConfig(rho=rho)
        for cond in ("sham", "reference-collective-2", "body-regional-2", "both-collective-2"):
            if cond not in [x.name for x in conds]:
                continue
            ci = cidx(panel, cond)
            sl = slice(ci * k, (ci + 1) * k)
            V, ema, R, Q = V1[sl].copy(), raw["s0/ema"].copy(), R1[sl].copy(), np.zeros((k, 16, 16))
            rng = Draws(Zf)
            for _ in range(L):
                V, ema, R = blueprint_step(V, ema, R, th, tissue, ladder, bp, "T", rng, c_m=c_m)
                Q = Q + NATIVE.rho * (V - Q)
            results[f"{panel}/{name}/{arm}/{cond}"] = all(np.array_equal(x, raw[f"{arm}/{f}"][ci]) for x, f in ((V, "V"), (R, "R"), (Q, "Q")))
    births, Zr = sim.recipients(cases)
    packets = raw["hold_site/Q"][0]
    V = births.reshape(-1, 16, 16)
    R = np.repeat(packets, D.RECIPIENTS, axis=0)
    rng = Draws(Zr.reshape(D.READ_UPDATES, -1, 16, 16))
    ema = V.copy()
    for _ in range(D.READ_UPDATES):
        V, ema, R = blueprint_step(V, ema, R, np.repeat(th, D.RECIPIENTS, axis=0), tissue, ladder,
                                   BlueprintConfig(rho=0.0), "T", rng)
    reread = sim.read_batch(packets, np.arange(k), th, births, Zr, p)
    results[f"{panel}/{name}/fresh_reader"] = bool(np.array_equal(V.reshape(k, D.RECIPIENTS, 16, 16), reread))
    return results


# ---------------------------------------------------------------- the checks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None, help="LO,HI: debugging on design.DEBUG_BLOCKS; the receipt then stays in ROOT")
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    global BLOCK
    BLOCK = lo
    receipt_path = FROZEN / "qualification_receipt.json" if a.blocks is None else root / "debug_qualification_receipt.json"
    calib = json.loads((FROZEN / "calibration.json").read_text())
    checks, flags = {}, []
    manifest = json.loads((root / "manifest.json").read_text())
    shard = lambda p, r, b=lo: npz(root / "shards" / p / r / f"{b}.npz")
    rawf = lambda p, r, b=lo: npz(root / "raw" / p / r / f"{b}.npz")

    # Q1
    missing = []
    for p, r in D.tasks():
        for b in range(lo, hi):
            path = root / "shards" / p / r / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{r}/{b}")
                continue
            e = npz(path)
            spec = D.PANELS[p]
            for arm in spec["arms"]:
                eps = ["v_qual", "d_body_l1"] if p == "F" else ["v_qual", "e20_qual", "r_sign", "d_body_l1"]
                eps += [] if p == "F" else [f"f{pk}_qual" for pk in arm.packets]
                shape = (D.GENERATIONS + 1, len(D.ENVIRONMENTS), D.NCASE) if p == "F" else (len(spec["conditions"]), D.NCASE)
                for ep in eps:
                    x = e.get(f"{arm.name}/{ep}")
                    if x is None or x.shape != shape or not np.isfinite(x).all():
                        missing.append(f"{p}/{r}/{b}/{arm.name}/{ep}")
            for pk in spec.get("packets", ()):
                if f"{pk}/fP_qual" not in e:
                    missing.append(f"{p}/{r}/{b}/{pk}")
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10], "tasks": len(manifest["tasks"])}

    # Q2
    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        r = D.PRIMARY if D.PRIMARY in D.PANELS[p]["regimes"] else D.PANELS[p]["regimes"][0]
        W.run_task(p, r, lo, "engineering", calib, str(serial))
        ok = True
        for kind in ("shards", "raw"):
            x, y = npz(root / kind / p / r / f"{lo}.npz"), npz(serial / kind / p / r / f"{lo}.npz")
            ok &= x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x)
        same[f"{p}/{r}"] = bool(ok)
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    # Q3
    legacy = {}
    legacy.update(legacy_replay("C", D.PRIMARY, rawf("C", D.PRIMARY),
                                {"inactive": (0.0, 0.0), "hold_site": (None, 0.0), "reciprocal": (None, None)}))
    r = D.regime("F4", 0.1, 2.5)
    legacy.update(legacy_replay("B", r, rawf("B", r), {"inactive": (0.0, 0.0), "hold_site": (None, 0.0)}))
    checks["Q3_legacy_bit_exact"] = {"pass": all(legacy.values()), "items": legacy}

    # Q4
    worst, items = 0.0, {}
    for p, r, arm, cond, ci in Q4_PICKS:
        (V, R, Q), start = scalar_window(p, r, arm, cond, ci, calib)
        raw = rawf(p, r)
        k = cidx(p, cond)
        d = max(float(np.abs(start[0] - raw["s0/V"][ci]).max()), float(np.abs(start[2] - raw["s0/R"][ci]).max()),
                float(np.abs(V - raw[f"{arm}/V"][k, ci]).max()), float(np.abs(R - raw[f"{arm}/R"][k, ci]).max()),
                float(np.abs(Q - raw[f"{arm}/Q"][k, ci]).max()))
        items[f"{p}/{r}/{arm}/{cond}/case{ci}"], worst = d, max(worst, d)
    raw = rawf("F", D.PRIMARY)
    chain = scalar_chain(D.PRIMARY, "arbiter_R", "mixed", 7, calib, generations=1)
    e = D.ENVIRONMENTS.index("mixed")
    for g, (V, packet) in enumerate(chain):
        d = max(float(np.abs(V - raw["arbiter_R/V"][g, e, 7]).max()), float(np.abs(packet - raw["arbiter_R/packet"][g, e, 7]).max()))
        items[f"F/{D.PRIMARY}/arbiter_R/mixed/gen{g}/case7"], worst = d, max(worst, d)
    rawc = rawf("C", D.PRIMARY)
    Vr = scalar_reading(D.PRIMARY, 0, rawc["hold_site/Q"][0, 0])
    cases = enrol([lo], D.MESSAGES, D.PARENTS, "engineering")
    births, Zr = sim.recipients(cases)
    fresh = sim.read_batch(rawc["hold_site/Q"][0], np.arange(D.NCASE), rawc["theta"], births, Zr, sim.params(D.PRIMARY)[1])
    d = float(np.abs(Vr - fresh[0, 0]).max())
    items["C/fresh/hold_site/sham/case0"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}

    # Q5
    alias = {}
    for r in D.PANELS["D"]["regimes"]:
        raw, conds = rawf("D", r), [c.name for c in D.COND_D]
        alias[f"D/{r}/clamp_site(reference)=hold(sham)"] = all(
            np.array_equal(raw["clamp_site/V"][conds.index(c)], raw["hold_site/V"][0]) and
            np.array_equal(raw["clamp_site/Q"][conds.index(c)], raw["hold_site/Q"][0]) for c in conds if c.startswith("reference"))
        for lvl in ("site", "region", "sheet"):
            alias[f"D/{r}/clamp_{lvl}=hold(R intact)"] = all(
                np.array_equal(raw[f"clamp_{lvl}/V"][conds.index(c)], raw["hold_site/V"][conds.index(c)]) for c in ("sham", "body-collective-2"))
        alias[f"D/{r}/dual_vote=hold(records agree)"] = all(
            np.array_equal(raw[f"dual_vote/{f}"][conds.index(c)], raw[f"hold_site/{f}"][conds.index(c)])
            for c in ("sham", "body-collective-2") for f in ("V", "R", "Q"))
        for band in ("regional", "collective"):
            alias[f"D/{r}/one-record arms ignore the second record's injury ({band})"] = all(
                np.array_equal(raw[f"{a}/V"][conds.index(f"reference2-{band}-2")], raw[f"{a}/V"][conds.index(f"reference-{band}-2")])
                for a in ("hold_site", "clamp_region", "arbiter"))
    for p in ("A", "B", "C"):
        for r in D.PANELS[p]["regimes"]:
            raw, e = rawf(p, r), shard(p, r)
            conds = D.PANELS[p]["conditions"]
            never = [i for i, c in enumerate(conds) if not any(ev.kind == "damage" and ev.target == "reference" for ev in c.events)
                     and not any(ev.kind == "impose" and ev.duration == 0 for ev in c.events)]
            alias[f"{p}/{r}/oracle=hold(no burst)"] = all(np.array_equal(raw["oracle/V"][i], raw["hold_site/V"][i]) for i in never)
            for arm in D.PANELS[p]["arms"]:
                if arm.control != "arbiter":
                    continue
                quiet = e[f"{arm.name}/a_bursts"] == 0
                alias[f"{p}/{r}/{arm.name}=hold(no burst)"] = bool(np.array_equal(raw[f"{arm.name}/V"][quiet], raw["hold_site/V"][quiet]))
    raw = rawf("C", D.PRIMARY)
    alias["C/hold_R=copy_post"] = bool(np.array_equal(raw["hold_site/R"], raw["copy_post/packet"]))
    for p in ("B", "D", "E"):
        for r in D.PANELS[p]["regimes"]:
            if r not in D.PANELS["C"]["regimes"]:
                continue
            x, y = rawf(p, r), rawf("C", r)
            shared = [c.name for c in D.PANELS[p]["conditions"] if c.name in [d.name for d in D.COND_C]]
            for arm in ("inactive", "hold_site", "hold_region", "hold_sheet"):
                if arm not in D.ARM[p]:
                    continue
                alias[f"{p}=C/{r}/{arm}"] = all(np.array_equal(x[f"{arm}/{f}"][cidx(p, c)], y[f"{arm}/{f}"][cidx("C", c)])
                                                for c in shared for f in ("V", "Q"))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": len(alias),
                                  "failed": [k for k, v in alias.items() if not v][:10]}

    # Q6
    bad = []
    for p, r in D.tasks():
        raw, e = rawf(p, r), shard(p, r)
        T = raw["targets"]
        if p == "F":
            for arm in D.PANELS["F"]["arms"]:
                V = raw[f"{arm.name}/V"]
                Tb = np.broadcast_to(T, V.shape)
                got = sim.body_endpoints(V.reshape(-1, 16, 16), Tb.reshape(-1, 16, 16), "v")
                got["p_sign"] = ((raw[f"{arm.name}/packet"] > 0) == (Tb > 0)).mean((-2, -1)).reshape(-1)
                bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(e[f"{arm.name}/{k}"].shape), e[f"{arm.name}/{k}"])]
            continue
        nc = len(D.PANELS[p]["conditions"])
        Tb = np.tile(T, (nc, 1, 1))
        cases = enrol([lo], D.MESSAGES, D.PARENTS, "engineering")
        births, Zr = sim.recipients(cases)
        idx = np.tile(np.arange(D.NCASE), nc)
        pr = sim.params(r)[1]
        for j, arm in enumerate(D.PANELS[p]["arms"]):
            got = sim.body_endpoints(raw[f"{arm.name}/V"].reshape(-1, 16, 16), Tb, "v")
            got.update(sim.body_endpoints(raw[f"{arm.name}/e20"].reshape(-1, 16, 16), Tb, "e20"))
            got["r_sign"] = ((raw[f"{arm.name}/R"].reshape(-1, 16, 16) > 0) == (Tb > 0)).mean((-2, -1))
            if j in (0, len(D.PANELS[p]["arms"]) - 1):         # re-read the packets of two arms per task
                for pk in arm.packets:
                    P = raw[f"{arm.name}/{pk}"].reshape(-1, 16, 16)
                    got.update(sim.fresh_endpoints(sim.read_batch(P, idx, raw["theta"], births, Zr, pr), Tb, f"f{pk}"))
            bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), e[f"{arm.name}/{k}"])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    # Q7, Q8
    reader, ok8, efficacy = {}, True, {}
    for p in ("A", "B", "C", "D", "E"):
        for r in D.PANELS[p]["regimes"]:
            es = [shard(p, r, b) for b in range(lo, hi)]
            m = lambda k: float(np.mean([x[k].mean() for x in es]))
            row = {"target_fP_sign": m("target/fP_sign"), "zero_fP_sign": m("zero/fP_sign"), "target_fP_qual": m("target/fP_qual")}
            primary = p == "C" and r == D.PRIMARY
            row["pass"] = row["target_fP_sign"] - row["zero_fP_sign"] >= 0.15 and (
                not primary or (row["target_fP_sign"] >= 0.75 and row["target_fP_qual"] >= 0.65))
            reader[f"{p}/{r}"] = row
            for x in es:
                for ci, cond in enumerate(D.PANELS[p]["conditions"]):
                    dmg = [ev for ev in cond.events if ev.kind == "damage"]
                    for s in range(2):
                        v = x.get(f"damage/slot{s}_v_rms")
                        if v is None:
                            continue
                        want_v = s < len(dmg) and dmg[s].target in ("body", "both")
                        want_r = s < len(dmg) and dmg[s].target in ("reference", "both", "reference2")
                        want_r2 = s < len(dmg) and dmg[s].target == "reference2"
                        rr, rr2 = x[f"damage/slot{s}_r_rms"][ci], x[f"damage/slot{s}_r2_rms"][ci]
                        ok8 &= bool((v[ci] > 0).all() if want_v else (v[ci] == 0).all())
                        ok8 &= bool((rr > 0).all() if want_r else (rr == 0).all())
                        ok8 &= bool((rr2 > 0).all() if want_r2 else (rr2 == 0).all())
    for r in D.PANELS["A"]["regimes"]:
        raw = rawf("A", r)
        i = cidx("A", "impose-inf")
        frac = float(((raw["inactive/e20"][i] > 0) == (raw["foreign"] > 0)).mean())
        efficacy[f"A/{r}/imposed_sign_at_e20"] = frac
        ok8 &= frac >= 0.99
    es = [shard("C", D.PRIMARY, b) for b in range(lo, hi)]
    level = lambda ep, ci: float(np.mean([x[f"hold_site/{ep}"][ci].mean() for x in es]))
    for loc in ("body", "reference"):
        drops = {band: max(level(ep, 0) - level(ep, cidx("C", f"{loc}-{band}-2")) for ep in ("v_qual", "fQ_qual"))
                 for band in D.BANDS}
        efficacy[loc] = drops
        ok8 &= max(drops.values()) >= 0.02
    primary_ok = reader[f"C/{D.PRIMARY}"]["pass"]
    for key, row in reader.items():
        if not row["pass"] and key != f"C/{D.PRIMARY}":
            flags.append(f"reader below threshold in {key}: successor endpoints reported as reader-unqualified")
    checks["Q7_known_reference_reader"] = {"pass": primary_ok, "regimes": reader}
    checks["Q8_perturbation_efficacy"] = {"pass": ok8, "efficacy": efficacy}

    # Q9
    walls = {}
    for key, t in manifest["tasks"].items():
        walls.setdefault(key.split("/")[0], []).append(t["wall_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu_forecast = sum(np.mean(walls[p]) * len(D.PANELS[p]["regimes"]) * n_dev for p in walls)
    longest = max(max(v) for v in walls.values())
    forecast_h = (cpu_forecast / WORKERS * 1.15 + longest) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task_bytes = manifest["bytes_written"] / len(manifest["tasks"])
    n_tasks = len(D.tasks()) * n_dev
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 24 and rss <= 0.8 * avail and per_task_bytes * n_tasks <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu_forecast / 3600, 2),
                              "workers": WORKERS, "task_wall_s_max": longest,
                              "task_wall_s_mean_by_panel": {p: round(float(np.mean(v)), 1) for p, v in walls.items()},
                              "rss_workers_gb": round(rss / 2 ** 30, 2), "mem_available_gb": round(avail / 2 ** 30, 1),
                              "forecast_dev_gb": round(per_task_bytes * n_tasks / 2 ** 30, 1), "disk_free_tb": round(free / 2 ** 40, 1)}

    # Q10
    out = root / "analysis_dry_run"
    proc = subprocess.run([sys.executable, "-m", "me002.analyze", "--root", str(root), "--stage", "preflight",
                           "--out", str(out)] + ([] if a.blocks is None else ["--blocks", a.blocks]),
                          cwd=LANE, capture_output=True, text=True)
    expected = [out / f"contrasts_{p}_{ep}.csv" for p in D.PANELS if p != "F" for ep in D.PRIMARY_ENDPOINTS[p]]
    expected += [out / "contrasts_F.csv", out / "summary.json", out / "predictions_scored.json"]
    verdicts = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and all(q.exists() for q in expected)
                                    and set(verdicts) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "returncode": proc.returncode, "stderr_tail": proc.stderr[-800:],
                                    "largest_git_file_bytes": max(sizes.values(), default=None), "sizes": sizes}

    failed = [k for k, v in checks.items() if not v["pass"]]
    status = "FAIL" if failed else ("PASS_WITH_FLAGS" if flags else "PASS")
    receipt = {"status": status, "failed": failed, "flags": flags, "design_digest": D.digest(),
               "preflight_root": str(root), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "numpy": np.__version__, "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": status, "failed": failed, "flags": flags}, indent=1))


if __name__ == "__main__":
    main()
