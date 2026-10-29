"""Only the injury sample size changes; native reader/writer equations are untouched."""
import hashlib
import json
import numpy as np
from it_common import P, e, require
import probes
import futures

ORIGINAL_PROBE = probes.environment
ORIGINAL_FUTURE = futures.environment


def random(namespace, stage, key, index, purpose, channel):
    require(purpose in ("writer", "evaluation") and channel in ("injury", "forcing"),
            "Undeclared random purpose/channel")
    payload = [namespace, stage, *key, int(index), purpose, channel]
    seed = int.from_bytes(hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode()).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def mask_for(namespace, stage, key, index, purpose, injury):
    available = np.flatnonzero(~e.PORTS.any(axis=0).ravel())
    require(type(injury) is int and 0 <= injury <= len(available), "Invalid injury size")
    mask = np.zeros((16, 16), bool)
    mask.ravel()[random(namespace, stage, key, index, purpose, "injury").choice(
        available, injury, replace=False)] = True
    require(int(mask.sum()) == injury and not np.any(mask & e.PORTS.any(axis=0)),
            "Injury count or protected ports changed")
    return mask


def environment(namespace, stage, key, index, purpose, regime, injury):
    require(regime in ("matched", "independent"), "Undeclared cue-noise regime")
    mask = mask_for(namespace, stage, key, index, purpose, injury)
    draws = random(namespace, stage, key, index, purpose, "forcing").standard_normal(
        (P["reader"]["read_steps"] + 1, 2, 16, 16))
    if regime == "matched":
        draws[:, 1] = draws[:, 0]
    return mask, P["reader"]["birth_sd"] * draws[0], draws[1:]


def install(injury):
    # Each task owns its process; no concurrent conditions share this module state.
    probes.environment = lambda stage, key, index, purpose, regime: environment(
        P["forcing"]["namespace"], stage, key, index, purpose, regime, injury)
    futures.environment = lambda stage, key, index, purpose, regime: environment(
        P["forcing"]["future_namespace"], stage, key, index, purpose, regime, injury)


def check_mask(mask, receipt, namespace, stage, key, index, purpose, injury):
    expected = mask_for(namespace, stage, key, index, purpose, injury)
    require(mask.dtype == np.dtype(bool) and mask.shape == (16, 16)
            and mask.tobytes() == expected.tobytes(), "Saved injury differs from declared law/stream")
    require(hashlib.sha256(mask.tobytes()).hexdigest() == receipt["sha256"]["mask"],
            "Injury receipt hash differs")


def measurement_masks(folder, row, regime, injury):
    from it_common import ev, read, parent
    count = 0
    for name in ("successor32", "direct64"):
        receipt = read(folder / (name + ".json"))
        raw = ev.load(folder / (name + ".npz"), receipt["raw_sha256"])
        for value in receipt["forcing"]:
            branch, index = value["branch"], value["probe"]
            check_mask(raw[branch + "_mask"][index], value, P["forcing"]["namespace"],
                       parent.C["stage"], row["key"], index, value["purpose"], injury)
            birth = raw[branch + "_birth"][index]
            require(hashlib.sha256(birth.tobytes()).hexdigest() == value["sha256"]["birth"],
                    "Saved birth receipt differs")
            if regime == "matched":
                require(np.array_equal(birth[0], birth[1]), "Matched birth draws differ")
            count += 1
    return count


def future_masks(folder, rows, injury, replicate):
    from it_common import ev, read, parent
    receipt = read(folder / "future.json")
    raw = ev.load(folder / "future.npz", receipt["raw_sha256"])
    expected_stage = parent.C["stage"] + f"/replicate_{replicate}"
    require(receipt["stage"] == expected_stage, "Wrong future replicate")
    expected = [(g, j, row) for g in range(15, 34) for j, row in enumerate(rows)]
    require(len(receipt["forcing"]) == len(expected), "Future forcing coverage differs")
    for value, (generation, j, row) in zip(receipt["forcing"], expected, strict=True):
        purpose = "writer" if generation < 33 else "evaluation"
        require(value["key"] == row["key"] and value["generation"] == generation
                and value["purpose"] == purpose, "Future forcing identity differs")
        check_mask(raw["mask"][generation - 15, j], value, P["forcing"]["future_namespace"],
                   expected_stage, row["key"], generation, purpose, injury)
        birth = raw["birth"][generation - 15, j]
        require(hashlib.sha256(birth.tobytes()).hexdigest() == value["sha256"]["birth"],
                "Future birth hash differs")
    return len(expected)
