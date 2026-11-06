"""SM008's reader: the statement candidates X1-X6, the reported parts, the lane's margin rule and the freeze. DRAFT (phase A).

python -m sm008.predict --root STAGE_ROOT [--root ...] --out DIR     ->  DIR/predictions_scored.json
python -m sm008.predict --margins --root STAGE_ROOT [--out PATH]      ->  the rule's narrowest thresholds on the pilot (P64b)
python -m sm008.predict --freeze                                     ->  sm008/frozen/predictions.json (on the lead's word)

Pooling (PLAN_SM008.md): a part's value for a case j (0-7) is the sheet of that case at the named role and position,
averaged over the futures; "a role's members" averages over every position the role holds; X4's group terms average over
the sheets with case index j of either role. Per block the mean of its 8 cases; a part the mean over the blocks; SD =
max(block SD, case SD / sqrt 8). The statements read li4 (the primary body); dw's versions are reported. On the pilot each
part must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values the rule
allows. Development intervals: mean +- t(0.975, n - 1) SD / sqrt n. A part is pooled only where every task of the stage has
every term; anything less is marked unavailable with its task count.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm008 import design as D  # noqa: E402

K_RULE = D.K_RULE
FROZEN = LANE / "sm008" / "frozen" / "predictions.json"
# the registered thresholds (Amendment 1, the lead's phase-A rulings sent 16:32:58Z, after P64's values): X1-X3 at the rule's
# narrowest on P64b; X4 an equivalence band with frozen margins (E2E002's null margin). X5 (Q5's identity) and X6 are reported.
TH = {"X1": -0.03, "X2": 0.01, "X3": -0.03, "X4": (-0.01, 0.01)}
HIST_BINS = np.linspace(0.5, 1.0, 11)
ROLE_OFF = {"healthy": 0, "struggling": D.NCASE}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(roots, check=True):
    """Every task's endpoints and its branch maps, checked by sha256 against its stage's manifest."""
    tasks, manifests = [], []
    for root in ([roots] if isinstance(roots, (str, Path)) else roots):
        root = Path(root)
        M = json.loads((root / "manifest.json").read_text())
        manifests.append(M)
        for name, t in sorted(M["tasks"].items()):
            f = t["files"]["shards"]
            path = root / f["path"]
            if check and sha(path) != f["sha256"]:
                raise ValueError(f"{name}: the shard's sha256 differs from the manifest's")
            z = np.load(path)
            meta = json.loads(str(z["__meta__"]))
            ends = {k: z[k] for k in z.files if k != "__meta__"}
            tasks.append({"name": name, "meta": meta, "ends": ends, "block": meta["block"], "body": meta["body"],
                          "stage": meta["stage"], "labels": [a[0] for a in meta["arrangements"]]})
    return tasks, manifests[0]


# ---------------------------------------------------------------- per-case vectors
def _values(t, key, read):
    e = t["ends"]
    if key in ("a_v", "sign"):
        reads = [int(r) for r in e["reads"]]
        r = D.WINDOW if read is None else read
        i = reads.index(r) if r in reads else (len(reads) - 1 if read is None and reads else None)
        return None if i is None else e[key][i]
    return e[key]


def sel(label, role, pos=None, key="a_v", read=None, fn=None):
    """Per case j: the mean over the futures (and over positions, if pos is None) of the role's case j in `label`."""
    def f(t):
        if label not in t["labels"]:
            return None
        v = _values(t, key, read)
        if v is None:
            return None
        if fn is not None:
            v = fn(v)
        e, ai = t["ends"], t["labels"].index(label)
        out = np.empty(D.NCASE)
        for j in range(D.NCASE):
            b = (e["br_arr"] == ai) & (e["br_case"] == ROLE_OFF[role] + j)
            if pos is not None:
                b &= e["br_pos"] == pos
            if not b.any():
                return None
            out[j] = v[b].mean()
        return out
    return f


def group(label, key="a_v", read=None):
    """Per case index j: the mean over every sheet of `label` with case index j, either role, every position."""
    def f(t):
        if label not in t["labels"]:
            return None
        v = _values(t, key, read)
        if v is None:
            return None
        e, ai = t["ends"], t["labels"].index(label)
        out = np.empty(D.NCASE)
        for j in range(D.NCASE):
            b = (e["br_arr"] == ai) & (e["br_case"] % D.NCASE == j)
            if not b.any():
                return None
            out[j] = v[b].mean()
        return out
    return f


def comb(*terms):
    """A per-case linear combination of per-case vectors: terms (fn, coefficient)."""
    def f(t):
        vals = [(c, fn(t)) for fn, c in terms]
        if any(v is None for _c, v in vals):
            return None
        return sum(c * v for c, v in vals)
    return f


def block_matrix(tasks, fn, bodies=("li4",)):
    """(blocks, cases) for the tasks of the given bodies (per case the mean over the bodies); the blocks ascending; the
    coverage (tasks with every term, tasks in scope). None for x if any task in scope lacks a term."""
    by, have, scope = {}, 0, 0
    for t in tasks:
        if t["body"] not in bodies:
            continue
        scope += 1
        v = fn(t)
        if v is not None:
            have += 1
            by.setdefault(t["block"], []).append(v)
    if not by or have < scope:
        return None, [], (have, scope)
    blocks = sorted(by)
    return np.array([np.mean(by[b], axis=0) for b in blocks]), blocks, (have, scope)


def sd_rule(x):
    nb, nc = x.shape
    blk = x.mean(1)
    sd_b = float(blk.std(ddof=1)) if nb > 1 else float("nan")
    sd_c = float(x.ravel().std(ddof=1) / math.sqrt(nc)) if x.size > 1 else float("nan")
    return (max(sd_b, sd_c) if nb > 1 else sd_c), sd_b, sd_c


def value(x, blocks, stage):
    nb = x.shape[0]
    sd, sd_b, sd_c = sd_rule(x)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb) if nb > 1 else float("nan")
    H = D.HALVES.get(stage)
    if H is not None and all(b in blocks for h in H for b in h):
        halves = [float(np.mean([x[blocks.index(b)].mean() for b in h])) for h in H]
    else:
        halves = [float("nan"), float("nan")]
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd_block": sd_b, "sd_case": sd_c, "halves": halves,
            "blocks": x.mean(1).tolist(), "n_blocks": nb, "n_cases_a_block": int(x.shape[1]),
            "max_abs_case": float(np.abs(x).max())}


def _step(edge):
    return D.STEP_NEAR0 if abs(edge) < 0.01 else D.STEP


def narrowest(v, sd, halves, kind):
    need = K_RULE * sd
    lo, hi = min(v - need, *halves), max(v + need, *halves)
    flo = lambda x: round(math.floor(round(x / _step(x), 9)) * _step(x), 3)
    cei = lambda x: round(math.ceil(round(x / _step(x), 9)) * _step(x), 3)
    if kind == "in":
        return [flo(lo), cei(hi)]
    if kind == "ge":
        return flo(lo)
    return cei(hi)


def registers(kind, nar):
    if nar is None:
        return None
    return kind == "in" or (kind == "ge" and nar > 0) or (kind == "le" and nar <= D.AT_MOST_MAX)


# ---------------------------------------------------------------- the statement candidates (PLAN_SM008.md)
def x1(edge="absorbing", suffix=""):
    return comb((sel(f"k1-corner/{edge}{suffix}", "struggling", 0), 1), (sel(f"k8/{edge}{suffix}", "struggling", 0), -1))


def x2(edge="absorbing", suffix=""):
    return comb((sel(f"k7-corner/{edge}{suffix}", "healthy", 0), 1), (sel(f"k0/{edge}{suffix}", "healthy", 0), -1))


def x4(edge="absorbing"):
    return comb((group(f"k4-half/{edge}"), 1), (group(f"k0/{edge}"), -0.5), (group(f"k8/{edge}"), -0.5))


def x6(edge="absorbing"):
    return comb((sel(f"k1-inner/{edge}", "struggling", 1), 1), (sel(f"k1-corner/{edge}", "struggling", 0), -1))


def parts():
    return [
        ("X1", "a(F0 at corner 0 | k1-corner) - a(F0 at corner 0 | k8), absorbing: a lone struggler among healthy neighbours", x1(), "le"),
        ("X2", "a(S4 at corner 0 | k7-corner) - a(S4 at corner 0 | k0), absorbing: a lone healthy sheet among strugglers", x2(), "ge"),
        ("X3", "X1 with the edge sealed", x1("sealed"), "le"),
        ("X4", "group mean at k4-half - the mean of the k0 and k8 group means, absorbing", x4(), "in"),
        ("X5", "X1 under the preprint's stress (an identity: exactly 0 by the layout)", x1("absorbing", "/paper"), "in"),
        ("X6", "a(F0 at inner 1 | k1-inner) - a(F0 at corner 0 | k1-corner), absorbing: the lone struggler's position", x6(), "in"),
    ]


def reported():
    rows = []
    for pid, words, fn, _kind in parts():
        rows.append((f"{pid}/dw", f"dw (weaker S4_t1, stronger F0_t1): {words}", fn, ("dw",)))
    for edge in ("absorbing", "sealed"):
        for body in D.BODIES:
            sfx = "" if body == "li4" else "/dw"
            rows += [(f"CL/{edge}{sfx}", f"clustering ({edge}{', dw' if sfx else ''}): a(struggling | k4-half) - a(struggling | k4-checker), "
                      f"the same mix of corners and inner cells",
                      comb((sel(f"k4-half/{edge}", "struggling"), 1), (sel(f"k4-checker/{edge}", "struggling"), -1)), (body,)),
                     (f"K2/{edge}{sfx}", f"k2 ({edge}{', dw' if sfx else ''}): a(struggling | k2-adjacent, an inner pair) - "
                      f"a(struggling | k2-apart, opposite corners)",
                      comb((sel(f"k2-adjacent/{edge}", "struggling"), 1), (sel(f"k2-apart/{edge}", "struggling"), -1)), (body,))]
    rows += [("X1/shared", "lambda 2: a(struggler at corner 0 | k1-corner) - a(same | k8)", x1("absorbing", "/shared"), ("li4",)),
             ("X2/shared", "lambda 2: a(healthy at corner 0 | k7-corner) - a(same | k0)", x2("absorbing", "/shared"), ("li4",)),
             ("X1/shared/dw", "dw, lambda 2: X1", x1("absorbing", "/shared"), ("dw",)),
             ("X2/shared/dw", "dw, lambda 2: X2", x2("absorbing", "/shared"), ("dw",))]
    for edge in ("absorbing", "sealed"):
        rows += [(f"P8/{edge}", f"pure struggling ({edge}): a(at inner 1) - a(at corner 0)",
                  comb((sel(f"k8/{edge}", "struggling", 1), 1), (sel(f"k8/{edge}", "struggling", 0), -1)), ("li4",)),
                 (f"P0/{edge}", f"pure healthy ({edge}): a(at inner 1) - a(at corner 0)",
                  comb((sel(f"k0/{edge}", "healthy", 1), 1), (sel(f"k0/{edge}", "healthy", 0), -1)), ("li4",))]
    for key, nm in (("expo_mean", "exposure"), ("gain_mean", "gain"), ("stress_mean", "stress")):
        rows += [(f"X1/{nm}", f"X1's {nm} (window mean): the struggler at corner 0, k1-corner - k8",
                  comb((sel("k1-corner/absorbing", "struggling", 0, key=key), 1), (sel("k8/absorbing", "struggling", 0, key=key), -1)), ("li4",)),
                 (f"X2/{nm}", f"X2's {nm} (window mean): the healthy sheet at corner 0, k7-corner - k0",
                  comb((sel("k7-corner/absorbing", "healthy", 0, key=key), 1), (sel("k0/absorbing", "healthy", 0, key=key), -1)), ("li4",))]
    return rows


def _score_one(tasks, pid, words, fn, kind, stage, th, bodies=("li4",)):
    x, blocks, cov = block_matrix(tasks, fn, bodies)
    if x is None:
        return {"id": pid, "part": words, "kind": kind, "available": False, "tasks": cov[0], "of": cov[1]}
    rec = {"id": pid, "part": words, "kind": kind, "available": True, "tasks": cov[0], "of": cov[1], **value(x, blocks, stage)}
    fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
    nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if (fin and kind) else None
    rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar) if kind else None, zero_sd=bool(rec["sd"] == 0))
    t = th.get(pid)
    if t is not None:
        v, sd = rec["value"], rec["sd"]
        dv = lambda z: z / sd if sd > 0 else (float("inf") if z > 0 else (0.0 if z == 0 else float("-inf")))
        if kind == "in":
            rec.update(threshold=list(t), holds=t[0] <= v <= t[1], margins=[dv(v - t[0]), dv(t[1] - v)])
        elif kind == "ge":
            rec.update(threshold=t, holds=v >= t, margins=[dv(v - t)])
        else:
            rec.update(threshold=t, holds=v <= t, margins=[dv(t - v)])
    return rec


def score(tasks, th=None, stage=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    return [_score_one(tasks, pid, w, fn, kind, stage, th) for pid, w, fn, kind in parts()]


def score_reported(tasks, stage=None):
    stage = stage or tasks[0]["stage"]
    return [_score_one(tasks, rid, w, fn, None, stage, {}, bodies) for rid, w, fn, bodies in reported()]


def x5_exact(tasks):
    """The preprint's mixing identity, sheet by sheet: every sheet of k1-corner/absorbing/paper against the sheet at the
    same (future, group, position) of k8 (struggling positions) or k0 (healthy positions), under the paper stress."""
    worst, n = 0.0, 0
    for t in tasks:
        e, labs = t["ends"], t["labels"]
        if not all(x in labs for x in ("k1-corner/absorbing/paper", "k0/absorbing/paper", "k8/absorbing/paper")):
            return None
        def at(label):
            ai = labs.index(label)
            return {(int(f), int(g), int(p)): i for i, (f, g, p) in enumerate(zip(e["br_future"], e["br_group"], e["br_pos"]))
                    if e["br_arr"][i] == ai}
        mix, h, s = at("k1-corner/absorbing/paper"), at("k0/absorbing/paper"), at("k8/absorbing/paper")
        for kk, i in mix.items():
            j = s[kk] if e["br_case"][i] >= D.NCASE else h[kk]
            for key in ("a_v", "sign"):
                worst = max(worst, float(np.abs(e[key][:, i] - e[key][:, j]).max()))
            for key in ("gain_mean", "expo_mean", "stress_mean"):
                worst = max(worst, abs(float(e[key][i] - e[key][j])))
            n += 1
    return {"sheets": n, "largest_difference": worst, "exact": worst == 0.0}


def levels(tasks):
    """Every arrangement's pooled level by body and role: a at every read, rescued, mean gain, exposure and stress; the
    group mean; the per-sheet histogram of a at the last read."""
    labels = tasks[0]["labels"]
    reads = [int(r) for r in tasks[0]["ends"]["reads"]]
    out = {}
    for body in D.BODIES:
        for lab in labels:
            rec = {}
            for role in ("healthy", "struggling"):
                x, _b, _c = block_matrix(tasks, sel(lab, role), (body,))
                if x is None:
                    rec[role] = None
                    continue
                rr = {f"a_{r}": float(block_matrix(tasks, sel(lab, role, read=r), (body,))[0].mean()) for r in reads}
                rr["rescued"] = float(block_matrix(tasks, sel(lab, role, fn=lambda v: (v >= D.RESCUED).astype(float)), (body,))[0].mean())
                for key in ("gain_mean", "expo_mean", "stress_mean"):
                    rr[key] = float(block_matrix(tasks, sel(lab, role, key=key), (body,))[0].mean())
                rec[role] = rr
            x, _b, _c = block_matrix(tasks, group(lab), (body,))
            rec["group_mean"] = None if x is None else float(x.mean())
            ai = labels.index(lab)
            sheets = np.concatenate([t["ends"]["a_v"][-1][t["ends"]["br_arr"] == ai] for t in tasks
                                     if t["labels"] == labels and t["body"] == body])
            rec["hist"] = np.histogram(sheets, bins=HIST_BINS)[0].tolist() if len(sheets) else []
            out[f"{body}|{lab}"] = rec
    return out


def margins(roots):
    """P64b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(roots)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    rep = score_reported(tasks, stage)
    print(f"P64b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.5f} SD {p['sd']:.5f} (block {p['sd_block']:.5f}, case {p['sd_case']:.5f}) "
              f"halves {p['halves'][0]:+.5f} {p['halves'][1]:+.5f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']}")
    return {"k_rule": K_RULE, "stage": stage, "root": str(roots), "design_digest": D.digest(), "parts": sc, "reported": rep,
            "x5_exact": x5_exact(tasks), "levels": levels(tasks), "hist_bins": HIST_BINS.tolist()}


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P64's margins and the lead's ruling come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f, _b in reported()], "predict_sha256": sha(Path(__file__))}
    FROZEN.parent.mkdir(exist_ok=True)
    FROZEN.write_text(json.dumps(rec, indent=1) + "\n")
    print(FROZEN, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True, action="append")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    roots = a.root if len(a.root) > 1 else a.root[0]
    if a.margins:
        rec = margins(roots)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(rec, indent=1) + "\n")
        return
    tasks, M = load(roots)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": [str(r) for r in a.root] if len(a.root) > 1 else str(a.root[0]),
         "design_digest": D.digest(), "parts": scored,
         "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "reported": rep, "x5_exact": x5_exact(tasks), "levels": levels(tasks), "hist_bins": HIST_BINS.tolist(),
         "thresholds": {k: (list(v) if isinstance(v, tuple) else v) for k, v in TH.items()}}, indent=1) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.5f} [{p['ci95'][0]:+.5f}, {p['ci95'][1]:+.5f}] SD {p['sd']:.5f} halves "
              f"{p['halves'][0]:+.5f} {p['halves'][1]:+.5f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
