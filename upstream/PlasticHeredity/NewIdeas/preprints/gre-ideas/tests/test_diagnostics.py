from __future__ import annotations

from pathlib import Path

import pytest

from gre_sim.artifacts import read_json, sha256_file, verify_checksums
from gre_sim.config import StudySpec
from gre_sim.diagnostics import DIAGNOSTIC_FORMAT, derive_diagnostics
from gre_sim.study import run_study, verify_run


def test_diagnostics_are_derived_without_changing_source_run(tmp_path: Path) -> None:
    source = tmp_path / "quick-run"
    output = tmp_path / "quick-diagnostics"
    run_study(StudySpec.quick(), source, workers=1)
    before = sha256_file(source / "SHA256SUMS")

    assert derive_diagnostics(source, output) == output.resolve()

    assert sha256_file(source / "SHA256SUMS") == before
    assert verify_run(source)["verified"]
    assert verify_checksums(output)["diagnostics.json"]
    diagnostic = read_json(output / "diagnostics.json")
    assert diagnostic["format"] == DIAGNOSTIC_FORMAT
    assert diagnostic["source_futures"] == 384
    assert set(diagnostic["primary_rulebook_diagnostics"]["strata"]) == {
        "boolean.evolved",
        "boolean.sampled",
        "wagner.evolved",
        "wagner.sampled",
    }
    assert len(diagnostic["primary_rulebook_diagnostics"]["per_rulebook"]) == 4
    assert len(list((output / "figures").glob("*.png"))) == 3
    report = (output / "PILOT_V1_DIAGNOSTIC_REPORT.md").read_text(encoding="utf-8")
    assert "cannot revise the frozen advancement decision" in report

    with pytest.raises(FileExistsError):
        derive_diagnostics(source, output)
