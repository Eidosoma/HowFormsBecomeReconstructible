"""One (panel, regime, block) task: acquisition, every arm and condition (or every chain), every
fresh reading. Inputs are public block addresses and frozen settings only. All arms of a case share
the acquired state, the onset, the injury fields and the future draws; recipients share their
births and draws across every packet. Targets, condition labels and schedules reach only the
scoring code, the clamps' protected backups and the privileged oracle. Writes an endpoint shard
and a raw-state shard, each atomically, then a completion record.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from mse import score
from mse.assay import REFERENCE_BOUND, birth
from mse.engine import Ledger, State
from mse.native import NATIVE, address
from mse.ops import block_projection

from . import design as D
from . import sim
from .policies import Arbiter2, Gain, Oracle2, Schedule, first20, periodic


def thresholds(arm, name, window, calib, newborn=False):
    if newborn:
        src = calib["newborn"][name]
        key = str(arm.latch)
        return src["mismatch_traj"][arm.trigger][key], src["surprise_traj"][key]
    src = calib["regimes"][name] if arm.thresholds == "regime" else calib["pooled"][D.pool_key(name)]
    tm = src["mismatch_traj"][arm.trigger][str(arm.mismatch_window or window)]
    ts = src["surprise_update"]["1000"] if arm.surprise == "update" else src["surprise_traj"][str(window)]
    return tm, ts


def controller(arm, n, name, window, calib, schedule=None, newborn=False):
    c = arm.control
    if c in ("inactive", "hold", "native"):
        return None
    if c == "burst0":
        return Schedule(first20)
    if c == "periodic":
        return Schedule(periodic(D.PERIOD))
    if c == "matched":
        return Gain(calib["gains"][name][arm.name] * NATIVE.gain)
    if c == "oracle":
        return Oracle2(schedule)
    if c == "arbiter":
        tm, ts = thresholds(arm, name, window, calib, newborn)
        return Arbiter2(n, tm, ts, arm.trigger, arm.latch, arm.abort, latch0=arm.latch if newborn else 0)
    raise ValueError(c)


def backup(R, level):
    return R.copy() if level == "site" else block_projection(R, sim.CLAMP_SIZE[level])


def telemetry(ctl, first_event, last_event, L):
    out = {"a_bursts": ctl.bursts, "a_first": ctl.first, "a_after": ctl.first_after(first_event),
           "a_after2": ctl.first_after(last_event)}
    out["a_win20"] = ((out["a_after"] >= 0) & (out["a_after"] < D.BURST_UPDATES)).astype(float)
    if isinstance(ctl, Arbiter2):
        out["a_latched"] = ctl.latched / L
        out["a_aborts"] = ctl.aborts
    return out


def tiled(s0, nc):
    t = lambda x: np.tile(x, (nc, 1, 1))
    return State(t(s0.V), t(s0.ema), t(s0.R), np.zeros((nc * len(s0.V), 16, 16)))


def window_task(panel, name, block, purpose, calib):
    spec = D.PANELS[panel]
    L, conds = spec["window"], spec["conditions"]
    cases, s0, th, p, T, Tf = sim.prepare(name, [block], purpose)
    k, nc = len(cases), len(conds)
    n = nc * k
    idx = np.tile(np.arange(k), nc)
    tau = sim.onsets(cases, spec["onset"])
    taub = np.tile(tau, nc)
    lastb = taub + np.concatenate([np.full(k, max([e.delay for e in c.events], default=0)) for c in conds])
    prog = sim.condition_program(conds, cases, tau, Tf, L)
    Zf = sim.draws(cases, "future", updates=L)
    births, Zr = sim.recipients(cases)
    Tb, Tfb, thb = T[idx], Tf[idx], th[idx]
    ends, raw, timing = {}, {}, {}

    def put(key, values, rows=nc):
        for kk, v in values.items():
            ends[f"{key}/{kk}"] = np.asarray(v, dtype=float).reshape(rows, k)

    put("acq", sim.body_endpoints(s0.V, T, "v0"), 1)
    put("acq", {"r_sign": score.sign_agreement(s0.R, T), "r_margin": (np.sign(T) * s0.R).mean((-2, -1))}, 1)
    raw.update({"s0/V": s0.V, "s0/R": s0.R, "s0/ema": s0.ema, "theta": th, "targets": T, "foreign": Tf,
                "tau": tau})
    base = tiled(s0, nc)
    rms = lambda x: np.sqrt((x ** 2).mean((-2, -1)))
    for j, (time_, dV, dR, dR2) in enumerate(prog.slots):
        put("damage", {f"slot{j}_v_rms": rms(dV) if dV is not None else np.zeros(n),
                       f"slot{j}_r_rms": rms(dR) if dR is not None else np.zeros(n),
                       f"slot{j}_r2_rms": rms(dR2) if dR2 is not None else np.zeros(n),
                       f"slot{j}_time": time_})
    sentinels = {e: taub + e - 1 for e in D.EARLY}
    for arm in spec["arms"]:
        t1 = time.time()
        sched = sim.oracle_schedule(conds, tau, k, L) if arm.control == "oracle" else None
        ctl = controller(arm, n, name, L, calib, sched)
        ledger = Ledger.zeros(n)
        clamp = (arm.clamp, backup(base.R, arm.clamp)) if arm.clamp else None
        two = arm.copies == 2
        extra = {}
        end, early, clamp_l1 = sim.simulate(base, thb, Zf, idx, p, L, sim.route(arm), ctl, prog, clamp, sentinels, ledger,
                                            copy2=base.R.copy() if two else None, out=extra)
        put(arm.name, sim.body_endpoints(end.V, Tb, "v"))
        if two:
            put(arm.name, {"r2_sign": score.sign_agreement(extra["R2"], Tb)})
            raw[f"{arm.name}/R2"] = extra["R2"].reshape(nc, k, 16, 16)
        for e in D.EARLY:
            put(arm.name, sim.body_endpoints(early[e], Tb, f"e{e}"))
        put(arm.name, {"r_sign": score.sign_agreement(end.R, Tb), "r_margin": (np.sign(Tb) * end.R).mean((-2, -1)),
                       "q_sign": score.sign_agreement(end.Q, Tb), "q_margin": (np.sign(Tb) * end.Q).mean((-2, -1)),
                       "d_body_l1": ledger.body_l1, "d_ref_l1": ledger.ref_l1, "d_clamp_l1": clamp_l1,
                       "d_messages": np.full(n, ledger.messages / ledger.updates)})
        if panel == "A":
            put(arm.name, {"rg_sign": score.sign_agreement(end.R, Tfb), "qg_sign": score.sign_agreement(end.Q, Tfb)})
            put(arm.name, {k2.replace("v_", "vg_"): v for k2, v in sim.body_endpoints(end.V, Tfb, "v").items()})
        if ctl is not None and hasattr(ctl, "bursts"):
            put(arm.name, telemetry(ctl, taub, lastb, L))
        for pk in arm.packets:
            P = end.Q if pk == "Q" else end.R
            F = sim.read_batch(P, idx, th, births, Zr, p)
            put(arm.name, sim.fresh_endpoints(F, Tb, f"f{pk}"))
            if panel == "A":
                put(arm.name, sim.fresh_endpoints(F, Tfb, f"g{pk}"))
        shape = (nc, k, 16, 16)
        raw.update({f"{arm.name}/V": end.V.reshape(shape), f"{arm.name}/R": end.R.reshape(shape),
                    f"{arm.name}/Q": end.Q.reshape(shape)})
        for e in D.EARLY:
            raw[f"{arm.name}/e{e}"] = early[e].reshape(shape)
        timing[arm.name] = round(time.time() - t1, 3)
    once = {"protected": s0.R, "backup_region": backup(s0.R, "region"), "backup_sheet": backup(s0.R, "sheet"),
            "target": T, "foreign_target": Tf, "zero": np.zeros_like(T)}
    for pk in spec["packets"]:
        t1 = time.time()
        if pk == "copy_post":
            _, P = prog.apply(1, base.V, base.R)       # start onset: the post-injury R of every branch
            rows, pidx = nc, idx
        else:
            P, rows, pidx = once[pk], 1, np.arange(k)
        F = sim.read_batch(P, pidx, th, births, Zr, p)
        put(pk, sim.fresh_endpoints(F, T[pidx], "fP"), rows)
        if panel == "A":
            put(pk, sim.fresh_endpoints(F, Tf[pidx], "gP"), rows)
        raw[f"{pk}/packet"] = P.reshape(rows, k, 16, 16)
        timing[pk] = round(time.time() - t1, 3)
    return ends, raw, timing, cases


def generation_program(cases, g, L):
    """Env-major program for one generation: none, reference, mixed. Onset, band and location are
    addressed by (case, 'gen', g, ...) and shared across arms and environments."""
    k = len(cases)
    n = len(D.ENVIRONMENTS) * k
    tau = np.array([int(address(D.TAG, *c.key(), "gen", g, "onset").integers(*D.GEN_ONSET)) for c in cases])
    band = [D.BANDS[int(address(D.TAG, *c.key(), "gen", g, "band").integers(3))] for c in cases]
    u = np.array([float(address(D.TAG, *c.key(), "gen", g, "loc").random()) for c in cases])
    edges = np.cumsum([w for _, w in D.MIX])
    loc = [D.MIX[int(np.searchsorted(edges, x, side="right"))][0] for x in u]
    field = lambda target: np.stack([sim.band_field([c], target, b, 2.0, "gen", g)[0] for c, b in zip(cases, band)])
    fb, fr = field("body"), field("reference")
    time_, dV, dR = np.full(n, -1), np.zeros((n, 16, 16)), np.zeros((n, 16, 16))
    for e, env in enumerate(D.ENVIRONMENTS):
        sl = slice(e * k, (e + 1) * k)
        if env == "none":
            continue
        time_[sl] = tau
        if env == "reference":
            dR[sl] = fr
        else:
            on_body = np.array([x in ("body", "both") for x in loc])[:, None, None]
            on_ref = np.array([x in ("reference", "both") for x in loc])[:, None, None]
            dV[sl], dR[sl] = np.where(on_body, fb, 0.0), np.where(on_ref, fr, 0.0)
    prog = sim.Program(n)
    prog.slots.append((time_, dV, dR, None))
    return prog, tau, band, loc


def chain_task(name, block, purpose, calib):
    spec = D.PANELS["F"]
    L, G = spec["window"], spec["generations"]
    cases, s0, th, p, T, Tf = sim.prepare(name, [block], purpose)
    k, ne = len(cases), len(D.ENVIRONMENTS)
    n = ne * k
    idx = np.tile(np.arange(k), ne)
    Tb, thb = T[idx], th[idx]
    germ = {"site": np.tile(s0.R, (ne, 1, 1)), "region": np.tile(backup(s0.R, "region"), (ne, 1, 1))}
    ends, raw, timing = {}, {}, {a.name: 0.0 for a in spec["arms"]}
    rec = {a.name: {} for a in spec["arms"]}
    packets, bodies, sent = {}, {a.name: [] for a in spec["arms"]}, {a.name: [] for a in spec["arms"]}
    sched = {"tau": [], "band": [], "loc": []}
    raw.update({"s0/V": s0.V, "s0/R": s0.R, "s0/ema": s0.ema, "theta": th, "targets": T})
    for g in range(G + 1):
        Z = sim.draws(cases, "gen", g, "life", updates=L)
        prog, tau, band, loc = generation_program(cases, g, L)
        sched["tau"].append(tau)
        sched["band"].append([D.BANDS.index(b) for b in band])
        sched["loc"].append([[x for x, _ in D.MIX].index(x) for x in loc])
        newborn = birth(D.TAG, cases, "gen", g, "birth")[idx] if g else None
        for arm in spec["arms"]:
            t1 = time.time()
            if g == 0:
                s = tiled(s0, ne)
            else:
                R_in = germ[arm.germline] if arm.germline else packets[arm.name]
                s = State(newborn.copy(), newborn.copy(), R_in.copy(), np.zeros((n, 16, 16)))
            ctl = controller(arm, n, name, L, calib, newborn=g > 0)
            ledger = Ledger.zeros(n)
            end, _, _ = sim.simulate(s, thb, Z, idx, p, L, sim.route(arm), ctl, prog, ledger=ledger)
            pk = arm.packets[0]
            out = germ[arm.germline] if pk == "germline" else (end.Q if pk == "Q" else end.R)
            packets[arm.name] = out.copy()
            r = rec[arm.name]
            vals = {**sim.body_endpoints(end.V, Tb, "v"), "p_sign": score.sign_agreement(out, Tb),
                    "p_margin": (np.sign(Tb) * out).mean((-2, -1)), "r_sign": score.sign_agreement(end.R, Tb),
                    "q_sign": score.sign_agreement(end.Q, Tb), "d_body_l1": ledger.body_l1, "d_ref_l1": ledger.ref_l1}
            if isinstance(ctl, Arbiter2):
                tb = np.tile(tau, ne)
                vals.update({"a_bursts": ctl.bursts, "a_after": ctl.first_after(tb), "a_latched": ctl.latched / L})
            for kk, v in vals.items():
                r.setdefault(kk, []).append(np.asarray(v, float).reshape(ne, k))
            bodies[arm.name].append(end.V.reshape(ne, k, 16, 16))
            sent[arm.name].append(out.reshape(ne, k, 16, 16))
            timing[arm.name] += time.time() - t1
    for a, r in rec.items():
        for kk, v in r.items():
            ends[f"{a}/{kk}"] = np.stack(v)                 # (generations + 1, environments, cases)
        raw[f"{a}/V"] = np.stack(bodies[a])
        raw[f"{a}/packet"] = np.stack(sent[a])
    raw.update({f"schedule/{kk}": np.array(v) for kk, v in sched.items()})
    timing = {kk: round(v, 3) for kk, v in timing.items()}
    return ends, raw, timing, cases


def run_task(panel, name, block, purpose, calib, root):
    """Everything for one panel, regime and source block; returns the completion record."""
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    task = chain_task(name, block, purpose, calib) if panel == "F" else window_task(panel, name, block, purpose, calib)
    ends, raw, timing, cases = task
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating)
               and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {panel} {name} {block}: {bad[:5]}")
    meta = {"panel": panel, "regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(),
            "calibration_digest": calib.get("design_digest"), "numpy": np.__version__, "timing_s": timing,
            "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / panel / name
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"panel": panel, "regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
              "pid": os.getpid(), "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / panel / name / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
