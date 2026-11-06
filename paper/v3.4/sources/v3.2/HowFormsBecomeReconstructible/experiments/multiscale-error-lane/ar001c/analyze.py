"""AR001C's reader: python -m ar001c.analyze --root STAGE_ROOT --out OUT_DIR

AR001's pooled arithmetic (ar001.analyze's, with each run's arms read from the shard's own meta, so the reader scores
reduced and full shards alike): per case the mean over the eight unit-body pairs, a block's value the mean over its
eight cases, equal weights over AR001's eight scorings at t = 8,000. It scores the registered criteria on the stage's
blocks, with 95% t intervals over the blocks:
  C1 (primary)     (a) U_ctrl(0.9, 0.1) - U(vote): the lower bound above 0
  C2 (co-primary)  (b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1): the lower bound above 0
  C3 (harm)        a sham's sheet cost r_all(rest) - r_all(dial): the upper bound <= 0.01 in cue@0 and <= 0.002 in none@0
CONFIRMED if C1, C2 and C3 all hold. Reported: the half-widths against their targets, every u and U of the three arms,
location alone (U_ctrl(1, 1) - U(vote)) and the U_ctrl line. Writes confirmation.json and TABLES.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar001 import analyze as AZ  # noqa: E402  (load and the pair list, unchanged)
from ar001 import design as A  # noqa: E402
from ar001c import design as D  # noqa: E402

PAIRS = AZ.PAIRS
load = AZ.load


def runarms(Z):
    """{run: arms} from every shard's meta; all shards must agree."""
    out = None
    for v in Z.values():
        m = {r: list(a) for r, a in json.loads(str(v["__meta__"]))["runs"]}
        assert out is None or m == out, "shards disagree on their runs"
        out = m
    return out


def blocks_of(Z):
    return sorted({k[2] for k in Z})


def case(Z, RA, run, ep, arm, read=A.T_READ, pairs=PAIRS):
    """(blocks, cases): per case the mean over the pairs (ar001.analyze.case's arithmetic)."""
    ri, ai = A.READS.index(read), RA[run].index(arm)
    return np.array([[Z[(b, u, k)][f"{run}/{ep}"][ri, ai] for b, u in pairs] for k in blocks_of(Z)]).mean(1)


def u(Z, RA, arm, s, pairs=PAIRS):
    sit, _, which = s.partition("/")
    return case(Z, RA, A.run_name(sit, 0.0), "r_in_old" if which == "old" else "r_in", arm, pairs=pairs)


def U(Z, RA, arm, pairs=PAIRS):
    return sum(A.WEIGHTS[s] * u(Z, RA, arm, s, pairs) for s in A.SCORINGS) / sum(A.WEIGHTS[s] for s in A.SCORINGS)


def U_ctrl(Z, RA, h, f, pairs=PAIRS):
    def uc(s):
        p = h if s in A.RIGHT else f
        return p * u(Z, RA, "dial", s, pairs) + (1 - p) * u(Z, RA, "rest", s, pairs)
    return sum(A.WEIGHTS[s] * uc(s) for s in A.SCORINGS) / sum(A.WEIGHTS[s] for s in A.SCORINGS)


def sham(Z, RA, run, pairs=PAIRS):
    return case(Z, RA, run, "r_all", "rest", pairs=pairs) - case(Z, RA, run, "r_all", "dial", pairs=pairs)


def interval(x):
    blk = x.mean(-1)
    n = len(blk)
    m, sd = float(blk.mean()), float(blk.std(ddof=1))
    h = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n))
    return {"mean": m, "lo": m - h, "hi": m + h, "half_width": h, "sd_block": sd,
            "sd_case8": float(x.ravel().std(ddof=1) / math.sqrt(x.shape[-1])), "n_blocks": n,
            "blocks": [float(v) for v in blk]}


def contrasts(Z):
    RA = runarms(Z)
    h, f = D.POINT
    a = U_ctrl(Z, RA, h, f) - U(Z, RA, D.BEST)
    b = U_ctrl(Z, RA, h, f) - U_ctrl(Z, RA, 1.0, 1.0)
    return RA, {"a": a, "b": b, "sham_cue": sham(Z, RA, "cue@0"), "sham_none": sham(Z, RA, "none@0"),
                "location_alone": U_ctrl(Z, RA, 1.0, 1.0) - U(Z, RA, D.BEST)}


def score(Z):
    RA, X = contrasts(Z)
    I = {k: interval(v) for k, v in X.items()}
    C = {"C1": {"criterion": D.CRITERIA["C1"], "lower_bound": I["a"]["lo"], "pass": I["a"]["lo"] > 0},
         "C2": {"criterion": D.CRITERIA["C2"], "lower_bound": I["b"]["lo"], "pass": I["b"]["lo"] > 0},
         "C3": {"criterion": D.CRITERIA["C3"], "upper_bound_cue": I["sham_cue"]["hi"], "upper_bound_none": I["sham_none"]["hi"],
                "pass": I["sham_cue"]["hi"] <= D.HARM["cue@0"] and I["sham_none"]["hi"] <= D.HARM["none@0"]}}
    verdict = "CONFIRMED" if all(c["pass"] for c in C.values()) else "NOT CONFIRMED"
    rep = {"half_widths": {k: {"half_width": I[k]["half_width"], "target": D.TARGET[k], "within": I[k]["half_width"] <= D.TARGET[k]}
                           for k in ("a", "b")},
           "u": {arm: {s: float(u(Z, RA, arm, s).mean()) for s in A.SCORINGS} for arm in D.ARMS},
           "U": {arm: float(U(Z, RA, arm).mean()) for arm in D.ARMS},
           "location_alone": I["location_alone"]}
    rest = {s: float(u(Z, RA, "rest", s).mean()) for s in A.SCORINGS}
    dlt = {s: float(u(Z, RA, "dial", s).mean()) - rest[s] for s in A.SCORINGS}
    wsum = sum(A.WEIGHTS.values())
    rep["U_ctrl_line"] = {"intercept_U_rest": rep["U"]["rest"],
                          "slope_h": sum(A.WEIGHTS[s] * dlt[s] for s in A.RIGHT) / wsum,
                          "slope_f": sum(A.WEIGHTS[s] * dlt[s] for s in A.WRONG) / wsum}
    m = json.loads(str(next(iter(Z.values()))["__meta__"]))
    return {"study": D.STUDY, "tag": m["tag"], "purpose": m["purpose"], "design_digest": m["design_digest"],
            "blocks": blocks_of(Z), "pairs": [f"{b}/{un}" for b, un in PAIRS], "runs": RA, "verdict": verdict,
            "criteria": C, "intervals": I, "reported": rep}


def tables(S):
    L = [f"# AR001C tables ({S['purpose']}, blocks {S['blocks'][0]}-{S['blocks'][-1]}, design {S['design_digest'][:12]})", "",
         f"**Verdict: {S['verdict']}**", "", "| Criterion | Bound | Rule | Pass |", "|---|---|---|---|"]
    c = S["criteria"]
    L.append(f"| C1 (a) U_ctrl(0.9, 0.1) - U(vote) | lower {c['C1']['lower_bound']:+.4f} | > 0 | {c['C1']['pass']} |")
    L.append(f"| C2 (b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1) | lower {c['C2']['lower_bound']:+.4f} | > 0 | {c['C2']['pass']} |")
    L.append(f"| C3 sham cost, cue@0 | upper {c['C3']['upper_bound_cue']:+.4f} | <= 0.01 | {c['C3']['pass']} |")
    L.append(f"| C3 sham cost, none@0 | upper {c['C3']['upper_bound_none']:+.4f} | <= 0.002 | {c['C3']['pass']} |")
    L += ["", "## The contrasts (95% t intervals over the blocks)", "",
          "| Contrast | Mean | Interval | Half-width | SD_block | Case SD / sqrt 8 |", "|---|---|---|---|---|---|"]
    for k, name in (("a", "(a) U_ctrl(0.9, 0.1) - U(vote)"), ("b", "(b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1)"),
                    ("sham_cue", "sham cost, cue@0"), ("sham_none", "sham cost, none@0"),
                    ("location_alone", "location alone, U_ctrl(1, 1) - U(vote)")):
        i = S["intervals"][k]
        L.append(f"| {name} | {i['mean']:+.4f} | [{i['lo']:+.4f}, {i['hi']:+.4f}] | {i['half_width']:.4f} | {i['sd_block']:.4f} | {i['sd_case8']:.4f} |")
    hw = S["reported"]["half_widths"]
    L += ["", "Half-widths against their targets (a third of the development values): "
          + "; ".join(f"({k}) {v['half_width']:.4f} against {v['target']:.4f}" for k, v in hw.items()), ""]
    L += ["## The three arms by scoring (pooled, t = 8,000)", "", "| Arm | " + " | ".join(A.SCORINGS) + " | U |",
          "|---" * (len(A.SCORINGS) + 2) + "|"]
    for arm in D.ARMS:
        L.append(f"| {arm} | " + " | ".join(f"{S['reported']['u'][arm][s]:.4f}" for s in A.SCORINGS)
                 + f" | {S['reported']['U'][arm]:.4f} |")
    ln = S["reported"]["U_ctrl_line"]
    L += ["", f"U_ctrl(h, f) = {ln['intercept_U_rest']:.4f} + {ln['slope_h']:.4f} h {ln['slope_f']:+.4f} f"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    Z = load(a.root)
    S = score(Z)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "confirmation.json").write_text(json.dumps(S, indent=1) + "\n")
    (a.out / "TABLES.md").write_text(tables(S))
    print(json.dumps({"verdict": S["verdict"], **{k: v["pass"] for k, v in S["criteria"].items()}}))


if __name__ == "__main__":
    main()
