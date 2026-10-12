from __future__ import annotations

from gre_sim.plastic_memory_analysis import analyze_memory_records
from gre_sim.plastic_memory_protocols import quick_spec


def _record(
    source: str,
    history: str,
    half: str,
    future_index: int,
    carrier: str,
    correct: bool,
) -> dict[str, object]:
    return {
        "future_id": f"{source}.{history}.{half}.{future_index}.{carrier}",
        "condition": "synthetic-adversarial",
        "midpoint_index": 0,
        "model": "boolean-quick",
        "cue_fraction": 1.0,
        "cue_dwell": 2,
        "mark_setting": "none",
        "carrier": carrier,
        "washout_age": 0,
        "challenge": "neutral_damage",
        "history": history,
        "source_id": source,
        "half": half,
        "future_index": future_index,
        "acquired": True,
        "correct_hold8": correct,
        "wrong_hold8": False,
        "generic_hold8": correct,
        "returned": correct,
        "form_destination": history if carrier != "destination_matched_donor" else "other",
        "descriptor_exact": True,
        "trace_digest": f"{source}.{history}.{half}.{future_index}",
    }


def test_worse_donor_cannot_manufacture_a_state_transfer_gate() -> None:
    records = []
    for source_index in range(8):
        source = f"source-{source_index}"
        correct = source_index % 4 != 0
        for history in ("A", "B"):
            for half, future_index in (("A", 0), ("B", 2)):
                records.extend(
                    (
                        _record(source, history, half, future_index, "self_continuation", correct),
                        _record(source, history, half, future_index, "state_transplant", correct),
                        _record(source, history, half, future_index, "reset_both", correct),
                        _record(
                            source,
                            history,
                            half,
                            future_index,
                            "destination_matched_donor",
                            False,
                        ),
                    )
                )
    analysis = analyze_memory_records(records, quick_spec())
    gate = analysis["state_transfer_gates"]["boolean-quick"]
    assert gate["metrics"]["risk_difference"]["mean"] == 0.0
    assert not gate["criteria"]["risk_difference_at_least_0_05"]
    assert not gate["passed"]
