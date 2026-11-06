"""HS001's qualification: python -m hs001.checks ROOT [--receipt PATH]  (fixed before their results; PLAN_HS001.md).

Q1 complete and finite; Q2 serial equals parallel; Q3 the bridges (E014's published scores on E014 block 12000 and
E014's own simulate; the subset generation against E006's ten-arm generation over 16 generations; the E-series
sources against their pins); Q4 an independent replay from saved checkpoint packets; Q5 aliases (the protected
probes constant across horizons and equal to the full panel's reads; copy = the rewrite record's read; copy_foreign =
the next cyclic founder's record); Q6 reanalysis from the raw states; Q7 efficacy of the fit and the ratio rule on
synthetic curves; Q8 pairing; Q9 resources; Q10 the reader's dry run. Any failure stops the campaign.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
sys.dont_write_bytecode = True

from hs001 import analyze as AN, design as D, fit as F, predict as PR, sim as S, worker as W  # noqa: E402

E14ROOT = D.EXP / "E014_long_renewal" / "runs" / "confirmation_v2"


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def q1(root, M):
    bad = []
    for b in M["blocks"]:
        for kind in ("shards", "raw"):
            z = np.load(root / kind / f"{b}.npz")
            for k in z.files:
                if k == "__meta__":
                    continue
                x = z[k]
                if np.issubdtype(x.dtype, np.floating) and not np.isfinite(x).all():
                    bad.append(f"{kind}/{b}/{k} nonfinite")
            if kind == "shards":
                C, H = len(D.CHECKPOINTS), M["horizon"]
                for f in D.FACTORS:
                    want = {"ck_scores": (C, 4, 2, 4, 4), "probe_scores": (4, 2, 4, 4), "g_scores": (H, 4, 2, 4, 4),
                            "conc_same": (C, 4, 4), "field_sd": (C, 4, 2, 4)}
                    for k, shp in want.items():
                        if z[f"f{f}/{k}"].shape != shp:
                            bad.append(f"{b}/f{f}/{k} shape {z[f'f{f}/{k}'].shape}")
                    for k in ("ck_scores", "probe_scores", "g_scores", "ck_sign_scores", "probe_sign_scores", "ck_amp", "probe_amp"):
                        x = z[f"f{f}/{k}"]
                        if x.min() < 0 or x.max() > 1:
                            bad.append(f"{b}/f{f}/{k} outside [0, 1]")
        if M["stage"] in W.EXPORT_STAGES:
            z = np.load(root / "export" / f"{b}.npz")
            C = len(D.CHECKPOINTS)
            for f in D.FACTORS:
                B = D.BYTES[f]
                want = {"packets_initial_lineage": ((4, 2, 4, B), np.uint8), "packets_initial_protected": ((4, 2, 4, B), np.uint8),
                        "packets_checkpoint": ((C, 4, 2, 4, B), np.uint8),
                        "recipient_checkpoint": ((C, 4, 2, 4, 3, 16, 16), np.float64),
                        "recipient_protected": ((4, 2, 4, 3, 16, 16), np.float64)}
                for k, (shp, dt) in want.items():
                    x = z[f"f{f}/{k}"]
                    if x.shape != shp or x.dtype != dt or (dt == np.float64 and not np.isfinite(x).all()):
                        bad.append(f"export/{b}/f{f}/{k} {x.shape} {x.dtype}")
            for k, (shp, dt) in {"evaluator/prototypes": ((4, 16, 16), np.float64),
                                 "evaluator/prototype_halves": ((2, 4, 16, 16), np.float64),
                                 "labels/lineage_source_founder": ((4, 4), np.int8),
                                 "labels/protected_source_founder": ((4, 4), np.int8),
                                 "labels/formation_qualified": ((4,), np.bool_), "ids/block": ((), np.int64),
                                 "ids/background_id": ((), np.int64), "ids/stream": ((), np.int64)}.items():
                if z[k].shape != shp or z[k].dtype != dt:
                    bad.append(f"export/{b}/{k} {z[k].shape} {z[k].dtype}")
            if int(z["ids/block"]) != b or int(z["ids/stream"]) != b + 1000000:
                bad.append(f"export/{b} ids")
    return {"pass": not bad, "blocks": len(M["blocks"]), "problems": bad[:10]}


def q2(root, M):
    b = M["blocks"][0]
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        W.run_task(b, M["stage"], tmp, M["horizon"])
        diff = []
        for kind in ("shards", "raw"):
            z0, z1 = np.load(root / kind / f"{b}.npz"), np.load(Path(tmp) / kind / f"{b}.npz")
            for k in z0.files:
                if k != "__meta__" and not np.array_equal(z0[k], z1[k]):
                    diff.append(f"{kind}/{k}")
    return {"pass": not diff, "block": b, "differing": diff}


def q3(root, M):
    out = {}
    pub = {}
    with open(E14ROOT / "observations.csv") as fh:
        for row in csv.DictReader(fh):
            if row["block"] == "12000":
                pub[(int(row["factor"]), row["stage"], int(row["founder"]), int(row["recipient"]), row["arm"])] = \
                    float(row["qualified_own"])
    worst, n, ok = 0.0, 0, True
    for f in D.FACTORS:
        br = S.bridge_e014(12000, f)
        ok &= br["packets_equal"] and br["outgoing_equal"] and br["g_scores_max_diff"] == 0 and \
            br["ck_scores_max_diff"] == 0 and br["copy_probe_max_diff"] == 0
        m = br["mine"]
        og, oc, op = S.own_scores(m["g_scores"]), S.own_scores(m["ck_scores"]), S.own_scores(m["probe_scores"][None])[0]
        for fo in range(4):
            for r in range(2):
                for a, arm in enumerate(D.LINEAGE):
                    for g in range(16):
                        worst = max(worst, abs(og[g, fo, r, a] - pub[(f, f"G{g + 1}", fo, r, arm)])); n += 1
                    for c in D.E014_CHECKPOINTS:
                        worst = max(worst, abs(oc[list(m["checkpoints"]).index(c), fo, r, a] - pub[(f, f"after_{c}", fo, r, arm)])); n += 1
                for c in D.E014_CHECKPOINTS:
                    worst = max(worst, abs(op[fo, r, 0] - pub[(f, f"after_{c}", fo, r, "copy")])); n += 1
    out["e014_block_12000"] = {"simulate_equal": bool(ok), "published_rows": n, "largest_difference": worst}
    b = M["blocks"][-1]
    src = S.source(b)
    eq = True
    for f in D.FACTORS:
        full, lin, _p, stream = S.initial(src, b, f)
        kept = [S.ARMS.index(a) for a in D.LINEAGE]
        for g in range(1, 17):
            full, _ = S.compact.generation(full, stream, g, f)
            lin, _ = S.generation(lin, stream, g, f, D.LINEAGE)
            eq &= bool(np.array_equal(full[:, :, kept], lin))
    out["subset_vs_ten_arms_16_generations"] = {"block": b, "equal": eq}
    pins = D.e_sources()
    frozen = json.loads((LANE / "hs001" / "frozen" / "design.json").read_text())["design"]["e_sources"] \
        if (LANE / "hs001" / "frozen" / "design.json").exists() else M["sources"]
    out["e_sources_unchanged"] = all(frozen.get(k) == v for k, v in pins.items())
    out["pass"] = ok and worst == 0 and eq and out["e_sources_unchanged"]
    return out


def q4(root, M):
    b = M["blocks"][0]
    raw, sh = np.load(root / "raw" / f"{b}.npz"), np.load(root / "shards" / f"{b}.npz")
    src = {"prototype": raw["prototype"]}
    stream = b + 1000000
    res = {}
    for f in D.FACTORS:
        ck = raw[f"f{f}/ck_packets"]
        i128, i192 = D.CHECKPOINTS.index(128), D.CHECKPOINTS.index(192)
        p = ck[i128].copy()
        for g in range(129, 193):
            p, _ = S.generation(p, stream, g, f, D.LINEAGE)
        rd = S.score(S.read(p, stream, f, D.LINEAGE)[None], src["prototype"])[0]
        p1, _ = S.generation(raw[f"f{f}/initial_lineage"], stream, 1, f, D.LINEAGE)
        res[str(f)] = {"packets_192_equal": bool(np.array_equal(p, ck[i192])),
                       "scores_192_equal": bool(np.array_equal(rd, sh[f"f{f}/ck_scores"][i192])),
                       "first_generation_equal": bool(np.array_equal(p1, ck[0]))}
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q5(root, M):
    b = M["blocks"][0]
    raw, sh = np.load(root / "raw" / f"{b}.npz"), np.load(root / "shards" / f"{b}.npz")
    src = S.source(b)
    stream = b + 1000000
    res = {}
    for f in D.FACTORS:
        full, lin, prot, _s = S.initial(src, b, f)
        v10 = S.read(full, stream, f, S.ARMS)
        sc10 = S.score(v10[None], src["prototype"])[0]
        pr = sh[f"f{f}/probe_scores"]
        again = S.score(S.read(raw[f"f{f}/initial_protected"], stream, f, D.PROBES)[None], src["prototype"])[0]
        lin_read = S.score(S.read(raw[f"f{f}/initial_lineage"], stream, f, D.LINEAGE)[None], src["prototype"])[0]
        res[str(f)] = {
            "probes_reread_equal": bool(np.array_equal(again, pr)),
            "probes_equal_ten_arm_panel": bool(all(np.array_equal(sc10[:, :, S.ARMS.index(D.PROBE_SOURCE[p])], pr[:, :, k])
                                                   for k, p in enumerate(D.PROBES))),
            "copy_equals_rewrite_record_read": bool(np.array_equal(lin_read[:, :, 0], pr[:, :, 0])),
            "copy_foreign_is_next_founder": bool(np.array_equal(raw[f"f{f}/initial_protected"][:, :, 1],
                                                                np.roll(raw[f"f{f}/initial_protected"][:, :, 0], -1, axis=0))),
            "copy_foreign_equals_foreign_arm_start": bool(np.array_equal(raw[f"f{f}/initial_protected"][:, :, 1],
                                                                         raw[f"f{f}/initial_lineage"][:, :, 1]))}
        if M["stage"] in W.EXPORT_STAGES:
            ex = np.load(root / "export" / f"{b}.npz")
            res[str(f)].update({
                "export_packets_equal_raw": bool(np.array_equal(ex[f"f{f}/packets_checkpoint"], raw[f"f{f}/ck_packets"])
                                                 and np.array_equal(ex[f"f{f}/packets_initial_lineage"], raw[f"f{f}/initial_lineage"])
                                                 and np.array_equal(ex[f"f{f}/packets_initial_protected"], raw[f"f{f}/initial_protected"])),
                "export_prototypes_equal_raw": bool(np.array_equal(ex["evaluator/prototypes"], raw["prototype"]))})
    if M["stage"] in W.EXPORT_STAGES:
        ex = np.load(root / "export" / f"{b}.npz")
        own = np.arange(4)
        res["labels"] = {
            "lineage": bool(np.array_equal(ex["labels/lineage_source_founder"],
                                           np.stack([own, (own + 1) % 4, -np.ones(4, int), -np.ones(4, int)], 1))),
            "protected": bool(np.array_equal(ex["labels/protected_source_founder"],
                                             np.stack([own, (own + 1) % 4, -np.ones(4, int), -np.ones(4, int)], 1))),
            "one_candidate_set": True}
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q6(root, M):
    b = M["blocks"][-1]
    raw, sh = np.load(root / "raw" / f"{b}.npz"), np.load(root / "shards" / f"{b}.npz")
    stream = b + 1000000
    res = {}
    for f in D.FACTORS:
        ck = raw[f"f{f}/ck_packets"]
        sc = np.stack([S.score(S.read(ck[i], stream, f, D.LINEAGE)[None], raw["prototype"])[0] for i in range(len(ck))])
        fields = S.tissue.unpack(ck, f)
        cs, cc, rs, rc = S.concordance(fields)
        res[str(f)] = {"ck_scores": bool(np.array_equal(sc, sh[f"f{f}/ck_scores"])),
                       "field_sd": bool(np.array_equal(fields.std(axis=(-2, -1)), sh[f"f{f}/field_sd"])),
                       "concordance": bool(np.array_equal(cs, sh[f"f{f}/conc_same"]) and np.array_equal(cc, sh[f"f{f}/conc_cross"])
                                           and np.array_equal(rs, sh[f"f{f}/corr_same"]) and np.array_equal(rc, sh[f"f{f}/corr_cross"]))}
        if M["stage"] in W.EXPORT_STAGES:
            ex = np.load(root / "export" / f"{b}.npz")
            proto = ex["evaluator/prototypes"]
            q, s_, a_ = S.outcomes(ex[f"f{f}/recipient_checkpoint"][:, :, :, :, 0], proto)
            pq, ps, pa = S.outcomes(ex[f"f{f}/recipient_protected"][None, :, :, :, 0], proto)
            res[str(f)]["export_fields_reproduce_Q_S_A"] = bool(
                np.array_equal(q, sh[f"f{f}/ck_scores"]) and np.array_equal(s_, sh[f"f{f}/ck_sign_scores"])
                and np.array_equal(a_, sh[f"f{f}/ck_amp"]) and np.array_equal(pq[0], sh[f"f{f}/probe_scores"])
                and np.array_equal(ps[0], sh[f"f{f}/probe_sign_scores"]) and np.array_equal(pa[0], sh[f"f{f}/probe_amp"]))
            rd = np.stack([S.read_state(ck[i], stream, f, D.LINEAGE) for i in range(len(ck))])
            res[str(f)]["export_fields_reproduced_from_packets"] = bool(np.array_equal(rd, ex[f"f{f}/recipient_checkpoint"]))
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q7():
    n = np.asarray(D.CHECKPOINTS, float)
    curve = lambda c, a, h: c + a * np.exp(-np.log(2) * (n - 1) / h)
    items = {}
    for c, a, h in ((1.0, 2.0, 8.0), (0.0, 3.0, 20.0), (-0.5, 1.5, 3.0), (0.3, 1.0, 60.0)):
        m1 = F.fit1(curve(c, a, h)[None])
        items[f"noiseless c {c} a {a} h {h}"] = bool(abs(m1["c"][0] - c) < 1e-6 and abs(m1["h"][0] / h - 1) < 1e-4)
    rng = np.random.default_rng(20261101)
    cover, ident_fast, ident_slow = [], [], []
    for rep in range(40):
        for c, h, slot in ((0.0, 6.0, "fast0"), (0.8, 6.0, "fast"), (0.8, 300.0, "slow")):
            blocks = curve(c, 2.0, h)[None] + rng.normal(0, 2.2, (128, n.size))
            sets = rng.integers(0, 128, (2000, 128))
            m1 = F.fit1(np.vstack([blocks.mean(0)[None], blocks[sets].mean(1)]))
            lo, hi = np.quantile(m1["c"][1:], [0.025, 0.975])
            hup = np.quantile(m1["h"][1:], 0.975)
            if slot == "slow":
                ident_slow.append(hup <= D.IDENTIFIED_H_MAX)
            else:
                ident_fast.append(hup <= D.IDENTIFIED_H_MAX)
                cover.append(lo <= c <= hi)
    items["coverage of c, fast decays (nominal 0.95)"] = float(np.mean(cover))
    items["fast decays identified"] = float(np.mean(ident_fast))
    items["slow decays (h 300) flagged not identified"] = float(1 - np.mean(ident_slow))
    den = rng.normal(0.2, 2.0, 128)
    s = rng.integers(0, 128, (2000, 128))
    items["a near-zero reference is not reported as a ratio"] = bool(
        np.quantile(den[s].mean(1), 0.025) < D.DENOM_MIN_FRACTION * den.mean())
    y = 0.4 + 1.0 * np.exp(-np.log(2) * (n - 1) / 2.0) + 1.2 * np.exp(-np.log(2) * (n - 1) / 40.0)
    m2 = F.fit2(y[None])
    items["M2 recovers two timescales"] = bool(abs(m2["c"][0] - 0.4) < 0.05 and abs(m2["h2"][0] / 40 - 1) < 0.1)
    ok = all(v for k, v in items.items() if isinstance(v, bool)) and items["coverage of c, fast decays (nominal 0.95)"] >= 0.85 \
        and items["fast decays identified"] >= 0.9 and items["slow decays (h 300) flagged not identified"] >= 0.9
    return {"pass": bool(ok), "items": items}


def q8(root, M):
    b = M["blocks"][0]
    src = S.source(b)
    res = {}
    for f in D.FACTORS:
        _full, lin, _p, stream = S.initial(src, b, f)
        a, _ = S.generation(lin, stream, 1, f, D.LINEAGE)
        a, _ = S.generation(a, stream, 2, f, D.LINEAGE)
        alone = lin[:, :, [0]].copy()
        for g in (1, 2):
            alone, _ = S.generation(alone, stream, g, f, ("rewrite",))
        twice = np.concatenate([lin, lin[:, :, [0]]], 2)
        for g in (1, 2):
            twice, _ = S.generation(twice, stream, g, f, D.LINEAGE + ("rewrite",))
        res[str(f)] = {"rewrite_alone_equals_batch": bool(np.array_equal(alone[:, :, 0], a[:, :, 0])),
                       "arm_listed_twice_identical": bool(np.array_equal(twice[:, :, 0], twice[:, :, -1]))}
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q9(root, M):
    cpu = np.mean([t["cpu_s"] for t in M["tasks"].values()])
    rss = max(t["maxrss_mb"] for t in M["tasks"].values())
    per_block_bytes = np.mean([sum(f["bytes"] for f in t["files"].values()) for t in M["tasks"].values()])
    nd, ne = len(D.IDENTITIES["development"]), len(D.IDENTITIES["e014"])
    cpu_h = (nd + ne) * cpu / 3600
    wall_h = (nd + ne) * cpu / 12 / 3600 * 1.15
    free = shutil.disk_usage(root).free
    return {"pass": bool(cpu_h <= 30 and wall_h <= 12 and rss <= 2048 and free > 100 * (nd + ne) * per_block_bytes),
            "cpu_s_per_block": float(cpu), "forecast_cpu_h": float(cpu_h), "forecast_wall_h_12_workers": float(wall_h),
            "development_blocks": nd, "e014_continuation_blocks": ne, "worker_rss_mb": float(rss),
            "bytes_per_block": float(per_block_bytes), "disk_free_bytes": int(free)}


def q10(root, M):
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        S_, arrays = AN.analyze(root, do_fit=True)
        Path(tmp, "summary.json").write_text(json.dumps(S_, indent=1) + "\n")
        np.savez_compressed(Path(tmp, "arrays.npz"), **arrays)
        from hs001 import tables as T
        T.main(tmp)
        scored = PR.score_all(root) if PR.PARTS else {"parts": []}
        Path(tmp, "predictions_scored.json").write_text(json.dumps(scored, indent=1) + "\n")
        sizes = {p.name: p.stat().st_size for p in Path(tmp).iterdir()}
    if M["stage"] in W.EXPORT_STAGES:
        from hs001 import export as X
        X.main(root)
        sizes["EXPORT_MANIFEST.json"] = (root / "EXPORT_MANIFEST.json").stat().st_size
    return {"pass": bool(all(v <= 256 * 1024 for k, v in sizes.items() if k != "arrays.npz") and len(scored["parts"]) == len(PR.PARTS)),
            "sizes": sizes, "parts_computed": len(scored["parts"]), "verdicts_opened": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--receipt", type=Path)
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    rec = {"study": D.STUDY, "stage": M["stage"], "root": str(root), "design_digest": D.digest(),
           "run_digest": M["design_digest"], "started_utc": utc()}
    t0 = time.process_time()
    for name, fn in (("Q1", lambda: q1(root, M)), ("Q2", lambda: q2(root, M)), ("Q3", lambda: q3(root, M)),
                     ("Q4", lambda: q4(root, M)), ("Q5", lambda: q5(root, M)), ("Q6", lambda: q6(root, M)),
                     ("Q7", q7), ("Q8", lambda: q8(root, M)), ("Q9", lambda: q9(root, M)), ("Q10", lambda: q10(root, M))):
        t = time.process_time()
        rec[name] = fn()
        rec[name]["cpu_s"] = round(time.process_time() - t, 1)
        print(f"{utc()} {name} {'PASS' if rec[name]['pass'] else 'FAIL'} ({rec[name]['cpu_s']} CPU-s)", flush=True)
    failed = [k for k in rec if k.startswith("Q") and not rec[k]["pass"]]
    rec.update(status="PASS" if not failed and rec["design_digest"] == rec["run_digest"] else "FAIL", failed=failed,
               finished_utc=utc(), cpu_s=round(time.process_time() - t0, 1))
    out = a.receipt or (root / "qualification_receipt.json")
    out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps({"status": rec["status"], "failed": failed}))


if __name__ == "__main__":
    main()
