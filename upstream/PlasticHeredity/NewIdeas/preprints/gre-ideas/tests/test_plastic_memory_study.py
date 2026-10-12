from __future__ import annotations

from pathlib import Path

import pytest

from gre_sim.artifacts import read_json, read_jsonl_gz, sha256_file
from gre_sim.plastic_memory_config import PlasticMemorySpec
from gre_sim.plastic_memory_protocols import quick_spec
from gre_sim.plastic_memory_study import (
    _render_report,
    recompute_memory_analysis,
    replay_memory_future,
    run_memory_study,
    verify_memory_run,
)


def test_memory_config_roundtrip() -> None:
    spec = quick_spec()
    assert PlasticMemorySpec.from_dict(spec.to_dict()) == spec


def test_memory_report_renders_unavailable_gate_estimates() -> None:
    unavailable = {"mean": None, "lower": None}
    gate = {
        "passed": False,
        "metrics": {
            "risk_difference": unavailable,
            "crossover": unavailable,
            "log_loss_gain": unavailable,
        },
        "split_half_reliability": None,
    }
    analysis = {
        "descriptor_exact_rate": None,
        "exploratory": True,
        "phase": "cue-calibration",
        "record_count": 24,
        "state_transfer_gates": {"boolean-primary": gate},
        "mark_transfer_gates": {
            "boolean-primary": {
                "half-1.mu-0.25": {
                    "passed": False,
                    "metrics": {"risk_difference": unavailable},
                }
            }
        },
    }
    manifest = {
        "source_rulebooks": 2,
        "elapsed_seconds": 1.0,
    }

    report = _render_report(analysis, manifest)

    assert "Absolute correct-form hold-8 gain: not estimable" in report
    assert "Held-out log-loss gain: not estimable" in report
    assert "forced-break hold-8 gain not estimable" in report


def test_quick_memory_run_resumes_recomputes_replays_and_is_worker_invariant(
    tmp_path: Path,
) -> None:
    spec = quick_spec()
    serial = tmp_path / "serial"
    run_memory_study(spec, serial, workers=1)
    verified = verify_memory_run(serial)
    assert verified["verified"]
    assert verified["self_transplant_equivalence"]["equal"]
    assert recompute_memory_analysis(serial)["matches"]
    first = next(read_jsonl_gz(serial / "futures.jsonl.gz"))
    assert replay_memory_future(serial, first["future_id"])["matches"]
    assert read_json(serial / "manifest.json")["record_count"] > 0

    checksum = sha256_file(serial / "SHA256SUMS")
    run_memory_study(spec, serial, workers=1)
    assert sha256_file(serial / "SHA256SUMS") == checksum

    parallel = tmp_path / "parallel"
    run_memory_study(spec, parallel, workers=2)
    assert sha256_file(serial / "futures.jsonl.gz") == sha256_file(
        parallel / "futures.jsonl.gz"
    )
    assert read_json(serial / "analysis.json") == read_json(
        parallel / "analysis.json"
    )


def test_memory_run_resumes_from_a_hashed_source_after_interruption(
    tmp_path: Path, monkeypatch
) -> None:
    import gre_sim.plastic_memory_study as study

    spec = quick_spec()
    destination = tmp_path / "interrupted"
    original = study.iter_memory_source_results

    def interrupted(registry, phase_spec, workers, progress):
        iterator = original(registry, phase_spec, workers, progress)
        yield next(iterator)
        raise RuntimeError("injected interruption")

    monkeypatch.setattr(study, "iter_memory_source_results", interrupted)
    with pytest.raises(RuntimeError, match="injected interruption"):
        run_memory_study(spec, destination, workers=1)
    assert len(list((destination / "shards").glob("*.manifest.json"))) == 1

    monkeypatch.setattr(study, "iter_memory_source_results", original)
    run_memory_study(spec, destination, workers=1)
    assert verify_memory_run(destination)["verified"]
