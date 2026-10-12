from __future__ import annotations

from dataclasses import replace

import numpy as np

from gre_sim.artifacts import read_json, read_jsonl_gz, sha256_file
from gre_sim.local_ph_config import LocalCarrierGenome, expected_local_records
from gre_sim.local_ph_dynamics import (
    LocalCarrierState,
    blank_local,
    copy_local,
    structural_mask,
    write_local,
)
from gre_sim.local_ph_protocols import (
    NOMINAL_COPY_NOISE,
    local_confirmation_spec,
    local_search_spec,
)
from gre_sim.local_ph_search import run_local_search, select_nominees, verify_local_search
from gre_sim.local_ph_study import replay_local_future, run_local_study, verify_local_study
from gre_sim.wagner import WagnerRulebook


def _genome(name: str = "local-test", k: int = 5) -> LocalCarrierGenome:
    return LocalCarrierGenome(name, 0.75, 0.02, 0.75, 2, "outgoing", k)


def test_confirmation_budget_is_explicit_and_below_cap() -> None:
    spec = local_confirmation_spec((_genome("first"), _genome("second", 3)))
    assert len(spec.conditions) == 22
    assert expected_local_records(spec) == 1_216_512
    assert spec.source_count == 96
    assert spec.checkpoint_generations == (0, 1, 2, 4, 8, 16)
    assert spec.challenges == ("forced_break", "neutral_damage", "release_only")


def test_local_writer_is_bounded_masked_and_target_blind() -> None:
    genome = _genome(k=3)
    initial = blank_local(10)
    written = write_local(initial, (0b1111111111, 0b1111111111), genome, (0, 2, 4))
    assert all(-1.0 <= value <= 1.0 for value in written.values)
    assert {index for index, value in enumerate(written.values) if value} == {0, 2, 4}
    opposing = write_local(written, (0, ), genome, (0, 2, 4))
    assert 0.0 < opposing.values[0] < written.values[0]
    copied = copy_local(
        written,
        genome,
        NOMINAL_COPY_NOISE,
        (0, 2, 4),
        np.random.Generator(np.random.Philox(123)),
    )
    assert all(copied.values[index] == 0.0 for index in set(range(10)) - {0, 2, 4})


def test_structural_mask_uses_only_wagner_weights() -> None:
    weights = np.zeros((10, 10), dtype=float)
    weights[:, 7] = 3.0
    weights[:, 2] = 2.0
    weights[:, 5] = 1.0
    rulebook = WagnerRulebook(weights, np.zeros(10), np.arange(10))
    assert structural_mask(rulebook, _genome(k=3)) == (7, 2, 5)
    random = structural_mask(rulebook, _genome(k=3), tuple(reversed(range(10))))
    assert random == (9, 8, 7)


def test_nominee_selection_freezes_strongest_and_simplest() -> None:
    strong = _genome("strong", 10)
    simple = _genome("simple", 3)
    weak = _genome("weak", 5)
    validation = {
        strong.name: {
            "genome": strong.to_dict(),
            "risk_gain": 0.20,
            "split_half_reliability": 0.90,
            "acquisition_rate": 0.90,
        },
        simple.name: {
            "genome": simple.to_dict(),
            "risk_gain": 0.10,
            "split_half_reliability": 0.80,
            "acquisition_rate": 0.90,
        },
        weak.name: {
            "genome": weak.to_dict(),
            "risk_gain": 0.01,
            "split_half_reliability": 1.0,
            "acquisition_rate": 1.0,
        },
    }
    selection = select_nominees(validation)
    assert selection["eligible"]
    assert [value["name"] for value in selection["nominees"]] == ["strong", "simple"]


def test_local_study_is_worker_invariant_and_replayable(tmp_path) -> None:
    base = local_confirmation_spec((_genome(),), smoke=True)
    spec = replace(base, source_count=1)
    one = run_local_study(spec, tmp_path / "one", 1)
    two = run_local_study(spec, tmp_path / "two", 2)
    assert verify_local_study(one)["records"] == expected_local_records(spec)
    assert sha256_file(one / "futures.jsonl.gz") == sha256_file(two / "futures.jsonl.gz")
    record = next(read_jsonl_gz(one / "futures.jsonl.gz"))
    assert record["expression_reset"] is True
    assert replay_local_future(one, record["future_id"])["matches"]
    assert read_json(one / "analysis.json")["carrier_target_access"] is False


def test_search_smoke_contract_is_small() -> None:
    spec = local_search_spec(smoke=True)
    spec.validate()
    assert spec.population_size == 8
    assert spec.generations == 1
    assert spec.training_sources == 2


def test_search_smoke_seals(tmp_path) -> None:
    run = run_local_search(local_search_spec(smoke=True), tmp_path / "search", 2)
    assert verify_local_search(run)["verified"]
    assert (run / "selection.json").is_file()
