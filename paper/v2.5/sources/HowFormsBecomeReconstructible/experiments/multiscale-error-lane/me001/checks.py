"""Qualification of ME001 v2 on the preflight (engineering) shards; criteria fixed in advance.

python -m me001.checks --root PREFLIGHT_ROOT --cpus LIST   (writes frozen/qualification_receipt.json)

Q1  complete and finite: every task, arm, condition and case present
Q2  serial = parallel: one task rerun in-process gives bit-identical shards
Q3  legacy replay: identity routes and the fresh reader equal legacy blueprint_step bit for bit
Q4  independent replay: a plain per-site loop using the design fixtures (operators.py)
    reproduces acquisition, twelve linear arms and a fresh reading within 1e-9
Q5  aliases exact: reference_r = inactive (V, Q), zero clamp = inactive, snapshot V = body_site V,
    sham start = pre-damage state
Q6  reanalysis: endpoints recomputed from saved states equal the saved endpoints; the fixture's
    offline_scores agree
Q7  known-reference reader: target-packet minus zero-packet fresh sign >= 0.15 in every regime;
    primary regime: target fresh sign >= 0.75 and fresh qualified >= 0.65
Q8  perturbation efficacy: every non-sham condition changes its damaged component in every case and
    leaves the other exactly unchanged; primary regime: at RMS 2, some band reduces body_site's
    v1000_qual or f_qual by >= 0.02 versus sham, for body and for reference damage
Q9  resources: forecast development wall <= 48 h on 12 workers, 12 x peak RSS <= 80% of available
    RAM, forecast bytes <= 80% of free disk
Q10 reader dry run: analyze.py completes on the preflight shards and scores every statement
A secondary-regime failure of Q7 alone gives PASS_WITH_FLAGS (that regime's successor endpoints
are reported as reader-unqualified); any other failure gives FAIL and stops the campaign.
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
from me001 import design as D  # noqa: E402
from me001 import worker as W  # noqa: E402
from mse.assay import band_damage, enrol, injure, spread, templates  # noqa: E402
from mse.engine import State  # noqa: E402
from mse.native import NATIVE, address, center, half_plane, thresholds  # noqa: E402

FROZEN = LANE / "me001" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


# ---------------------------------------------------------------- independent scalar model
def op(level, offset=(0, 0)):
    if level == "site":
        return lambda x: x.copy()
    if tuple(offset) == (0, 0):
        return lambda x: fixture.spatial_operator(x, level)
    return lambda x: fixture.shifted_operator(x, level, offset)


def scalar_channel(spec):
    """Linear channels only, composed literally (actuator after sensor)."""
    if spec is None:
        return None
    sl, so, al, ao, decision = spec
    s, a = op(sl, so), op(al, ao)
    if decision == "linear":
        return lambda d: a(s(d))
    if decision == "reverse":
        return lambda d: -a(s(d))
    if decision == "permute":
        size = {"site": 1, "region": 4, "sheet": 8}[sl]
        n, perm = 16 // size, D.PERMUTATIONS[sl]

        def f(d):
            x = s(d)
            coarse = np.array([[x[i * size, j * size] for j in range(n)] for i in range(n)]).ravel()
            moved = coarse[list(perm)].reshape(n, n)
            return a(np.kron(moved, np.ones((size, size))))
        return f
    raise ValueError(decision)


def scalar_step(V, ema, R, Q, theta, z, p, body, ref, gain, rate, capture=None, snapshot=None):
    """capture: None (Q not written), 'body' or 'snapshot'."""
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
    if capture == "body":
        Q = Q + p.rho * (Vn - Q)
    elif capture == "snapshot":
        Q = Q + p.rho * (snapshot - Q)
    return Vn, ema, R, Q


def scalar_case(regime, case_index):
    """Acquisition, twelve linear arms and one fresh reading for one case, from addresses alone."""
    shift, p = W.params(regime)
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    c = cases[case_index]
    q = replace(p, threshold_spread=spread(D.TAG, BLOCK))
    th = thresholds(address(D.TAG, "theta", BLOCK), q)
    T = np.roll(half_plane(c.message, D.AMPLITUDE), shift, axis=(0, 1))
    V = 0.2 * center(address(D.TAG, *c.key(), "birth").standard_normal((16, 16)))
    ema, R, Q = V.copy(), V.copy(), np.zeros((16, 16))
    site = scalar_channel(D.ch("site"))
    for stream, n in (("settle", D.SETTLE), ("teach", D.TEACH), ("release", D.RELEASE)):
        Z = address(D.TAG, *c.key(), stream).standard_normal((n, 16, 16))
        for t in range(n):
            if stream == "teach":
                V = T.copy()
            V, ema, R, Q = scalar_step(V, ema, R, Q, th, Z[t], p, site,
                                       None if stream == "release" else site, p.gain, p.rho)
    s0 = (V, ema, R)
    Zf = address(D.TAG, *c.key(), "future").standard_normal((D.WINDOW, 16, 16))
    out = {"s0/V": V, "s0/R": R, "arms": {}}
    picks = [("body_site", "both-regional-1"), ("body_region", "both-regional-1"), ("body_sheet", "body-collective-2"),
             ("reciprocal_region", "both-collective-1"), ("reference_sheet", "reference-regional-2"),
             ("place_region_act", "reference-collective-2"), ("place_sheet_sense", "body-regional-2"),
             ("write20_region", "reference-regional-2"), ("wait500_site", "both-fine-2"),
             ("snapshot", "reference-collective-1"), ("reverse_region", "sham"), ("permute_sheet", "body-fine-1")]
    names = [D.condition_name(i) for i in D.FULL]
    for arm_name, cond in picks:
        arm = D.ARM[arm_name]
        loc, band, rms = D.CONDITIONS[names.index(cond)]
        bd = band_damage(D.TAG, [c], "body", band, rms)[0] if loc in ("body", "both") else 0.0
        rd = band_damage(D.TAG, [c], "reference", band, rms)[0] if loc in ("reference", "both") else 0.0
        V, ema, R = np.clip(s0[0] + bd, -2, 2), s0[1].copy(), np.clip(s0[2] + rd, -2, 2)
        Q = np.zeros((16, 16))
        snap = V.copy()
        t = 0
        for seg in arm.segments:
            body, ref = scalar_channel(seg.body), scalar_channel(seg.reference)
            gain, rate = (0.0, D.BURST_RATE) if seg.policy == "burst" else (p.gain, p.rho)
            for _ in range(seg.updates):
                V, ema, R, Q = scalar_step(V, ema, R, Q, th, Zf[t], p, body, ref, gain, rate,
                                           capture=arm.capture, snapshot=snap)
                t += 1
        out["arms"][(arm_name, cond)] = (V, R, Q)
    arm_name, cond = picks[0]
    packet = out["arms"][(arm_name, cond)][2]
    Vr = 0.2 * center(address(D.TAG, *c.key(), "recipient", 0, "birth").standard_normal((16, 16)))
    er, Qr = Vr.copy(), np.zeros((16, 16))
    Zr = address(D.TAG, *c.key(), "recipient", 0, "read").standard_normal((D.READ_UPDATES, 16, 16))
    Rr = packet.copy()
    for t in range(D.READ_UPDATES):
        Vr, er, Rr, Qr = scalar_step(Vr, er, Rr, Qr, th, Zr[t], p, site, None, p.gain, p.rho)
    out["fresh"] = (arm_name, cond, Vr)
    return out


# ---------------------------------------------------------------- legacy replay
class Draws:
    """Supplies the addressed draws to legacy code, which asks its rng once per update."""

    def __init__(self, Z):
        self.Z, self.t = Z, 0

    def standard_normal(self, shape):
        z = self.Z[self.t]
        assert z.shape == tuple(shape)
        self.t += 1
        return z


def legacy_replay(regime, shard_raw):
    sys.dont_write_bytecode = True
    for name in ("voltage_web", "ladder_web", "blueprint_web", "growing_web", "contract_bridge", "glider_test", "xeno_bridge"):
        sys.path.insert(0, str(LEGACY / name / "src"))
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step
    from ladder_web.config import LadderConfig
    from voltage_web.config import VoltageConfig
    shift, p = W.params(regime)
    tissue, ladder = VoltageConfig(sigma=p.sigma), LadderConfig()
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "engineering")
    th = shard_raw["theta"]
    Zf = W.draws(cases, "future", updates=D.WINDOW)
    results = {}
    names = [D.condition_name(i) for i in D.FULL]
    s0V, s0R, s0e = shard_raw["s0/V"], shard_raw["s0/R"], shard_raw["s0/ema"]
    for arm, (c_m, rho) in {"inactive": (0.0, 0.0), "body_site": (None, 0.0), "reference_site": (0.0, None),
                            "reciprocal_site": (None, None)}.items():
        bp = BlueprintConfig() if rho is None else BlueprintConfig(rho=rho)
        for cond in ("sham", "both-regional-2", "reference-collective-1"):
            ci = names.index(cond)
            loc, band, rms = D.CONDITIONS[ci]
            bd = band_damage(D.TAG, cases, "body", band, rms) if loc in ("body", "both") else None
            rd = band_damage(D.TAG, cases, "reference", band, rms) if loc in ("reference", "both") else None
            st = injure(State(s0V, s0e, s0R, np.zeros_like(s0V)), bd, rd)
            V, ema, R, Q = st.V.copy(), st.ema.copy(), st.R.copy(), np.zeros_like(st.V)
            rng = Draws(Zf)
            for _ in range(D.WINDOW):
                V, ema, R = blueprint_step(V, ema, R, th, tissue, ladder, bp, "T", rng, c_m=c_m)
                Q = Q + NATIVE.rho * (V - Q)
            k = D.arm_conditions(D.ARM[arm]).index(ci)
            results[f"{arm}/{cond}"] = all(np.array_equal(x, shard_raw[f"{arm}/{f}"][k]) for x, f in ((V, "V"), (R, "R"), (Q, "Q")))
    births, Zr = W.recipients(cases)
    k = D.FULL.index(0)
    packets = shard_raw["body_site/Q"][k]
    V = births.reshape(-1, 16, 16)
    R = np.repeat(packets, D.RECIPIENTS, axis=0)
    rng = Draws(Zr.reshape(D.READ_UPDATES, -1, 16, 16))
    ema = V.copy()
    for _ in range(D.READ_UPDATES):
        V, ema, R = blueprint_step(V, ema, R, np.repeat(th, D.RECIPIENTS, axis=0), tissue, ladder,
                                   BlueprintConfig(rho=0.0), "T", rng)
    results["fresh_reader/body_site/sham"] = bool(np.array_equal(V.reshape(8, D.RECIPIENTS, 16, 16),
                                                                 shard_raw["body_site/fresh"][k]))
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
    thresholds_frozen = json.loads((FROZEN / "thresholds.json").read_text())["regimes"]
    checks, flags = {}, []
    manifest = json.loads((root / "manifest.json").read_text())

    # Q1
    missing, ok = [], True
    for r in D.REGIMES:
        for b in range(lo, hi):
            e = npz(root / "shards" / r / f"{b}.npz")
            for arm in D.ARMS:
                n = len(D.arm_conditions(arm))
                for ep in ("v1000_qual", "f_qual", "v20_qual", "q_sign", "d_body_l1"):
                    x = e.get(f"{arm.name}/{ep}")
                    if x is None or x.shape != (n, W.NCASE) or not np.isfinite(x).all():
                        missing.append(f"{r}/{b}/{arm.name}/{ep}")
            for pk in D.PACKETS:
                if f"{pk}/f_qual" not in e:
                    missing.append(f"{r}/{b}/{pk}")
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10], "tasks": len(manifest["tasks"])}

    # Q2
    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    W.run_task(D.PRIMARY, lo, "engineering", thresholds_frozen[D.PRIMARY], str(serial))
    same = True
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / D.PRIMARY / f"{lo}.npz"), npz(serial / kind / D.PRIMARY / f"{lo}.npz")
        same &= x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x)
    checks["Q2_serial_equals_parallel"] = {"pass": bool(same), "task": f"{D.PRIMARY}/{lo}"}

    # Q3
    legacy = {}
    for r in (D.PRIMARY, "F2_s0.1"):
        res = legacy_replay(r, npz(root / "raw" / r / f"{lo}.npz"))
        legacy.update({f"{r}/{k}": v for k, v in res.items()})
    checks["Q3_legacy_bit_exact"] = {"pass": all(legacy.values()), "items": legacy}

    # Q4
    worst, items = 0.0, {}
    for r, ci in ((D.PRIMARY, 0), ("F4_s0.1", 5)):
        sc = scalar_case(r, ci)
        raw = npz(root / "raw" / r / f"{lo}.npz")
        for k in ("s0/V", "s0/R"):
            d = float(np.abs(sc[k] - raw[k][ci]).max())
            items[f"{r}/{k}"], worst = d, max(worst, d)
        for (arm, cond), (V, R, Q) in sc["arms"].items():
            k = D.arm_conditions(D.ARM[arm]).index([D.condition_name(i) for i in D.FULL].index(cond))
            d = max(float(np.abs(V - raw[f"{arm}/V"][k, ci]).max()), float(np.abs(R - raw[f"{arm}/R"][k, ci]).max()),
                    float(np.abs(Q - raw[f"{arm}/Q"][k, ci]).max()))
            items[f"{r}/{arm}/{cond}"], worst = d, max(worst, d)
        arm, cond, Vr = sc["fresh"]
        k = D.arm_conditions(D.ARM[arm]).index([D.condition_name(i) for i in D.FULL].index(cond))
        d = float(np.abs(Vr - raw[f"{arm}/fresh"][k, ci, 0]).max())
        items[f"{r}/fresh/{arm}/{cond}"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}

    # Q5
    alias = {}
    for r in D.REGIMES:
        raw = npz(root / "raw" / r / f"{lo}.npz")
        for lvl in ("site", "region", "sheet"):
            alias[f"{r}/reference_{lvl}=inactive"] = all(np.array_equal(raw[f"reference_{lvl}/{f}"], raw[f"inactive/{f}"])
                                                         for f in ("V", "Q", "fresh"))
        alias[f"{r}/snapshot_V=body_site_V"] = bool(np.array_equal(raw["snapshot/V"], raw["body_site/V"]))
        e = npz(root / "shards" / r / f"{lo}.npz")
        alias[f"{r}/sham_start=s0"] = bool(e["damage/v_rms"][0].max() == 0 and e["damage/r_rms"][0].max() == 0)
    shift, p = W.params(D.PRIMARY)
    cases, s0, th, p, shift, _ = W.prepare(D.PRIMARY, [lo], "engineering")
    starts = [injure(s0, band_damage(D.TAG, cases, "body", b, x) if l in ("body", "both") else None,
                     band_damage(D.TAG, cases, "reference", b, x) if l in ("reference", "both") else None)
              for l, b, x in D.CONDITIONS]
    zero = D.Arm("zero_site", "check", (D.Segment(D.WINDOW, body=D.ch("site", decision="zero")),), "single")
    end, *_ = W.run_arm(zero, starts, D.SINGLE, th, W.draws(cases, "future", updates=D.WINDOW), p,
                        thresholds_frozen[D.PRIMARY])
    raw = npz(root / "raw" / D.PRIMARY / f"{lo}.npz")
    keep = [D.FULL.index(c) for c in D.SINGLE]
    alias["zero_clamp=inactive"] = bool(np.array_equal(end.V.reshape(len(D.SINGLE), 8, 16, 16), raw["inactive/V"][keep])
                                        and np.array_equal(end.Q.reshape(len(D.SINGLE), 8, 16, 16), raw["inactive/Q"][keep]))
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    # Q6
    bad, fx = [], 0.0
    for r in D.REGIMES:
        shift, _ = W.params(r)
        raw, e = npz(root / "raw" / r / f"{lo}.npz"), npz(root / "shards" / r / f"{lo}.npz")
        T = raw["targets"]
        edge = W.edges(T)
        templ = np.stack([np.roll(half_plane(k, D.AMPLITUDE), shift, axis=(0, 1)) for k in range(4)])
        own = np.array([c.message for c in enrol([lo], D.MESSAGES, D.PARENTS, "engineering")])
        for arm in D.ARMS:
            nc = len(D.arm_conditions(arm))
            Tb = np.tile(T, (nc, 1, 1))
            ob = np.tile(own, nc)
            got = W.body_endpoints(raw[f"{arm.name}/V"].reshape(-1, 16, 16), Tb, np.tile(edge, (nc, 1, 1)), "v1000")
            got.update(W.fresh_endpoints(raw[f"{arm.name}/fresh"].reshape(nc * 8, -1, 16, 16), Tb, templ, ob))
            for k, v in got.items():
                if not np.array_equal(v.reshape(nc, 8), e[f"{arm.name}/{k}"]):
                    bad.append(f"{r}/{arm.name}/{k}")
            V = raw[f"{arm.name}/V"]
            for i in (0, nc - 1):
                s = fixture.offline_scores(V[i, 3], T[3])
                fx = max(fx, abs(s["qualified_percent"] / 100 - e[f"{arm.name}/v1000_qual"][i, 3]),
                         abs(s["sign_percent"] / 100 - e[f"{arm.name}/v1000_sign"][i, 3]))
    checks["Q6_reanalysis"] = {"pass": bool(not bad and fx <= 1e-12), "mismatched": bad[:10], "fixture_max_diff": fx}

    # Q7, Q8
    reader, efficacy, ok8 = {}, {}, True
    names = [D.condition_name(i) for i in D.FULL]
    for r in D.REGIMES:
        es = [npz(root / "shards" / r / f"{b}.npz") for b in range(lo, hi)]
        m = lambda k: float(np.mean([e[k].mean() for e in es]))
        row = {"target_f_sign": m("target/f_sign"), "zero_f_sign": m("zero/f_sign"), "target_f_qual": m("target/f_qual")}
        row["pass"] = row["target_f_sign"] - row["zero_f_sign"] >= 0.15 and (
            r != D.PRIMARY or (row["target_f_sign"] >= 0.75 and row["target_f_qual"] >= 0.65))
        reader[r] = row
        for e in es:
            for ci, (loc, band, rms) in enumerate(D.CONDITIONS):
                if loc == "sham":
                    continue
                v, rr = e["damage/v_rms"][ci], e["damage/r_rms"][ci]
                want_v, want_r = loc in ("body", "both"), loc in ("reference", "both")
                ok8 &= bool((v > 0).all() if want_v else (v == 0).all()) and bool((rr > 0).all() if want_r else (rr == 0).all())
        if r == D.PRIMARY:
            level = lambda ep, ci: float(np.mean([e[f"body_site/{ep}"][ci].mean() for e in es]))
            for loc in ("body", "reference"):
                drops = {}
                for band in D.BANDS:
                    ci = names.index(f"{loc}-{band}-2")
                    drops[band] = max(level(ep, 0) - level(ep, ci) for ep in ("v1000_qual", "f_qual"))
                efficacy[loc] = drops
                ok8 &= max(drops.values()) >= 0.02
    primary_ok = reader[D.PRIMARY]["pass"]
    for r, row in reader.items():
        if not row["pass"] and r != D.PRIMARY:
            flags.append(f"reader below threshold in {r}: successor endpoints reported as reader-unqualified")
    checks["Q7_known_reference_reader"] = {"pass": primary_ok, "regimes": reader}
    checks["Q8_perturbation_efficacy"] = {"pass": ok8, "primary_rms2_drops": efficacy}

    # Q9
    walls = [t["wall_s"] for t in manifest["tasks"].values()]
    per_task_bytes = manifest["bytes_written"] / len(manifest["tasks"])
    n_dev = len(D.REGIMES) * (D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0])
    forecast_h = max(walls) * np.ceil(n_dev / 12) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * 12
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 48 and rss <= 0.8 * avail and per_task_bytes * n_dev <= 0.8 * free),
                              "forecast_wall_h_12_workers": round(float(forecast_h), 2), "task_wall_s_max": max(walls),
                              "task_wall_s_median": float(np.median(walls)), "rss_12_workers_gb": round(rss / 2 ** 30, 2),
                              "mem_available_gb": round(avail / 2 ** 30, 1), "forecast_dev_gb": round(per_task_bytes * n_dev / 2 ** 30, 1),
                              "disk_free_tb": round(free / 2 ** 40, 1), "cpu_s_total_preflight": manifest["cpu_s_total"]}

    # Q10
    out = root / "analysis_dry_run"
    proc = subprocess.run([sys.executable, "-m", "me001.analyze", "--root", str(root), "--stage", "preflight",
                           "--out", str(out)] + ([] if a.blocks is None else ["--blocks", a.blocks]),
                          cwd=LANE, capture_output=True, text=True)
    expected = [out / f"contrasts_{r}_{ep}.csv" for r in D.REGIMES for ep in D.PRIMARY_ENDPOINTS]
    expected += [out / "summary.json", out / "predictions_scored.json", out / f"blocks_{D.PRIMARY}.csv"]
    verdicts = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    sizes = {p.name: p.stat().st_size for p in expected if p.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and all(p.exists() for p in expected)
                                    and set(verdicts) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "returncode": proc.returncode, "stderr_tail": proc.stderr[-800:],
                                    "largest_git_file_bytes": max(sizes.values(), default=None)}

    failed = [k for k, v in checks.items() if not v["pass"]]
    status = "FAIL" if failed else ("PASS_WITH_FLAGS" if flags else "PASS")
    receipt = {"status": status, "failed": failed, "flags": flags, "design_digest": D.digest(),
               "preflight_root": str(root), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "numpy": np.__version__, "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": status, "failed": failed, "flags": flags}, indent=1))


if __name__ == "__main__":
    main()
