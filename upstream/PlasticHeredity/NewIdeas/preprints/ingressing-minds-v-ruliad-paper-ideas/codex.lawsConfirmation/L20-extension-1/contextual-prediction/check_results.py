"""D176 audited report rendering/checking. No fitting or experiment launch."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from l20_extension1 import contextual_prediction_run as run

HERE = Path(__file__).resolve().parent
COMPLETE = '56b52d31df6cb945fa4e09c651f968d330ff7ba3aac006d32e53c02a66c28345'
FREEZE = 'f89912c48432ec7190c82cb7af0c22abb53bed73ce52e298e1723fd1da9f6cfb'
ALPHAS = (.001, .01, .1)
GROUPS = ('A ordinary', 'A aligned', 'B ordinary', 'B aligned')


def source():
    assert run.io.sha256_file(run.freeze_path()) == FREEZE
    assert run.io.sha256_file(run.complete_path()) == COMPLETE
    frozen = run.frozen(); done = run.io.read_json(run.complete_path()); audit = run.io.read_json(run.audit_path())
    assert done['status'] == 'COMPLETE' and audit['passes']
    assert audit['complete_sha256'] == COMPLETE and audit['freeze_sha256'] == FREEZE
    run.check.same(audit['verification'], done['verification'])
    run.io.verify_hashes(done['output_sha256'])
    summary = run.io.read_json(run.output_dir()/'summary.json')
    target = run.npz(run.ROOT/'outputs'/run.io.OLD157/'dataset.npz', ('futures', 'block_ids'))
    p, raw, _ = run.references()
    p.update(run.npz(run.output_dir()/'predictions.npz', run.model.NEW))
    raw.update(run.npz(run.output_dir()/'raw_predictions.npz', run.model.NEW))
    losses = run.npz(run.output_dir()/'case_losses.npz', run.model.KEYS)
    run.check.report(target, p, raw, summary, losses)
    return summary, done, audit, frozen


def pair(s, candidate, reference, alpha=.01):
    return next(r for r in s['comparisons'] if (r['candidate'], r['reference'], r['alpha']) == (candidate, reference, alpha))


def gain_percent(s, row):
    i = ALPHAS.index(row['alpha'])
    return 100*row['mse_reduction']/s['absolute'][row['reference']][i]['mse']


def facts(s):
    focal = pair(s, 'interaction/tied:pulse', 'interaction/tied:passive')
    old = pair(s, 'old/tied:pulse', 'old/tied:passive')
    return dict(focal_pulse_mse_increase_percent=-gain_percent(s, focal),
        focal_gain_mse=focal['mse_reduction'], helped=focal['positive_blocks'], harmed=focal['negative_blocks'],
        focal_omit_range=[min(focal['score_only_omit_gains']), max(focal['score_only_omit_gains'])],
        focal_all_16_score_omissions_negative=all(x < 0 for x in focal['score_only_omit_gains']),
        focal_rmse_increase_points=s['absolute']['interaction/tied:pulse'][1]['rmse_points']-s['absolute']['interaction/tied:passive'][1]['rmse_points'],
        pulse_loses_all_three_interaction_settings=all(pair(s, 'interaction/tied:pulse', 'interaction/tied:passive', a)['mse_reduction'] < 0 for a in ALPHAS),
        focal_gap_change_vs_old=focal['mse_reduction']-old['mse_reduction'],
        clipped=sum(r['clipped'] for rows in s['absolute'].values() for r in rows),
        selected_cheap_alpha={k: r['alpha'] for k, r in s['selected_cheap'].items()},
        focal_selected_cheap_gain_percent={r['reference']: 100*r['mse_reduction']/s['selected_cheap'][r['reference']]['metrics']['mse']
            for r in s['selected_contexts'] if r['candidate'] == 'interaction/tied:pulse'})


def fmt(v): return format(v, '.10g')


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join('---' for _ in headers)+' |']+
        ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])+'\n'


def compact(s):
    versions = table(['Model version', 'Passive MSE', 'Pulse MSE', 'Pulse error increase'],
        [(v, f"{s['absolute'][v+'/tied:passive'][1]['mse']:.9f}",
          f"{s['absolute'][v+'/tied:pulse'][1]['mse']:.9f}",
          f"{-gain_percent(s, pair(s, v+'/tied:pulse', v+'/tied:passive')):.6f}%") for v in ('old', 'settings', 'interaction')])
    alphas = table(['Alpha', 'Pulse MSE increase over matched passive', 'Helped / harmed founders'],
        [(a, f"{-gain_percent(s, r):.6f}%", f"{r['positive_blocks']} / {r['negative_blocks']}")
         for a in ALPHAS for r in [pair(s, 'interaction/tied:pulse', 'interaction/tied:passive', a)]])
    cheap = table(['Cheap reference', 'Selected alpha', 'MSE', 'Focal interaction pulse error increase'],
        [(k, choice['alpha'], f"{choice['metrics']['mse']:.9f}",
          f"{-100*r['mse_reduction']/choice['metrics']['mse']:.6f}%")
         for k in run.model.CHEAP for choice in [s['selected_cheap'][k]]
         for r in s['selected_contexts'] if r['candidate'] == 'interaction/tied:pulse' and r['reference'] == k])
    return versions, alphas, cheap


def render(s):
    rows = [(k, a, s['absolute'][k][i]) for k in run.model.KEYS for i, a in enumerate(ALPHAS)]
    text = ['# D176 — complete fixed development comparisons\n',
        '[Interpretation](RESULTS.md), [protocol](PROTOCOL_V1.md), [checker](check_results.py).\n',
        'All sixteen founders, four lives, four groups and four saved futures are retained. '
        'Old = no geometry inputs; settings = additive q0/q1; interaction = own-reading x (own q minus 1). '
        'There is no separate interaction/starting model: settings/starting is its unchanged starting baseline.\n',
        'Positive gain means reference MSE minus candidate MSE. MSE is native preference squared, '
        'not a survival percentage. MAE/RMSE/bias are preference points. All omissions hold existing '
        'forecasts fixed; they are not refits or intervals. Selected cheap alphas are selection-affected '
        'development context, not deployment selection.\n',
        'Every founder loss/gain/omission vector is retained unrounded in the '
        '[external summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_contextual_prediction_dev_v1_attempt1/summary.json) '
        'and per-case losses in the adjacent case_losses.npz. This appendix displays every fixed comparison, '
        'all group gains, omission ranges and the complete focal founder vector.\n']
    text += ['## All 33 absolute score rows\n', table(
        ['Model', 'Alpha', 'MSE', 'Mean-target MSE', 'MAE points', 'RMSE points', 'Bias points', 'Clipped / 256'],
        [(k, a, *(fmt(r[j]) for j in ('mse', 'mean_target_mse', 'mae_points', 'rmse_points', 'bias_points')), r['clipped']) for k, a, r in rows])]
    text += ['## Group MSE — all rows\n', table(['Model', 'Alpha', *GROUPS],
        [(k, a, *(fmt(x) for x in r['group_mse'])) for k, a, r in rows])]
    text += ['## Individual-future MSE — all rows\n',
        'The common saved within-case dispersion is '+fmt(rows[0][2]['future_dispersion'])+
        '. This is an empirical identity, not an irreducible noise bound.\n',
        table(['Model', 'Alpha', 'Future 0', 'Future 1', 'Future 2', 'Future 3'],
        [(k, a, *(fmt(x) for x in r['future_mse'])) for k, a, r in rows])]
    comparisons = [(f'C{i+1:03}', r) for i, r in enumerate(s['comparisons'])]
    text += ['## All 138 same-alpha comparisons\n', table(
        ['ID', 'Candidate', 'Reference', 'Alpha', 'MSE gain', 'Gain %', '+ / - / zero founders', 'Omit min', 'Omit max'],
        [(ID, r['candidate'], r['reference'], r['alpha'], fmt(r['mse_reduction']), fmt(gain_percent(s, r)),
          f"{r['positive_blocks']} / {r['negative_blocks']} / {r['zero_blocks']}",
          fmt(min(r['score_only_omit_gains'])), fmt(max(r['score_only_omit_gains']))) for ID, r in comparisons])]
    changes = [(f'G{i+1:02}', r) for i, r in enumerate(s['gap_changes'])]
    text += ['## All nine changes in pulse/passive gap\n',
        'Positive means the later representation improves the pulse-minus-passive MSE gain, not necessarily either absolute error.\n',
        table(['ID', 'Before', 'After', 'Alpha', 'Change in MSE gain', '+ / - / zero founders', 'Omit min', 'Omit max'],
        [(ID, r['before'], r['after'], r['alpha'], fmt(r['mse_reduction']),
          f"{r['positive_blocks']} / {r['negative_blocks']} / {r['zero_blocks']}",
          fmt(min(r['score_only_omit_gains'])), fmt(max(r['score_only_omit_gains']))) for ID, r in changes])]
    text += ['## Selected cheap baselines — selection-affected context\n', table(
        ['Reference', 'Selected alpha', 'MSE', 'RMSE points'],
        [(k, s['selected_cheap'][k]['alpha'], fmt(s['selected_cheap'][k]['metrics']['mse']),
          fmt(s['selected_cheap'][k]['metrics']['rmse_points'])) for k in run.model.CHEAP])]
    selected = [(f'S{i+1:02}', r) for i, r in enumerate(s['selected_contexts'])]
    text += ['## All 30 selected-cheap contexts\n', table(
        ['ID', 'Candidate at .01', 'Reference', 'Reference alpha', 'MSE gain', 'Gain %', '+ / - / zero founders', 'Omit min', 'Omit max'],
        [(ID, r['candidate'], r['reference'], r['reference_alpha'], fmt(r['mse_reduction']),
          fmt(100*r['mse_reduction']/s['selected_cheap'][r['reference']]['metrics']['mse']),
          f"{r['positive_blocks']} / {r['negative_blocks']} / {r['zero_blocks']}",
          fmt(min(r['score_only_omit_gains'])), fmt(max(r['score_only_omit_gains']))) for ID, r in selected])]
    text += ['## Group gains for every comparison, gap change and selected context\n', table(['ID', *GROUPS],
        [(ID, *(fmt(x) for x in r['group_gains'])) for ID, r in comparisons+changes+selected])]
    focal = pair(s, 'interaction/tied:pulse', 'interaction/tied:passive')
    text += ['## Complete focal founder scores and score-only omissions\n', table(
        ['Founder', 'Passive MSE', 'Pulse MSE', 'Pulse gain', 'Gain if this founder scores omitted'],
        [(b, fmt(s['absolute']['interaction/tied:passive'][1]['block_mse'][i]),
          fmt(s['absolute']['interaction/tied:pulse'][1]['block_mse'][i]), fmt(focal['block_gains'][i]),
          fmt(focal['score_only_omit_gains'][i])) for i, b in enumerate(s['blocks'])])]
    return '\n'.join(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table-patch', action='store_true')
    parser.add_argument('--facts', action='store_true')
    parser.add_argument('--receipt', action='store_true')
    args = parser.parse_args()
    s, done, audit, frozen = source()
    if args.table_patch:
        assert not args.facts and not args.receipt
        path = HERE/'TABLES.md'; assert not path.exists()
        print('*** Begin Patch\n*** Add File: '+str(path)+'\n'+'\n'.join('+'+x for x in render(s).splitlines())+'\n*** End Patch')
        return
    if args.facts:
        assert not args.receipt
        print(json.dumps(facts(s), sort_keys=True))
        for t in compact(s): print(t)
        print(json.dumps(dict(inputs=len(frozen['input_sha256']), outputs=len(done['output_sha256']),
            audit_sha256=run.io.sha256_file(run.audit_path()), summary_sha256=run.io.sha256_file(run.output_dir()/'summary.json'),
            resources=run.resources()), sort_keys=True))
        return
    expected = render(s)
    assert (HERE/'TABLES.md').read_text() == expected
    report = (HERE/'RESULTS.md').read_text()
    for t in compact(s): assert t in report
    paths = [HERE/p for p in ('RESULTS.md', 'TABLES.md', 'README.md', 'check_results.py')]
    links = 0
    for p in paths[:-1]:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', p.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (p.parent/target.split('#')[0]).resolve().is_file(), target
                links += 1
    tables = expected.count('## ')
    numeric = sum(line.startswith('| ') and not line.startswith('| ---') for line in expected.splitlines())-tables
    result = dict(passes=True, checked_utc=run.io.utc_now(), source_sha256=dict(freeze=FREEZE, complete=COMPLETE,
        audit=run.io.sha256_file(run.audit_path())), documentation_sha256=run.io.hashes(paths), facts=facts(s),
        appendix_tables=tables, appendix_numeric_rows=numeric, narrative_tables=3, links_checked=links,
        independent_scores_checked=True, new_fits=0, new_dynamics=0, automatic_successor=False)
    if args.receipt: run.io.write_json(run.ROOT/'logs'/(run.RUN+'_documentation_v1.json'), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'documentation_sha256'}, sort_keys=True))


if __name__ == '__main__': main()

