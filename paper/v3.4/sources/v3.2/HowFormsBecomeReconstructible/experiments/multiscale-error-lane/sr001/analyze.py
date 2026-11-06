"""SR001's frozen reader: per-case endpoints from the shards, block means, the registered statements, the retention curves
and the fresh recipients' tables.

python -m sr001.analyze --root RUN_ROOT --stage {preflight,development,probe} [--out DIR] [--blocks LO,HI]

A case's value of an endpoint is read from its lineage's shard; a statement part pools over its (body, unit) items (the
mean over them for each case), then the mean over the block's 8 cases is the block value, and the statement is scored on
the mean over blocks (unrounded). Endpoints (every one inversion-invariant, NP001's dated note):
  a(x)     max(align, 1 - align) of the record (x = r) or the body (x = v) with the unit's template
  af(x)    the largest inversion-invariant agreement with a foreign placement (T rolled by 1/8, 1/4 or 3/8 period)
  q(x)     (a - af) / (1 - C), C = 0.75 (the largest inversion-invariant agreement between T and a foreign placement,
           checked from the templates by Q7): the history specificity, 1 for the exact history, about 0 when the
           pattern is lost, negative when a foreign placement fits better
  spacing  the record's or body's mean wavelength (dl001.sim.spacing)
Recipients: rq and ra are q and a of a fresh recipient's body at the last read (2,000 updates) reading a route's G16
record; their gain is the recipient's value less its paired no-record control's.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from sr001 import design as D  # noqa: E402

C = 0.75
RIX = {r: i for i, r in enumerate(D.ROUTENAMES)}
BIX = {b: i for i, b in enumerate(D.ROUTENAMES + ("none",))}


def load(root, blocks):
    """data[(body, unit)][key] = (blocks, ...) arrays from the shards, every case kept (the last axis)."""
    data = {}
    for body, unit in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / unit / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(body, unit)] = {k: np.stack(v) for k, v in arrs.items()}
    return data


inv = lambda x: np.maximum(x, 1.0 - x)


def a(data, body, unit, route, gen, x="r"):
    """(blocks, cases): the inversion-invariant agreement of the record (x = r) or body (x = v) after generation gen."""
    return inv(data[(body, unit)][f"g/{x}_a"][:, gen - 1, RIX[route]])


def af(data, body, unit, route, gen, x="r"):
    return inv(data[(body, unit)][f"g/{x}_f"][:, gen - 1, :, RIX[route]]).max(1)


def q(data, body, unit, route, gen, x="r"):
    return (a(data, body, unit, route, gen, x) - af(data, body, unit, route, gen, x)) / (1.0 - C)


def spacing(data, body, unit, route, gen, x="r"):
    return data[(body, unit)][f"g/{x}_spacing"][:, gen - 1, RIX[route]]


def rec_a(data, body, unit, RB, branch):
    """(blocks, cases): a recipient's inversion-invariant agreement at the last read."""
    return inv(data[(body, unit)][f"rec/{RB}/v_a"][:, -1, BIX[branch]])


def rec_q(data, body, unit, RB, branch):
    d = data[(body, unit)]
    return (inv(d[f"rec/{RB}/v_a"][:, -1, BIX[branch]]) - inv(d[f"rec/{RB}/v_f"][:, -1, :, BIX[branch]]).max(1)) / (1.0 - C)


def pooled_cases(data, items, f):
    """(blocks, cases): the mean over the items (body, unit) of f(data, body, unit) for each case."""
    return np.mean([f(data, b, u) for b, u in items], axis=0)


def ci(x):
    n = len(x)
    m = float(x.mean())
    if n < 2:
        return [m, None, None]
    h = float(stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n))
    return [m, m - h, m + h]


def curves(data):
    """Retention curves: per body, unit and route, a(r), q(r), a(v) and the record's spacing at every generation, the
    mean over blocks of the block means."""
    out = {}
    for body, unit in D.tasks():
        node = out.setdefault(body, {}).setdefault(unit, {})
        for route in D.ROUTENAMES:
            node[route] = {e: [round(float(f(data, body, unit, route, g).mean()), 6) for g in D.GEN_READS]
                           for e, f in (("a_r", a), ("q_r", q),
                                        ("a_v", lambda *z: a(*z, x="v")), ("spacing_r", spacing))}
    return out


def recipients(data):
    """Per body, unit, recipient kind and branch: ra, rq at the last read (mean over blocks) and their gain over the
    paired control."""
    out = {}
    for body, unit in D.tasks():
        node = out.setdefault(body, {}).setdefault(unit, {})
        for RB in D.RECIPIENTS:
            n2 = node.setdefault(RB, {})
            c_a, c_q = rec_a(data, body, unit, RB, "none"), rec_q(data, body, unit, RB, "none")
            for br in D.ROUTENAMES + ("none",):
                ra, rq = rec_a(data, body, unit, RB, br), rec_q(data, body, unit, RB, br)
                n2[br] = {"ra": round(float(ra.mean()), 6), "rq": round(float(rq.mean()), 6),
                          "ra_gain": round(float((ra - c_a).mean()), 6), "rq_gain": round(float((rq - c_q).mean()), 6)}
    return out


def contrasts(data, out):
    """contrasts.csv: at G16, every route's q(r) and a(r) per body and unit with 95% t intervals over blocks, and each
    route's paired difference from body@p at the same rate (the vote and parity against the body route)."""
    head = ["body", "unit", "contrast", "endpoint", "mean", "lo95", "hi95", "blocks"]
    rows = []
    G = D.GENS
    for body, unit in D.tasks():
        for route in D.ROUTENAMES:
            for e, f in (("q_r", q), ("a_r", a)):
                v = f(data, body, unit, route, G).mean(-1)
                rows.append([body, unit, route, e, *[None if x is None else round(x, 6) for x in ci(v)], len(v)])
        for p in D.RATES:
            for alt in ("vote", "parity"):
                v = (q(data, body, unit, f"{alt}@{p:g}", G) - q(data, body, unit, f"body@{p:g}", G)).mean(-1)
                rows.append([body, unit, f"{alt}@{p:g}-body@{p:g}", "q_r", *[None if x is None else round(x, 6) for x in ci(v)], len(v)])
    with open(out / "contrasts.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(rows)


def main():
    from sr001.predict import score
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development", "probe"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "sr001")
    ap.add_argument("--blocks", default=None)
    a_ = ap.parse_args()
    if a_.stage == "probe":                      # P39's shards (the reader run unstubbed before the freeze)
        blocks = list(range(*D.PROBE_BLOCKS))
    else:
        blocks = D.stage_blocks(a_.stage, None if a_.blocks is None else tuple(map(int, a_.blocks.split(","))))
    root = a_.root.resolve()
    a_.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    S = score(data)
    head = {"stage": a_.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "routes": D.ROUTENAMES,
            "bodies": D.BODIES, "units": D.UNITS, "gens": D.GENS, "recipients": D.RECIPIENTS}
    (a_.out / "curves.json").write_text(json.dumps(dict(head, curves=curves(data)), separators=(",", ":")) + "\n")
    (a_.out / "recipients.json").write_text(json.dumps(dict(head, recipients=recipients(data)), separators=(",", ":")) + "\n")
    (a_.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a_.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
