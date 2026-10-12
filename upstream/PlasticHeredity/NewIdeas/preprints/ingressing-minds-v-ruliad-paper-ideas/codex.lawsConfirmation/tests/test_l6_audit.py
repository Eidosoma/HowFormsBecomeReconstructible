import json
from pathlib import Path

from laws_confirmation.competence_math import recalculate_grafts
from laws_confirmation.l6_audit import (
    E29_HISTORICAL_FUTURES,
    _recursive_close,
    source_config_digests,
)


IDEAS = Path(__file__).resolve().parents[2]


def test_l6_source_config_digests_match_retained_defaults():
    assert source_config_digests() == {
        "morpho_gps": "2b95f98e2ae2eb2f092cf8a1f46868ba4879f093e88027513f02d3bbe9ffc4fc",
        "collective_decision": "df5a1aa7256335390c18260a60ebe704c0d445e229547a2a093f50d3d2166a93",
        "setpoint_rewrite": "48ac009655861e57fbcf6da4c08c982092f43910ed7828b170436dbf7391eee1",
    }


def test_e29_replay_contract_counts_only_historical_futures():
    assert E29_HISTORICAL_FUTURES == 80 * 4 * 32


def test_retained_e32_counts_and_failed_gates_recalculate():
    entries = []
    work = IDEAS / "collective_decision/results/full/work"
    for path in sorted(work.glob("graft_shard_*_of_04.json")):
        entries.extend(json.loads(path.read_text(encoding="utf-8"))["entries"])
    summary = json.loads(
        (IDEAS / "collective_decision/results/full/graft_summary.json").read_text(
            encoding="utf-8"
        )
    )
    result = recalculate_grafts(entries, draws=64)
    assert _recursive_close(result["source_projection"], summary["gates"])
    assert result["overall"]["resolved"] == 195
    assert result["overall"]["unresolved"] == 1341
    assert result["overall"]["chimeras"] == 0
    assert result["source_projection"]["gate_depth_wins"] is False
    assert result["source_projection"]["gate_share_ladder"] is False
    assert result["source_projection"]["gate_chimeras"] is False
