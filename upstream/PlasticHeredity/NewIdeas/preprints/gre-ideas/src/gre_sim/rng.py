"""Stable, worker-count-independent random stream derivation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np


def seed_for(master_seed: str, *parts: Any) -> int:
    """Derive a 128-bit seed from semantic stream coordinates."""

    payload = json.dumps(
        [master_seed, *parts], sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=16).digest(), "big")


def rng_for(master_seed: str, *parts: Any) -> np.random.Generator:
    return np.random.Generator(np.random.Philox(seed_for(master_seed, *parts)))


def digest_parts(*parts: Any, size: int = 16) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.blake2b(payload, digest_size=size).hexdigest()

