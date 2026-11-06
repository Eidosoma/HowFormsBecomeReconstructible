"""SM001's tables: python -m sm001.tables --root ROOT --stage STAGE --dir OUT_DIR -> OUT_DIR/TABLES.md

The scored statements; the reported parts; the frozen model and both comparators, their FIT R^2 and their errors on each
TEST set; and every TEST condition's pooled endpoint beside the model's and the comparators' predictions, the 32 x 32
observation at the same x and, for a refined condition, its twin.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import analyze as A  # noqa: E402
from sm001 import predict as P  # noqa: E402


def num(x, spec):
    return "" if x is None else format(x, spec)


def part_rows(scored):
    out = []
    for sid, st in scored.items():
        for name, p in st["parts"].items():
            rule = "" if "threshold" not in p else f"{p['sense']} {p['threshold']:+}"
            out.append(f"| {sid} | {st['verdict']} | {name} | {p['value']:+.4f} | {rule} | {num(p.get('sd_T'), '.4f')} | "
                       f"{num(p.get('sd_F'), '.4f')} | {num(p.get('margin'), '.2f')} |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    scored = json.loads((a.dir / "predictions_scored.json").read_text())
    reported = json.loads((a.dir / "reported.json").read_text())
    blob = json.loads((a.dir / "model.json").read_text()) if (a.dir / "model.json").exists() else \
        json.loads((LANE / "sm001" / "frozen" / "model.json").read_text())
    head = ["| Id | Verdict | Part | Value | Rule | SD_T | SD_F | Margin (SDs) |", "|---|---|---|---|---|---|---|---|"]
    lines = [f"# SM001 tables ({a.stage})", "", "## Statements", "", *head, *part_rows(scored), "",
             "## Reported (F3-F6: the full refinement against the 32 x 32 means; R1-R3: the twin's other contrasts; "
             "C: the comparators against the model)", "", *head, *part_rows(reported["parts"])]
    m, par, S = blob["model"], blob["comparator_param"], reported["summary"]
    lines += ["", "## The frozen model and comparators", "",
              "The model: logistic(" + " + ".join(f"{b:+.4f} {t}" for t, b in zip(m["terms"], m["beta"])) + f"), FIT R^2 {m['r2']:.4f} "
              f"on {m['n']} condition means.", "",
              "The parametric comparator: logistic(" + " + ".join(f"{b:+.4f} {t}" for t, b in zip(par["terms"], par["beta"]))
              + f"), FIT R^2 {par['r2']:.4f} (A log2 lam_rest, B log2 w, C log2 L, M the delay multiple, T log2 tau_c).", "",
              f"The {blob['comparator']['k']}-nearest-neighbour comparator on " + ", ".join(blob["comparator"]["terms"]) + ".", "",
              "| TEST set | Conditions | MAE model | MAE 4-NN | MAE parametric | Bias model | Bias 4-NN | Bias parametric |",
              "|---|---|---|---|---|---|---|---|"]
    for k, v in S["sets"].items():
        lines.append(f"| {k} | {v['conditions']} | {v['mae_model']:.4f} | {v['mae_4nn']:.4f} | {v['mae_parametric']:.4f} | "
                     f"{v['bias_model']:+.4f} | {v['bias_4nn']:+.4f} | {v['bias_parametric']:+.4f} |")
    _, test_pairs = A.stage_pairs(a.stage, a.root)
    if test_pairs:
        Z, _ = A.load(a.root, test_pairs)
        rows = P.attach(A.conditions(Z, test_pairs), blob)
        lines += ["", "## Test conditions (pooled)", "",
                  "| Unit | L | Arm | E | Model | 4-NN | Parametric | E at 32 (same x) | Twin E | Episode r_in | Twin r_in | Generic | Control |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            tw = r["twin"]
            lines.append(f"| {r['unit']} | {r['L']} | {r['arm']} | {r['E'].mean():.3f} | {r['E_dim']:.3f} | {r['E_abs']:.3f} | "
                         f"{r['E_par']:.3f} | {num(r['E_32'], '.3f')} | {num(None if tw is None else tw['E'].mean(), '.3f')} | "
                         f"{r['r_in'].mean():.3f} | {num(None if tw is None else tw['r_in'].mean(), '.3f')} | "
                         f"{r['E_gen'].mean():.3f} | {r['E_ctrl'].mean():.3f} |")
    (a.dir / "TABLES.md").write_text("\n".join(lines) + "\n")
    print(a.dir / "TABLES.md")


if __name__ == "__main__":
    main()
