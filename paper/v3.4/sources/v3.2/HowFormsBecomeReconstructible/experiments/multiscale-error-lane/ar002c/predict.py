"""AR002C's criteria: python -m ar002c.predict --root STAGE_ROOT --out FILE  (writes confirmation.json)

The registered criteria (design.CRITERIA), as REGISTRATION_AR002.md declared them for AR002C, scored on the stage's
blocks with design.INTERVAL (mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n)):
  C1 (primary)     (a) U(det) - U(vote): the lower bound above 0
  C2 (co-primary)  (b) (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2: the lower bound above 0
  C3 (harm)        r_all(rest) - r_all(det) at t = 8,000: the upper bound <= 0.01 in cue@0 and <= 0.002 in none@0
CONFIRMED only if C1, C2 and C3 all hold; otherwise NOT CONFIRMED, naming the criteria that failed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar002c import analyze as AN  # noqa: E402
from ar002c import design as D  # noqa: E402


def score(Z):
    X = AN.contrasts(Z)
    I = {k: AN.interval(v) for k, v in X.items()}
    C = {"C1": {"criterion": D.CRITERIA["C1"], "lower_bound": I["a"]["lo"], "pass": I["a"]["lo"] > 0},
         "C2": {"criterion": D.CRITERIA["C2"], "lower_bound": I["b"]["lo"], "pass": I["b"]["lo"] > 0},
         "C3": {"criterion": D.CRITERIA["C3"], "upper_bound_cue": I["sham_cue"]["hi"],
                "upper_bound_none": I["sham_none"]["hi"],
                "pass": I["sham_cue"]["hi"] <= D.HARM["cue@0"] and I["sham_none"]["hi"] <= D.HARM["none@0"]}}
    failed = [k for k, c in C.items() if not c["pass"]]
    m = AN.AZ.meta(Z)
    return {"study": D.STUDY, "tag": m["tag"], "purpose": m["purpose"], "design_digest": m["design_digest"],
            "blocks": AN.AZ.blocks_of(Z), "interval": D.INTERVAL, "criteria": C, "intervals": I,
            "verdict": "CONFIRMED" if not failed else "NOT CONFIRMED", "failed": failed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    S = score(AN.load(a.root))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(S, indent=1) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
