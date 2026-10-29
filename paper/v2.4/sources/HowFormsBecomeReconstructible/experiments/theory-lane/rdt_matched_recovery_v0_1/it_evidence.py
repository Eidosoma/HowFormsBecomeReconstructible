"""Condition-aware panel, unit and full-panel forecast commitments."""
from datetime import datetime
from pathlib import Path
import shutil
import time
import numpy as np

from it_common import (
    ROOT, NATIVE, C, P, MODELS, REGIMES, parent, ev, read, ledger, require,
    configure, identity, binding,
)
import it_forcing
import ff_selection
import ff_evidence
import pipeline
import fe_measurement
import verify_science
import cp_models


def create_panel(root, spec):
    configure(spec["scope"], C["injury_levels"][0])
    rows, refs = [], []
    source = read(ROOT / "context/SOURCE_COHORT.json")
    for block in spec["blocks"]:
        folder = root / f"units/panel/b{block}"
        folder.mkdir(parents=True)
        if spec["scope"] == "qualification":
            # Use all four disposable structures, matching the target's four-packet
            # unit size. Both task rules occur in each expression class.
            disposable = pipeline.specification("native_qualification")
            disposable["records_per_block"] = 4
            disposable["keys"] = [[b, h, f, 0] for b in spec["blocks"]
                                  for h, f in zip(P["acquisition"]["histories"], (0, 1, 1, 0), strict=True)]
            raw, selected, receipt = pipeline.synthetic_acquisition(
                block, disposable)
            ev.save(folder / "boundary.npz", raw)
            provenance = dict(synthetic=True, native_reads=0)
        else:
            origin = ROOT / f"context/founders/b{block}"
            ledger.verify(origin)
            enrolled = read(origin / "ENROLLMENT.json")["rows"]
            ff_selection.check_rows(block, enrolled, True)
            selected = [r for r in source["rows"] if r["block"] == block]
            require(selected == ff_selection.select(enrolled), "Saved boundary-only selection changed")
            shutil.copyfile(origin / "boundary.npz", folder / "boundary.npz")
            provenance = dict(synthetic=False, source_commit_sha256=ev.sha(origin / "COMMIT.json"),
                              source_path=str(origin.relative_to(ROOT)), native_reads=0)
        ff_selection.check_rows(block, selected, False)
        require(all(1 <= sum(r["current_pass"] == c for r in selected) <= 2 for c in (0, 1)),
                "Both original expression classes required")
        ledger.atomic_json(folder / "ENROLLMENT.json", dict(rows=selected, provenance=provenance))
        check = verify_science.boundary(NATIVE, folder, selected, spec["scope"] == "qualification")
        ledger.atomic_json(folder / "VERIFICATION.json", check)
        ledger.commit(folder, identity(spec, "panel", block=block), dict(block=block, rows=selected))
        refs.append(ledger.reference(root, folder))
        rows.extend(selected)
    folder = root / "panel"
    folder.mkdir()
    plan = dict(binding=binding(), spec=spec, rows=rows, blocks=spec["blocks"], references=refs)
    ledger.atomic_json(folder / "COHORT.json", plan)
    ledger.commit(folder, identity(spec, "panel_seal"), dict(blocks=spec["blocks"], rows=rows))
    return ledger.reference(root, folder)


def panel(root, ref, spec):
    folder, entry = ledger.referenced(root, ref, identity(spec, "panel_seal"))
    plan = read(folder / "COHORT.json")
    require(plan["binding"] == binding() and plan["spec"] == spec and plan["blocks"] == spec["blocks"],
            "Panel binding or scope differs")
    require(entry["payload"] == dict(blocks=plan["blocks"], rows=plan["rows"]), "Panel payload differs")
    require(len(plan["references"]) == len(plan["blocks"]), "Missing panel source")
    keys = [tuple(r["key"]) for r in plan["rows"]]
    require(len(keys) == len(set(keys)) and sorted({r["block"] for r in plan["rows"]}) == plan["blocks"],
            "Duplicate or incomplete panel")
    return plan


def source(root, plan, block, spec):
    require(block in plan["blocks"], "Block outside fixed panel")
    ref = plan["references"][plan["blocks"].index(block)]
    folder, entry = ledger.referenced(root, ref, identity(spec, "panel", block=block))
    rows = [r for r in plan["rows"] if r["block"] == block]
    require(entry["payload"] == dict(block=block, rows=rows), "Block panel payload differs")
    require(read(folder / "ENROLLMENT.json")["rows"] == rows, "Enrollment differs")
    verify_science.boundary(NATIVE, folder, rows, spec["scope"] == "qualification")
    return rows, pipeline.packets_for(folder, rows)


def measurement(root, ref, rows, spec, injury, benchmark=False, regime=None, packet_index=None):
    kind = "benchmark" if benchmark else "measure"
    fields = dict(block=rows[0]["block"], injury=injury)
    if benchmark:
        fields.update(regime=regime, packet_index=packet_index)
    folder, entry = ledger.referenced(root, ref, identity(spec, kind, **fields))
    configure("benchmark" if benchmark else spec["scope"], injury)
    forecasts = []
    for i, row in enumerate(rows):
        for g in ((regime,) if benchmark else REGIMES):
            case = folder / "case" if benchmark else folder / f"case_{i:02d}_{g}"
            prediction = fe_measurement.check_saved(case, row, g)
            require(it_forcing.measurement_masks(case, row, g, injury) == 128, "Mask coverage differs")
            expected_order = ["successor32", "direct64"]
            index = packet_index if benchmark else i
            if (index + REGIMES.index(g)) % 2:
                expected_order.reverse()
            require(read(case / "ORDER.json") == dict(order=expected_order, packet_index=index),
                    "Measurement order differs")
            forecasts.append(dict(**prediction, injury=injury))
    payload = dict(**fields, forecasts=forecasts, native_reads=len(forecasts) * 128,
                   flat_native_reads=len(forecasts) * 4)
    require(entry["payload"] == payload, "Measurement payload/cost differs")
    require(read(folder / "FORECASTS.json") == forecasts, "Forecast aggregate differs")
    return forecasts


def check_coverage(rows, forecasts, spec):
    expected = {(tuple(r["key"]), n, g) for r in rows for n in spec["injuries"] for g in REGIMES}
    actual = {(tuple(f["key"]), f["injury"], f["regime"]) for f in forecasts}
    require(len(forecasts) == len(actual) and actual == expected, "Full declared-condition forecast coverage required")
    ff_evidence.check_model_coverage(forecasts)
    lookup = {tuple(r["key"]): r for r in rows}
    for f in forecasts:
        require(all(f.get(k) == v for k, v in lookup[tuple(f["key"])].items()),
                "Forecast boundary or task changed")


def seal_forecasts(root, spec, panel_ref, refs):
    require(not (root / "units/future").exists(), "Future evidence precedes the global seal")
    plan = panel(root, panel_ref, spec)
    expected = [(n, b) for n in spec["injuries"] for b in spec["blocks"]]
    require(len(refs) == len(expected), "Incomplete measurement blocks")
    forecasts = []
    for ref, (injury, block) in zip(refs, expected, strict=True):
        rows, _ = source(root, plan, block, spec)
        forecasts.extend(measurement(root, ref, rows, spec, injury))
    check_coverage(plan["rows"], forecasts, spec)
    folder = root / "forecast_seal"
    folder.mkdir()
    started = time.process_time()
    candidates = cp_models.forecasts(forecasts)
    inference_cpu = time.process_time() - started
    value = dict(utc=ev.utc(), binding=binding(), spec=spec, panel=panel_ref,
                 rows=plan["rows"], measurements=refs, forecasts=forecasts,
                 candidate_forecasts=candidates, candidate_first_seal_cpu_seconds=inference_cpu,
                 candidate_models_sha256=C["candidate_models_sha256"],
                 calibration_models_sha256=C["calibration_models_sha256"],
                 all_conditions_checked_before_any_future=True)
    cp_models.check_sealed(forecasts, value["candidate_forecasts"])
    ledger.atomic_json(folder / "FORECAST_SEAL.json", value)
    ledger.commit(folder, identity(spec, "forecast_seal"), dict(forecasts=len(forecasts)))
    return dict(path="forecast_seal/FORECAST_SEAL.json", sha256=ev.sha(folder / "FORECAST_SEAL.json"),
                ref=ledger.reference(root, folder))


def check_seal(root, ref, spec):
    path = ledger.child(root, ref["path"])
    require(path.exists() and ev.sha(path) == ref["sha256"], "Unchanged global forecast seal required")
    folder, entry = ledger.referenced(root, ref["ref"], identity(spec, "forecast_seal"))
    require(path == folder / "FORECAST_SEAL.json", "Wrong seal path")
    seal = read(path)
    require(seal["binding"] == binding() and seal["spec"] == spec
            and seal["all_conditions_checked_before_any_future"], "Wrong global seal binding")
    plan = panel(root, seal["panel"], spec)
    require(plan["rows"] == seal["rows"], "Sealed panel differs")
    check_coverage(seal["rows"], seal["forecasts"], spec)
    require(seal["candidate_models_sha256"] == C["candidate_models_sha256"], "Candidate model binding differs")
    require(seal["calibration_models_sha256"] == C["calibration_models_sha256"], "Calibration binding differs")
    cp_models.check_sealed(seal["forecasts"], seal["candidate_forecasts"])
    require(entry["payload"] == dict(forecasts=len(seal["forecasts"])), "Seal count differs")
    return path, seal


def future(root, ref, rows, replicate, spec, injury, seal_ref):
    folder, entry = ledger.referenced(root, ref, identity(
        spec, "future", block=rows[0]["block"], injury=injury, replicate=replicate,
        seal_sha256=seal_ref["sha256"]))
    configure(spec["scope"], injury)
    key = min(rows, key=lambda r: r["selection_hash"])["key"]
    outcomes = []
    for regime in REGIMES:
        case = folder / regime
        labels = read(case / "OUTCOMES.json")
        verify_science.continuation(case, rows, labels, P["reader"], seal_ref["sha256"], key)
        it_forcing.future_masks(case, rows, injury, replicate)
        outcomes.extend(dict(**y, injury=injury, replicate=replicate) for y in labels)
    payload = dict(block=rows[0]["block"], injury=injury, replicate=replicate,
                   outcomes=outcomes, native_reads=len(rows) * 2 * 19, flat_native_reads=2 * 19)
    require(entry["payload"] == payload, "Continuation payload/cost differs")
    seal = read(ledger.child(root, seal_ref["path"]))
    require(datetime.fromisoformat(read(folder / "START.json")["utc"]) >
            datetime.fromisoformat(seal["utc"]), "Future started before global seal")
    return outcomes
