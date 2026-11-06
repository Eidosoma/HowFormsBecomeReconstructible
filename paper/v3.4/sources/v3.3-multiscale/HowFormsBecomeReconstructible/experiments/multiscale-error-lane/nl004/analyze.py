"""NL004's frozen reader: per-case values, block means, the registered parts and the reported contrasts.

python -m nl004.analyze --root RUN_ROOT --stage {smoke,probe,preflight,debug,development} [--out DIR]

A part is a sum of coefficient x endpoint terms, each term one (unit, key, branch) at the last read; it is formed per
case (every term of a part is paired within the case: the same acquisitions, anchor sites, noise and event). A block's
value is the mean over its 8 cases, an undefined case (NaN: a killed square with no differing region, NL002's
Amendment 1) left out; the part is the mean over the blocks, unrounded. SD_block is the larger of the SD over the block values and
the SD over every defined case divided by sqrt(8); the 95% interval is the mean +- t(0.975, n - 1) SD_block / sqrt(n).
Keys: 't/r/<e>' and 't/v/<e>' the tissue's record and body, 't/a/<e>' the arbiter's refused shares and the anchors'
shares, 's/<e>' the L1-only recipient (labels, then A's and B's acquired records and nothing), 'c/<e>' the coded
recipient (labels), 'g/<e>' the coded recipient gated by the parent's given anchors (design.parent_gated), 'm/<e>' the
coded recipient gated by anchors the successor makes from the record it inherits (labels).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from nl004 import design as D  # noqa: E402


def load(root, blocks, units=D.UNITS):
    """data[unit] = {'meta': [...], key: (blocks, reads, branches, cases)}; the branch names per key family."""
    data = {}
    for u in units:
        arrs, metas = {}, []
        for b in blocks:
            with np.load(root / "shards" / u / f"{b}.npz") as z:
                meta = json.loads(str(z["__meta__"]))
                metas.append(meta)
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[u] = {k: np.stack(v) for k, v in arrs.items()}
        m0 = metas[0]
        assert all(m["labels"] == m0["labels"] and m["gated"] == m0["gated"] for m in metas)
        names = [f"{a}/{e}" for a, e in m0["labels"]]
        rnames = [f"{a}/{e}" for a, e in m0.get("rlabels", [])]
        data[u]["_names"] = {"t/": names, "c/": rnames, "s/": rnames + list(m0["succ"]), "g/": list(m0["parent_gated"]),
                             "m/": rnames}
        data[u]["_meta"] = metas
    return data


def case_values(data, unit, key, branch, read=-1):
    """(blocks, cases): one endpoint of one branch at one read."""
    fam = key[:2]
    names = data[unit]["_names"][fam]
    return data[unit][key][:, read, names.index(branch), :]


def part_cases(data, terms):
    """(blocks, cases): sum of coefficient x term, paired within the case."""
    return sum(c * case_values(data, u, k, b) for c, u, k, b in terms)


def estimate(x):
    """x (blocks, cases) -> value, SD_block, the two SDs, the 95% interval, the halves, the block values."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        blk = np.nanmean(x, axis=1)
    n = len(blk)
    v = float(np.mean(blk))
    sd4 = float(np.std(blk, ddof=1)) if n > 1 else float("nan")
    flat = x[np.isfinite(x)]
    sdc = float(np.std(flat, ddof=1) / math.sqrt(x.shape[1])) if flat.size > 1 else float("nan")
    sd = max(sd4, sdc)
    h = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if n > 1 else float("nan")
    return {"value": v, "sd": sd, "sd_block": sd4, "sd_case8": sdc, "ci95": [v - h, v + h],
            "halves": [float(np.mean(blk[: n // 2])), float(np.mean(blk[n // 2:]))], "blocks": [float(b) for b in blk]}


def levels(data, keys=None):
    """L[unit][key][branch] = [mean over blocks of the block means] at each read (unrounded), for the summaries."""
    L = {}
    for u, arrs in data.items():
        node = L.setdefault(u, {})
        for key, x in arrs.items():
            if key.startswith("_") or (keys is not None and key.split("/")[-1] not in keys) or key[:2] not in ("t/", "s/", "c/", "g/", "m/"):
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                bm = np.nanmean(x, axis=-1)                         # (blocks, reads, branches)
            names = arrs["_names"][key[:2]]
            node[key] = {nm: [round(float(np.mean(bm[:, ti, bi])), 6) for ti in range(bm.shape[1])] for bi, nm in enumerate(names)}
    return L


STORE = ("align_A", "region_ok_A", "min_reg_ok_A", "min_cell_ok_A", "ev_reg_ok", "spec_reg", "k_spec_reg", "k_reg_ok_A",
         "ref_all", "ref_dreg", "ref_other", "ever", "anc_present", "anc_A", "anc_B", "anc_A_min", "anc_A_ev", "anc_A_kill",
         "anc_B_kill", "anc_A_dreg", "anc_B_dreg", "anc_A_kd", "anc_B_kd")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("smoke", "probe", "preflight", "debug", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl004")
    a = ap.parse_args()
    from nl004.predict import score
    blocks = D.stage_blocks(a.stage)
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    S = score(data)
    L = levels(data, STORE)
    head = {"stage": a.stage, "blocks": blocks, "design_digest": D.digest(), "rule": D.RULE, "units": list(D.UNITS),
            "reads": list(D.READS), "reads2": list(D.READS2)}
    for u in D.UNITS:
        (a.out / f"summary_{u}.json").write_text(json.dumps(dict(head, levels=L[u]), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in S.items() if isinstance(v, dict) and "verdict" in v}))


if __name__ == "__main__":
    main()
