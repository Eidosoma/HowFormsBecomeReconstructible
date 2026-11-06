"""SM006's tables: python -m sm006.tables --dir DIR --model MODEL_JSON  ->  DIR/TABLES.md, from DIR/predictions_scored.json:
the selection on FIT, the erasure sizes, the parts and the reported parts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm006 import design as D  # noqa: E402

iv = lambda v, ci, p=4: f"{v:+.{p}f} [{ci[0]:+.{p}f}, {ci[1]:+.{p}f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    a = ap.parse_args()
    S = json.loads((a.dir / "predictions_scored.json").read_text())
    B = json.loads(a.model.read_text())
    L = [f"# SM006 tables: {S['stage']}", "", f"The model: {B['chosen']} (sha256 {B['model_sha256'][:16]}), FIT R^2 "
         f"{B['model']['r2']:.4f}, {B['n_fit']} FIT means. FIT bias (E - the model): "
         + ", ".join(f"{k} {v:+.4f}" for k, v in B["fit_bias"].items()) + ".", "",
         "Erasure sizes (side/grain/gain factor): " + ", ".join(f"{k} {v}" for k, v in B["eps"].items()) + ".", "",
         "## The selection on FIT", "", "| Candidate | Terms | Rank | Condition number | Leave-one-block-out | FIT R^2 | |",
         "|---|---|---|---|---|---|---|"]
    for n, t in D.CANDIDATES.items():
        idf = B["identification"][n]
        L.append(f"| {n} | {len(t)} | {idf['rank']} | {idf['cond']:.1f} | {B['lobo'].get(n, float('nan')):.6f} | "
                 f"{B['candidates'][n]['r2']:.4f} | {'chosen' if n == B['chosen'] else ''} |")
    rep = {p["id"]: p for p in S["reported"]}
    beside = S.get("h1_beside", {})
    U = {u["id"]: u["value"] for u in (S.get("sensitivity_U") or {}).get("values", [])}
    L += ["", "## The statement candidates", "",
          "H1 beside each part: H1 in the model's place (for S2 and S7, which compare the two, the first term: |H1's error|). "
          "U: the reported sensitivity (the model's terms refitted on the FIT means whose erasure size is not censored), its "
          "value only." + ("" if U else " U is not computed on this stage."), "",
          "| Id | Part | Value [95%] | SD (T, F) | Halves | Narrowest | Threshold | | H1 [95%] | U |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for p in S["parts"]:
        h = rep.get(beside.get(p["id"]))
        L.append(f"| {p['id']} | {p['part']} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} ({p['sd_T']:.4f}, {p['sd_F']:.4f}) | "
                 f"{p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} | {p['narrowest']} | {p.get('threshold', '')} | "
                 f"{('HOLDS' if p['holds'] else 'FAILS') if 'holds' in p else ''} | "
                 f"{iv(h['value'], h['ci95']) if h else ''} | {format(U[p['id']], '+.4f') if p['id'] in U else ''} |")
    L += ["", "## Reported", "", "| Id | Part | Value [95%] | SD (T, F) | Halves |", "|---|---|---|---|---|"]
    for p in S["reported"]:
        L.append(f"| {p['id']} | {p['part']} | {iv(p['value'], p['ci95'])} | {p['sd']:.4f} ({p['sd_T']:.4f}, {p['sd_F']:.4f}) | "
                 f"{p['halves'][0]:+.4f}, {p['halves'][1]:+.4f} |")
    (a.dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {a.dir / 'TABLES.md'}")


if __name__ == "__main__":
    main()
