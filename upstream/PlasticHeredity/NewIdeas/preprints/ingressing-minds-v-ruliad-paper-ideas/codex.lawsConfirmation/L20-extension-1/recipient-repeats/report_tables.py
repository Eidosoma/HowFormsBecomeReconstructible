"""Render D181's frozen results as Markdown; read-only, no audit inspection."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from l20_extension1 import recipient_repeats_population_run as run

PIN = "5b171e325d9c9703f58cc937a5a1877bc38e9f11e9032cf3b0823dd2baa4f0b3"
PARTS = ("record", "recipient", "interaction", "total")


def number(value, points=False):
    if value is None:
        return "undefined"
    return f"{100*value:.4f}" if points else f"{value:.9g}"


def group_name(group):
    return "/".join((group["assay"], "AB"[group["family"]], group["condition"])) + ("*" if group["focal"] else "")


def render():
    def forbidden(*args, **kwargs):
        raise AssertionError("reporting must not simulate, refit or rebuild production summaries")
    run.model.simulate_life = run.check.physics.step = run.analysis.summarize = forbidden
    assert run.sha256_file(run.run_dir()/"COMPLETE.json") == PIN
    frozen = run.frozen()
    done = run.files.read_json(run.run_dir()/"COMPLETE.json")
    assert done["freeze_sha256"] == run.sha256_file(run.freeze_path())
    run.verify(done["output_sha256"])
    records = run.files.read_json(run.output_dir()/"records.json")
    report = run.files.read_json(run.output_dir()/"summary.json")
    proof = run.stats_check.check_report(report, records)
    run.check.prior.nested(proof, done["verification"]["saved_statistics"])
    old = run.previous.previous
    old_done = run.files.read_json(old.run_dir()/"COMPLETE.json")
    old_path = old.output_dir()/"summary.json"
    assert frozen["inputs"][str(old_path)] == old_done["output_sha256"][str(old_path)]
    assert run.sha256_file(old_path) == old_done["output_sha256"][str(old_path)]
    history = run.files.read_json(old_path)
    old_groups = {(g["assay"], g["family"], g["condition"]): g for g in history["groups"]}
    lines = ["# D181 Tables for the four future recurrence test", "",
        "2026-10-10. Completed population results. [Interpretation and formal audit",
        "closeout](POPULATION_RESULTS.md) and",
        "[fixed protocol](PROTOCOL_V1.md). These tables are read-only views of the",
        "frozen results, with no new trajectories, predictors or tuned comparisons.", "",
        "All four reused founder blocks and all 32 F0 records remain. Each family",
        "has 16 records, three settings and four fresh futures, or 192 labelled",
        "paths per writer/control condition. Common-reader B ordinary is focal (*).",
        "Native-reader and aligned-writing results do not replace it.", "",
        "Preference points are 100 times own-minus-alternative preference, not success",
        "percentages. Negative preferences favor the alternative. All means equally",
        "weight the fixed donors, lives and futures. Signed components use original",
        "squared-score units, not points or variance percentages; negatives remain.", "",
        "Pair products share futures and are not independent replications. Neither",
        "donor/future omission ranges nor ranking counts are confidence intervals.", "",
        "All 1,152 absolute control cells, 960 paired contrasts and 4,608 per-assay",
        "records remain in the immutable external JSON. Tables below aggregate controls",
        "equally over donors/futures for readability, while retaining every condition.", ""]
    sections = []
    def table(title, header, rows):
        rows = list(rows)
        assert rows and all(len(row) == len(header) for row in rows)
        sections.append(dict(title=title, rows=len(rows)))
        lines.extend(["## " + title, "", "| " + " | ".join(header) + " |",
                      "| " + " | ".join("---" for _ in header) + " |"])
        for row in rows:
            lines.append("| " + " | ".join(str(value) for value in row) + " |")
        lines.append("")
    def selected(assay, family, kind):
        return [r for r in records if (r["assay"], r["family"], r["condition"]) == (assay, family, kind)]
    def mean(rows, field):
        assert rows
        return float(np.mean([row[field] for row in rows]))
    absolute, diagnostics = [], []
    for assay in run.analysis.ASSAYS:
        for family in (0, 1):
            for kind in run.model.CONDITIONS:
                rows = selected(assay, family, kind)
                assert len(rows) == 192
                absolute.append([assay, "AB"[family], kind] + [
                    number(mean([x for x in rows if x["coupling"] == g], "preference"), True)
                    for g in run.model.COUPLINGS] + [number(mean(rows, "preference"), True)])
                diagnostics.append([assay, "AB"[family], kind, number(mean(rows, "body_rms")),
                    number(mean(rows, "clip_fraction"), True), number(max(x["clip_fraction"] for x in rows), True)])
    table("Absolute preference including every control", ["Assay", "Family", "Condition", "g 0.75", "g 1.0", "g 1.25", "Pooled"], absolute)
    contrasts = []
    for assay in run.analysis.ASSAYS:
        for family in (0, 1):
            for first, second in run.analysis.CONTRASTS:
                rows = [r for r in report["control_contrasts"] if
                        (r["assay"], r["family"], r["first"], r["second"]) == (assay, family, first, second)]
                assert len(rows) == 48
                contrasts.append([assay, "AB"[family], first + " minus " + second] + [
                    number(mean([x for x in rows if x["coupling"] == g], "first_minus_second"), True)
                    for g in run.model.COUPLINGS] + [number(mean(rows, "first_minus_second"), True)])
    table("All five fixed contrasts in preference points", ["Assay", "Family", "Contrast", "g 0.75", "g 1.0", "g 1.25", "Pooled"], contrasts)
    table("Signed components averaged over six fresh pairs", ["Group"] + list(PARTS),
          ([group_name(g)] + [number(g["cross_replica"][k]) for k in PARTS] for g in report["groups"]))
    compare, pairs, futures, ranks, pair_ranks = [], [], [], [], []
    for g in report["groups"]:
        name = group_name(g)
        old_g = old_groups[g["assay"], g["family"], g["condition"]]
        indexed = {(p["first"], p["second"]): p for p in g["pair_components"]}
        compare.append([name, number(old_g["cross_replica"]["interaction"])] + [
            number(indexed[p]["components"]["interaction"]) for p in ((2, 3), (4, 5))] +
            [number(g["cross_replica"]["interaction"])])
        for p in g["pair_components"]:
            pairs.append([name, f"{p['first']},{p['second']}"] + [number(p["components"][k]) for k in PARTS])
        for replica, value, part in zip(g["replicas"], g["replica_means"], g["replica_partitions"]):
            futures.append([name, replica, number(value, True)] + [number(part[k]) for k in PARTS])
        def rank_values(row):
            return [f"{row['first']} vs {row['second']}", number(row["spearman"]),
                    row["reversed"], row["unchanged"], row["tied"], row["replication_consistent_reversals"]]
        ranks.extend([name] + rank_values(row) for row in g["rankings"])
        pair_ranks.extend([name, ",".join(map(str, pair["replicas"]))] + rank_values(row)
                          for pair in g["paired_rankings"] for row in pair["comparisons"])
    table("Historical and fixed fresh pair interaction estimates", ["Group", "Old 0,1", "Fresh 2,3", "Fresh 4,5", "Fresh six pair mean"], compare)
    lines.extend(["The old pair is shown for context only and is not pooled into fresh estimates.", ""])
    table("Every fresh pair signed product", ["Group", "Futures"] + list(PARTS), pairs)
    table("Separate future means and nonnegative partitions", ["Group", "Future", "Mean points"] + list(PARTS), futures)
    table("Four future mean rankings", ["Group", "Settings", "Spearman", "Reversed", "Unchanged", "Tied", "All four consistent"], ranks)
    lines.extend(["Each row concerns 120 overlapping record pairs, not independent trials. The",
                  "all-four rule is stricter than D180's two-future rule, so raw counts do not",
                  "measure improvement over D180. Interaction need not reverse rankings.", ""])
    table("Fixed two future rankings", ["Group", "Futures", "Settings", "Spearman", "Reversed", "Unchanged", "Tied", "Both consistent"], pair_ranks)
    shape, addresses = [], []
    for family in (0, 1):
        for kind in run.model.CONDITIONS:
            rows = selected("common", family, kind)
            native = selected("native", family, kind)
            for a, b in zip(rows, native):
                for key in ("f0_own_correlation", "f3_own_correlation", "guide_family", "guide_shift"):
                    assert a[key] == b[key]
            shape.append(["AB"[family], kind] + [number(mean(rows, k)) for k in (
                "f0_own_correlation", "f3_own_correlation", "f0_own_minus_alternative", "f3_own_minus_alternative")] +
                [f"{sum(x['guide_family'] == family for x in rows)}/192"])
            counts = Counter((x["guide_family"], *x["guide_shift"]) for x in rows)
            for (label, dy, dx), count in sorted(counts.items()):
                addresses.append(["AB"[family], kind, "unassigned" if label == -1 else "AB"[label], f"{dy},{dx}", count])
    table("Shape and guide recognition pooled over settings", ["Family", "Condition", "F0 own corr", "F3 own corr", "F0 own alt corr", "F3 own alt corr", "Guide correct"], shape)
    lines.extend(["Shape and guide labels/addresses are aliases across the common/native assays",
                  "of each packet, so shown once. These are 192 labelled paths, not founders.",
                  "Write-off uses the fixed zero-correlation and unassigned-label convention.", ""])
    table("Every terminal guide label and address", ["Target", "Condition", "Guide label", "Forward shift", "Paths"], addresses)
    table("Terminal body diagnostics", ["Assay", "Family", "Condition", "Mean RMS", "Mean clipped sites percent", "Maximum clipped sites percent"], diagnostics)
    lines.extend(["These are terminal-only diagnostics; they do not establish absence of clipping",
                  "in intermediate states. Forward shifts are the guide-selected (row,column) addresses.", ""])
    for title, field, address in (("Every donor description", "donor_blocks", "index"),
                                 ("Every donor omission", "leave_one_block_out", "omitted"),
                                 ("Every future omission", "leave_one_future_out", "omitted")):
        table(title, ["Group", address, "g 0.75 points", "g 1.0 points", "g 1.25 points"] + list(PARTS),
              ([group_name(g), row[address]] + [number(x, True) for x in row["coupling_means"]] +
               [number(row["cross_replica"][k]) for k in PARTS] for g in report["groups"] for row in g[field]))
    lines.extend(["## Immutable data references", "",
        "External root: /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1.", "",
        "Population run: l20_extension1_recipient_repeats_population_v1_attempt1.", "",
        "Full rows: outputs/<run>/records.json; full fixed summaries: outputs/<run>/summary.json.", "",
        "COMPLETE SHA-256: " + PIN, "",
        "Records SHA-256: " + run.sha256_file(run.output_dir()/"records.json"), "",
        "Summary SHA-256: " + run.sha256_file(run.output_dir()/"summary.json"), "",
        "D180 summary SHA-256: " + run.sha256_file(old_path), "",
        "The source code/inputs are frozen; this rendering tool is downstream documentation",
        "and is not an executor dependency. Audit progress is not inspected. All complete",
        "path-level measurements, including guide addresses, remain externally available.", ""])
    return "\n".join(lines), sections


if __name__ == "__main__":
    text, sections = render()
    print(json.dumps(dict(markdown=text, sections=sections, numeric_rows=sum(s["rows"] for s in sections),
                          new_dynamics=0, audit_progress_inspected=False)))
