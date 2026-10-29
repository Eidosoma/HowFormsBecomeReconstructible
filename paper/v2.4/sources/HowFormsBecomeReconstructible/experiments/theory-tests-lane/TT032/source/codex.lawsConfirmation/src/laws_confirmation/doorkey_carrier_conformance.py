"""Randomized byte-for-byte differential tests for the PHRL-0 carrier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import numpy as np

from . import doorkey_carrier as numpy_carrier


def _load_reference(path: Path) -> ModuleType:
    if not path.is_file():
        raise FileNotFoundError(path)
    name = "_doorkey_reference_phrl_slot_germ"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load carrier reference: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _torch_array(tensor: Any) -> np.ndarray:
    return tensor.detach().cpu().numpy()


def run_torch_differential(
    reference_source: Path,
    *,
    trials: int = 256,
    seed: int = 2_314_640,
) -> dict[str, Any]:
    """Exercise both implementations on identical deterministic inputs."""

    if trials < 1:
        raise ValueError("trials must be positive")
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PyTorch is required for differential conformance") from error

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # PyTorch permits setting this only before inter-op work begins. The
        # launcher also constrains the process, and the observed value is
        # reported by the caller.
        pass
    reference = _load_reference(reference_source)
    numpy_schema = numpy_carrier.GermSchema()
    torch_schema = reference.GermSchema()
    schema_fields = tuple(numpy_schema.__dataclass_fields__)
    schema_equal = all(
        getattr(numpy_schema, name) == getattr(torch_schema, name)
        for name in schema_fields
    )
    rng = np.random.default_rng(seed)
    mismatches: list[dict[str, Any]] = []
    operations = {
        "empty": 0,
        "read": 0,
        "write": 0,
        "commit": 0,
        "permute": 0,
        "corrupt": 0,
    }
    max_prior_absolute_difference = 0.0

    for trial in range(trials):
        batch_size = 1 + trial % 7
        numpy_germ = numpy_carrier.empty_germ(batch_size, numpy_schema)
        torch_germ = reference.empty_germ(
            batch_size, torch_schema, torch.device("cpu")
        )
        operations["empty"] += batch_size
        if not np.array_equal(numpy_germ, _torch_array(torch_germ)):
            mismatches.append({"trial": trial, "operation": "empty"})
            continue

        # Repeated writes in one trial exercise fresh commits, agreement/aging,
        # semantic replacement, confirmation blocks, and explicit revocation.
        for round_index in range(4):
            evidence = rng.normal(
                0.0, 1.7, size=(batch_size, 4, 8)
            ).astype(np.float32)
            mode = (trial + round_index) % 4
            if mode in (0, 2):
                targets = rng.integers(0, 8, size=(batch_size, 4))
                for batch in range(batch_size):
                    for slot in range(4):
                        evidence[batch, slot, targets[batch, slot]] += np.float32(10.0)
            elif mode == 1:
                evidence *= np.float32(0.05)

            confirmation = None
            if (trial + round_index) % 3 == 0:
                confirmation = rng.random((batch_size, 4)) > 0.25
            revocation = None
            if (trial + round_index) % 5 == 0:
                revocation = rng.random((batch_size, 4)) < 0.20

            numpy_read = numpy_carrier.read_germ(numpy_germ, numpy_schema)
            torch_read = reference.read_germ(torch_germ, torch_schema)
            operations["read"] += batch_size * 4
            prior_difference = float(
                np.max(
                    np.abs(
                        numpy_read.prior_logits
                        - _torch_array(torch_read.prior_logits)
                    )
                )
            )
            max_prior_absolute_difference = max(
                max_prior_absolute_difference, prior_difference
            )
            read_equal = (
                np.array_equal(numpy_read.active, _torch_array(torch_read.active))
                and np.array_equal(
                    numpy_read.checksum_valid,
                    _torch_array(torch_read.checksum_valid),
                )
                and np.array_equal(
                    numpy_read.address_valid, _torch_array(torch_read.address_valid)
                )
                and np.array_equal(numpy_read.trust, _torch_array(torch_read.trust))
                and np.array_equal(
                    numpy_read.freshness, _torch_array(torch_read.freshness)
                )
                and prior_difference == 0.0
            )
            if not read_equal:
                mismatches.append(
                    {"trial": trial, "round": round_index, "operation": "read"}
                )

            torch_confirmation = (
                None if confirmation is None else torch.from_numpy(confirmation)
            )
            torch_revocation = (
                None if revocation is None else torch.from_numpy(revocation)
            )
            numpy_written, numpy_commit = numpy_carrier.write_germ_from_local_evidence(
                evidence,
                numpy_germ,
                numpy_schema,
                confirmation_mask=confirmation,
                revocation_mask=revocation,
            )
            torch_written, torch_commit = reference.write_germ_from_local_evidence(
                torch.from_numpy(evidence),
                torch_germ,
                torch_schema,
                confirmation_mask=torch_confirmation,
                revocation_mask=torch_revocation,
            )
            operations["write"] += batch_size * 4
            operations["commit"] += int(numpy_commit.sum())
            if not np.array_equal(numpy_commit, _torch_array(torch_commit)):
                mismatches.append(
                    {"trial": trial, "round": round_index, "operation": "commit"}
                )
            if not np.array_equal(numpy_written, _torch_array(torch_written)):
                differing = int(
                    np.count_nonzero(numpy_written != _torch_array(torch_written))
                )
                mismatches.append(
                    {
                        "trial": trial,
                        "round": round_index,
                        "operation": "write",
                        "differing_bytes": differing,
                    }
                )
            numpy_germ = numpy_written
            torch_germ = torch_written

        permutation = rng.permutation(4).astype(np.int64)
        numpy_permuted = numpy_carrier.permute_payloads(
            numpy_germ, permutation, numpy_schema
        )
        torch_permuted = reference.permute_payloads(
            torch_germ, torch.from_numpy(permutation), torch_schema
        )
        operations["permute"] += batch_size
        if not np.array_equal(numpy_permuted, _torch_array(torch_permuted)):
            mismatches.append({"trial": trial, "operation": "permute"})

        byte_index = int(rng.integers(0, 64))
        mask = int(1 << int(rng.integers(0, 8)))
        numpy_corrupted = numpy_carrier.corrupt_byte(
            numpy_permuted, byte_index, mask
        )
        torch_corrupted = reference.corrupt_byte(
            torch_permuted, byte_index, mask
        )
        operations["corrupt"] += batch_size
        if not np.array_equal(numpy_corrupted, _torch_array(torch_corrupted)):
            mismatches.append({"trial": trial, "operation": "corrupt"})

    return {
        "reference_source": str(reference_source),
        "trials": trials,
        "seed": seed,
        "schema_fields": list(schema_fields),
        "schema_equal": schema_equal,
        "operations": operations,
        "max_prior_absolute_difference": max_prior_absolute_difference,
        "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:20],
        "byte_exact": schema_equal and not mismatches,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
        "cuda_available": torch.cuda.is_available(),
    }

