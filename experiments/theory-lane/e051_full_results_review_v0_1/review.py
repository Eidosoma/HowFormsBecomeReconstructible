"""Read-only E051 result verification; no dynamics or production imports.

Recomputes scores, block summaries, bootstrap intervals and decisions from the
saved cases. The separate E051 dynamics audit is checked by its hash bindings,
not rerun. Writes only a new, exclusive result file beside this script.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
ROOT = LANE.parent
E051 = ROOT / "E051_cue_pairing_robustness"
RUN = E051 / "runs/robustness_v1"
PILOT = LANE / "p01_writer_factorial_pulse_v0_1/runs/pilot_v1"
PAIRINGS = ("paired", "noise_0999", "noise_099", "noise_09", "noise_0", "reset_099", "reset_0")
WRITERS = ("exact_rewrite", "tolerance_rewrite", "ordinary_rewrite", "contrast_rewrite", "exact_preserve")
CONDITIONS = tuple(f"{p}/{w}" for p in PAIRINGS for w in WRITERS)
HORIZONS = (0, 8, 16, 24, 32)
INJURIES = ("intact", "scattered", "square")
BLOCKS = list(range(34000, 34032))


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_score(ports, correct, margin):
    # Axes: condition, founder, recipient, cue, optional injury, output port.
    assert ports.shape[:4] == (correct.shape[0], 4, 4, 2)
    assert np.isfinite(ports).all()
    expected = np.empty_like(margin)
    for founder, rule in enumerate((1., -1., 1., -1.)):
        for cue_index, cue in enumerate((1., -1.)):
            selected = ports[:, founder, :, cue_index]
            expected[:, founder, :, cue_index] = np.minimum(
                rule * cue * selected[..., 0], -rule * cue * selected[..., 1])
    assert expected.dtype == margin.dtype and expected.tobytes() == margin.tobytes()
    assert np.array_equal(expected > .25, correct)


def main():
    started = time.monotonic()
    evidence = {}

    def bind(path, expected=None):
        digest = sha(path)
        if expected is not None:
            assert digest == expected, str(path)
        evidence[str(path.relative_to(ROOT))] = digest
        return digest

    complete, manifest, summary = (read(RUN / n) for n in ("COMPLETE.json", "manifest.json", "summary.json"))
    audit, closeout = read(RUN / "INDEPENDENT_AUDIT.json"), read(E051 / "analysis/closeout_v1.json")
    assert complete["status"] == "COMPLETE" and complete["blocks_completed"] == 32
    assert not (RUN / "FAILED.json").exists()
    for name in ("manifest.json", "summary.json", "REPORT.md"):
        bind(RUN / name, complete["outputs_sha256"][name])
    for rel, digest in manifest["inputs_sha256"].items():
        bind(ROOT / rel, digest)
        bind(RUN / "inputs" / rel, digest)
    assert audit["status"] == closeout["status"] == "PASS"
    bind(RUN / "COMPLETE.json", audit["complete_sha256"])
    bind(E051 / "audit.py", audit["audit_code_sha256"])
    for rel, digest in closeout["evidence_sha256"].items():
        if "/robustness_v1/" in rel:
            bind(ROOT / rel, digest)
    bind(E051 / "analysis/closeout_v1.json")
    assert audit["all_teaching_rebuilding_holding_and_assays_replayed"]
    assert audit["all_mechanism_counts_and_connectivity_replayed"]
    # This flag is false by construction in scientific mode: E041 byte matching
    # is a compatibility check on the excluded fixture and benchmark only.
    assert audit["legacy_three_policies_all_boundaries_and_assays_match"] is False
    assert manifest["contract"]["mode"] == summary["mode"] == "scientific"
    assert manifest["contract"]["blocks"] == summary["blocks"] == BLOCKS
    assert tuple(summary["conditions"]) == CONDITIONS
    assert summary["cfg"]["margin"] == .25 and summary["lineages_per_condition"] == 512
    assert summary["independent_unit"] == "block" and summary["bootstrap_resamples"] == 10000

    values = {}
    counts, weight_sums = [], []
    terminal = []
    equivalent = {p: {"body_ports_byte_equal": True, "assay_ports_byte_equal": True} for p in PAIRINGS[1:5]}
    body_observations = terminal_observations = 0

    def append(key, value):
        values.setdefault(key, []).append(float(value))

    for block in BLOCKS:
        name = f"cases_{block:06d}.npz"
        bind(RUN / name, complete["outputs_sha256"][name])
        with np.load(RUN / name, allow_pickle=False) as saved:
            data = {k: saved[k] for k in saved.files}
        body_observations += data["body_correct"].size
        for g in range(32):
            verify_score(data["body_ports"][g], data["body_correct"][g], data["body_margin"][g])
            rates = data["body_correct"][g].all(axis=3).mean(axis=(1, 2))
            for index, name in enumerate(CONDITIONS):
                append(f"body/{g+1}/{name}", rates[index])
        for h in HORIZONS:
            prefix = f"assay_h{h}"
            ports, correct, margins = (data[f"{prefix}_{k}"] for k in ("ports", "correct", "margin"))
            verify_score(ports, correct, margins)
            terminal_observations += correct.size
            rates = correct.all(axis=3).mean(axis=(1, 2))
            names = ("initial", "erased") if h == 0 else (*CONDITIONS, "erased")
            for index, name in enumerate(names):
                for j, injury in enumerate(INJURIES):
                    append(f"assay/{h}/{name}/{injury}", rates[index, j])
            if h:
                for p, checks in equivalent.items():
                    a, b = CONDITIONS.index(p + "/exact_rewrite"), CONDITIONS.index(p + "/contrast_rewrite")
                    checks["assay_ports_byte_equal"] &= ports[a].tobytes() == ports[b].tobytes()
        terminal.append(data["assay_h32_correct"][..., 1].all(axis=3))
        for p, checks in equivalent.items():
            a, b = CONDITIONS.index(p + "/exact_rewrite"), CONDITIONS.index(p + "/contrast_rewrite")
            checks["body_ports_byte_equal"] &= data["body_ports"][:, a].tobytes() == data["body_ports"][:, b].tobytes()
        # Generation 1 has no returning cells. Sum within each block first.
        counts.append(data["counts"][1:].sum(axis=(0, 2, 3)))
        weight_sums.append(data["sums"][1:].sum(axis=(0, 2, 3)))

    values = {k: np.array(v) for k, v in values.items()}
    count = np.array(counts)
    sums = np.array(weight_sums)
    fields = {"exact_zero_returning": (4, 3), "ordinary_selected_returning": (5, 3),
              "nonzero_returning": (6, 3), "strong_returning": (7, 3),
              "new_nonzero_available": (9, 8), "returning_reachable_before": (11, 10),
              "returning_reachable_after": (12, 10), "ordinary_selected_available": (2, 0)}
    for index, name in enumerate(CONDITIONS):
        pairing, writer = name.split("/")
        x = values[f"assay/32/{name}/scattered"]
        if pairing != "paired":
            values[f"pairing_effect/{name}"] = x - values[f"assay/32/paired/{writer}/scattered"]
        if writer != "exact_rewrite":
            values[f"writer_effect/{name}"] = x - values[f"assay/32/{pairing}/exact_rewrite/scattered"]
        for key, (numerator, denominator) in fields.items():
            assert (count[:, index, denominator] > 0).all()
            values[f"mechanism/{name}/{key}"] = count[:, index, numerator] / count[:, index, denominator]
        for j, key in enumerate(("mean_abs_returning_weight", "mean_abs_returning_contrast")):
            values[f"mechanism/{name}/{key}"] = sums[:, index, j] / count[:, index, 3]

    # Reproduce the frozen block-bootstrap stream, without importing its helper.
    seed_bytes = hashlib.sha256(b'["E051","bootstrap","cue_pairing_robustness"]').digest()[:16]
    generator = np.random.Generator(np.random.PCG64(int.from_bytes(seed_bytes, "little")))
    draws = generator.integers(0, 32, (10000, 32))
    assert set(values) == set(summary["statistics"])
    for key, x in values.items():
        expected = {"mean": float(x.mean()), "block_means": x.tolist(),
                    "ci95": np.quantile(x[draws].mean(axis=1), [.025, .975]).tolist()}
        assert expected == summary["statistics"][key], key
    assert len(values) == audit["summaries_checked"] == 1966
    assert body_observations == summary["body_cue_observations"] == audit["body_cue_observations"]
    assert terminal_observations == summary["terminal_cue_observations"] == audit["terminal_cue_observations"]

    statistics = summary["statistics"]
    gates = {"paired_baseline_lower_above_075": statistics["assay/32/paired/exact_rewrite/scattered"]["ci95"][0] > .75}
    for p in ("noise_0999", "reset_099"):
        gates[p + "_lower_above_075"] = statistics[f"assay/32/{p}/exact_rewrite/scattered"]["ci95"][0] > .75
        gates[p + "_difference_lower_above_minus_005"] = statistics[f"pairing_effect/{p}/exact_rewrite"]["ci95"][0] > -.05
        assert summary["primary_classifications"][p] == "ROBUST_WITHIN_FIVE_POINTS"
    assert gates == summary["primary_gates"] and all(gates.values())
    assert summary["primary_decision"] == audit["scientific_decision"] == True
    assert summary["status"] == "PAIRING_ROBUSTNESS_ESTABLISHED"

    flags = np.stack(terminal)
    results = {}
    for index, name in enumerate((*CONDITIONS, "erased")):
        results[name] = {"successes": int(flags[:, index].sum()), "lineages": 512,
                         "first_8_successes": int(flags[:8, index].sum()),
                         "remaining_24_successes": int(flags[8:, index].sum()),
                         **statistics[f"assay/32/{name}/scattered"]}
    fallback = {}
    for p in PAIRINGS:
        index = CONDITIONS.index(p + "/exact_rewrite")
        fallback[p] = {"selected_returning_edges": int(count[:, index, 5].sum()),
                       "returning_edges": int(count[:, index, 3].sum()),
                       "block_rate": statistics[f"mechanism/{p}/exact_rewrite/ordinary_selected_returning"]}

    pilot_complete = read(PILOT / "COMPLETE.json")
    bind(PILOT / "COMPLETE.json")
    for name in ("REPORT.md", "analysis.json", "terminal_lineages.csv", "sign_completion_block_summaries.csv", "verification.json"):
        bind(PILOT / name, pilot_complete["outputs_sha256"][name])
    with (PILOT / "sign_completion_block_summaries.csv").open() as stream:
        completions = list(csv.DictReader(stream))
    assert len(completions) == 720
    assert all(float(r["magnitude_sign_fallback_fraction"]) == 0 for r in completions)
    bind(Path(__file__))
    result = dict(status="PASS", utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-started,
        scope="Saved-case scoring and inference recomputation; source bindings and existing independent dynamics audit checked. No dynamics rerun.",
        blocks=BLOCKS, statistics_recomputed=len(values), primary_gates=gates,
        body_cue_observations_rescored=body_observations, terminal_cue_observations_rescored=terminal_observations,
        h32_scattered=results, original_returning_fallback=fallback,
        original_vs_pure_contrast=equivalent,
        pilot_sign_completion_rows_checked=len(completions), pilot_sign_completion_used=False,
        existing_dynamics_audit_utc=audit["utc"], existing_dynamics_audit_status=audit["status"],
        newly_exposed="All 32 blocks, seven pairings, five writers, saved body/assay outcomes and aggregate mechanisms; remaining 24 blocks are development evidence from this review onward.",
        evidence_sha256=evidence)
    with (HERE / "verification.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "seconds", "statistics_recomputed", "primary_gates", "original_vs_pure_contrast", "pilot_sign_completion_used")}, indent=2))
    for p in PAIRINGS:
        print(p, {w: results[p + "/" + w]["successes"] for w in WRITERS},
              "fallback", fallback[p]["block_rate"]["mean"])


if __name__ == "__main__":
    main()
