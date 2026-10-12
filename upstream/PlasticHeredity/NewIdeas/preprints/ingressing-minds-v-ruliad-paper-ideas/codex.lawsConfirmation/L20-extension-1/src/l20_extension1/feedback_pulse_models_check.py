"""D173 independent forecast, raw-tie, SVD and score reconstruction."""
import numpy as np
from . import settings_prediction_check as independent
from .feedback_pulse_models import ALPHAS, OBSERVERS

same = independent.same


def matrices(data):
    a, first = data['start'], data['u0']
    return {'starting': a.copy(), 'one_copy': np.concatenate([a, first], axis=3),
            'tied:passive': np.concatenate([a, first, data['u1']], axis=3),
            'tied:pulse': np.concatenate([a, first, data['pulse']], axis=3)}


def check_fits(data, predictions, raw, fits):
    n = len(data['block_ids']); ids = data['block_ids']
    assert set(predictions) == set(raw) == set(fits) == set(OBSERVERS)
    x = matrices(data)
    y = np.sum(data['futures'], axis=3).reshape(n * 16) / 4
    g = np.tile(np.array([0, 1, 2, 3], np.int64), n * 4)
    owners = np.repeat(np.arange(n), 16)
    worst_svd = worst_tie = worst_gradient = 0.
    checked = 0
    for name in OBSERVERS:
        record = fits[name]; tied = name.startswith('tied:')
        assert set(record) == {'observer', 'blocks', 'alphas', 'target', 'folds'}
        same({k: v for k, v in record.items() if k != 'folds'},
             dict(observer=name, blocks=ids.tolist(), alphas=list(ALPHAS), target='future_mean'))
        assert len(record['folds']) == n
        assert predictions[name].shape == raw[name].shape == (3, n, 4, 4)
        np.testing.assert_array_equal(predictions[name], np.maximum(-1, np.minimum(1, raw[name])))
        X = x[name].reshape(n * 16, -1)
        for block, fold in enumerate(record['folds']):
            train, test = owners != block, owners == block
            assert set(fold) == {'validation_block', 'training_blocks', 'models'}
            assert fold['validation_block'] == int(ids[block]) and fold['training_blocks'] == np.delete(ids, block).tolist()
            assert len(fold['models']) == 3
            for i, alpha in enumerate(ALPHAS):
                model = fold['models'][i]
                _, gradient, tie, _ = independent.verify_model(model, X[train], y[train], g[train], X[test], g[test],
                    raw[name][i, block].ravel(), alpha, tied, False)
                solution, expected = independent.svd_solution(X[train], y[train], g[train], X[test], g[test], alpha, tied)
                for key, value in solution.items():
                    if key != 'reduced_coefficients' or tied:
                        same(model[key], value)
                same(raw[name][i, block].ravel(), expected)
                worst_svd = max(worst_svd, float(abs(raw[name][i, block].ravel() - expected).max()))
                worst_gradient = max(worst_gradient, gradient)
                worst_tie = max(worst_tie, tie)
                checked += 1
    return dict(passes=True, models_checked=checked, independent_group_svd=True,
        max_prediction_residual=worst_svd, max_raw_tie_residual=worst_tie,
        max_projected_gradient=worst_gradient, all_whole_founders_retained=True)


def check_summary(data, predictions, raw, summary, losses):
    n = len(data['block_ids']); futures = data['futures']; mean_y = np.sum(futures, -1) / 4
    assert set(losses) == set(OBSERVERS)
    absolute, case = {}, {}
    for name in OBSERVERS:
        rows, square = [], []
        for i, alpha in enumerate(ALPHAS):
            error = predictions[name][i, ..., None] - futures
            sq = np.sum(error * error, -1) / 4
            square.append(sq)
            mse = float(np.sum(sq) / (n * 16))
            block = [float(np.sum(sq[b]) / 16) for b in range(n)]
            group = [float(np.sum(sq[:, :, g]) / (n * 4)) for g in range(4)]
            mean_loss = float(np.sum((predictions[name][i] - mean_y)**2) / (n * 16))
            dispersion = float(np.sum((futures - mean_y[..., None])**2) / (n * 64))
            assert abs(mse - mean_loss - dispersion) <= 2e-12
            rows.append(dict(alpha=alpha, mse=mse, mae=float(np.sum(abs(error)) / (n * 64)),
                rmse_points=float(100 * np.sqrt(mse)), bias=float(np.sum(error) / (n * 64)),
                block_mse=block, group_mse=group, mean_target_mse=mean_loss, future_dispersion=dispersion,
                clipped=int(np.count_nonzero(predictions[name][i] != raw[name][i]))))
        absolute[name], case[name] = rows, np.stack(square)
        same(losses[name], case[name])

    def pair(c, r, ci, ri, selected=False):
        gain = case[r][ri] - case[c][ci]
        blocks = [float(np.sum(gain[b]) / 16) for b in range(n)]
        total = sum(blocks) / n; denominator = absolute[r][ri]['mse']
        mean_gain = np.mean((predictions[r][ri] - mean_y)**2 - (predictions[c][ci] - mean_y)**2)
        assert abs(total - mean_gain) <= 2e-12
        return dict(candidate=c, reference=r, candidate_alpha=ALPHAS[ci], reference_alpha=ALPHAS[ri],
            gain=total, percent_mse_reduction=100 * total / denominator if denominator else None,
            block_gains=blocks, group_gains=[float(np.sum(gain[:, :, g]) / (n * 4)) for g in range(4)],
            positive=sum(v > 0 for v in blocks), negative=sum(v < 0 for v in blocks), zero=sum(v == 0 for v in blocks),
            score_only_omit_gains=[sum(blocks[:b] + blocks[b+1:]) / (n - 1) for b in range(n)], selection_affected_context=selected)

    pairs = [('tied:pulse', 'tied:passive'), ('tied:pulse', 'starting'), ('tied:pulse', 'one_copy'),
             ('tied:passive', 'starting'), ('tied:passive', 'one_copy'), ('one_copy', 'starting')]
    selection = {}
    for name in ('starting', 'one_copy'):
        values = [row['mse'] for row in absolute[name]]
        selection[name] = max(i for i, value in enumerate(values) if value <= min(values) + 1e-12)
    expected = dict(schema='d173_feedback_pulse_prediction_v1', blocks=data['block_ids'].tolist(),
        alphas=[.001, .01, .1], observers=list(OBSERVERS), focal=['tied:pulse', 'tied:passive', .01],
        absolute=absolute, comparisons=[pair(c, r, i, i) for i in range(3) for c, r in pairs],
        selected_cheap_alphas={k: ALPHAS[v] for k, v in selection.items()},
        selected_cheap_comparisons=[pair(c, r, 1, selection[r], True) for c in ('tied:pulse', 'tied:passive') for r in ('starting', 'one_copy')],
        target='four_future_mean', cases=n * 16, prospective_evidence=False, confidence_intervals=False,
        equivalence_test=False, deployment_selected=False, automatic_successor=False)
    same(summary, expected)
    return dict(passes=True, absolute_rows=12, paired_rows=18, selection_affected_rows=4,
        individual_future_mean_gain_identity=True, whole_founder_score_omissions=True)
