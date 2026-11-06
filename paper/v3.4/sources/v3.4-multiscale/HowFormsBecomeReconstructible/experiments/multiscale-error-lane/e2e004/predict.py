"""E2E004's reader: the statement candidates (G1-G4), the declared trade-off reading, the reported parts, the lane's
margin rule and the freeze. DRAFT (phase A).

python -m e2e004.predict --root STAGE_ROOT --out DIR     ->  DIR/predictions_scored.json
python -m e2e004.predict --margins --root STAGE_ROOT     ->  the rule's narrowest thresholds on the stage (P60b)
python -m e2e004.predict --freeze                         ->  e2e004/frozen/predictions.json (phase B, on the lead's word)

Pooling (the AR studies'): per case (block, message, parent) the mean over the unit-body pairs and the futures; a block's
value the mean of its cases; a part the mean over the blocks. SD = max(block SD, case SD / sqrt(cases a block)). On the
pilot each part must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values
the rule allows (hundredths, or 0.005 within 0.01 of zero). Development intervals: mean +- t(0.975, n - 1) SD / sqrt n.
Coverage (E2E001's lesson): a part or a level is pooled only where every task of the stage has every term; anything less
is marked partial, with its task count, never pooled. There are no detectors in E2E004, so there are no per-event
quantities.
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
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e004 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds, from P60 by the rule (P60b, probes/results/p60b_e2e004_margins.txt, 15:26Z on 4 November): G1 and G2
# at the rule's narrowest bounds above 0; G3 and G4 at their narrowest bands
TH = {"G1": 0.18, "G2": 0.2, "G3": [0.19, 0.27], "G4": [-0.28, -0.1]}
B_P, V_P, R_P, V1_P = "body/protected", "vote/protected", "record/protected", "vote1/protected"
B_X, V_X, R_X, V1_X = "body/post", "vote/post", "record/post", "vote1/post"
TRADE_ROUTES = ("body", "vote", "record", "vote1")    # the declared reading: every route run
CORE_ROUTES = ("body", "vote", "record")             # and over AR001's three fixed policies (disclosed: added after P60)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root, check=True):
    """Every task's endpoints and its row map, checked by sha256 against the stage's manifest."""
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    tasks = []
    for name, t in sorted(M["tasks"].items()):
        f = t["files"]["shards"]
        path = root / f["path"]
        if check and sha(path) != f["sha256"]:
            raise ValueError(f"{name}: the shard's sha256 differs from the manifest's")
        z = np.load(path)
        meta = json.loads(str(z["__meta__"]))
        ends = {k: z[k] for k in z.files if k != "__meta__"}
        tasks.append({"name": name, "meta": meta, "ends": ends, "block": meta["block"], "body": meta["body"],
                      "unit": meta["unit"], "stage": meta["stage"]})
    return tasks, M


def val_f(task, label, e, g, kind="g"):
    """{future: (cases,)}: `label`'s endpoint (kind "g") or diagnostic (kind "d") at generation g in every future that
    ran its row ({None: ...} at g 0); None if the task has no such row."""
    lab = task["meta"]["labels"]
    if label not in lab:
        return None
    i = lab[label]
    E = task["ends"]
    if g == 0 and kind == "g":
        return {None: E[f"g0/{e}"][i]}
    out = {}
    for f in range(task["meta"]["futures"]):
        key = f"f{f}/{kind}{g}/rows"
        if key in E:
            rows = list(E[key])
            if i in rows:
                out[f] = E[f"f{f}/{kind}{g}/{e}"][rows.index(i)]
    return out or None


def lin(*terms):
    """sum of c x endpoint over terms (c, label, e, g[, kind]), paired within each future: the mean over the futures in
    which every term with g > 0 ran; None where a term is missing."""
    def f(task):
        vals = []
        for term in terms:
            c, label, e, g = term[:4]
            v = val_f(task, label, e, g, term[4] if len(term) > 4 else "g")
            if v is None:
                return None
            vals.append((c, v))
        futs = None
        for _c, v in vals:
            if None not in v:
                futs = set(v) if futs is None else futs & set(v)
        if futs is None:
            return sum(c * v[None] for c, v in vals)
        if not futs:
            return None
        return np.mean([sum(c * (v[None] if None in v else v[fu]) for c, v in vals) for fu in sorted(futs)], axis=0)
    return f


def block_matrix(tasks, fn, subset=None):
    """(blocks, cases): per case the mean over the unit-body pairs; the block order ascending; and the coverage
    (tasks with every term, tasks in scope). None for x if any task in scope lacks a term (partial coverage)."""
    by, have, scope = {}, 0, 0
    for t in tasks:
        if subset is not None and (t["body"], t["unit"]) not in subset:
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
    sd_c = float(x.ravel().std(ddof=1) / math.sqrt(nc))
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
            "blocks": x.mean(1).tolist(), "n_blocks": nb, "n_cases_a_block": int(x.shape[1])}


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


def parts():
    return [
        ("G1", "the vote keeps more history than the body route: q_r(vote/protected) - q_r(body/protected), g 8",
         lin((1, V_P, "q_r", 8), (-1, B_P, "q_r", 8)), "ge"),
        ("G2", "the body route heals an inherited error more: u_r(body/post) - u_r(vote/post), g 8",
         lin((1, B_X, "u_r", 8), (-1, V_X, "u_r", 8)), "ge"),
        ("G3", "the record route against the vote, keeping: q_r(record/protected) - q_r(vote/protected), g 8",
         lin((1, R_P, "q_r", 8), (-1, V_P, "q_r", 8)), "in"),
        ("G4", "the record route against the vote, healing: u_r(record/post) - u_r(vote/post), g 8",
         lin((1, R_X, "u_r", 8), (-1, V_X, "u_r", 8)), "in"),
    ]


def reported():
    out = []
    for g in (1, 3, 8):
        for e in ("q_r", "u_r", "u_v"):
            out.append((f"R-keep-vb-{e}-{g}", f"{e}(vote/protected) - {e}(body/protected), g {g}",
                        lin((1, V_P, e, g), (-1, B_P, e, g))))
            out.append((f"R-keep-rv-{e}-{g}", f"{e}(record/protected) - {e}(vote/protected), g {g}",
                        lin((1, R_P, e, g), (-1, V_P, e, g))))
            out.append((f"R-keep-v1v-{e}-{g}", f"{e}(vote1/protected) - {e}(vote/protected), g {g} (the second copy)",
                        lin((1, V1_P, e, g), (-1, V_P, e, g))))
            out.append((f"R-keep-v1b-{e}-{g}", f"{e}(vote1/protected) - {e}(body/protected), g {g}",
                        lin((1, V1_P, e, g), (-1, B_P, e, g))))
        for e in ("u_r", "u_v", "q_r"):
            out.append((f"R-heal-bv-{e}-{g}", f"{e}(body/post) - {e}(vote/post), g {g}", lin((1, B_X, e, g), (-1, V_X, e, g))))
            out.append((f"R-heal-rv-{e}-{g}", f"{e}(record/post) - {e}(vote/post), g {g}", lin((1, R_X, e, g), (-1, V_X, e, g))))
            out.append((f"R-heal-v1v-{e}-{g}", f"{e}(vote1/post) - {e}(vote/post), g {g} (the second copy)",
                        lin((1, V1_X, e, g), (-1, V_X, e, g))))
            out.append((f"R-heal-v1b-{e}-{g}", f"{e}(vote1/post) - {e}(body/post), g {g}", lin((1, V1_X, e, g), (-1, B_X, e, g))))
    for route in ("body", "vote", "record"):
        for g in (1, 3, 8):
            out.append((f"R-vms-{route}-{g}", f"u_r({route}/vms) - u_r({route}/post), g {g} (the repaired record)",
                        lin((1, f"{route}/vms", "u_r", g), (-1, f"{route}/post", "u_r", g))))
    return out


LEVEL_ENDS = ("u_r", "u_v", "a_r", "q_r", "q_v", "u_r_raw", "agree_in")


def labels_of(tasks):
    out = []
    for t in tasks:
        for lab in t["meta"]["labels"]:
            if lab not in out:
                out.append(lab)
    return out


def pooled(tasks, fn):
    """The pooled value overall and by item set, with the coverage; partial coverage is marked, not pooled."""
    x, _b, cov = block_matrix(tasks, fn)
    rec = {"tasks": cov[0], "of": cov[1]}
    if x is None:
        rec["partial"] = cov[0] > 0
        return rec
    rec["all"] = float(x.mean())
    for name, subset in D.ITEM_SETS.items():
        xs, _bs, _c = block_matrix(tasks, fn, set(subset))
        if xs is not None:
            rec[name] = float(xs.mean())
    return rec


def levels(tasks):
    """Every label's pooled endpoint at generations 0, 1, 3 and 8, overall and by item set, with its coverage."""
    out = {}
    for label in labels_of(tasks):
        for e in LEVEL_ENDS:
            for g in (0,) + D.HORIZONS:
                rec = pooled(tasks, lin((1, label, e, g)))
                if rec["tasks"]:
                    out[f"{label}|{e}|{g}"] = rec
    return out


def trade_off(tasks, g=8, routes=TRADE_ROUTES):
    """The declared trade-off reading: rank the routes run by q_r(protected) (keeping) and by u_r(post) (healing) at g;
    the reading holds where the order by keeping, most first, is the order by healing, least first. Overall and by set."""
    out = {}
    for name, subset in (("all", None),) + tuple(D.ITEM_SETS.items()):
        keep, heal = {}, {}
        for route in routes:
            xk, _b, _c = block_matrix(tasks, lin((1, f"{route}/protected", "q_r", g)), None if subset is None else set(subset))
            xh, _b, _c = block_matrix(tasks, lin((1, f"{route}/post", "u_r", g)), None if subset is None else set(subset))
            if xk is not None and xh is not None:
                keep[route], heal[route] = float(xk.mean()), float(xh.mean())
        by_keep = sorted(keep, key=lambda r: -keep[r])
        by_heal = sorted(heal, key=lambda r: heal[r])
        out[name] = {"keep_q_r": keep, "heal_u_r": heal, "order_by_keeping": by_keep, "order_by_healing_least_first": by_heal,
                     "reversed": bool(len(keep) >= 2 and by_keep == by_heal)}
    return out


def score(tasks, th=None, stage=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    out = []
    for pid, words, fn, kind in parts():
        x, blocks, cov = block_matrix(tasks, fn)
        if x is None:
            out.append({"id": pid, "part": words, "kind": kind, "available": False, "tasks": cov[0], "of": cov[1]})
            continue
        rec = {"id": pid, "part": words, "kind": kind, "available": True, "tasks": cov[0], "of": cov[1],
               **value(x, blocks, stage)}
        fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
        nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if fin else None
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar), zero_sd=bool(rec["sd"] == 0))
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
        by_set = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                by_set[name] = {"value": float(xs.mean()), "blocks": xs.mean(1).tolist()}
        rec["by_item_set"] = by_set
        out.append(rec)
    return out


def score_reported(tasks, stage=None):
    stage = stage or tasks[0]["stage"]
    out = []
    for rid, words, fn in reported():
        x, blocks, cov = block_matrix(tasks, fn)
        if x is None:
            out.append({"id": rid, "part": words, "available": False, "tasks": cov[0], "of": cov[1]})
            continue
        rec = {"id": rid, "part": words, "available": True, "tasks": cov[0], "of": cov[1], **value(x, blocks, stage)}
        rec["by_item_set"] = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                rec["by_item_set"][name] = float(xs.mean())
        out.append(rec)
    return out


def aliases(tasks):
    """Per part, the tasks in which its two lineages ran on one row (an alias: the difference is exactly 0 there)."""
    pairs = {"G1": (V_P, B_P), "G2": (B_X, V_X), "G3": (R_P, V_P), "G4": (R_X, V_X)}
    out = {}
    for pid, (a, b) in pairs.items():
        out[pid] = sum(1 for t in tasks if a in t["meta"]["labels"] and b in t["meta"]["labels"]
                       and t["meta"]["labels"][a] == t["meta"]["labels"][b])
    return out


def margins(root):
    """P58b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(root)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    al = aliases(tasks)
    print(f"P60b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']} aliased tasks {al[p['id']]}"
              + "  by set " + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p["by_item_set"].items()))
    return sc, al


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P58's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e004" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    if a.margins:
        sc, al = margins(a.root)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps({"k_rule": K_RULE, "parts": sc, "aliased_tasks": al}, indent=1) + "\n")
        return
    tasks, M = load(a.root)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root), "design_digest": D.digest(), "parts": scored,
         "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "aliased_tasks": aliases(tasks), "trade_off": trade_off(tasks),
         "trade_off_core": trade_off(tasks, routes=CORE_ROUTES), "reported": rep, "levels": levels(tasks)},
        indent=1) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
