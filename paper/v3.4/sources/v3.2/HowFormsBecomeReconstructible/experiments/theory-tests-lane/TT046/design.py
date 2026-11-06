"""Minimal source-recipe adapter; no outcome-dependent selection."""
from common import FAMILIES,GEOMETRIES,ROLES
STRATA=GEOMETRIES
def families(role):
    assert role in ROLES
    return FAMILIES
