"""E2E003's reader: the statement candidates (J1-J5), the reported parts, every lineage's levels and diagnostics, the
lane's margin rule and the freeze. DRAFT (phase A).

python -m e2e003.predict --root STAGE_ROOT --out DIR     ->  DIR/predictions_scored.json
python -m e2e003.predict --margins --root STAGE_ROOT     ->  the rule's narrowest thresholds on the stage (P59b)
python -m e2e003.predict --freeze                         ->  e2e003/frozen/predictions.json (phase B, on the lead's word)

E2E002's reader functions, imported unchanged (e2e002.predict: load, val_f, lin, block_matrix, sd_rule, narrowest,
registers): per case (block, message, parent) the mean over the unit-body pairs and the futures; a block's value the mean
of its cases; a part the mean over the blocks; SD = max(block SD, case SD / sqrt(cases a block)). On the pilot each part
must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values the rule allows
(hundredths, or 0.005 within 0.01 of zero); an "at least" part registers only above 0, an "at most" only at 0.05 or less.
Development intervals: mean +- t(0.975, n - 1) SD / sqrt n. Coverage: a part or level is pooled only where every task of
the stage has every term; anything less is marked partial, with its task count, never pooled.
Endpoints (PLAN_E2E003.md): U is u_r on the union of generation 0's patch and every patch injured so far; u_r is on the
generation's own patch; a_r and q_r are whole-sheet (e2e001.sim.score).
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

from e2e002 import predict as P2  # noqa: E402  (load, val_f, lin, block_matrix, sd_rule, narrowest, registers; unchanged)
from e2e003 import design as D  # noqa: E402

load, val_f, lin, block_matrix, sd_rule, narrowest, registers, sha = (P2.load, P2.val_f, P2.lin, P2.block_matrix,
                                                                      P2.sd_rule, P2.narrowest, P2.registers, P2.sha)
K_RULE = D.K_RULE
# the thresholds, from P59 by the rule (P59b, probes/results/p59b_e2e003_margins.txt, 4 November about 13:22Z): the
# rule's narrowest for every part. J2b, J3d, J4a and J4b are equivalence bands at their narrowest (Amendment 1, the lead's
# ruling of about 13:43Z, after P59's values and before any development value: the plan declared them "at least (above
# 0)", which P59 cannot support; PROTOCOL §10: "finite nulls require adequate precision relative to frozen
# meaningful-effect margins"; as E2E002's Amendment 1); probes/results/p59b_e2e003_margins_amended.txt
TH = {"J1a": 0.31, "J1b": 0.05, "J2a": 0.08, "J2b": [-0.04, 0.02], "J3a": 0.28, "J3b": 0.04, "J3c": 0.06,
      "J3d": [-0.04, 0.03], "J4a": [-0.02, 0.02], "J4b": [-0.03, 0.01], "J5a": [0.09, 0.25], "J5b": [0.06, 0.13]}
E0, O0, V0_, C0 = "vtol-every/memory@0", "vtol-once/memory@0", "vote/memory@0", "uninjured"
E1_, O1, V1, M1 = "vtol-every/memory@1", "vtol-once/memory@1", "vote/memory@1", "vms-every/memory@1"
G = D.G_MAIN


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


def d(a, b, e, g):
    return lin((1, a, e, g), (-1, b, e, g))


PAIRS = {"J1a": (E0, V0_), "J1b": (E0, V0_), "J2a": (E1_, V1), "J2b": (E1_, V1), "J3a": (E0, O0), "J3b": (E0, O0),
         "J3c": (E1_, O1), "J3d": (E1_, O1), "J4a": (E1_, M1), "J4b": (E1_, M1), "J5a": (C0, E0), "J5b": (C0, E0)}
ENDPOINT = {"J1a": "U", "J1b": "q_r", "J2a": "U", "J2b": "q_r", "J3a": "U", "J3b": "q_r", "J3c": "U", "J3d": "q_r",
            "J4a": "U", "J4b": "q_r", "J5a": "U", "J5b": "q_r"}


def parts():
    return [
        ("J1a", "U(vtol-every) - U(vote), memory@0, g 8: every generation against the best fixed policy, the accumulated damage",
         d(E0, V0_, "U", G), "ge"),
        ("J1b", "q_r(vtol-every) - q_r(vote), memory@0, g 8: and the lineage's history", d(E0, V0_, "q_r", G), "ge"),
        ("J2a", "U(vtol-every) - U(vote), memory@1, g 8: under misreads in every generation", d(E1_, V1, "U", G), "ge"),
        ("J2b", "q_r(vtol-every) - q_r(vote), memory@1, g 8 (equivalence band, Amendment 1)", d(E1_, V1, "q_r", G), "in"),
        ("J3a", "U(vtol-every) - U(vtol-once), memory@0, g 8: every against once", d(E0, O0, "U", G), "ge"),
        ("J3b", "q_r(vtol-every) - q_r(vtol-once), memory@0, g 8", d(E0, O0, "q_r", G), "ge"),
        ("J3c", "U(vtol-every) - U(vtol-once), memory@1, g 8", d(E1_, O1, "U", G), "ge"),
        ("J3d", "q_r(vtol-every) - q_r(vtol-once), memory@1, g 8 (equivalence band, Amendment 1)", d(E1_, O1, "q_r", G),
         "in"),
        ("J4a", "U(vtol-every) - U(vms-every), memory@1, g 8: the misread recovery, generation after generation "
                "(equivalence band, Amendment 1)", d(E1_, M1, "U", G), "in"),
        ("J4b", "q_r(vtol-every) - q_r(vms-every), memory@1, g 8 (equivalence band, Amendment 1)", d(E1_, M1, "q_r", G),
         "in"),
        ("J5a", "U(uninjured) - U(vtol-every), memory@0, g 8: how close to an uninjured lineage (band)", d(C0, E0, "U", G), "in"),
        ("J5b", "q_r(uninjured) - q_r(vtol-every), memory@0, g 8 (band)", d(C0, E0, "q_r", G), "in"),
    ]


def reported():
    out = []
    for g in (1, 3, 8):
        for pid, words, _fn, _k in parts():
            a, b = PAIRS[pid]
            if g != G:
                out.append((f"R-{pid}-{g}", f"{words.split(':')[0].replace('g 8', f'g {g}')}", d(a, b, ENDPOINT[pid], g)))
        out.append((f"R-own-every-vote-{g}", f"u_r(vtol-every) - u_r(vote) on the generation's own patch, memory@0, g {g}",
                    d(E0, V0_, "u_r", g)))
        out.append((f"R-own-every-once-{g}", f"u_r(vtol-every) - u_r(vtol-once) on the own patch, memory@0, g {g}",
                    d(E0, O0, "u_r", g)))
        out.append((f"R-a-every-vote-{g}", f"a_r(vtol-every) - a_r(vote), memory@0, g {g}", d(E0, V0_, "a_r", g)))
        out.append((f"R-once-vote-{g}", f"U(vtol-once) - U(vote), memory@0, g {g}", d(O0, V0_, "U", g)))
        out.append((f"R-ceiling-vote-{g}", f"U(uninjured) - U(vote), memory@0, g {g}", d(C0, V0_, "U", g)))
        out.append((f"R-ceiling-once-{g}", f"U(uninjured) - U(vtol-once), memory@0, g {g}", d(C0, O0, "U", g)))
        out.append((f"R-vms0-{g}", f"U(vtol-every) - U(vms-every), memory@0, g {g} (the optional row)",
                    d(E0, "vms-every/memory@0", "U", g)))
        out.append((f"R-vms1-vote-{g}", f"U(vms-every) - U(vote), memory@1, g {g}", d(M1, V1, "U", g)))
    return out


LEVEL_ENDS = ("U", "u_r", "a_r", "q_r", "u_v", "q_v", "U_v", "U_raw", "u_r_raw", "agree_in", "agree_U")
DIAG_ENDS = ("fired", "det_on", "det_fp", "det_fp_in", "det_zone", "det_zone_in", "opened", "opened_out", "signal",
             "committed_end", "cue_dis_birth", "injury_ok")


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


def detector_labels(tasks):
    out = set()
    for t in tasks:
        for lab, i in t["meta"]["labels"].items():
            if t["meta"]["rows"][i]["policy"] != "vote":
                out.add(lab)
    return out


def onset_share(label, g, which):
    """(cases,) per task: the share of the label's lineage-cases at generation g whose detector fired at update 1
    ("at1"), later ("later") or never ("never"), from the saved onsets (det_on: the onset update, -1 where it never
    fired); the mean over the futures that ran the row."""
    test = {"at1": lambda v: v == 1, "later": lambda v: v > 1, "never": lambda v: v < 0}[which]

    def f(task):
        v = val_f(task, label, "det_on", g, "d")
        return None if v is None else np.mean([test(x).astype(float) for x in v.values()], axis=0)
    return f


def onsets(tasks):
    """The lead's reported diagnostic (ruling 6): per generation, for every controller lineage, the pooled shares
    firing at update 1, later and never, and the quartiles of the later onsets over every lineage-case of the stage
    (the body's own confidence in the patch is not saved, so the onsets stand alone)."""
    out = {}
    gmax = max(r["stop"] for t in tasks for r in t["meta"]["rows"])
    for label in sorted(detector_labels(tasks)):
        for g in range(1, gmax + 1):
            rec = {w: pooled(tasks, onset_share(label, g, w)) for w in ("at1", "later", "never")}
            vals = [x for t in tasks for v in (val_f(t, label, "det_on", g, "d") or {}).values() for x in v]
            later = np.array([x for x in vals if x > 1])
            rec["n_lineage_cases"], rec["n_later"] = len(vals), int(later.size)
            rec["later_quartiles"] = [float(q) for q in np.percentile(later, (25, 50, 75))] if later.size else None
            out[f"{label}|d{g}"] = rec
    return out


def levels(tasks):
    """Every label's pooled endpoint at generations 0-8, and a detector lineage's diagnostics in every generation."""
    out = {}
    det = detector_labels(tasks)
    gmax = max(r["stop"] for t in tasks for r in t["meta"]["rows"])
    for label in labels_of(tasks):
        for e in LEVEL_ENDS:
            for g in range(0, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g)))
                if rec["tasks"]:
                    out[f"{label}|{e}|{g}"] = rec
        for e in DIAG_ENDS:
            if label not in det and e not in ("fired", "injury_ok", "cue_dis_birth"):
                continue
            for g in range(1, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g, "d")))
                if rec["tasks"]:
                    out[f"{label}|{e}|d{g}"] = rec
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
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar), zero_sd=bool(rec["sd"] == 0))
        if fin and rec["sd"] > 0 and nar is not None:
            v, sd = rec["value"], rec["sd"]
            rec["margin_at_narrowest"] = ([_dv(v - nar[0], sd), _dv(nar[1] - v, sd)] if kind == "in"
                                          else [_dv(v - nar, sd)] if kind == "ge" else [_dv(nar - v, sd)])
        t = th.get(pid)
        if t is not None:
            v, sd = rec["value"], rec["sd"]
            if kind == "in":
                rec.update(threshold=list(t), holds=bool(t[0] <= v <= t[1]), margins=[_dv(v - t[0], sd), _dv(t[1] - v, sd)])
            elif kind == "ge":
                rec.update(threshold=t, holds=bool(v >= t), margins=[_dv(v - t, sd)])
            else:
                rec.update(threshold=t, holds=bool(v <= t), margins=[_dv(t - v, sd)])
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
    out = {}
    for pid, (a, b) in PAIRS.items():
        out[pid] = sum(1 for t in tasks if a in t["meta"]["labels"] and b in t["meta"]["labels"]
                       and t["meta"]["labels"][a] == t["meta"]["labels"][b])
    return out


def margins(root):
    """P59b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(root)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    al = aliases(tasks)
    print(f"P59b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']} aliased tasks {al[p['id']]}  by set "
              + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p["by_item_set"].items()))
    return sc, al


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P59's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e003" / "frozen" / "predictions.json"
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
         "aliased_tasks": aliases(tasks), "reported": rep, "levels": levels(tasks), "onsets": onsets(tasks)},
        separators=(",", ":")) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
