from __future__ import annotations

from pathlib import Path

from gre_sim.artifacts import read_json, verify_checksums
from gre_sim.plastic_memory_evolution import (
    MemoryEvolutionSpec,
    quick_evolution_spec,
    run_memory_evolution,
)


def test_quick_memory_evolution_checkpoints_and_seals(tmp_path: Path) -> None:
    spec = quick_evolution_spec()
    assert MemoryEvolutionSpec.from_dict(spec.to_dict()) == spec
    destination = tmp_path / "evolution"
    run_memory_evolution(spec, destination, workers=2)
    verify_checksums(destination)
    analysis = read_json(destination / "analysis.json")
    assert len(analysis["cells"]) == 3
    assert read_json(destination / "manifest.json")["populations"] == 3
    run_memory_evolution(spec, destination, workers=1)

