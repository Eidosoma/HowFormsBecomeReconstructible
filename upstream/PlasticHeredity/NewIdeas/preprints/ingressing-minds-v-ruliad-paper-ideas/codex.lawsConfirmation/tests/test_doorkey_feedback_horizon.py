import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_feedback_horizon import (
    PRIOR_SCOUT_RUN,
    qualify_prior_scout,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prior_scout_gate_checks_workspace_source_and_output_hashes(tmp_path):
    workspace = Path(__file__).resolve().parents[1]
    source = Path(__file__).resolve()
    prior = tmp_path / "scout.json"
    prior.write_text(
        json.dumps({"completed_cleanly": True, "run_id": PRIOR_SCOUT_RUN}),
        encoding="utf-8",
    )
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(
        json.dumps({"input_sha256": {str(source): _sha256(source)}}),
        encoding="utf-8",
    )
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("frozen\n", encoding="utf-8")
    hashes = tmp_path / "output_hashes.sha256"
    hashes.write_text(f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8")

    passing = qualify_prior_scout(workspace, prior, manifest, hashes)
    assert passing["passes"], passing

    artifact.write_text("changed\n", encoding="utf-8")
    failing = qualify_prior_scout(workspace, prior, manifest, hashes)
    assert not failing["passes"]
    assert not failing["gates"]["all_prior_output_hashes_verify"]
