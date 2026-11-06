"""Reproduce E107 and expand its selected panel using archived acquisition counts.

No native modules imported, no dynamics, no refitting, no predictor recalibration.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import json
import math
import time
import numpy as np
from scipy.stats import t

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent/'rdt_fresh_equal_read_v0_1'
RUN=STUDY/'runs/scientific_v1'
INPUTS=STUDY/'jobs/qualification_v1/inputs'
MODELS=['successor32','direct64','pooled32','direct8','tt008']
ALL_MODELS=MODELS+['development_constant']
REGIMES=['matched','independent']
PROFILES=['balanced','balanced_fail','balanced_pass','population','population_fail','population_pass']
SEED=10720261101
BOOTSTRAPS=10000


def utc():return datetime.now(timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())


def write_json(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def write_csv(path,rows):
    assert rows
    with Path(path).open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


class Evidence:
    def __init__(self):
        self.consumed={}
        self.complete=self.direct(RUN/'COMPLETE.json')
        assert self.complete['status']=='COMPLETE' and self.complete['scope']=='scientific'
        assert self.complete['new_model_fits']==self.complete['synthetic_outcomes']==0
        self.output=self.direct(RUN/'OUTPUTS.json',self.complete['output_manifest_sha256'])['sha256']
        self.input=self.direct(INPUTS/'INPUTS.json',self.complete['input_manifest_sha256'])['sha256']
        old=self.direct(HERE/'INTAKE.json')
        assert sha(RUN/'COMPLETE.json')==old['complete_sha256']
        assert self.complete['forecast_seal_sha256']==old['seal_sha256']

    def raw(self,path,expected=None):
        raw=path.read_bytes();h=digest(raw)
        if expected is not None:assert h==expected,str(path)
        self.consumed[str(path)]=dict(sha256=h,bytes=len(raw),resolved_path=str(path.resolve()))
        return raw

    def direct(self,path,expected=None):return json.loads(self.raw(path,expected))
    def output_json(self,name):return self.direct(RUN/name,self.output[name])
    def input_json(self,name):return self.direct(INPUTS/name,self.input[name])

    def reference(self,ref):
        name=ref['path']+'/COMMIT.json'
        assert not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts
        result=self.output_json(name)
        assert self.output[name]==ref['commit_sha256']
        return result


def scalar_probability(forecast,model,name):
    x=list(forecast['boundary'])
    if name!='tt008':x.append(forecast['fractions'][name])
    m=model['model'];sc=m['scaling'];coef=m['coefficients']
    assert len(x)==len(sc['mean'])==len(sc['scale'])==len(coef)-1
    eta=math.fsum([coef[0]]+[b*(v-mu)/sd for v,b,mu,sd in zip(x,coef[1:],sc['mean'],sc['scale'],strict=True)])
    return 1/(1+math.exp(-eta)) if eta>=0 else math.exp(eta)/(1+math.exp(eta))


def select(rows):
    result=[]
    for c in (0,1):
        group=[r for r in rows if r['current_pass']==c]
        by_rule=[[r for r in group if r['rule']==s] for s in (-1,1)]
        if all(by_rule):result.extend(min(v,key=lambda r:r['selection_hash']) for v in by_rule)
        else:result.extend(sorted(group,key=lambda r:r['selection_hash'])[:2])
    return result


def recover():
    ev=Evidence();protocol=ev.input_json('protocol.json')
    native=ev.input_json('qualified/native/protocol.json')
    models=ev.input_json('qualified/FROZEN_MODELS.json')['models']
    assert ev.input['qualified/FROZEN_MODELS.json']==protocol['models_sha256']
    sources=ev.input_json('qualified/SOURCE_BINDINGS.json')['files']
    raw=ev.raw(INPUTS/'qualified/context/DATA.npz',sources['DATA.npz']['sha256'])
    assert sources['DATA.npz']['sha256']==ev.input['qualified/context/DATA.npz']
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:
        dev_y=z['y'];dev_blocks=z['blocks']
        assert len(dev_y)==512 and set(dev_blocks)==set(range(34000,34008))
        assert np.isin(dev_y,[0,1]).all() and all((dev_blocks==b).sum()==64 for b in set(dev_blocks))
        constant=float(dev_y.mean())
    assert constant==443/512
    seal=ev.output_json('forecast_seal/FORECAST_SEAL.json')
    assert ev.output['forecast_seal/FORECAST_SEAL.json']==ev.complete['forecast_seal_sha256']
    assert seal['all_forecasts_independently_checked_before_any_future']
    plan=ev.output_json('selection/COHORT.json')
    assert plan['rows']==seal['rows'] and plan['blocks']==seal['blocks']==list(range(80))
    assert plan['attempted_blocks']==list(range(80)) and not plan['ineligible_blocks'] and not plan['surplus_blocks']
    all_rows=[];selection=[]
    for ref in plan['acquisitions']:
        commit=ev.reference(ref);rows=commit['payload']['rows'];b=commit['payload']['block']
        enrolled=ev.output_json(ref['path']+'/ENROLLMENT.json');assert enrolled['rows']==rows
        assert len(rows)==64 and len({tuple(r['key']) for r in rows})==64
        assert {tuple(r['key']) for r in rows}=={(b,h,f,r) for h in native['acquisition']['histories'] for f in range(4) for r in range(4)}
        assert {r['current_pass'] for r in rows}=={0,1}
        for row in rows:
            assert row['key']==[b,row['history'],row['founder'],row['recipient']]
            assert row['rule']==(1 if row['founder']%2==0 else -1)
            assert row['boundary'][4]==min(row['boundary'][:4])
            assert row['current_pass']==row['boundary'][5]==int(row['boundary'][4]>.25)
            ranking=json.dumps([protocol['namespace']+'/selection',*row['key']],separators=(',',':')).encode()
            assert digest(ranking)==row['selection_hash']
        selection.extend(select(rows));all_rows.extend(rows)
    assert selection==plan['rows'] and len(all_rows)==5120 and len(selection)==319
    forecasts=[]
    for ref in seal['measurements']:
        commit=ev.reference(ref);assert commit['utc']<seal['utc']
        forecasts.extend(commit['payload']['forecasts'])
    assert forecasts==seal['forecasts'] and len(forecasts)==638
    metadata={tuple(r['key']):r for r in selection}
    fp={};maximum_error=0.
    for record in forecasts:
        key=(tuple(record['key']),record['regime']);assert key not in fp
        assert all(record[k]==v for k,v in metadata[key[0]].items())
        assert set(record['probabilities'])==set(MODELS)
        for name in MODELS:
            p=record['probabilities'][name];assert 0<=p<=1
            error=abs(p-scalar_probability(record,models[name],name));maximum_error=max(error,maximum_error)
        fp[key]=record
    assert maximum_error<1e-12
    refs=ev.output_json('FUTURE_REFERENCES.json');labels=[];starts=[]
    for ref in refs:
        commit=ev.reference(ref);start=ev.output_json(ref['path']+'/START.json')
        assert start['utc']>seal['utc'];starts.append(start['utc'])
        labels.extend(commit['payload']['outcomes'])
    assert labels==ev.output_json('OUTCOMES.json') and len(labels)==2552
    lookup={}
    for row in labels:
        key=(tuple(row['key']),row['regime'],row['replicate']);assert key not in lookup
        assert row['passed']==int(row['margin']>.25)
        lookup[key]=row
    expected={(tuple(r['key']),g,j) for r in selection for g in REGIMES for j in range(4)}
    assert set(lookup)==expected
    p=np.array([[[fp[(tuple(r['key']),g)]['probabilities'][m] for m in MODELS]+[constant] for r in selection] for g in REGIMES])
    y=np.array([[[lookup[(tuple(r['key']),g,j)]['passed'] for j in range(4)] for r in selection] for g in REGIMES],float)
    audit=ev.direct(STUDY/'checks/SCIENTIFIC_V1_EVIDENCE_AUDIT.json')
    assert audit['status']=='PASS' and audit['complete_sha256']==sha(RUN/'COMPLETE.json')
    assert audit['output_manifest_sha256']==sha(RUN/'OUTPUTS.json')
    original=ev.output_json('ANALYSIS.json');resources=ev.output_json('RESOURCES.json')
    return dict(evidence=ev,protocol=protocol,rows=selection,all_rows=all_rows,forecasts=forecasts,
                labels=labels,p=p,y=y,original=original,constant=constant,resources=resources,
                seal_utc=seal['utc'],first_future_utc=min(starts),maximum_probability_error=maximum_error,
                completed_original_dynamics_audit=audit)


def weights(acquisition,selected):
    full=Counter((r['block'],r['current_pass'],r['rule']) for r in acquisition)
    sample=Counter((r['block'],r['current_pass'],r['rule']) for r in selected)
    byclass=Counter((r['block'],r['current_pass']) for r in selected)
    assert all(sample[k]>0 for k,n in full.items() if n)
    B=len({r['block'] for r in selected});w=[];info=[]
    for r in selected:
        cell=(r['block'],r['current_pass'],r['rule']);N,n=full[cell],sample[cell]
        expansion=N/n;balanced=1/(B*2*byclass[cell[:2]])
        info.append(dict(block=r['block'],history=r['history'],founder=r['founder'],recipient=r['recipient'],
            current_pass=r['current_pass'],rule=r['rule'],cell_acquired=N,cell_selected=n,
            inclusion_probability_analogue=n/N,expansion=expansion))
        w.append((balanced,expansion))
    w=np.array(w);c=np.array([r['current_pass'] for r in selected])
    result={}
    for name,column in [('balanced',0),('population',1)]:
        a=w[:,column]
        result[name]=a/a.sum()
        for cls,label in [(0,'fail'),(1,'pass')]:
            z=a*(c==cls);result[name+'_'+label]=z/z.sum()
    for i,row in enumerate(info):
        row.update({name:float(result[name][i]) for name in PROFILES})
    assert np.isclose(w[:,1].sum(),len(acquisition))
    assert np.isclose(sum(w[i,1] for i in range(len(c)) if c[i]==0),sum(r['current_pass']==0 for r in acquisition))
    cells=[]
    for b in sorted({r['block'] for r in acquisition}):
        for cls in (0,1):
            for rule in (-1,1):
                key=(b,cls,rule);N,n=full[key],sample[key]
                cells.append(dict(block=b,current_pass=cls,rule=rule,acquired=N,selected=n,
                    supported=(N==0 or n>0),inclusion_probability_analogue=n/N if N else None,
                    expansion=N/n if n else None))
    return result,info,cells


def block_sum(values,weight,blocks,B=80):
    v=np.asarray(values)
    if v.ndim==1:v=v[:,None]
    a=np.zeros((B,v.shape[1]));np.add.at(a,blocks,v*weight[:,None]);return a


def estimate(values,weight,blocks,draw_counts):
    num=block_sum(values,weight,blocks,len(draw_counts[0]))
    den=np.bincount(blocks,weights=weight,minlength=len(draw_counts[0]))
    boot_den=draw_counts@den
    valid=boot_den>0
    boot=np.full((len(draw_counts),num.shape[1]),np.nan)
    boot[valid]=(draw_counts[valid]@num)/boot_den[valid,None]
    mean=num.sum(0)/den.sum() if den.sum()>0 else np.full(num.shape[1],np.nan)
    return mean,boot,num,den


def bounds(values):
    values=np.asarray(values);v=values[np.isfinite(values)]
    return np.quantile(v,[.025,.975]).tolist() if len(v) else [None,None]


def original_t(values):
    mean=float(np.mean(values));radius=float(t.ppf(.975,len(values)-1)*np.std(values,ddof=1)/math.sqrt(len(values)))
    return mean,mean-radius,mean+radius


def summarize(data,output):
    rows=data['rows'];blocks=np.array([r['block'] for r in rows]);y=data['y'];p=data['p']
    ws,weight_rows,cells=weights(data['all_rows'],rows)
    idx=np.random.default_rng(SEED).integers(0,80,(BOOTSTRAPS,80))
    draws=np.array([np.bincount(v,minlength=80) for v in idx],float)
    summary=[];contrasts=[];calibration=[];block_rows=[];contributions=[];reproduction=[]
    profile_meta={}
    for profile in PROFILES:
        w=ws[profile];active=w>0
        mass=np.bincount(blocks,weights=w,minlength=80)
        profile_meta[profile]=dict(selected_records=int(active.sum()),represented_blocks=int((mass>0).sum()),
            current_failure_weight=float(w[np.array([r['current_pass']==0 for r in rows])].sum()),
            max_packet_weight=float(w.max()),kish_packet_weight_size=float(1/(w@w)),
            max_block_weight=float(mass.max()),kish_block_weight_size=float(1/(mass@mass)))
        for g,regime in enumerate(REGIMES):
            losses=((p[g,:,:,None]-y[g,:,None,:])**2).mean(-1)
            observed=y[g].mean(-1)
            values=np.column_stack((losses,observed,p[g]))
            mean,boot,num,den=estimate(values,w,blocks,draws)
            reference=mean[5];reference_boot=boot[:,5]
            ece=np.zeros(6);ece_boot=np.zeros((BOOTSTRAPS,6))
            for m,model in enumerate(ALL_MODELS):
                bins=np.minimum((p[g,:,m]*10).astype(int),9)
                for bin_id in range(10):
                    mask=bins==bin_id;weight=w*mask
                    binmass=float(weight.sum())
                    if binmass:
                        bm,bb,bn,bd=estimate(np.column_stack((p[g,:,m],observed,losses[:,m])),weight,blocks,draws)
                        boot_mass=(draws@bd)/(draws@den)
                        bias=bm[0]-bm[1];bias_boot=bb[:,0]-bb[:,1]
                        ece[m]+=binmass*abs(bias)
                        ece_boot[:,m]+=np.nan_to_num(boot_mass*abs(bias_boot),nan=0.)
                        pr,ob,bs=map(float,bm);valid=int(np.isfinite(bb[:,0]).sum())
                        pr_ci=bounds(bb[:,0]);ob_ci=bounds(bb[:,1]);bs_ci=bounds(bb[:,2]);bias_ci=bounds(bias_boot)
                    else:
                        pr=ob=bs=bias=None;valid=0
                        pr_ci=ob_ci=bs_ci=bias_ci=[None,None]
                    record=dict(profile=profile,regime=regime,model=model,bin=bin_id,lower=bin_id/10,upper=(bin_id+1)/10,
                        weight=binmass,packets=int((mask&active).sum()),blocks=len(set(blocks[mask&active])),
                        predicted=pr,observed=ob,brier=bs,bias=bias,
                        predicted_low=pr_ci[0],predicted_high=pr_ci[1],observed_low=ob_ci[0],observed_high=ob_ci[1],
                        brier_low=bs_ci[0],brier_high=bs_ci[1],bias_low=bias_ci[0],bias_high=bias_ci[1],
                        valid_bootstraps=valid,empty_bootstraps=BOOTSTRAPS-valid)
                    calibration.append(record)
                    if profile=='balanced' and model in MODELS:
                        old=data['original']['regimes'][regime]['calibration'][model][bin_id]
                        for name in ['weight','predicted','observed','brier']:
                            a=record[name];b=old[name]
                            assert (a is None and b is None) or (a is not None and b is not None and abs(a-b)<2e-12),(regime,model,bin_id,name)
                        assert record['packets']==old['packets']
            for m,model in enumerate(ALL_MODELS):
                score=float(mean[m]);skill=float(1-score/reference)
                skill_boot=1-boot[:,m]/reference_boot
                bi=bounds(boot[:,m]);si=bounds(skill_boot);pi=bounds(boot[:,6])
                mi=bounds(boot[:,7+m]);bias=float(mean[7+m]-mean[6]);ci=bounds(boot[:,7+m]-boot[:,6]);ei=bounds(ece_boot[:,m])
                row=dict(profile=profile,regime=regime,model=model,brier=score,brier_low=bi[0],brier_high=bi[1],
                    terminal_success=float(mean[6]),terminal_success_low=pi[0],terminal_success_high=pi[1],
                    mean_prediction=float(mean[7+m]),mean_prediction_low=mi[0],mean_prediction_high=mi[1],
                    calibration_bias=bias,calibration_bias_low=ci[0],calibration_bias_high=ci[1],
                    ece10=float(ece[m]),ece10_low=ei[0],ece10_high=ei[1],
                    constant_probability=data['constant'],constant_brier=float(reference),brier_skill=skill,
                    brier_skill_low=si[0],brier_skill_high=si[1],
                    current_failure_weight=profile_meta[profile]['current_failure_weight'],
                    inference='retrospective paired source-block bootstrap; conditional on frozen fits')
                summary.append(row)
                for b in range(80):
                    block_rows.append(dict(profile=profile,regime=regime,block=b,model=model,
                        block_weight=float(den[b]),brier_numerator=float(num[b,m]),
                        success_numerator=float(num[b,6]),prediction_numerator=float(num[b,7+m])))
                if model!='successor32':
                    gains=boot[:,m]-boot[:,0];gi=bounds(gains)
                    constant_gains=boot[:,5]-boot[:,m]
                    record=dict(profile=profile,regime=regime,rival=model,candidate='successor32',
                        gain=float(mean[m]-mean[0]),bootstrap_low=gi[0],bootstrap_high=gi[1],
                        original_t_low=None,original_t_high=None,original_margin=None,original_decision=None,
                        role='retrospective extension')
                    if profile=='balanced' and model in MODELS:
                        old=data['original']['regimes'][regime]['contrasts'][model]
                        bg=(num[:,m]-num[:,0])*80
                        average,lo,hi=original_t(bg)
                        np.testing.assert_allclose(bg,old['block_gains'],rtol=0,atol=2e-12)
                        np.testing.assert_allclose([average,lo,hi],[old['mean_gain'],old['lower'],old['upper']],rtol=0,atol=2e-12)
                        margin=old['margin'];decision='SUPPORTED' if lo>margin else 'REJECTED' if hi<=margin else 'UNRESOLVED'
                        assert decision==old['decision']
                        record.update(original_t_low=lo,original_t_high=hi,original_margin=margin,original_decision=decision,
                            role='unchanged original primary' if model in ('direct64','pooled32') else 'unchanged original secondary')
                    contrasts.append(record)
                if profile in ('balanced','population'):
                    for field in ('current_pass','history','rule'):
                        for level in sorted({r[field] for r in rows}):
                            mask=np.array([r[field]==level for r in rows]);wm=float(w[mask].sum())
                            loss_mass=float(w[mask]@losses[mask,m]);gain_mass=float(w[mask]@(losses[mask,m]-losses[mask,0]))
                            contributions.append(dict(profile=profile,regime=regime,field=field,level=level,model=model,
                                weight=wm,selected_packets=int((mask&active).sum()),loss_mass=loss_mass,
                                conditional_brier=loss_mass/wm if wm else None,gain_mass_vs_successor32=gain_mass))
                            if profile=='balanced' and field in ('current_pass','history') and model in MODELS:
                                old=data['original']['regimes'][regime]['strata'][field][str(level)]
                                assert abs(wm-old['weight'])<2e-12 and abs(loss_mass-old['loss_mass'][model])<2e-12
                                if model!='successor32':assert abs(gain_mass-old['gain_mass'][model])<2e-12
                if profile=='balanced' and model in MODELS:
                    old=data['original']['regimes'][regime]
                    assert abs(score-old['brier'][model])<2e-12 and abs(mean[6]-old['observed_success'])<2e-12
                    reproduction.append(dict(regime=regime,model=model,absolute_brier_error=abs(score-old['brier'][model])))
    # Explicit paired model-vs-constant intervals, not ratios of separate uncertainty limits.
    baseline_contrasts=[]
    for profile in PROFILES:
        w=ws[profile]
        for g,regime in enumerate(REGIMES):
            losses=((p[g,:,:,None]-y[g,:,None,:])**2).mean(-1)
            mean,boot,_,_=estimate(losses,w,blocks,draws)
            for m,model in enumerate(MODELS):
                lo,hi=bounds(boot[:,5]-boot[:,m])
                baseline_contrasts.append(dict(profile=profile,regime=regime,model=model,
                    constant_minus_model_brier=float(mean[5]-mean[m]),low=lo,high=hi))
    verdict=data['original']['decision']
    assert verdict=='ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED'
    originals=[r for r in contrasts if r['role']=='unchanged original primary']
    assert len(originals)==4 and all(r['original_decision']=='SUPPORTED' for r in originals)
    result=dict(status='COMPLETE_RETROSPECTIVE_REPORTING',utc=utc(),original_verdict_unchanged=verdict,
        selected_blocks=80,selected_records=319,future_outcomes=2552,acquired_records=5120,
        acquired_current_fail=868,acquired_current_pass=4252,acquired_current_failure_prevalence=868/5120,
        ineligible_blocks=0,surplus_blocks=0,constant=dict(value=data['constant'],successes=443,development_records=512,
            development_blocks=list(range(34000,34008)),applied_unchanged_to=REGIMES,
            baseline_definition_retrospective=True,source_regime='matched development; not recalibrated to independent futures'),
        weights=profile_meta,bootstrap=dict(samples=BOOTSTRAPS,seed=SEED,unit='source block',paired=True,
            additional_intervals='pointwise percentile, retrospective; no subgroup qualification'),
        summary=summary,comparisons=contrasts,baseline_comparisons=baseline_contrasts,
        original_reproduction=reproduction,calibration_file='calibration.csv',block_contributions_file='block_scores.csv',
        new_native_reads=0,new_model_fits=0,predictions_recalibrated=False)
    output.mkdir()
    for name,records in [('summary',summary),('contrasts',contrasts),('constant_contrasts',baseline_contrasts),
                         ('calibration',calibration),('block_scores',block_rows),('weights',weight_rows),
                         ('selection_cells',cells),('subgroup_contributions',contributions)]:
        write_csv(output/(name+'.csv'),records)
    keys=['block','history','founder','recipient','rule','current_pass','selection_hash','packet_sha256']
    selected_keys={tuple(r['key']) for r in rows}
    acquired=[dict(**{k:r[k] for k in keys},current_margin=r['boundary'][4],selected=tuple(r['key']) in selected_keys) for r in data['all_rows']]
    write_csv(output/'acquisition.csv',acquired)
    forecast_rows=[]
    for f in data['forecasts']:
        row={k:f[k] for k in keys};row['regime']=f['regime']
        row.update({f'boundary_{i}':v for i,v in enumerate(f['boundary'])})
        row.update({'p_'+m:f['probabilities'][m] for m in MODELS})
        row.update({'q_'+m:f['fractions'][m] for m in MODELS});forecast_rows.append(row)
    write_csv(output/'forecasts.csv',forecast_rows)
    rows_by_key={tuple(r['key']):r for r in rows}
    outcomes=[]
    for yrow in data['labels']:
        row=rows_by_key[tuple(yrow['key'])]
        outcomes.append(dict(**{k:row[k] for k in ['block','history','founder','recipient','rule','current_pass']},
            regime=yrow['regime'],replicate=yrow['replicate'],terminal_success=yrow['passed'],terminal_margin=yrow['margin']))
    write_csv(output/'outcomes.csv',outcomes)
    write_json(output/'SUMMARY.json',result)
    write_json(output/'ORIGINAL_ANALYSIS.json',data['original'])
    write_json(output/'FIXED_BASELINE.json',result['constant'])
    provenance=dict(utc=utc(),source_run=str(RUN.resolve()),source_files=data['evidence'].consumed,
        files_verified=len(data['evidence'].consumed),forecast_seal_utc=data['seal_utc'],first_future_utc=data['first_future_utc'],
        all_forecasts_precede_every_future=True,all_acquisition_rows_and_selection_rebuilt=True,
        all_frozen_probabilities_scalar_checked=3190,maximum_probability_error=data['maximum_probability_error'],
        every_future_unit_label_matches_aggregate=True,original_dynamics_audit='Reused completed SCIENTIFIC_V1_EVIDENCE_AUDIT.json; no new state replay.',
        original_dynamics_audit_output_files=data['completed_original_dynamics_audit']['output_files_verified'],
        consumed_original_files_only_reverified=True,code_sha256=sha(Path(__file__)),analysis_plan_sha256=sha(HERE/'ANALYSIS_PLAN.txt'))
    write_json(output/'PROVENANCE.json',provenance)
    return result


def main(output):
    assert not output.exists();start=time.monotonic();data=recover();result=summarize(data,output)
    write_json(output/'COMPUTE.json',dict(seconds=time.monotonic()-start,threads=1,new_native_reads=0,new_native_writes=0,new_fits=0))
    print(json.dumps({k:result[k] for k in ['status','original_verdict_unchanged','selected_blocks','selected_records','future_outcomes']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'results_v1')
    args=parser.parse_args();main(args.output)
