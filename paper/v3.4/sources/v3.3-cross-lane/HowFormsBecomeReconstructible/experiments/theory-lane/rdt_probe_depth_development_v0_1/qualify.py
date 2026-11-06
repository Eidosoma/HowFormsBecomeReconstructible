"""Bounded integration and synthetic fitting/scoring qualification, never science."""
from pc_common import *
import argparse
import signal
import subprocess
import time
from pc_admission import admission
from pc_measure import measure
from pc_run import measurements
from pc_fit import Fits


def main(output):
    started=time.monotonic();output.mkdir(parents=True,exist_ok=False)
    def stop(*_):raise TimeoutError('Qualification hard limit; no retry')
    signal.signal(signal.SIGALRM,stop);signal.alarm(900)
    admitted=admission();write(output/'CPU_ADMISSION.json',admitted)
    require(admitted['available_worker_slots']>=1,'No qualification CPU slot')
    workers=min(2,admitted['available_worker_slots']);deadline=time.time()+900
    code={p.name:sha(p) for p in ROOT.glob('*.py')}
    test=subprocess.run([sys.executable,str(ROOT/'test_development.py')],capture_output=True,text=True,timeout=180)
    write(output/'TESTS.json',dict(status='PASS' if not test.returncode else 'FAIL',stdout=test.stdout,stderr=test.stderr))
    require(test.returncode==0,test.stdout+test.stderr)
    cases=read(ROOT/'prepared/CASES.json');source=read(ROOT/'prepared/SOURCES.json');schema=read(ROOT/'prepared/SCHEMA.json')
    chosen=[cases[i] for i in (0,1,4,5)]
    require({(c['regime'],c['current_pass']) for c in chosen}==set((r,c) for r in REGIMES for c in (0,1)),'Qualification class/regime coverage')
    receipts=measurements(chosen,output/'native',workers,deadline,scope='qualification',n=20)
    partial=measure(chosen[0],output/'partial_batch',deadline,scope='qualification',n=5)
    for r in receipts:
        folder=output/'native'/r['case_id'];raw=load_arrays(folder/'arrays.npz',r['raw_sha256'])
        require(float(raw['terminal_passed'].mean())==r['q2'],'Saved native feature')
        if r['case_id']==partial['case_id']:
            short=load_arrays(output/'partial_batch/arrays.npz',partial['raw_sha256'])
            for name in ('writer2_end','writer2_outgoing','terminal_end','terminal_windows','terminal_outgoing','terminal_passed'):
                require(raw[name][:5].tobytes()==short[name].tobytes(),'Batch-size invariance')
    raw=load_arrays(ROOT/'prepared/FEATURES.npz',source['output_files_sha256']['FEATURES.npz'])
    rng=np.random.default_rng(10720261102)
    x=np.column_stack((raw['cheap'],raw['q'],rng.uniform(size=638)))
    synthetic_y=rng.binomial(1,.6,size=(638,4)).astype(np.uint8)
    data=dict(X=x,y=synthetic_y.mean(axis=1),blocks=np.array([c['fold'] for c in cases]),
              weights=np.array([c['weights']['balanced']/2 for c in cases]))
    fit=Fits(data,schema);t=time.monotonic();cpu=time.process_time();selections=[]
    for held in range(8):
        train=[g for g in range(8) if g!=held];best,_=fit.select('depth2',train)
        artifact=fit.fit_export('depth2',train,best,schema['families']['depth2'])
        mask=data['blocks']==held;cols=[schema['all_columns'].index(n) for n in artifact['columns']]
        a=fit.math.export_probability(x[mask][:,cols],artifact)
        b=fit.inner.probabilities('depth2',train,best['ridge'],best['calibration'])[mask]
        require(np.max(abs(a-b))<1e-12,'Synthetic exported-model inference')
        selections.append(best)
    best,_=fit.select('depth2',list(range(8)));fit.fit_export('depth2',list(range(8)),best,schema['families']['depth2'])
    fit_cost=dict(wall_seconds=time.monotonic()-t,cpu_seconds=time.process_time()-cpu,
                  base_fits=len(fit.inner.receipts),calibration_fits=len(fit.inner.calibration_receipts))
    write(output/'SYNTHETIC_FIT.json',dict(classification='SYNTHETIC_TARGETS_ONLY_NO_SCIENTIFIC_MODEL',
        family='depth2',feature_dimension=71,cost=fit_cost,selections=selections))
    # Exercise the full score/calibration/export path with synthetic probabilities/targets.
    fixture=output/'synthetic_scoring';(fixture/'fitting').mkdir(parents=True)
    names=[*FAMILIES,*['archived_e107_'+n for n in LEGACY],*['fixed_tt051_'+n for n in ORDINARY],'constant']
    probabilities=rng.uniform(.001,.999,size=(638,len(names)));probabilities[:,-1]=443/512
    save_arrays(fixture/'fitting/SCORING.npz',dict(probability=probabilities,y=synthetic_y,cheap=raw['cheap'],
        q=x[:,-4:],block=np.array([c['block'] for c in cases]),fold=data['blocks'],
        current_pass=np.array([c['current_pass'] for c in cases]),regime=np.array([REGIMES.index(c['regime']) for c in cases]),
        weights=np.array([[c['weights'][p] for p in PROFILES] for c in cases])))
    write(fixture/'fitting/SCORING_SCHEMA.json',dict(models=names))
    write_csv(fixture/'fitting/HELD_FOLD_PREDICTIONS.csv',[dict(qualification_only=True)])
    write(fixture/'fitting/PREDICTION_SEAL.json',dict(predictions_sha256=sha(fixture/'fitting/HELD_FOLD_PREDICTIONS.csv')))
    write(fixture/'fitting/COMPLETE.json',dict(status='SYNTHETIC_FIXTURE_NOT_A_FIT'))
    from pc_score import main as score
    t=time.monotonic();scored=score(fixture,deadline);score_seconds=time.monotonic()-t
    report=fixture/'analysis/REPORT.txt'
    report.write_text('QUALIFICATION ONLY: SYNTHETIC TARGETS AND PROBABILITIES. NOT SCIENTIFIC EVIDENCE.\n\n'+report.read_text())
    fake_summary=read(fixture/'analysis/SUMMARY.json')
    fake_summary.update(qualification_only=True,targets_and_probabilities_synthetic=True,scientific_result=False)
    with (fixture/'analysis/SUMMARY.json').open('w') as f:json.dump(fake_summary,f,indent=2);f.write('\n')
    for row in csv_rows(fixture/'analysis/summary.csv'):
        m=names.index(row['model']);ri=REGIMES.index(row['regime']);profile=row['profile']
        w=np.array([c['weights'][profile]*(REGIMES.index(c['regime'])==ri) for c in cases])
        expected=float((w[:,None]*(probabilities[:,m,None]-synthetic_y)**2).sum()/(4*w.sum()))
        require(abs(expected-float(row['brier']))<1e-12,'Synthetic full scoring path')
    for name,digest in code.items():require(sha(ROOT/name)==digest,'Qualification source edited while running')
    files={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='STATUS.json'}
    write(output/'OUTPUTS.json',dict(sha256=files))
    result=dict(status='PASS',utc=utc(),classification='QUALIFICATION_NOT_SCIENTIFIC_RESULTS',
        code_sha256=code,prepared_source_sha256=sha(ROOT/'prepared/SOURCES.json'),tests=9,native_cases=4,
        partial_batch_check=True,new_qualification_native_reads=170,flat_reads=10,
        native_receipts=receipts,synthetic_fit_cost=fit_cost,synthetic_scoring_wall_seconds=score_seconds,
        complete_scoring_groups=len(csv_rows(fixture/'analysis/summary.csv')),
        real_target_values_read=False,automatic_development_launch=False,
        wall_seconds=time.monotonic()-started,output_manifest_sha256=sha(output/'OUTPUTS.json'))
    write(output/'COMPLETE.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('native_receipts','code_sha256')}),flush=True)
    signal.alarm(0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
