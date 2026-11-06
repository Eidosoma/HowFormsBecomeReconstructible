"""E2E006's reader: the registered statements (Amendment 2: H1-H3 reversed, H5 at g 3, the decomposition N1-N3 and
R1-R3), the reported parts, the realized exposures, the lane's margin rule and the freeze. DRAFT (phase A).

python -m e2e006.predict --root ROOT [ROOT ...] --out DIR     ->  DIR/predictions_scored.json and DIR/levels.json
python -m e2e006.predict --margins --root ROOT [ROOT ...]     ->  the rule's narrowest thresholds on the stage(s) (P63b)
python -m e2e006.predict --kappa --root KAPPA_ROOT            ->  P63k: kappa from the reference configuration's exposures
python -m e2e006.predict --freeze                              ->  e2e006/frozen/predictions.json (phase B, on the lead's word)

Several roots (the pilot: P63's and P63x's) are read as one stage: their records of each task (the same raw file, tag and
futures, so the same births, injuries and noise) are merged, the later root's rows after the earlier's.

Pooling (the AR studies'): per case (block, message, parent) the mean over the unit-body pairs and the futures; a block's
value the mean of its cases; a part the mean over the blocks. SD = max(block SD, case SD / sqrt(cases a block)). On the
pilot each part must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values
the rule allows (hundredths, or 0.005 within 0.01 of zero). Development intervals: mean +- t(0.975, n - 1) SD / sqrt n.
Coverage (E2E001's lesson): a part or a level is pooled only where every task of the stage has every term; anything less
is marked partial, with its task count, never pooled. Kinds of value: "g" a lineage's read at generation g (with the
field present, where the row has one), "x" the fresh successor's read after generation g (field-free, never in the
lineage), "d" a diagnostic of generation g (the exposures among them). There are no detectors in the field rows; vtol's
firings, where it runs, are pooled per lineage-case (the fired share) and per firing.
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

from e2e006 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds (Amendment 2, the lead's rulings of 13:46:59Z): H1-H3 reversed at the rule's narrowest "at most" bounds on
# P63 (written after P63's values, opposite to the plan's declared direction); H5 at g 3 at its narrowest band on P63;
# N1-N3 and R1-R3 declared before their values, their thresholds from P63 + P63x by the rule (set after P63x)
TH = {"H1": -0.05, "H2": -0.04, "H3": -0.01, "H5": [-0.04, 0.02],
      # P63xb (P63 + P63x merged, 14:09:31Z on 5 November): each N band lies inside MEANINGFUL, each R bound at most 0.05
      "N1": [-0.01, 0.01], "N2": [-0.01, 0.02], "N3": [-0.01, 0.01], "R1": -0.09, "R2": -0.08, "R3": -0.02}
MEANINGFUL = (-0.03, 0.03)      # the lead's frozen meaningful-effect margin: an N band registers only inside it
NONE, ISO, SH, RET, EAR, LAT = ("vote/none", "vote/isolated", "vote/shared", "vote/shared-retained", "vote/shared-early",
                                "vote/shared-late")
PRO, VT, UNI, VTS, ISM = "protected", "vtol-every", "uninjured", "vtol-every/shared", "vote/isolated-matched"
G = D.G_MAIN


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root, check=True):
    """Every task's endpoints and its row map, checked by sha256 against the stage's manifest. root: one stage root, or a
    list of them read as one stage (merge)."""
    if isinstance(root, (list, tuple)):
        if len(root) == 1:
            return load(root[0], check)
        tasks, M = load(root[0], check)
        for r in root[1:]:
            t2, M2 = load(r, check)
            tasks, M = merge(tasks, M, t2, M2)
        return tasks, M
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


def merge(tasks_a, Ma, tasks_b, Mb):
    """Two stages' records of the same tasks as one stage: per task, b's rows follow a's (labels, row indices and every
    per-row array); the schedules must be equal (the same tag), and so must the futures."""
    by_b = {t["name"]: t for t in tasks_b}
    if set(by_b) != {t["name"] for t in tasks_a}:
        raise ValueError("the stages hold different tasks")
    out = []
    for ta in tasks_a:
        tb = by_b[ta["name"]]
        ma, mb, ea, eb = ta["meta"], tb["meta"], ta["ends"], tb["ends"]
        if ma["futures"] != mb["futures"] or ma["tag"] != mb["tag"]:
            raise ValueError(f"{ta['name']}: the stages differ in futures or tag")
        if set(ma["labels"]) & set(mb["labels"]):
            raise ValueError(f"{ta['name']}: a label in both stages")
        n = len(ma["rows"])
        E = {}
        for key in sorted(set(ea) | set(eb)):
            if key.startswith("schedule/"):
                x, y = ea[key], eb[key]
                m = min(x.shape[1], y.shape[1])
                if not np.array_equal(x[:, :m], y[:, :m]):
                    raise ValueError(f"{ta['name']}: the schedules differ")
                E[key] = x if x.shape[1] >= y.shape[1] else y
                continue
            head = key.rsplit("/", 1)[0]
            in_a, in_b = key in ea, key in eb
            if key.endswith("/rows"):
                E[key] = np.concatenate(([ea[key]] if in_a else []) + ([eb[key] + n] if in_b else [])).astype(int)
            elif in_a and in_b:
                E[key] = np.concatenate([ea[key], eb[key]])
            elif (in_a and f"{head}/rows" in eb) or (in_b and f"{head}/rows" in ea) or key.startswith("g0/"):
                raise ValueError(f"{ta['name']}: {key} in one stage only")
            else:
                E[key] = ea[key] if in_a else eb[key]
        meta = dict(ma, rows=ma["rows"] + mb["rows"], labels=dict(ma["labels"], **{k: v + n for k, v in mb["labels"].items()}),
                    aliases=dict(ma["aliases"], **mb["aliases"]), sources=dict(ma["sources"], **mb["sources"]),
                    merged_from=ma.get("merged_from", [ma["stage"]]) + [mb["stage"]])
        out.append(dict(ta, meta=meta, ends=E))
    M = dict(Ma, merged_from=Ma.get("merged_from", [Ma["stage"]]) + [Mb["stage"]],
             cpu_s_total=Ma.get("cpu_s_total", 0) + Mb.get("cpu_s_total", 0))
    return out, M


def val_f(task, label, e, g, kind="g"):
    """{future: (cases,)}: `label`'s read (kind "g"), its fresh successor's read (kind "x") or diagnostic (kind "d") at
    generation g in every future that ran its row ({None: ...} at g 0); None if the task has no such row."""
    lab = task["meta"]["labels"]
    if label not in lab:
        return None
    i = lab[label]
    E = task["ends"]
    if g == 0 and kind == "g":
        k = f"g0/{e}"
        return {None: E[k][i]} if k in E else None
    out = {}
    for f in range(task["meta"]["futures"]):
        key = f"f{f}/{kind}{g}/rows"
        if key in E and f"f{f}/{kind}{g}/{e}" in E:
            rows = list(E[key])
            if i in rows:
                out[f] = E[f"f{f}/{kind}{g}/{e}"][rows.index(i)]
    return out or None


def lin(*terms):
    """sum of c x value over terms (c, label, e, g[, kind]), paired within each future: the mean over the futures in
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


def registers(kind, nar, pid=None):
    """Whether a part registers at its narrowest threshold: an "at least" bound above 0, an "at most" bound at most
    AT_MOST_MAX (0.05; the R parts' limit too), a band always, except N1-N3, whose band must lie inside MEANINGFUL."""
    if nar is None:
        return None
    if pid is not None and pid.startswith("N"):
        return bool(MEANINGFUL[0] <= nar[0] and nar[1] <= MEANINGFUL[1])
    return kind == "in" or (kind == "ge" and nar > 0) or (kind == "le" and nar <= D.AT_MOST_MAX)


GE = D.G_EARLY_LATE
# the statements (id: a, b, endpoint, kind of value, generation, kind, words): a - b
PARTS = {
    "H1": (SH, ISO, "U_v", "g", G, "le", "the group at one kappa, present organization: U_v(vote/shared) - "
                                         "U_v(vote/isolated), g 8 (reversed after P63)"),
    "H2": (SH, ISO, "q_r", "g", G, "le", "the group at one kappa, history: q_r(vote/shared) - q_r(vote/isolated), g 8 "
                                         "(reversed after P63)"),
    "H3": (SH, ISO, "U_v", "x", G, "le", "the group at one kappa, what the record carries: the fresh successor's U_v, "
                                         "vote/shared - vote/isolated, after g 8 (reversed after P63)"),
    "H5": (EAR, LAT, "U_v", "g", GE, "in", "early against late assistance at matched exposure: U_v(vote/shared-early) - "
                                           "U_v(vote/shared-late), g 3"),
    "N1": (SH, ISM, "U_v", "g", G, "in", "the neighbours' signal at a matched mean response, present organization: "
                                         "U_v(vote/shared) - U_v(vote/isolated-matched), g 8"),
    "N2": (SH, ISM, "q_r", "g", G, "in", "the neighbours' signal at a matched mean response, history: q_r(vote/shared) - "
                                         "q_r(vote/isolated-matched), g 8"),
    "N3": (SH, ISM, "U_v", "x", G, "in", "the neighbours' signal at a matched mean response, what the record carries: the "
                                         "fresh successor's U_v, vote/shared - vote/isolated-matched, after g 8"),
    "R1": (ISM, NONE, "U_v", "g", G, "le", "the response at the shared row's size, private signals only, present "
                                           "organization: U_v(vote/isolated-matched) - U_v(vote/none), g 8"),
    "R2": (ISM, NONE, "q_r", "g", G, "le", "the response at the shared row's size, private signals only, history: "
                                           "q_r(vote/isolated-matched) - q_r(vote/none), g 8"),
    "R3": (ISM, NONE, "U_v", "x", G, "le", "the response at the shared row's size, private signals only, what the record "
                                           "carries: the fresh successor's U_v, vote/isolated-matched - vote/none, after g 8"),
}
PAIRS = {pid: (a, b, e, k) for pid, (a, b, e, k, _g, _kind, _w) in PARTS.items()}
KINDS = {pid: v[5] for pid, v in PARTS.items()}
WORDS = {pid: v[6] for pid, v in PARTS.items()}
FIELD_ROWS = (ISO, SH, ISM, EAR, LAT)


def d(a, b, e, g, kind="g"):
    return lin((1, a, e, g, kind), (-1, b, e, g, kind))


def parts():
    return [(pid, w, d(a, b, e, g, k), kind) for pid, (a, b, e, k, g, kind, w) in PARTS.items()]


def reported():
    """The parts at their other horizons; the decomposition's other endpoints; the response at the isolated row's size
    (isolated - none) and the total (shared - none); the comparators protected and vtol-every against every field row;
    retained - shared (P63 only: not a channel at these parameters); early - late in q_r and the fresh successor."""
    out = []
    for g in D.HORIZONS:
        for pid, (a, b, e, k, gp, _kind, w) in PARTS.items():
            if g != gp:
                out.append((f"R-{pid}-{g}", f"{w} [at g {g}]", d(a, b, e, g, k)))
        for name, (a, b) in {"sh-iso": (SH, ISO), "sh-ism": (SH, ISM), "ism-none": (ISM, NONE), "iso-none": (ISO, NONE),
                             "sh-none": (SH, NONE), "ism-iso": (ISM, ISO)}.items():
            for e in ("U_v", "q_r", "a_v", "U"):
                out.append((f"R-{name}-{e}-{g}", f"{e}({a}) - {e}({b}), g {g}", d(a, b, e, g)))
            for e in ("U_v", "q_r", "a_v", "q_v"):
                out.append((f"R-{name}-fresh-{e}-{g}", f"the fresh successor's {e}, {a} - {b}, after g {g}",
                            d(a, b, e, g, "x")))
        for row in FIELD_ROWS:
            for comp, cn in ((PRO, "pro"), (VT, "vtol")):
                for e in ("U_v", "q_r", "a_v"):
                    out.append((f"R-{row.split('/')[-1]}-{cn}-{e}-{g}", f"{e}({row}) - {e}({comp}), g {g}",
                                d(row, comp, e, g)))
                out.append((f"R-{row.split('/')[-1]}-{cn}-fresh-U_v-{g}",
                            f"the fresh successor's U_v, {row} - {comp}, after g {g}", d(row, comp, "U_v", g, "x")))
        for e in ("U_v", "q_r"):
            out.append((f"R-ret-sh-{e}-{g}", f"{e}(vote/shared-retained) - {e}(vote/shared), g {g} (P63 only)",
                        d(RET, SH, e, g)))
        out.append((f"R-ret-sh-fresh-U_v-{g}", f"the fresh successor's U_v, retained - shared, after g {g} (P63 only)",
                    d(RET, SH, "U_v", g, "x")))
        out.append((f"R-ea-la-q_r-{g}", f"q_r(vote/shared-early) - q_r(vote/shared-late), g {g}", d(EAR, LAT, "q_r", g)))
        out.append((f"R-ea-la-fresh-U_v-{g}", f"the fresh successor's U_v, early - late, after g {g}",
                    d(EAR, LAT, "U_v", g, "x")))
    return out


LEVEL_ENDS = ("U", "U_v", "U_raw", "agree_U", "u_r", "u_v", "a_r", "a_v", "q_r", "q_v")
FRESH_ENDS = ("U", "U_v", "a_r", "a_v", "q_r", "q_v")
FIELD_DIAG = ("exp_full", "exp_early", "exp_late", "kexp")
DET_DIAG = ("fired", "det_fp_in", "det_zone_in", "opened", "opened_out")


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


def gmax_of(tasks):
    return max(r["stop"] for t in tasks for r in t["meta"]["rows"])


def levels(tasks):
    """Every label's pooled read at generations 0-8, its fresh successor's at FRESH_AT, the field rows' exposures and the
    detector rows' firing diagnostics in every generation, and every row's injury check."""
    out = {}
    gmax = gmax_of(tasks)
    for label in labels_of(tasks):
        some = next(t for t in tasks if label in t["meta"]["labels"])
        field = row_of(some, label)["field"] != "none"
        det = row_of(some, label)["policy"] != "vote"
        for e in LEVEL_ENDS:
            for g in range(0, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g)))
                if rec["tasks"]:
                    out[f"{label}|{e}|{g}"] = rec
        for e in FRESH_ENDS:
            for g in D.FRESH_AT:
                rec = pooled(tasks, lin((1, label, e, g, "x")))
                if rec["tasks"]:
                    out[f"{label}|{e}|x{g}"] = rec
        diag = ("injury_ok",) + (FIELD_DIAG if field else ()) + (DET_DIAG if det else ())
        for e in diag:
            for g in range(1, gmax + 1):
                rec = pooled(tasks, lin((1, label, e, g, "d")))
                if rec["tasks"]:
                    out[f"{label}|{e}|d{g}"] = rec
    return out


def per_firing(tasks):
    """vtol's firings, per firing (the lane's rule for event diagnostics): over every fired lineage-case of a detector
    row at generation g, the mean share of the patch inside its zone and its first-pass footprint, and the count."""
    out = {}
    gmax = gmax_of(tasks)
    for label in labels_of(tasks):
        some = next(t for t in tasks if label in t["meta"]["labels"])
        if row_of(some, label)["policy"] == "vote":
            continue
        for g in range(1, gmax + 1):
            n_cases, n_fired, zin, fin = 0, 0, [], []
            for t in tasks:
                f = val_f(t, label, "fired", g, "d")
                if f is None:
                    continue
                z = val_f(t, label, "det_zone_in", g, "d")
                p = val_f(t, label, "det_fp_in", g, "d")
                for fu in f:
                    m = f[fu].astype(bool)
                    n_cases += m.size
                    n_fired += int(m.sum())
                    zin += list(z[fu][m])
                    fin += list(p[fu][m])
            if n_cases:
                out[f"{label}|d{g}"] = {"firings": n_fired, "lineage_cases": n_cases,
                                        "zone_in_patch_per_firing": float(np.mean(zin)) if zin else None,
                                        "footprint_in_patch_per_firing": float(np.mean(fin)) if fin else None}
    return out


def exposures(tasks):
    """The realized exposures (reported beside the contrasts, the lead's ruling 5): per field row and generation, the
    pooled mean exposure x(t) over the generation and its halves, and the realized integrated kappa x exposure a
    generation (kappa x x(t) summed over the updates where the response acted: kexp x T_GEN), with the early and late
    rows' ratio, and the matched isolated row's against the shared row's (Amendment 2)."""
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
                x, _b, cov = block_matrix(tasks, lin((1, label, e, g, "d")))
                if x is not None:
                    rec[e] = float(x.mean())
            if rec:
                rec["integrated_kexp"] = rec["kexp"] * D.T_GEN
                rows[g] = rec
        out[label] = rows
    for name, (a, b) in (("early_over_late_integrated", (EAR, LAT)), ("matched_over_shared_integrated", (ISM, SH)),
                         ("isolated_over_shared_integrated", (ISO, SH))):
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
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar, pid), zero_sd=bool(rec["sd"] == 0))
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
    """Per part, the tasks in which its two lineages ran on one row (an alias: the difference is exactly 0 there)."""
    out = {}
    for pid, (a, b, _e, _k) in PAIRS.items():
        out[pid] = sum(1 for t in tasks if a in t["meta"]["labels"] and b in t["meta"]["labels"]
                       and t["meta"]["labels"][a] == t["meta"]["labels"][b])
    return out


def margins(root):
    """P63b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers
    (an N band only inside MEANINGFUL, an R bound only at most 0.05); the realized exposures beside them."""
    tasks, M = load(root)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    al = aliases(tasks)
    print(f"P63b margins on {'+'.join(M.get('merged_from', [stage]))} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']} aliased tasks {al[p['id']]}"
              + "  by set " + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p["by_item_set"].items()))
    ex = exposures(tasks)
    for label, rows in ex.items():
        if label.endswith("_integrated"):
            print(f"{label.replace('_integrated', '').replace('_over_', ' / ')}: integrated kappa x exposure, by "
                  f"generation: " + ", ".join(f"g{g} {v:.3f}" for g, v in rows.items()))
            continue
        print(f"{label}: " + "; ".join(f"g{g} x {r['exp_full']:.4f} (early {r['exp_early']:.4f}, late {r['exp_late']:.4f}) "
                                       f"int kx {r['integrated_kexp']:.0f}" for g, r in rows.items() if g in D.HORIZONS))
    return sc, al, ex


def kappa(root):
    """P63k: kappa from the reference configuration (the shared row at kappa 0 on the debug record's eight tasks,
    generations 1-8; engineering only, nothing scored): kappa x mean x = 1 over the whole generation, and kappa_early,
    kappa_late the same over updates 1-4,000 and 4,001-8,000, each rounded to four significant figures. The isolated row's
    exposures beside it (the exposure ratio; not used for kappa)."""
    tasks, M = load(root)
    if M["stage"] != "kappa" or any(t["meta"]["scored"] for t in tasks) or any(t["meta"]["kappa_override"] != 0.0
                                                                                  for t in tasks):
        sys.exit("P63k reads only the kappa stage (kappa 0, unscored)")
    if any(k.startswith("g0/") or "/g" in k or "/x" in k for t in tasks for k in t["ends"]):
        sys.exit("the kappa stage holds a read: refusing")
    sig = lambda v: float(f"{v:.4g}")
    rec = {"study": D.STUDY, "probe": "P63k", "root": str(root), "design_digest": M["design_digest"],
           "tasks": len(tasks), "bridge_all_equal": M["bridge_all_equal"], "cpu_s_total": M["cpu_s_total"],
           "wall_s": M["wall_s"]}
    gmax = gmax_of(tasks)
    for label in ("vote/shared@k0", "vote/isolated@k0"):
        means, per_g, per_body = {}, {}, {}
        for e in ("exp_full", "exp_early", "exp_late", "kexp"):
            vals = []
            for g in range(1, gmax + 1):
                x = np.array([val_f(t, label, e, g, "d")[0] for t in tasks])          # (tasks, cases)
                vals.append(x)
                per_g.setdefault(g, {})[e] = float(x.mean())
            allv = np.stack(vals)                                                   # (g, tasks, cases)
            means[e] = float(allv.mean())
            for b in sorted({t["body"] for t in tasks}):
                sel = [j for j, t in enumerate(tasks) if t["body"] == b]
                per_body.setdefault(b, {})[e] = float(allv[:, sel].mean())
            if e == "exp_full":
                means["exp_full_sheet_sd"] = float(allv.mean((0, 1)).std(ddof=1))
                means["exp_full_task_sd"] = float(allv.mean((0, 2)).std(ddof=1))
        rec[label] = {"mean": means, "by_generation": per_g, "by_body": per_body,
                      "injury_ok": bool(all(val_f(t, label, "injury_ok", g, "d")[0].all() for t in tasks
                                            for g in range(1, gmax + 1)))}
    s = rec["vote/shared@k0"]["mean"]
    rec["kappa"] = {"kappa": sig(1.0 / s["exp_full"]), "kappa_early": sig(1.0 / s["exp_early"]),
                    "kappa_late": sig(1.0 / s["exp_late"])}
    i = rec["vote/isolated@k0"]["mean"]
    rec["isolated_over_shared_exposure"] = i["exp_full"] / s["exp_full"]
    rec["kexp_all_zero"] = bool(s["kexp"] == 0 and i["kexp"] == 0)
    return rec


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P63's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "meaningful_margin_n": list(MEANINGFUL),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e006" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    ap.add_argument("--kappa", action="store_true")
    a = ap.parse_args()
    root = a.root[0] if len(a.root) == 1 else list(a.root)
    if a.kappa:
        rec = kappa(root)
        txt = json.dumps(rec, indent=1) + "\n"
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(txt)
        print(json.dumps({k: rec[k] for k in ("kappa", "isolated_over_shared_exposure", "kexp_all_zero",
                                              "bridge_all_equal")}))
        return
    if a.margins:
        sc, al, ex = margins(root)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps({"k_rule": K_RULE, "parts": sc, "aliased_tasks": al, "exposures": ex},
                                        indent=1) + "\n")
        return
    tasks, M = load(root)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "merged_from": M.get("merged_from"), "root": [str(r) for r in a.root],
         "design_digest": D.digest(), "parts": scored, "thresholds": TH, "meaningful_margin_n": list(MEANINGFUL),
         "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "aliased_tasks": aliases(tasks), "exposures": exposures(tasks), "per_firing": per_firing(tasks),
         "reported": rep}, indent=1) + "\n")
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
