from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gre_sim.artifacts import read_json, read_jsonl_gz, sha256_file
from gre_sim.config import StudySpec
from gre_sim.mechanism_config import MechanismSpec
from gre_sim.mechanism_study import (
    recompute_mechanism_analysis,
    replay_mechanism_future,
    run_mechanism_study,
    verify_mechanism_run,
)
from gre_sim.study import run_study


def test_quick_mechanism_run_verifies_recomputes_and_replays(tmp_path: Path) -> None:
    parent_spec = replace(
        StudySpec.quick_v2(),
        cohorts=("sampled",),
        launch_states_per_rulebook=2,
    )
    parent = tmp_path / "parent"
    run_study(parent_spec, parent, workers=1)
    destination = tmp_path / "mechanism"
    run_mechanism_study(
        MechanismSpec.quick(), destination, parent, workers=1
    )
    verification = verify_mechanism_run(destination)
    assert verification["verified"]
    assert verification["records"] == 200
    assert recompute_mechanism_analysis(destination)["matches"]
    first = next(read_jsonl_gz(destination / "futures.jsonl.gz"))
    assert replay_mechanism_future(destination, first["future_id"])["matches"]
    assert (destination / "report.md").is_file()
    assert len(list((destination / "figures").glob("*.png"))) == 2

    parallel = tmp_path / "mechanism-parallel"
    run_mechanism_study(MechanismSpec.quick(), parallel, parent, workers=2)
    assert sha256_file(parallel / "futures.jsonl.gz") == sha256_file(
        destination / "futures.jsonl.gz"
    )
    assert read_json(parallel / "analysis.json") == read_json(
        destination / "analysis.json"
    )
