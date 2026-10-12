#!/usr/bin/env python3
"""Run Adaptive Maintenance with JSON-stable registration serialization.

The frozen scientific configuration uses tuples in memory, while registrations
read back from JSON contain lists.  Canonical JSON and protocol digests treat
those representations identically, but the campaign's legacy resume gate uses
raw Python equality.  Normalize only the two configuration serializers at the
launcher boundary so an interrupted, byte-equivalent campaign can resume.
"""

from __future__ import annotations

import json

from gre_sim.wagner_ph_cooption_config import CooptionSpec
from gre_sim.wagner_ph_maintenance_config import MaintenanceSpec


_maintenance_to_dict = MaintenanceSpec.to_dict
_cooption_to_dict = CooptionSpec.to_dict


def _json_normalize(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


def _maintenance_json_dict(self: MaintenanceSpec) -> dict[str, object]:
    value = _json_normalize(_maintenance_to_dict(self))
    assert isinstance(value, dict)
    return value


def _cooption_json_dict(self: CooptionSpec) -> dict[str, object]:
    value = _json_normalize(_cooption_to_dict(self))
    assert isinstance(value, dict)
    return value


MaintenanceSpec.to_dict = _maintenance_json_dict
CooptionSpec.to_dict = _cooption_json_dict


if __name__ == "__main__":
    from gre_sim.wagner_ph_maintenance_cli import main

    raise SystemExit(main())
