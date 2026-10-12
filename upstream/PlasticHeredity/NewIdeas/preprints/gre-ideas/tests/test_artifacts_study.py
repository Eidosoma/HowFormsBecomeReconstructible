from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from gre_sim.artifacts import (
    atomic_destination,
    canonical_digest,
    read_json,
    read_jsonl_gz,
    verify_checksums,
    write_checksums,
)
from gre_sim.config import StudySpec
from gre_sim.study import recompute_analysis, replay_future, run_study, verify_run


def test_atomic_destination_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        with atomic_destination(destination):
            pass


def test_checksum_detects_corruption(tmp_path: Path) -> None:
    directory = tmp_path / "checksums"
    directory.mkdir()
    target = directory / "value.txt"
    target.write_text("first", encoding="utf-8")
    write_checksums(directory)
    assert verify_checksums(directory)["value.txt"]
    target.write_text("second", encoding="utf-8")
    with pytest.raises(ValueError):
        verify_checksums(directory)


def test_complete_quick_run_verifies_reanalyzes_and_replays(tmp_path: Path) -> None:
    destination = tmp_path / "quick-run"
    run_study(StudySpec.quick(), destination, workers=1)
    verification = verify_run(destination)
    assert verification["verified"]
    assert verification["records"] == 384
    assert recompute_analysis(destination)["matches"]
    first = next(read_jsonl_gz(destination / "futures.jsonl.gz"))
    replay = replay_future(destination, first["future_id"])
    assert replay["matches"]
    assert len(replay["observations"]) == StudySpec.quick().horizon
    assert (destination / "report.md").is_file()
    assert len(list((destination / "figures").glob("*.png"))) == 3


def test_v2_donor_run_verifies_reanalyzes_and_replays_whole_half(tmp_path: Path) -> None:
    destination = tmp_path / "quick-v2-run"
    spec = replace(
        StudySpec.quick_v2(), engines=("boolean",), cohorts=("sampled",)
    )
    run_study(spec, destination, workers=1)
    verification = verify_run(destination)
    assert verification["verified"]
    assert verification["records"] == 224
    assert recompute_analysis(destination)["matches"]
    assert read_json(destination / "registration.json")["format"] == (
        "gre-rehoming-registration-v2-prototype"
    )
    assert read_json(destination / "manifest.json")["raw_format"] == (
        "gre-rehoming-futures-v2-prototype"
    )
    assert read_json(destination / "analysis.json")["format"] == (
        "gre-rehoming-analysis-v2-prototype"
    )
    donor = next(
        record
        for record in read_jsonl_gz(destination / "futures.jsonl.gz")
        if record["inheritance_mode"] == "donor_shuffled"
        and float(record["carryover"]) == 1.0
    )
    replay = replay_future(destination, donor["future_id"])
    assert replay["matches"]
    assert len(replay["observations"]) == spec.horizon
    report = (destination / "report.md").read_text(encoding="utf-8")
    assert "Own-history contrast" in report
    assert "engineering diagnostic" in report
