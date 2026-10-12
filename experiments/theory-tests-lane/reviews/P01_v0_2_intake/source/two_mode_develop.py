"""Observable-only two-cycle development, introduced after the tabular result.

All cases and seeds are constructed development evidence. A same-structure HMM
is mathematically identical to the proposed response law and remains a tie.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

import two_mode as tm
from develop import STATUS, stamp, sha, write_once

ROOT = Path(__file__).resolve().parent


def calibrate(output):
    started = time.perf_counter()
    rng = np.random.default_rng(1730)
    # Fixed before this script's first execution; outcome-informed choice of
    # model family follows the retained first development calculation.
    cases = [dict(name="slow_loss_ready", params=[.8, .25, .99, 1., 1.]),
             dict(name="fast_loss_ready", params=[.8, .25, .92, 1., 1.]),
             dict(name="slow_loss_initially_poor_expression", params=[.8, .25, .99, .25, 1.])]
    horizons = [0, 1, 2, 4, 8, 16, 32, 64]
    result = dict(status=STATUS, created_at_utc=stamp(), seed=1730, paths_per_case=512,
                  observation_contract="512 independent two-cycle toy trajectories, three categorical readouts each; hidden states are not supplied to either estimator.",
                  calibration_depths=[0, 1, 2], horizons=horizons,
                  code_sha256={name: sha(ROOT/name) for name in ("two_mode.py", "two_mode_develop.py", "joint_kernel.py", "develop.py")},
                  cases=[])
    for case in cases:
        probability = tm.pattern_probabilities(case["params"])
        counts = rng.multinomial(512, probability)
        fit = tm.fit_patterns(counts)
        # Preserve the original seed and explicitly retain unsupported rows.
        # This handling was added after the retained first calibration failure.
        try:
            init, markov = tm.output_markov(counts)
            markov_forecasts = [list(init @ np.linalg.matrix_power(markov, h)) for h in horizons]
            markov_status = "FITTED"
        except ValueError as error:
            markov_forecasts = None
            markov_status = "UNSUPPORTED: " + str(error)
        result["cases"].append(dict(**case, counts=counts.tolist(), fit=fit,
            forecasts=tm.distributions(fit["params"], horizons).tolist(),
            ordinary_output_markov_status=markov_status,
            ordinary_output_markov_forecasts=markov_forecasts,
            ordinary_structured_hmm_forecasts=tm.distributions(fit["params"], horizons).tolist()))
    result["elapsed_seconds"] = time.perf_counter()-started
    write_once(output, result)
    print(json.dumps(dict(output=str(output), status=STATUS, seconds=result["elapsed_seconds"])))


def evaluate(calibration, output):
    frozen = json.loads(Path(calibration).read_text())
    for name, checksum in frozen["code_sha256"].items():
        if sha(ROOT/name) != checksum:
            raise ValueError("Code changed after observable toy freeze: "+name)
    report = dict(status=STATUS, created_at_utc=stamp(), calibration_sha256=sha(calibration),
                  interpretation="Three constructed cases and one sampling realization each. No confidence interval, empirical superiority claim, or native-system validation.", cases=[])
    horizons = frozen["horizons"]
    unseen_depths = np.array(horizons) > 2
    for case in frozen["cases"]:
        truth = tm.distributions(case["params"], horizons)
        errors = {}
        for name in ("forecasts", "ordinary_output_markov_forecasts", "ordinary_structured_hmm_forecasts"):
            if case[name] is None:
                errors[name] = dict(status=case["ordinary_output_markov_status"])
                continue
            estimate = np.asarray(case[name])
            errors[name] = dict(rmse_target_A=float(np.sqrt(np.mean((estimate[unseen_depths, 0]-truth[unseen_depths, 0])**2))),
                                max_absolute_category_error=float(np.max(np.abs(estimate[unseen_depths]-truth[unseen_depths]))))
        identified = tm.exact_moment_identification(tm.distributions(case["params"], [0, 1, 2]))
        h32 = horizons.index(32)
        report["cases"].append(dict(name=case["name"], true_params=case["params"], fitted_params=case["fit"]["params"],
            exact_inversion_max_error=float(np.max(np.abs(np.asarray(identified)-case["params"]))),
            h32=dict(truth=truth[h32].tolist(), forecast=case["forecasts"][h32],
                     ordinary_output_markov=(case["ordinary_output_markov_forecasts"][h32]
                         if case["ordinary_output_markov_forecasts"] is not None else None)),
            errors_over_horizons_greater_than_two=errors,
            successful_optimizer_starts=sum(a["success"] for a in case["fit"]["attempts"])))
    write_once(output, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["calibrate", "evaluate"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--calibration", type=Path)
    args = p.parse_args()
    if args.phase == "calibrate": calibrate(args.output)
    else: evaluate(args.calibration, args.output)
