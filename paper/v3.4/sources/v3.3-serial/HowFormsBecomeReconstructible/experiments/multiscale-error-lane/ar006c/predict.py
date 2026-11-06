"""AR006C's criteria: python -m ar006c.predict --root STAGE_ROOT --out FILE  (writes confirmation.json)

The registered criteria (design.CRITERIA; PLAN_AR006.md's declaration with the lead's rulings of 4 November 2026), scored
on the stage's blocks with design.INTERVAL (mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n)):
  K1       r_all(vote) - r_all(vtol) at t = 8,000: the upper bound <= 0.01 in cue@0 and <= 0.002 in none@0
  K3 (a)   R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1): the lower bound >= 0.04
  K5 (a)   u(vtol) - u(vms) in correlated@0 at 4 x 4: the lower bound >= -0.005
CONFIRMED only if K1, K3 (a) and K5 (a) all hold; otherwise NOT CONFIRMED, naming the criteria that failed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar006c import analyze as AN  # noqa: E402
from ar006c import design as D  # noqa: E402


def score(Z):
    X = AN.contrasts(Z)
    I = {k: AN.interval(v) for k, v in X.items()}

    def bound(k):
        return I[k]["hi"] if D.THRESHOLDS[k][0] == "le" else I[k]["lo"]

    def ok(k):
        sense, c = D.THRESHOLDS[k]
        return bool(bound(k) <= c) if sense == "le" else bool(bound(k) >= c)

    C = {"K1": {"criterion": D.CRITERIA["K1"], "upper_bound_cue": bound("k1_cue"), "upper_bound_none": bound("k1_none"),
                "pass": ok("k1_cue") and ok("k1_none")},
         "K3a": {"criterion": D.CRITERIA["K3a"], "lower_bound": bound("k3a"), "pass": ok("k3a")},
         "K5a": {"criterion": D.CRITERIA["K5a"], "lower_bound": bound("k5a"), "pass": ok("k5a")}}
    failed = [k for k, c in C.items() if not c["pass"]]
    m = AN.Z5.AZ.meta(Z)
    return {"study": D.STUDY, "tag": m["tag"], "purpose": m["purpose"], "design_digest": m["design_digest"],
            "blocks": AN.blocks_of(Z), "interval": D.INTERVAL, "thresholds": D.THRESHOLDS, "criteria": C,
            "intervals": I, "verdict": "CONFIRMED" if not failed else "NOT CONFIRMED", "failed": failed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    S = score(AN.load(a.root))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(S, indent=1, default=float) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
