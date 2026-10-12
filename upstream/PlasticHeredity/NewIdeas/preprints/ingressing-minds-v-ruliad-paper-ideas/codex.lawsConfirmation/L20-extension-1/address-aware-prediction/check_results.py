"""Read-only rendering/checking of D171's audited results; optional external receipt.

No fitting, predictor selection, new statistics or simulation entry point.
The table patch is printed for apply_patch; this script never writes local docs.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from l20_extension1 import settings_prediction_run as run
from laws_confirmation.io import sha256_file, utc_now

HERE = Path(__file__).resolve().parent
COMPLETE = '41a9fa1d8d63bdcdfab971b5470ab614bf4d2b13cd3a73555a8f239130db51d4'
AUDIT = 'eb5b76b5d456fe8054a16e3de4270152158bef8f7437cae58a9f8123cae5fab2'
ALPHAS = (.001, .01, .1)
OBSERVERS = ('starting', 'one_copy', 'tied:passive', 'tied:shuffle',
             'tied:attenuate', 'tied:sham_plus', 'tied:sham_minus')
VERSIONS = ('old', 'settings')
GROUPS = ('A ordinary', 'A aligned', 'B ordinary', 'B aligned')


def source():
    freeze = run.checked_freeze(); timing = run.checked_timing()
    folder = run.ROOT / 'runs' / run.RUN; out = run.ROOT / 'outputs' / run.RUN
    assert sha256_file(folder / 'COMPLETE.json') == COMPLETE
    done = run.read_json(folder / 'COMPLETE.json')
    assert done['status'] == 'COMPLETE' and not (folder / 'FAILED.json').exists()
    assert sha256_file(folder / 'MANIFEST.json') == done['manifest_sha256']
    assert sha256_file(out / 'output_hashes.json') == done['hash_index_sha256']
    assert run.read_json(out / 'output_hashes.json') == done['output_sha256']
    run.verify_hashes(done['output_sha256'])
    ap = run.ROOT / 'logs' / (run.RUN + '_saved_audit_v1.json')
    assert sha256_file(ap) == AUDIT
    audit = run.read_json(ap)
    assert audit['passes'] and audit['complete_sha256'] == COMPLETE
    run.check.same(audit['verification'], done['verification'])
    summary = run.read_json(out / 'summary.json')
    losses = run.load_npz(out / 'case_losses.npz')
    assert summary['blocks'] == list(range(90000, 90016))
    assert summary['new_fits'] == 336 and summary['new_predictions'] == 5376
    assert not summary['prospective_evidence'] and not summary['confidence_intervals']
    assert len(summary['absolute']) == 14 and len(summary['comparisons']) == 93
    for k, rows in summary['absolute'].items():
        for i, row in enumerate(rows):
            assert losses[k][i].shape == (16, 4, 4)
            np.testing.assert_allclose(row['block_mse'], losses[k][i].mean((1, 2)), atol=1e-14, rtol=0)
            np.testing.assert_allclose(row['group_mse'], losses[k][i].mean((0, 1)), atol=1e-14, rtol=0)
            assert abs(row['mse'] - losses[k][i].mean()) < 1e-14
            assert abs(row['mse'] - row['mean_target_mse'] - row['irreducible_future_variance']) < 1e-14
    for row in summary['comparisons']:
        i = ALPHAS.index(row['alpha'])
        gain = losses[row['reference']][i] - losses[row['candidate']][i]
        np.testing.assert_allclose(row['block_gains'], gain.mean((1, 2)), atol=1e-14, rtol=0)
        assert abs(row['mse_reduction'] - gain.mean()) < 1e-14
    return summary, done, audit, freeze, timing


def comparison(s, candidate, reference, alpha=.01):
    rows = [r for r in s['comparisons'] if (r['candidate'], r['reference'], r['alpha']) == (candidate, reference, alpha)]
    assert len(rows) == 1
    return rows[0]


def facts(s):
    interface = [comparison(s, 'settings/' + k, 'old/' + k, a) for k in OBSERVERS for a in ALPHAS]
    degradation = [-100 * r['mse_reduction'] / s['absolute'][r['reference']][ALPHAS.index(r['alpha'])]['mse'] for r in interface]
    before = comparison(s, 'old/tied:sham_minus', 'old/tied:passive')
    after = comparison(s, 'settings/tied:sham_minus', 'settings/tied:passive')
    gap = next(r for r in s['gap_changes'] if r['challenge'] == 'tied:sham_minus' and r['alpha'] == .01)
    selected = [r for r in s['selected_cheap_comparisons'] if r['candidate'] == 'settings/tied:sham_minus']
    return dict(all_21_settings_extensions_worse=all(x > 0 for x in degradation),
        degradation_percent_range=[min(degradation), max(degradation)],
        all_336_score_only_omissions_still_worse=all(max(r['score_only_omit_gains']) < 0 for r in interface),
        focal_old_gain_percent=100 * before['mse_reduction'] / s['absolute']['old/tied:passive'][1]['mse'],
        focal_new_gain_percent=100 * after['mse_reduction'] / s['absolute']['settings/tied:passive'][1]['mse'],
        focal_new_gain_mse=after['mse_reduction'], focal_change_in_gain_mse=gap['mse_reduction'],
        focal_positive_blocks=after['positive_blocks'], focal_negative_blocks=after['negative_blocks'],
        focal_score_only_omission_range=[min(after['score_only_omit_gains']), max(after['score_only_omit_gains'])],
        focal_selected_cheap_gains_percent={r['reference']: 100 * r['mse_reduction'] /
            s['cheap_selection_context'][r['reference']]['metrics']['mse'] for r in selected},
        focal_group_gains=after['group_gains'], clipped_predictions=sum(v['clipped'] for rows in s['absolute'].values() for v in rows))


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
                     + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]) + '\n'


def f(x): return format(x, '.10g')
def vector(values): return ', '.join(f(v) for v in values)


def render(s):
    text = ['# D171 — complete saved-data result tables\n',
        '2026-09-23. Development only, not prospective confirmation. [Interpretation](RESULTS.md), '
        '[protocol](EXECUTION_PROTOCOL_V1.md), [table checker](check_results.py).\n',
        'Every founder 90000–90015, four lives, four public groups and four saved futures is retained. '
        'Lower absolute error is better. A positive gain is reference MSE minus candidate MSE. '
        'Relative gains use the named reference at that alpha. MSE is in native target units squared; '
        'MAE/RMSE/bias are preference points (100 times target units). Old = no diagnostic settings; '
        'settings = the same two effective settings supplied to every observer. '
        'Residual-minus is the focal challenge, not a newly selected winner.\n',
        'All omission ranges and vectors below are score-only omissions of fixed out-of-fold forecasts, '
        'not deletion refits or confidence intervals. Cheap-baseline alpha selection is explicitly '
        'selection-affected development context. No p-values, equivalence or deployment selection.\n']
    absolute = [(v + '/' + name, a, s['absolute'][v + '/' + name][i])
                for v in VERSIONS for name in OBSERVERS for i, a in enumerate(ALPHAS)]
    text += ['## Absolute errors — all 42 settings\n', table(
        ['Observer', 'Alpha', 'Individual-future MSE', 'Mean-target MSE', 'MAE points', 'RMSE points', 'Bias points', 'Clipped / 256'],
        [(k, a, f(r['mse']), f(r['mean_target_mse']), f(r['mae_points']), f(r['rmse_points']), f(r['bias_points']), r['clipped']) for k, a, r in absolute])]
    text += ['## All public groups\n', table(['Observer', 'Alpha', 'Group', 'MSE', 'MAE points', 'RMSE points', 'Bias points', 'Clipped / 64'],
        [(k, a, GROUPS[j], f(r['group_mse'][j]), f(r['group_mae_points'][j]), f(100 * np.sqrt(r['group_mse'][j])),
          f(r['group_bias_points'][j]), r['group_clipped'][j]) for k, a, r in absolute for j in range(4)])]
    text += ['## Four individual futures\n',
        'The same within-case future dispersion, ' + f(absolute[0][2]['irreducible_future_variance']) +
        ', separates individual-future and mean-target MSE for every predictor. '
        'This is an accounting identity for these four saved outcomes, not a universal noise-floor claim.\n',
        table(['Observer', 'Alpha', 'Future 0 MSE', 'Future 1 MSE', 'Future 2 MSE', 'Future 3 MSE'],
              [(k, a, *(f(x) for x in r['future_mse'])) for k, a, r in absolute])]
    text += ['## All 93 fixed paired comparisons\n', table(
        ['Candidate', 'Reference', 'Alpha', 'MSE gain', 'Gain % reference', '+ / − / zero founders', 'Omit min MSE gain', 'Omit max MSE gain'],
        [(r['candidate'], r['reference'], r['alpha'], f(r['mse_reduction']),
          f(100 * r['mse_reduction'] / s['absolute'][r['reference']][ALPHAS.index(r['alpha'])]['mse']),
          f"{r['positive_blocks']} / {r['negative_blocks']} / {r['zero_blocks']}",
          f(min(r['score_only_omit_gains'])), f(max(r['score_only_omit_gains']))) for r in s['comparisons']])]
    text += ['## Challenge/passive gap changes after adding settings\n',
        'Raw new gap minus raw old gap, without changing percentage denominators. Positive means the challenge/passive gap increased.\n',
        table(['Challenge', 'Alpha', 'Change in MSE gain', 'A ordinary', 'A aligned', 'B ordinary', 'B aligned', '+ / − founders', 'Omit min', 'Omit max'],
        [(r['challenge'], r['alpha'], f(r['mse_reduction']), *(f(x) for x in r['group_gains']),
          f"{r['positive_blocks']} / {r['negative_blocks']}", f(min(r['score_only_omit_gains'])), f(max(r['score_only_omit_gains']))) for r in s['gap_changes']])]
    text += ['## Cheap baselines — own selected alpha, selection-affected context\n', table(
        ['Baseline', 'Selected alpha', 'MSE', 'MAE points', 'RMSE points'],
        [(k, r['alpha'], f(r['metrics']['mse']), f(r['metrics']['mae_points']), f(r['metrics']['rmse_points']))
         for k, r in s['cheap_selection_context'].items()])]
    text += ['## Focal-alpha diagnostic models versus selected cheap baselines\n', table(
        ['Candidate at .01', 'Cheap reference', 'Reference alpha', 'MSE gain', 'Gain % reference', '+ / − founders', 'Omit min', 'Omit max'],
        [(r['candidate'], r['reference'], r['reference_alpha'], f(r['mse_reduction']),
          f(100 * r['mse_reduction'] / s['cheap_selection_context'][r['reference']]['metrics']['mse']),
          f"{r['positive_blocks']} / {r['negative_blocks']}", f(min(r['score_only_omit_gains'])), f(max(r['score_only_omit_gains'])))
         for r in s['selected_cheap_comparisons']])]
    text += ['## Complete founder loss vectors\n',
        'Each vector is ordered 90000, 90001, …, 90015. Full-precision MAE/bias vectors are also preserved in the audited summary.\n',
        table(['Observer', 'Alpha', 'Individual-future founder MSE vector', 'Mean-target founder MSE vector'],
              [(k, a, vector(r['block_mse']), vector(r['block_mean_target_mse'])) for k, a, r in absolute])]
    text += ['## Complete paired founder/group gains and omission vectors\n',
        'Founder order is 90000–90015; group order is A ordinary, A aligned, B ordinary, B aligned. '
        'The last vector omits the corresponding founder from scoring only.\n',
        table(['Candidate', 'Reference', 'Alpha', 'Founder gain vector', 'Group gain vector', 'Score-only omission vector'],
              [(r['candidate'], r['reference'], r['alpha'], vector(r['block_gains']), vector(r['group_gains']), vector(r['score_only_omit_gains']))
               for r in s['comparisons']])]
    text += ['## Provenance\n',
        'External numeric source: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/' + run.RUN + '/summary.json` '
        'and `case_losses.npz`. All full-precision vectors, including gap-change and selected-cheap founder/omission vectors, remain there. '
        'No unreported condition or founder is removed.\n',
        'COMPLETE SHA-256: `' + COMPLETE + '`. Independent saved-audit SHA-256: `' + AUDIT + '`.\n']
    return '\n'.join(text)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--table-patch', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    s, done, audit, freeze, timing = source()
    if args.table_patch:
        print('*** Begin Patch\n*** Add File: ' + str(HERE / 'TABLES.md') + '\n' +
              '\n'.join('+' + line for line in render(s).splitlines()) + '\n*** End Patch')
        return
    assert (HERE / 'TABLES.md').read_text() == render(s), 'saved tables differ from audited numbers'
    links = []
    documents = [HERE / name for name in ('RESULTS.md', 'TABLES.md', 'README.md', 'WORKLOG.md')]
    for path in documents:
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent / link.split('#')[0]).resolve().is_file(), (path, link)
                links.append([str(path), link])
    result = dict(passes=True, checked_utc=utc_now(), complete_sha256=COMPLETE, audit_sha256=AUDIT,
        source_inputs_checked=len(freeze['input_sha256']), table_numeric_rows=sum(x.startswith('|') for x in render(s).splitlines()) - 18,
        local_links_checked=len(links), documentation_sha256=run.hashes(documents + [Path(__file__)]),
        facts=facts(s), new_fits=0, new_forecasts=0, new_dynamics=0, prospective_evidence=False,
        automatic_successor=False)
    if args.receipt:
        run.write_json(args.receipt, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
