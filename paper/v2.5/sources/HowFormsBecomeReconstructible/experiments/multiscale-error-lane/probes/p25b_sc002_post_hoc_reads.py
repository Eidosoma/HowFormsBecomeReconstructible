"""Post-hoc read P25b (python probes/p25b_sc002_post_hoc_reads.py): SC002's development data, read again by the lead.
POSTHOC_READ_NOT_REGISTERED; written after SC002's development read (28 October 2026). No simulation: it reads the
development shards (each checked against the run's manifest by sha256) and P25's static map.

Block means as sc002.analyze makes them (each block's mean over its 8 cases), unrounded, at t = 4,000:
  c2_split     C2's two contrasts (mat-300 at mu 1e-3 minus mat-1000 at 2.5e-4) split into turnover's own part and the
               detector's. change4 r_in: turnover alone is the cue arm's (no detector) difference between the two rates.
               cue8 r_all: the same arms with no event (turnover eroding the record), then corruption's extra loss, and
               the cue arm's own extra loss. Per unit-body pair: the mean, its 95% t interval over the 16 blocks and the
               blocks above zero.
  extra_loss   the record lost to scattered cue corruption against the arm's own no-event run (none8 - cue8, r_all),
               beyond what the cue arm loses the same way; ranges over units and bodies, and its ratio to P25's static
               false-alarm share for that regime.
  beyond_cue   change4 and change8 r_in minus the cue arm's, against P25's static adoption shares.
  commitments  the share of sites committed with no event (none8 'opened', mean over the window), by rate and arm.
  regrowth     regrow+cue8 minus regrow8 inside the wound (r_in), by arm; and the maturing arms minus inst-3 in
               regrow+cue8.
Writes probes/results/p25b_sc002_post_hoc_reads.json.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from sc002 import design as D  # noqa: E402

RUN = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sc002/development")
ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
MAT = ("mat-300", "mat-1000")
H, L = "@0.001", "@0.00025"
MUS = ("@0", L, H)


def load():
    man = json.loads((RUN / "manifest.json").read_text())
    for t in man["tasks"].values():
        f = t["files"]["shards"]
        if hashlib.sha256((RUN / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            raise SystemExit(f"shard {f['path']} does not match the manifest")
    blocks = range(*json.loads((LANE / "results/sc002/summary_dw.json").read_text())["blocks"])
    data = {}
    for u, b in ALL:
        acc = {}
        for blk in blocks:
            with np.load(RUN / "shards" / b / u / f"{blk}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        acc.setdefault(k, []).append(z[k].mean(-1))
        data[(u, b)] = {k: np.stack(v) for k, v in acc.items()}
    return data, len(man["tasks"])


def main():
    data, ntasks = load()
    A = {a: i for i, a in enumerate(D.ARMS)}

    def bk(u, b, rn, arm, e="r_in"):
        x = data[(u, b)][f"{rn}/{e}"]
        return x[:, A[arm]] if e == "opened" else x[:, -1, A[arm]]

    def ci(v):
        h = float(stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / math.sqrt(len(v)))
        m = float(v.mean())
        return {"mean": round(m, 4), "lo95": round(m - h, 4), "hi95": round(m + h, 4), "blocks_pos": int((v > 0).sum()),
                "blocks": len(v)}

    def rng(v, d=4):
        v = [float(q) for q in v]
        return [round(min(v), d), round(max(v), d)]

    def extra(u, b, mu, a):
        return ((bk(u, b, "none8" + mu, a, "r_all") - bk(u, b, "cue8" + mu, a, "r_all"))
                - (bk(u, b, "none8" + mu, "cue", "r_all") - bk(u, b, "cue8" + mu, "cue", "r_all")))

    out = {"read": "P25b", "status": "POSTHOC_READ_NOT_REGISTERED", "tasks_checked": ntasks, "t": D.READS[-1]}
    c2 = {}
    for u, b in ALL:
        tot = bk(u, b, "change4" + H, "mat-300") - bk(u, b, "change4" + L, "mat-1000")
        tur = bk(u, b, "change4" + H, "cue") - bk(u, b, "change4" + L, "cue")
        ctot = bk(u, b, "cue8" + H, "mat-300", "r_all") - bk(u, b, "cue8" + L, "mat-1000", "r_all")
        cnone = bk(u, b, "none8" + H, "mat-300", "r_all") - bk(u, b, "none8" + L, "mat-1000", "r_all")
        ccue = ((bk(u, b, "cue8" + H, "cue", "r_all") - bk(u, b, "none8" + H, "cue", "r_all"))
                - (bk(u, b, "cue8" + L, "cue", "r_all") - bk(u, b, "none8" + L, "cue", "r_all")))
        c2[f"{u}/{b}"] = {"change4_total": ci(tot), "change4_turnover_alone": ci(tur), "change4_detector": ci(tot - tur),
                          "cue8_total": ci(ctot), "cue8_no_event": ci(cnone), "cue8_corruption_extra": ci(ctot - cnone),
                          "cue8_cue_arm_corruption_extra": ci(ccue), "cue8_detector_extra": ci(ctot - cnone - ccue)}
    out["c2_split"] = c2
    out["c2_split_means"] = {k: round(float(np.mean([c2[p][k]["mean"] for p in c2])), 4) for k in next(iter(c2.values()))}

    P = json.loads((LANE / "probes/results/p25_sc002_design_inputs.json").read_text())["static"]

    def static(mu, a):
        if a.startswith("inst-"):
            return P["uniform"][a.split("-")[1]]
        return P["regimes"][mu[1:] + "/" + a]["population"]

    el, bc = {}, {}
    for mu in MUS:
        for a in D.ARMS[1:]:
            if mu == "@0" and a in MAT:
                continue
            st = static(mu, a)
            ex = [float(extra(u, b, mu, a).mean()) for u, b in ALL]
            el[f"{a}{mu}"] = {"extra_loss": rng(ex), "static_false_alarms": round(st["false_alarms"], 4),
                              "ratio": rng([q / st["false_alarms"] for q in ex], 2) if st["false_alarms"] > 0.001 else None}
            bc[f"{a}{mu}"] = {s: {"run_beyond_cue": rng(float((bk(u, b, s + mu, a) - bk(u, b, s + mu, "cue")).mean())
                                                    for u, b in ALL), "static": round(st[s], 4)}
                              for s in ("change4", "change8")}
        el[f"cue{mu}"] = {"own_loss": rng(float((bk(u, b, "none8" + mu, "cue", "r_all")
                                                 - bk(u, b, "cue8" + mu, "cue", "r_all")).mean()) for u, b in ALL)}
    out["extra_loss"], out["beyond_cue"] = el, bc
    out["commitments"] = {mu: {a: [round(float(bk(u, b, "none8" + mu, a, "opened").mean()), 5) for u, b in ALL]
                               for a in D.ARMS} for mu in MUS}
    out["commitments_order"] = [f"{u}/{b}" for u, b in ALL]
    out["regrowth"] = {
        "corrupt_minus_clean_inside": {a: rng(float((bk(u, b, "regrow+cue8@0", a) - bk(u, b, "regrow8@0", a)).mean())
                                                for u, b in ALL) for a in D.ARMS},
        "corrupt_mat_minus_inst3_inside": {u: rng(float((bk(u, b, "regrow+cue8@0", m) - bk(u, b, "regrow+cue8@0", "inst-3")).mean())
                                                  for b in D.BODIES for m in MAT) for u in D.UNITS}}
    path = LANE / "probes" / "results" / "p25b_sc002_post_hoc_reads.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["c2_split_means"]))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
