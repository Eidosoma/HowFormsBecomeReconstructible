"""Independent scalar construction checks for D183; no production import."""

import hashlib
import math

import numpy as np


NAMES = ("own", "partner", "own_scrambled", "partner_scrambled", "history_erased")


def exact(left, right):
    assert left.dtype == right.dtype and left.shape == right.shape
    assert left.tobytes() == right.tobytes()


def check(theta, kept, fresh, residual, tissue, replicates, constructed):
    assert set(constructed) == {"common", "residual", "fresh", "partners", "permutations"} | {
        f"body_{name}" for name in NAMES}
    n = 4 * replicates
    for value in (theta, kept, residual):
        assert value.shape == (n, 16, 16) and value.dtype == np.float64 and np.isfinite(value).all()
    assert fresh.dtype == bool and fresh.shape == kept.shape
    exact(constructed["fresh"], fresh)
    exact(constructed["residual"], residual)
    indices = np.asarray([((i // replicates + 2) % 4) * replicates + i % replicates for i in range(n)])
    exact(constructed["partners"], indices)
    seed = int.from_bytes(hashlib.sha256(f"l22-active-form-boundary-v1:{tissue}:shuffle".encode()).digest()[:16], "little")
    generator = np.random.default_rng(seed)
    permutations = np.asarray([generator.permutation(128) for _ in range(replicates)])
    exact(constructed["permutations"], permutations)
    for i, j in enumerate(indices):
        assert fresh[i].sum() == 128
        exact(fresh[i], fresh[j])
        exact(kept[i][fresh[i]], kept[j][fresh[j]])
        left = min(i, int(j))
        right = max(i, int(j))
        mean = [(float(x) + float(y)) / 2 for x, y in zip(theta[left].flat, theta[right].flat)]
        center = math.fsum(mean) / 256
        shifted = [v - center for v in mean]
        scale = math.sqrt(math.fsum(v * v for v in shifted) / 256)
        assert scale > 1e-9
        expected = np.asarray([v * (.3 / scale) for v in shifted]).reshape(16, 16)
        common = constructed["common"]
        assert common.dtype == np.float64 and common.shape == kept.shape
        assert np.isfinite(common).all()
        np.testing.assert_allclose(common[i], expected, rtol=0., atol=2e-13)
        exact(common[i], common[j])
        for name in NAMES:
            value = constructed[f"body_{name}"]
            assert value.dtype == np.float64 and value.shape == kept.shape and np.isfinite(value).all()
            exact(value[i][fresh[i]], kept[i][fresh[i]])
            mask = ~fresh[i]
            origin = kept[j if name.startswith("partner") else i][mask]
            if name == "history_erased":
                wanted = np.zeros(128, dtype=np.float64)
            elif name.endswith("scrambled"):
                wanted = np.asarray([origin[int(k)] for k in permutations[i % replicates]])
            else:
                wanted = origin
            exact(value[i][mask], wanted)
            if name.endswith("scrambled"):
                exact(np.sort(value[i][mask]), np.sort(origin))
    return dict(passes=True, records=n, unordered_pairs=n // 2,
                exact_common_packets=True, identical_fresh_fill=True,
                value_matched_scrambles=True, new_dynamics=0)


def check_initial(boundary, body, packet, initial):
    assert set(initial) == {"V", "ema", "R", "theta"}
    exact(initial["V"], boundary[f"body_{body}"])
    exact(initial["theta"], boundary[packet])
    exact(initial["R"], np.zeros_like(initial["V"]))
    exact(initial["ema"], np.zeros_like(initial["V"]))

