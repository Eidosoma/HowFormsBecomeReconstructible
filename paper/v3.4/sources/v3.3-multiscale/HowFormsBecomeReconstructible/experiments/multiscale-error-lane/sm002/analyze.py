"""SM002's rows and the margin rule's SD.

  E_u(cond)    the unscaled reader's agreement with the acquired template inside the injured patch after 2,000
               updates of reading the episode's final record (SM001's E), per case
  E_cg(cond)   the cg reader's (sm002.coarse): the same record coarse-grained 2 x 2, read on the half-side lattice by
               SM001's reader unchanged, the final body lifted back and scored on the full grid as E_u is
  gen_u, gen_cg the generic recovery: the best agreement inside the patch over every shift of the template (any phase)
  r_in         the episode's own patch agreement at 4,000 updates (both readers read the same record)
  the twin     of a refined condition (w, L, c, m, tau): the transfer condition (w/2, L/2, c/2, m, tau) on the same side
               64, blocks, cases, acquisition draws, noise streams, anchors and patch corner (SM001's)
A block's value is the mean over its 8 cases; a part the mean over its blocks. Every part here lies inside one stage,
so its SD is the max rule on its case values: max(SD over the blocks' means, SD over every case / sqrt(cases a block))
(BE002's block SD with the lead's case floor, BE009).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as S1D  # noqa: E402
from sm002 import design as D  # noqa: E402

READ2 = -1          # the unscaled reader's last read (2,000 updates)
READ1 = -1          # the episode's last read (4,000 updates)


def load(root, pairs):
    Z = {(u, b): dict(np.load(Path(root) / "shards" / u / f"{b}.npz")) for u, b in pairs}
    meta = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
    return Z, meta


def stage_pairs(stage, root=None):
    if root is not None and (Path(root) / "manifest.json").exists():
        return [tuple(x) for x in json.loads((Path(root) / "manifest.json").read_text())["pairs"]]
    return [(u, b) for u in D.UNITS for b in D.stage_blocks(stage)]


def conditions(Z, pairs):
    """One row per (unit, patch size, arm) over the pairs' blocks: the design's values and the per-block, per-case
    endpoints of both readers."""
    units = [u for u in D.UNITS if any(uu == u for uu, _ in pairs)]
    rows = []
    for u in units:
        blocks = sorted(b for uu, b in pairs if uu == u)
        cfg = S1D.UNIT[u]
        arms = D.unit_arms(u)
        na = len(arms)
        for L in cfg["sizes"]:
            rn = f"L{L}"
            for ai, a in enumerate(arms):
                g = lambda key, ri=None, j=ai: np.array([Z[(u, b)][f"{rn}/{key}"][j] if ri is None
                                                          else Z[(u, b)][f"{rn}/{key}"][ri, j] for b in blocks])
                rows.append({"unit": u, "kind": cfg["kind"], "w": cfg["w"], "L": L, "arm": a["name"], "c": a["c"],
                             "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"], "x2": L / a["lam_rest"],
                             "blocks": blocks,
                             "E_u": g("u/in", READ2), "E_u_ctrl": g("u/in", READ2, na), "gen_u": g("u/in_gen", READ2),
                             "shape_u": g("u/shape", READ2), "spacing_u": g("u/spacing", READ2),
                             "E_u_500": g("u/in", 0), "E_u_1000": g("u/in", 1),
                             "E_cg": g("cg/in"), "E_cg_ctrl": g("cg/in", None, na), "gen_cg": g("cg/in_gen"),
                             "shape_cg": g("cg/shape"), "spacing_cg": g("cg/spacing"),
                             "E_cgc_500": g("cg/c/in", 0), "E_cgc_1000": g("cg/c/in", 1), "E_cgc": g("cg/c/in", READ2),
                             "ties": g("cg/ties"), "r_in": g("r_in", READ1),
                             "wall": np.array([Z[(u, b)][f"{rn}/wall"] for b in blocks])})
    return rows


def fkey(r):
    return (r["w"], r["L"], r["c"], r["m"], r["tau"])


def attach_twins(rows):
    """Each refined row's twin: the transfer row at half every length, on the same blocks."""
    by = {(r["kind"],) + fkey(r): r for r in rows}
    for r in rows:
        r["twin"] = None
        if r["kind"] == "refine":
            t = by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"]))
            if t is None or t["blocks"] != r["blocks"]:
                raise ValueError(f"the twin of {r['unit']} L{r['L']} {r['arm']} is missing or on other blocks")
            r["twin"] = t
    return rows


def sd_rule(x):
    """(SD over the blocks' means, SD over every case / sqrt(cases a block), the larger) for case values x (blocks,
    cases)."""
    blk = x.mean(1)
    sd4 = float(blk.std(ddof=1))
    sdc = float(x.ravel().std(ddof=1) / math.sqrt(x.shape[1]))
    return sd4, sdc, max(sd4, sdc)
