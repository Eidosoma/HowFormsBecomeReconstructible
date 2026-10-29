"""Saved-source D183 boundary qualification; never generates scientific futures."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np

from . import l22_active_form as model
from .io import canonical_digest, sha256_file, utc_now


WS = Path(__file__).resolve().parents[2]
ROOT = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form")
SOURCE_ROOT = ROOT.parent
SOURCE_ID = "l22_fresh_donor_reversal_v1_attempt1"
RUN_ID = "l22_active_form_boundary_v1_attempt1"
CAP = 256 * 1024**2
RESERVE = 4 * 1024**3
SCIENCE = ("L22-active-form/DEVELOPMENT_V1.md", "src/laws_confirmation/l22_active_form.py",
           "src/laws_confirmation/l22_active_form_qualification.py",
           "scripts/check_l22_active_form_boundary.py", "tests/test_l22_active_form.py")


def checker():
    path = WS / "scripts/check_l22_active_form_boundary.py"
    spec = importlib.util.spec_from_file_location("d183_scalar_boundary_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime():
    assert ROOT.is_dir() and Path("/mnt/bioIce1").resolve() in ROOT.resolve().parents
    cpus = sorted(os.sched_getaffinity(0))
    assert 0 < len(cpus) <= 6 and set(cpus) <= set(range(6))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert os.environ.get(name) == "1", name
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    size = sum(p.stat().st_size for p in ROOT.rglob("*") if p.is_file())
    assert size < CAP and shutil.disk_usage(ROOT).free >= RESERVE
    return dict(bytes=size, cap_bytes=CAP, reserve_bytes=RESERVE, affinity=cpus,
                numerical_threads=1, workers=1)


def destination(path):
    assert ROOT.resolve() in path.resolve().parents
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with destination(path).open("x", encoding="utf-8") as handle:
        handle.write(encoded)


def write_arrays(path, values):
    assert all(isinstance(v, np.ndarray) and v.dtype != object for v in values.values())
    with destination(path).open("xb") as handle:
        np.savez_compressed(handle, **values)


def arrays(path):
    with np.load(path, allow_pickle=False) as value:
        return {k: value[k].copy() for k in value.files}


def verify(hashes):
    for path, expected in hashes.items():
        assert sha256_file(Path(path)) == expected, path


def test_receipt(path):
    assert ROOT.resolve() in path.resolve().parents and path.is_file()
    suites = ET.parse(path).getroot()
    groups = [suites] if suites.tag == "testsuite" else list(suites.findall("testsuite"))
    assert groups
    assert all(int(suite.get(k, "0")) == 0 for suite in groups for k in ("failures", "errors", "skipped"))
    cases = list(suites.iter("testcase"))
    assert len(cases) == sum(int(suite.get("tests", "0")) for suite in groups)
    assert not any(list(case.iter(k)) for case in cases for k in ("failure", "error", "skipped"))
    assert len(cases) >= 50 and any(c.get("name") == "test_native_update_bridge_and_selective_controls" for c in cases)
    assert any(c.get("name") == "test_fresh_reader_resets_and_exact_common_control" for c in cases)
    return dict(path=str(path.resolve()), sha256=sha256_file(path), cases=len(cases),
                seconds=sum(float(suite.get("time", "0")) for suite in groups))


def source_contract(xml):
    assert xml.stat().st_mtime_ns >= max((WS / p).stat().st_mtime_ns for p in SCIENCE), "rerun tests after science edits"
    directory = SOURCE_ROOT / "outputs" / SOURCE_ID
    run = SOURCE_ROOT / "runs" / SOURCE_ID
    state = json.loads((run / "STATUS.json").read_text())
    assert state["status"] == "COMPLETE" and state["completed_cleanly"] is True
    assert state["verified_saved_analysis"] is True and state["checked_tissues"] == 16
    assert (run / "COMPLETE").exists() and not (run / "FAILED").exists()
    manifest = directory / "output_hashes.sha256"
    lines = [line.split("  ", 1) for line in manifest.read_text().splitlines()]
    old = {path: digest for digest, path in lines}
    assert len(lines) == len(old) == 707
    selected = {}
    for index in model.DEVELOPMENT:
        for name in ("parent.npz", "boundary.npz", "writing.json"):
            path = directory / f"tissue_{index}" / name
            assert str(path) in old
            selected[str(path)] = old[str(path)]
    verify(selected)
    deps = model.source.input_paths()
    deps += [Path(model.__file__).with_name("l22_fixed_record_readout.py")]
    deps += [WS / p for p in SCIENCE]
    deps += [manifest, run / "STATUS.json", run / "MANIFEST.json", run / "COMPLETE", xml]
    hashes = {str(p.resolve()): sha256_file(p) for p in sorted(set(deps))}
    hashes.update(selected)
    return dict(schema="d183_boundary_qualification_v1", frozen_utc=utc_now(),
        inputs=hashes, tests=test_receipt(xml), development_blocks=list(model.DEVELOPMENT),
        pairs=[list(p) for p in model.PAIRS], norm=.3, reset=dict(R="zero", ema="zero"),
        source_id=SOURCE_ID, source_manifest_entries=707, selected_source_files=48,
        entire_historical_panel_reaudited=False, prospective_confirmation=False,
        new_scientific_dynamics=0, new_founders=0, python=sys.version, numpy=np.__version__,
        resources=runtime(), automatic_successor=False)


def qualify(xml):
    runtime()
    tick = time.monotonic()
    freeze = source_contract(xml)
    run, output = ROOT / "runs" / RUN_ID, ROOT / "outputs" / RUN_ID
    assert not run.exists() and not output.exists(), "immutable attempt already exists"
    run.mkdir()
    output.mkdir()
    try:
        write_json(run / "FREEZE.json", freeze)
        check = checker()
        results = []
        for index in model.DEVELOPMENT:
            source_dir = SOURCE_ROOT / "outputs" / SOURCE_ID / f"tissue_{index}"
            parent = arrays(source_dir / "parent.npz")
            original = arrays(source_dir / "boundary.npz")
            metadata = json.loads((source_dir / "writing.json").read_text())
            assert metadata["tissue"] == index and metadata["passes"] is True
            assert metadata["parent_origin"] == "fresh_source_preparation"
            assert model.source.base.state_digest(parent) == metadata["source_parent_sha256"]
            assert model.source.base.array_digest(original["native_theta"]) == metadata["source_native_sha256"]
            cfg = model.source.CONFIG
            assert canonical_digest(metadata["config"]) == canonical_digest(
                asdict(model.source.CONFIG) | {"times": [0, 1, 50, 250, 500, 1000]})
            args = (parent["theta"], original["kept_V"], original["fresh"],
                    original["damaged_theta"], index, cfg.replicates)
            cell = output / f"tissue_{index}"
            cell.mkdir()
            try:
                boundary = model.construct(*args)
            except model.DegenerateCommonRecord as error:
                result = dict(tissue=index, construction_passes=False, error=str(error),
                              retained=True, replaced=False)
                write_json(cell / "CHECK.json", result)
                results.append(result)
                continue
            proof = check.check(*args, boundary)
            initial_states = {}
            for packet in model.PACKETS:
                for body in model.BODIES:
                    initial = model.initial(boundary, body, packet)
                    check.check_initial(boundary, body, packet, initial)
                    initial_states.update({f"{packet}__{body}__{key}": value for key, value in initial.items()})
            write_arrays(cell / "boundary.npz", boundary)
            write_arrays(cell / "initial_states.npz", initial_states)
            saved_boundary, saved_initials = arrays(cell / "boundary.npz"), arrays(cell / "initial_states.npz")
            assert check.check(*args, saved_boundary) == proof
            for packet in model.PACKETS:
                for body in model.BODIES:
                    prefix = f"{packet}__{body}__"
                    restored = {key: saved_initials[prefix + key] for key in model.STATE_KEYS}
                    check.check_initial(saved_boundary, body, packet, restored)
            result = dict(tissue=index, construction_passes=True, proof=proof,
                initial_states_checked=10, saved_roundtrip_passes=True,
                source_files={str(p): freeze["inputs"][str(p)] for p in sorted(source_dir.iterdir())
                              if str(p) in freeze["inputs"]})
            write_json(cell / "CHECK.json", result)
            results.append(result)
            runtime()
        assert [r["tissue"] for r in results] == list(model.DEVELOPMENT)
        passed = all(r["construction_passes"] for r in results)
        report = dict(boundary_qualification_passes=passed, blocks=len(results), records=16 * 16,
            unordered_pairs=16 * 8, results=results, new_scientific_dynamics=0,
            new_founders=0, new_functional_outcomes=0, fresh_confirmation_started=False,
            serial_renewal_started=False, law_verdict_changes=0, automatic_successor=False)
        write_json(output / "summary.json", report)
        verify(freeze["inputs"])
        output_hashes = {str(p): sha256_file(p) for p in sorted(output.rglob("*")) if p.is_file()}
        done = dict(status="COMPLETE", completed_utc=utc_now(), seconds=time.monotonic()-tick,
            boundary_qualification_passes=passed, freeze_sha256=sha256_file(run / "FREEZE.json"),
            outputs=output_hashes, resources=runtime(), new_scientific_dynamics=0,
            new_functional_outcomes=0, automatic_successor=False)
        write_json(run / "COMPLETE.json", done)
        return done
    except Exception as error:
        write_json(run / "FAILED.json", dict(failed_utc=utc_now(), error=str(error),
            traceback=traceback.format_exc(), automatic_retry=False))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualify", type=Path, required=True, help="passed scoped pytest XML")
    args = parser.parse_args()
    result = qualify(args.qualify.resolve())
    print(json.dumps({k: v for k, v in result.items() if k != "outputs"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

