"""Post-hoc descriptive read of BR001's saved development records (outside the frozen glob; not registered):
python -m br001.post.mechanisms --root DEV --out results/br001

Three questions about why five statements failed, answered from the final arrays only (no new simulation):
  A. commitment: under lasting impositions, do mismatch-gated writers stall the record partway, short of the
     bistable barrier at zero? (sites where the imposed message differs from the original)
  B. scar leakage: does a held scar change the body outside its patch, in the conserved and the open body?
  C. consensus and fine detail: does the self-correcting record lose the sites whose target sign differs
     from most of their neighbours (minority sites), and keep the others?
  D. lesion geometry (added after probe P8): does consensus repair depend on whether a lesion patch crosses
     one of the template's own walls (both signs inside the patch) or lies inside one domain?
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from br001 import design as D  # noqa: E402
from mse.native import neighbours  # noqa: E402

BLOCKS = range(*D.IDENTITIES["development"])


def raw(root, panel, r, b):
    return np.load(root / "raw" / panel / r / f"{b}.npz")


def commitment(root, cal):
    out = {}
    cp = [c.name for c in D.COND_P]
    for r in D.PANELS["P"]["regimes"]:
        th = cal["regimes"][r]["mismatch"]
        row = {"stall_point_full_region": round(-D.AMPLITUDE + float(np.sqrt(th)), 3)}
        for cond in ("impose-inf-cued", "impose-inf"):
            ci = cp.index(cond)
            for arm in ("write_always", "write_duration", "write_tags", "write_phase"):
                rs = []
                for b in BLOCKS:
                    z = raw(root, "P", r, b)
                    flip = np.sign(z["foreign"]) != np.sign(z["targets"])
                    want = np.sign(z["foreign"])[flip]
                    got = z[f"{arm}/R"][ci][flip] * want          # > 0: adopted; < 0: kept the old sign
                    rs.append(got)
                g = np.concatenate(rs)
                row[f"{cond}/{arm}"] = {"adopted": round(float((g > 0).mean()), 4),
                                        "stalled_0_to_0.9": round(float(((g <= 0) & (g > -0.9)).mean()), 4),
                                        "unwritten": round(float((g <= -0.9).mean()), 4),
                                        "median_old_sign_value": round(float(-np.median(g[g <= 0])) if (g <= 0).any() else 0.0, 3)}
        out[r] = row
    return out


def leakage(root):
    out = {}
    cp = [c.name for c in D.COND_P]
    for r in D.PANELS["P"]["regimes"]:
        row = {}
        for cond in ("sham", "scar-6x6"):
            ci = cp.index(cond)
            agree_v, agree_r, mean_shift = [], [], []
            for b in BLOCKS:
                z = raw(root, "P", r, b)
                m = z["mask"][cp.index("scar-6x6")]
                outside = ~m
                T = z["targets"]
                for arm, acc in (("write_none", agree_v), ("write_tags", agree_r)):
                    X = z[f"{arm}/V"][ci] if arm == "write_none" else z[f"{arm}/R"][ci]
                    acc.append((((X > 0) == (T > 0)) & outside).sum((-2, -1)) / outside.sum((-2, -1)))
                V = z["write_none/V"][ci]
                n_out = outside.sum((-2, -1))
                shift = ((V * outside).sum((-2, -1)) - (z["s0/V"] * outside).sum((-2, -1))) / n_out
                mean_shift.append(shift * np.sign(-(T * m).sum((-2, -1)) + 1e-12))
            row[cond] = {"none_body_agree_outside_patch": round(float(np.concatenate(agree_v).mean()), 4),
                         "tags_record_agree_outside_patch": round(float(np.concatenate(agree_r).mean()), 4),
                         "body_mean_shift_outside_patch_toward_scar": round(float(np.concatenate(mean_shift).mean()), 4)}
        out[r] = row
    return out


def consensus(root):
    out = {}
    for r in D.PANELS["L"]["regimes"]:
        lost_min, lost_maj, frac_min = [], [], []
        for b in BLOCKS:
            z = raw(root, "L", r, b)
            T = z["targets"]
            minority = np.sign(T) != np.sign(neighbours(np.sign(T)) + 1e-12)
            R = z["self/R"][0]                                     # sham
            lost = (R > 0) != (T > 0)
            lost_min.append((lost & minority).sum() / max(minority.sum(), 1))
            lost_maj.append((lost & ~minority).sum() / (~minority).sum())
            frac_min.append(minority.mean())
        out[r] = {"minority_site_fraction": round(float(np.mean(frac_min)), 4),
                  "self_sham_lost_at_minority_sites": round(float(np.mean(lost_min)), 4),
                  "self_sham_lost_at_other_sites": round(float(np.mean(lost_maj)), 4)}
    return out


def geometry(root):
    out = {}
    cl = [c.name for c in D.COND_L]
    for r in (D.regime("F0", 0.1), D.regime("BL", 0.1)):
        row = {}
        for s in D.SIZES:
            ci = cl.index(f"both-{s}x{s}")
            got = {"crossing": {"self": [], "multi": []}, "inside": {"self": [], "multi": []}}
            for b in BLOCKS:
                z = raw(root, "L", r, b)
                T, m = z["targets"], z["mask"][ci]
                for j in range(T.shape[0]):
                    inside = T[j][m[j]]
                    key = "crossing" if (inside > 0).any() and (inside < 0).any() else "inside"
                    for arm in ("self", "multi"):
                        got[key][arm].append(float((((z[f"{arm}/R"][ci][j] > 0) == (T[j] > 0))[m[j]]).mean()))
            row[f"both-{s}x{s}"] = {key: {"cases": len(v["self"]),
                                          **{arm: round(float(np.mean(x)), 4) if x else None for arm, x in v.items()}}
                                    for key, v in got.items()}
        out[r] = row
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cal = json.loads((Path(__file__).resolve().parents[1] / "frozen" / "calibration.json").read_text())
    res = {"note": "post-hoc, descriptive, not registered; final arrays of the development run",
           "A_commitment": commitment(a.root, cal), "B_scar_leakage": leakage(a.root), "C_consensus": consensus(a.root),
           "D_geometry": geometry(a.root)}
    (a.out / "mechanisms.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
