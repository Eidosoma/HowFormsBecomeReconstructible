"""Read-only NumPy aggregation of the saved audit; no audit-module import."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent/'p02_common_future_v0_1'


def read(path):
    return json.loads(path.read_text())


def table(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def close(a,b):
    assert abs(a-b) < 2e-12,(a,b)


def key(r):
    return (r['block'],r['history'],r['founder'],r['recipient'])


def main():
    result=read(HERE/'results.json')
    for name,digest in result['source_files_sha256'].items():
        assert hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest() == digest
    rows=table(SOURCE/'results/records.csv')
    predictions=table(SOURCE/'results/predictions.csv')
    cfg=read(SOURCE/'config.json')
    models=[m['id'] for m in cfg['models']]
    lookup={(r['model'],key(r)):float(r['probability']) for r in predictions}
    index={key(r):i for i,r in enumerate(rows)}
    p=np.array([[lookup[m,key(r)] for r in rows] for m in models])
    y=np.array([int(r['terminal_success']) for r in rows])
    passed=np.array([bool(int(r['current_pass'])) for r in rows])
    block=np.array([int(r['block']) for r in rows])
    errors=(p-y[None,:])**2
    for label,subset in [('all',np.ones(512,bool)),('currently_pass',passed),('currently_fail',~passed)]:
        out=result['strata'][label]
        assert out['n']==int(subset.sum()) and out['terminal_successes']==int(y[subset].sum())
        assert out['terminal_failures']==int((1-y[subset]).sum())
        for hi,history in enumerate(cfg['histories']):
            sub=subset & np.array([r['history']==history for r in rows])
            assert out['by_history'][history]==dict(n=int(sub.sum()),terminal_successes=int(y[sub].sum()))
        for mi,m in enumerate(models):
            close(out['scores'][m]['record_weighted_brier'],float(errors[mi,subset].mean()))
            block_scores=[]
            for b in cfg['blocks']:
                sub=subset & (block==b)
                observed=out['scores'][m]['by_block'][str(b)]
                assert observed['n']==int(sub.sum())
                close(observed['brier'],float(errors[mi,sub].mean()))
                block_scores.append(float(errors[mi,sub].mean()))
            close(out['scores'][m]['equal_block_brier'],float(np.mean(block_scores)))
        for contrast in out['contrasts']:
            delta=errors[models.index(contrast['baseline'])]-errors[models.index(contrast['candidate'])]
            close(contrast['record_weighted_improvement'],float(delta[subset].mean()))
            close(contrast['contribution_to_overall_brier_improvement'],float(delta[subset].sum()/512))
            values=[]
            for b in cfg['blocks']:
                value=float(delta[subset & (block==b)].mean())
                close(contrast['by_block'][str(b)],value)
                values.append(value)
            close(contrast['equal_block_improvement'],float(np.mean(values)))
            assert contrast['positive_blocks']==sum(v>0 for v in values)
            assert contrast['negative_blocks']==sum(v<0 for v in values)
    # Build the original matching set from the four outputs, not audit pair rows.
    pair_indices=[]
    for r in rows:
        if r['history']!=cfg['matched_pair'][0]:
            continue
        i=index[key(r)]
        j=index[(r['block'],cfg['matched_pair'][1],r['founder'],r['recipient'])]
        gap=max(abs(float(rows[i][n])-float(rows[j][n])) for n in cfg['expression_features'][:4])
        if passed[i] and passed[j] and gap<=cfg['match_caliper']:
            pair_indices.append((i,j))
    assert len(pair_indices)==84
    ii,jj=np.array(pair_indices).T
    for rule,out in result['matched_decisions'].items():
        if rule=='constant':
            w=np.ones(len(ii))
        else:
            if rule in ('margin','signed'):
                field='current_margin' if rule=='margin' else 'signed_transfer'
                values=np.array([float(r[field]) for r in rows])
            else:
                values=p[models.index(rule)]
            difference=values[ii]-values[jj]
            w=np.where(difference>0,1.,np.where(difference<0,0.,.5))
        achieved=w*y[ii]+(1-w)*y[jj]
        oracle=np.maximum(y[ii],y[jj])
        different=y[ii]!=y[jj]
        for label,selection in [('all',np.ones(84,bool)),*[(str(b),block[ii]==b) for b in cfg['blocks']]]:
            target=out if label=='all' else out['by_block'][label]
            disc=selection & different
            assert target['n']==int(selection.sum())
            close(target['successes'],float(achieved[selection].sum()))
            assert target['oracle']==int(oracle[selection].sum())
            close(target['regret'],float((oracle-achieved)[selection].sum()))
            assert target['discordant']==int(disc.sum())
            close(target['discordant_correct'],float(achieved[disc].sum()))
            assert target['discordant_ties']==int(((w==.5)&disc).sum())
    receipt=dict(status='PASS',created_at_utc=datetime.now(timezone.utc).isoformat(),
        records=512,forecasts=3072,strata=3,models=6,blocks=8,matched_pairs=84,choice_rules=6,
        audit_module_imported=False,source_module_imported=False,
        results_sha256=hashlib.sha256((HERE/'results.json').read_bytes()).hexdigest())
    with (HERE/'verification.json').open('x') as f:
        json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
