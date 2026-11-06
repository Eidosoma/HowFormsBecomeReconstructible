"""Nested grouped fits; fractional targets preserve individual-future Brier."""
from pc_common import *
import time


def future_brier(p,ybar):
    return np.asarray(p)**2-2*np.asarray(p)*np.asarray(ybar)+np.asarray(ybar)


class Fits:
    def __init__(self,data,schema):
        _,self.math=cheap()
        self.inner=self.math.Fits(data,schema)
        self.data=data

    def select(self,family,train):
        train=tuple(sorted(train));results=[]
        for ridge in self.math.RIDGES:
            scores={c:[] for c in self.math.CALIBRATIONS}
            for held in train:
                keep=[b for b in train if b!=held]
                mask=self.data['blocks']==held;w=self.data['weights'][mask];w=w/w.sum()
                for cal in self.math.CALIBRATIONS:
                    p=self.inner.probabilities(family,keep,ridge,cal)[mask]
                    scores[cal].append(float(w@future_brier(p,self.data['y'][mask])))
            for cal,losses in scores.items():
                results.append(dict(ridge=ridge,calibration=cal,brier=float(np.mean(losses)),
                                    validation_folds=list(train),fold_losses=losses))
        best=min(results,key=lambda r:(r['brier'],self.math.CALIBRATIONS.index(r['calibration']),-r['ridge']))
        return best,results

    def fit_export(self,family,train,chosen,columns):
        fit,_=self.inner.fit(family,train,chosen['ridge'])
        cal=self.inner.calibration(family,train,chosen['ridge'],chosen['calibration'])
        return dict(columns=columns,base=fit,calibration=cal,selection=chosen,training_folds=list(train))


def build_targets(cases):
    source=read(ROOT/'prepared/SOURCES.json')
    path=Path(source['target_outcome_source'])
    require(sha(path)==source['target_outcome_sha256'],'Saved target outcome identity')
    mapping={}
    for row in csv_rows(path):
        key=(row_key(row),row['regime'],int(row['replicate']))
        require(key not in mapping,'Duplicate target identity')
        mapping[key]=int(row['terminal_success'])
    y=np.array([[mapping[(tuple(c['key']),c['regime'],r)] for r in range(4)] for c in cases],dtype=np.uint8)
    require(len(mapping)==y.size==2552 and np.isin(y,[0,1]).all(),'All individual binary futures')
    return y


def fit_all(run,receipts,deadline):
    started=time.process_time();wall=time.monotonic()
    folder=Path(run)/'fitting';folder.mkdir()
    source=read(ROOT/'prepared/SOURCES.json');cases=read(ROOT/'prepared/CASES.json');schema=read(ROOT/'prepared/SCHEMA.json')
    raw=load_arrays(ROOT/'prepared/FEATURES.npz',source['output_files_sha256']['FEATURES.npz'])
    require({r['case_id'] for r in receipts}=={c['case_id'] for c in cases},'Complete depth-two feature cohort')
    byid={r['case_id']:r for r in receipts}
    q2=np.array([byid[c['case_id']]['q2'] for c in cases])
    x=np.column_stack((raw['cheap'],raw['q'],q2));y=build_targets(cases);ybar=y.mean(axis=1)
    groups=np.array([c['fold'] for c in cases]);weights=np.array([c['weights']['balanced']/2 for c in cases])
    require(abs(weights.sum()-1)<1e-12 and x.shape==(638,74),'Complete model matrix and weights')
    data=dict(X=x,y=ybar,weights=weights,blocks=groups)
    fits=Fits(data,schema)
    predictions=np.full((638,len(FAMILIES)),np.nan);outer_models={};selections=[]
    for col,family in enumerate(FAMILIES):
        outer_models[family]={}
        for held in range(8):
            require(time.time()<deadline,'Fitting deadline')
            train=[b for b in range(8) if b!=held]
            chosen,candidates=fits.select(family,train)
            p=fits.inner.probabilities(family,train,chosen['ridge'],chosen['calibration'])
            mask=groups==held;predictions[mask,col]=p[mask]
            artifact=fits.fit_export(family,train,chosen,schema['families'][family])
            features=x[mask][:,[schema['all_columns'].index(n) for n in artifact['columns']]]
            independent=fits.math.export_probability(features,artifact)
            require(np.max(abs(independent-p[mask]))<1e-12,'Scalar exported model prediction')
            artifact['training_source_blocks']=[b for b in range(80) if b%8!=held]
            outer_models[family][str(held)]=artifact
            selections.append(dict(family=family,held_fold=held,chosen=chosen,candidates=candidates))
    require(np.isfinite(predictions).all() and np.all((predictions>=0)&(predictions<=1)),'Complete held-fold probabilities')
    pred_rows=[]
    for i,c in enumerate(cases):
        pred_rows.append(dict(case_id=c['case_id'],block=c['block'],fold=c['fold'],regime=c['regime'],
            current_pass=c['current_pass'],**{name:float(predictions[i,j]) for j,name in enumerate(FAMILIES)}))
    # This is an explicit scoring barrier, not a claim that these old targets were untouched.
    write_csv(folder/'HELD_FOLD_PREDICTIONS.csv',pred_rows)
    write(folder/'OUTER_MODELS.json',outer_models)
    write(folder/'INNER_SELECTION.json',selections)
    write(folder/'PREDICTION_SEAL.json',dict(utc=utc(),predictions_sha256=sha(folder/'HELD_FOLD_PREDICTIONS.csv'),
        outer_models_sha256=sha(folder/'OUTER_MODELS.json'),status='POST_HOC_HELD_FOLD_PREDICTIONS_BEFORE_AGGREGATE_SCORING',
        source_blocks=80,folds=8,previously_exposed_targets=True))
    final={};final_selection=[]
    for family in FAMILIES:
        require(time.time()<deadline,'Final-fit deadline')
        chosen,candidates=fits.select(family,list(range(8)))
        final[family]=fits.fit_export(family,list(range(8)),chosen,schema['families'][family])
        final[family]['training_source_blocks']=list(range(80))
        final_selection.append(dict(family=family,chosen=chosen,candidates=candidates))
    inference_cost=[]
    for family,model in final.items():
        positions=[schema['all_columns'].index(n) for n in model['columns']]
        begin=time.process_time();t0=time.monotonic()
        for _ in range(10):fits.math.export_probability(x[:,positions],model)
        inference_cost.append(dict(family=family,cases=638,repeats=10,
            cpu_seconds_per_case=(time.process_time()-begin)/6380,
            wall_seconds_per_case=(time.monotonic()-t0)/6380,feature_construction_included=False))
    write(folder/'INFERENCE_COSTS.json',inference_cost)
    write(folder/'MODELS.json',dict(models=final,classification='DEVELOPMENT_CANDIDATES_NOT_CONFIRMATION',
        source_blocks=list(range(80)),features=schema['all_columns'],target='18 exact rewrites then fresh g33 read'))
    write(folder/'FINAL_SELECTION.json',final_selection)
    write(folder/'MODEL_FREEZE.json',dict(utc=utc(),model_sha256=sha(folder/'MODELS.json'),
        development_freeze_sha256=sha(ROOT/'FREEZE.json'),fresh_confirmation_launched=False,
        source_case_manifest_sha256=sha(ROOT/'prepared/CASES.json')))
    write(folder/'FIT_RECEIPTS.json',dict(base_fits=fits.inner.receipts,calibrations=fits.inner.calibration_receipts,
        group_ids_are_folds=True,actual_source_blocks_by_fold={str(f):list(range(f,80,8)) for f in range(8)},
        base_cpu_seconds=fits.inner.cpu,calibration_cpu_seconds=fits.inner.cal_cpu))
    _,maths=cheap();fixed=read(ROOT/'comparator/MODELS.json')
    fixed_probability=np.column_stack([maths.export_probability(x[:,[schema['all_columns'].index(n) for n in fixed['models'][name]['columns']]],fixed['models'][name]) for name in ORDINARY])
    all_p=np.column_stack((predictions,raw['legacy_probability'],fixed_probability,np.full(638,443/512)))
    names=[*FAMILIES,*['archived_e107_'+n for n in LEGACY],*['fixed_tt051_'+n for n in ORDINARY],'constant']
    save_arrays(folder/'SCORING.npz',dict(probability=all_p,y=y,cheap=raw['cheap'],q=np.column_stack((raw['q'],q2)),
        block=np.array([c['block'] for c in cases]),fold=groups,current_pass=np.array([c['current_pass'] for c in cases]),
        regime=np.array([REGIMES.index(c['regime']) for c in cases]),weights=np.array([[c['weights'][p] for p in PROFILES] for c in cases])))
    write(folder/'SCORING_SCHEMA.json',dict(models=names,profiles=list(PROFILES),regimes=list(REGIMES),families=list(FAMILIES),
        known_related_source_exposure={'fixed_tt051':'Blocks 0..7 are related to its development. Descriptive reference, not held-out qualification.'}))
    result=dict(status='COMPLETE',cpu_seconds=time.process_time()-started,wall_seconds=time.monotonic()-wall,
                base_fits=len(fits.inner.receipts),calibration_fits=len(fits.inner.calibration_receipts),
                held_predictions=predictions.size,final_models=len(final))
    write(folder/'COMPLETE.json',result)
    return result
