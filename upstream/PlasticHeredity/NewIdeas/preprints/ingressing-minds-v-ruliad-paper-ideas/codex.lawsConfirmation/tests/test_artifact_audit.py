import numpy as np

from laws_confirmation.artifact_audit import _compare_string_fields, _field_matches


def test_field_matches_normalizes_numpy_booleans():
    assert _field_matches(
        {"gate": np.bool_(False)},
        {"gate": False},
        ("gate",),
    ) == {"gate": True}


def test_missing_string_field_is_reported_not_counted_as_mismatch():
    result = _compare_string_fields(
        [{"rule": "1", "library_size": "0"}],
        [{"rule": "1", "support_masks": ""}],
        ("rule",),
        "library",
        "support_masks",
    )
    assert result["available"] is False
    assert result["n_common"] == 1
    assert "exact_matches" not in result
