"""Render TABLES.md from the reader's outputs: python -m lr001.tables --out OUT_DIR

Every number from summary.json (block means over cases; '-' where a case has no scored sites, such as region-minority
cells in F0 and S4).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr001 import design as D  # noqa: E402


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in body]
    return "\n".join(out)


def f3(x):
    return "-" if x is None else f"{x:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    summ = json.loads((a.out / "summary.json").read_text())
    verdicts = json.loads((a.out / "predictions_scored.json").read_text())
    L = summ["levels"]
    md = [f"# LR001 tables ({summ['stage']}, blocks {summ['blocks'][0]}–{summ['blocks'][1] - 1})", "",
          "Block means over cases ('-': no scored sites). Branches as in lr001/design.py.", "",
          "## Registered statements", "", table(["id", "verdict"], [[k, v["verdict"]] for k, v in verdicts.items()]), ""]
    body = [[u, f"{s:g}"] + [f3(L["A"][u][f"s{s:g}"][f"bond_accuracy@{t}"]) for t in D.A_READS] for u in D.A_UNITS for s in D.A_SIGMAS]
    md += ["## A. Bond accuracy after teaching updates", "", table(["family", "sigma", *[f"{t} updates" for t in D.A_READS]], body), ""]
    for u in D.E_UNITS:
        for ep in ("bond_err", "sign", "minority"):
            body = [[br] + [f3(L["E"][u][br][f"{ep}@{t}"]) for t in D.E_READS] for br in D.branches("E")]
            md += [f"## E. {u}: {ep}", "", table(["rate/repair", *[f"t = {t}" for t in D.E_READS]], body), ""]
    conds = [c.name for c in D.C_CONDS]
    for u in D.C_UNITS:
        for ep in ("kept@4000", "kept_min@4000", "kept_maj@4000"):
            body = [[code] + [f3(L["C"][u][f"{code}/{c}"][ep]) for c in conds if c != "sham"] for code in D.C_CODES]
            md += [f"## C. {u}: {ep}", "", table(["code", *[c for c in conds if c != "sham"]], body), ""]
        body = [[code] + [f3(L["C"][u][f"{code}/sham"][f"{ep}@4000"]) for ep in ("sign", "minority", "majority")] for code in D.C_CODES]
        md += [f"## C. {u}: undamaged record at t = 4000", "", table(["code", "sign", "minority", "majority"], body), ""]
    for u in D.T_UNITS:
        body = [[br] + [f3(L["T"][u][br][f"{ep}@8000"]) for ep in ("sign", "minority", "majority", "bond_err")]
                + [summ["turnovers_per_case"][u][br]] for br in D.branches("T")]
        md += [f"## T. {u}: t = 8000", "", table(["rate/mode", "sign", "minority", "majority", "bond_err", "turnovers per case"], body), ""]
    for u in D.L_UNITS:
        body = [[br] + [f3(L["L"][u][br][f"{ep}@{t}"]) for t in D.L_READS for ep in ("record_kept", "body_kept", "bond_err")]
                for br in D.branches("L")]
        head = ["learning"] + [f"{ep} @{t}" for t in D.L_READS for ep in ("record_kept", "body_kept", "bond_err")]
        md += [f"## L. {u}: inside the scar's patch", "", table(head, body), ""]
    (a.out / "TABLES.md").write_text("\n".join(md) + "\n")
    print(f"wrote {a.out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
