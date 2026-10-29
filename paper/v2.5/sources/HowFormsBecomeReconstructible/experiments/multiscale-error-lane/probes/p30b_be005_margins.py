"""P30b (python probes/p30b_be005_margins.py): the margins of BE005's registered thresholds on probe P30.
ENGINEERING_PROBE_NOT_EVIDENCE; a reading of P30's block values, run before the freeze.

For every part of be005/predict.py: the pooled per-block value (the mean over the twelve unit-body pairs), its mean
and SD over P30's four blocks and the margin at the registered threshold in SDs (every-item parts: SD_block =
max(own SD, the RMS of the SDs over the part's items), the worst item). BE002's rule asks >= 1.68
(= 3 sqrt(1/4 + 1/16)). Also scores the statements on P30's block means. Writes probes/results/p30b_be005_margins.json."""
from __future__ import annotations

import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be005 import design as D  # noqa: E402
from be005 import predict as P  # noqa: E402

FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p30_be005_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p30b_be005_margins.json"
RULE = 3 * np.sqrt(1 / 4 + 1 / 16)


def per_block_levels(F):
    """L_blk[blk] = levels in the reader's shape for one block (mean over its cases; SD None), and L_all over blocks."""
    blocks = [str(b) for b in F["blocks"]]
    runs = {D.run_name(*x): x for x in D.RUNS}

    def build(sel):
        L = {}
        for u, node in F["blocks_values"].items():
            for key, per in node.items():
                b, rn, e = key.split("/", 2)
                if e == "trace":
                    continue
                x = np.mean([np.array(per[k], float) for k in sel], 0)
                rnode = L.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {})
                if e == "n_anc":
                    rnode["_n_anc"] = [float(x), None]
                    continue
                for ai, arm in enumerate(runs[rn][3]):
                    n = rnode.setdefault(arm, {})
                    n[e] = [float(x[ai]), None] if x.ndim == 1 else [[float(v), None] for v in x[:, ai]]
        for u in L:
            for b in L[u]:
                for rn, rnode in L[u][b].items():
                    na = rnode["_n_anc"][0]
                    for arm, n in rnode.items():
                        if arm != "_n_anc":
                            n["anc_right"] = [[v[0] / na, None] for v in n["n_anc_ok"]]
                            n["anc_on_share"] = [n["anc_on"][0] / na, None]
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
                          "sd": round(sd, 5), "margin": round(mg, 2), "items": {"/".join(map(str, it)): round(float(v.mean()), 5) for it, v in vals.items()}})
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
    res = {"probe": "P30b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "rule": round(float(RULE), 3), "blocks": F["blocks"],
           "design_digest_probe": F["design_digest_draft"], "design_digest_now": D.digest(), "thresholds": P.THR,
           "verdicts_on_p30_means": {k: v["verdict"] for k, v in S.items()}, "parts": parts}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for p in parts:
        if p["pooled"]:
            flag = "" if p["margin"] >= RULE else "   <-- below 1.68"
            print(f"{p['part']:58s} pooled {p['mean']:+.4f} (SD {p['sd']:.4f}) thr {p['sense']} {p['threshold']:+.4f}  margin {p['margin']:.2f}{flag}")
        else:
            ms = [r["mean"] for r in p["rows"]]
            flag = "" if p["worst_margin"] >= RULE else "   <-- below 1.68"
            print(f"{p['part']:58s} items {min(ms):+.4f}..{max(ms):+.4f} (RMS SD {p['rms_sd']:.4f}) thr {p['sense']} "
                  f"{p['threshold']:+.4f}  worst margin {p['worst_margin']:.2f}{flag}")
    print("verdicts on P30's means:", res["verdicts_on_p30_means"])


if __name__ == "__main__":
    main()
