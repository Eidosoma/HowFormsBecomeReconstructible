"""Outcome-informed decomposition of saved P02 forecasts; no refits."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'p02_common_future_v0_1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def table(name):
    with (SOURCE/'results'/name).open() as f:
        return list(csv.DictReader(f))


def key(r):
    return tuple(r[k] for k in ('block', 'history', 'founder', 'recipient'))


def average(values):
    return sum(values)/len(values) if values else None


def main():
    frozen = read(HERE/'definition_snapshot.json')
    for name, digest in frozen['files_sha256'].items():
        assert sha(HERE/name) == digest
    complete = read(SOURCE/'COMPLETE.json')
    assert sha(SOURCE/'FINAL_SNAPSHOT.json') == complete['final_snapshot_sha256']
    source_snapshot = read(SOURCE/'FINAL_SNAPSHOT.json')['files_sha256']
    files = ['config.json','results/records.csv','results/predictions.csv','results/pairs.csv','results/analysis.json']
    for name in files:
        assert sha(SOURCE/name) == source_snapshot[name]
    cfg = read(SOURCE/'config.json')
    rows, predictions, pairs = table('records.csv'), table('predictions.csv'), table('pairs.csv')
    record = {key(r):r for r in rows}
    pred = {(r['model'],key(r)):r for r in predictions}
    assert len(rows) == len(record) == 512
    assert len(predictions) == len(pred) == 3072
    models = [m['id'] for m in cfg['models']]
    blocks = list(map(str,cfg['blocks']))
    for m in models:
        assert {k for model,k in pred if model == m} == set(record)
    errors = {}
    for (m,k), r in pred.items():
        assert int(r['target']) == int(record[k]['terminal_success'])
        brier = (float(r['probability'])-int(r['target']))**2
        assert abs(brier-float(r['brier'])) < 1e-15
        errors[m,k] = brier
    strata = {'all':list(record), 'currently_pass':[k for k,r in record.items() if int(r['current_pass'])],
              'currently_fail':[k for k,r in record.items() if not int(r['current_pass'])]}
    summaries = {}
    comparisons = [cfg['primary_comparison'],cfg['secondary_comparison'],
                   ['expression_history','expression_unsigned_signed']]
    for label, keys in strata.items():
        scores = {}
        for model in models:
            by_block = {b:dict(n=len(group := [k for k in keys if k[0] == b]),
                              brier=average([errors[model,k] for k in group])) for b in blocks}
            scores[model] = dict(record_weighted_brier=average([errors[model,k] for k in keys]),
                equal_block_brier=average([r['brier'] for r in by_block.values() if r['n']]),by_block=by_block)
        contrasts = []
        for base,candidate in comparisons:
            differences = {b:average([errors[base,k]-errors[candidate,k] for k in keys if k[0] == b]) for b in blocks}
            values = [v for v in differences.values() if v is not None]
            contrasts.append(dict(baseline=base,candidate=candidate,
                record_weighted_improvement=average([errors[base,k]-errors[candidate,k] for k in keys]),
                equal_block_improvement=average(values),
                contribution_to_overall_brier_improvement=sum(errors[base,k]-errors[candidate,k] for k in keys)/len(record),
                positive_blocks=sum(v > 0 for v in values),negative_blocks=sum(v < 0 for v in values),
                tied_blocks=sum(v == 0 for v in values),by_block=differences))
        summaries[label] = dict(n=len(keys),terminal_successes=sum(int(record[k]['terminal_success']) for k in keys),
            terminal_failures=sum(1-int(record[k]['terminal_success']) for k in keys),scores=scores,contrasts=contrasts,
            by_history={h:dict(n=len(group := [k for k in keys if k[1] == h]),
                terminal_successes=sum(int(record[k]['terminal_success']) for k in group)) for h in cfg['histories']})
    for i in range(3):
        total=summaries['all']['contrasts'][i]['record_weighted_improvement']
        parts=sum(summaries[s]['contrasts'][i]['contribution_to_overall_brier_improvement'] for s in ('currently_pass','currently_fail'))
        assert abs(total-parts) < 1e-14
    strict = [r for r in pairs if int(r['strict_match'])]
    assert len(strict) == 84
    decision_models = ['expression_history','expression_unsigned_signed','quadratic_unsigned_signed']
    decision_rows = []
    for r in strict:
        a,b = [(r['block'],h,r['founder'],r['recipient']) for h in cfg['matched_pair']]
        ya,yb = int(record[a]['terminal_success']),int(record[b]['terminal_success'])
        weights = {rule:float(r['choose_spaced_'+rule]) for rule in ('constant','margin','signed')}
        for m in decision_models:
            pa,pb = float(pred[m,a]['probability']),float(pred[m,b]['probability'])
            weights[m] = 1. if pa > pb else 0. if pa < pb else .5
        for rule,w in weights.items():
            decision_rows.append(dict(rule=rule,block=r['block'],founder=r['founder'],recipient=r['recipient'],
                spaced_outcome=ya,clustered_outcome=yb,choice_weight_spaced=w,attained=w*ya+(1-w)*yb,
                oracle=max(ya,yb),discordant=ya != yb))

    def decision(group):
        discordant=[r for r in group if r['discordant']]
        return dict(n=len(group),successes=sum(r['attained'] for r in group),oracle=sum(r['oracle'] for r in group),
            regret=sum(r['oracle']-r['attained'] for r in group),discordant=len(discordant),
            discordant_correct=sum(r['attained'] for r in discordant),
            discordant_ties=sum(r['choice_weight_spaced'] == .5 for r in discordant))
    decisions={}
    for rule in ('constant','margin','signed',*decision_models):
        group=[r for r in decision_rows if r['rule'] == rule]
        decisions[rule]=decision(group)
        decisions[rule]['by_block']={b:decision([r for r in group if r['block'] == b]) for b in blocks}
    previous=read(SOURCE/'results/analysis.json')
    for rule in ('constant','margin','signed'):
        expected=previous['matching']['choices_on_strict_matches'][rule]
        for name in ('n','successes','regret','discordant','discordant_ties'):
            assert decisions[rule][name] == expected[name]
    result=dict(status='EXPLORATORY_AUDIT_COMPLETE',created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_files_sha256={str((SOURCE/name).relative_to(HERE.parent)):sha(SOURCE/name)
                             for name in [*files,'COMPLETE.json','FINAL_SNAPSHOT.json']},
        native_simulations=False,refits=0,rows=512,predictions=3072,strata=summaries,matched_decisions=decisions)
    write(HERE/'results.json',result)
    with (HERE/'matched_decisions.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(decision_rows[0]));w.writeheader();w.writerows(decision_rows)
    print(json.dumps(dict(status=result['status'],strata={s:{k:v for k,v in x.items() if k not in ('scores','by_history')} for s,x in summaries.items()},
                          choices={r:{k:v for k,v in d.items() if k != 'by_block'} for r,d in decisions.items()})))


if __name__ == '__main__':
    main()
