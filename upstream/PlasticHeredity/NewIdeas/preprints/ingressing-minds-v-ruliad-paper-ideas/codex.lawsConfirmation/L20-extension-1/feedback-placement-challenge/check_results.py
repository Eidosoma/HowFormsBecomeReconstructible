"""D174 audited-result rendering and document checks; no fits or dynamics.

Prints a Markdown table patch for apply_patch, never writes local documents.
An optional write-once receipt goes only to the external study root.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from l20_extension1 import feedback_pulse_development_run as run

HERE = Path(__file__).resolve().parent
PINS = {
    run.freeze_path(): 'd0e7e0a784d19c3a42da9325c3ce129f88e7592c2cb384c5186427ce1af1a66b',
    run.timing_path(): '4bc9f52a00f1f96438057a1be5297d00ab150daad13864c81df48965ca11def9',
    run.run_dir() / 'COMPLETE.json': '97c1a81a18a6186f4dfc3ddb22eaff81a6f707275a78fb0732ab3c188937ccea',
    run.audit_path(): 'ac8b1b3d7841beb9744817b6b83742d5365765d9a6217fcf0fcfe9b673840815',
    run.output_dir() / 'panel/summary.json': 'f83033a3ff4e5501b9a2acd134ab6fc23361c65cbc8aefd95e0dae57eb2cc5cb',
}
ALPHAS = (.001, .01, .1)
OBSERVERS = ('starting', 'one_copy', 'tied:passive', 'tied:pulse')
GROUPS = ('A ordinary', 'A aligned', 'B ordinary', 'B aligned')
RECEIPT = run.ROOT / 'logs' / (run.RUN + '_results_documentation_v1.json')


def source():
    run.io.verify_hashes({str(p): h for p, h in PINS.items()})
    frozen = run.frozen(); run.timing(); done = run.completed()
    audit = run.io.read_json(run.audit_path())
    assert audit['passes'] and not run.audit_path().with_suffix('.failed.json').exists()
    assert audit['complete_sha256'] == PINS[run.run_dir() / 'COMPLETE.json']
    assert audit['freeze_sha256'] == PINS[run.freeze_path()]
    assert not audit['production_simulator_called'] and not audit['production_fitter_called']
    assert audit['new_real_fits'] == audit['new_actual_lineages'] == 0
    assert not audit['automatic_successor']
    assert [row['index'] for row in audit['physical']] == list(run.dev.IDS)
    assert all(row['passes'] and row['full_physics_replayed'] for row in audit['physical'])
    assert sum(row['writer_paths'] for row in audit['physical']) == audit['independent_writer_paths'] == 512
    assert sum(row['reader_paths'] for row in audit['physical']) == audit['independent_reader_paths'] == 1024
    assert sum(row['original_U1_reproductions'] for row in audit['physical']) == 256
    assert max(row['maximum_state_residual'] for row in audit['physical']) == 0
    run.dev.model_check.same(audit['models'], done['verification'])
    run.dev.verify_seal(run.output_dir(), 'development', PINS[run.freeze_path()], frozen['input_sha256'])
    directory = run.output_dir() / 'panel'
    summary = run.io.read_json(directory / 'summary.json')
    predictions = run.dev.load_npz(directory / 'predictions.npz')
    raw = run.dev.load_npz(directory / 'raw_predictions.npz')
    losses = run.dev.load_npz(directory / 'case_losses.npz')
    target = run.dev.load_npz(run.ROOT / 'outputs' / run.io.OLD157 / 'dataset.npz', ('block_ids', 'futures'))
    assert target['block_ids'].tolist() == list(run.dev.IDS) and target['futures'].shape == (16, 4, 4, 4)
    proof = run.dev.model_check.check_summary(target, predictions, raw, summary, losses)
    run.dev.model_check.same(proof, audit['models']['scores'])
    assert summary['focal'] == ['tied:pulse', 'tied:passive', .01]
    assert not summary['prospective_evidence'] and not summary['confidence_intervals']
    assert not summary['equivalence_test'] and not summary['deployment_selected']
    future_mse = {k: ((p[..., None] - target['futures']) ** 2).mean((1, 2, 3)) for k, p in predictions.items()}
    return summary, done, audit, frozen, future_mse


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
        + ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows]) + '\n'


def fmt(value): return format(value, '.12g')


def render(summary, future_mse):
    text = ['# D174 — complete audited development tables\n',
        '[Interpretation](RESULTS.md), [protocol](DEVELOPMENT_PROTOCOL_V1.md), [checker](check_results.py).\n',
        'All 16 founders (90000–90015), four lives, four public groups and four saved futures are retained. '
        'Starting-only has no diagnostic copy; one-copy uses U0; passive uses U0/U1; pulse uses U0/P1. '
        'Focal remains pulse versus passive at alpha .01. These are development results, not a fresh test.\n',
        'Lower absolute errors are better. MSE is squared native preference, not survival percentage. '
        'MAE, RMSE and bias are preference points (100 times native preference). '
        'Positive paired gain means reference MSE minus candidate MSE: a candidate improvement. '
        'Relative gain divides by the named reference MSE. No forecast clipped.\n',
        'All single-founder omissions below omit only scores of fixed out-of-fold predictions; '
        'they are not refits, exclusions, confidence intervals or independent experiments. '
        'Selected cheap-baseline settings are explicitly selection-affected development context.\n']
    rows = [(k, alpha, summary['absolute'][k][i]) for k in OBSERVERS for i, alpha in enumerate(ALPHAS)]
    text += ['## Absolute errors — all 12 settings\n', table(
        ['Observer', 'Alpha', 'MSE', 'Mean-target MSE', 'MAE points', 'RMSE points', 'Bias points', 'Clipped / 256'],
        [(k, a, fmt(r['mse']), fmt(r['mean_target_mse']), fmt(100*r['mae']), fmt(r['rmse_points']),
          fmt(100*r['bias']), r['clipped']) for k, a, r in rows])]
    text += ['## Group MSE — all groups and settings\n', table(['Observer', 'Alpha', *GROUPS],
        [(k, a, *(fmt(x) for x in r['group_mse'])) for k, a, r in rows])]
    text += ['## Individual saved futures\n',
        'Individual-future MSE equals mean-target MSE plus the common within-case dispersion '
        + fmt(rows[0][2]['future_dispersion']) + '. This exact saved-sample identity is not a universal noise floor.\n',
        table(['Observer', 'Alpha', 'Future 0 MSE', 'Future 1 MSE', 'Future 2 MSE', 'Future 3 MSE'],
        [(k, a, *(fmt(x) for x in future_mse[k][i])) for k in OBSERVERS for i, a in enumerate(ALPHAS)])]
    comparisons = [(f'C{i+1:02}', row) for i, row in enumerate(summary['comparisons'])]
    selected = [(f'S{i+1:02}', row) for i, row in enumerate(summary['selected_cheap_comparisons'])]
    for heading, panel in [('All 18 same-alpha comparisons', comparisons),
                           ('Four selected-cheap contexts — selection affected', selected)]:
        text += ['## ' + heading + '\n', table(
            ['ID', 'Candidate', 'Reference', 'Candidate alpha', 'Reference alpha', 'MSE gain', 'Gain %', '+ / - / zero founders', 'Omit min', 'Omit max'],
            [(key, r['candidate'], r['reference'], r['candidate_alpha'], r['reference_alpha'], fmt(r['gain']),
              fmt(r['percent_mse_reduction']), f"{r['positive']} / {r['negative']} / {r['zero']}",
              fmt(min(r['score_only_omit_gains'])), fmt(max(r['score_only_omit_gains']))) for key, r in panel])]
    text += ['## Group gains — same comparison IDs\n', table(['ID', *GROUPS],
        [(key, *(fmt(x) for x in r['group_gains'])) for key, r in comparisons + selected])]
    for i, alpha in enumerate(ALPHAS):
        text += [f'## Absolute founder MSE — alpha {alpha}\n', table(['Founder', *OBSERVERS],
            [(block, *(fmt(summary['absolute'][k][i]['block_mse'][b]) for k in OBSERVERS))
             for b, block in enumerate(summary['blocks'])])]
    for heading, field in [('Founder paired gains', 'block_gains'), ('Score-only founder omissions', 'score_only_omit_gains')]:
        for panelname, panel in [(f'alpha {a}', comparisons[i*6:(i+1)*6]) for i, a in enumerate(ALPHAS)] + [('selected-cheap context', selected)]:
            text += [f'## {heading} — {panelname}\n', table(['Founder' if field == 'block_gains' else 'Omitted founder',
                *(key for key, r in panel)], [(block, *(fmt(r[field][b]) for key, r in panel))
                 for b, block in enumerate(summary['blocks'])])]
    return '\n'.join(text)


def facts(summary):
    focal = next(r for r in summary['comparisons'] if (r['candidate'], r['reference'], r['candidate_alpha']) == ('tied:pulse', 'tied:passive', .01))
    fixed = [r for r in summary['comparisons'] if (r['candidate'], r['reference']) == ('tied:pulse', 'tied:passive')]
    return dict(focal_mse_gain=focal['gain'], focal_mse_increase_percent=-focal['percent_mse_reduction'],
        pulse_worse_at_all_three_alphas=all(r['gain'] < 0 for r in fixed),
        positive_founders=focal['positive'], negative_founders=focal['negative'],
        score_omissions_reversing_focal_mean=[b for b, g in zip(summary['blocks'], focal['score_only_omit_gains']) if g > 0],
        focal_rmse_increase_points=summary['absolute']['tied:pulse'][1]['rmse_points']-summary['absolute']['tied:passive'][1]['rmse_points'],
        selected_cheap_alphas=summary['selected_cheap_alphas'],
        clipped_forecasts=sum(r['clipped'] for rows in summary['absolute'].values() for r in rows))


def check_report_tables(report, summary):
    """Check every rounded data row in the narrative, not just the appendix."""
    panels = re.findall(r'(?m)(?:^\|[^\n]*\n)+', report)
    actual = [panel.splitlines()[2:] for panel in panels]
    names = ('Starting-only', 'One-copy', 'Passive', 'Pulse')
    copies = (0, 1, 2, 2)
    rows = [[(name, copies[i], f"{r['mse']:.9f}",
              f"{100*r['mae']:.5f}", f"{r['rmse_points']:.5f}")
             for i, (name, k) in enumerate(zip(names, OBSERVERS))
             for r in [summary['absolute'][k][1]]]]
    paired = [r for r in summary['comparisons']
              if (r['candidate'], r['reference']) == ('tied:pulse', 'tied:passive')]
    assert [r['candidate_alpha'] for r in paired] == list(ALPHAS)
    rows.append([(label, f"{summary['absolute']['tied:pulse'][i]['mse']:.9f}",
                  f"{summary['absolute']['tied:passive'][i]['mse']:.9f}",
                  f"{-r['percent_mse_reduction']:.6f}%", f"{r['positive']} / {r['negative']}")
                 for i, (label, r) in enumerate(zip(('.001', '.01, focal', '.1'), paired))])
    cheap = [next(r for r in summary['selected_cheap_comparisons']
                  if (r['candidate'], r['reference']) == ('tied:pulse', k))
             for k in OBSERVERS[:2]]
    rows.append([(names[i], format(r['reference_alpha'], 'g').removeprefix('0'),
                  f"{summary['absolute'][r['reference']][ALPHAS.index(r['reference_alpha'])]['mse']:.9f}",
                  f"{-r['percent_mse_reduction']:.6f}% higher MSE")
                 for i, r in enumerate(cheap)])
    rows.append([(group, f'{gain:+.12f}') for group, gain in zip(GROUPS, paired[1]['group_gains'])])
    expected = [['| ' + ' | '.join(str(v) for v in row) + ' |' for row in panel] for panel in rows]
    assert actual == expected, 'narrative table/rounding mismatch'
    return len(expected), sum(map(len, expected))


def check(summary, done, audit, frozen, future_mse):
    expected = render(summary, future_mse)
    assert (HERE / 'TABLES.md').read_text() == expected, 'table/rounding/layout mismatch'
    report = (HERE / 'RESULTS.md').read_text()
    report_tables, report_rows = check_report_tables(report, summary)
    fact = facts(summary)
    assert fact['pulse_worse_at_all_three_alphas'] and fact['score_omissions_reversing_focal_mean'] == [90014]
    required = ('0.723964%', '0.006551446', '0.006504357', '8.09410', '8.06496', '0.02914',
        '0.590979%', '0.566790%', '90014', 'not prospective', 'not equivalence',
        '292.29', '132.76', '48,944,066', '70,801,383', '155', '39', '192', '512', '1,024')
    assert all(v in report for v in required), 'required result fact/qualification missing'
    paths = [HERE / p for p in ('RESULTS.md', 'TABLES.md', 'BIG_PICTURE.md', 'DEVELOPMENT_STATUS.md', 'README.md', 'check_results.py')]
    links = 0
    for path in paths[:-1]:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent / target.split('#')[0]).resolve().is_file(), target
                links += 1
    files = [p for p in run.artifact_files() if p != RECEIPT]
    assert len(files) == 139 and sum(p.stat().st_size for p in files) == 70801383
    numeric_rows = sum(1 for line in expected.splitlines() if line.startswith('| ') and not line.startswith('| ---')) - expected.count('## ')
    return dict(passes=True, checked_utc=run.io.utc_now(), source_sha256={str(p): h for p, h in PINS.items()},
        documentation_sha256=run.io.hashes(paths), facts=fact, input_hashes=len(frozen['input_sha256']),
        output_hashes=len(done['output_sha256']), independent_scores_reconstructed=True,
        tables=expected.count('## '), numeric_rows=numeric_rows,
        report_tables=report_tables, report_numeric_rows=report_rows, links_checked=links,
        retained_files_before_receipt=len(files), retained_bytes_before_receipt=70801383,
        new_fits=0, new_forecasts=0, new_physics=0, prospective_evidence=False, automatic_successor=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table-patch', action='store_true')
    parser.add_argument('--facts', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    summary, done, audit, frozen, future = source()
    if args.table_patch:
        assert args.receipt is None and not args.facts
        path = HERE / 'TABLES.md'; assert not path.exists()
        print('*** Begin Patch\n*** Add File: ' + str(path) + '\n' +
            '\n'.join('+' + line for line in render(summary, future).splitlines()) + '\n*** End Patch')
    elif args.facts:
        assert args.receipt is None
        print(json.dumps(facts(summary), sort_keys=True))
    else:
        result = check(summary, done, audit, frozen, future)
        if args.receipt:
            assert args.receipt == RECEIPT
            run.io.write_json(RECEIPT, result)
        print(json.dumps({k: v for k, v in result.items() if k not in ('source_sha256', 'documentation_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
