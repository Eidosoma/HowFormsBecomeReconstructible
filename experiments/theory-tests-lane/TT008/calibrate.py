"""Freeze and evaluate the declared comparator grid on exposed data only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np
from scipy.stats import chi2,nct,t
import forecast as f
import support as s

OWN=('support.py','prepare.py','forecast.py','check_forecasts.py','calibrate.py','selection.json','SOURCE_RECEIPT.json')


def power(effect,sd,n):
    if sd==0:return float(effect>0)
    return float(nct.sf(t.ppf(1-s.CFG['planning_one_sided_alpha'],n-1),n-1,effect*np.sqrt(n)/sd))


def execute(output,inputs):
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    try:
        os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});s.verify_sources()
        s.dump(output/'manifest.json',dict(study='TT008',stage='DEVELOPMENT_COMPARATOR_SELECTION',created_utc=s.utc(),inputs=inputs,
            workers=1,numerical_threads=1,prospective_outcomes_generated=False))
        import check_forecasts
        s.dump(output/'checks.json',check_forecasts.run())
        rows=s.records();packets=s.packets(rows);block=np.array([r['block'] for r in rows]);y=np.array([r['terminal_success'] for r in rows],float)
        s.require(len(rows)==512 and len(set(s.key(r) for r in rows))==512 and set(block)==set(s.CFG['development_blocks']),'Development identity')
        specs=f.candidates();scores=[];predictions=[];fit_receipts=[]
        for spec in specs:
            for heldout in s.CFG['development_blocks']:
                test=block==heldout;train=~test;p,fit=f.fit_predict(spec,rows,packets,y,train,test)
                scores.append(dict(model=spec['id'],role=spec['role'],block=heldout,n=int(test.sum()),brier=float(np.mean((p-y[test])**2))))
                fit_receipts.append(dict(model=spec['id'],heldout_block=heldout,train_blocks=sorted(set(block[train].tolist())),n_train=int(train.sum()),
                    fit_maximum_residual=fit.get('maximum_gradient',fit.get('maximum_residual')),family=spec['family']))
                for i,probability in zip(np.flatnonzero(test),p,strict=True):predictions.append(dict(model=spec['id'],**{k:rows[i][k] for k in s.KEYS},target=int(y[i]),probability=float(probability),brier=float((probability-y[i])**2)))
        ranking=sorted([dict(model=spec['id'],role=spec['role'],brier=float(np.mean([r['brier'] for r in scores if r['model']==spec['id']]))) for spec in specs],key=lambda r:(r['brier'],r['model']))
        expression=next(r['model'] for r in ranking if r['role']=='expression_rival');packet=next(r['model'] for r in ranking if r['role']=='full_record_rival')
        index={(r['model'],r['block']):r['brier'] for r in scores};planning=[]
        for baseline in dict.fromkeys(['expression_history',expression,packet]):
            delta=np.array([index[baseline,b]-index['candidate',b] for b in s.CFG['development_blocks']]);gain=float(delta.mean());sd=float(delta.std(ddof=1));upper=sd*np.sqrt(7/chi2.ppf(.05,7))
            ns=[n for n in range(s.CFG['minimum_test_blocks'],s.CFG['maximum_test_blocks']+1,s.CFG['block_count_multiple']) if power(gain-s.CFG['practical_brier_margin'],sd,n)>=s.CFG['planning_power']]
            planning.append(dict(baseline=baseline,role='full_record_challenge' if baseline==packet else 'primary',gain=gain,block_gains=delta.tolist(),sd=sd,
                normal_theory_upper_sd95=float(upper),suggested_blocks=ns[0] if ns else None,
                power_at_64_point_variance=power(gain-.002,sd,64),power_at_64_upper_variance=power(gain-.002,upper,64)))
        required=[p['suggested_blocks'] for p in planning if p['role']=='primary'];gate=all(n is not None for n in required)
        chosen=max(required) if gate else None
        selected=list(dict.fromkeys(['candidate','expression_history',expression,packet]));fullfits={}
        for name in selected:
            spec=next(r for r in specs if r['id']==name);_,fullfits[name]=f.fit_predict(spec,rows,packets,y,np.ones(512,bool),np.ones(512,bool))
        previous={(r['model'],int(r['block']),r['history'],int(r['founder']),int(r['recipient'])):float(r['refit_probability']) for r in s.table(s.HERE/'source/prior_predictions.csv')}
        max_previous=0.
        for row in predictions:
            if row['model']=='candidate':max_previous=max(max_previous,s.close(row['probability'],previous['expression_unsigned_signed',*s.key(row)],1e-12,'Prior independent refit'))
        result=dict(status='COMPLETE_DEVELOPMENT_SELECTION',classification='OUTCOME_INFORMED_DEVELOPMENT',candidate='candidate',selected_expression_rival=expression,
            selected_full_record_challenge=packet,retained_models=selected,model_grid=specs,ranking=ranking,planning=planning,
            practical_brier_margin=s.CFG['practical_brier_margin'],prospective_design_gate_pass=gate,proposed_test_blocks=chosen,
            power_scope='Approximate normal/t planning from eight exposed cross-validated block differences; no achieved-power or generalization guarantee.',
            maximum_previous_refit_error=max_previous,seconds=time.monotonic()-start,native_test_outcomes_generated=False)
        s.csv_write(output/'scores.csv',scores);s.csv_write(output/'predictions.csv',predictions);s.dump(output/'fit_receipts.json',fit_receipts);s.dump(output/'frozen_models.json',fullfits);s.dump(output/'selection_result.json',result)
        for rel,digest in inputs.items():s.require(s.sha(s.HERE/rel)==digest,'Calibration inputs changed')
        s.dump(output/'COMPLETE.json',dict(status='COMPLETE',utc=s.utc(),seconds=time.monotonic()-start,
            outputs_sha256={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file()},native_test_outcomes_generated=False))
        print(json.dumps({k:result[k] for k in ['status','selected_expression_rival','selected_full_record_challenge','prospective_design_gate_pass','proposed_test_blocks','seconds']},indent=2),flush=True)
    except BaseException:s.dump(output/'FAILED.json',dict(utc=s.utc(),traceback=traceback.format_exc()));raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name');parser.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.execute:
        job=s.read(args.execute/'job.json');execute(Path(job['output']),job['inputs_sha256']);return
    s.require(args.name and args.name.replace('_','').isalnum(),'Unique calibration name')
    sources=s.verify_sources();inputs={name:s.sha(s.HERE/name) for name in sorted([*OWN,*sources])}
    job=s.HERE/'jobs'/args.name;output=s.HERE/'runs'/args.name;s.require(not output.exists(),'Existing calibration output');job.mkdir(parents=True,exist_ok=False)
    for rel,digest in inputs.items():
        target=job/'inputs/TT008'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.HERE/rel,target);s.require(s.sha(target)==digest,'Frozen copy')
    s.dump(job/'job.json',dict(output=str(output),created_utc=s.utc(),inputs_sha256=inputs,classification='DEVELOPMENT_ONLY',native_test_outcomes_generated=False))
    with (job/'console.log').open('x') as log:
        subprocess.run([sys.executable,'-B',str(job/'inputs/TT008/calibrate.py'),'--execute',str(job)],stdout=log,stderr=subprocess.STDOUT,check=True)
    print((output/'selection_result.json').read_text())


if __name__=='__main__':main()
