"""Freeze retained summaries for two editorial figures; no models or inference run."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile

P = Path(__file__).resolve().parents[1]
DATA = P / 'paper_assets/data'
ARCHIVE = DATA / 'review-figures-v2.5-sources.zip'
FILES = [
    'experiments/E077_fresh_reconstruction_tradeoff/INTERPRETATION.md',
    'experiments/E077_fresh_reconstruction_tradeoff/analysis/closeout_v1.json',
    'experiments/E077_fresh_reconstruction_tradeoff/PROTOCOL.md',
    'experiments/theory-tests-lane/TT018/closeout_checks/v1/recomputed/record_probabilities.csv',
    'experiments/theory-tests-lane/TT018/closeout_checks/v1/recomputed/sealed_forecasts.csv',
    'experiments/theory-tests-lane/TT018/closeout_checks/v1/recomputed/paired_state_effects.json',
    'experiments/theory-tests-lane/TT018/closeout_checks/v1/recomputed/analysis.json',
    'experiments/theory-tests-lane/TT018/INTERPRETATION.md',
    'experiments/theory-tests-lane/TT018/PROTOCOL.md',
]


def main():
    # Once frozen, rebuilding reads the archive, not evolving lane files.
    if not ARCHIVE.exists():
        with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in FILES:
                z.write(P / name, name)
    with zipfile.ZipFile(ARCHIVE) as z:
        raw = {name: z.read(name) for name in FILES}
    sources = [{'path': n, 'sha256': hashlib.sha256(raw[n]).hexdigest()}
               for n in FILES]
    report = raw[FILES[0]].decode()
    rows = []
    for code, label, n in [('I0', 'Unpruned now', 571), ('P0', 'Pruned now', 647),
                           ('I1', 'Unpruned successor', 643), ('P1', 'Pruned successor', 572),
                           ('M1', 'Magnitudes only', 283), ('J1', 'Signs + magnitudes', 653)]:
        assert re.search(rf'^\| {code}:.*?\| {n:,}/1,024 \|', report, re.M), code
        rows.append(dict(code=code, label=label, successes=n, trials=1024, percent=100*n/1024))
    contrasts = []
    for pair in ['P0 − I0', 'P1 − I1', 'M1 − P1', 'J1 − P1']:
        m = re.search(rf'^\| {pair}:.*?\| \*\*([+−\d.]+) \[([−\d.]+), ([−\d.]+)\]', report, re.M)
        assert m, pair
        val = lambda s: float(s.replace('−', '-'))
        contrasts.append(dict(contrast=pair, mean=val(m[1]), low=val(m[2]), high=val(m[3]), coverage=.9875))
    f = 'experiments/theory-tests-lane/TT018/closeout_checks/v1/recomputed/'
    probabilities = list(csv.DictReader(raw[f+'record_probabilities.csv'].decode().splitlines()))
    forecasts = list(csv.DictReader(raw[f+'sealed_forecasts.csv'].decode().splitlines()))
    effects = json.loads(raw[f+'paired_state_effects.json'])
    analysis = json.loads(raw[f+'analysis.json'])
    records = []
    for x in forecasts:
        rid = x['record_id']
        policies = {}
        for row in probabilities:
            if row['record_id'] == rid and row['endpoint'] == 'terminal_record':
                policies[row['policy']] = {k: (int(row[k]) if k in ('successes','trials') else float(row[k]))
                    for k in ['successes','trials','probability','pointwise95_low','pointwise95_high']}
        effect = next(e for e in effects if e['record_id'] == rid and e['endpoint']=='terminal_record')
        records.append(dict(record_id=rid, block=int(x['block']), index=int(x['index']),
                            current_pass=bool(int(x['current_pass'])), history=x['history'],
                            policies=policies, paired=effect))
    records.sort(key=lambda r:r['block'])
    assert len(records)==64 and len({r['block'] for r in records})==64
    assert sum(not r['current_pass'] for r in records)==9
    for policy, total in [('untreated',3585),('one_time',3688),('repeated',3757)]:
        assert sum(r['policies'][policy]['successes'] for r in records)==total
        assert all(r['policies'][policy]['trials']==64 for r in records)
    assert sum(r['paired']['treated_only'] for r in records)==213
    assert sum(r['paired']['control_only'] for r in records)==41
    assert sum(r['paired']['mean']>0 for r in records)==51
    assert sum(r['paired']['mean']<0 for r in records)==3
    data = dict(version='2.5', date='2026-10-29',
        scope='Editorial display of retained outcomes; no new simulation, fitted model, bootstrap or confidence interval.',
        pruning=dict(rows=rows, contrasts=contrasts, independent_blocks=32,
                     interval='Original 98.75% whole-block bootstrap intervals; four primary contrasts.',
                     immediate_beneficiaries=87, later_harmed_among_immediate_beneficiaries=8,
                     audit_scope='Counts and intervals transcribed from retained interpretation; raw E077 runs absent here.'),
        futures=dict(records=records, primary=analysis['primary'],
                     audit_scope='All retained per-record terminal counts, status classes and paired effects checked; trajectories not replayed.'),
        source_archive=str(ARCHIVE.relative_to(P)), sources=sources)
    dest=DATA/'review-figures-v2.5.json'
    dest.write_text(json.dumps(data,indent=2)+'\n')
    manifest=dict(archive=str(ARCHIVE.relative_to(P)),archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                  sources=sources,data=str(dest.relative_to(P)),data_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    (P/'reviews/V2.5_FIGURE_SOURCES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Verified six pruning counts, four original intervals and all 64 repeated-future records.')


if __name__=='__main__':
    main()
