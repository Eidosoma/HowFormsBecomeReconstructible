"""E2E001's reader: the statement candidates (E1-E9), the reported parts, the lane's margin rule and the freeze.

python -m e2e001.predict --root STAGE_ROOT --out DIR     ->  DIR/predictions_scored.json
python -m e2e001.predict --freeze                         ->  e2e001/frozen/predictions.json (phase B, on the lead's word)

Pooling (the AR studies'): per case (block, message, parent) the mean over the eight unit-body pairs and the futures; a
block's value the mean of its eight cases; a part the mean over the blocks. SD = max(block SD, case SD / sqrt 8). On the
pilot each part must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values
the rule allows (hundredths, or 0.005 within 0.01 of zero). Development intervals: mean +- t(0.975, n - 1) SD / sqrt n.
Endpoints at generation g (0 = the restored record at t = 8,000): e2e001.sim.score; a label is an arm and its situation
("vguard/memory@0"), "protected", "post/<situation>", or a control ("foreign/...", "noread/protected", "unint/<arm>/memory@0"
= uninterrupted, approximate, "Q/<arm>/memory@0").
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

from e2e001 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds, from P56 by the rule (probes/p56b_e2e001_margins.py, 13:19:27Z on 3 November): bands at their
# narrowest; 'at least' parts above 0; E7 (narrowest -0.05) does not register (reported). E8: the lead's ruling (P56c,
# about 13:45Z), the confirmed no-event bound 0.002 (AR005's K2a) as a fixed bound: on P56 E8 is exactly 0 with SD 0
# (vguard never fired under none@0 on P53, so its packet is the vote's), which supports it
TH = {"E1": 0.2, "E2": 0.08, "E3": 0.07, "E4": [-0.35, -0.15], "E5": [0.005, 0.18], "E6": 0.15, "E8": 0.002, "E9": 0.18}
M0, M1, N0 = "memory@0", "memory@1", "none@0"


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


def val_f(task, label, e, g):
    """{future: (cases,)}: the endpoint of `label` at generation g in every future that ran its row ({None: ...} at g 0);
    None if the task has no such row. Later futures run the main rows only (design.SIDE_FUTURES)."""
    lab = task["meta"]["labels"]
    if label not in lab:
        return None
    i = lab[label]
    E = task["ends"]
    if g == 0:
        return {None: E[f"g0/{e}"][i]}
    out = {}
    for f in range(task["meta"]["futures"]):
        key = f"f{f}/g{g}/rows"
        if key in E:
            rows = list(E[key])
            if i in rows:
                out[f] = E[f"f{f}/g{g}/{e}"][rows.index(i)]
    return out or None


def val(task, label, e, g):
    """(cases,) the mean over the futures that ran the row."""
    v = val_f(task, label, e, g)
    return None if v is None else np.mean(list(v.values()), axis=0)


def lin(*terms):
    """sum of c x endpoint over terms (c, label, e, g), paired within each future: the mean over the futures in which every
    term with g > 0 ran (a generation-0 term enters every future alike); None where a term is missing."""
    def f(task):
        vals = []
        for c, label, e, g in terms:
            v = val_f(task, label, e, g)
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
    """(blocks, cases) per case the mean over the unit-body pairs; the block order ascending. None if no task has it."""
    by = {}
    for t in tasks:
        if subset is not None and (t["body"], t["unit"]) not in subset:
            continue
        v = fn(t)
        if v is not None:
            by.setdefault(t["block"], []).append(v)
    if not by:
        return None, []
    blocks = sorted(by)
    return np.array([np.mean(by[b], axis=0) for b in blocks]), blocks


def sd_rule(x):
    nb, nc = x.shape
    blk = x.mean(1)
    sd_b = float(blk.std(ddof=1)) if nb > 1 else float("nan")
    sd_c = float(x.ravel().std(ddof=1) / math.sqrt(nc))
    return max(sd_b, sd_c) if nb > 1 else sd_c, sd_b, sd_c


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
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd_block": sd_b, "sd_case8": sd_c, "halves": halves,
            "blocks": x.mean(1).tolist(), "n_blocks": nb}


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
    C = D.CONTROLLER
    return [
        ("E1", "the repair crosses the first renewal: u_r(vguard) - u_r(vote), memory@0, g 1",
         lin((1, f"{C}/{M0}", "u_r", 1), (-1, f"vote/{M0}", "u_r", 1)), "ge"),
        ("E2", "it lasts eight renewals: u_r(vguard) - u_r(vote), memory@0, g 8",
         lin((1, f"{C}/{M0}", "u_r", 8), (-1, f"vote/{M0}", "u_r", 8)), "ge"),
        ("E3", "the confirmed controller's: u_r(vms) - u_r(vote), memory@0, g 8",
         lin((1, f"vms/{M0}", "u_r", 8), (-1, f"vote/{M0}", "u_r", 8)), "ge"),
        ("E4", "the advantage's change through renewal: [u_r(vguard) - u_r(vote)] at g 8 less at g 0, memory@0",
         lin((1, f"{C}/{M0}", "u_r", 8), (-1, f"vote/{M0}", "u_r", 8), (-1, f"{C}/{M0}", "u_r", 0), (1, f"vote/{M0}", "u_r", 0)),
         "in"),
        ("E5", "protected storage's lead after renewal: u_r(protected) - u_r(vguard), memory@0, g 8",
         lin((1, "protected", "u_r", 8), (-1, f"{C}/{M0}", "u_r", 8)), "in"),
        ("E6", "repair against unrepaired copying after renewal: u_r(vguard) - u_r(post-damage), memory@0, g 8",
         lin((1, f"{C}/{M0}", "u_r", 8), (-1, f"post/{M0}", "u_r", 8)), "ge"),
        ("E7", "the misread recovery after renewal: u_r(vguard) - u_r(vms), memory@1, g 8",
         lin((1, f"{C}/{M1}", "u_r", 8), (-1, f"vms/{M1}", "u_r", 8)), "ge"),
        ("E8", "the no-event cost in later generations: a_r(vote) - a_r(vguard), none@0, g 8",
         lin((1, f"vote/{N0}", "a_r", 8), (-1, f"{C}/{N0}", "a_r", 8)), "le"),
        ("E9", "the first successor's own reconstruction: u_v(vguard) - u_v(vote), memory@0, g 1",
         lin((1, f"{C}/{M0}", "u_v", 1), (-1, f"vote/{M0}", "u_v", 1)), "ge"),
    ]


LEVEL_LABELS = ("protected", f"post/{M0}", f"vote/{M0}", f"vms/{M0}", f"vguard/{M0}", f"vms/{M1}", f"vguard/{M1}",
                f"vote/{N0}", f"vms/{N0}", f"vguard/{N0}", "vote/cue@0", "vms/cue@0", "vguard/cue@0",
                "vote/correlated@0", "vms/correlated@0", "vguard/correlated@0", "foreign/protected",
                f"foreign/vguard/{M0}", "noread/protected", f"unint/vote/{M0}", f"unint/vms/{M0}", f"unint/vguard/{M0}",
                f"Q/vote/{M0}", f"Q/vms/{M0}", f"Q/vguard/{M0}")
LEVEL_ENDS = ("u_r", "u_v", "a_r", "q_r", "q_v", "u_r_raw", "agree_in")


def reported():
    """The reported contrasts (the levels are reported separately, every label, endpoint and generation)."""
    C = D.CONTROLLER
    out = []
    for g in (0, 1, 3, 8):
        out.append((f"R-vms-{g}", f"u_r(vms) - u_r(vote), memory@0, g {g}",
                    lin((1, f"vms/{M0}", "u_r", g), (-1, f"vote/{M0}", "u_r", g))))
    out.append(("R-mismatch0", "mismatch at g 0 in the patch, vguard less vote: (1 - agree_in(vguard)) - (1 - agree_in(vote)), memory@0",
                lin((-1, f"{C}/{M0}", "agree_in", 0), (1, f"vote/{M0}", "agree_in", 0))))
    for g in (1, 3):
        out.append((f"R-own-foreign-q-{g}", f"q_r(protected) - q_r(foreign protected), g {g}",
                    lin((1, "protected", "q_r", g), (-1, "foreign/protected", "q_r", g))))
        out.append((f"R-own-foreign-u-{g}", f"u_r(vguard) - u_r(foreign vguard), memory@0, g {g}",
                    lin((1, f"{C}/{M0}", "u_r", g), (-1, f"foreign/{C}/{M0}", "u_r", g))))
        out.append((f"R-noread-q-{g}", f"q_r(protected) - q_r(disabled reading), g {g}",
                    lin((1, "protected", "q_r", g), (-1, "noread/protected", "q_r", g))))
        for arm in D.POLICIES:
            out.append((f"R-unint-{arm}-{g}", f"u_r(uninterrupted, approximate) - u_r(lineage), {arm}, memory@0, g {g}",
                        lin((1, f"unint/{arm}/{M0}", "u_r", g), (-1, f"{arm}/{M0}", "u_r", g))))
            out.append((f"R-Q-{arm}-{g}", f"u_r(Q boundary) - u_r(SR001's packet), {arm}, memory@0, g {g}",
                        lin((1, f"Q/{arm}/{M0}", "u_r", g), (-1, f"{arm}/{M0}", "u_r", g))))
    out.append(("R-protected-q-8", "q_r(protected), g 8 (the route's own erosion)", lin((1, "protected", "q_r", 8))))
    out.append(("R-protected-noread-q-3", "q_r(disabled reading), g 3 (the native baseline)", lin((1, "noread/protected", "q_r", 3))))
    for sit in ("cue@0", "correlated@0"):
        for g in (1, 3):
            out.append((f"R-{sit}-{g}", f"u_r(vguard) - u_r(vote), {sit}, g {g}",
                        lin((1, f"{C}/{sit}", "u_r", g), (-1, f"vote/{sit}", "u_r", g))))
    out.append(("R-E7-at-0", "u_r(vguard) - u_r(vms), memory@1, g 0", lin((1, f"{C}/{M1}", "u_r", 0), (-1, f"vms/{M1}", "u_r", 0))))
    return out


def score(tasks, th=None, stage=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    out = []
    for pid, words, fn, kind in parts():
        x, blocks = block_matrix(tasks, fn)
        if x is None:
            out.append({"id": pid, "part": words, "kind": kind, "available": False})
            continue
        rec = {"id": pid, "part": words, "kind": kind, "available": True, **value(x, blocks, stage)}
        fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
        nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if fin else None
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar))
        t = th.get(pid)
        if t is not None:
            v, sd = rec["value"], rec["sd"]
            dv = lambda x: x / sd if sd > 0 else (float("inf") if x > 0 else (0.0 if x == 0 else float("-inf")))
            if kind == "in":
                rec.update(threshold=list(t), holds=t[0] <= v <= t[1], margins=[dv(v - t[0]), dv(t[1] - v)])
            elif kind == "ge":
                rec.update(threshold=t, holds=v >= t, margins=[dv(v - t)])
            else:
                rec.update(threshold=t, holds=v <= t, margins=[dv(t - v)])
        by_set = {}
        for name, subset in D.ITEM_SETS.items():
            xs, bs = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                by_set[name] = {"value": float(xs.mean()), "blocks": xs.mean(1).tolist()}
        rec["by_item_set"] = by_set
        out.append(rec)
    return out


def score_reported(tasks, stage=None):
    stage = stage or tasks[0]["stage"]
    out = []
    for rid, words, fn in reported():
        x, blocks = block_matrix(tasks, fn)
        if x is None:
            out.append({"id": rid, "part": words, "available": False})
            continue
        rec = {"id": rid, "part": words, "available": True, **value(x, blocks, stage)}
        rec["by_item_set"] = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _ = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                rec["by_item_set"][name] = float(xs.mean())
        out.append(rec)
    return out


def levels(tasks):
    """Every label's pooled endpoint at every generation, overall and by item set (numbers only)."""
    out = {}
    for label in LEVEL_LABELS:
        for e in LEVEL_ENDS:
            for g in (0, 1, 3, 8):
                fn = lin((1, label, e, g))
                x, _ = block_matrix(tasks, fn)
                if x is None:
                    continue
                rec = {"all": float(x.mean())}
                for name, subset in D.ITEM_SETS.items():
                    xs, _ = block_matrix(tasks, fn, set(subset))
                    if xs is not None:
                        rec[name] = float(xs.mean())
                out[f"{label}|{e}|{g}"] = rec
    return out


def futures_spread(tasks):
    """The mean over cases of the SD across futures of u_r at g 8, per policy (memory@0); None with one future."""
    out = {}
    for arm in ("protected", f"vote/{M0}", f"vms/{M0}", f"{D.CONTROLLER}/{M0}", f"post/{M0}"):
        sds = []
        for t in tasks:
            nf = t["meta"]["futures"]
            lab = t["meta"]["labels"]
            if nf < 2 or arm not in lab:
                continue
            i = lab[arm]
            vals = []
            for f in range(nf):
                rows = list(t["ends"][f"f{f}/g8/rows"])
                if i in rows:
                    vals.append(t["ends"][f"f{f}/g8/u_r"][rows.index(i)])
            if len(vals) == nf:
                sds.append(np.std(vals, axis=0, ddof=1).mean())
        out[arm] = float(np.mean(sds)) if sds else None
    return out


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P56's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e001" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tasks, M = load(a.root)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root), "design_digest": D.digest(), "parts": scored,
         "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "reported": rep, "levels": levels(tasks), "futures_spread": futures_spread(tasks)}, indent=1) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
