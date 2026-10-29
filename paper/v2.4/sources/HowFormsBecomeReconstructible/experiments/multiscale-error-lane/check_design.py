"""Check synthetic mathematics/design only; does not qualify native dynamics."""
from pathlib import Path
import hashlib
import json
import itertools
import numpy as np

from operators import LEVELS, block_projection, error_bands, offline_scores, sensing_then_action, spatial_operator, shifted_operator

ROOT = Path(__file__).resolve().parent


def main():
    design = json.loads((ROOT / "design.json").read_text())
    assert not design["frozen"] and design["scientific_runs"] == 0
    assert design["resources"]["allocated_cpus"] == 12
    assert design["resources"]["cpu_first"]
    assert design["me001_draft"]["source_cases"] == 16 * 4 * 2
    assert np.zeros((16, 16), dtype=np.float64).nbytes == design["model"]["packet_bytes"]

    x = np.random.Generator(np.random.PCG64(20261024)).normal(size=(16, 16)) + 0.4
    original = x.copy()
    bands = error_bands(x)
    np.testing.assert_allclose(sum(bands.values()), x, atol=1e-12, rtol=0)
    for a, b in itertools.combinations(bands.values(), 2):
        assert abs(float(np.sum(a * b))) < 1e-10
    np.testing.assert_allclose(sum(np.sum(a * a) for a in bands.values()), np.sum(x * x), atol=1e-10, rtol=0)
    for size in (1, 4, 8, 16):
        p = block_projection(x, size)
        np.testing.assert_allclose(block_projection(p, size), p, atol=1e-12, rtol=0)
    assert abs(float(spatial_operator(x, "sheet").mean())) < 1e-12
    np.testing.assert_array_equal(x, original)

    # Verify all nine compositions, and expose duplicate mathematical maps.
    classes = []
    for s, a in itertools.product(LEVELS, repeat=2):
        out = sensing_then_action(x, s, a)
        for group in classes:
            if np.allclose(out, group["output"], atol=1e-12, rtol=0):
                group["pairs"].append([s, a])
                break
        else:
            classes.append({"output": out, "pairs": [[s, a]]})
    assert len(classes) == 3
    # This one-field check accompanies the analytic nested-projection identity;
    # it is not an empirical proof of a native-dynamics intervention effect.

    for level in ("region", "sheet"):
        before = spatial_operator(shifted_operator(x, level), level)
        after = shifted_operator(spatial_operator(x, level), level)
        assert np.linalg.norm(before - after) > 1e-6
    np.testing.assert_allclose(spatial_operator(shifted_operator(x, "sheet", (4, 4)), "sheet"), 0, atol=1e-12, rtol=0)

    target = np.ones((16, 16))
    strong, weak, wrong = [offline_scores(np.full((16, 16), v), target) for v in (1.0, 0.1, -1.0)]
    assert strong["sign_percent"] == weak["sign_percent"] == 100
    assert strong["qualified_percent"] == 100 and weak["qualified_percent"] == 0
    assert wrong["amplitude_percent"] == 100 and wrong["sign_percent"] == 0
    assert offline_scores(np.full((16, 16), 0.2), target)["amplitude_percent"] == 0
    for score in (strong, weak, wrong):
        assert np.sum(score["joint_counts_match_by_eligible"]) == 256
        assert score["qualified_percent"] == 100 * score["joint_counts_match_by_eligible"][1][1] / 256

    # Same accessible state, opposite evaluated histories: no hidden target input.
    rows, columns = np.indices((16, 16))
    X = np.where(columns < 8, 1.0, -1.0)
    Y = np.where(rows < 8, 1.0, -1.0)
    assert offline_scores(X, X)["sign_percent"] > offline_scores(Y, X)["sign_percent"]
    assert offline_scores(X, Y)["sign_percent"] < offline_scores(Y, Y)["sign_percent"]

    report = {
        "status": "PASS_SYNTHETIC_ONLY",
        "native_dynamics_qualified": False,
        "controller_interface_qualified": False,
        "scientific_runs": 0,
        "checks": ["packet_size", "12_cpu_configuration", "orthogonal_error_decomposition",
                   "projection_idempotence", "nonmutating_operators", "three_alias_classes",
                   "one_site_noncommuting_placement", "half_quadrant_annihilation",
                   "sign_amplitude_intersection", "strict_amplitude_threshold",
                   "indistinguishable_state_example"],
        "operator_alias_classes": [g["pairs"] for g in classes],
        "numpy_version": np.__version__,
        "source_sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
                          for n in ["operators.py", "check_design.py", "design.json"]}
    }
    destination = ROOT / "checks" / "synthetic_design_v1.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "scientific_runs": 0,
                      "alias_classes": len(classes), "receipt": str(destination)}))


if __name__ == "__main__":
    main()
