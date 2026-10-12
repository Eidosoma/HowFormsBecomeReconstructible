"""Separate reconstruction of extraction, forecasts, matches and all scores.

Does not import the extraction, analysis or core calculation modules.
"""
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULT = HERE / 'results'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(name):
    with (RESULT / name).open() as f:
        return list(csv.DictReader(f))


def close(a, b, tolerance=2e-12):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance, (a, b)


def identity(row):
    return tuple(row[k] for k in ('block', 'history', 'founder', 'recipient'))


def feature(row, name):
    if name.startswith('history='):
        return float(row['history'] == name.split('=', 1)[1])
    if '*' in name:
        a, b = name.split('*')
        return float(row[a])*float(row[b])
    return float(row[name])


def group_stats(group):
    outcomes = [(int(r['spaced_terminal']), int(r['clustered_terminal'])) for r in group]
    differences = [float(r['max_expression_difference']) for r in group]
    return dict(n=len(group), spaced_successes=sum(a for a,b in outcomes), clustered_successes=sum(b for a,b in outcomes),
        both_pass=sum(a == b == 1 for a,b in outcomes), both_fail=sum(a == b == 0 for a,b in outcomes),
        spaced_only=sum(a == 1 and b == 0 for a,b in outcomes), clustered_only=sum(a == 0 and b == 1 for a,b in outcomes),
        difference=sum(a-b for a,b in outcomes)/len(group) if group else None,
        mean_expression_difference=sum(differences)/len(group) if group else None,
        max_expression_difference=max(differences) if group else None)


def compare_dict(actual, expected):
    for k, v in expected.items():
        if v is None:
            assert actual[k] is None
        elif isinstance(v, float):
            close(actual[k], v)
        else:
            assert actual[k] == v, (k, actual[k], v)


def choice_stats(group, rule):
    successes = regrets = 0.
    ranks, ties, oracle = [], 0, 0
    for r in group:
        a, b, w = int(r['spaced_terminal']), int(r['clustered_terminal']), float(r['choose_spaced_'+rule])
        chosen = w*a+(1-w)*b
        successes += chosen
        oracle += max(a,b)
        regrets += max(a,b)-chosen
        if a != b:
            ranks.append(chosen)
            ties += int(w == .5)
    return dict(n=len(group), successes=successes, regret=regrets, hindsight_oracle_successes=oracle,
        success_rate=successes/len(group) if group else None, mean_regret=regrets/len(group) if group else None,
        discordant=len(ranks), discordant_accuracy=sum(ranks)/len(ranks) if ranks else None,
        discordant_ties=ties, discordant_nontie_coverage=(len(ranks)-ties)/len(ranks) if ranks else None)


def native_check(records, cfg):
    index = {identity(r): r for r in records}
    dense_checks = 0
    for bi, block in enumerate(cfg['blocks']):
        with np.load((HERE / cfg['spacing_run']) / f'boundary_{block:06d}_g14.npz', allow_pickle=False) as f:
            spacing = {k: f[k] for k in ('mean_ports', 'outgoing', 'end', 'masks')}
        with np.load((HERE / cfg['pulse_run']) / f'boundary_{block:06d}_g14.npz', allow_pickle=False) as f:
            pulse = {k: f[k] for k in ('mean_ports', 'outgoing', 'end', 'masks')}
        with np.load((HERE / cfg['spacing_run']) / f'cases_{block:06d}.npz', allow_pickle=False) as f:
            terminal = f['assay_both_pass']
            terminal_margin = f['assay_min_margin']
        for hi, history in enumerate(cfg['histories']):
            raw, ri = (pulse, 2) if hi == 1 else (spacing, {0:0, 2:1, 3:2}[hi])
            for founder, recipient in itertools.product(range(4), range(4)):
                r = index[(str(block), history, str(founder), str(recipient))]
                rule = 1. if founder % 2 == 0 else -1.
                aligned = []
                for cue, sign in enumerate((1., -1.)):
                    for port, orientation in enumerate((1., -1.)):
                        aligned.append(float(raw['mean_ports'][ri, founder, recipient, cue, port])*rule*sign*orientation)
                for name, value in zip(cfg['expression_features'][:4], aligned):
                    assert float(r[name]) == value
                assert float(r['current_margin']) == min(aligned)
                assert int(r['current_pass']) == int(min(aligned) > .25)
                ci = [0, 2, 3, 4][hi]
                assert int(r['terminal_success']) == int(terminal[ci, founder, recipient, 1])
                assert float(r['terminal_margin']) == float(terminal_margin[ci, founder, recipient, 1])
                if (founder, recipient) != (bi % 4, (2*bi+hi) % 4):
                    continue
                weight = np.frombuffer(raw['outgoing'][ri, founder, recipient].tobytes(), dtype='<f8').reshape(2,16,16)
                x = np.tanh(3.*raw['end'][ri, founder, recipient])
                mask = raw['masks'][founder, recipient]
                d = (x[0]-x[1])/2.
                operator = np.zeros((256,256))
                for y, col in itertools.product(range(16), range(16)):
                    for plane, (yy, xx) in enumerate(((y,(col+1)%16), ((y+1)%16,col))):
                        q = d[y,col]*d[yy,xx]
                        c = (x[0,y,col]*x[0,yy,xx]+x[1,y,col]*x[1,yy,xx])/2.
                        expected = 0. if mask[y,col] or mask[yy,xx] else q if q != 0. else c
                        assert weight[plane,y,col] == expected
                        a, b = 16*y+col, 16*yy+xx
                        operator[a,b] = operator[b,a] = expected
                for i in range(256):
                    den = sum(abs(v) for v in operator[i])
                    if den:
                        operator[i] /= den
                ports = [[16*y+x for y in range(yy,yy+2) for x in range(xx,xx+2)]
                         for yy,xx in ((7,1), (3,10), (11,10))]
                values = []
                for op in (operator, abs(operator)):
                    field = np.zeros(256)
                    field[ports[0]] = 1.
                    for _ in range(64):
                        field = op @ field
                        field[ports[0]] = 1.
                    values.append([float(np.mean(field[p])) for p in ports[1:]])
                close(float(r['signed_transfer']), min(rule*values[0][0], -rule*values[0][1]), 1e-13)
                close(float(r['unsigned_access']), min(values[1]), 1e-13)
                dense_checks += 1
    return dense_checks


def main():
    cfg, result = read(HERE / 'config.json'), read(RESULT / 'analysis.json')
    for name, digest in read(HERE / 'definition_snapshot.json')['files_sha256'].items():
        assert sha(HERE / name) == digest
    extraction = read(RESULT / 'extraction.json')
    for name, digest in extraction['source_files_sha256'].items():
        assert sha(HERE.parent / name) == digest
    assert sha(RESULT / 'records.csv') == extraction['records_sha256']
    records, predictions, pairs, scores = [table(n) for n in ('records.csv', 'predictions.csv', 'pairs.csv', 'scores.csv')]
    index = {identity(r): r for r in records}
    expected = set(itertools.product(map(str,cfg['blocks']), cfg['histories'], map(str,range(4)), map(str,range(4))))
    assert len(records) == len(index) == 512 and set(index) == expected
    dense = native_check(records, cfg)
    fits = read(RESULT / 'fits.json')
    fit_index = {(f['model'], str(f['heldout_block'])): f for f in fits}
    assert len(fits) == len(fit_index) == 48
    model_ids = [m['id'] for m in cfg['models']]
    assert set(fit_index) == set(itertools.product(model_ids, map(str,cfg['blocks'])))
    for f in fits:
        train = [r for r in records if int(r['block']) != f['heldout_block']]
        assert f['train_blocks'] == [b for b in cfg['blocks'] if b != f['heldout_block']]
        assert f['n_train'] == len(train) == 448 and f['n_test'] == 64
        model = next(m for m in cfg['models'] if m['id'] == f['model'])
        if model.get('estimator') == 'rate':
            for history in cfg['histories']:
                group = [r for r in train if r['history'] == history]
                s = sum(int(r['terminal_success']) for r in group)
                assert f['counts'][history] == dict(n=len(group), successes=s)
                close(f['rates'][history], (s+.5)/(len(group)+1))
            continue
        names = cfg['expression_features'] + (cfg['conventional_features'] if model['unsigned'] else [])
        names += ['history='+h for h in cfg['histories'][1:]]
        if model['quadratic']:
            names += [a+'*'+b for a,b in itertools.combinations_with_replacement(cfg['expression_features'][:4],2)]
        if model['signed']:
            names += cfg['candidate_features']
        assert f['columns'] == names and f['success']
        matrix = np.array([[feature(r,n) for n in names] for r in train])
        for j in range(len(names)):
            close(f['mean'][j], float(matrix[:,j].mean()))
            std = float(matrix[:,j].std())
            close(f['scale'][j], std if std > 1e-12 else 1.)
        a = np.column_stack((np.ones(len(train)), (matrix-np.array(f['mean']))/np.array(f['scale'])))
        y = np.array([int(r['terminal_success']) for r in train])
        w = np.array(f['coefficients'])
        logits = a@w
        loss = np.mean(np.logaddexp(0.,logits)-y*logits) + .5*.01*np.sum(w[1:]**2)
        close(float(loss), f['objective'])
        gradient = a.T@(1./(1.+np.exp(-logits))-y)/len(train)
        gradient[1:] += .01*w[1:]
        assert np.max(abs(gradient)) < 1e-5
    predicted = set()
    for r in predictions:
        key = (r['model'], *identity(r))
        assert key not in predicted
        predicted.add(key)
        native, f = index[identity(r)], fit_index[(r['model'],r['block'])]
        if f['model'] == 'history_rate':
            p = f['rates'][r['history']]
            z = math.log(p/(1-p))
        else:
            z = f['coefficients'][0] + sum(w*(feature(native,n)-m)/s
                for w,n,m,s in zip(f['coefficients'][1:],f['columns'],f['mean'],f['scale']))
            p = 1/(1+math.exp(-z))
        y = int(native['terminal_success'])
        assert int(r['target']) == y
        close(float(r['log_odds']),z)
        close(float(r['probability']),p)
        close(float(r['brier']),(p-y)**2)
        close(float(r['log_loss']),max(z,0)+math.log1p(math.exp(-abs(z)))-y*z)
    assert predicted == {(m,*k) for m in model_ids for k in expected}
    assert len(scores) == 240
    score_index = {}
    for s in scores:
        key = (s['model'],s['block'],s['history'])
        assert key not in score_index
        score_index[key] = s
        group = [r for r in predictions if r['model'] == s['model'] and r['block'] == s['block']
                 and (s['history'] == 'all' or r['history'] == s['history'])]
        assert int(s['n']) == len(group)
        for metric in ('brier','log_loss'):
            close(float(s[metric]),sum(float(r[metric]) for r in group)/len(group))
    for model in model_ids:
        for history in ['all',*cfg['histories']]:
            group = [s for s in scores if s['model'] == model and s['history'] == history]
            assert len(group) == 8
            for metric in ('brier','log_loss'):
                close(result['forecasts']['scores'][model][history][metric], sum(float(s[metric]) for s in group)/8)
    for contrast in result['forecasts']['comparisons']:
        diffs = []
        for b in cfg['blocks']:
            d = float(score_index[(contrast['baseline'],str(b),'all')]['brier'])-float(score_index[(contrast['candidate'],str(b),'all')]['brier'])
            close(contrast['block_brier_improvements'][str(b)],d)
            diffs.append(d)
        close(contrast['mean_brier_improvement'],sum(diffs)/8)
        assert contrast['positive_blocks'] == sum(d > 0 for d in diffs)
        assert contrast['negative_blocks'] == sum(d < 0 for d in diffs)
        assert contrast['tied_blocks'] == sum(d == 0 for d in diffs)
    seen_pairs = set()
    for r in pairs:
        key = tuple(r[k] for k in ('block','founder','recipient'))
        assert key not in seen_pairs
        seen_pairs.add(key)
        a,b = [index[(key[0],h,key[1],key[2])] for h in cfg['matched_pair']]
        delta = max(abs(float(a[k])-float(b[k])) for k in cfg['expression_features'][:4])
        assert float(r['max_expression_difference']) == delta
        coarse = int(a['current_pass']) == int(b['current_pass']) == 1
        assert int(r['current_both_pass']) == coarse
        assert int(r['strict_match']) == (coarse and delta <= cfg['match_caliper'])
        assert int(r['exact_expression']) == (delta == 0)
        for prefix,native in (('spaced',a),('clustered',b)):
            assert int(r[prefix+'_terminal']) == int(native['terminal_success'])
            assert int(r[prefix+'_current']) == int(native['current_pass'])
            assert float(r[prefix+'_margin']) == float(native['current_margin'])
            assert float(r[prefix+'_signed']) == float(native['signed_transfer'])
        assert float(r['choose_spaced_constant']) == 1.
        for rule,field in (('margin','current_margin'),('signed','signed_transfer')):
            aa,bb = float(a[field]),float(b[field])
            assert float(r['choose_spaced_'+rule]) == (1. if aa > bb else 0. if aa < bb else .5)
    assert len(seen_pairs) == 128
    for name,field in (('all',None),('both_current_pass','current_both_pass'),('strict','strict_match'),('exact','exact_expression')):
        group = [r for r in pairs if field is None or int(r[field])]
        summary = result['matching']['subsets'][name]
        compare_dict(summary,group_stats(group))
        for b in cfg['blocks']:
            compare_dict(summary['by_block'][str(b)],group_stats([r for r in group if int(r['block']) == b]))
    strict = [r for r in pairs if int(r['strict_match'])]
    for rule in ('constant','margin','signed'):
        summary = result['matching']['choices_on_strict_matches'][rule]
        compare_dict(summary,choice_stats(strict,rule))
        for b in cfg['blocks']:
            compare_dict(summary['by_block'][str(b)],choice_stats([r for r in strict if int(r['block']) == b],rule))
    for h,counts in result['counts'].items():
        group = [r for r in records if r['history'] == h]
        assert counts == dict(n=len(group), current_successes=sum(int(r['current_pass']) for r in group),
                              terminal_successes=sum(int(r['terminal_success']) for r in group))
    receipt = dict(status='PASS', verified_at_utc=datetime.now(timezone.utc).isoformat(),
        source_files=len(extraction['source_files_sha256']), records=512, dense_native_contexts=dense,
        predictions=3072, fits=48, block_history_scores=240, matched_pairs=128,
        all_match_subsets_and_choice_yields_verified=True, modules_under_test_imported=False,
        files_sha256={str(p.relative_to(HERE)):sha(p) for p in sorted(RESULT.iterdir()) if p.is_file()})
    with (RESULT / 'verification.json').open('x') as f:
        json.dump(receipt,f,indent=2,allow_nan=False)
        f.write('\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'files_sha256'}))


if __name__ == '__main__':
    main()
