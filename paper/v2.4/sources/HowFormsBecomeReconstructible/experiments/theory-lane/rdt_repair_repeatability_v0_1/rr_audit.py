"""Independent scalar reductions and independent random-stream commitments."""
from collections import Counter
import hashlib
import itertools
import json
import math
import statistics
import numpy as np
from scipy.stats import t
from rr_common import C, REGIMES, MODELS, inherited, require, read


def near(a, b):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-12, 'Independent scalar disagreement')


def scalar_statistics(d, weights):
    n, repeats = len(d), len(d[0])
    means = [math.fsum(weights[i]*d[i][r] for i in range(n)) for r in range(repeats)]
    terms = [math.fsum(weights[i]*(d[i][r]-means[r])*(d[i][s]-means[s]) for i in range(n))
             for r in range(repeats) for s in range(repeats) if r != s]
    noise = math.fsum(weights[i] * math.fsum((d[i][r]-d[i][s])**2 for r,s in itertools.combinations(range(repeats),2))
                      / (repeats*(repeats-1)) for i in range(n))
    return dict(variance=statistics.mean(terms), future_noise=noise, mean_benefit=statistics.mean(means), replicate_means=means)


def check_interval(saved, value, se, blocks):
    near(saved['estimate'], value); near(saved['standard_error'], se)
    radius = float(t.ppf(.975, blocks-1))*se
    near(saved['lower'], value-radius); near(saved['upper'], value+radius)
    require(saved['zero_variance_caution'] == (se == 0), 'False zero-variance certainty')


def check_blocks(saved, values):
    check_interval(saved, statistics.mean(values), statistics.stdev(values)/math.sqrt(len(values)), len(values))
    for a,b in zip(saved['block_values'], values, strict=True): near(a,b)


def evaluate(rows, forecasts, outcomes, result):
    blocks = sorted({r['block'] for r in rows})
    count = Counter((r['block'],r['current_pass']) for r in rows)
    w = [1/(2*len(blocks)*count[r['block'],r['current_pass']]) for r in rows]
    labels = {(tuple(o['key']), o['regime'], o['replicate']): o for o in outcomes}
    pred = {(tuple(f['key']), f['regime']): f['probabilities'] for f in forecasts}
    reps = C['cohort']['new_replicates']
    require(len(labels) == len(outcomes) == len(rows)*len(REGIMES)*len(reps), 'Scalar coverage')
    signals=[]
    for regime in REGIMES:
        saved=result['regimes'][regime]
        c=[[labels[tuple(row['key']),regime,r]['control'] for r in reps] for row in rows]
        a=[[labels[tuple(row['key']),regime,r]['repaired'] for r in reps] for row in rows]
        d=[[av-cv for av,cv in zip(ar,cr,strict=True)] for ar,cr in zip(a,c,strict=True)]
        stat=scalar_statistics(d,w)
        for k in ('variance','future_noise','mean_benefit'): near(saved[k],stat[k])
        for av,bv in zip(saved['replicate_means'],stat['replicate_means'],strict=True): near(av,bv)
        pairs=[math.fsum(w[i]*d[i][r]*d[i][s] for i in range(len(rows)))-stat['replicate_means'][r]*stat['replicate_means'][s] for r,s in itertools.combinations(range(len(reps)),2)]
        for av,bv in zip(saved['pair_covariances'],pairs,strict=True): near(av,bv)
        leaves=[]; benefits=[]
        for block in blocks:
            indices=[i for i,row in enumerate(rows) if row['block'] != block]
            weight=math.fsum(w[i] for i in indices)
            leaves.append(scalar_statistics([d[i] for i in indices],[w[i]/weight for i in indices])['variance'])
            values=[]
            for current in (0,1):
                values.append(statistics.mean(statistics.mean(d[i]) for i,row in enumerate(rows) if row['block']==block and row['current_pass']==current))
            benefits.append(statistics.mean(values))
        se=math.sqrt((len(blocks)-1)/len(blocks)*math.fsum((v-statistics.mean(leaves))**2 for v in leaves))
        check_interval(saved['primary'],stat['variance'],se,len(blocks))
        for item,block,value in zip(saved['leave_one_block'],blocks,leaves,strict=True):
            require(item['block']==block,'Block deletion identity'); near(item['variance'],value)
        signal='REPEATABILITY_SIGNAL' if se>0 and saved['primary']['lower']>0 else 'UNRESOLVED'
        require(signal==saved['signal'],'Repeatability decision'); signals.append(signal)
        check_blocks(saved['mean_benefit_interval'],benefits)
        for i,packet in enumerate(saved['packets']):
            require(packet['key']==rows[i]['key'] and packet['differences']==d[i],'Per-packet evidence')
            near(packet['weight'],w[i]); near(packet['mean_benefit'],statistics.mean(d[i])); near(packet['sample_variance'],statistics.variance(d[i]))
        categories={(0,0):'neither_pass',(0,1):'rescue',(1,0):'harm',(1,1):'both_pass'}
        events=Counter(); fractions={name:[] for name in categories.values()}
        for i in range(len(rows)):
            for r in range(len(reps)):
                name=categories[c[i][r],a[i][r]]
                events[name]+=1; fractions[name].append(w[i]/len(reps))
        for name in categories.values():
            require(saved['events'][name]['count']==events[name],'Paired event count')
            near(saved['events'][name]['fraction'],math.fsum(fractions[name]))
        near(saved['control_success'],math.fsum(w[i]*statistics.mean(c[i]) for i in range(len(rows))))
        near(saved['repair_success'],math.fsum(w[i]*statistics.mean(a[i]) for i in range(len(rows))))
        near(saved['repair_success']-saved['control_success'],saved['mean_benefit'])
        losses={}
        for model in MODELS:
            losses[model]=[statistics.mean((v-pred[tuple(row['key']),regime][model])**2 for v in c[i]) for i,row in enumerate(rows)]
            bv=[math.fsum(w[i]*losses[model][i] for i,row in enumerate(rows) if row['block']==block)*len(blocks) for block in blocks]
            check_blocks(saved['control_forecasts'][model],bv)
            require(saved['control_forecasts'][model]['extra_native_probes']==C['costs']['extra_frozen_probe_reads_per_record_regime'][model],'Probe cost')
        for rival in ('tt008','direct_rival'):
            bv=[math.fsum(w[i]*(losses[rival][i]-losses['candidate'][i]) for i,row in enumerate(rows) if row['block']==block)*len(blocks) for block in blocks]
            check_blocks(saved['control_forecast_gains'][rival+'_minus_successor'],bv)
    joint='BOTH_REGIMES_REPEATABILITY_SIGNAL' if all(s=='REPEATABILITY_SIGNAL' for s in signals) else 'UNRESOLVED'
    require(result['signal']==joint,'Joint repeatability decision')
    return dict(status='PASS',independent_scalar_analysis=True,regimes=2,blocks=len(blocks),paired_outcomes=len(outcomes),replicates=len(reps),no_model_fits=True)


def forcing(folder, replica, stage, audit_key):
    """Regenerate the audited key's forcing using a separately spelled-out seed construction."""
    receipt=read(folder/'future.json')
    regime=receipt['regime']
    available=np.flatnonzero(~inherited.e.PORTS.any(axis=0).ravel())
    checked=0
    for row in receipt['forcing']:
        if row['key'] != audit_key: continue
        def rng(channel):
            components=[C['future']['namespace'],stage,replica]+list(audit_key)+[row['generation'],row['purpose'],channel]
            raw=json.dumps(components,separators=(',',':')).encode('utf-8')
            value=int.from_bytes(hashlib.sha256(raw).digest()[0:16],byteorder='little')
            return np.random.Generator(np.random.PCG64(value))
        mask=np.zeros((16,16),bool)
        mask.reshape(-1)[rng('injury').choice(available,size=24,replace=False)]=True
        draws=rng('forcing').standard_normal((2049,2,16,16))
        if regime=='matched': draws[:,1,:,:]=draws[:,0,:,:]
        birth=draws[0]*inherited.C['reader']['birth_sd']
        expected={name:hashlib.sha256(array.tobytes()).hexdigest() for name,array in [('mask',mask),('birth',birth),('noise',draws[1:])]}
        require(row['sha256']==expected,'Replicate forcing commitment differs')
        checked+=1
    require(checked==19,'Every audited generation requires forcing verification')
    return dict(status='PASS',replicate=replica,independently_regenerated_forcings=checked)
