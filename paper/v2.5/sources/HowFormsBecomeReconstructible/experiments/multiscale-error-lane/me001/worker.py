"""One (regime, block) task: acquisition, damage, every arm and every fresh reading.

Inputs are public block addresses and frozen settings only. All arms of a case share the
acquired state, the injury fields and the future draws; recipients share their births and
draws across every packet. The controller sees V-tilde, ema and R (mse.engine); targets,
condition labels and masks reach only the scoring code below and the privileged oracle.
Writes an endpoint shard and a raw-state shard, each atomically.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from mse import score
from mse.assay import Noise, acquire, band_damage, birth, enrol, injure, templates
from mse.engine import ROUTES, Channel, Ledger, Route, State, run
from mse.native import NATIVE, address, half_plane
from mse.ops import Op, bands

from . import design as D
from .policies import FEATURES, Arbiter, Oracle, Tap, burst

READ_ROUTE = Route(reference=None, capture=None)
OFF_ROUTE = Route(body=None, reference=None, capture=None)
NCASE = len(D.MESSAGES) * len(D.PARENTS)


def params(name):
    family, sigma = D.REGIMES[name]
    return D.FAMILIES[family], replace(NATIVE, sigma=sigma)


def channel(spec):
    if spec is None:
        return None
    sl, so, al, ao, decision = spec
    perm = D.PERMUTATIONS[sl] if decision == "permute" else None
    return Channel(Op(sl, tuple(so)), Op(al, tuple(ao)), decision, 0.0, perm)


def route(seg, capture):
    return Route(body=channel(seg.body), reference=channel(seg.reference), capture=capture)


def prepare(name, blocks, purpose):
    """Acquired, released, pre-damage state with Q = 0; theta and targets per case."""
    shift, p = params(name)
    cases = enrol(blocks, D.MESSAGES, D.PARENTS, purpose)
    s, th = acquire(D.TAG, cases, D.SETTLE, D.TEACH, D.AMPLITUDE, p, shift, per_tissue=D.PER_TISSUE_THETA)
    taught_R = s.R.copy()
    s = run(s, th, Noise(D.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return cases, State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, p, shift, taught_R


def draws(cases, *stream, updates):
    """Standard normals shaped (updates, cases, 16, 16) from each case's addressed stream."""
    return np.stack([address(D.TAG, *c.key(), *stream).standard_normal((updates, 16, 16)) for c in cases], 1)


def recipients(cases):
    births = np.stack([birth(D.TAG, cases, "recipient", r, "birth") for r in range(D.RECIPIENTS)], 1)
    Z = np.stack([draws(cases, "recipient", r, "read", updates=D.READ_UPDATES) for r in range(D.RECIPIENTS)], 2)
    return births, Z


def read_batch(packets, idx, th, births, Z, p, rt=READ_ROUTE):
    """Fresh recipients hold each packet as their reference (assay.read, batched by case index)."""
    n, k = len(packets), D.RECIPIENTS
    V = births[idx].reshape(n * k, 16, 16)
    s = State(V, V.copy(), np.repeat(packets, k, axis=0), np.zeros_like(V))
    s = run(s, np.repeat(th[idx], k, axis=0), lambda t: Z[t - 1][idx].reshape(n * k, 16, 16), rt,
            D.READ_UPDATES, p)
    return s.V.reshape(n, k, 16, 16)


def edges(T):
    s = T > 0
    e = np.zeros_like(s)
    for shift, axis in ((1, -2), (-1, -2), (1, -1), (-1, -1)):
        e |= s != np.roll(s, shift, axis)
    return e


def body_endpoints(V, T, edge, prefix):
    m, a = (V > 0) == (T > 0), np.abs(V) > score.ELIGIBLE
    out = {"sign": m.mean((-2, -1)), "amp": a.mean((-2, -1)), "qual": (m & a).mean((-2, -1)),
           "margin": (np.sign(T) * V).mean((-2, -1)), "mean": V.mean((-2, -1)),
           "sign_boundary": (m & edge).sum((-2, -1)) / edge.sum((-2, -1)),
           "sign_interior": (m & ~edge).sum((-2, -1)) / (~edge).sum((-2, -1))}
    out.update({f"err_{k}": v for k, v in score.band_errors(V, T).items()})
    return {f"{prefix}_{k}": v for k, v in out.items()}


def fresh_endpoints(F, T, templ, own, prefix="f"):
    Tt = T[:, None]
    m, a = (F > 0) == (Tt > 0), np.abs(F) > score.ELIGIBLE
    out = {"sign": m.mean((-2, -1)), "amp": a.mean((-2, -1)), "qual": (m & a).mean((-2, -1)),
           "margin": (np.sign(Tt) * F).mean((-2, -1))}
    if prefix == "f":
        out["rec"] = score.recognition(F, templ, own[:, None].repeat(F.shape[1], 1))
        out.update({f"err_{k}": v for k, v in score.band_errors(F, Tt).items()})
        j = score.joint(F, Tt) / 256.0
        out.update({"j00": j[..., 0, 0], "j01": j[..., 0, 1], "j10": j[..., 1, 0], "j11": j[..., 1, 1]})
    return {f"{prefix}_{k}": v.mean(1) for k, v in out.items()}


def damage_record(s0, start):
    dV, dR = start.V - s0.V, start.R - s0.R
    out = {"v_rms": np.sqrt((dV ** 2).mean((-2, -1))), "r_rms": np.sqrt((dR ** 2).mean((-2, -1))),
           "v_mean_shift": dV.mean((-2, -1)), "v_mean_start": start.V.mean((-2, -1)),
           "v_flips": ((start.V > 0) != (s0.V > 0)).mean((-2, -1)),
           "r_flips": ((start.R > 0) != (s0.R > 0)).mean((-2, -1)),
           "v_at_bound": (np.abs(start.V) >= NATIVE.bound).mean((-2, -1)),
           "r_at_bound": (np.abs(start.R) >= NATIVE.bound).mean((-2, -1)),
           "v_extreme": np.abs(dV).max((-2, -1)), "r_extreme": np.abs(dR).max((-2, -1))}
    for k, v in bands(dV).items():
        out[f"v_band_{k}"] = (v ** 2).mean((-2, -1))
    for k, v in bands(dR).items():
        out[f"r_band_{k}"] = (v ** 2).mean((-2, -1))
    return out


def run_arm(arm, starts, conds, th, Zf, p, thresholds):
    n = len(conds) * NCASE
    idx = np.tile(np.arange(NCASE), len(conds))
    cat = lambda f: np.concatenate([getattr(starts[c], f) for c in conds])
    s = State(cat("V"), cat("ema"), cat("R"), np.zeros((n, 16, 16)))
    if arm.capture == "snapshot":
        s.snapshot = s.V.copy()
    theta = th[idx]
    ledger = Ledger.zeros(n)
    kinds = {seg.policy for seg in arm.segments}
    inner = None
    if "arbiter" in kinds or "changepoint" in kinds:
        inner = Arbiter(n, thresholds["mismatch"], thresholds["surprise"], latch="arbiter" in kinds)
    elif "oracle" in kinds:
        inner = Oracle(np.repeat([D.CONDITIONS[c][0] == "reference" for c in conds], NCASE))
    tap = Tap(n, p=p) if arm.traced else None
    early, t0 = {}, 0
    for seg in arm.segments:
        seg_inner = burst if seg.policy == "burst" else (inner if seg.policy else None)
        if tap is not None:
            tap.inner = seg_inner
        policy = tap if tap is not None else seg_inner

        def rec(t, st, o=t0):
            if t > 0 and o + t in D.EARLY:
                early[o + t] = st.V.copy()
        s = run(s, theta, lambda t, o=t0: Zf[o + t - 1][idx], route(seg, arm.capture), seg.updates, p,
                ledger=ledger, every=1, record=rec, policy=policy)
        t0 += seg.updates
    assert t0 == D.WINDOW and set(early) == set(D.EARLY)
    return s, ledger, early, tap, inner


def run_task(name, block, purpose, thresholds, root):
    """Everything for one regime and one source block; returns the completion record."""
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    cases, s0, th, p, shift, taught_R = prepare(name, [block], purpose)
    T = templates(cases, D.AMPLITUDE, shift)
    edge = edges(T)
    templ = np.stack([np.roll(half_plane(k, D.AMPLITUDE), shift, axis=(0, 1)) for k in range(4)])
    own = np.array([c.message for c in cases])
    foreign = np.array([cases.index(next(c2 for c2 in cases if c2.parent == c.parent and c2.message == D.FOREIGN[c.message]))
                        for c in cases])
    Zf = draws(cases, "future", updates=D.WINDOW)
    births, Zr = recipients(cases)
    ends, raw, timing = {}, {}, {}

    def put(key, values, n_cond):
        for k, v in values.items():
            ends[f"{key}/{k}"] = np.asarray(v, dtype=float).reshape(n_cond, NCASE)

    ends.update({f"acq/{k}": v[None] for k, v in body_endpoints(s0.V, T, edge, "v0").items()})
    ends["acq/taught_r_sign"] = score.sign_agreement(taught_R, T)[None]
    ends["acq/r_sign"] = score.sign_agreement(s0.R, T)[None]
    ends["acq/r_margin"] = (np.sign(T) * s0.R).mean((-2, -1))[None]
    raw.update({"s0/V": s0.V, "s0/R": s0.R, "s0/ema": s0.ema, "theta": th, "targets": T})

    starts = []
    for loc, band, rms in D.CONDITIONS:
        bd = band_damage(D.TAG, cases, "body", band, rms) if loc in ("body", "both") else None
        rd = band_damage(D.TAG, cases, "reference", band, rms) if loc in ("reference", "both") else None
        starts.append(injure(s0, bd, rd))
    records = [damage_record(s0, st) for st in starts]
    for k in records[0]:
        ends[f"damage/{k}"] = np.stack([r[k] for r in records])

    for arm in D.ARMS:
        t1 = time.time()
        conds = D.arm_conditions(arm)
        nc = len(conds)
        idx = np.tile(np.arange(NCASE), nc)
        end, ledger, early, tap, inner = run_arm(arm, starts, conds, th, Zf, p, thresholds)
        Tb, eb = T[idx], edge[idx]
        put(arm.name, body_endpoints(end.V, Tb, eb, "v1000"), nc)
        for t in D.EARLY:
            put(arm.name, body_endpoints(early[t], Tb, eb, f"v{t}"), nc)
        put(arm.name, {"r_sign": score.sign_agreement(end.R, Tb), "r_margin": (np.sign(Tb) * end.R).mean((-2, -1)),
                       "q_sign": score.sign_agreement(end.Q, Tb), "q_margin": (np.sign(Tb) * end.Q).mean((-2, -1))}, nc)
        put(arm.name, {f"d_{k}": getattr(ledger, k) for k in ("body_l1", "body_l2", "body_sites", "ref_l1", "ref_l2")}, nc)
        ends[f"{arm.name}/d_messages_per_update"] = np.full((nc, NCASE), ledger.messages / ledger.updates)
        if inner is not None:
            put(arm.name, {"a_bursts": inner.bursts, "a_first": inner.first}, nc)
        if tap is not None:
            put(arm.name, {f"tr_{f}_{t}": tap.trace[i, j] for i, t in enumerate(D.TRACE_TIMES)
                           for j, f in enumerate(FEATURES)}, nc)
            put(arm.name, {f"mx_{f}": tap.maximum[j] for j, f in enumerate(FEATURES)}, nc)
        fresh = read_batch(end.Q, idx, th, births, Zr, p)
        put(arm.name, fresh_endpoints(fresh, Tb, templ, own[idx]), nc)
        shape = (nc, NCASE, 16, 16)
        raw.update({f"{arm.name}/V": end.V.reshape(shape), f"{arm.name}/R": end.R.reshape(shape),
                    f"{arm.name}/Q": end.Q.reshape(shape), f"{arm.name}/fresh": fresh.reshape(nc, NCASE, -1, 16, 16)})
        for t in D.EARLY:
            raw[f"{arm.name}/V{t}"] = early[t].reshape(shape)
        if arm.foreign:
            fidx = (np.arange(nc)[:, None] * NCASE + foreign[None, :]).ravel()
            xf = read_batch(end.Q[fidx], idx, th, births, Zr, p)
            put(arm.name, fresh_endpoints(xf, Tb, templ, own[idx], "x"), nc)
            raw[f"{arm.name}/foreign_fresh"] = xf.reshape(nc, NCASE, -1, 16, 16)
        timing[arm.name] = round(time.time() - t1, 3)

    packets = {"copy_post": np.stack([st.R for st in starts]), "protected": s0.R[None], "target": T[None],
               "zero": np.zeros_like(T)[None], "off_reader": np.zeros_like(T)[None]}
    for packet, P in packets.items():
        t1 = time.time()
        nc = len(P)
        idx = np.tile(np.arange(NCASE), nc)
        flat = P.reshape(nc * NCASE, 16, 16)
        fresh = read_batch(flat, idx, th, births, Zr, p, OFF_ROUTE if packet == "off_reader" else READ_ROUTE)
        put(packet, fresh_endpoints(fresh, T[idx], templ, own[idx]), nc)
        raw[f"{packet}/fresh"] = fresh.reshape(nc, NCASE, -1, 16, 16)
        if packet in D.FOREIGN_PACKETS:
            fidx = (np.arange(nc)[:, None] * NCASE + foreign[None, :]).ravel()
            xf = read_batch(flat[fidx], idx, th, births, Zr, p)
            put(packet, fresh_endpoints(xf, T[idx], templ, own[idx], "x"), nc)
            raw[f"{packet}/foreign_fresh"] = xf.reshape(nc, NCASE, -1, 16, 16)
        timing[packet] = round(time.time() - t1, 3)

    for arrays in (ends, raw):
        bad = [k for k, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating)
               and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {name} {block}: {bad[:5]}")
    meta = {"regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(),
            "thresholds": thresholds, "numpy": np.__version__, "timing_s": timing,
            "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / name
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(), "files": out,
              "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
              "pid": os.getpid(), "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / name / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
