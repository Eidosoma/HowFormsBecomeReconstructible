from __future__ import annotations

import pytest

pytest.importorskip("pymdp")

from fep_lab.campaign import run_all, status
from fep_lab.config import profile_config
from fep_lab.integrity import read_json


@pytest.mark.slow
def test_complete_fep_lab_smoke_campaign_replays(tmp_path) -> None:
    output = run_all(tmp_path, profile_config("smoke"))
    state = status(tmp_path, "smoke")
    replay = read_json(tmp_path / "smoke" / "replay" / "replay.json")
    metrics = read_json(output / "metrics.json")

    assert state["validation_sealed"]
    assert state["simulation_sealed"]
    assert state["replay_sealed"]
    assert state["analysis_sealed"]
    assert replay["all_exact"]
    assert metrics["verdict"] == "WORKFLOW_ONLY"
