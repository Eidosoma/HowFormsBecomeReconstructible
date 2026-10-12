"""Render/check D175 documentation from the audited saved summary; no new fits."""
import argparse
import json
import re
import numpy as np
import measure as m
import verify as v
import workflow as w


def sources():
    w.frozen()
    done, audit = w.read_json(w.COMPLETE), w.read_json(w.AUDIT)
    assert done['passes'] and audit['passes']
    assert audit['complete_sha256'] == w.digest(w.COMPLETE)
    assert audit['freeze_sha256'] == done['freeze_sha256'] == w.digest(w.FREEZE)
    w.verify_hashes(done['output_sha256'])
    report = w.read_json(w.OUTPUT / 'summary.json')
    arrays = w.npz(w.OUTPUT / 'measurements.npz', ('distance', 'shape_valid', 'entry', 'q', 'endpoint', 'routing'))
    assert report == m.summary(arrays)
    v.summary(arrays, report)
    return report, arrays, done, audit


def fmt(value): return 'undefined' if value is None else format(value, '.10g')


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join('---' for _ in headers)+' |'] +
        ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])+'\n'


def render(report):
    groups = report['groups']
    text = ['# D175 — complete fixed checkpoint summaries\n',
        '[Interpretation](RESULTS.md), [protocol](PROTOCOL_V1.md), [checker](report.py).\n',
        'All 16 founders, four lives and four groups are retained: 256 U1/P1 pairs. '
        'Delta means P1 minus U1; nonnegative distances describe differences, not benefits. '
        'RMS values keep their native field units. Unit-centered shape distance removes mean/scale; '
        'it is not target fidelity. Undefined shape measurements remain masked, not measured zero.\n',
        'No prospective test, fitted predictor, actual-lineage outcomes, confidence intervals or '
        'new dynamics. All per-case measurements and every founder/stage summary remain in the '
        '[external summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_feedback_pulse_checkpoint_v1_attempt1/summary.json) '
        'and the adjacent measurements.npz.\n']
    text += ['## Pulse entry — feedback available for update 301\n', table(
        ['Group', 'Mean feedback displacement RMS', 'Mean normal RMS', 'Ratio of pooled RMS'],
        [(g['group'], fmt(g['entry_mean_delta']), fmt(g['entry_mean_U_rms']), fmt(g['entry_relative_rms'])) for g in groups])]
    text += ['## All writer/export/fresh-reader stages\n', table(
        ['Group', 'Stage', 'Mean delta RMS', 'Pooled delta RMS', 'Mean U RMS', 'Mean P RMS', 'Mean shape distance', 'Shape valid / invalid'],
        [(g['group'], s['stage'], *(fmt(s[k]) for k in ('mean_delta', 'rms_delta', 'mean_U_rms', 'mean_P_rms', 'shape_distance')),
          f"{s['shape_valid']} / {s['shape_invalid']}") for g in groups for s in g['stages']])]
    text += ['## End-of-writing difference relative to end-of-pulse\n',
        'Ratio of pooled RMS at 1000 to that at 400, separately for each field. '
        'Counts compare individual-case raw RMS differences; no monotonic trajectory is assumed.\n', table(
        ['Group', 'Field', '1000 / 400', 'Smaller / equal / larger cases', 'Zero denominators'],
        [(g['group'], r['field'], fmt(r['rms_ratio']), f"{r['smaller']} / {r['equal']} / {r['larger']}", r['zero_denominators'])
         for g in groups for r in g['recovery']])]
    text += ['## All six diagnostic endpoint features\n',
        'Correlations/preferences below are native units, not percentages. '
        'Founder signs use tolerance 1e-12 after averaging four lives.\n', table(
        ['Group', 'Feature', 'U mean', 'P mean', 'Mean delta', 'Mean absolute delta', '+ / - / numerical-zero founders'],
        [(g['group'], r['feature'], *(fmt(r[k]) for k in ('mean_U', 'mean_P', 'mean_delta', 'mean_absolute_delta')),
          f"{r['positive']} / {r['negative']} / {r['numerical_zero']}") for g in groups for r in g['endpoint']])]
    text += ['## Routing — every group has 64 pairs\n', table(
        ['Group', 'Family changes', 'Shift changes', 'U ties', 'P ties', 'U correct', 'P correct'],
        [(g['group'], *(g['route'][k] for k in ('family_switch', 'shift_switch', 'U_tie', 'P_tie', 'U_correct', 'P_correct'))) for g in groups])]
    text += ['## Complete delta-q profiles — descriptive, including empty cells\n',
        'Writer columns are mean RMS branch distances; final columns are signed endpoint differences. '
        'Supports are not independent randomized q-effect estimates.\n', table(
        ['Group', 'Delta q', 'Cases', 'Founders', 'Writer R distance at 400', 'Writer R distance at 1000', 'Own-best delta', 'Diagnostic preference delta'],
        [(g['group'], r['delta_q'], r['n'], r['founders'], *(fmt(x) for x in (r['means'] or [None]*4)))
         for g in groups for r in g['geometry']])]
    for g in groups:
        text += [f"## Founder endpoint differences — {g['group']}\n", table(['Founder', *m.FEATURES],
            [(ID, *(fmt(r['founder_deltas'][b]) for r in g['endpoint'])) for b, ID in enumerate(m.IDS)])]
    for g in groups:
        text += [f"## Founder 1000/400 pooled-difference ratios — {g['group']}\n", table(['Founder', *m.FIELDS],
            [(ID, *(fmt(r['founders'][b]['rms_ratio']) for r in g['recovery'])) for b, ID in enumerate(m.IDS)])]
    return '\n'.join(text)


def compact(report):
    recovery = table(['Group', 'V difference remaining', 'R difference remaining', 'Theta difference multiplier'],
        [(g['group'].replace('_', ' '), f"{100*g['recovery'][0]['rms_ratio']:.1f}%",
          f"{100*g['recovery'][2]['rms_ratio']:.1f}%", f"{g['recovery'][3]['rms_ratio']:.2f}x") for g in report['groups']])
    endpoint = table(['Group', 'Own-best correlation change', 'Diagnostic preference change, points', 'Selected-shift changes / 64'],
        [(g['group'].replace('_', ' '), f"{g['endpoint'][0]['mean_delta']:+.6f}",
          f"{100*g['endpoint'][4]['mean_delta']:+.3f}", g['route']['shift_switch']) for g in report['groups']])
    return recovery, endpoint


def facts(report, arrays):
    values = arrays['distance']
    return dict(complete_cases=256, outgoing_nonzero_cases=int(np.count_nonzero(values[..., m.STAGES.index('outgoing'), 0])),
        fresh_V_nonzero_cases=int(np.count_nonzero(values[..., -1, 0])),
        family_changes=sum(g['route']['family_switch'] for g in report['groups']),
        shift_changes=sum(g['route']['shift_switch'] for g in report['groups']),
        smaller_R_cases=sum(g['recovery'][2]['smaller'] for g in report['groups']),
        larger_theta_cases=sum(g['recovery'][3]['larger'] for g in report['groups']),
        normalized_export_shape_residual=float(np.max(abs(values[..., m.STAGES.index('tanh_R'), 3]-values[..., m.STAGES.index('outgoing'), 3]))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table-patch', action='store_true')
    parser.add_argument('--facts', action='store_true')
    parser.add_argument('--receipt', action='store_true')
    args = parser.parse_args()
    report, arrays, done, audit = sources()
    if args.table_patch:
        assert not args.facts and not args.receipt
        path = w.HERE / 'TABLES.md'; assert not path.exists()
        print('*** Begin Patch\n*** Add File: '+str(path)+'\n'+
              '\n'.join('+'+s for s in render(report).splitlines())+'\n*** End Patch')
        return
    if args.facts:
        assert not args.receipt
        print(json.dumps(facts(report, arrays), sort_keys=True))
        for text in compact(report): print(text)
        print(json.dumps(dict(resources=w.resources(), freeze=w.digest(w.FREEZE),
            complete=w.digest(w.COMPLETE), audit=w.digest(w.AUDIT), summary=w.digest(w.OUTPUT/'summary.json'),
            maximum_check_residual=max(r['maximum_residual'] for r in audit['checks'])), sort_keys=True))
        return
    tables = render(report)
    assert (w.HERE / 'TABLES.md').read_text() == tables
    assert tables.count('## ') == 14
    assert sum(line.startswith('| ') and not line.startswith('| ---') for line in tables.splitlines())-14 == 332
    text = (w.HERE / 'RESULTS.md').read_text()
    for tbl in compact(report): assert tbl in text
    paths = [w.HERE / name for name in ('RESULTS.md', 'TABLES.md', 'README.md', 'report.py')]
    links = 0
    for p in paths[:-1]:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', p.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (p.parent / target.split('#')[0]).resolve().is_file(), target
                links += 1
    result = dict(passes=True, checked_utc=w.utc(), documentation_sha256=w.hashes(paths),
        freeze_sha256=w.digest(w.FREEZE), complete_sha256=w.digest(w.COMPLETE), audit_sha256=w.digest(w.AUDIT),
        facts=facts(report, arrays), links_checked=links, appendix_tables=14, appendix_rows=332,
        narrative_tables=2, new_fits=0, new_dynamics=0, outcomes_loaded=False, automatic_successor=False)
    if args.receipt:
        w.save_json(w.ROOT/'logs'/(w.RUN+'_documentation_v1.json'), result)
    print(json.dumps({k: value for k, value in result.items() if k != 'documentation_sha256'}, sort_keys=True))


if __name__ == '__main__': main()
