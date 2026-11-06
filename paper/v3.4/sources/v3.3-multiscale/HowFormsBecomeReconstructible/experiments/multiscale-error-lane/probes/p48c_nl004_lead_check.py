"""P48c (python probes/p48c_nl004_lead_check.py ROOT): the lead's check of NL004, anchors the tissue makes.
LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by the lead in reviewing NL004's
phase A and committed before the freeze, dry-run first on P48 (engineering blocks 900129-900132, tag mse-p48);
1 November 2026; no simulation.

It checks the sha256 of every shard and raw file against the run's manifest (and, at the development stage, the run's
digest against the frozen design's), then:
1. recomputes the 26 registered parts (H1-H7) from REGISTRATION_NL004.md's words, not from nl004.analyze or
   nl004.predict, unrounded:
   - an endpoint is read at the last read (2,000 updates for the tissue and the recipients), per case: 't/r/' the
     tissue's record, 't/a/' the arbiter's refused shares and the anchors' shares, 'g/' the coded recipient gated by
     the parent's given anchors and 'm/' the one gated by anchors the successor makes at birth (both scored on the
     recipient's body); the branch names from each shard's own meta;
   - a part is formed per case, paired within the case; a block's value is the mean over its defined cases; the part
     is the mean over the blocks;
   - SD_block is the larger of the SD over the block values and the SD over every defined case / sqrt 8; the 95%
     interval is the mean +- t(0.975, n - 1) SD_block / sqrt n; on the probe, the margins (>= 3 sqrt(1/4 + 1/16)) and
     both halves;
2. from the raw final states, with the lead's own region signs and scoring (not nl002.sim.score):
   - the premise: A's acquired record holds A's sign at every cell and |R0| >= 0.2 everywhere;
   - every anchor code made at the branch against its declared source: A sign(R0), Mv sign(V0), Mpre sign(Racq0),
     Mmid sign(Racq100), Mmidc the confident part of Racq100, Me under R the record with the four regions flipped,
     Me under change B's record in the differing regions; K's square removed for the codes made before the kill;
   - the slow copies' anchors against sign(a), and every gated branch's anchor shares against the shards';
   - the successor's anchors made at birth (sign of the parent's final record at the sites) against the shards';
   - the shards' last-read spec_reg, align_A, ev_reg_ok and k_spec_reg recomputed from the final records;
3. reported beside them: the anchor codes' table, the gain sweep, the successors, the slow copies against the given
   anchors per case, the race in the R regions' anchors, the K arms (H8, reported by the lead's ruling), and the
   change comparison.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from mse.assay import Case                                      # noqa: E402  (frozen engine: the case keys)
from nl001 import sim as N1S                                     # noqa: E402  (frozen: the event regions, the kill square)

ROOT = Path(sys.argv[1])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []
say = lambda s="": (out.append(s), print(s, flush=True))

M = json.load(open(ROOT / "manifest.json"))
DEV = list(range(910517, 910522)) + list(range(910594, 910600)) + list(range(910873, 910878))
WANT = {"probe": ("mse-p48", [900129, 900130, 900131, 900132]), "development": ("mse-nl004", DEV)}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0], (STAGE, M["tag"])
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert not bad, bad[:5]
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1] and len(M["tasks"]) == 2 * len(BLOCKS), (BLOCKS, len(M["tasks"]))
NB = len(BLOCKS)
frozen = LANE / "nl004" / "frozen" / "design.json"
if STAGE == "development":
    assert frozen.exists() and json.load(open(frozen))["digest"] == M["design_digest"], "the draw is not under the frozen design"
say(f"P48c on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE != 'development' else ''}): {len(M['tasks'])} tasks, "
    f"{sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the manifest's; digest "
    f"{M['design_digest'][:12]}; rule {M['rule']}; {M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} "
    f"CPU-h, {M['workers']} workers, peak worker RSS {M['worker_maxrss_mb_peak']} MB")
assert M["rule"] == {"n": 1, "q": 0.75, "ring": 0, "ring_max": 0}

Z, NAMES, META = {}, {}, {}
for u in ("none", "dw"):
    for b in BLOCKS:
        z = np.load(ROOT / "shards" / u / f"{b}.npz")
        m = json.loads(str(z["__meta__"]))
        assert (m["unit"], int(m["block"]), m["tag"], m["design_digest"]) == (u, b, M["tag"], M["design_digest"])
        assert m["nl003_digest"].startswith("ece312e2b4f8") and m["rule"] == M["rule"]
        assert m["reads"] == [250, 1000, 2000] and m["reads2"] == [500, 1000, 2000] and len(m["cases"]) == 8
        tl = [f"{a}/{e}" for a, e in m["labels"]]
        rl = [f"{a}/{e}" for a, e in m["rlabels"]]
        nm = {"t/": tl, "s/": rl + list(m["succ"]), "c/": rl, "g/": list(m["parent_gated"]), "m/": rl,
              "gated": list(m["gated"]), "slow_rows": list(m["slow_rows"])}
        if u in NAMES:
            assert NAMES[u] == nm
        NAMES[u] = nm
        Z[(u, b)] = z
        META[(u, b)] = m


def ep(u, key, br, read=-1):
    """(blocks, cases) at a read (the last by default)."""
    i = NAMES[u][key[:2]].index(br)
    return np.array([Z[(u, b)][key][read, i, :] for b in BLOCKS], float)


def est(x):
    blk = np.array([np.mean(r[np.isfinite(r)]) for r in x])
    v = float(blk.mean())
    flat = x[np.isfinite(x)]
    sd4, sdc = blk.std(ddof=1), flat.std(ddof=1) / math.sqrt(x.shape[1])
    sd = max(sd4, sdc)
    h = stats.t.ppf(0.975, NB - 1) * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sd4": sd4, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())), "nan": int((~np.isfinite(x)).sum()),
            "def_per_block": [int(np.isfinite(r).sum()) for r in x]}


K = "k0.75"
R_, A_, G_, MM = "t/r/", "t/a/", "g/", "m/"
D_ = lambda u, key, b1, b2: ep(u, key, b1) - ep(u, key, b2)
prot = lambda u, code: D_(u, R_ + "spec_reg", f"foreign-{K}+{code}/none", f"foreign-{K}/none")
UN = {"none": "stores", "dw": "body"}
PARTS = []
for u, th in (("none", -0.9), ("dw", -0.5)):
    PARTS.append(("H1", f"{UN[u]}: ev(copy+Me/R) - ev(copy/R)", th, "le",
                  lambda u=u: D_(u, R_ + "ev_reg_ok", f"copy-{K}+Me/R", f"copy-{K}/R")))
for u, th in (("none", 1.25), ("dw", 1.05)):
    PARTS.append(("H2", f"{UN[u]}: spec(foreign+A/none) - spec(foreign+Mt1000/none)", th, "ge",
                  lambda u=u: D_(u, R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}+Mt1000/none")))
for u, th in (("none", 0.8), ("dw", 0.65)):
    PARTS.append(("H3", f"{UN[u]}: spec(foreign+A/none) - spec(foreign+Mpre/none)", th, "ge",
                  lambda u=u: D_(u, R_ + "spec_reg", f"foreign-{K}+A/none", f"foreign-{K}+Mpre/none")))
for u, th in (("none", 0.2), ("dw", 0.1)):
    PARTS.append(("H3", f"{UN[u]}: ref_all(copy+Mpre/none) - ref_all(copy+A/none)", th, "ge",
                  lambda u=u: D_(u, A_ + "ref_all", f"copy-{K}+Mpre/none", f"copy-{K}+A/none")))
for u, th in (("none", 0.85), ("dw", 1.0)):
    PARTS.append(("H4", f"{UN[u]}: protection(Mv) = spec(foreign+Mv/none) - spec(foreign/none)", th, "ge",
                  lambda u=u: prot(u, "Mv")))
PARTS.append(("H4", "body: align_A(copy+Mv/none) - align_A(copy/none)", 0.03, "ge",
              lambda: D_("dw", R_ + "align_A", f"copy-{K}+Mv/none", f"copy-{K}/none")))
for code, ths in (("S1e-2", (1.3, 1.15)), ("S1e-3", (1.3, 1.1))):
    for u, th in zip(("none", "dw"), ths):
        PARTS.append(("H5", f"{UN[u]}: protection({code})", th, "ge", lambda u=u, code=code: prot(u, code)))
for code, ths, sense in (("S1e-2", (-0.85, -0.45), "le"), ("S1e-3", (-0.07, -0.06), "ge")):
    for u, th in zip(("none", "dw"), ths):
        PARTS.append(("H5", f"{UN[u]}: ev(copy+{code}/R) - ev(copy+A/R)", th, sense,
                      lambda u=u, code=code: D_(u, R_ + "ev_reg_ok", f"copy-{K}+{code}/R", f"copy-{K}+A/R")))
PARTS.append(("H6", "body: m/spec(foreign+A/none), the successor-made gated recipient after a protected parent", 0.6, "ge",
              lambda: ep("dw", MM + "spec_reg", f"foreign-{K}+A/none")))
PARTS.append(("H6", "body: m/spec(foreign/none), the same after an overwritten parent", -0.3, "le",
              lambda: ep("dw", MM + "spec_reg", f"foreign-{K}/none")))
PARTS.append(("H6", "body: m/spec(foreign+A/none) - g/spec(foreign+A/none), own anchors less the parent's", -0.02, "ge",
              lambda: ep("dw", MM + "spec_reg", f"foreign-{K}+A/none") - ep("dw", G_ + "spec_reg", f"foreign-{K}+A/none")))
for u, th in (("none", -0.95), ("dw", -0.8)):
    PARTS.append(("H7", f"{UN[u]}: spec(foreign+Me/change)", th, "le", lambda u=u: ep(u, R_ + "spec_reg", f"foreign-{K}+Me/change")))
for u, th in (("none", -1.45), ("dw", -1.25)):
    PARTS.append(("H7", f"{UN[u]}: spec(copy+Me/change) - spec(copy/change)", th, "le",
                  lambda u=u: D_(u, R_ + "spec_reg", f"copy-{K}+Me/change", f"copy-{K}/change")))
assert len(PARTS) == 26

KR = 3 * math.sqrt(1 / 4 + 1 / 16)
say(f"\nREGISTERED PARTS ({NB} blocks x 8 cases; [95% t interval], t(0.975, {NB - 1}) = {stats.t.ppf(0.975, NB - 1):.4f}; "
    f"SD_block the larger of the block SD and the case SD / sqrt 8; the rule: each margin >= {KR:.4f}, both halves passing)")
ok_by, worst = {}, []
for sid, words, th, sense, f in PARTS:
    q = est(f())
    holds = q["v"] >= th if sense == "ge" else q["v"] <= th
    ok_by.setdefault(sid, []).append(holds)
    say(f"  {sid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}]  SD {q['sd']:.6f} (block {q['sd4']:.6f}, case/sqrt8 "
        f"{q['sdc']:.6f})  {'>=' if sense == 'ge' else '<='} {th:+.2f}: {'holds' if holds else 'FAILS'}"
        + (f"; {q['nan']} undefined cases (defined per block {q['def_per_block']})" if q["nan"] else ""))
    if NB == 4:
        marg = ((q["v"] - th) if sense == "ge" else (th - q["v"])) / q["sd"] if q["sd"] > 0 else math.inf
        hok = all((h >= th) if sense == "ge" else (h <= th) for h in q["halves"])
        worst.append((marg, sid, words))
        say(f"       margin {marg:.4f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}; rule "
            f"{'ok' if marg >= KR and hok else 'NOT MET'}")
say("  VERDICTS: " + ", ".join(f"{s} {'HOLDS' if all(v) else 'FAILS'}" for s, v in ok_by.items())
    + ("  [a dry run on engineering blocks: not a development result]" if STAGE != "development" else ""))
if worst:
    say("  narrowest margins: " + "; ".join(f"{s} {w.split(':')[0]} {m:.2f}" for m, s, w in sorted(worst)[:5]))

# ---------- 2. the raw final states ----------
say("\nFROM THE RAW FINAL STATES (the lead's own region signs and scoring)")


def usign(x, s):
    """The sign of each s x s unit's mean of sign(x)."""
    n = x.shape[-1] // s
    return np.sign(np.sign(x).reshape(*x.shape[:-2], n, s, n, s).mean(axis=(-3, -1)))


def frac(mask, ok):
    n = mask.sum((-2, -1))
    return np.where(n > 0, (mask & ok).sum((-2, -1)) / np.maximum(n, 1), np.nan)


rep = lambda x, s=4: np.repeat(np.repeat(x, s, -2), s, -1)
prem = {"cells": 0, "wrong": 0, "minabs": math.inf}
anc_bad, anc_n, sh_max, slow_bad, born_max, born_n = {}, {}, 0.0, 0, 0.0, 0
end_max = {e: 0.0 for e in ("spec_reg", "align_A", "ev_reg_ok", "k_spec_reg")}
for u in ("none", "dw"):
    for b in BLOCKS:
        m = META[(u, b)]
        raw = np.load(ROOT / "raw" / u / f"{b}.npz")
        TA, TB = raw["TA"].astype(float), raw["TB"].astype(float)
        R0, RB, V0 = raw["R0"].astype(float), raw["RB"].astype(float), raw["V0"].astype(float)
        sites = raw["sites"].astype(bool)
        cases = [Case(*c) for c in m["cases"]]
        units = N1S.event_units(cases, m["tag"])
        prem["cells"] += R0.size
        prem["wrong"] += int((np.sign(R0) != np.sign(TA)).sum())
        prem["minabs"] = min(prem["minabs"], float(np.abs(R0).min()))
        regA, regB = usign(TA, 4), usign(TB, 4)
        dreg = regA != regB
        ev = np.zeros_like(dreg)
        for j, uu in enumerate(units):
            for (ri, rj) in uu["regions"]:
                ev[j, ri, rj] = True
        kill = np.stack([N1S.kill_mask(uu, raw["TA"][j]) for j, uu in enumerate(units)])
        kreg = usign(kill * 1.0, 4) > 0
        kdreg = kreg & dreg
        # the declared sources of the codes made at the branch (before K's removal)
        flipR = R0.copy()
        for j, uu in enumerate(units):
            for (ri, rj) in uu["regions"]:
                flipR[j, ri * 4:(ri + 1) * 4, rj * 4:(rj + 1) * 4] *= -1
        conf = lambda x: np.where(x >= 0.2, 1.0, np.where(x <= -0.2, -1.0, 0.0))
        SRC = {"A": np.sign(R0), "Mv": np.sign(V0), "Mpre": np.sign(raw["Racq0"].astype(float)),
               "Mmid": np.sign(raw["Racq100"].astype(float)), "Mmidc": conf(raw["Racq100"].astype(float))}
        gated, tl = NAMES[u]["gated"], NAMES[u]["t/"]
        am_all, av_all = raw["am"].astype(bool), raw["aval"].astype(float)
        a_slow, srows = raw["a_slow"].astype(float), NAMES[u]["slow_rows"]
        r_fin = raw["r"].astype(float)
        for gi, lab in enumerate(gated):
            arm, event = lab.split("/")
            code = arm.split("+")[1]
            am, av = am_all[gi], av_all[gi]
            li = tl.index(lab)
            # the anchor shares against the shards' (the last read): present, at A's sign, at B's sign
            for key, val in (("anc_present", am.sum((-2, -1))), ("anc_A", (am & (av == np.sign(TA))).sum((-2, -1))),
                             ("anc_B", (am & (av == np.sign(TB))).sum((-2, -1)))):
                sh_max = max(sh_max, float(np.abs(val / sites.sum((-2, -1)) - Z[(u, b)][A_ + key][-1, li, :]).max()))
            if code in ("S1e-2", "S1e-3"):
                rows = [srows.index(li * 8 + j) for j in range(8)]
                sa = a_slow[rows]
                slow_bad += int(((sa != 0) != am).sum() + (np.sign(sa) != av).sum())
                continue
            if code in ("Mt250", "Mt1000"):
                continue                                       # made at t_c from a record the raw files do not keep
            if code == "Me":
                src = np.where(rep(dreg), RB, R0) if event == "change" else (flipR if event == "R" else None)
                src = np.sign(src)
            else:
                src = SRC[code]
            want_m = sites & (src != 0)
            if event == "K" and code != "Me":
                want_m = want_m & ~kill
            bad_ = int((want_m != am).sum() + (np.where(want_m, src, 0.0) != av).sum())
            anc_bad[code] = anc_bad.get(code, 0) + bad_
            anc_n[code] = anc_n.get(code, 0) + 1
        # the shards' endpoints recomputed from the final records
        rs = usign(r_fin, 4)
        for li, lab in enumerate(tl):
            arm, event = lab.split("/")
            x = r_fin[li]
            got = {"spec_reg": frac(dreg, rs[li] == regA) - frac(dreg, rs[li] == regB),
                   "align_A": (np.sign(x) == np.sign(TA)).mean((-2, -1))}
            if event == "R":
                got["ev_reg_ok"] = frac(ev, rs[li] == regA)
            if event == "K":
                got["k_spec_reg"] = frac(kdreg, rs[li] == regA) - frac(kdreg, rs[li] == regB)
            for e, v in got.items():
                w = Z[(u, b)][R_ + e][-1, li, :]
                fin = np.isfinite(w)
                assert np.array_equal(fin, np.isfinite(v)), (u, b, lab, e)
                end_max[e] = max(end_max[e], float(np.abs(v[fin] - w[fin]).max()) if fin.any() else 0.0)
        # the successor's anchors made at birth from the parent's final record
        for ri, lab in enumerate(NAMES[u]["m/"]):
            x = r_fin[tl.index(lab)]
            amb = sites & (x != 0)
            for key, val in (("anc_present", amb.sum((-2, -1))), ("anc_A", (amb & (np.sign(x) == np.sign(TA))).sum((-2, -1)))):
                born_max = max(born_max, float(np.abs(val / sites.sum((-2, -1)) - Z[(u, b)][MM + key][-1, ri, :]).max()))
            born_n += 1
say(f"  the premise: sign(R0_A) differs from A's template at {prem['wrong']} of {prem['cells']:,} cells; min |R0_A| "
    f"{prem['minabs']:.4f} (VMIN 0.2): the branch commitment from the record is the given anchors")
say("  the anchors made at the branch against their declared sources (sites, value 0 = none, K's square removed), "
    "differing cells: " + ", ".join(f"{c} {anc_bad[c]} over {anc_n[c]} branches" for c in sorted(anc_bad)))
say(f"  the slow copies' anchors against sign(a): {slow_bad} differing cells; every gated branch's anchor shares "
    f"(present, at A's, at B's sign) against the shards': largest difference {sh_max:.2e}")
say(f"  the successor's anchors made at birth (present, at A's sign) against the shards', {born_n} label-blocks: "
    f"largest difference {born_max:.2e}")
say("  the shards' last-read endpoints recomputed from the final records, largest difference: "
    + ", ".join(f"{e} {v:.2e}" for e, v in end_max.items()))

# ---------- 3. reported ----------
say("\nREPORTED (not registered)")
mean = lambda x: est(x)["v"]
say("  every anchor code at 0.75 x KC (last read): spec foreign/none, protection (share of A's), spec corrupt/none, "
    "repair ev copy/R (change from off), align copy/none, refused share copy/none")
for u in ("none", "dw"):
    pA = mean(prot(u, "A"))
    for code in ("", "A", "Mv", "Mt250", "Mt1000", "Mpre", "Mmid", "Mmidc", "S1e-2", "S1e-3"):
        c = f"+{code}" if code else ""
        sf = mean(ep(u, R_ + "spec_reg", f"foreign-{K}{c}/none"))
        sc = mean(ep(u, R_ + "spec_reg", f"corrupt-{K}{c}/none"))
        evr = mean(ep(u, R_ + "ev_reg_ok", f"copy-{K}{c}/R"))
        dev = mean(D_(u, R_ + "ev_reg_ok", f"copy-{K}{c}/R", f"copy-{K}/R"))
        al = mean(ep(u, R_ + "align_A", f"copy-{K}{c}/none"))
        if code:
            p_ = mean(prot(u, code))
            rc = mean(ep(u, A_ + "ref_all", f"copy-{K}{c}/none"))
            say(f"    {code:6s} {UN[u]:6s} {sf:+.3f}  {p_:+.3f} ({p_ / pA:.2f})  {sc:+.3f}  {evr:.3f} ({dev:+.3f})  {al:.3f}  {rc:.3f}")
        else:
            say(f"    {'off':6s} {UN[u]:6s} {sf:+.3f}  {'':15s}  {sc:+.3f}  {evr:.3f}  {al:.3f}")
    me = ep(u, R_ + "ev_reg_ok", f"copy-{K}+Me/R")
    say(f"    {'Me':6s} {UN[u]:6s} repair {mean(me):.3f}; its R regions' anchors at A's sign "
        f"{mean(ep(u, A_ + 'anc_A_ev', f'copy-{K}+Me/R')):.3f}")
say("  the anchors' shares: at A's sign over the sites, on A's minority cells; Mmidc present")
for u in ("none", "dw"):
    for code in ("Mv", "Mpre", "Mmid", "Mmidc"):
        say(f"    {code:6s} {UN[u]:6s} {mean(ep(u, A_ + 'anc_A', f'copy-{K}+{code}/none')):.3f}  "
            f"{mean(ep(u, A_ + 'anc_A_min', f'copy-{K}+{code}/none')):.3f}  present "
            f"{mean(ep(u, A_ + 'anc_present', f'copy-{K}+{code}/none')):.3f}")
say("  the slow copies against the given anchors, per case (spec foreign/none): cases equal / all")
for u in ("none", "dw"):
    for code in ("S1e-2", "S1e-3"):
        d = D_(u, R_ + "spec_reg", f"foreign-{K}+{code}/none", f"foreign-{K}+A/none")
        say(f"    {code} {UN[u]}: {int((d == 0).sum())} / {d.size}; mean difference {mean(d):+.4f}")
say("  the race: the R regions' anchors at A's sign, and the repair, at reads 250 / 1,000 / 2,000 (copy+X/R)")
for u in ("none", "dw"):
    for code in ("A", "S1e-2", "S1e-3"):
        an = [mean(ep(u, A_ + "anc_A_ev", f"copy-{K}+{code}/R", rd)) for rd in range(3)]
        ev_ = [mean(ep(u, R_ + "ev_reg_ok", f"copy-{K}+{code}/R", rd)) for rd in range(3)]
        mn = [mean(ep(u, A_ + "anc_A_min", f"copy-{K}+{code}/none", rd)) for rd in range(3)]
        say(f"    {code:6s} {UN[u]:6s} anchors {an[0]:.3f} {an[1]:.3f} {an[2]:.3f}; repair {ev_[0]:.3f} {ev_[1]:.3f} "
            f"{ev_[2]:.3f}; minority-cell anchors at A's sign (copy/none) {mn[0]:.3f} {mn[1]:.3f} {mn[2]:.3f}")
say("  the gain sweep: spec foreign/none, ev copy/R, spec corrupt/none for off, A, Mv, S1e-3")
for k in ("k0.5", "k0.75", "k1"):
    for u in ("none", "dw"):
        cells = []
        for code in ("", "+A", "+Mv", "+S1e-3"):
            cells.append(f"{mean(ep(u, R_ + 'spec_reg', f'foreign-{k}{code}/none')):+.3f}, "
                         f"{mean(ep(u, R_ + 'ev_reg_ok', f'copy-{k}{code}/R')):.3f}, "
                         f"{mean(ep(u, R_ + 'spec_reg', f'corrupt-{k}{code}/none')):+.3f}")
        say(f"    {k:5s} {UN[u]:6s} " + " | ".join(cells))
say("  the successors: the successor-made gated recipient's spec after foreign+X/none (and after the arbiter off)")
for u in ("none", "dw"):
    row = [f"off {mean(ep(u, MM + 'spec_reg', f'foreign-{K}/none')):+.3f}"]
    row += [f"{c} {mean(ep(u, MM + 'spec_reg', f'foreign-{K}+{c}/none')):+.3f}"
            for c in ("A", "Mv", "Mt250", "Mt1000", "Mpre", "Mmid", "Mmidc", "S1e-2", "S1e-3")]
    row.append(f"parent-gated (A) {mean(ep(u, G_ + 'spec_reg', f'foreign-{K}+A/none')):+.3f}")
    row.append(f"record-only after foreign+A {mean(ep(u, 's/spec_reg', f'foreign-{K}+A/none')):+.3f}, ungated coded "
               f"{mean(ep(u, 'c/spec_reg', f'foreign-{K}+A/none')):+.3f}")
    say(f"    {UN[u]}: " + "; ".join(row))
say("  K (H8, reported by the lead's ruling): spec over the sheet and inside the killed square (k_spec), foreign+X/K; "
    "k_spec(foreign+S1e-3/K) - k_spec(foreign+A/K) per case")
for u in ("none", "dw"):
    row = []
    for code in ("", "+A", "+Mv", "+S1e-2", "+S1e-3"):
        row.append(f"{code[1:] or 'off'} {mean(ep(u, R_ + 'spec_reg', f'foreign-{K}{code}/K')):+.3f} / "
                   f"{mean(ep(u, R_ + 'k_spec_reg', f'foreign-{K}{code}/K')):+.3f}")
    say(f"    {UN[u]}: " + "; ".join(row))
    for code in ("S1e-2", "S1e-3"):
        d = D_(u, R_ + "k_spec_reg", f"foreign-{K}+{code}/K", f"foreign-{K}+A/K")
        dc = D_(u, R_ + "k_spec_reg", f"copy-{K}+{code}/K", f"copy-{K}+A/K")
        q, qc = est(d), est(dc)
        fin = np.isfinite(d)
        say(f"      {code}: foreign {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.4f}), nonzero in "
            f"{int((d[fin] != 0).sum())} of {int(fin.sum())} defined cases; copy {qc['v']:+.6f}, nonzero in "
            f"{int((dc[np.isfinite(dc)] != 0).sum())}; the square's differing-region sites at B's sign "
            f"{mean(ep(u, A_ + 'anc_B_kd', f'foreign-{K}+{code}/K')):.3f}")
say("  change: spec against A, copy/change (off, A, Me); foreign/change (off, A, Me)")
for u in ("none", "dw"):
    say(f"    {UN[u]}: copy " + ", ".join(f"{mean(ep(u, R_ + 'spec_reg', f'copy-{K}{c}/change')):+.3f}" for c in ("", "+A", "+Me"))
        + "; foreign " + ", ".join(f"{mean(ep(u, R_ + 'spec_reg', f'foreign-{K}{c}/change')):+.3f}" for c in ("", "+A", "+Me")))
say("  late commitments: the final spec foreign+Mt/none against the arbiter-off twin's at t_c")
for u in ("none", "dw"):
    for code, rd in (("Mt250", 0), ("Mt1000", 1)):
        say(f"    {code} {UN[u]}: {mean(ep(u, R_ + 'spec_reg', f'foreign-{K}+{code}/none')):+.3f} against "
            f"{mean(ep(u, R_ + 'spec_reg', f'foreign-{K}/none', rd)):+.3f}")

name = f"p48c_nl004_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
