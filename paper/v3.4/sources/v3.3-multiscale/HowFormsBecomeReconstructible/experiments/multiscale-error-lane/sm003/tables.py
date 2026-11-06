"""SM003's tables: python -m sm003.tables --root TEST_ROOT --model MODEL_JSON --dir DIR  (DIR/TABLES.md, DIR/reported.json)

The registered parts (from DIR/predictions_scored.json when present), the model's selection and fit, every predictor's
condition-level error and bias on each TEST set and grain (reported, not registered), and the pooled conditions.
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

from sm003 import analyze as A  # noqa: E402
from sm003 import predict as P  # noqa: E402

PRED = (("new", "the model"), ("sm1", "SM001's model"), ("par", "parametric"), ("nn", "4-NN"))


def sets(rows):
    out = {}
    for r in rows:
        key = (r["kind"], r["g"], "late" if r["m"] == 2 else "prompt")
        out.setdefault((r["kind"], r["g"], "all"), []).append(r)
        out.setdefault(key, []).append(r)
    return out


def errors(rows, Pr):
    """Each predictor's condition-level error (the mean over conditions of |pooled E - prediction|) and bias."""
    res = {}
    for key, rr in sorted(sets(rows).items()):
        E = np.array([r["E"].mean() for r in rr])
        res["/".join(map(str, key))] = {name: {"mae": float(np.mean(np.abs(E - np.array([Pr[name][id(r)] for r in rr])))),
                                               "bias": float(np.mean(E - np.array([Pr[name][id(r)] for r in rr])))}
                                        for name, _ in PRED} | {"n": len(rr), "E": float(E.mean())}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    rows = A.test_rows(a.root)
    blob = json.loads(a.model.read_text())
    Pr = P.predictions(rows, blob)
    err = errors(rows, Pr)
    scored = (json.loads((a.dir / "predictions_scored.json").read_text()) if (a.dir / "predictions_scored.json").exists()
              else {"parts": P.score(rows, blob), "verdicts": None})
    stage = rows[0]["stage"]
    L = [f"# SM003 tables ({stage}, {len({tuple(r['blocks']) for r in rows})} block set(s), {len(rows)} condition-grains)", ""]
    L += ["## Registered parts", "", "| Id | Part | Value [95%] | Threshold | SD (T, F) | Margins | Halves | Holds |",
          "|---|---|---|---|---|---|---|---|"]
    for p in scored["parts"]:
        th = f"[{p['threshold'][0]:+.2f}, {p['threshold'][1]:+.2f}]" if p["kind"] == "in" else f"≥ {p['threshold']:+.2f}"
        L.append(f"| {p['id']} | {p['part']} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {th} | "
                 f"{p['sd']:.4f} ({p['sd_T']:.4f}, {p['sd_F']:.4f}) | {', '.join(f'{m:.2f}' for m in p['margins'])} | "
                 f"{p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {'yes' if p['holds'] else 'no'} |")
    L += ["", "## The model (frozen on the FIT rereads)", "",
          f"- Chosen form: {blob['chosen']} ({len(blob['model']['terms'])} terms: {', '.join(blob['model']['terms'])}); "
          f"FIT R² {blob['model']['r2']:.4f} on {blob['model']['n']} condition means.",
          "- Leave-one-block-out error by candidate: " + ", ".join(f"{k} {v:.4f}" for k, v in blob["lobo"].items()) + ".",
          f"- Comparators: the parametric (22 terms) FIT R² {blob['parametric']['r2']:.4f}; the 4-NN on six standardised features.",
          "", "## Each predictor's condition-level error and bias (reported, not registered)", "",
          "| Set (kind / g / signal) | n | mean E | " + " | ".join(f"{lbl}: error, bias" for _, lbl in PRED) + " |",
          "|---|---|---|" + "---|" * len(PRED)]
    for key, v in err.items():
        L.append(f"| {key} | {v['n']} | {v['E']:.3f} | " + " | ".join(f"{v[n]['mae']:.3f}, {v[n]['bias']:+.3f}" for n, _ in PRED) + " |")
    L += ["", "## Conditions (pooled over blocks and cases; 3 decimals)", "",
          "| Unit | L | Arm | g | e | E | model | SM001 | parametric | 4-NN | twin (g) | twin (g / 2) | r_in |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tw = f"{r['twin']['E'].mean():.3f}" if r.get("twin") is not None else ""
        th = f"{r['twin_half']['E'].mean():.3f}" if r.get("twin_half") is not None else ""
        L.append(f"| {r['unit']} | {r['L']} | {r['arm']} | {r['g']} | {r['x'][4]:+.2f} | {r['E'].mean():.3f} | "
                 f"{Pr['new'][id(r)]:.3f} | {Pr['sm1'][id(r)]:.3f} | {Pr['par'][id(r)]:.3f} | {Pr['nn'][id(r)]:.3f} | {tw} | "
                 f"{th} | {r['r_in'].mean():.3f} |")
    a.dir.mkdir(parents=True, exist_ok=True)
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    (a.dir / "reported.json").write_text(json.dumps({"errors": err, "chosen": blob["chosen"], "lobo": blob["lobo"],
                                                     "r2": {"model": blob["model"]["r2"], "parametric": blob["parametric"]["r2"]}},
                                                    indent=1) + "\n")
    print("wrote", a.dir / "TABLES.md")


if __name__ == "__main__":
    main()
