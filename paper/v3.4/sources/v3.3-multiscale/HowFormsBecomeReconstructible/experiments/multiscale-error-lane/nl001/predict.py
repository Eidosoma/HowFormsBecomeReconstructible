"""NL001's registered statements: parts, rules and scoring.

A part is a set of items, each an arm's endpoint under an event (or a paired difference of two), read at the last
read (t = 2,000); every item must pass its bound (sense ge / le). score(get) evaluates every statement with get(arm,
event, endpoint) returning the item's value: the mean over blocks for scoring (a block's value is its 8 cases' mean),
or the per-block array for the margins (probes/p34b_nl001_margins.py). A statement HOLDS when every part passes.
Bounds marked static are set by the outcome's own scale (see REGISTRATION_NL001.md), not by the probe's spread.
"""
from __future__ import annotations

import numpy as np

BASE = ("L1", "L1L2", "L1L3", "L1L2L3", "L1L2rL3", "L1L2L3d")


def lv(arm, event, ep):
    return ("lv", arm, event, ep)


def diff(a, b, event, ep):
    return ("diff", a, b, event, ep)


STATEMENTS = [
    {"id": "D1",
     "words": "Each scale's errors are repaired by a level at that scale. Scattered fine flips are repaired by every "
              "arm. Coherent regional errors (a region's records flipped with its boundary bonds, so the record holds "
              "no trace) are repaired by every arm with a region code and by no arm without one, a block code of up to "
              "8 times the lane's gain included. A coherent block error is not repaired by the record alone or with a "
              "region code.",
     "rule": "HOLDS if at t = 2,000 every base arm's fine_ok under F is >= 0.95; regions_ok under R is >= 0.5 for "
             "L1L2, L1L2L3, L1L2rL3 and L1L2L3d and <= 0.5 for L1, L1L3, L1L3-k3x4 and L1L3-k3x8; and block_ok under B "
             "is <= 0.5 for L1 and L1L2, else FAILS.",
     "parts": [("fine flips repaired, every base arm", [lv(a, "F", "fine_ok") for a in BASE], "ge", 0.95, "static"),
               ("regional errors repaired with a region code", [lv(a, "R", "regions_ok") for a in ("L1L2", "L1L2L3", "L1L2rL3", "L1L2L3d")], "ge", 0.5, "static"),
               ("regional errors left without one", [lv(a, "R", "regions_ok") for a in ("L1", "L1L3", "L1L3-k3x4", "L1L3-k3x8")], "le", 0.5, "static"),
               ("block error left without a block code", [lv(a, "B", "block_ok") for a in ("L1", "L1L2")], "le", 0.5, "static")]},
    {"id": "D2",
     "words": "Under damage at three scales at once (fine flips, four coherent regional errors and a coherent block "
              "error), the relative three-level hierarchy repairs every scale, while the record alone, the record "
              "with a block code, and the absolute and derived hierarchies each leave the block (and without a region "
              "code the regions) wrong.",
     "rule": "HOLDS if at t = 2,000 under FRB the cell_err of L1L2rL3 is <= 0.01, and the cell_err of each of L1, L1L3, "
             "L1L2, L1L2L3 and L1L2L3d is >= 0.05, else FAILS.",
     "parts": [("the relative hierarchy repairs every scale", [lv("L1L2rL3", "FRB", "cell_err")], "le", 0.01, "probe"),
               ("the others leave the block", [lv(a, "FRB", "cell_err") for a in ("L1", "L1L3", "L1L2", "L1L2L3", "L1L2L3d")], "ge", 0.05, "probe")]},
    {"id": "C1",
     "words": "Where nothing is damaged, no level costs anything: every arm keeps the pattern, the strongest block "
              "codes included.",
     "rule": "HOLDS if at t = 2,000 under none the cell_err of every arm run there is <= 0.001, else FAILS.",
     "parts": [("no damage, every arm", "NONE_ARMS", "le", 0.001, "static")]},
    {"id": "T1",
     "words": "The region code overrides the record by its gain, whether it is right or wrong. At 0.75 and 1 times the "
              "lane's gain it repairs coherent regional errors and imposes a corrupted region store on its region; at "
              "0.25 and 0.5 times it does neither.",
     "rule": "HOLDS if at t = 2,000 regions_ok under R is >= 0.5 for L1L2-k2x0.75 and L1L2 and <= 0.5 for L1L2-k2x0.25 "
             "and L1L2-k2x0.5, and c2_ok under C2 is <= 0.5 for L1L2-k2x0.75 and L1L2 and >= 0.5 for L1L2-k2x0.25 and "
             "L1L2-k2x0.5, else FAILS.",
     "parts": [("strong: repairs", [lv(a, "R", "regions_ok") for a in ("L1L2-k2x0.75", "L1L2")], "ge", 0.5, "static"),
               ("weak: does not repair", [lv(a, "R", "regions_ok") for a in ("L1L2-k2x0.25", "L1L2-k2x0.5")], "le", 0.5, "static"),
               ("strong: imposes a corrupted store", [lv(a, "C2", "c2_ok") for a in ("L1L2-k2x0.75", "L1L2")], "le", 0.5, "static"),
               ("weak: does not impose", [lv(a, "C2", "c2_ok") for a in ("L1L2-k2x0.25", "L1L2-k2x0.5")], "ge", 0.5, "static")]},
    {"id": "T2",
     "words": "An absolute block code overrides the record and the region codes by its gain, whether it is right or "
              "wrong. At up to 3 times the lane's gain it neither repairs a coherent block error that corrupted the "
              "region codes too nor imposes a corrupted block store; at 5 times and more it does both.",
     "rule": "HOLDS if at t = 2,000 block_ok under B is <= 0.5 for L1L2L3, L1L2L3-k3x2 and L1L2L3-k3x3 and >= 0.5 for "
             "L1L2L3-k3x5, -k3x6 and -k3x8, and block_ok under C3 is >= 0.5 for L1L2L3, -k3x2 and -k3x3 and <= 0.5 for "
             "-k3x5, -k3x6 and -k3x8, else FAILS.",
     "parts": [("weak: does not repair", [lv(a, "B", "block_ok") for a in ("L1L2L3", "L1L2L3-k3x2", "L1L2L3-k3x3")], "le", 0.5, "static"),
               ("strong: repairs", [lv(a, "B", "block_ok") for a in ("L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8")], "ge", 0.5, "static"),
               ("weak: does not impose", [lv(a, "C3", "block_ok") for a in ("L1L2L3", "L1L2L3-k3x2", "L1L2L3-k3x3")], "ge", 0.5, "static"),
               ("strong: imposes a corrupted store", [lv(a, "C3", "block_ok") for a in ("L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8")], "le", 0.5, "static")]},
    {"id": "T3",
     "words": "A block code that overrides a coherent block error restores the block's sign but not its minority "
              "regions: with the region codes corrupted, or with no region code, the block's minority regions stay "
              "wrong.",
     "rule": "HOLDS if at t = 2,000 under B, for L1L2L3-k3x5, -k3x6, -k3x8, L1L3-k3x4 and L1L3-k3x8, block_ok is >= 0.5 "
             "and bmin_ok is <= 0.5, else FAILS.",
     "parts": [("the block's sign restored", [lv(a, "B", "block_ok") for a in ("L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8", "L1L3-k3x4", "L1L3-k3x8")], "ge", 0.5, "static"),
               ("its minority regions not", [lv(a, "B", "bmin_ok") for a in ("L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8", "L1L3-k3x4", "L1L3-k3x8")], "le", 0.5, "static")]},
    {"id": "T4",
     "words": "In the relative hierarchy (region codes held relative to the block's store) the block store dictates at "
              "every gain tested: a coherent block error is repaired with its minority regions, and a corrupted block "
              "store re-specifies the whole block, its minority regions included.",
     "rule": "HOLDS if at t = 2,000, for L1L2rL3 and L1L2rL3-k3x0.25, block_ok and bmin_ok under B are >= 0.5 and "
             "block_ok and bmin_ok under C3 are <= 0.5, else FAILS.",
     "parts": [("repairs the block and its minority regions", [lv(a, "B", e) for a in ("L1L2rL3", "L1L2rL3-k3x0.25") for e in ("block_ok", "bmin_ok")], "ge", 0.5, "static"),
               ("imposes a corrupted store, minority regions included", [lv(a, "C3", e) for a in ("L1L2rL3", "L1L2rL3-k3x0.25") for e in ("block_ok", "bmin_ok")], "le", 0.5, "static")]},
    {"id": "T5",
     "words": "A block code derived from the region codes, with no store of its own, neither repairs a coherent block "
              "error that corrupted those codes nor is corrupted by a block store.",
     "rule": "HOLDS if at t = 2,000 L1L2L3d's block_ok is <= 0.5 under B and >= 0.5 under C3, else FAILS.",
     "parts": [("does not repair", [lv("L1L2L3d", "B", "block_ok")], "le", 0.5, "static"),
               ("is not corrupted", [lv("L1L2L3d", "C3", "block_ok")], "ge", 0.5, "static")]},
    {"id": "K1",
     "words": "In a wound that kills every copy at the region scale and below (a 2 x 2 square of regions), a block code "
              "fills the killed regions with the block's majority: killed minority regions are restored at least 0.15 "
              "less often with a block code than without one.",
     "rule": "HOLDS if at t = 2,000 under K the kill_min_ok of L1 less L1L3's, of L1L2 less L1L2L3's, and of L1L2 less "
             "L1L2rL3's (paired within block) are each >= 0.15, else FAILS.",
     "parts": [("killed minority regions, without minus with a block code",
                [diff("L1", "L1L3", "K", "kill_min_ok"), diff("L1L2", "L1L2L3", "K", "kill_min_ok"),
                 diff("L1L2", "L1L2rL3", "K", "kill_min_ok")], "ge", 0.15, "probe")]},
]


def items_of(part, runs):
    items = part[1]
    if items == "NONE_ARMS":
        return [lv(a, "none", "cell_err") for a in runs["none"]]
    return items


def value(item, get):
    if item[0] == "lv":
        return get(item[1], item[2], item[3])
    return get(item[1], item[3], item[4]) - get(item[2], item[3], item[4])


def label(item):
    return f"{item[1]}/{item[2]}/{item[3]}" if item[0] == "lv" else f"{item[1]}-{item[2]}/{item[3]}/{item[4]}"


def passes(x, threshold, sense):
    return bool(x >= threshold) if sense == "ge" else bool(x <= threshold)


def score(get, runs):
    """get(arm, event, endpoint) -> the item's value (a float: the mean over blocks at the last read)."""
    out = {}
    for s in STATEMENTS:
        parts = {}
        for name, _, sense, thr, kind in s["parts"]:
            items = items_of((name, _), runs)
            vals = {label(i): float(value(i, get)) for i in items}
            parts[name] = {"pass": all(passes(v, thr, sense) for v in vals.values()), "sense": sense,
                           "threshold": thr, "bound": kind, "items": vals}
        out[s["id"]] = {"verdict": "HOLDS" if all(p["pass"] for p in parts.values()) else "FAILS",
                        "words": s["words"], "rule": s["rule"], "parts": parts}
    return out


def margins(get_blocks, runs, k=3 * np.sqrt(1 / 4 + 1 / 16)):
    """BE002's rule on per-block values: SD_block = max(own SD, RMS of the part's SDs); margin = distance of the
    worst item's mean from the bound over its SD_block. get_blocks(arm, event, ep) -> per-block array."""
    out = {}
    for s in STATEMENTS:
        for name, _, sense, thr, kind in s["parts"]:
            items = items_of((name, _), runs)
            arrs = {label(i): np.asarray(value(i, get_blocks), float) for i in items}
            sds = {key: float(np.std(v, ddof=1)) for key, v in arrs.items()}
            rms = float(np.sqrt(np.mean([x ** 2 for x in sds.values()])))
            ms = {key: float(np.mean(v)) for key, v in arrs.items()}
            dist = {key: (m - thr if sense == "ge" else thr - m) for key, m in ms.items()}
            mg = {key: (dist[key] / max(sds[key], rms) if max(sds[key], rms) > 0 else float("inf")) for key in ms}
            worst = min(mg, key=lambda key: (mg[key], dist[key]))
            halves = [all(passes(float(np.mean(v[sl])), thr, sense) for v in arrs.values())
                      for sl in (slice(0, len(next(iter(arrs.values()))) // 2), slice(len(next(iter(arrs.values()))) // 2, None))]
            out[f"{s['id']} {name}"] = {"items": ms, "sds": sds, "rms_sd": rms, "worst": worst,
                                        "worst_mean": ms[worst], "worst_sd": sds[worst], "margin": mg[worst],
                                        "all_pass": all(passes(m, thr, sense) for m in ms.values()), "halves": halves,
                                        "threshold": thr, "sense": sense, "bound": kind,
                                        "ok": bool(mg[worst] >= k) or (kind == "static" and rms == 0)}
    return out
