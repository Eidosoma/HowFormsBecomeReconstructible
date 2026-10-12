import json
from pathlib import Path

import numpy as np

from laws_confirmation.eca_sim import (
    LineageContract,
    _update_observer_batch,
    build_domain_dictionary,
    eca_step,
    event_bernoulli_mask,
    evaluate_condition,
    final4_counts,
    hash_launch_row,
    trajectory_key,
)


def _scalar_step(row: np.ndarray, rule: int) -> np.ndarray:
    width = len(row)
    return np.array(
        [
            bool(
                (rule >> (4 * int(row[index - 1]) + 2 * int(row[index]) + int(row[(index + 1) % width])))
                & 1
            )
            for index in range(width)
        ],
        dtype=np.bool_,
    )


def _hex_row(value: str, width: int = 64) -> np.ndarray:
    integer = int(value, 16)
    return np.array(
        [bool((integer >> (width - 1 - index)) & 1) for index in range(width)],
        dtype=np.bool_,
    )


def test_vector_step_matches_independent_scalar_reference_at_odd_and_even_widths():
    rng = np.random.default_rng(20260902)
    for width in (9, 16, 63, 64, 65):
        rows = rng.integers(0, 2, size=(4, width), dtype=np.uint8).astype(bool)
        for rule in (0, 18, 35, 90, 110, 204, 255):
            expected = np.stack([_scalar_step(row, rule) for row in rows])
            np.testing.assert_array_equal(eca_step(rows, rule), expected)


def test_rule_and_spectrum_kernels_replay_all_disclosed_e19_golden_sweeps():
    workspace = Path(__file__).resolve().parents[1]
    fixture_path = (
        workspace.parent
        / "codex.reconstructionsAndStressTesting/plastic_ca/data/e19_golden_traces.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    sweep_checks = 0
    spectrum_checks = 0
    for rule_text, settings in fixture["traces"].items():
        rule = int(rule_text)
        for setting in settings.values():
            for generation in setting["generations"]:
                row = _hex_row(generation["start_row_hex"])[None, :]
                masks = generation["process_masks_nonzero"]
                for sweep, expected_hex in enumerate(
                    generation["rows_hex_per_sweep"], start=1
                ):
                    row = eca_step(row, rule)
                    row ^= _hex_row(masks.get(str(sweep), "0"))[None, :]
                    np.testing.assert_array_equal(row[0], _hex_row(expected_hex))
                    sweep_checks += 1
                expected_counts = np.array(
                    generation["final4_counts_of_64"], dtype=np.float64
                )
                np.testing.assert_array_equal(final4_counts(row)[0], expected_counts)
                spectrum_checks += 1
    assert sweep_checks == 907
    assert spectrum_checks == 15


def test_four_mer_census_has_exact_width_mass():
    rows = np.array(
        [[0, 1, 0, 1, 1, 0, 0], [1, 1, 1, 0, 0, 0, 1]],
        dtype=np.bool_,
    )
    counts = final4_counts(rows)
    np.testing.assert_array_equal(counts.sum(axis=1), np.array([7.0, 7.0]))


def test_launch_rows_are_domain_separated_and_non_monochrome():
    first = hash_launch_row("benchmark-one", "benchmark", 7, 65)
    repeated = hash_launch_row("benchmark-one", "benchmark", 7, 65)
    other = hash_launch_row("benchmark-two", "benchmark", 7, 65)
    np.testing.assert_array_equal(first, repeated)
    assert not np.array_equal(first, other)
    assert first.any() and not first.all()


def test_counter_masks_are_reproducible_and_future_order_independent():
    futures = np.array([5, 1, 9], dtype=np.int64)
    together = event_bernoulli_mask(
        12345, futures, 2, 7, 64, 0.2, kind="process"
    )
    repeated = event_bernoulli_mask(
        12345, futures, 2, 7, 64, 0.2, kind="process"
    )
    np.testing.assert_array_equal(together, repeated)
    for row, future in zip(together, futures, strict=True):
        alone = event_bernoulli_mask(
            12345, np.array([future]), 2, 7, 64, 0.2, kind="process"
        )
        np.testing.assert_array_equal(row, alone[0])
    assert not np.array_equal(
        together,
        event_bernoulli_mask(12345, futures, 2, 7, 64, 0.2, kind="copy"),
    )


def test_counter_masks_have_the_requested_bernoulli_marginal():
    mask = event_bernoulli_mask(
        8675309,
        np.arange(2048, dtype=np.int64),
        4,
        11,
        64,
        0.2,
        kind="process",
    )
    assert abs(float(mask.mean()) - 0.2) < 0.005


def test_vector_observer_update_reaches_strict_only_after_later_recovery_run():
    contract = LineageContract(
        width=8,
        flip_noise=0.0,
        copy_error=0.0,
        n_launches=1,
        futures_per_launch=2,
        namespace="unit-benchmark-observer",
        launch_split="benchmark",
        horizon=11,
        strict_run=8,
    )
    compositions = np.zeros((2, 11, 16), dtype=np.float64)
    lengths = np.zeros(2, dtype=np.int16)
    first_break = np.full(2, -1, dtype=np.int16)
    broke_by_8 = np.zeros(2, dtype=np.bool_)
    strict_positive = np.zeros(2, dtype=np.bool_)
    a = np.eye(16)[0]
    b = np.eye(16)[1]
    c = np.eye(16)[2]
    for generation in range(11):
        first = a if generation == 0 else b if generation == 1 else c
        observed = np.stack((first, a))
        _update_observer_batch(
            compositions,
            lengths,
            first_break,
            broke_by_8,
            strict_positive,
            np.array([0, 1]),
            generation,
            observed,
            contract,
        )
        if generation < 10:
            assert not strict_positive[0]
    assert first_break.tolist() == [0, -1]
    assert broke_by_8.tolist() == [True, False]
    assert strict_positive.tolist() == [True, False]


def test_small_condition_runs_at_nonstandard_width():
    contract = LineageContract(
        width=11,
        flip_noise=0.01,
        copy_error=0.015,
        n_launches=2,
        futures_per_launch=3,
        namespace="unit-benchmark-trajectory",
        launch_split="benchmark",
        activity_budget=11,
        min_sweeps=2,
        max_sweeps=8,
        horizon=5,
        break_horizon=3,
        strict_run=2,
    )
    assert trajectory_key(110, 0, contract) == trajectory_key(110, 0, contract)
    result = evaluate_condition(110, contract, observer="raw4")
    assert result.n_futures == 6
    assert result.total_sweeps > 0
    assert len(result.launches) == 2


def test_particle_dictionary_is_deterministic_and_width_bounded():
    kwargs = {
        "rule": 110,
        "width": 13,
        "namespace": "unit-benchmark-domain",
        "n_seeds": 4,
        "burnin": 3,
        "collect": 2,
        "cap": 16,
    }
    first = build_domain_dictionary(**kwargs)
    second = build_domain_dictionary(**kwargs)
    assert first == second
    assert 0.0 <= first.coverage <= 1.0
    assert len(first.codes) <= 16
    assert all(0 <= code < 512 for code in first.codes)
