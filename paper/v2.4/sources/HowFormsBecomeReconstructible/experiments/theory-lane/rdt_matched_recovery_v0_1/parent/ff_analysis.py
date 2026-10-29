"""Complete-cohort, balanced-class, repeated individual Brier scoring."""
import numpy as np
from scipy.stats import t
from ff_common import ROOT, C, REGIMES, MODELS, read, require


def validate(rows, forecasts, outcomes, spec):
    keys = [tuple(r['key']) for r in rows]
    blocks = sorted({r['block'] for r in rows})
    require(len(keys) == len(set(keys)) and len(blocks) == spec['eligible_blocks'], 'Complete unique cohort required')
    for b in blocks:
        for c in (0,1):
            require(1 <= sum(r['block']==b and r['current_pass']==c for r in rows) <= 2, 'Each block requires both classes with up to2 packets')
    fm = {(tuple(f['key']),f['regime']):f for f in forecasts}
    ym = {(tuple(y['key']),y['regime'],y['replicate']):y for y in outcomes}
    fp = {(k,g) for k in keys for g in REGIMES}
    yp = {(k,g,r) for k in keys for g in REGIMES for r in spec['repeats']}
    require(len(forecasts)==len(fm) and set(fm)==fp, 'Missing, duplicate or extra forecasts')
    require(len(outcomes)==len(ym) and set(ym)==yp, 'Missing, duplicate or extra outcomes; no partial score')
    for row in rows:
        for regime in REGIMES:
            f = fm[(tuple(row['key']),regime)]
            require(all(f.get(k)==v for k,v in row.items()), 'Forecast boundary metadata differs')
            require(set(f['probabilities'])==set(MODELS), 'Five fixed predictors required')
            require(all(np.isfinite(p) and 0<=p<=1 for p in f['probabilities'].values()), 'Invalid probability')
    require(all(y['passed'] in (0,1) for y in outcomes), 'Binary native outcomes required')
    return blocks,fm,ym


def analyze(rows, forecasts, outcomes, spec):
    blocks,fm,ym = validate(rows,forecasts,outcomes,spec)
    result = dict(scope=spec['scope'],blocks=len(blocks),packets=len(rows),future_outcomes=len(outcomes),
                  inference_unit='acquisition block',repeats=spec['repeats'],regimes={},new_model_fits=0)
    decisions=[]
    for regime in REGIMES:
        losses={m:[] for m in MODELS};weights=[];preds={m:[] for m in MODELS};observed=[]
        for row in rows:
            k=tuple(row['key']); p=fm[(k,regime)]['probabilities']
            ys=np.array([ym[(k,regime,r)]['passed'] for r in spec['repeats']])
            n=sum(s['block']==row['block'] and s['current_pass']==row['current_pass'] for s in rows)
            weights.append(1/(len(blocks)*2*n));observed.append(float(ys.mean()))
            for m in MODELS:
                losses[m].append(float(np.mean((p[m]-ys)**2)))
                preds[m].append(p[m])
        w=np.array(weights);require(abs(w.sum()-1)<1e-12, 'Weight normalization')
        losses={m:np.array(v) for m,v in losses.items()}; contrasts={}
        for rival,margin in C['analysis']['margins'].items():
            gain=losses[rival]-losses['successor32']; bv=[]
            for b in blocks:
                i=np.array([r['block']==b for r in rows]);bv.append(float(np.sum(w[i]*gain[i])*len(blocks)))
            v=np.array(bv);mean=float(v.mean());sd=float(v.std(ddof=1))
            radius=float(t.ppf(.975,len(blocks)-1)*sd/np.sqrt(len(blocks)))
            lo,hi=mean-radius,mean+radius
            decision='SUPPORTED' if lo>margin else 'REJECTED' if hi<=margin else 'UNRESOLVED'
            contrasts[rival]=dict(block_ids=blocks,block_gains=bv,mean_gain=mean,sample_sd=sd,
                lower=lo,upper=hi,margin=margin,decision=decision,blocks=len(blocks))
            if rival in C['analysis']['primary_rivals']:decisions.append(decision)
        strata={}
        for field in ('current_pass','history'):
            strata[field]={}
            for value in sorted({r[field] for r in rows}):
                mask=np.array([r[field]==value for r in rows]);mass=float(w[mask].sum())
                strata[field][str(value)]=dict(weight=mass,packets=int(mask.sum()),
                    blocks=len({r['block'] for r in rows if r[field]==value}),
                    loss_mass={m:float(np.dot(w[mask],losses[m][mask])) for m in MODELS},
                    gain_mass={m:float(np.dot(w[mask],(losses[m]-losses['successor32'])[mask])) for m in C['analysis']['margins']})
        calibration={}
        for m in MODELS:
            bins=[];p=np.array(preds[m]);observed_array=np.array(observed)
            for i in range(10):
                mask=np.minimum((p*10).astype(int),9)==i;mass=float(w[mask].sum())
                bins.append(dict(bin=i,weight=mass,packets=int(mask.sum()),
                    predicted=float(np.dot(w[mask],p[mask])/mass) if mass else None,
                    observed=float(np.dot(w[mask],observed_array[mask])/mass) if mass else None,
                    brier=float(np.dot(w[mask],losses[m][mask])/mass) if mass else None))
            calibration[m]=bins
        result['regimes'][regime]=dict(contrasts=contrasts,primary={r:contrasts[r] for r in C['analysis']['primary_rivals']},
            secondary={r:contrasts[r] for r in C['analysis']['secondary_rivals']},brier={m:float(np.dot(w,losses[m])) for m in MODELS},
            observed_success=float(np.dot(w,observed)),strata=strata,calibration=calibration)
    result['decision']=('ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED' if all(x=='SUPPORTED' for x in decisions)
        else 'AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in decisions else 'UNRESOLVED')
    return result


def report(result, costs):
    measured_costs = read(ROOT / 'context/PREDICTOR_COSTS.json')['models']
    lines = [f"Scope: {result['scope']}. Complete {result['blocks']}-block, {result['packets']}-packet cohort.", '',
        f"Equal-read primary decision: **{result['decision']}**.", '',
        'Brier losses average individual future losses with equal block and expression-class weights.', '',
        '| Predictor | Native reads per packet/regime | Standalone CPU seconds, audits excluded | Matched Brier | Independent Brier |',
        '|---|---:|---:|---:|---:|']
    for name in MODELS:
        reads = costs['forecast_native_reads_per_packet_regime'][name]
        cpu = measured_costs[name]['standalone_cpu_seconds_excluding_audit']
        shown = 'Not separately timed' if cpu is None else f'{cpu:.3f}'
        lines.append(f"| {name} | {reads} | {shown} | {result['regimes']['matched']['brier'][name]:.6f} | {result['regimes']['independent']['brier'][name]:.6f} |")
    lines += ['', '| Role | Regime | Rival | Brier gain | Lower | Upper | Margin | Component decision |',
        '|---|---|---|---:|---:|---:|---:|---|']
    for regime, value in result['regimes'].items():
        for rival, a in value['contrasts'].items():
            role = 'Primary' if rival in C['analysis']['primary_rivals'] else 'Descriptive secondary'
            lines.append(f"| {role} | {regime} | {rival} | {a['mean_gain']:.6f} | {a['lower']:.6f} | {a['upper']:.6f} | {a['margin']} | {a['decision']} |")
    lines += ['', 'Positive gain is rival minus successor32 Brier loss. The joint claim requires all four equal-read primary advantages. Secondary component labels do not establish a fresh all-eight claim. Intervals are individual nominal 95% block-t intervals, not simultaneous intervals.', '',
        'The shared measurement uses 128 primary reads plus four flat dynamics audit reads per packet/regime. Successor32/direct64 CPU costs come from the measured eight-worker benchmark; pooled32/direct8 CPU costs come from the earlier four-worker standalone benchmark. Shared boundary acquisition and model-training costs are separate. TT008 requires no additional probe reads.', '',
        f"Total incurred primary native reads: {costs['primary_native_reads']}; flat audit reads: {costs['flat_native_reads']}; worker CPU seconds: {costs['worker_cpu_seconds']:.3f}.", '',
        'The measured eight-worker benchmark and retained slower acquisition/continuation timings are bound in the frozen resource review. Conditional power and runtime forecasts remain estimates. Incomplete cohorts receive no inferential verdict.', '',
        'This tests forecasting under fresh founder and future streams in the original apparatus. It does not uniquely establish RDT, a reader/writer distribution-shift prediction, or a repair-benefit scheduler. Synthetic qualification outcomes have no scientific inferential meaning.', '']
    return '\n'.join(lines)

