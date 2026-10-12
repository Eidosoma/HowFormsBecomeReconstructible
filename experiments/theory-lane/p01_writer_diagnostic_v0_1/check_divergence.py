"""Reproduce the explicitly post-hoc first-divergence check from saved states."""
import json
from pathlib import Path
import numpy as np
from analyze import load_rows
from extract import ROOT, read_retained, sha


def main():
    cfg=json.loads((ROOT/'config.json').read_text())
    run=(ROOT/cfg['source_run']).resolve()
    conditions=json.loads((run/'manifest.json').read_text())['contract']['conditions']
    complete=json.loads((ROOT/'results/COMPLETE.json').read_text())
    expected_inputs={r['path']:r['sha256'] for r in complete['raw_data']}
    rows=load_rows(ROOT/'results/features.csv')
    previous=json.loads((ROOT/'results/first_divergence_checks.json').read_text())
    expected={r['pairing']:r for r in previous['checks']}
    for pairing in cfg['pairings']:
        relevant=[r for r in rows if r['pairing']==pairing and r['source_writer']=='exact_rewrite'
                  and r['reader_row_l1_mean']>0]
        generation=int(min(r['generation'] for r in relevant))
        i=conditions.index(pairing+'/exact_rewrite');j=conditions.index(pairing+'/tolerance_rewrite')
        same=different=0
        for block in cfg['blocks']:
            path=run/f'boundary_{block:06d}_g{generation}.npz'
            assert sha(path)==expected_inputs[str(path)]
            raw,_=read_retained(path,['end','outgoing'])
            for founder in range(4):
                for recipient in range(4):
                    a=(i,founder,recipient);b=(j,founder,recipient)
                    same+=raw['end'][a].tobytes()==raw['end'][b].tobytes()
                    different+=raw['outgoing'][a].tobytes()!=raw['outgoing'][b].tobytes()
        found=dict(pairing=pairing,generation=generation,same_body_lineages=same,
                   different_outgoing_lineages=different,total=128)
        assert found==expected[pairing],(found,expected[pairing])
        print(json.dumps(found))
    print('Post-hoc divergence checks reproduced; source hashes and retained-array commitments match.')


if __name__=='__main__':main()
