"""Fixed nested development, all ablations, separate ancestor panel and export."""
from io_utils import *
import models,checks,features,time,traceback,csv,math,signal
from scipy.special import expit

def verify():
    frozen=read(ROOT/'INPUT_FREEZE.json')
    for p,h in frozen['sha256'].items():assert sha(p)==h,p
    return frozen

def score(p,d,mask):
    w=d['weights'][mask];w=w/w.sum();y=d['y'][mask];p=p[mask];clipped=np.clip(p,1e-12,1-1e-12)
    return dict(brier=float(w@((p-y)**2)),log_loss=float(-w@(y*np.log(clipped)+(1-y)*np.log1p(-clipped))),
        mean_probability=float(w@p),observed=float(w@y),bias=float(w@(p-y)),rows=int(mask.sum()))

def main():
    start=time.monotonic();cpu=time.process_time();verify();out=ROOT/'development_v1';out.mkdir()
    limit=read(ROOT/'RUNTIME_PRICE.json')['hard_seconds']
    def timeout(*args):raise TimeoutError('Frozen development hard deadline exceeded')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,limit)
    try:
        data=arrays(ROOT/'DATA.npz');schema=read(ROOT/'FEATURE_SCHEMA.json');c=models.Fits(data,schema)
        y=data['y'];predictions={};fullfits={};selection={};audits=[]
        for family in features.FAMILIES:
            probabilities=np.empty(len(y));family_selection=[]
            for held in BLOCKS:
                train=[b for b in BLOCKS if b!=held];best,grid=c.select(family,train)
                values=c.probabilities(family,train,best['ridge'],best['calibration']);mask=data['blocks']==held
                probabilities[mask]=values[mask]
                fit,_=c.fit(family,train,best['ridge']);training=~mask
                audits.append(dict(family=family,held=held,**checks.audit_fit(c.x[family][training],y[training],data['weights'][training],fit)))
                family_selection.append(dict(held_out_block=held,train_blocks=train,selected=best,grid=grid))
            predictions[family]=probabilities
            best,grid=c.select(family,BLOCKS);fit,_=c.fit(family,BLOCKS,best['ridge'])
            cal=c.calibration(family,BLOCKS,best['ridge'],best['calibration'])
            final=dict(columns=schema['families'][family],base=fit,calibration=cal,training_blocks=BLOCKS,selection=best)
            values=models.export_probability(c.x[family],final)
            assert np.max(abs(values-c.probabilities(family,BLOCKS,best['ridge'],best['calibration'])))<1e-12
            audits.append(dict(family=family,held=None,**checks.audit_fit(c.x[family],y,data['weights'],fit)))
            fullfits[family]=final;selection[family]=dict(outer=family_selection,final=best,final_grid=grid)
            print(json.dumps(dict(event='FAMILY_COMPLETE',family=family,elapsed_seconds=time.monotonic()-start)),flush=True)
        # The original published reference is never refit on any new outcome.
        old=read(ROOT/'TT008_FIXED_REFERENCE.json');idx=[schema['all_columns'].index(k) for k in features.B11]
        x=data['X'][:,idx];raw=(x-np.array(old['scaling']['mean']))/np.array(old['scaling']['scale'])
        predictions['frozen_tt008']=expit(np.c_[np.ones(len(x)),raw]@np.array(old['coefficients']))
        metrics={};allmask=np.ones(len(y),bool)
        for family,p in predictions.items():
            result=dict(overall=score(p,data,allmask),blocks={str(b):score(p,data,data['blocks']==b) for b in BLOCKS},
                conditions={f'{injury}_{regime}':score(p,data,(data['injury']==injury)&(data['noise']==regime))
                    for injury in (12,24,36) for regime in (False,True)},
                original_expression={str(k):score(p,data,data['current_pass']==k) for k in (0,1)},calibration_bins=[])
            for b in range(10):
                mask=(p>=b/10)&((p<(b+1)/10) if b<9 else (p<=1))
                if mask.any():result['calibration_bins'].append(dict(bin=b,weight=float(data['weights'][mask].sum()/data['weights'].sum()),**score(p,data,mask)))
                else:result['calibration_bins'].append(dict(bin=b,weight=0.,rows=0))
            metrics[family]=result
        pairs=[('cheap_all',f) for f in features.FAMILIES if f not in ('cheap_all','plus_parent','plus_grandparent')]
        pairs += [('cheap_all','frozen_tt008'),('plus_parent','cheap_all'),('plus_grandparent','plus_parent'),('plus_grandparent','cheap_all')]
        contrasts=[]
        for candidate,reference in pairs:
            gains=[metrics[reference]['blocks'][str(b)]['brier']-metrics[candidate]['blocks'][str(b)]['brier'] for b in BLOCKS]
            contrasts.append(dict(candidate=candidate,reference=reference,mean_gain=math.fsum(gains)/len(gains),
                block_gains=gains,positive_blocks=sum(g>0 for g in gains),negative_blocks=sum(g<0 for g in gains),
                interpretation='Nested cross-validation on exposed development; no confirmatory p-value'))
        with (out/'PREDICTIONS.csv').open('x',newline='') as f:
            identities=read(ROOT/'IDENTITIES.json');columns=list(identities[0])+['outcome','weight']+list(predictions)
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
            for i,row in enumerate(identities):
                writer.writerow(dict(row,outcome=int(y[i]),weight=float(data['weights'][i]),**{k:float(v[i]) for k,v in predictions.items()}))
        save(out/'PROBABILITIES.npz',predictions)
        artifact=dict(version='TT051_models_v1',created_utc=now(),classification='DEVELOPMENT_TRAINED_FROZEN_FOR_LATER_UNTOUCHED_EVALUATION',
            feature_columns=schema['all_columns'],models=fullfits,main_comparator='cheap_all',
            native_probe_reads=0,training_blocks=BLOCKS,training_namespace='rdt_fresh_equal_read_v0_1 scientific acquisition',
            excluded_from_confirmation=list(range(80)),TT008_test_blocks_excluded=[8800000,8800063],E107_excluded=True,
            expected_future_contract='g14 capture;18 exact rewrites;freshg33;injury/noise declared;original expression-class selection')
        write(out/'MODELS.json',artifact);write(out/'TUNING.json',selection)
        write(out/'FIT_RECEIPTS.json',dict(base=c.receipts,calibration=c.calibration_receipts))
        write(out/'AUDITS.json',dict(status='PASS',selected_fit_audits=audits,exported_probabilities_reproduced=True))
        result=dict(classification='EXPOSED_DEVELOPMENT_ONLY',utc=now(),metrics=metrics,paired_comparisons=contrasts,
            source_blocks=8,source_packets=32,rows=768,fit_count=len(c.receipts),calibration_fit_count=len(c.calibration_receipts),
            fit_cpu_seconds=c.cpu,calibration_cpu_seconds=c.cal_cpu,cpu_seconds=time.process_time()-cpu,
            wall_seconds=time.monotonic()-start,new_native_reads=0,new_terminal_futures=0,
            main_comparator_fixed_before_results=True,selection_not_prospective_confirmation=True)
        write(out/'RESULTS.json',result)
        write(out/'ANCESTOR_COMPARISON.json',dict(classification='LIMITED_PREDICTOR_HISTORY_COMPARISON_NOT_DYNAMICAL_SUFFICIENCY_TEST',
            current_record_generation=14,parent_generation=13,grandparent_generation=12,
            comparisons=[v for v in contrasts if v['candidate'] in ('plus_parent','plus_grandparent')],
            non_Markov_evidence=False,interpretation='Ancestor summaries can improve an incomplete current-state predictor even when full-record transitions satisfy the reset contract.'))
        verify()
        write(out/'MODEL_FREEZE.json',dict(status='FROZEN_FOR_LATER_EVALUATION',utc=now(),model_sha256=sha(out/'MODELS.json'),
            feature_schema_sha256=sha(ROOT/'FEATURE_SCHEMA.json'),input_freeze_sha256=sha(ROOT/'INPUT_FREEZE.json'),
            outcome_scope='all fitting/selection used declared exposed development only',untouched_source_outcomes_opened=False,
            cohort_for_confirmation_reserved=False,simulation_launch_authorized_here=False))
        write(out/'COMPLETE.json',dict(status='COMPLETE',utc=now(),wall_seconds=time.monotonic()-start,
            input_freeze_sha256=sha(ROOT/'INPUT_FREEZE.json'),outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
        print(json.dumps(dict(status='COMPLETE',wall_seconds=time.monotonic()-start,fit_count=len(c.receipts))),flush=True)
    except BaseException:
        write(out/'FAILED.json',dict(utc=now(),traceback=traceback.format_exc()));raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

if __name__=='__main__':main()
