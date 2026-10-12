#!/usr/bin/env python3
"""Present TT014's retained repair results and frozen algorithm boundary.

No scientific code is imported, no optimizer or dynamics are run, and no new
uncertainty is estimated. The aggregate interval is the original stratified
Welch–Satterthwaite interval; all 64 block differences are displayed.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = "experiments/theory-tests-lane/TT014/"
RUN = BASE + "runs/validation_v1/"
INSPECTION = ROOT / "reviews/V0.20_TT014_SOURCES.json"
ARCHIVE = ROOT / "paper_assets/data/tt014-repair-v0.20-source-records.zip"
DATA = ROOT / "paper_assets/data/tt014-repair-v0.20.json"
CSV = ROOT / "paper_assets/data/tt014-blocks-v0.20.csv"
ASSETS = ROOT / "paper_assets/figures/tt014-repair-assets-v0.20.json"
STEM = ROOT / "paper_assets/figures/data-tt014-repair-v0.20"
VARIANTS = ("outgoing", "recipient_completion", "recipient_shuffled", "erased")
HISTORY_LABELS = ("Exact\nrewrite", "Single\npulse", "Spaced\npulses", "Clustered\npulses")
INK, TEAL, AMBER, MUTED = "#123449", "#007E88", "#C98019", "#647684"
HISTORY_COLORS = ("#247BB0", TEAL, "#8764A0", AMBER)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialized(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def extract():
    manifest = json.loads(INSPECTION.read_text())
    assert sha(ARCHIVE) == manifest["archive_sha256"]
    with zipfile.ZipFile(ARCHIVE) as z:
        for source in manifest["sources"]:
            assert hashlib.sha256(z.read(source["member"])).hexdigest() == source["sha256"]
        read = lambda p: json.loads(z.read(p))
        registration = read(BASE + "REGISTRATION.json")
        complete = read(RUN + "COMPLETE.json")
        closeout = read(BASE + "CLOSEOUT.json")
        assert hashlib.sha256(z.read(RUN + "COMPLETE.json")).hexdigest() == closeout["completion_sha256"]
        for name in ("optimizer.py", "repair.py", "native.py", "optimizer_audit.py", "support.py", "plan.json"):
            assert hashlib.sha256(z.read(BASE + name)).hexdigest() == registration["design_inputs_sha256"][name]
        for name in ("analysis.json", "block_summaries.csv", "block_contrast_counts.json"):
            assert hashlib.sha256(z.read(RUN + name)).hexdigest() == complete["outputs_sha256"][name]
        analysis = read(RUN + "analysis.json")
        plan = read(BASE + "plan.json")
        counts = read(RUN + "block_contrast_counts.json")
        rows = list(csv.DictReader(io.StringIO(z.read(RUN + "block_summaries.csv").decode())))

    assert len(rows) == 64 * 4
    indexed = {(int(r["block"]), r["variant"]): r for r in rows}
    assert len(indexed) == len(rows)
    blocks = sorted({b for b, _ in indexed})
    assert blocks == plan["blocks"] == list(range(14000000, 14000064))
    primary = analysis["primary_effects"]["recipient_minus_outgoing"]
    block_rows = []
    for block in blocks:
        history = plan["history_by_block"][str(block)]
        successes = {}
        for variant in VARIANTS:
            row = indexed[block, variant]
            assert int(row["history"]) == history
            assert int(row["reads"]) == 16 * 8
            successes[variant] = int(row["intended"])
        difference = successes["recipient_completion"] - successes["outgoing"]
        assert difference / 128 == primary["by_block"][str(block)]
        block_rows.append(dict(block=block, history=history,
                               history_name=plan["histories"][history],
                               assessments_per_condition=128, **successes,
                               repaired_minus_untreated_count=difference,
                               repaired_minus_untreated_pp=100 * difference / 128))
    rates = {}
    for variant in VARIANTS:
        rate = analysis["rate_summaries"][variant]["intended"]
        assert sum(r[variant] for r in block_rows) == rate["successes"]
        assert rate["reads"] == 8192
        assert rate["successes"] / rate["reads"] == rate["mean"]
        rates[variant] = {k: rate[k] for k in ("successes", "reads", "mean")}
    paired = analysis["paired_counts"]["recipient_minus_outgoing"]
    assert paired == closeout["paired_counts"]["recipient_minus_outgoing"]
    assert paired["both"] + paired["left_only"] == rates["recipient_completion"]["successes"]
    assert paired["both"] + paired["right_only"] == rates["outgoing"]["successes"]
    assert sum(paired[k] for k in ("both", "left_only", "right_only", "neither")) == paired["reads"]
    assert (paired["left_only"] - paired["right_only"]) / paired["reads"] == primary["mean"]
    for h in range(4):
        observed = [r["repaired_minus_untreated_count"] for r in block_rows if r["history"] == h]
        assert observed == counts["recipient_minus_outgoing"][h]
    directions = {"positive": sum(r["repaired_minus_untreated_count"] > 0 for r in block_rows),
                  "ties": sum(r["repaired_minus_untreated_count"] == 0 for r in block_rows),
                  "negative": sum(r["repaired_minus_untreated_count"] < 0 for r in block_rows)}
    assert list(directions.values()) == [primary["positive_blocks"], primary["tied_blocks"], primary["negative_blocks"]]
    data = dict(study="TT014", evidence_note="E78", cohort_records=1024,
                independent_blocks=64, records_per_block=16,
                assessments_per_record=8, endpoint="One fresh injured reconstruction; both supplied cues pass.",
                rates=rates, paired_assessments=paired, block_directions=directions,
                primary_gain_pp=100 * primary["mean"],
                primary_two_sided95_pp=[100 * v for v in primary["two_sided95"]],
                uncertainty_method=primary["method"],
                interval_origin="Original saved interval, not recomputed for presentation.",
                blocks=block_rows, simulations_run=False, new_inference=False)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(block_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(block_rows)
    return data, buffer.getvalue()


def panel(ax, label, title):
    ax.text(0, 1.10, label, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=20, fontweight="bold", color=TEAL)
    ax.text(.075, 1.10, title, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=18, fontweight="bold", color=INK)


def plot(data):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15,
                         "text.color": INK, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#AABAC2", "svg.hashsalt": "TT014-v020"})
    fig = plt.figure(figsize=(12.6, 9.6), facecolor="white")
    fig.suptitle("Surviving record structure can guide repair", x=.5, y=.985,
                 fontsize=24, fontweight="bold", color=INK)
    fig.text(.5, .923, "TT014  ·  1,024 records enrolled without a success filter  ·  64 fresh blocks",
             ha="center", fontsize=15, color=MUTED)
    grid = fig.add_gridspec(2, 2, left=.082, right=.974, bottom=.105, top=.835,
                           width_ratios=[1, 1.08], height_ratios=[1, 1],
                           hspace=.64, wspace=.38)
    a, b, c, d = [fig.add_subplot(grid[i, j]) for i, j in ((0, 0), (0, 1), (1, 0), (1, 1))]

    # A is explicitly schematic: no individual record or generated field is shown.
    panel(a, "A", "What the supplied repair does")
    a.set(xlim=(0, 1), ylim=(0, 1)); a.axis("off")
    labels = ["Surviving learned record",
              "Fit cell signs to surviving connections",
              "Fill zeros; preserve surviving weights",
              "Fresh body reads the repaired record"]
    for i, label in enumerate(labels):
        y = .85 - i * .215
        patch = FancyBboxPatch((.01, y - .066), .98, .133,
                               boxstyle="round,pad=0.009,rounding_size=0.014",
                               linewidth=1.2, edgecolor="#91B7C0",
                               facecolor="#EAF5F6" if i in (1, 2) else "#F3F6F8")
        a.add_patch(patch)
        a.text(.5, y, label, ha="center", va="center", fontsize=15.3)
        if i < 3:
            a.annotate("", xy=(.5, y - .138), xytext=(.5, y - .071),
                       arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.7))
    a.text(.5, -.025, "Fixed input pins, lattice, solver and reader.\nNo old backup or desired output label at repair.",
           ha="center", va="top", fontsize=13.5, color=MUTED)

    panel(b, "B", "One fresh reconstruction")
    colors = [MUTED, TEAL, AMBER, "#B9C3C8"]
    for i, variant in enumerate(VARIANTS):
        rate = data["rates"][variant]
        height = 100 * rate["mean"]
        b.bar(i, height, width=.63, color=colors[i], zorder=3)
        b.text(i, height + 2.5, f"{height:.2f}%", ha="center", fontsize=15.5,
               fontweight="bold", color=colors[i] if i < 3 else MUTED)
        b.text(i, height + 10, f"{rate['successes']:,}", ha="center", fontsize=13.5, color=MUTED)
    b.set(ylim=(0, 110), xlim=(-.58, 3.58), ylabel="Successful assessments (%)")
    b.set_xticks(range(4), ["Unmodified", "Repaired", "Shuffled\nadded signs", "Erased"], fontsize=13)
    b.set_yticks(range(0, 101, 25))
    b.grid(axis="y", color="#E6EBEF", zorder=0)
    b.tick_params(axis="x", length=0)
    b.text(.5, -.27, "Counts above bars; 8,192 assessments per condition.",
           ha="center", transform=b.transAxes, fontsize=12.5, color=MUTED)

    panel(c, "C", "Paired rescues and losses")
    c.set(xlim=(0, 2), ylim=(0, 2))
    values = [(0, 1, data["paired_assessments"]["left_only"], "Repair only", "#D9F0EE", TEAL),
              (1, 1, data["paired_assessments"]["both"], "Both succeed", "#EBF4F6", INK),
              (0, 0, data["paired_assessments"]["neither"], "Neither succeeds", "#F0F3F5", MUTED),
              (1, 0, data["paired_assessments"]["right_only"], "Unmodified only", "#FFF0DC", "#A9650D")]
    for x, y, number, label, bg, fg in values:
        c.add_patch(Rectangle((x + .025, y + .025), .95, .95, facecolor=bg, edgecolor="white"))
        c.text(x + .5, y + .59, f"{number:,}", ha="center", va="center",
               fontsize=24, fontweight="bold", color=fg)
        c.text(x + .5, y + .30, label, ha="center", va="center", fontsize=13, color=fg)
    c.set_xticks([.5, 1.5], ["Fail", "Pass"], fontsize=15)
    c.set_yticks([.5, 1.5], ["Fail", "Pass"], fontsize=15)
    c.set_xlabel("Unmodified record", labelpad=7)
    c.set_ylabel("Repaired record", labelpad=8)
    c.tick_params(length=0)
    for spine in c.spines.values(): spine.set_visible(False)

    panel(d, "D", "Consistency across blocks")
    mean, ci = data["primary_gain_pp"], data["primary_two_sided95_pp"]
    d.axhspan(*ci, color="#E0EBEF", alpha=.8, zorder=0)
    d.axhline(mean, color=INK, lw=1.25, zorder=1)
    d.axhline(0, color=MUTED, lw=1, linestyle="--", zorder=1)
    for h, color in enumerate(HISTORY_COLORS):
        subset = [r for r in data["blocks"] if r["history"] == h]
        # Fixed within-history block order gives every block a distinct x position.
        x = h + np.linspace(-.27, .27, 16)
        d.scatter(x, [r["repaired_minus_untreated_pp"] for r in subset],
                  s=43, color=color, edgecolors="white", linewidths=.5, zorder=4)
    d.set(ylim=(-5, 27.5), xlim=(-.55, 3.55), ylabel="Repaired − unmodified (pp)")
    d.set_xticks(range(4), HISTORY_LABELS, fontsize=13)
    d.set_yticks([-5, 0, 5, 10, 15, 20, 25])
    d.tick_params(axis="x", length=0)
    d.grid(axis="y", color="#E6EBEF", zorder=0)
    d.text(.5, 1.025, "61 improve  ·  2 tie  ·  1 worsens", transform=d.transAxes,
           ha="center", fontsize=14, color=MUTED)
    fig.text(.745, .031, f"Overall gain: +{mean:.2f} pp  [95% CI {ci[0]:.2f}, {ci[1]:.2f}]",
             ha="center", fontsize=15, fontweight="bold", color=INK)
    fig.text(.272, .031, "536 rescued  ·  50 lost  ·  8,192 paired assessments",
             ha="center", fontsize=13.5, color=MUTED)

    fig.savefig(STEM.with_name(STEM.name + ".png"), dpi=300, facecolor="white")
    fig.savefig(STEM.with_name(STEM.name + ".svg"), facecolor="white", metadata={"Date": None})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify extraction and saved assets without rewriting them.")
    args = parser.parse_args()
    data, table = extract()
    if args.check:
        assert DATA.read_text() == serialized(data)
        assert CSV.read_text() == table
        assets = json.loads(ASSETS.read_text())
        for name in ("data", "csv", "archive", "source_inspection", "plot_script"):
            assert sha(ROOT / assets[name]) == assets[name + "_sha256"]
        for entry in assets["outputs"]:
            assert sha(ROOT / entry["path"]) == entry["sha256"]
        print("PASS: registered implementation, completion-bound counts, all 64 blocks, paired identities and figure hashes.")
        return
    DATA.write_text(serialized(data))
    CSV.write_text(table)
    plot(data)
    manifest = dict(figure_id="fig-tt014-repair", kind="measured-with-schematic",
                    png=STEM.with_name(STEM.name + ".png").name, new_simulations=False,
                    new_inference=False, primary_qualification_unchanged=True,
                    inferential_unit="64 independent blocks; 8,192 assessments are nested repeats.",
                    panel_a="Protocol schematic, not a saved field or reconstruction history.",
                    panel_d="All blocks; deterministic x-offsets in block order; saved overall two-sided interval.")
    for name, path in (("data", DATA), ("csv", CSV), ("archive", ARCHIVE),
                       ("source_inspection", INSPECTION), ("plot_script", Path(__file__).resolve())):
        manifest[name] = str(path.relative_to(ROOT))
        manifest[name + "_sha256"] = sha(path)
    manifest["outputs"] = [dict(path=str(STEM.with_name(STEM.name + ext).relative_to(ROOT)), sha256=sha(STEM.with_name(STEM.name + ext)))
                           for ext in (".png", ".svg")]
    ASSETS.write_text(serialized(manifest))
    print("Rendered TT014 from retained evidence: +5.93 pp, 536 rescues / 50 losses, 61/2/1 blocks.")


if __name__ == "__main__":
    main()
