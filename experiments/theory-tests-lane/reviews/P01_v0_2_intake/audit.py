"""Independent scalar probability checks of the received draft; no native claim."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE/'source'
sys.path.insert(0, str(SOURCE))
import two_mode as tm

STATES = list(itertools.product((0, 1), repeat=2))
EMIT = (2, 0, 2, 1)
HORIZONS = (0, 1, 2, 3, 4, 8, 16, 32, 64)


def scalar_model(theta):
    pi, mu, lam, r0, chi = map(float, theta)
    flip = (1-lam)/2
    lose, recover = (1-pi)*(1-mu), pi*(1-mu)
    initial = [((1+chi)/2 if identity == 0 else (1-chi)/2)*
        (r0 if ready else 1-r0) for identity, ready in STATES]
    matrix = []
    for identity, ready in STATES:
        row = []
        for new_identity, new_ready in STATES:
            identity_probability = 1-flip if identity == new_identity else flip
            ready_probability = (1-lose if new_ready else lose) if ready else (recover if new_ready else 1-recover)
            row.append(identity_probability*ready_probability)
        matrix.append(row)
    return initial, matrix


def scalar_probabilities(theta):
    initial, matrix = scalar_model(theta)
    patterns = [0.]*27
    for a, b, c in itertools.product(range(4), repeat=3):
        patterns[9*EMIT[a]+3*EMIT[b]+EMIT[c]] += initial[a]*matrix[a][b]*matrix[b][c]
    state = initial
    marginal = {}
    for h in range(max(HORIZONS)+1):
        if h in HORIZONS:
            marginal[h] = [sum(state[i] for i in range(4) if EMIT[i] == value) for value in range(3)]
        state = [sum(state[i]*matrix[i][j] for i in range(4)) for j in range(4)]
    return np.array(patterns), marginal


def loss(theta, counts):
    probability, _ = scalar_probabilities(theta)
    support = counts > 0
    return float(-sum(float(counts[i])*np.log(max(float(probability[i]), 1e-15))
                      for i in np.flatnonzero(support))/counts.sum())


def main():
    output = HERE/'audit_v1'
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    try:
        snapshot = json.loads((SOURCE/'snapshot.json').read_text())
        for record in snapshot['files']:
            digest = hashlib.sha256((SOURCE/record['path']).read_bytes()).hexdigest()
            assert digest == record['sha256'], record['path']
        parameters = list(itertools.product((0., .3, 1.), (0., .5, 1.), (0., .7, 1.), (0., .4, 1.), (-1., 0., 1.)))
        rng = np.random.default_rng(2026100803)
        interior = np.column_stack((rng.uniform(.05, .95, (100, 4)), rng.uniform(.2, .9, 100)))
        parameters += interior.tolist()
        max_pattern_error = 0.; max_marginal_error = 0.
        for theta in parameters:
            p, marginals = scalar_probabilities(theta)
            reference = tm.pattern_probabilities(theta)
            np.testing.assert_allclose(p, reference, rtol=0, atol=2e-13)
            assert abs(sum(p)-1) < 2e-13
            max_pattern_error = max(max_pattern_error, float(np.max(np.abs(p-reference))))
            for h in HORIZONS:
                predicted = tm.distributions(theta, [h])[0]
                np.testing.assert_allclose(marginals[h], predicted, rtol=0, atol=2e-13)
                max_marginal_error = max(max_marginal_error, float(np.max(np.abs(marginals[h]-predicted))))
        inversion_cases = 0
        for theta in interior:
            if abs(theta[0]-theta[3]) < 1e-3:
                continue
            _, marginal = scalar_probabilities(theta)
            recovered = tm.exact_moment_identification([marginal[h] for h in (0, 1, 2)])
            np.testing.assert_allclose(recovered, theta, rtol=0, atol=1e-10)
            inversion_cases += 1
        forecasts = json.loads((SOURCE/'results/observable_forecasts_v1.json').read_text())
        seed = np.random.default_rng(forecasts['seed'])
        cases = []
        for case in forecasts['cases']:
            counts = np.array(case['counts'])
            probability, truth = scalar_probabilities(case['params'])
            np.testing.assert_array_equal(seed.multinomial(forecasts['paths_per_case'], probability), counts)
            theta = case['fit']['params']
            recorded_loss = case['fit']['average_negative_log_likelihood']
            independent_loss = loss(theta, counts)
            assert abs(independent_loss-recorded_loss) < 1e-12
            _, fitted_marginal = scalar_probabilities(theta)
            for h, saved in zip(forecasts['horizons'], case['forecasts'], strict=True):
                np.testing.assert_allclose(fitted_marginal[h], saved, rtol=0, atol=2e-13)
            fitted_again = tm.fit_patterns(counts)
            np.testing.assert_allclose(fitted_again['params'], theta, rtol=0, atol=1e-10)
            assert abs(fitted_again['average_negative_log_likelihood']-recorded_loss) < 1e-12
            # Predeclared coordinate perturbations are an optimizer diagnostic,
            # not a confidence region or a proof of global optimality.
            best = independent_loss; witness = None
            for column, delta, sign in itertools.product(range(5), (1e-5, 1e-3, 1e-2), (-1, 1)):
                perturbed = list(theta)
                perturbed[column] = float(np.clip(theta[column]+sign*delta, -1 if column == 4 else 0, 1))
                value = loss(perturbed, counts)
                if value < best:
                    best, witness = value, perturbed
            cases.append(dict(name=case['name'], counts_reproduced=True, fit_reproduced=True,
                independent_negative_log_likelihood=independent_loss,
                true_h32_A=truth[32][0], forecast_h32_A=fitted_marginal[32][0],
                h32_A_error=fitted_marginal[32][0]-truth[32][0],
                identity_mode_at_boundary=bool(theta[2] == 1.),
                local_perturbation_loss_improvement=independent_loss-best,
                local_perturbation_issue=independent_loss-best > 1e-6,
                improving_witness=witness))
        report = dict(status='PASS', scope='Scalar probability/path-likelihood checks and deterministic toy-fit replay. No native validation or external replication.',
            utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-started,
            package_files_verified=len(snapshot['files']), parameter_cases=len(parameters),
            marginal_vectors_checked=len(parameters)*len(HORIZONS), exact_inversion_cases=inversion_cases,
            max_pattern_absolute_difference=max_pattern_error, max_marginal_absolute_difference=max_marginal_error,
            cases=cases, audit_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            source_snapshot_sha256=hashlib.sha256((SOURCE/'snapshot.json').read_bytes()).hexdigest())
        with (output/'AUDIT.json').open('x') as f:
            json.dump(report,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
        print(json.dumps(report), flush=True)
    except BaseException:
        with (output/'FAILED.json').open('x') as f:
            json.dump({'status':'FAILED','traceback':traceback.format_exc()},f,indent=2)
        raise


if __name__ == '__main__':
    main()
