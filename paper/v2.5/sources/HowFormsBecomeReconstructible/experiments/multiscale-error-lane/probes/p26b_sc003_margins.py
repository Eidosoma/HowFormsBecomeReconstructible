"""Engineering probe P26b (python probes/p26b_sc003_margins.py): the quantities SC003's draft statements read, from
P26's per-block values (the scratch FULL file), with means, SDs over P26's four blocks and per-item values.
ENGINEERING_PROBE_NOT_EVIDENCE; the threshold input for REGISTRATION_SC003.md (BE002's rule: SD_block = max(the item's
own SD, the RMS of the part's item SDs); an every-item part must sit >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside
P26's worst item; a pooled part uses the SD over blocks of the pooled per-block value).
Writes probes/results/p26b_sc003_margins.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from sc003 import design as D  # noqa: E402

FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p26_sc003_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p26b_sc003_margins.json"
K = 3.0 * np.sqrt(1 / 4 + 1 / 16)
ITEMS = tuple((u, b) for u in D.UNITS for b in D.BODIES)


def main():
    F = json.loads(FULL.read_text())
    BV, blocks = F["blocks_values"], F["blocks"]

    def arms(u, b, rn):
        return BV[u][f"{b}/{rn}/arms"][str(blocks[0])]

    def val(u, b, rn, arm, e="r_in", ti=-1):
        """Per-block values (array over P26's blocks)."""
        i = arms(u, b, rn).index(arm)
        return np.array([BV[u][f"{b}/{rn}/{e}"][str(blk)][ti][i] for blk in blocks])

    def tr(u, b, rn, arm, t, e="trace"):
        i = arms(u, b, rn).index(arm)
        return np.array([BV[u][f"{b}/{rn}/{e}"][str(blk)][t // D.TRACE - 1][i] for blk in blocks])

    def newc(u, b, rn, arm, q):
        i = arms(u, b, rn).index(arm)
        return np.array([BV[u][f"{b}/{rn}/newc"][str(blk)][q][i] for blk in blocks])

    def summ(items):
        """items: {name: per-block array}; per-item mean, SD; pooled per-block mean's mean and SD."""
        pooled = np.mean(np.stack(list(items.values())), 0)
        sds = {k: float(v.std(ddof=1)) for k, v in items.items()}
        rms = float(np.sqrt(np.mean(np.square(list(sds.values())))))
        return {"items": {k: [round(float(v.mean()), 5), round(sds[k], 5)] for k, v in items.items()},
                "min": round(min(float(v.mean()) for v in items.values()), 5),
                "max": round(max(float(v.mean()) for v in items.values()), 5),
                "rms_sd": round(rms, 5), "pooled": [round(float(pooled.mean()), 5), round(float(pooled.std(ddof=1)), 5)]}

    def loss(u, b, mu, arm):
        """Extra loss under scattered corruption: (none8 - cue8) r_all of the arm, beyond the cue arm's own."""
        g = lambda a: val(u, b, f"none8@{mu:g}", a, "r_all") - val(u, b, f"cue8@{mu:g}", a, "r_all")
        return g(arm) - g("cue")

    Q = {}
    for mu in D.MUS:
        m = f"@{mu:g}"
        Q[f"iso_minus_inst_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", "iso-3") - val(u, b, f"change4{m}", "inst-3") for u, b in ITEMS})
        for tau in ("300", "1000"):
            Q[f"emt{tau}_minus_inst_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", f"emt-{tau}") - val(u, b, f"change4{m}", "inst-3") for u, b in ITEMS})
            Q[f"isoemt{tau}_minus_emt{tau}_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", f"iso-emt-{tau}") - val(u, b, f"change4{m}", f"emt-{tau}") for u, b in ITEMS})
            Q[f"mat{tau}_minus_isoemt{tau}_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", f"mat-{tau}") - val(u, b, f"change4{m}", f"iso-emt-{tau}") for u, b in ITEMS})
            Q[f"mat{tau}_minus_emt{tau}_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", f"mat-{tau}") - val(u, b, f"change4{m}", f"emt-{tau}") for u, b in ITEMS})
            Q[f"mat{tau}_minus_inst_change4{m}"] = summ({f"{u}/{b}": val(u, b, f"change4{m}", f"mat-{tau}") - val(u, b, f"change4{m}", "inst-3") for u, b in ITEMS})
            Q[f"extra_loss_mat{tau}_minus_isoemt{tau}{m}"] = summ({f"{u}/{b}": loss(u, b, mu, f"mat-{tau}") - loss(u, b, mu, f"iso-emt-{tau}") for u, b in ITEMS})
            Q[f"none_r_all_mat{tau}_minus_isoemt{tau}{m}"] = summ({f"{u}/{b}": val(u, b, f"none8{m}", f"mat-{tau}", "r_all") - val(u, b, f"none8{m}", f"iso-emt-{tau}", "r_all") for u, b in ITEMS})
            Q[f"isoemt{tau}_gain_minus_iso3_gain_change4{m}"] = summ({f"{u}/{b}": (val(u, b, f"change4{m}", f"iso-emt-{tau}") - val(u, b, f"change4{m}", f"emt-{tau}")) - (val(u, b, f"change4{m}", "iso-3") - val(u, b, f"change4{m}", "inst-3")) for u, b in ITEMS})
        for arm in D.ARMS_T[1:]:
            Q[f"extra_loss_{arm}{m}"] = summ({f"{u}/{b}": loss(u, b, mu, arm) for u, b in ITEMS})
            Q[f"none_r_all_{arm}_minus_inst{m}"] = summ({f"{u}/{b}": val(u, b, f"none8{m}", arm, "r_all") - val(u, b, f"none8{m}", "inst-3", "r_all") for u, b in ITEMS})
            for s in ("none8", "cue8", "change4"):
                Q[f"newc0_{arm}_{s}{m}"] = summ({f"{u}/{b}": newc(u, b, f"{s}{m}", arm, 0) for u, b in ITEMS})
        Q[f"iso_extra_loss_minus_inst{m}"] = summ({f"{u}/{b}": loss(u, b, mu, "iso-3") - loss(u, b, mu, "inst-3") for u, b in ITEMS})
        for tau in ("300", "1000"):
            Q[f"newc0_ratio_mat{tau}_to_iso_none8{m}"] = summ({f"{u}/{b}": newc(u, b, f"none8{m}", f"mat-{tau}", 0) / np.maximum(newc(u, b, f"none8{m}", "iso-3", 0), 1e-9) for u, b in ITEMS})
            Q[f"newc0_ratio_mat{tau}_to_iso_cue8{m}"] = summ({f"{u}/{b}": newc(u, b, f"cue8{m}", f"mat-{tau}", 0) / np.maximum(newc(u, b, f"cue8{m}", "iso-3", 0), 1e-9) for u, b in ITEMS})
    # the pace: the birth check's adoption against births per site (mu t), the pooled coupling's against time
    for t_fast, t_slow in ((250, 1000), (500, 2000), (1000, 4000)):
        d_f = {f"{u}/{b}": tr(u, b, "change4@0.001", "iso-3", t_fast) - tr(u, b, "change4@0.001", "inst-3", t_fast) for u, b in ITEMS}
        d_s = {f"{u}/{b}": tr(u, b, "change4@0.00025", "iso-3", t_slow) - tr(u, b, "change4@0.00025", "inst-3", t_slow) for u, b in ITEMS}
        Q[f"pace_iso_mut{t_fast / 1000:g}_fast_minus_slow"] = summ({k: d_f[k] - d_s[k] for k in d_f})
        Q[f"pace_iso_mut{t_fast / 1000:g}_fast"] = summ(d_f)
        Q[f"pace_iso_mut{t_fast / 1000:g}_slow"] = summ(d_s)
    for t in (250, 1000, 2000, 4000):
        Q[f"pace_iso_t{t}_fast_minus_slow"] = summ({f"{u}/{b}": (tr(u, b, "change4@0.001", "iso-3", t) - tr(u, b, "change4@0.001", "inst-3", t))
                                                    - (tr(u, b, "change4@0.00025", "iso-3", t) - tr(u, b, "change4@0.00025", "inst-3", t)) for u, b in ITEMS})
        for mu in D.MUS:
            m = f"@{mu:g}"
            for arm in ("iso-3", "emt-300", "emt-1000", "mat-300", "mat-1000", "iso-emt-300", "iso-emt-1000"):
                Q[f"trace_{arm}_minus_inst_t{t}{m}"] = summ({f"{u}/{b}": tr(u, b, f"change4{m}", arm, t) - tr(u, b, f"change4{m}", "inst-3", t) for u, b in ITEMS})
    # births, not time: at t, the fast rate's birth-check adoption nearer the slow rate's at equal births (4t) than at t
    for t_ in (500, 1000):
        f_ = {f"{u}/{b}": tr(u, b, "change4@0.001", "iso-3", t_) - tr(u, b, "change4@0.001", "inst-3", t_) for u, b in ITEMS}
        s1 = {f"{u}/{b}": tr(u, b, "change4@0.00025", "iso-3", t_) - tr(u, b, "change4@0.00025", "inst-3", t_) for u, b in ITEMS}
        s4 = {f"{u}/{b}": tr(u, b, "change4@0.00025", "iso-3", 4 * t_) - tr(u, b, "change4@0.00025", "inst-3", 4 * t_) for u, b in ITEMS}
        F_, S1, S4_ = (np.mean(np.stack(list(x.values())), 0) for x in (f_, s1, s4))          # pooled per block
        g = (F_ - S1) - np.abs(F_ - S4_)
        Q[f"pace_nearer_births_t{t_}"] = {"pooled": [round(float(g.mean()), 5), round(float(g.std(ddof=1)), 5)],
                                          "equal_time": [round(float((F_ - S1).mean()), 5), round(float((F_ - S1).std(ddof=1)), 5)],
                                          "equal_births": [round(float((F_ - S4_).mean()), 5), round(float((F_ - S4_).std(ddof=1)), 5)]}
    # the same, averaged over t = 200, 300, ..., 1,000 (mu t = 0.2 ... 1 at the faster rate)
    ts = list(range(200, 1001, 100))
    per = lambda mu_, arm_, t_: {f"{u}/{b}": tr(u, b, f"change4@{mu_:g}", arm_, t_) - tr(u, b, f"change4@{mu_:g}", "inst-3", t_) for u, b in ITEMS}
    et = {k: np.mean([per(1e-3, "iso-3", t_)[k] - per(2.5e-4, "iso-3", t_)[k] for t_ in ts], 0) for k in per(1e-3, "iso-3", 200)}
    eb = {k: np.mean([per(1e-3, "iso-3", t_)[k] - per(2.5e-4, "iso-3", 4 * t_)[k] for t_ in ts], 0) for k in et}
    Q["pace_avg_equal_time"] = summ(et)
    Q["pace_avg_equal_births"] = summ(eb)
    ET, EB = np.mean(np.stack(list(et.values())), 0), np.mean(np.stack(list(eb.values())), 0)
    g = ET - np.abs(EB)
    Q["pace_avg_time_minus_abs_births"] = {"pooled": [round(float(g.mean()), 5), round(float(g.std(ddof=1)), 5)]}
    # the pooled coupling at once, the check over time: adoption beyond inst-3 from t = 200 to t = 2,000
    for mu in D.MUS:
        m_ = f"@{mu:g}"
        for arm in ("emt-300", "emt-1000", "iso-3"):
            Q[f"growth_200_2000_{arm}{m_}"] = summ({f"{u}/{b}": (tr(u, b, f"change4{m_}", arm, 2000) - tr(u, b, f"change4{m_}", "inst-3", 2000))
                                                    - (tr(u, b, f"change4{m_}", arm, 200) - tr(u, b, f"change4{m_}", "inst-3", 200)) for u, b in ITEMS})
            Q[f"level_t200_{arm}{m_}"] = summ({f"{u}/{b}": tr(u, b, f"change4{m_}", arm, 200) - tr(u, b, f"change4{m_}", "inst-3", 200) for u, b in ITEMS})
        for tau in ("300", "1000"):
            Q[f"growth_iso_minus_emt{tau}{m_}"] = summ({f"{u}/{b}": ((tr(u, b, f"change4{m_}", "iso-3", 2000) - tr(u, b, f"change4{m_}", "iso-3", 200))
                                                                  - (tr(u, b, f"change4{m_}", f"emt-{tau}", 2000) - tr(u, b, f"change4{m_}", f"emt-{tau}", 200)))
                                                                 for u, b in ITEMS})
        Q[f"iso_extra_loss_rate_diff"] = summ({f"{u}/{b}": loss(u, b, 1e-3, "iso-3") - loss(u, b, 2.5e-4, "iso-3") for u, b in ITEMS})
        Q[f"none_r_all_iso-3_minus_inst_S4{m_}"] = summ({f"{u}/{b}": val(u, b, f"none8{m_}", "iso-3", "r_all") - val(u, b, f"none8{m_}", "inst-3", "r_all") for u, b in ITEMS if u.startswith("S4")})
    # the wound
    Q["regrow_iso-3_minus_inst_S4"] = summ({f"{u}/{b}": val(u, b, "regrow8@0", "iso-3") - val(u, b, "regrow8@0", "inst-3") for u, b in ITEMS if u.startswith("S4")})
    Q["regrow_iso-3_minus_inst_F0"] = summ({f"{u}/{b}": val(u, b, "regrow8@0", "iso-3") - val(u, b, "regrow8@0", "inst-3") for u, b in ITEMS if u.startswith("F0")})
    for arm in ("iso-3", "mat-300", "mat-1000"):
        Q[f"regrow_{arm}_minus_inst"] = summ({f"{u}/{b}": val(u, b, "regrow8@0", arm) - val(u, b, "regrow8@0", "inst-3") for u, b in ITEMS})
        Q[f"regrow_shrink_{arm}"] = summ({f"{u}/{b}": (val(u, b, "regrow8@0", arm) - val(u, b, "regrow8@0", "inst-3"))
                                          - (val(u, b, "regrow+cue8@0", arm) - val(u, b, "regrow+cue8@0", "inst-3")) for u, b in ITEMS})
        Q[f"regrow_cue_r_out_{arm}_minus_inst"] = summ({f"{u}/{b}": val(u, b, "regrow+cue8@0", arm, "r_out") - val(u, b, "regrow+cue8@0", "inst-3", "r_out") for u, b in ITEMS})
        Q[f"regrow_r_out_{arm}_minus_inst"] = summ({f"{u}/{b}": val(u, b, "regrow8@0", arm, "r_out") - val(u, b, "regrow8@0", "inst-3", "r_out") for u, b in ITEMS})
    for arm in ("mat-300", "mat-1000"):
        Q[f"regrow_{arm}_minus_iso"] = summ({f"{u}/{b}": val(u, b, "regrow8@0", arm) - val(u, b, "regrow8@0", "iso-3") for u, b in ITEMS})
    # probe-only laws at mu 1e-3
    for arm in ("gate-300", "sister-300"):
        for s in ("cue8", "change4"):
            rn = f"{s}@0.001"
            ep = "r_all" if s == "cue8" else "r_in"
            Q[f"probe_{arm}_minus_mat300_{s}"] = summ({f"{u}/{b}": val(u, b, rn, arm, ep) - val(u, b, rn, "mat-300", ep) for u, b in ITEMS})
            for q in range(len(D.AGE_BINS)):
                Q[f"probe_newc{q}_{arm}_{s}"] = summ({f"{u}/{b}": newc(u, b, rn, arm, q) for u, b in ITEMS})
                Q[f"probe_newc{q}_mat-300_{s}"] = summ({f"{u}/{b}": newc(u, b, rn, "mat-300", q) for u, b in ITEMS})
    out = {"probe": "P26b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "source": str(FULL), "blocks": blocks,
           "k_every_item": round(float(K), 4), "quantities": Q}
    OUT.write_text(json.dumps(out, indent=0, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} B)")


if __name__ == "__main__":
    main()
