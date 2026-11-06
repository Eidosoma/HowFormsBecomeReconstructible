"""E2E007's reader: the statement candidates Z1-Z5, Z1x, Z3x, the reported parts, the observer, the exposures, the lane's
margin rule and the freeze. DRAFT (phase A).

python -m e2e007.predict --root ROOT --out DIR     ->  DIR/predictions_scored.json and DIR/levels.json
python -m e2e007.predict --margins --root ROOT     ->  the rule's narrowest thresholds on the stage (P66b)
python -m e2e007.predict --freeze                  ->  e2e007/frozen/predictions.json (phase B, on the lead's word)

Pooling (E2E006's): per case (block, message, parent) the mean over the unit-body pairs and the futures; a block's value the
mean of its cases; a part the mean over the blocks. SD = max(block SD, case SD / sqrt(cases a block)). On the pilot each
part must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values the rule
allows (hundredths, or 0.005 within 0.01 of zero); an "at least" registers only above 0, an "at most" only at or below
0.05. Development intervals: mean +- t(0.975, n - 1) SD / sqrt n. Coverage: a part or a level is pooled only where every
task of the stage has every term. Kinds of value: "g" a lineage's read at generation g (the field present where the row has
one), "x" the fresh successor's read after generation g (field-free), "d" a diagnostic of generation g.
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

from e2e006.predict import block_matrix, lin, load, val_f  # noqa: E402  (frozen: the stage reader's machinery)
from e2e007 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the registered thresholds (Amendment 1: the lead's rulings of 23:16:21Z, the rule's narrowest on P66); Z3 and Z3x in the
# direction P66 showed, written after its values against the plan's declared "at least" (as E2E006's H1-H3 were)
TH = {"Z1": 0.17, "Z2": 0.09, "Z3": 0.02, "Z4": 0.07, "Z5": -0.03, "Z1x": 0.19, "Z3x": -0.01}
G = D.G_MAIN
NM, RM, XM, NB, RB, XB = ("none/memory", "raise/memory", "relax/memory", "none/body", "raise/body", "relax/body")
XMM = "relax-matched/memory"    # Amendment 1: reported, not registered


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def d(a, b, e, g, kind="g"):
    return lin((1, a, e, g, kind), (-1, b, e, g, kind))


def inter(e, g, kind="g"):
    """the interaction: [raise/body - none/body] - [raise/memory - none/memory]"""
    return lin((1, RB, e, g, kind), (-1, NB, e, g, kind), (-1, RM, e, g, kind), (1, NM, e, g, kind))


# the statement candidates (PLAN_E2E007.md; kinds declared before any value): id -> (function maker, g, kind, words)
PARTS = {
    "Z1": (lambda g: d(XM, NM, "U_v", g), G, "ge", "the opposite response under memory injury, present organization: "
                                                   "U_v(relax/memory) - U_v(none/memory), g 8"),
    "Z2": (lambda g: d(XM, NM, "q_r", g), G, "ge", "the opposite response under memory injury, history: q_r(relax/memory) - "
                                                   "q_r(none/memory), g 8"),
    "Z3": (lambda g: d(RB, NB, "U_v", g), G, "le", "the ruled response under body injury, present organization: "
                                                   "U_v(raise/body) - U_v(none/body), g 8 (at most: reversed after "
                                                   "P66's values, Amendment 1)"),
    "Z4": (lambda g: inter("U_v", g), G, "ge", "the interaction: [U_v(raise/body) - U_v(none/body)] - [U_v(raise/memory) - "
                                               "U_v(none/memory)], g 8"),
    "Z5": (lambda g: d(XB, NB, "U_v", g), G, "le", "the opposite response under body injury: U_v(relax/body) - "
                                                   "U_v(none/body), g 8"),
    "Z1x": (lambda g: d(XM, NM, "U_v", g, "x"), G, "ge", "what the record carries, the opposite response under memory "
                                                         "injury: the fresh successor's U_v, relax/memory - none/memory, "
                                                         "after g 8"),
    "Z3x": (lambda g: d(RB, NB, "U_v", g, "x"), G, "le", "what the record carries, the ruled response under body injury: "
                                                         "the fresh successor's U_v, raise/body - none/body, after g 8 "
                                                         "(at most: reversed after P66's values, Amendment 1)"),
}
KINDS = {pid: v[2] for pid, v in PARTS.items()}
WORDS = {pid: v[3] for pid, v in PARTS.items()}
FIELD_ROWS = (RM, XM, RB, XB, XMM)


def parts():
    return [(pid, w, fn(g), kind) for pid, (fn, g, kind, w) in PARTS.items()]


def reported():
    """The parts at generations 1 and 3 (the lineage's); under body injury q_r and the fresh successor's q_r, raise and
    relax against none; raise - none under memory injury (E2E006's direction); relax - raise under each target; a_v; the
    observer's agreement (relax and raise against none) at each of its updates."""
    out = []
    for g in (1, 3):
        for pid, (fn, gp, _kind, w) in PARTS.items():
            if not pid.endswith("x"):
                out.append((f"R-{pid}-{g}", f"{w} [at g {g}]", fn(g)))
    for g in D.HORIZONS:
        for name, (a, b) in {"raise-none-memory": (RM, NM), "relax-none-memory": (XM, NM), "raise-none-body": (RB, NB),
                             "relax-none-body": (XB, NB), "relax-raise-memory": (XM, RM),
                             "relax-raise-body": (XB, RB), "matched-none-memory": (XMM, NM),
                             "matched-relax-memory": (XMM, XM)}.items():
            for e in ("U_v", "q_r", "a_v", "U"):
                out.append((f"R-{name}-{e}-{g}", f"{e}({a}) - {e}({b}), g {g}", d(a, b, e, g)))
        out.append((f"R-inter-q_r-{g}", f"the interaction in q_r, g {g}", inter("q_r", g)))
    for g in D.FRESH_AT:
        for name, (a, b) in {"raise-none-memory": (RM, NM), "relax-none-memory": (XM, NM), "raise-none-body": (RB, NB),
                             "relax-none-body": (XB, NB), "matched-none-memory": (XMM, NM),
                             "matched-relax-memory": (XMM, XM)}.items():
            for e in ("U_v", "q_r", "a_v", "q_v"):
                out.append((f"R-{name}-fresh-{e}-{g}", f"the fresh successor's {e}, {a} - {b}, after g {g}",
                            d(a, b, e, g, "x")))
        out.append((f"R-inter-fresh-U_v-{g}", f"the interaction in the fresh successor's U_v, after g {g}",
                    inter("U_v", g, "x")))
    for g in D.HORIZONS:
        for o in D.OBS:
            for name, (a, b) in {"raise-none-body": (RB, NB), "relax-none-body": (XB, NB), "raise-none-memory": (RM, NM),
                                 "relax-none-memory": (XM, NM), "matched-none-memory": (XMM, NM)}.items():
                out.append((f"R-agree_{o}-{name}-{g}", f"the observer's agreement at '{o}', {a} - {b}, g {g}",
                            d(a, b, f"agree_{o}", g, "d")))
    return out


LEVEL_ENDS = ("U", "U_v", "U_raw", "agree_U", "u_r", "u_v", "a_r", "a_v", "q_r", "q_v")
FRESH_ENDS = ("U", "U_v", "a_r", "a_v", "q_r", "q_v")
FIELD_DIAG = ("exp_full", "exp_early", "exp_late", "kexp")
OBS_DIAG = tuple(f"agree_{o}" for o in D.OBS)


def labels_of(tasks):
    out = []
    for t in tasks:
        for lab in t["meta"]["labels"]:
            if lab not in out:
                out.append(lab)
    return out


def row_of(task, label):
    return task["meta"]["rows"][task["meta"]["labels"][label]]


def pooled(tasks, fn):
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


def gmax_of(tasks):
    return max(r["stop"] for t in tasks for r in t["meta"]["rows"])


def levels(tasks):
    """Every label's pooled read at generations 0-8, its fresh successor's after FRESH_AT, the field rows' exposures, the
    observer and the injury checks in every generation."""
    out = {}
    gmax = gmax_of(tasks)
    fresh_at = D.STAGE_FRESH_AT.get(tasks[0]["stage"], D.FRESH_AT)
    for label in labels_of(tasks):
        some = next(t for t in tasks if label in t["meta"]["labels"])
        field = row_of(some, label)["field"] != "none"
        for e in LEVEL_ENDS:
            for g in range(0, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g)))
                if rec["tasks"]:
                    out[f"{label}|{e}|{g}"] = rec
        for e in FRESH_ENDS:
            for g in fresh_at:
                rec = pooled(tasks, lin((1, label, e, g, "x")))
                if rec["tasks"]:
                    out[f"{label}|{e}|x{g}"] = rec
        for e in ("injury_ok", "body_injury_ok") + (FIELD_DIAG if field else ()) + OBS_DIAG:
            for g in range(1, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g, "d")))
                if rec["tasks"]:
                    out[f"{label}|{e}|d{g}"] = rec
    return out


def exposures(tasks):
    """Per field row and generation: the pooled mean exposure over the generation and its halves, and the realized
    integrated kappa x exposure (kexp x T_GEN); relax's against raise's under each target."""
    out = {}
    gmax = gmax_of(tasks)
    for label in labels_of(tasks):
        some = next(t for t in tasks if label in t["meta"]["labels"])
        if row_of(some, label)["field"] == "none":
            continue
        rows = {}
        for g in range(1, gmax + 1):
            rec = {}
            for e in FIELD_DIAG:
                x, _b, _c = block_matrix(tasks, lin((1, label, e, g, "d")))
                if x is not None:
                    rec[e] = float(x.mean())
            if rec:
                rec["integrated_kexp"] = rec["kexp"] * D.T_GEN
                rows[g] = rec
        out[label] = rows
    for name, (a, b) in (("relax_over_raise_memory_integrated", (XM, RM)), ("relax_over_raise_body_integrated", (XB, RB)),
                         ("matched_over_raise_memory_integrated", (XMM, RM))):
        if a in out and b in out:
            out[name] = {g: out[a][g]["integrated_kexp"] / out[b][g]["integrated_kexp"]
                         for g in out[a] if g in out[b] and out[b][g]["integrated_kexp"] > 0}
    return out


def _dv(z, sd):
    return z / sd if sd > 0 else (float("inf") if z > 0 else (0.0 if z == 0 else float("-inf")))


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
        band = narrowest(rec["value"], rec["sd"], rec["halves"], "in") if fin else None   # for a null, the lead's to rule
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar), narrowest_band=band,
                   zero_sd=bool(rec["sd"] == 0))
        t = th.get(pid)
        if t is not None:
            v, sd = rec["value"], rec["sd"]
            if kind == "in":
                rec.update(threshold=list(t), holds=t[0] <= v <= t[1], margins=[_dv(v - t[0], sd), _dv(t[1] - v, sd)])
            elif kind == "ge":
                rec.update(threshold=t, holds=v >= t, margins=[_dv(v - t, sd)])
            else:
                rec.update(threshold=t, holds=v <= t, margins=[_dv(t - v, sd)])
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
        rec.pop("blocks")
        rec["by_item_set"] = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                rec["by_item_set"][name] = float(xs.mean())
        out.append(rec)
    return out


def aliases(tasks):
    """Per pair of labels a part compares, the tasks in which they ran on one row (an alias: the difference is 0 there)."""
    pairs = {(XM, NM), (RB, NB), (RM, NM), (XB, NB), (XMM, NM), (XMM, XM)}
    out = {}
    for a, b in sorted(pairs):
        out[f"{a} | {b}"] = sum(1 for t in tasks if a in t["meta"]["labels"] and b in t["meta"]["labels"]
                                and t["meta"]["labels"][a] == t["meta"]["labels"][b])
    return out


def margins(root):
    """P66b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(root)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    al = aliases(tasks)
    print(f"P66b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} band {p['narrowest_band']} zero-SD {p['zero_sd']}"
              + "  by set " + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p["by_item_set"].items()))
    print("aliased tasks:", al)
    ex = exposures(tasks)
    for label, rows in ex.items():
        if label.endswith("_integrated"):
            print(f"{label}: " + ", ".join(f"g{g} {v:.3f}" for g, v in rows.items()))
            continue
        print(f"{label}: " + "; ".join(f"g{g} x {r['exp_full']:.4f} int kx {r['integrated_kexp']:.0f}"
                                       for g, r in rows.items() if g in D.HORIZONS))
    return sc, al, ex


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P66's margins and the lead's ruling come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e007" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, nargs="+", required=True, help="one stage root, or several read as one stage "
                                                                     "(merged per task: P66 with P66x)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    if a.margins:
        sc, al, ex = margins(a.root if len(a.root) > 1 else a.root[0])
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps({"k_rule": K_RULE, "parts": sc, "aliased_tasks": al, "exposures": ex},
                                        indent=1) + "\n")
        return
    tasks, M = load(a.root if len(a.root) > 1 else a.root[0])
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": [str(r) for r in a.root], "merged_from": M.get("merged_from"),
         "design_digest": D.digest(), "kappa_matched": D.KAPPA_MATCHED, "parts": scored,
         "thresholds": TH, "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "aliased_tasks": aliases(tasks), "exposures": exposures(tasks), "reported": rep}, indent=1) + "\n")
    (a.out / "levels.json").write_text(json.dumps({"study": D.STUDY, "stage": stage, "levels": levels(tasks)}) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
