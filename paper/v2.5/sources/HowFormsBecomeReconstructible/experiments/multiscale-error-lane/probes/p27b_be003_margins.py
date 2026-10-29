"""P27b (python probes/p27b_be003_margins.py): the margins of BE003's registered thresholds on probe P27.
ENGINEERING_PROBE_NOT_EVIDENCE; a reading of P27's block values, run before the freeze.

For every statement of be003/predict.py: each item's mean and SD over P27's four blocks, SD_block = max(own SD, the RMS of
the SDs over the part's items), and the margin at the registered threshold in SD_block (every-item parts: the worst item;
pooled parts: the SD over blocks of the pooled per-block value). BE002's rule asks >= 1.68 (= 3 sqrt(1/4 + 1/16)). Also
scores the statements on P27's block means. Writes probes/results/p27b_be003_margins.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be003 import design as D  # noqa: E402
from be003 import predict as P  # noqa: E402

FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p27_be003_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p27b_be003_margins.json"
RULE = 3 * np.sqrt(1 / 4 + 1 / 16)


def levels(F, blk=None):
    """L[unit][body][run][arm][endpoint] = [[value, None] at each read]: one block's case means, or the mean over blocks."""
    L = {}
    for u, node in F["blocks_values"].items():
        for key, per in node.items():
            b, rn, e = key.split("/", 2)
            if rn not in D.RUNNAMES or e.startswith("trace_"):
                continue
            x = np.array(per[str(blk)] if blk is not None else np.mean([per[k] for k in per], 0), float)
            arms = F["run_arms"][rn]
            for ai, arm in enumerate(arms):
                n = L.setdefault(u, {}).setdefault(b, {}).setdefault(rn, {}).setdefault(arm, {})
                n[e] = [float(x[ai]), None] if x.ndim == 1 else [[float(v), None] for v in x[:, ai]]
    return L


def part(name, per_block, thr, sense):
    """per_block: {item: [value per block]}; sense '>=', '<=' or 'abs<='. Returns the rows and the worst margin."""
    sd = {k: float(np.std(v, ddof=1)) for k, v in per_block.items()}
    rms = float(np.sqrt(np.mean([s ** 2 for s in sd.values()])))
    rows, worst = [], np.inf
    for k, v in per_block.items():
        m, sb = float(np.mean(v)), max(sd[k], rms) if len(per_block) > 1 else sd[k]
        mg = {">=": (m - thr) / sb, "<=": (thr - m) / sb, "abs<=": (thr - abs(m)) / sb}[sense] if sb > 0 else np.inf
        rows.append({"item": k, "mean": round(m, 5), "sd": round(sd[k], 5), "sd_block": round(sb, 5),
                     "margin": None if not np.isfinite(mg) else round(float(mg), 2)})
        worst = min(worst, mg)
    return {"part": name, "threshold": thr, "sense": sense, "rms_sd": round(rms, 5), "rows": rows,
            "worst_margin": None if not np.isfinite(worst) else round(float(worst), 2)}


def main():
    F = json.loads(FULL.read_text())
    blocks = F["blocks"]
    S_b = [P.score(levels(F, blk)) for blk in blocks]
    T = P.THR
    get = lambda f: {k: [f(s)[k] for s in S_b] for k in f(S_b[0])}          # noqa: E731
    parts = []
    w1 = lambda k: (lambda s: {i: v[k] for i, v in s["W1"]["items"].items()})   # noqa: E731
    parts.append(part("W1 mat-300 - dial", get(w1("mat-300_minus_dial")), T["W1"]["match"], "abs<="))
    parts.append(part("W1 mat-300 - inst-1", get(w1("mat-300_minus_inst-1")), T["W1"]["match"], "abs<="))
    s4 = {f"{i}/{k}": v for k in ("mat-300_minus_inst-3", "dial_minus_inst-3") for i, v in get(w1(k)).items() if i.startswith("S4")}
    parts.append(part("W1 S4 over inst-3", s4, T["W1"]["s4"], ">="))
    parts.append(part("W1 F0 mean over inst-3 (pooled)", {"pooled": [s["W1"]["F0_mean_over_inst-3"] for s in S_b]}, T["W1"]["f0"], ">="))
    parts.append(part("W2 interaction (pooled)", {"pooled": [s["W2"]["mean_interaction"] for s in S_b]}, T["W2"]["interaction"], "<="))
    parts.append(part("W2 mat-dial - mat-300 (pooled)", {"pooled": [s["W2"]["mean_mat-dial_minus_mat-300"] for s in S_b]}, T["W2"]["stack"], "<="))
    parts.append(part("W3 mat-dial late - mat-300", get(lambda s: {i: v["mat-dial_late_minus_mat-300"] for i, v in s["W3"]["items"].items()}),
                      T["W3"]["same"], "abs<="))
    parts.append(part("W3 dial late - inst-3 (pooled)", {"pooled": [s["W3"]["mean_dial_late_minus_inst-3"] for s in S_b]}, T["W3"]["over_inst3"], ">="))
    parts.append(part("W3 dial late - prompt (pooled)", {"pooled": [s["W3"]["mean_dial_late_minus_prompt"] for s in S_b]}, -T["W3"]["deficit"], ">="))
    parts.append(part("W4 extra loss r_in", get(lambda s: s["W4"]["extra_loss_r_in"]), T["W4"]["loss"], ">="))
    ring = get(lambda s: s["W5"]["extra_loss_r_ring"])
    parts.append(part("W5 ring dial", {k: v for k, v in ring.items() if k.endswith("/dial")}, T["W5"]["ring_dial"], ">="))
    parts.append(part("W5 ring free window", {k: v for k, v in ring.items() if not k.endswith("/dial")}, T["W5"]["ring_free"], "abs<="))
    parts.append(part("W5 r_out", get(lambda s: s["W5"]["r_out_minus_inst-3"]), T["W5"]["out"], "abs<="))
    tw = get(lambda s: {f"{i}/{a}": x[a] for i, x in s["W6"]["r_twin_minus_inst-3"].items() for a in x})
    parts.append(part("W6 twin free window", {k: v for k, v in tw.items() if not k.endswith("/dial")}, T["W6"]["free"], "abs<="))
    parts.append(part("W6 twin dial", {k: v for k, v in tw.items() if k.endswith("/dial")}, T["W6"]["told"], ">="))
    parts.append(part("W7 net mat-300 - inst-3, d 0", get(lambda s: s["W7"]["net_mat-300_minus_inst-3"]), T["W7"]["item"], ">="))
    parts.append(part("W7 (pooled)", {"pooled": [s["W7"]["mean"] for s in S_b]}, T["W7"]["mean"], ">="))
    parts.append(part("W8 d300 net mat-1000 - mat-300 (items, reported)", get(lambda s: s["W8"]["d300_net_mat-1000_minus_mat-300"]), 0.0, ">="))
    parts.append(part("W8 d300 (pooled)", {"pooled": [s["W8"]["d300_mean"] for s in S_b]}, T["W8"]["d300_mean"], ">="))
    for a in ("mat-300", "mat-1000"):
        parts.append(part(f"W8 d2000 {a} - inst-3 (pooled)", {"pooled": [s["W8"]["d2000_means"][a] for s in S_b]}, T["W8"]["closed"], "abs<="))
    parts.append(part("W8 d2000 dial - inst-3 (pooled)", {"pooled": [s["W8"]["d2000_means"]["dial"] for s in S_b]}, T["W8"]["open"], ">="))
    probe_score = P.score(levels(F))
    res = {"probe": "P27b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "rule": round(float(RULE), 3), "blocks": blocks,
           "design_digest_probe": F["design_digest_draft"], "design_digest_now": D.digest(), "thresholds": T, "parts": parts,
           "verdicts_on_P27_means": {k: v["verdict"] for k, v in probe_score.items()}}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for p_ in parts:
        flag = "" if p_["worst_margin"] is None or p_["worst_margin"] >= RULE else "   <-- below 1.68"
        print(f"{p_['part']:36s} thr {p_['threshold']:+.4f} {p_['sense']:5s} worst margin {p_['worst_margin']}{flag}")
        print("      " + "  ".join(f"{r['item']}: {r['mean']:+.4f} ({r['sd']:.4f})" for r in p_["rows"][:8]))
    print("verdicts on P27's means:", res["verdicts_on_P27_means"])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
