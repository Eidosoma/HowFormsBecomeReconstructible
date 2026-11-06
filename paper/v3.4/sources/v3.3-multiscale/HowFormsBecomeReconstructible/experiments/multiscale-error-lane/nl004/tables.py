"""NL004's tables: python -m nl004.tables --root RUN_ROOT --stage {smoke,probe,preflight,debug,development} [--out DIR]

Writes TABLES.md: the registered parts (value, 95% interval, SD_block, threshold, verdict); the reported comparison of
every anchor code at 0.75 x KC (protection under the foreign and corrupt references and its share of the given
anchors', the faithful copy's repair and its cost, its alignment, minority cells and regions, refused shares, and
the anchors' own shares); the gain sweep; the successors; the change and K arms; and the levels at the last read for
every branch in both units. Each level is the mean over the blocks of the block means (an undefined case left out).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from nl004 import analyze as AN, design as D  # noqa: E402
from nl004.predict import score  # noqa: E402

K = f"k{D.KSTAR:g}"


def lv(data, u, key, br, read=-1):
    names = data[u]["_names"][key[:2]]
    if br not in names:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return float(np.mean(np.nanmean(data[u][key][:, read, names.index(br), :], axis=1)))


def fmt(x, sign=True):
    return "–" if not np.isfinite(x) else (f"{x:+.3f}" if sign else f"{x:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("smoke", "probe", "preflight", "debug", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl004")
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage)
    data = AN.load(a.root.resolve(), blocks)
    S = score(data)
    out = [f"# NL004 tables ({a.stage}, blocks {blocks[0]}-{blocks[-1]}, {len(blocks)} blocks; rule {D.RULE})", "",
           "## Registered parts", "", "| Statement | Part | Value [95%] | SD_block | Rule | Verdict |", "|---|---|---|---|---|---|"]
    for sid, node in S.items():
        for name, p in node["parts"].items():
            th = "unset" if p["threshold"] is None else f"{p['sense']} {p['threshold']:+}"
            out.append(f"| {sid} | {name} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {p['sd']:.4f} | {th} | {node['verdict']} |")
    codes = [""] + [c for c in D.CODES if c != "Me"]
    for u in D.UNITS:
        f = lambda key, br: lv(data, u, key, br)
        pA = f("t/r/spec_reg", f"foreign-{K}+A/none") - f("t/r/spec_reg", f"foreign-{K}/none")
        out += ["", f"## The anchor codes at 0.75 x KC, unit {u}", "",
                "| Anchors | spec foreign | protection (share of A's) | spec corrupt | repair (copy, R) | repair cost | "
                "align (copy) | min cells | min regions | refused: copy, foreign (differing / other) | anchors at A's sign: "
                "all, minority cells, R regions |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in codes:
            sfx = f"+{c}" if c else ""
            sf, sf0 = f("t/r/spec_reg", f"foreign-{K}{sfx}/none"), f("t/r/spec_reg", f"foreign-{K}/none")
            ev, ev0 = f("t/r/ev_reg_ok", f"copy-{K}{sfx}/R"), f("t/r/ev_reg_ok", f"copy-{K}/R")
            prot = sf - sf0
            share = prot / pA if c and abs(pA) > 1e-12 else float("nan")
            ref = "" if not c else (f"{fmt(f('t/a/ref_all', f'copy-{K}{sfx}/none'), False)}, "
                                    f"{fmt(f('t/a/ref_dreg', f'foreign-{K}{sfx}/none'), False)} / "
                                    f"{fmt(f('t/a/ref_other', f'foreign-{K}{sfx}/none'), False)}")
            anc = "" if not c else (f"{fmt(f('t/a/anc_A', f'copy-{K}{sfx}/none'), False)}, "
                                    f"{fmt(f('t/a/anc_A_min', f'copy-{K}{sfx}/none'), False)}, "
                                    f"{fmt(f('t/a/anc_A_ev', f'copy-{K}{sfx}/R'), False)}")
            out.append(f"| {c or 'off'} | {fmt(sf)} | {fmt(prot) if c else ''}{'' if not c else f' ({share:.2f})'} | "
                       f"{fmt(f('t/r/spec_reg', f'corrupt-{K}{sfx}/none'))} | {fmt(ev, False)} | {fmt(ev - ev0) if c else ''} | "
                       f"{fmt(f('t/r/align_A', f'copy-{K}{sfx}/none'), False)} | {fmt(f('t/r/min_cell_ok_A', f'copy-{K}{sfx}/none'), False)} | "
                       f"{fmt(f('t/r/min_reg_ok_A', f'copy-{K}{sfx}/none'), False)} | {ref} | {anc} |")
        out.append(f"| Me (R only) | | | | {fmt(f('t/r/ev_reg_ok', f'copy-{K}+Me/R'), False)} | "
                   f"{fmt(f('t/r/ev_reg_ok', f'copy-{K}+Me/R') - f('t/r/ev_reg_ok', f'copy-{K}/R'))} | | | | | "
                   f"R regions {fmt(f('t/a/anc_A_ev', f'copy-{K}+Me/R'), False)} |")
        out += ["", f"## The gain sweep, unit {u} (spec foreign, repair, spec corrupt)", "",
                "| k2 | off | A | Mv | S1e-3 |", "|---|---|---|---|---|"]
        for g in D.GAINS:
            row = []
            for c in D.SWEEP:
                sfx = f"+{c}" if c else ""
                row.append(f"{fmt(f('t/r/spec_reg', f'foreign-k{g:g}{sfx}/none'))}, {fmt(f('t/r/ev_reg_ok', f'copy-k{g:g}{sfx}/R'), False)}, "
                           f"{fmt(f('t/r/spec_reg', f'corrupt-k{g:g}{sfx}/none'))}")
            out.append(f"| {g:g} | " + " | ".join(row) + " |")
        out += ["", f"## The successors after the foreign and copy references, unit {u}", "",
                "| Parent | s/spec | c/spec | g/spec (parent's given anchors) | m/spec (successor-made) | m/ anchors at A's sign "
                "(differing regions) | m/ refused ever |", "|---|---|---|---|---|---|---|"]
        for br in data[u]["_names"]["m/"]:
            g = fmt(lv(data, u, "g/spec_reg", br)) if br in data[u]["_names"]["g/"] else ""
            out.append(f"| {br} | {fmt(lv(data, u, 's/spec_reg', br))} | {fmt(lv(data, u, 'c/spec_reg', br))} | {g} | "
                       f"{fmt(lv(data, u, 'm/spec_reg', br))} | {fmt(lv(data, u, 'm/anc_A_dreg', br), False)} | "
                       f"{fmt(lv(data, u, 'm/ever', br), False)} |")
        out += ["", f"## change and K, unit {u}", "", "| Branch | spec | k_spec | anchors at B's sign: differing regions, "
                "the square's differing regions | refused (all) |", "|---|---|---|---|---|"]
        for br in data[u]["_names"]["t/"]:
            if br.endswith("/change") or (br.endswith("/K") and K in br):
                out.append(f"| {br} | {fmt(f('t/r/spec_reg', br))} | {fmt(f('t/r/k_spec_reg', br))} | "
                           f"{fmt(f('t/a/anc_B_dreg', br), False)}, {fmt(f('t/a/anc_B_kd', br), False)} | "
                           f"{fmt(f('t/a/ref_all', br), False)} |")
        out += ["", f"## Levels at the last read, unit {u}", "",
                "| Branch | ev | spec | k_spec | align_A | min_cell | min_reg | refused (all, differing, other) | anchors present, A, B |",
                "|---|---|---|---|---|---|---|---|---|"]
        for br in data[u]["_names"]["t/"]:
            ff = lambda key, b=br: lv(data, u, key, b)
            ref = "" if "+" not in br else f"{ff('t/a/ref_all'):.3f}, {ff('t/a/ref_dreg'):.3f}, {ff('t/a/ref_other'):.3f}"
            anc = "" if "+" not in br else f"{ff('t/a/anc_present'):.3f}, {ff('t/a/anc_A'):.3f}, {ff('t/a/anc_B'):.3f}"
            out.append(f"| {br} | {ff('t/r/ev_reg_ok'):.3f} | {ff('t/r/spec_reg'):+.3f} | {fmt(ff('t/r/k_spec_reg'))} | "
                       f"{ff('t/r/align_A'):.3f} | {ff('t/r/min_cell_ok_A'):.3f} | {ff('t/r/min_reg_ok_A'):.3f} | {ref} | {anc} |")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "TABLES.md").write_text("\n".join(out) + "\n")
    print("wrote", a.out / "TABLES.md")


if __name__ == "__main__":
    main()
