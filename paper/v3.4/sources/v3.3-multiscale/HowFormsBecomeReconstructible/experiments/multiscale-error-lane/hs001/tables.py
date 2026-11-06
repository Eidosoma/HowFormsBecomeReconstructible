"""HS001's tables: python -m hs001.tables READ_DIR  ->  READ_DIR/TABLES.md from summary.json (percentage points)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from hs001 import design as D  # noqa: E402


def fmt(m, c):
    return f"{m:+.3f} [{c[0]:+.3f}, {c[1]:+.3f}]"


def main(read_dir):
    read_dir = Path(read_dir)
    S = json.loads((read_dir / "summary.json").read_text())
    C = S["checkpoints"]
    L = [f"# HS001 tables: {S['stage']} ({S['n_blocks']} blocks, digest {S['design_digest'][:12]})", "",
         f"Formation qualified: {100 * S['formation_qualified']:.2f}% of founders. Units: percentage points of E014's "
         "qualified agreement Q against the own founder; 95% whole-block intervals (E014's generator).", ""]
    for f in D.FACTORS:
        g = S[str(f)]
        r = g["reference"]
        L += [f"## {g['bytes']} bytes", "",
              f"- The reference Delta_P = Q(copy) - Q(copy_foreign): {fmt(r['mean'], r['ci95'])} (block SD "
              f"{r['block_sd']:.3f}; positive in {r['positive_blocks']} of {S['n_blocks']} blocks); "
              f"R_H reported as a ratio: {g['reference_resolved']}.",
              f"- Q(copy) {g['Q_copy']['mean']:.3f}, Q(copy_foreign) {g['Q_copy_foreign']['mean']:.3f}, "
              f"Q(copy_erased) {g['Q_copy_erased']['mean']:.3f}, Q(copy_background) {g['Q_copy_background']['mean']:.3f}.", "",
              "| Rewrites | Q(rewrite) | D = own - foreign | R_H | rewrite - erased | foreign - erased | deficit vs copy | "
              "concordance excess (rewrite) |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for k, n in enumerate(C):
            L.append(f"| {n} | {g['Q_rewrite']['mean'][k]:.3f} | {fmt(g['D']['mean'][k], g['D']['ci95'][k])} | "
                     f"{g['R_H']['ratio'][k]:.3f} [{g['R_H']['ci95'][k][0]:.3f}, {g['R_H']['ci95'][k][1]:.3f}] | "
                     f"{g['rewrite_minus_erased']['mean'][k]:+.3f} | {g['foreign_minus_erased']['mean'][k]:+.3f} | "
                     f"{g['deficit']['mean'][k]:+.3f} | {fmt(g['conc_rewrite']['mean'][k], g['conc_rewrite']['ci95'][k])} |")
        if "D16_minus_D1" in g:
            x = g["D16_minus_D1"]
            L += ["", f"- D(16) - D(1): {fmt(x['mean'], x['ci95'])}."]
        for key in ("fit_D", "fit_R_H"):
            if key in g:
                q = g[key]
                m1, m0, m2 = q["M1"], q["M0"], q["M2"]
                L += ["", f"**The asymptote ({'D' if key == 'fit_D' else 'R_H'}):** {q['reading']}.",
                      f"- M1: c {fmt(m1['c'], m1['c_ci95'])}, a {fmt(m1['a'], m1['a_ci95'])}, half-life {m1['h']:.2f} "
                      f"[{m1['h_ci95'][0]:.2f}, {m1['h_ci95'][1]:.2f}] rewrites (identified if the upper bound <= "
                      f"{D.IDENTIFIED_H_MAX:g}: {q['identified']}); remaining at 256 {fmt(m1['remaining_at_horizon'], m1['remaining_at_horizon_ci95'])}.",
                      f"- M0: a {fmt(m0['a'], m0['a_ci95'])}, half-life {m0['h']:.2f} [{m0['h_ci95'][0]:.2f}, {m0['h_ci95'][1]:.2f}]; "
                      f"SSE(M0) - SSE(M1) {fmt(q['sse_M0_minus_M1'], q['sse_M0_minus_M1_ci95'])}.",
                      f"- M2: c {fmt(m2['c'], m2['c_ci95'])}, h1 {m2['h1']:.2f}, h2 {m2['h2']:.2f}; SSE(M1) - SSE(M2) "
                      f"{fmt(q['sse_M1_minus_M2'], q['sse_M1_minus_M2_ci95'])}.",
                      f"- Model-free: late mean (128, 192, 256) {fmt(q['late_mean'], q['late_mean_ci95'])}; late slope "
                      f"D(256) - D(128) {fmt(q['late_slope'], q['late_slope_ci95'])}."]
        L.append("")
    (read_dir / "TABLES.md").write_text("\n".join(L) + "\n")
    print(f"-> {read_dir}/TABLES.md")


if __name__ == "__main__":
    main(sys.argv[1])
