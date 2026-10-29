#!/usr/bin/env python3
"""Extract existing tissue summaries for figures; never run model code or inference.

This optional extraction needs the retained external archive. Rendering uses the
small checked-in extract and does not require that archive. Saved intervals and
verdicts are copied unchanged; only equal-tissue means and unit conversions are
calculated here.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = '/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs'
FILES = {
    'D073': 'l22_fresh_writing_replication_v1_attempt1_independent_rescore_v1/rescore.json',
    'D074': 'l22_body_source_v1_attempt1_independent_rescore_v1/rescore.json',
    'D099': 'l15_reversal_defense_v1_attempt1/summary.json',
    'L17': 'l17_replacement_chain_v1_attempt1/replacement_chain.json',
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(DEFAULT))
    args = parser.parse_args()
    sources, loaded = [], {}
    for key, rel in FILES.items():
        path = args.source_root / rel
        raw = path.read_bytes()
        loaded[key] = json.loads(raw)
        sources.append(dict(campaign=key, path=rel, bytes=len(raw),
                            sha256=hashlib.sha256(raw).hexdigest()))
    out = dict(schema='forms_measured_figures_v1', source_root=str(args.source_root),
               sources=sources, new_simulations=0, new_statistical_tests=0,
               scope='Saved summaries and existing audit results; not a new raw-array audit.',
               interval_policy='Copy original intervals; no rebootstrap or pooled endpoints.')
    for key in ['D073', 'D074']:
        data = loaded[key]
        assert data['passes'] and len(data['checked']) == 16
        arms = ['damaged', 'fixed', 'loop'] if key == 'D073' else ['damaged', 'kept_loop', 'scrambled_loop', 'donor_loop']
        points = {arm: [c['readout']['arms'][arm]['accuracy'] for c in data['checked']] for arm in arms}
        out[key] = dict(tissues=[c['tissue'] for c in data['checked']],
                        means={arm: mean(values) for arm, values in points.items()},
                        tissue_accuracy=points, contrasts=data['classification']['co_primary'],
                        verdict=data['classification']['label'],
                        unit='four-message recognition probability')
        for contrast in out[key]['contrasts'].values():
            assert abs(mean(contrast['tissue_differences']) - contrast['mean']) < 1e-12
            assert contrast['resamples'] == 10000
    assert abs(out['D073']['means']['loop']-out['D073']['means']['fixed']-out['D073']['contrasts']['loop_vs_fixed']['mean']) < 1e-12
    assert out['D074']['contrasts']['donor_redirection']['supported'] is False

    data=loaded['D099']
    assert len(data['tissues'])==8 and not data['bounded_pattern_supported']
    out['D099']=dict(tissues=data['tissues'], primary=data['primary'],
                     directions=data['direction_contrasts'],
                     recovery=[data['endpoints'][f'd{d}_sustained_new_post'] for d in [0,1]],
                     criteria=data['behavioral_criteria'],
                     unit='new-pattern sign fidelity on the 128-site disagreement mask')
    for item in out['D099']['directions']+out['D099']['recovery']:
        assert abs(mean(item['block_means'])-item['mean']) < 1e-12

    data=loaded['L17']
    assert data['completed_cleanly'] and len(data['results'])==8
    rows=[]
    for generation in range(1,13):
        for arm in ['split_replace','protected_copy','split_reset']:
            values=[t['generations'][generation-1]['summaries']['candidate'][arm]['1000']['body_accuracy'] for t in data['results']]
            rows.append(dict(generation=generation, arm=arm, mean=mean(values), tissue_means=values))
    out['L17']=dict(tissues=[t['tissue'] for t in data['results']], rows=rows,
                   terminal_contrasts=data['classification']['co_primary_G12'],
                   verdict=data['classification']['label'],
                   unit='four-stripe-message body recognition probability')
    selected={r['generation']:r['mean'] for r in rows if r['arm']=='split_replace'}
    for g,value in {1:1.,2:.90625,3:.640625,12:.2734375}.items():
        assert abs(selected[g]-value)<1e-12
    assert not any(c['supported'] for c in out['L17']['terminal_contrasts'].values())
    # Ensure the read-only extraction has not raced a changing source file.
    for item in sources:
        assert hashlib.sha256((args.source_root/item['path']).read_bytes()).hexdigest()==item['sha256']
    dest=ROOT/'paper_assets/data'
    dest.mkdir(exist_ok=True)
    (dest/'measured-figures-v1.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    with (dest/'measured-endpoints-v1.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['campaign','endpoint','mean_fraction','interval_low_fraction','interval_high_fraction','interval_type','positive_tissues','qualifies'])
        for campaign in ['D073','D074']:
            for name,c in out[campaign]['contrasts'].items():
                writer.writerow([campaign,name,c['mean'],*c['interval'],'three-endpoint adjusted (98.333% individual)',c['positive_tissues'],c['supported']])
        for name,c in [('weaker_direction',out['D099']['primary'])]+[(f'direction_{i}',x) for i,x in enumerate(out['D099']['directions'])]+[(f'direction_{i}_acquired_new_recovery',x) for i,x in enumerate(out['D099']['recovery'])]:
            writer.writerow(['D099',name,c['mean'],*c['pointwise_block_bootstrap_95'],'95% paired tissue bootstrap','',''])
    with (dest/'replacement-loss-v1.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['generation','arm','equal_tissue_mean']+[f'tissue_{t}' for t in out['L17']['tissues']])
        for row in rows: writer.writerow([row['generation'],row['arm'],row['mean'],*row['tissue_means']])
    print('Extracted four retained summaries; checked selected published endpoints and saved verdicts. No model runs or new inference.')

if __name__=='__main__': main()
