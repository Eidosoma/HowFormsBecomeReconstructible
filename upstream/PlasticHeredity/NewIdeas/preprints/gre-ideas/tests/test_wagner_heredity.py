from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gre_sim.artifacts import (
    canonical_digest,
    read_json,
    read_jsonl_gz,
    sha256_file,
    write_json,
)
from gre_sim.plastic_memory_protocols import calibration_spec
from gre_sim.wagner_heredity_analysis import passing_state_writers
from gre_sim.wagner_heredity_campaign import expected_heredity_futures
from gre_sim.wagner_heredity_config import WagnerHereditySpec
from gre_sim.wagner_heredity_evolution import (
    HeredityEvolutionSpec,
    quick_evolution_spec,
    run_heredity_evolution,
)
from gre_sim.wagner_heredity_orchestrator import (
    run_full_wagner_heredity_campaign,
    verify_wagner_heredity_campaign,
)
from gre_sim.wagner_heredity_protocols import discovery_spec, quick_spec
from gre_sim.wagner_heredity_study import (
    recompute_heredity_analysis,
    replay_heredity_future,
    run_heredity_study,
    verify_heredity_run,
)


def test_heredity_contract_roundtrips_and_counts_are_frozen() -> None:
    discovery = discovery_spec("0" * 64)
    assert WagnerHereditySpec.from_dict(discovery.to_dict()) == discovery
    assert expected_heredity_futures(discovery) == 2_801_664
    assert expected_heredity_futures(quick_spec()) == 432
    evolution = quick_evolution_spec()
    assert HeredityEvolutionSpec.from_dict(evolution.to_dict()) == evolution


def test_legacy_plastic_memory_digest_remains_unchanged() -> None:
    assert canonical_digest(calibration_spec().to_dict()) == (
        "b8ced905fffad8e058d2188f6b6ae12e4fafd428a3eebfb9e6ea25037afc054c"
    )


def test_quick_heredity_run_resumes_recomputes_and_replays(tmp_path: Path) -> None:
    destination = tmp_path / "quick"
    run_heredity_study(quick_spec(), destination, workers=1)
    assert verify_heredity_run(destination)["verified"]
    assert recompute_heredity_analysis(destination)["matches"]
    analysis = read_json(destination / "analysis.json")
    assert analysis["self_transplant_equivalence"]["equal"]
    first = next(read_jsonl_gz(destination / "futures.jsonl.gz"))
    assert replay_heredity_future(destination, first["future_id"])["matches"]
    checksum = sha256_file(destination / "SHA256SUMS")
    run_heredity_study(quick_spec(), destination, workers=1)
    assert sha256_file(destination / "SHA256SUMS") == checksum


def test_heredity_run_is_worker_invariant(tmp_path: Path) -> None:
    spec = replace(quick_spec(), source_count=2)
    serial = tmp_path / "serial"
    parallel = tmp_path / "parallel"
    run_heredity_study(spec, serial, workers=1)
    run_heredity_study(spec, parallel, workers=2)
    assert sha256_file(serial / "futures.jsonl.gz") == sha256_file(
        parallel / "futures.jsonl.gz"
    )
    assert read_json(serial / "analysis.json") == read_json(
        parallel / "analysis.json"
    )


def test_heredity_run_resumes_from_a_hashed_source(
    tmp_path: Path, monkeypatch
) -> None:
    import gre_sim.wagner_heredity_study as study

    destination = tmp_path / "interrupted"
    spec = replace(quick_spec(), source_count=2)
    original = study.iter_heredity_source_results

    def interrupted(registry, value, workers, progress):
        iterator = original(registry, value, workers, progress)
        yield next(iterator)
        raise RuntimeError("injected heredity interruption")

    monkeypatch.setattr(study, "iter_heredity_source_results", interrupted)
    with pytest.raises(RuntimeError, match="injected heredity interruption"):
        run_heredity_study(spec, destination, workers=1)
    assert len(list((destination / "shards").glob("*.manifest.json"))) == 1

    monkeypatch.setattr(study, "iter_heredity_source_results", original)
    run_heredity_study(spec, destination, workers=1)
    assert verify_heredity_run(destination)["verified"]


def test_state_selection_never_promotes_boundary_diagnostics() -> None:
    analysis = {
        "state_transfer_gates": {
            "hard": {"primary": True, "passed": True},
            "boundary": {"primary": False, "passed": True},
            "soft": {"primary": True, "passed": False},
        }
    }
    assert passing_state_writers(analysis) == ("hard",)


def test_quick_heredity_evolution_seals_and_resumes(tmp_path: Path) -> None:
    destination = tmp_path / "evolution"
    run_heredity_evolution(quick_evolution_spec(), destination, workers=1)
    assert read_json(destination / "analysis.json")["format"] == (
        "gre-wagner-heredity-evolution-analysis-v1"
    )
    checksum = sha256_file(destination / "SHA256SUMS")
    run_heredity_evolution(quick_evolution_spec(), destination, workers=1)
    assert sha256_file(destination / "SHA256SUMS") == checksum


def test_quick_full_heredity_orchestrator_seals_and_resumes(
    tmp_path: Path, monkeypatch
) -> None:
    import gre_sim.wagner_heredity_orchestrator as orchestrator

    parent = tmp_path / "parent-rescue"
    parent.mkdir()
    write_json(
        parent / "candidate.json",
        {
            "ready": True,
            "selected": {
                "model": {
                    "variant": "wagner_sequential",
                    "gamma_variance": 0.0,
                },
                "intervention": {"mode": "persistent_hard", "fraction": 1.0},
            },
        },
    )
    (parent / "SHA256SUMS").write_text("fixture\n", encoding="ascii")
    monkeypatch.setattr(
        orchestrator, "verify_wagner_rescue_campaign", lambda path: {"verified": True}
    )
    monkeypatch.setattr(orchestrator, "discovery_spec", quick_spec)
    monkeypatch.setattr(
        orchestrator, "confirmation_spec", lambda digest, selected: quick_spec(digest)
    )
    monkeypatch.setattr(
        orchestrator,
        "mark_discovery_spec",
        lambda digest, writer: quick_spec(digest),
    )
    monkeypatch.setattr(
        orchestrator, "passing_state_writers", lambda analysis: ("hard-quick",)
    )
    monkeypatch.setattr(orchestrator, "weakest_writer", lambda names: "hard-quick")
    monkeypatch.setattr(orchestrator, "select_mark_candidate", lambda analysis, writer: None)

    output = tmp_path / "campaign"
    run_full_wagner_heredity_campaign(
        parent, output, workers=1, gard_root=None, include_evolution=False
    )
    assert verify_wagner_heredity_campaign(output)["verified"]
    assert read_json(output / "campaign-manifest.json")["confirmed_writers"] == [
        "hard-quick"
    ]
    checksum = sha256_file(output / "SHA256SUMS")
    run_full_wagner_heredity_campaign(
        parent, output, workers=1, gard_root=None, include_evolution=False
    )
    assert sha256_file(output / "SHA256SUMS") == checksum
