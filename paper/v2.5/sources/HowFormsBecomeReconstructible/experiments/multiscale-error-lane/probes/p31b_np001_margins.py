"""P31b (python probes/p31b_np001_margins.py): the margins of NP001's registered thresholds on probe P31.
ENGINEERING_PROBE_NOT_EVIDENCE; a reading of P31's block values, run before the freeze.

For every part of np001/predict.py: every item's mean and SD over P31's four blocks and the margin at the registered
threshold in SDs (every-item parts: SD_block = max(own SD, the RMS of the SDs over the part's items), the worst item;
pooled parts: the SD over blocks of the pooled per-block value). BE002's rule asks >= 1.68 (= 3 sqrt(1/4 + 1/16)); an
item with SD 0 sets no bound (BE004's E4): its margin is reported against the part's RMS. Also scores the statements on
P31's block means. Writes probes/results/p31b_np001_margins.json."""
from __future__ import annotations

import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from np001 import design as D  # noqa: E402
from np001 import predict as P  # noqa: E402

FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p31_np001_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p31b_np001_margins.json"
RULE = 3 * np.sqrt(1 / 4 + 1 / 16)


def per_block_levels(F):
    """L_blk[blk] = levels in the reader's shape for one block (mean over its cases; SD None), and L_all over blocks."""
    blocks = [str(b) for b in F["meta"]["blocks"]]

    def build(sel):
        L = {}
        for key, per in F["values"].items():
            b, u = key.split("/")
            node = L.setdefault(b, {}).setdefault(u, {"s1": {}, "s2": {}})
            for c, ends in per[sel[0]]["s1"].items():
                node["s1"][c] = {e: [[float(v), None] for v in np.mean([per[k]["s1"][c][e] for k in sel], 0)] for e in ends}
            for B, br in per[sel[0]]["s2"].items():
                node["s2"][B] = {c: {e: [[float(v), None] for v in np.mean([per[k]["s2"][B][c][e] for k in sel], 0)]
                                     for e in ends} for c, ends in br.items()}
        return L
    return {k: build([k]) for k in blocks}, build(blocks)


def main():
    F = json.loads(FULL.read_text())
    Lb, Lall = per_block_levels(F)
    blocks = list(Lb)
    parts = []
    for part in P.PARTS:
        name, items, thr, sense, pooled = part["name"], part["items"], part["threshold"], part["sense"], part["pooled"]
        vals = {it: np.array([part["value"](Lb[k], *it) for k in blocks]) for it in items}
        if pooled:
            x = np.mean(list(vals.values()), 0)
            m, sd = float(x.mean()), float(x.std(ddof=1))
            mg = {"ge": (m - thr) / sd, "le": (thr - m) / sd, "abs": (thr - abs(m)) / sd}[sense] if sd > 0 else float("inf")
            parts.append({"part": name, "pooled": True, "threshold": thr, "sense": sense, "mean": round(m, 5),
                          "sd": round(sd, 5), "margin": round(mg, 2),
                          "items": {"/".join(map(str, it)): round(float(v.mean()), 5) for it, v in vals.items()}})
        else:
            sds = {it: float(v.std(ddof=1)) for it, v in vals.items()}
            rms = float(np.sqrt(np.mean(np.square(list(sds.values())))))
            rows = []
            for it, v in vals.items():
                sdb = max(sds[it], rms)
                m = float(v.mean())
                mg = {"ge": (m - thr) / sdb, "le": (thr - m) / sdb, "abs": (thr - abs(m)) / sdb}[sense] if sdb > 0 else float("inf")
                rows.append({"item": "/".join(map(str, it)), "mean": round(m, 5), "sd": round(sds[it], 5),
                             "sd_block": round(sdb, 5), "margin": round(mg, 2)})
            parts.append({"part": name, "pooled": False, "threshold": thr, "sense": sense, "rms_sd": round(rms, 5),
                          "rows": rows, "worst_margin": min(r["margin"] for r in rows)})
    S = P.score(Lall)
    res = {"probe": "P31b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "rule": round(float(RULE), 3),
           "blocks": F["meta"]["blocks"], "design_digest_probe": F["meta"]["design_digest"],
           "design_digest_now": D.digest(), "thresholds": P.THR,
           "verdicts_on_p31_means": {k: v["verdict"] for k, v in S.items()}, "parts": parts}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for p in parts:
        if p["pooled"]:
            flag = "" if p["margin"] >= RULE else "   <-- below 1.68"
            print(f"{p['part']:56s} pooled {p['mean']:+.4f} (SD {p['sd']:.4f}) thr {p['sense']} {p['threshold']:+.4f}  "
                  f"margin {p['margin']:.2f}{flag}")
        else:
            ms = [r["mean"] for r in p["rows"]]
            flag = "" if p["worst_margin"] >= RULE else "   <-- below 1.68"
            print(f"{p['part']:56s} items {min(ms):+.4f}..{max(ms):+.4f} (RMS SD {p['rms_sd']:.4f}) thr {p['sense']} "
                  f"{p['threshold']:+.4f}  worst margin {p['worst_margin']:.2f}{flag}")
    print("verdicts on P31's means:", res["verdicts_on_p31_means"])


if __name__ == "__main__":
    main()
