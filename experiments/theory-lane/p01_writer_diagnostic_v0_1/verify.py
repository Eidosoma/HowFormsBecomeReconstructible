"""Verify artifact bindings and independently recalculate reported Brier scores."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snapshot=json.loads((ROOT/'snapshot.json').read_text())
    for item in snapshot['files']:
        path=ROOT/item['path']
        assert path.is_file() and sha(path)==item['sha256'],str(path)
    complete=json.loads((ROOT/'results/COMPLETE.json').read_text())
    report=json.loads((ROOT/'results/analysis.json').read_text())
    assert sha(ROOT/'config.json')==complete['config_sha256']
    assert sha(ROOT/'results/features.csv')==complete['features_sha256']==report['feature_sha256']
    for name,expected in complete['code_sha256'].items():assert sha(ROOT/name)==expected,name
    assert sha(ROOT/'analyze.py')==report['analysis_sha256']
    assert sha(ROOT/'results/held_out_predictions.csv')==report['prediction_sha256']
    totals={}
    with (ROOT/'results/held_out_predictions.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            target=row['target'];block=int(float(row['block']));y=float(row['observed'])
            assert y in (0.,1.)
            for model in ('current_expression_and_context','plus_mechanistic_features'):
                p=float(row[model]);assert 0<=p<=1
                key=(target,model,block)
                n,error=totals.get(key,(0,0.))
                totals[key]=(n+1,error+(p-y)**2)
    for target,check in report['prediction_checks'].items():
        for model,record in check['models'].items():
            block_errors=[]
            for fold in record['folds']:
                n,error=totals[target,model,fold['block']]
                assert n==fold['n']
                block_errors.append(error/n)
                assert abs(error/n-fold['brier'])<1e-12
            assert abs(sum(block_errors)/len(block_errors)-record['mean_block_brier'])<1e-12
    print(f"Verified {len(snapshot['files'])} files, all calculation bindings and independent blockwise Brier recomputation.")
    print('Retrospective development only; no new native dynamics or full E051 audit.')


if __name__=='__main__':main()
