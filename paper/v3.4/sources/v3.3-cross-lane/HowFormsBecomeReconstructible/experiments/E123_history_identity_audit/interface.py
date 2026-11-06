"""Explicit retained-array boundary; labels and grouping never enter observers."""
from __future__ import annotations

import hashlib
import numpy as np

CHECKPOINTS = (1, 3, 8, 16)
ROUTES = (("own", 0), ("foreign", 1), ("protected_own", 7))
INPUT_SETS = {
    "setup": (), "record": ("R",), "body": ("B",),
    "joint": ("R", "B"), "outgoing": ("O",),
    "body_postwrite": ("B_postwrite",),
}


def content_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def decode(packet, factor):
    packet = np.asarray(packet)
    if factor not in (1, 4) or packet.dtype != np.uint8 or packet.shape[-1] != 2048 // factor**2:
        raise ValueError("Invalid native packet")
    low = np.frombuffer(packet.tobytes(), dtype="<f8").reshape(*packet.shape[:-1], 16 // factor, 16 // factor)
    if not np.isfinite(low).all():
        raise ValueError("Nonfinite packet")
    return low.repeat(factor, axis=-2).repeat(factor, axis=-1)


def encode(field, factor):
    field = np.asarray(field)
    if field.dtype != np.float64 or field.shape[-2:] != (16, 16):
        raise ValueError("Native float64 field required")
    low = field if factor == 1 else field.reshape(*field.shape[:-2], 4, 4, 4, 4).mean(axis=(-3, -1))
    if factor not in (1, 4):
        raise ValueError("Undeclared factor")
    return np.ascontiguousarray(low, dtype="<f8").view(np.uint8).reshape(*field.shape[:-2], -1).copy()


def joint_counts(v, dictionary):
    """Counts in [candidate, sign flag, amplitude flag]; no decoder decisions."""
    v, dictionary = np.asarray(v), np.asarray(dictionary)
    if v.shape[-2:] != (16, 16) or dictionary.shape != (4, 16, 16):
        raise ValueError("Wrong coordinate frame")
    if not np.isfinite(v).all() or not np.isfinite(dictionary).all():
        raise ValueError("Nonfinite native fields")
    sign = (v[..., None, :, :] > 0) == (dictionary > 0)
    amplitude = np.abs(v[..., None, :, :]) > .2
    result = np.empty((*v.shape[:-2], 4, 2, 2), dtype=np.uint16)
    for s in (0, 1):
        for a in (0, 1):
            result[..., s, a] = ((sign == s) & (amplitude == a)).sum(axis=(-2, -1))
    assert np.all(result.sum(axis=(-2, -1)) == 256)
    return result


def make_payload(raw, block, factor, boundary):
    """Development fixture only. All metadata are returned separately."""
    if boundary not in ("checkpoint", "lifecycle"):
        raise ValueError(boundary)
    selected = ROUTES if boundary == "checkpoint" else ROUTES[:2]
    payload = {"A_background": raw["background"].copy(), "D": raw["prototype"].copy(),
               "A_factor": np.array(factor, dtype=np.int64)}
    series = {k: [] for k in ("R", "B", "birth", "challenge_mask")}
    if boundary == "lifecycle":
        series.update({k: [] for k in ("O", "B_postwrite", "written_field")})
    rows = []
    for h, g in enumerate(CHECKPOINTS):
        for f in range(4):
            for r in range(2):
                for route, a in selected:
                    idx = (h if boundary == "checkpoint" else g - 1, f, r, a)
                    if boundary == "checkpoint":
                        series["R"].append(raw["checkpoint_packets"][idx])
                        series["B"].append(raw["checkpoint_read"][idx])
                        birth, mask = raw["checkpoint_birth"][h, f, r, 0], raw["checkpoint_mask"][h, f, r]
                    else:
                        series["R"].append(raw["incoming"][idx])
                        series["B"].append(raw["generation_read"][idx])
                        series["O"].append(raw["outgoing"][idx])
                        written = raw["generation_written"][idx]
                        series["B_postwrite"].append(written[:3])
                        series["written_field"].append(written[3])
                        birth, mask = raw["generation_birth"][g-1, f, r, 0], raw["generation_mask"][g-1, f, r]
                    series["birth"].append(birth); series["challenge_mask"].append(mask)
                    key = f"E014:{block}:{factor}:{boundary}:{g}:{f}:{r}:{route}"
                    rows.append(dict(row=len(rows), case_id=hashlib.sha256(key.encode()).hexdigest()[:24],
                        source_block_id=block, factor=factor, packet_bytes=2048//factor**2,
                        boundary=boundary, horizon=g, founder_slot=f, recipient=r, condition=route,
                        historical_donor=(f+1)%4 if route=="foreign" else f, native_target=f,
                        candidate_dictionary_id=f"E014:{block}:four_founders",
                        candidate_labels=[0,1,2,3], exposure_status="development_interface_post_hoc",
                        applied_challenge=False))
    payload.update({k: np.stack(v) for k,v in series.items()})
    return payload, rows


def observer_inputs(payload, row, input_set):
    """Whitelist only. No labels, IDs, counts, filenames, masks or RNG seeds."""
    if input_set not in INPUT_SETS:
        raise ValueError("Unknown input set")
    if not 0 <= row < len(payload["R"]):
        raise IndexError(row)
    out = {k: payload[k].copy() for k in ("A_background", "A_factor", "D")}
    for key in INPUT_SETS[input_set]:
        if key not in payload:
            raise ValueError(f"{key} absent at this boundary; cannot invent outgoing state")
        out[key] = payload[key][row].copy()
    return out
