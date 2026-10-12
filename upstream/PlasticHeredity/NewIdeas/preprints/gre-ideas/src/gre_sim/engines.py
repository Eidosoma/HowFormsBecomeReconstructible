"""Cross-engine helpers and serialization."""

from __future__ import annotations

from typing import Any, TypeAlias

from .boolean import BooleanRulebook
from .wagner import WagnerRulebook


Rulebook: TypeAlias = BooleanRulebook | WagnerRulebook


def engine_name(rulebook: Rulebook) -> str:
    if isinstance(rulebook, BooleanRulebook):
        return "boolean"
    if isinstance(rulebook, WagnerRulebook):
        return "wagner"
    raise TypeError(f"unsupported rulebook: {type(rulebook)!r}")


def rulebook_from_dict(value: dict[str, Any]) -> Rulebook:
    if value.get("engine") == "boolean":
        return BooleanRulebook.from_dict(value)
    if value.get("engine") == "wagner":
        return WagnerRulebook.from_dict(value)
    raise ValueError(f"unknown rulebook engine: {value.get('engine')!r}")

