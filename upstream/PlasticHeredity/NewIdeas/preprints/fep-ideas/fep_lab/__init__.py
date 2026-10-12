"""Known-positive Markov-blanket and active-inference laboratory."""

from .config import LabConfig, profile_config
from .homeostat import HomeostatEnvironment, build_homeostat_model
from .reference import ReferenceBackend
from .types import Action, CategoricalModel

__all__ = [
    "Action",
    "CategoricalModel",
    "HomeostatEnvironment",
    "LabConfig",
    "ReferenceBackend",
    "build_homeostat_model",
    "profile_config",
]

__version__ = "0.1.0"
