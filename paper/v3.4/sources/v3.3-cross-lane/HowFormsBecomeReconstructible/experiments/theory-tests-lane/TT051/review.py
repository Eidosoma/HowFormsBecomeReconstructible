"""Verify saved data provenance and scalar development scoring, no new fitting."""
from io_utils import *
import csv,math,ast,time

def main():
    start=time.monotonic();out=ROOT/'development_v2';done=read(out/'COMPLETE.json');assert done['status']=='COMPLETE'
    freeze=read(ROOT/'INPUT_FREEZE_v2.json')
    for p,h in freeze['sha256'].items():assert sha(p)==h,p
    for name,h in done['outputs'].items():assert sha(out/name)==h,name
    raw=arrays(ROOT/'DATA.npz');schema=read(ROOT/'FEATURE_SCHEMA.json');result=read(out/'RESULTS.json')
    with (out/'PREDICTIONS.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==768;ids=read(ROOT/'IDENTITIES.json')
    training=read(THEORY/'rdt_cheap_probe_transfer_v0_1/context/TRAINING_AUDIT.json')['training']
    source=Path(training['source']);assert sha(source/'COMPLETE.json')==training['source_complete_sha256']
    assert sha(source/'FEATURES.json')==training['source_features_sha256']
    commit=read(source/'COMPLETE.json');assert sha(source/'OUTPUTS.json')==commit['output_manifest_sha256']
    output_manifest=read(source/'OUTPUTS.json')['sha256'];assert output_manifest['FEATURES.json']==sha(source/'FEATURES.json')
    parent=[r for r in read(source/'FEATURES.json')['records'] if r['block'] in BLOCKS]
    parent={tuple([r['injury'],r['regime'],*r['key'],r['target_replicate']]):r for r in parent};assert len(parent)==768
    for i,(row,identity) in enumerate(zip(rows,ids,strict=True)):
        assert ast.literal_eval(row['key'])==identity['key']
        key=tuple([identity['injury'],identity['regime'],*identity['key'],identity['target_replicate']])
        original=parent[key];assert int(row['outcome'])==raw['y'][i]==original['outcome']
        assert int(row['block'])==raw['blocks'][i] and float(row['weight'])==raw['weights'][i]
        assert original['boundary']==[raw['X'][i,schema['all_columns'].index(n)] for n in schema['boundary_order']]
    count=0;maximum=0.
    for family,metrics in result['metrics'].items():
        groups=[('overall',rows,metrics['overall'])]
        groups += [(f'block{b}',[r for r in rows if int(r['block'])==b],metrics['blocks'][str(b)]) for b in BLOCKS]
        for name,subset,saved in groups:
            total=math.fsum(float(r['weight']) for r in subset)
            brier=math.fsum(float(r['weight'])*(float(r[family])-int(r['outcome']))**2 for r in subset)/total
            bias=math.fsum(float(r['weight'])*(float(r[family])-int(r['outcome'])) for r in subset)/total
            logloss=0.
            terms=[]
            for r in subset:
                p=min(1-1e-12,max(1e-12,float(r[family])));y=int(r['outcome'])
                terms.append(-float(r['weight'])*(y*math.log(p)+(1-y)*math.log1p(-p)))
            logloss=math.fsum(terms)/total
            for a,b in [(brier,saved['brier']),(bias,saved['bias']),(logloss,saved['log_loss'])]:
                error=abs(a-b);maximum=max(maximum,error);assert error<2e-13
            count+=1
    for comparison in result['paired_comparisons']:
        a,b=comparison['candidate'],comparison['reference']
        direct=[]
        for block in BLOCKS:
            subset=[r for r in rows if int(r['block'])==block];den=math.fsum(float(r['weight']) for r in subset)
            delta=math.fsum(float(r['weight'])*((float(r[b])-int(r['outcome']))**2-(float(r[a])-int(r['outcome']))**2) for r in subset)/den
            direct.append(delta)
        assert max(abs(x-y) for x,y in zip(direct,comparison['block_gains']))<2e-14
    # Verify the old comparator development without inspecting old prospective outcomes.
    historical=LANE/'TT008';calibration=historical/'runs/calibration_v1';complete=read(calibration/'COMPLETE.json')
    for name,h in complete['outputs_sha256'].items():assert sha(calibration/name)==h,name
    receipts=read(calibration/'fit_receipts.json');assert len(receipts)==176
    assert len({r['model'] for r in receipts})==22
    for r in receipts:
        assert r['heldout_block'] not in r['train_blocks'] and len(r['train_blocks'])==7 and r['n_train']==448
    registration=read(historical/'REGISTRATION.json')
    assert sha(historical/'FROZEN_MODELS.json')==registration['models_sha256']
    docs=['selection.json','forecast.py','support.py','calibrate.py','finalize.py','measure.py','engine.py',
          'DEVELOPMENT.md','EXECUTION.md','FROZEN_MODELS.json','REGISTRATION.json']
    write(ROOT/'TT008_AUDIT_RECEIPT.json',dict(status='PASS',utc=now(),development_cv_fits=176,models=22,
        calibration_seconds=complete['seconds'],source_hashes={n:sha(historical/n) for n in docs},
        prospective_outcome_files_read=False,scientific_choices_changed=False))
    receipt=dict(status='PASS',utc=now(),source_label_rows_independently_verified=len(rows),scalar_score_groups=count,
        maximum_score_error=maximum,paired_comparisons=len(result['paired_comparisons']),
        fitted_models=len(read(out/'MODELS.json')['models']),final_model_sha256=sha(out/'MODELS.json'),
        freeze_sha256=sha(out/'MODEL_FREEZE.json'),original_failure_preserved=True,TT050_polled=False,
        new_native_reads=0,seconds=time.monotonic()-start)
    write(ROOT/'REVIEW.json',receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
