"""HS002's tables: python -m hs002.tables READ_DIR  ->  READ_DIR/TABLES.md (percentage points of E014's Q)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from hs002 import design as D  # noqa: E402


def fmt(m, c):
    return f"{m:+.3f} [{c[0]:+.3f}, {c[1]:+.3f}]"


def fit_lines(name, q):
    m1, m0, m2 = q["M1"], q["M0"], q["M2"]
    why = f" ({'; '.join(q.get('reasons', []))})" if q.get("reasons") else ""
    dwhy = f" ({'; '.join(q.get('reasons_declared', []))})" if q.get("reasons_declared") else ""
    out = [f"**{name}: {q['reading']}{why}.** The drift bound: {q.get('drift_bound_text', '-')}. By the rule as first declared: "
           f"{q['reading_declared']}{dwhy}.",
           f"- M1: c {fmt(m1['c'], m1['c_ci95'])}, a {fmt(m1['a'], m1['a_ci95'])}, half-life {m1['h']:.2f} "
           f"[{m1['h_ci95'][0]:.2f}, {m1['h_ci95'][1]:.2f}] (identified if the upper bound <= {D.IDENTIFIED_H_MAX:g}: {q['identified']}); "
           f"remaining at 1,024 {fmt(m1['remaining_at_horizon'], m1['remaining_at_horizon_ci95'])}.",
           f"- M2: c {fmt(m2['c'], m2['c_ci95'])}, h1 {m2['h1']:.2f}, h2 {m2['h2']:.2f} [{m2['h2_ci95'][0]:.2f}, {m2['h2_ci95'][1]:.2f}]; "
           f"SSE(M1) - SSE(M2) {fmt(q['sse_M1_minus_M2'], q['sse_M1_minus_M2_ci95'])}.",
           f"- M0: half-life {m0['h']:.2f} [{m0['h_ci95'][0]:.2f}, {m0['h_ci95'][1]:.2f}]; SSE(M0) - SSE(M1) "
           f"{fmt(q['sse_M0_minus_M1'], q['sse_M0_minus_M1_ci95'])}."]
    if "d1024_minus_d512" in q:
        out.append(f"- Model-free: D(1024) - D(512) {fmt(q['d1024_minus_d512'], q['d1024_minus_d512_ci95'])}; D(1024) - D(256) "
                   f"{fmt(q['d1024_minus_d256'], q['d1024_minus_d256_ci95'])}; late mean (768, 896, 1,024) "
                   f"{fmt(q['late_mean'], q['late_mean_ci95'])}.")
    return out


def main(read_dir):
    read_dir = Path(read_dir)
    S = json.loads((read_dir / "summary.json").read_text())
    C = S["checkpoints"]
    L = [f"# HS002 tables: {S['stage']} ({S['n_blocks']} blocks, digest {S['design_digest'][:12]})", "",
         f"HS001's rewrites 1-256 joined with HS002's continuation to 1,024. Formation qualified: "
         f"{100 * S['formation_qualified']:.2f}% of founders. 95% whole-block intervals (E014's generator).", ""]
    for f in S["factors"]:
        g = S[str(f)]
        r = g["reference"]
        L += [f"## {g['bytes']} bytes", "", f"- The reference (HS001's, constant): {fmt(r['mean'], r['ci95'])}; R_H as a ratio: "
              f"{g['reference_resolved']}. Basins: **{g['basins']}**.", "",
              "| Rewrites | D = own - foreign | R_H | rewrite - erased | deficit vs copy | concordance excess: rewrite / foreign / erased / background |",
              "| --- | --- | --- | --- | --- | --- |"]
        for k, n in enumerate(C):
            if n < 16 and n not in (1, 4, 8):
                continue
            L.append(f"| {n} | {fmt(g['D']['mean'][k], g['D']['ci95'][k])} | {g['R_H']['ratio'][k]:.3f} "
                     f"[{g['R_H']['ci95'][k][0]:.3f}, {g['R_H']['ci95'][k][1]:.3f}] | {g['rewrite_minus_erased']['mean'][k]:+.3f} | "
                     f"{g['deficit']['mean'][k]:+.3f} | " + " / ".join(f"{g['conc_' + a]['mean'][k]:+.2f}" for a in D.LINEAGE) + " |")
        L.append("")
        for key, name in (("fit_D", "The reading (D)"), ("fit_R_H", "R_H"), ("fit_floor", "The floor rewrite - erased")):
            if key in g:
                L += fit_lines(name, g[key]) + [""]
    (read_dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {read_dir}/TABLES.md")


if __name__ == "__main__":
    main(sys.argv[1])
