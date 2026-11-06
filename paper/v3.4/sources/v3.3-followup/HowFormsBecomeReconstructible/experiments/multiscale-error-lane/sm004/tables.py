"""SM004's tables: python -m sm004.tables --root STAGE_ROOT --model MODEL_JSON --dir DIR  ->  DIR/TABLES.md

The selection on FIT (every candidate's identification, leave-one-block-out error and FIT R^2), the FIT bias by grain,
the contrasts the frozen fits predict from FIT alone, each predictor's condition-level error and bias by set, grain and
signal (pooled E over the stage's blocks), and the scored parts (DIR/predictions_scored.json, when there).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm004 import analyze as A  # noqa: E402
from sm004 import design as D  # noqa: E402
from sm004 import predict as PR  # noqa: E402

NAMES = {"new": "the model", "f4": "F4", "sm1": "SM001's model", "par": "the parametric", "par2": "parametric + G^2",
         "nn": "the 4-NN"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    rows = A.test_rows(a.root)
    blob = json.loads(a.model.read_text())
    P = PR.predictions(rows, blob)
    M = json.loads((a.root / "manifest.json").read_text())
    blocks = sorted({b for _, b in M["pairs"]})
    L = [f"# SM004 tables: {M['stage']} ({len(blocks)} blocks: {blocks[0]}-{blocks[-1]}, tag {M['tag']})", "",
         f"The model: {blob['chosen']} (sha256 {blob['model_sha256'][:16]}), FIT R^2 {blob['model']['r2']:.4f}; "
         f"FIT bias by grain (E - the model): " + ", ".join(f"g {g} {v:+.4f}" for g, v in blob["fit_bias_by_grain"].items()) + ".",
         "", "## The selection on FIT (864 condition means, 16 blocks)", "",
         "| Candidate | Terms | Rank | Condition number | Leave-one-block-out error | FIT R^2 | |", "|---|---|---|---|---|---|---|"]
    for name, terms in D.CANDIDATES.items():
        idf = blob["identification"][name]
        L.append(f"| {name} | {len(terms)} | {idf['rank']} | {idf['cond']:.1f} | "
                 f"{blob['lobo'].get(name, float('nan')):.5f} | {blob['candidates'][name]['r2']:.4f} | "
                 f"{'chosen' if name == blob['chosen'] else ''} |")
    L += ["", f"The comparators on the same means: the parametric R^2 {blob['parametric']['r2']:.4f}; "
          f"with (log2 g)^2 {blob['parametric_g2']['r2']:.4f}.", "",
          "## The contrasts predicted from FIT alone (on this stage's conditions)", ""]
    pc = PR.predicted_contrasts(rows, P)
    for key, v in pc.items():
        L.append(f"- {NAMES[key]}: " + "; ".join(f"{k.replace('_', ' ')} {x:+.4f}" for k, x in v.items()))
    L += ["", "## Each predictor's condition-level error (mean |E - prediction|, bias E - prediction in brackets)", "",
          "| Set | g | Signal | Conditions | E | " + " | ".join(NAMES[k] for k in NAMES) + " |",
          "|---|---|---|---|---|" + "---|" * len(NAMES)]
    for kind in ("transfer", "refine"):
        for g in D.GRAINS:
            for sig, m in (("all", None), ("late", 2), ("prompt", 0)):
                rr = PR.sel(rows, kind, g, m=m)
                if not rr:
                    continue
                E = np.array([r["E"].mean() for r in rr])
                cells = []
                for key in NAMES:
                    p = np.array([P[key][id(r)] for r in rr])
                    cells.append(f"{np.abs(E - p).mean():.3f} ({(E - p).mean():+.3f})")
                L.append(f"| {kind} | {g} | {sig} | {len(rr)} | {E.mean():.3f} | " + " | ".join(cells) + " |")
    sc = a.dir / "predictions_scored.json"
    if sc.exists():
        S = json.loads(sc.read_text())
        L += ["", "## The statement candidates", "",
              "| Id | Part | Value [95%] | SD (T, F) | Halves | Narrowest | Registers | Threshold | |", "|---|---|---|---|---|---|---|---|---|"]
        for p in S["parts"]:
            L.append(f"| {p['id']} | {p['part']} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | "
                     f"{p['sd']:.4f} ({p['sd_T']:.4f}, {p['sd_F']:.4f}) | {p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | "
                     f"{p['narrowest']} | {p['registers_at_narrowest']} | {p.get('threshold', '')} | "
                     f"{('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} |")
        L += ["", "## Reported", "", "| Id | Part | Value [95%] | SD (T, F) |", "|---|---|---|---|"]
        for p in S["reported"]:
            L.append(f"| {p['id']} | {p['part']} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | "
                     f"{p['sd']:.4f} ({p['sd_T']:.4f}, {p['sd_F']:.4f}) |")
        sens = S.get("sensitivities")
        if isinstance(sens, dict):
            L += ["", "## The reported sensitivities (TEST only; the same parts as numbers, no thresholds)", "",
                  "| Id | " + " | ".join(f"{name} [95%]" for name in sens) + " |", "|---|" + "---|" * len(sens)]
            for i, p in enumerate(S["parts"]):
                L.append(f"| {p['id']} | " + " | ".join(
                    f"{v['parts'][i]['value']:+.4f} [{v['parts'][i]['ci95'][0]:+.4f}, {v['parts'][i]['ci95'][1]:+.4f}]"
                    for v in sens.values()) + " |")
        elif sens:
            L += ["", f"The reported sensitivities: {sens}."]
    a.dir.mkdir(parents=True, exist_ok=True)
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
