from __future__ import annotations

import os

from fep_surprise.campaign import confirm, develop, register, replay, status
from fep_surprise.config import profile_config
from fep_surprise.validation import validate


def test_campaign_uses_a_headless_matplotlib_backend() -> None:
    import matplotlib
    import matplotlib.pyplot as plt

    figure = plt.figure()
    assert matplotlib.get_backend().lower() == "agg"
    plt.close(figure)


def test_complete_smoke_campaign_replays_exactly(tmp_path) -> None:
    config = profile_config("smoke")
    register(tmp_path, config)
    validation = validate(config, tmp_path / "smoke" / "validation")
    assert validation["all_pass"]
    develop(tmp_path, config, workers=1)
    confirmation = confirm(tmp_path, config, workers=1)
    replay_bundle = replay(tmp_path, config)
    assert (confirmation / "metrics.json").is_file()
    assert (confirmation / "REPORT.md").is_file()
    assert (replay_bundle / "replay.json").is_file()
    state = status(tmp_path, "smoke")
    assert state["development"]["sealed"]
    assert state["confirmation"]["sealed"]
    assert state["replay"]["sealed"]


def test_status_reports_detached_process_liveness(tmp_path) -> None:
    output = tmp_path / "full"
    output.mkdir()
    (output / "full-run.status").write_text("running\n")
    (output / "full-run.pid").write_text(f"{os.getpid()}\n")
    (output / "full-run.session").write_text("test-session\n")
    (output / "full-run.started").write_text("2026-08-18T00:00:00Z\n")

    state = status(tmp_path, "full")

    assert state["detached_run_status"] == "running"
    assert state["detached_run_pid"] == str(os.getpid())
    assert state["detached_run_alive"] is True
    assert state["detached_run_session"] == "test-session"
    assert state["detached_run_started"] == "2026-08-18T00:00:00Z"


def test_status_rejects_invalid_pid(tmp_path) -> None:
    output = tmp_path / "full"
    output.mkdir()
    (output / "full-run.pid").write_text("not-a-pid\n")

    assert status(tmp_path, "full")["detached_run_alive"] is False
