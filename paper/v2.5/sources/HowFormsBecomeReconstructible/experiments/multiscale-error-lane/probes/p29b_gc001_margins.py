"""P29b (python probes/p29b_gc001_margins.py): the margins of GC001's registered thresholds on probe P29.
ENGINEERING_PROBE_NOT_EVIDENCE; a reading of P29's block values, run before the freeze.

For every part of gc001/predict.py: each item's mean and SD over P29's four blocks, SD_block = max(own SD, the RMS of the
SDs over the part's items), and the margin at the registered threshold in SD_block (every-item parts: the worst item;
pooled parts: the SD over blocks of the pooled per-block value). BE002's rule asks >= 1.68. Also scores the statements on
P29's block means, and prints the levels used in the plan. Writes probes/results/p29b_gc001_margins.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from gc001 import design as D  # noqa: E402
from gc001 import predict as P  # noqa: E402

FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p29_gc001_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p29b_gc001_margins.json"


def per_block(F):
    """B[u][b][run][arm][endpoint] = per-block values at t = 4,000 (blocks in P29's order)."""
    blocks = [str(b) for b in F["blocks"]]
    B = {}
    for u, node in F["blocks_values"].items():
        for key, per in node.items():
            b, rn, e = key.split("/", 2)
            if e == "trace_all":
                continue
            x = np.array([per[k] for k in blocks], float)
            n = B.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
            if e in ("misread", "misread_band"):
                n[f"_{e}"] = x
                continue
            for ai, arm in enumerate(D.ARMS):
                n.setdefault(arm, {})[e] = x[:, ai] if x.ndim == 2 else x[:, -1, ai]
    return B


def margin(p, B):
    vals = P.values(B, p)
    if p["pooled"]:
        x = np.mean(list(vals.values()), 0)
        m, sd = float(x.mean()), float(x.std(ddof=1))
        rows = [{"item": "pooled", "mean": round(m, 5), "sd": round(sd, 5)}]
        sds = [sd]
        sdb = [sd]
        means = [m]
    else:
        means = [float(v.mean()) for v in vals.values()]
        sds = [float(v.std(ddof=1)) for v in vals.values()]
        rms = float(np.sqrt(np.mean(np.square(sds))))
        sdb = [max(s, rms) for s in sds]
        rows = [{"item": "/".join(map(str, it)), "mean": round(m, 5), "sd": round(s, 5), "sd_block": round(sb, 5)}
                for it, m, s, sb in zip(vals, means, sds, sdb)]
    thr = p["thr"]
    mg = []
    for m, sb in zip(means, sdb):
        d = {"ge": m - thr, "le": thr - m, "abs": thr - abs(m)}[p["sense"]]
        mg.append(d / sb if sb > 0 else float("inf"))
    for r, g in zip(rows, mg):
        r["margin"] = round(g, 2)
    return {"part": p["name"], "threshold": thr, "sense": p["sense"], "pooled": p["pooled"], "rows": rows,
            "worst_margin": round(min(mg), 2), "zero_sd_items": int(sum(s == 0 for s in sds))}


def main():
    F = json.loads(FULL.read_text())
    B = per_block(F)
    parts = [margin(p, B) for p in P.PARTS]
    for r in parts:
        ms = [x["mean"] for x in r["rows"]]
        print(f"{r['part']:62s} {min(ms):+.4f}..{max(ms):+.4f} thr {r['sense']} {r['threshold']} worst margin {r['worst_margin']}"
              + (f"  ZERO-SD items {r['zero_sd_items']}" if r["zero_sd_items"] else ""))
    sc = P.score(B)
    print({k: v["verdict"] for k, v in sc.items()})
    OUT.write_text(json.dumps({"probe": "P29b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "rule": round(float(P.RULE_K), 3),
                               "blocks": F["blocks"], "design_digest_probe": F["design_digest_draft"], "design_digest_now": D.digest(),
                               "thresholds": P.THR, "parts": parts, "verdicts_on_p29": {k: v["verdict"] for k, v in sc.items()}},
                              indent=1) + "\n")
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
