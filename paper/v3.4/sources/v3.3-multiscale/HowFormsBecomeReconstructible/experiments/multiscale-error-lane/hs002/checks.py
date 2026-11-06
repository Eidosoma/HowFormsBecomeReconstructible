"""HS002's qualification: python -m hs002.checks ROOT [--receipt PATH]  (fixed before their results; PLAN_HS002.md).

Q1 complete and finite (and the export's schema); Q2 serial equals parallel; Q3 the bridges (the continuation equals an
uninterrupted run bit for bit; the saved rewrite-256 packets equal an in-memory HS001 lifecycle; every source raw file
equals its HS001-recorded sha256; the imported hs001 and E-series sources equal HS001's frozen ones); Q4 a replay from
saved checkpoint packets; Q5 aliases (the final packets are the 1,024 checkpoint's; the export's packets, prototypes
and labels); Q6 reanalysis from the raw states; Q7 efficacy as amended by the lead's ruling (hs002.fit equals hs001.fit on HS001's
checkpoints; rule AH's readings on calibrated synthetic cohorts); Q8 pairing; Q9 resources; Q10 the reader's dry run. Any failure stops the campaign.
"""
from __future__ import annotations

import argparse
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

from hs001 import design as H1, fit as F1, sim as S1  # noqa: E402
from hs002 import analyze as AN, design as D, fit as F, predict as PR, sim as S, worker as W  # noqa: E402


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def q1(root, M):
    bad = []
    K = len(D.NEW_CHECKPOINTS)
    for b in M["blocks"]:
        for kind in ("shards", "raw") + (("export",) if M["stage"] in D.EXPORT_STAGES else ()):
            z = np.load(root / kind / f"{b}.npz")
            for k in z.files:
                if k != "__meta__" and np.issubdtype(z[k].dtype, np.floating) and not np.isfinite(z[k]).all():
                    bad.append(f"{kind}/{b}/{k} nonfinite")
        z = np.load(root / "shards" / f"{b}.npz")
        for f in D.FACTORS[M["stage"]]:
            want = {"ck_scores": (K, 4, 2, 4, 4), "ck_sign_scores": (K, 4, 2, 4, 4), "ck_amp": (K, 4, 2, 4),
                    "g_scores": (D.HORIZON - D.START, 4, 2, 4, 4), "conc_same": (K, 4, 4), "field_sd": (K, 4, 2, 4)}
            for k, shp in want.items():
                if z[f"f{f}/{k}"].shape != shp:
                    bad.append(f"{b}/f{f}/{k} {z[f'f{f}/{k}'].shape}")
            for k in ("ck_scores", "ck_sign_scores", "ck_amp", "g_scores"):
                if z[f"f{f}/{k}"].min() < 0 or z[f"f{f}/{k}"].max() > 1:
                    bad.append(f"{b}/f{f}/{k} outside [0, 1]")
        if M["stage"] in D.EXPORT_STAGES:
            ex = np.load(root / "export" / f"{b}.npz")
            for f in D.FACTORS[M["stage"]]:
                for k, (shp, dt) in {"packets_checkpoint": ((K, 4, 2, 4, H1.BYTES[f]), np.uint8),
                                     "recipient_checkpoint": ((K, 4, 2, 4, 3, 16, 16), np.float64)}.items():
                    if ex[f"f{f}/{k}"].shape != shp or ex[f"f{f}/{k}"].dtype != dt:
                        bad.append(f"export/{b}/f{f}/{k}")
            if ex["evaluator/prototypes"].shape != (4, 16, 16) or int(ex["ids/block"]) != b:
                bad.append(f"export/{b} evaluator or ids")
        rec = json.loads((root / "done" / f"{b}.json").read_text())
        src = json.loads((D.SOURCE_ROOT[M["stage"]] / "manifest.json").read_text())["tasks"][str(b)]["files"]["raw"]["sha256"]
        if rec["source"]["sha256"] != src:
            bad.append(f"{b} source sha256")
    return {"pass": not bad, "blocks": len(M["blocks"]), "problems": bad[:10]}


def q2(root, M):
    b = M["blocks"][0]
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        W.run_task(b, M["stage"], tmp, M["horizon"])
        diff = [f"{kind}/{k}" for kind in ("shards", "raw") for k in np.load(root / kind / f"{b}.npz").files
                if k != "__meta__" and not np.array_equal(np.load(root / kind / f"{b}.npz")[k], np.load(Path(tmp) / kind / f"{b}.npz")[k])]
    return {"pass": not diff, "block": b, "differing": diff}


def q3(root, M):
    out = {}
    out["continuation_vs_uninterrupted"] = {str(f): S.bridge_exact(950003, f, end=320) for f in (1, 4)}
    ok = all(all(v for k, v in r.items() if k != "end") for r in out["continuation_vs_uninterrupted"].values())
    b = M["blocks"][-1]
    raw1, _prov = W.source_raw(M["stage"], b)
    src = S1.source(b)
    eq = {}
    for f in D.FACTORS[M["stage"]]:
        lc = S1.lifecycle(src, b, f)
        eq[str(f)] = bool(np.array_equal(lc["final_packets"], raw1[f"f{f}/final_packets"]))
    out["saved_256_equal_in_memory"] = {"block": b, **eq}
    srcs = 0
    for bb in M["blocks"]:
        W.source_raw(M["stage"], bb)
        srcs += 1
    out["source_records_checked"] = srcs
    frozen1 = json.loads((LANE / "hs001" / "frozen" / "design.json").read_text())["sources"]
    now1 = H1.sources(LANE)
    out["hs001_and_e_sources_unchanged"] = all(frozen1.get(k) == v for k, v in now1.items())
    out["pass"] = bool(ok and all(eq.values()) and out["hs001_and_e_sources_unchanged"])
    return out


def q4(root, M):
    b = M["blocks"][0]
    raw, sh = np.load(root / "raw" / f"{b}.npz"), np.load(root / "shards" / f"{b}.npz")
    proto = W.source_raw(M["stage"], b)[0]["prototype"]
    res = {}
    for f in D.FACTORS[M["stage"]]:
        ck = raw[f"f{f}/ck_packets"]
        i512, i640 = D.NEW_CHECKPOINTS.index(512), D.NEW_CHECKPOINTS.index(640)
        c = S.continue_lineages(ck[i512], b, f, proto, start=512, horizon=640, checkpoints=(640,))
        res[str(f)] = {"packets_640": bool(np.array_equal(c["ck_packets"][0], ck[i640])),
                       "scores_640": bool(np.array_equal(c["ck_scores"][0], sh[f"f{f}/ck_scores"][i640])),
                       "lineage_reads_513_640": bool(np.array_equal(c["g_scores"], sh[f"f{f}/g_scores"][512 - D.START:640 - D.START]))}
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q5(root, M):
    b = M["blocks"][0]
    raw = np.load(root / "raw" / f"{b}.npz")
    res = {}
    for f in D.FACTORS[M["stage"]]:
        res[str(f)] = {"final_is_1024": bool(np.array_equal(raw[f"f{f}/final_packets"], raw[f"f{f}/ck_packets"][-1]))}
        if M["stage"] in D.EXPORT_STAGES:
            ex = np.load(root / "export" / f"{b}.npz")
            res[str(f)]["export_packets_equal_raw"] = bool(np.array_equal(ex[f"f{f}/packets_checkpoint"], raw[f"f{f}/ck_packets"]))
    if M["stage"] in D.EXPORT_STAGES:
        ex = np.load(root / "export" / f"{b}.npz")
        own = np.arange(4)
        res["export"] = {"prototypes_equal_hs001": bool(np.array_equal(ex["evaluator/prototypes"], W.source_raw(M["stage"], b)[0]["prototype"])),
                         "labels": bool(np.array_equal(ex["labels/lineage_source_founder"],
                                                       np.stack([own, (own + 1) % 4, -np.ones(4, int), -np.ones(4, int)], 1)))}
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "checks": res}


def q6(root, M):
    b = M["blocks"][-1]
    raw, sh = np.load(root / "raw" / f"{b}.npz"), np.load(root / "shards" / f"{b}.npz")
    proto = W.source_raw(M["stage"], b)[0]["prototype"]
    stream = b + 1000000
    res = {}
    for f in D.FACTORS[M["stage"]]:
        ck = raw[f"f{f}/ck_packets"]
        rs = np.stack([S1.read_state(ck[i], stream, f, D.LINEAGE) for i in range(len(ck))])
        q, s_, a_ = S1.outcomes(rs[:, :, :, :, 0], proto)
        fields = S1.tissue.unpack(ck, f)
        cs, cc, r1, r2 = S1.concordance(fields)
        res[str(f)] = {"Q_S_A": bool(np.array_equal(q, sh[f"f{f}/ck_scores"]) and np.array_equal(s_, sh[f"f{f}/ck_sign_scores"])
                                     and np.array_equal(a_, sh[f"f{f}/ck_amp"])),
                       "field_sd": bool(np.array_equal(fields.std(axis=(-2, -1)), sh[f"f{f}/field_sd"])),
                       "concordance": bool(np.array_equal(cs, sh[f"f{f}/conc_same"]) and np.array_equal(cc, sh[f"f{f}/conc_cross"])
                                           and np.array_equal(r1, sh[f"f{f}/corr_same"]) and np.array_equal(r2, sh[f"f{f}/corr_cross"]))}
        if M["stage"] in D.EXPORT_STAGES:
            ex = np.load(root / "export" / f"{b}.npz")
            res[str(f)]["export_fields_equal_reread"] = bool(np.array_equal(ex[f"f{f}/recipient_checkpoint"], rs))
    return {"pass": all(all(v.values()) for v in res.values()), "block": b, "budgets": res}


def q7():
    """Efficacy, as amended by the lead's ruling on Q7 (rule AH; PLAN_HS002.md's amendment)."""
    items = {}
    rng = np.random.default_rng(20261101)
    n16 = np.asarray(H1.CHECKPOINTS, float)
    Y = rng.normal(0, 1, (5, 16)) + 1.0 + 2.0 * np.exp(-np.log(2) * (n16 - 1) / 6.0)
    a, b = F1.fit1(Y), F.fit1(Y, n16)
    items["fit1 equals hs001.fit on HS001's checkpoints"] = bool(all(np.array_equal(a[k], b[k]) for k in ("c", "a", "h", "sse")))
    a2, b2 = F1.fit2(Y[:2]), F.fit2(Y[:2], n16)
    items["fit2 equals hs001.fit"] = bool(all(np.array_equal(a2[k], b2[k]) for k in ("c", "a1", "h1", "a2", "h2", "sse")))
    n = np.asarray(D.CHECKPOINTS, float)
    K = n.size
    e = lambda h: np.exp(-np.log(2) * (n - 1) / h)
    curve = lambda c, a_, h: c + a_ * e(h)
    for c, a_, h in ((1.0, 1.0, 5.0), (0.0, 2.0, 30.0), (0.5, -0.5, 3.0)):
        m = F.fit1(curve(c, a_, h)[None], n)
        items[f"noiseless c {c} a {a_} h {h}"] = bool(abs(m["c"][0] - c) < 1e-6 and abs(m["h"][0] / h - 1) < 1e-4)
    # the readings, pass/fail: noise calibrated to HS001's development (P50q's "level + independent": SD 1.9 at every
    # checkpoint, rho 0.943, giving an SD of 0.64 for D(256) - D(128)); 10 cohorts of 128 blocks a truth, Q7's seed
    L_ = np.linalg.cholesky(1.9 ** 2 * (0.943 + (1 - 0.943) * np.eye(K)))
    rng2 = np.random.default_rng(20261101)
    truths = {"plateau c1 a1 h5": curve(1.0, 1.0, 5.0), "zero c0 a2 h5": curve(0.0, 2.0, 5.0),
              "linear drift": 1.6 - 0.0012 * (n - 1), "slow decay c0 a2 h600": curve(0.0, 2.0, 600.0),
              "fast+slow to zero (a1 1.0 h5, a2 1.1 h2 600)": 1.0 * e(5.0) + 1.1 * e(600.0)}
    tallies = {}
    for name, y in truths.items():
        t = {}
        for _ in range(10):
            blocks = y[None] + rng2.normal(0, 1, (128, K)) @ L_.T
            sets = rng2.integers(0, 128, (1000, 128))
            r = F.summarise(blocks.mean(0), blocks[sets].mean(1))["reading"]
            t[r] = t.get(r, 0) + 1
        tallies[name] = t
    P, Z, S_ = "a plateau within 1,024 rewrites", "decay to zero or below within 1,024 rewrites", "a slow drift"
    items["calibrated readings (10 cohorts a truth)"] = tallies
    items["plateau: at least 8 of 10 read as plateaus"] = tallies["plateau c1 a1 h5"].get(P, 0) >= 8
    items["zero: at least 8 of 10 as decay to zero, at most 1 of 10 as a plateau"] = (tallies["zero c0 a2 h5"].get(Z, 0) >= 8
                                                                                       and tallies["zero c0 a2 h5"].get(P, 0) <= 1)
    items["drift: at least 8 of 10 as slow drifts, none as plateaus"] = (tallies["linear drift"].get(S_, 0) >= 8
                                                                         and tallies["linear drift"].get(P, 0) == 0)
    items["slow decay h600: none as plateaus"] = tallies["slow decay c0 a2 h600"].get(P, 0) == 0
    items["fast+slow decay to zero: none as plateaus"] = tallies["fast+slow to zero (a1 1.0 h5, a2 1.1 h2 600)"].get(P, 0) == 0

    def cohort(y, sd=2.2, nb=128, nboot=2000):
        blocks = y[None] + rng.normal(0, sd, (nb, n.size))
        sets = rng.integers(0, nb, (nboot, nb))
        return blocks.mean(0), blocks[sets].mean(1)

    reported = {}
    for sd in (1.2, 2.2):                            # independent noise: reported, not pass/fail (the lead's ruling)
        for name, y in (("plateau", curve(1.0, 1.0, 5.0)), ("drift", 1.6 - 0.0012 * (n - 1)),
                        ("slow decay", curve(0.0, 2.0, 600.0)), ("zero", curve(0.0, 2.0, 5.0))):
            cur, boot = cohort(y, sd=sd)
            r = F.summarise(cur, boot)
            reported[f"sd {sd} {name}"] = f"{r['reading']} (as first declared: {r['reading_declared']})"
    items["reported: independent-noise cohorts"] = reported
    cover = []
    for _ in range(40):
        cur, boot = cohort(curve(0.8, 1.5, 6.0))
        m = F.fit1(np.vstack([cur[None], boot]), n)
        lo, hi = np.quantile(m["c"][1:], [0.025, 0.975])
        cover.append(lo <= 0.8 <= hi)
    items["coverage of c (nominal 0.95)"] = float(np.mean(cover))
    ok = all(v for k, v in items.items() if isinstance(v, bool)) and items["coverage of c (nominal 0.95)"] >= 0.85
    return {"pass": bool(ok), "items": items}


def q8(root, M):
    b = M["blocks"][0]
    raw1 = W.source_raw(M["stage"], b)[0]
    res = {}
    for f in D.FACTORS[M["stage"]]:
        p = raw1[f"f{f}/final_packets"]
        stream = b + 1000000
        x, _ = S1.generation(p, stream, 257, f, D.LINEAGE)
        y, _ = S1.generation(p[:, :, [0]].copy(), stream, 257, f, ("rewrite",))
        res[str(f)] = bool(np.array_equal(x[:, :, 0], y[:, :, 0]))
    return {"pass": all(res.values()), "block": b, "rewrite_alone_equals_batch": res}


def q9(root, M):
    cpu = np.mean([t["cpu_s"] for t in M["tasks"].values()]) / len(D.FACTORS[M["stage"]])    # a block-budget
    rss = max(t["maxrss_mb"] for t in M["tasks"].values())
    per = np.mean([sum(f["bytes"] for f in t["files"].values()) for t in M["tasks"].values()])
    nd, ne = len(D.IDENTITIES["development"]), len(D.IDENTITIES["e014"])
    cpu_h = (nd * len(D.FACTORS["development"]) + ne * len(D.FACTORS["e014"])) * cpu / 3600
    wall_h = cpu_h / 12 * 1.15
    free = shutil.disk_usage(root).free
    return {"pass": bool(cpu_h <= 30 and wall_h <= 12 and rss <= 2048 and free > 100 * (nd + ne) * per),
            "cpu_s_per_block_budget": float(cpu), "forecast_cpu_h": float(cpu_h), "forecast_wall_h_12_workers": float(wall_h),
            "worker_rss_mb": float(rss), "bytes_per_block": float(per), "disk_free_bytes": int(free)}


def q10(root, M):
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        S_, arrays = AN.analyze(root, do_fit=True)
        Path(tmp, "summary.json").write_text(json.dumps(S_, indent=1) + "\n")
        from hs002 import tables as T
        T.main(tmp)
        scored = PR.score_all(root) if PR.PARTS else {"parts": []}
        Path(tmp, "predictions_scored.json").write_text(json.dumps(scored, indent=1) + "\n")
        sizes = {p.name: p.stat().st_size for p in Path(tmp).iterdir()}
    if M["stage"] in D.EXPORT_STAGES:
        from hs002 import export as X
        X.main(root)
        sizes["EXPORT_MANIFEST.json"] = (root / "EXPORT_MANIFEST.json").stat().st_size
    return {"pass": bool(all(v <= 256 * 1024 for v in sizes.values()) and len(scored["parts"]) == len(PR.PARTS)),
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
