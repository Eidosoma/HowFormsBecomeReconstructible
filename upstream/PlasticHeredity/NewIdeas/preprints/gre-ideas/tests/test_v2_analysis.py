from __future__ import annotations

import collections
import copy
from dataclasses import replace

from gre_sim.analysis import (
    RegistryContexts,
    _hierarchical_probabilities,
    _smoothed_probabilities,
    _tune_shrinkage_kappa,
)
from gre_sim.campaign import build_registry
from gre_sim.config import StudySpec


def test_zero_shrinkage_exactly_reproduces_audit_committor() -> None:
    categories = ("point:0", "point:1", "off_library")
    counts = collections.Counter({"point:0": 3, "point:1": 1})
    prior = {"point:0": 0.2, "point:1": 0.3, "off_library": 0.5}
    assert _hierarchical_probabilities(counts, prior, categories, 0.5, 0.0) == (
        _smoothed_probabilities(counts, categories, 0.5)
    )


def test_nested_shrinkage_excludes_heldout_source_and_ties_choose_zero() -> None:
    spec = replace(
        StudySpec.quick_v2(), engines=("boolean",), cohorts=("sampled",)
    )
    registry = build_registry(spec)
    prototype = registry["sources"][0]
    sources = []
    for source_id in ("heldout", "mapping-1", "mapping-2"):
        bundle = copy.deepcopy(prototype)
        bundle["source_id"] = source_id
        sources.append(bundle)
    synthetic_registry = {**registry, "sources": sources}
    contexts = RegistryContexts(synthetic_registry)

    records = []
    for bundle in sources:
        point_label = next(
            attractor.label
            for attractor in contexts.get(bundle["source_id"], 0, "natural").landscape.attractors
            if attractor.kind == "point"
        )
        for state_id in (0, 1):
            for future_index in (0, 1):
                records.append(
                    {
                        "engine": "boolean",
                        "cohort": "sampled",
                        "source_id": bundle["source_id"],
                        "state_id": state_id,
                        "arm": "natural",
                        "carryover": 1.0,
                        "inheritance_mode": "self",
                        "future_index": future_index,
                        "half": "A",
                        "destination": point_label,
                    }
                )
    heldout = next(record for record in records if record["source_id"] == "heldout")
    assert _tune_shrinkage_kappa(heldout, records, contexts, spec) == 0.0

    changed = copy.deepcopy(records)
    for record in changed:
        if record["source_id"] == "heldout":
            record["destination"] = "nonconvergent"
    assert _tune_shrinkage_kappa(heldout, changed, contexts, spec) == 0.0
