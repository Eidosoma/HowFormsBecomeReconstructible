#!/usr/bin/env python3
"""Full-cost evaluation of the frozen optional-reference decisions."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import islice, zip_longest
import json
from math import prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-active-verification-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-verification-value-v1/attempt-01'
PREVIOUS_SHA = '26cda981012aaf060e7f1c24165fb17489af24d658c95f711e7f4db776f7ff80'
REPORT_SHA = '2ae43013e790a82617a4a6629030da5f36b645b8415c9a4f92f0732a3f7afa2b'
HELPER_SHA = '18632e11c805fb09f358319ded95d5dd937dd00cc1895e993b5116e8569f933b'
ARMS = ('passive','immediate','future')
EVENTS = ('learning_only','myopic_rejected')
BASE,CAP,T = 400,64,99


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_verification_value.py').read_bytes()).hexdigest() == HELPER_SHA
V = module('frozen_verification',SOURCE/'check_fep_verification_value.py')
R = V.R
check,write,identity = V.check,V.write,V.identity
DECISIONS = PREVIOUS/'VERIFICATION_DECISIONS.jsonl.gz'
BAD = tuple(tuple(sum(int(d[e if w == 0 else 3-e] != w and d[e if w == 0 else 3-e] != 2)
                     for w in (0,1)) for e in range(4)) for d in R.C.ACTS)
ASK = tuple(tuple(sum(int(d[e if w == 0 else 3-e] == 2)
                     for w in (0,1)) for e in range(4)) for d in R.C.ACTS)


def shape(z,s,decisions):
    initial = z['initial'][s]
    warnings = tuple(x[s] for x in z['warnings'])
    labels = tuple(x[s] for x in z['labels'])
    asks = tuple(tuple(int(decisions[g][0] == 2) if a == 0 else decisions[g][a]
                       for g in (0,1)) for a in range(3))
    return initial,warnings,labels,asks


def features(program,first,joint):
    initial,warnings,labels,asks = program
    values = [[0]*4 for _ in ARMS]
    events = [0,0]
    attribution = [[0]*4 for _ in EVENTS]
    for e in range(4):
        g = min(e,3-e)
        current = R.C.ACTS[initial][e]  # W=0; complement symmetry is checked upstream.
        cache,contributions = {},[]
        for a in range(3):
            bought = bool(asks[a][g])
            code = labels[e] if bought else warnings[g]
            if code not in cache:
                cache[code] = (sum(joint[e][f]*BAD[code][f] for f in range(4)),
                               sum(joint[e][f]*ASK[code][f] for f in range(4)))
            row = (first[e]*int(not bought and current == 1),first[e]*int(bought),*cache[code])
            contributions.append(row)
            for j,x in enumerate(row):
                values[a][j] += x
        conditions = (asks[2][g] and not asks[1][g],asks[1][g] and not asks[2][g])
        for t,yes in enumerate(conditions):
            if yes:
                check('selection','only previously unchecked reports differ',current != 2)
                events[t] += first[e]
                for j in range(4):
                    attribution[t][j] += contributions[2][j]-contributions[1][j]
    check('attribution','disjoint event accounting',all(
        sum(row[j] for row in attribution) == values[2][j]-values[1][j] for j in range(4)))
    return values,events,attribution


def fresh():
    return dict(mass=0,count=0,values=[[0]*4 for _ in ARMS],events=[0,0],attribution=[[0]*4 for _ in EVENTS])


def accumulate(stat,feat,weight,mass,n):
    stat['mass'] += mass
    stat['count'] += n*mass
    values,events,attribution = feat
    for a in range(3):
        for j in range(4):
            stat['values'][a][j] += weight*values[a][j]
    for t in range(2):
        stat['events'][t] += weight*events[t]
        for j in range(4):
            stat['attribution'][t][j] += weight*attribution[t][j]


def decomposition(v):
    wrong,reference,fwrong,fref = v
    out = dict(first_wrong_loss=wrong/100,first_reference_expense=reference/1000,
               later_task_loss=T*(fwrong+fref/10)/100)
    out['net_difference'] = sum(out.values())
    return out


def summarize(stat,mass_den,first_den,future_den):
    check('mass','stopped law normalized',stat['mass'] == mass_den)
    n = F(stat['count'],mass_den)
    normalized = [[F(row[j],first_den if j < 2 else future_den) for j in range(4)] for row in stat['values']]
    arms = {}
    for a,name in enumerate(ARMS):
        wrong,reference,fw,fr = normalized[a]
        check('probability','valid reference and error accounting',0 <= wrong+reference <= 1 and 0 <= fw+fr <= 1)
        raw1,rawf = wrong+reference/10,fw+fr/10
        arms[name] = dict(first_wrong_probability=wrong,first_reference_probability=reference,
            future_wrong_probability=fw,future_reference_probability=fr,
            first_raw_risk=raw1,future_raw_risk=rawf,
            episode_expected_references=reference+T*fr,episode_expected_wrong_reports=wrong+T*fw,
            additional_first_reference_probability=reference-normalized[0][1],
            net_loss=(raw1+T*rawf)/100+n/100000)
        check('selection','no removal of original purchases',arms[name]['additional_first_reference_probability'] >= 0)
    contrasts = {f'future_minus_{other}':arms['future']['net_loss']-arms[other]['net_loss'] for other in ('passive','immediate')}
    contrasts['immediate_minus_passive'] = arms['immediate']['net_loss']-arms['passive']['net_loss']
    decompositions = {}
    for a,name in enumerate(ARMS[:2]):
        d = decomposition([normalized[2][j]-normalized[a][j] for j in range(4)])
        check('attribution','total cost decomposition',d['net_difference'] == contrasts['future_minus_'+name])
        decompositions['future_minus_'+name] = d
    attribution = {name:decomposition([F(row[j],first_den if j < 2 else future_den) for j in range(4)])
                   for name,row in zip(EVENTS,stat['attribution'])}
    check('attribution','event cost decomposition',sum(row['net_difference'] for row in attribution.values()) == contrasts['future_minus_immediate'])
    return dict(expected_calibrations=n,calibration_cost_per_task=n/100000,arms=arms,contrasts=contrasts,
        decompositions=decompositions,event_attribution=attribution,
        events={name:F(x,first_den) for name,x in zip(EVENTS,stat['events'])})


class Collector:
    def __init__(self,cap=CAP):
        self.cap = cap
        self.prior = [fresh(),fresh()]
        self.actual = {label:[fresh(),fresh()] for label in R.TRUTHS}
        self.powers = {label:[[x**n for n in range(cap+1)] for x in q] for label,q in R.TRUTHS.items()}
        self.tails = [BASE**n for n in range(cap+1)]
        self.caches = {label:{} for label in R.TRUTHS}
        self.joints = {label:tuple(tuple(x*y for y in q) for x in q) for label,q in R.TRUTHS.items()}
        self.rows,self.stopped = 0,0

    def collect(self,z,k,decisions):
        n,c = sum(z['c']),z['c']
        for s in (0,1):
            if not k[s]:
                check('saved decisions','unreachable arm absent',decisions[s] is None)
                continue
            program = shape(z,s,decisions[s])
            feat = features(program,z['mix'],z['joint'])
            costs = [2*(10*x[0]+x[1])+T*(10*x[2]+x[3]) for x in feat[0]]
            check('prior control','future-aware conditional dominance',costs[2] <= min(costs[:2]))
            accumulate(self.prior[s],feat,k[s],k[s]*sum(z['mix']),n)
            for label,q in R.TRUTHS.items():
                p = self.powers[label]
                mass = k[s]*prod(p[e][c[e]] for e in range(4))*self.tails[self.cap-n]
                if not mass:
                    continue
                cache = self.caches[label]
                if program not in cache:
                    cache[program] = features(program,q,self.joints[label])
                accumulate(self.actual[label][s],cache[program],mass,mass,n)
            self.stopped += 1
        self.rows += 1

    def finish(self):
        prior = {name:summarize(self.prior[s],V.DEN,V.DEN,2*V.DEN) for s,name in enumerate(V.NAMES)}
        d = BASE**self.cap
        actual = {label:{name:summarize(rows[s],d,BASE*d,2*BASE**2*d) for s,name in enumerate(V.NAMES)}
                  for label,rows in self.actual.items()}
        return prior,actual


def read_rows():
    with gzip.open(V.LEDGER,'rt') as post, gzip.open(DECISIONS,'rt') as choices:
        for line,other in zip_longest(post,choices):
            check('saved decisions','ledgers same length',line is not None and other is not None)
            row,decision = json.loads(line),json.loads(other)
            check('saved decisions','ledgers aligned',row[:5] == decision[:5])
            z,k = V.visit(row)
            for s in (0,1):
                if not k[s]:
                    check('saved decisions','unused arm not scored',decision[5][s] is None)
                    continue
                rebuilt = []
                for g in (0,1):
                    b = V.branch(z,s,g)
                    rebuilt.append([b['b'],int(b['now']),int(b['future']),int(b['delta'] > 0)-int(b['delta'] < 0)])
                check('saved decisions','frozen acquisition rule reproduced',rebuilt == decision[5][s])
            yield z,k,decision[5]


def direct(program,first,joint):
    initial,warnings,labels,asks = program
    result = [[0]*4 for _ in ARMS]
    for w in (0,1):
        for e in range(4):
            y = e if w == 0 else 3-e
            g = min(y,3-y)
            for a in range(3):
                bought = asks[a][g]
                result[a][0] += first[e]*int(not bought and R.C.ACTS[initial][y] != w)
                result[a][1] += first[e]*int(bought)
                code = labels[e] if bought else warnings[g]
                for v in (0,1):
                    for f in range(4):
                        act = R.C.ACTS[code][f if v == 0 else 3-f]
                        result[a][2] += joint[e][f]*int(act != 2 and act != v)
                        result[a][3] += joint[e][f]*int(act == 2)
    return result


def qualify():
    start = perf_counter()
    ref = module('independent_factor_reference',SOURCE/'check_fep_factor_revision.py')
    for code in range(81):
        check('qualification','separate physical error/reference units',
              tuple(10*x+y for x,y in zip(BAD[code],ASK[code])) == R.C.UNITS[code])
    states = 0
    for n in range(5):
        for c in ref.histograms(n):
            z = V.kernel(c)
            first = []
            joint = []
            for e in range(4):
                ev = ref.evidence(R.add(c,e))
                first.append((9*ev[0]+ev[1])*V.SCALE)
                row = []
                for f in range(4):
                    ev = ref.evidence(R.add(R.add(c,e),f))
                    row.append((9*ev[0]+ev[1])*V.SCALE)
                joint.append(row)
            check('qualification','independent likelihood moments',first == list(z['mix']) and joint == [list(row) for row in z['joint']])
            for s in (0,1):
                ds = []
                for g in (0,1):
                    b = V.branch(z,s,g)
                    ds.append([b['b'],int(b['now']),int(b['future']),int(b['delta'] > 0)-int(b['delta'] < 0)])
                program = shape(z,s,ds)
                laws = [(first,joint)] + [(q,tuple(tuple(x*y for y in q) for x in q)) for q in R.TRUTHS.values()]
                for p,j in laws:
                    f = features(program,p,j)
                    d = direct(program,p,j)
                    check('qualification','full target/error enumeration',d == [[2*x for x in row] for row in f[0]])
                f = features(program,first,joint)
                costs = [2*(10*x[0]+x[1])+T*(10*x[2]+x[3]) for x in f[0]]
                check('qualification','conditional prior choice control',costs[2] <= min(costs[:2]))
                neutral = (*program[:3],(program[3][0],)*3)
                noextra = features(neutral,first,joint)
                check('qualification','no added purchase makes arms equal',noextra[0][0] == noextra[0][1] == noextra[0][2] and noextra[1] == [0,0])
            states += 1
    # Independently enumerate ordered leaves of a small outcome-dependent stopping tree.
    leaves = Counter()
    def paths(s,sequence):
        n = len(sequence)
        if n == 0 or (n < 3 and ((s == 0 and n == 1 and sequence[0] != 0) or
             (s == 0 and n == 2 and 3 in sequence) or (s == 1 and n == 1 and sequence[0] != 3))):
            for e in range(4):
                paths(s,sequence+(e,))
        else:
            leaves[s,tuple(sequence.count(e) for e in range(4))] += 1
    for s in (0,1):
        paths(s,())
    saved = R.toy_stops(ref,3)
    for n in range(4):
        for c in R.counts(n):
            for s in (0,1):
                check('qualification','ordered stopping multiplicities',saved[s][n][R.ix(n,*c[:3])] == leaves[s,c])
    for q in R.TRUTHS.values():
        for s in (0,1):
            mass = sum(F(k*prod(q[e]**c[e] for e in range(4)),BASE**sum(c)) for (t,c),k in leaves.items() if s == t)
            check('qualification','ordered stopping probabilities',mass == 1)
    elapsed = perf_counter()-start
    begin = perf_counter()
    collector = Collector()
    for z,k,ds in islice(read_rows(),512):
        collector.collect(z,k,ds)
    bench = perf_counter()-begin
    forecast = 90+4*bench*136499/512
    return dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),qualification_seconds=elapsed,
        small_count_states=states,physical_laws=len(R.TRUTHS),benchmark_rows=512,benchmark_seconds=bench,
        forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90 seconds I/O plus four times full-workload 512-row measured rate')


def bridge(row,old):
    passive = row['arms']['passive']
    for key in ('expected_calibrations','calibration_cost_per_task'):
        check('bridge','unchanged '+key,row[key] == F(old[key]['exact']))
    for key in ('first_reference_probability','first_wrong_probability'):
        check('bridge','same passive '+key,passive[key] == F(old[key]['exact']))
    for key in ('net_loss','future_raw_risk'):
        check('bridge','same passive '+key,passive[key] == F(old['arms']['full'][key]['exact']))
    row['no_update_net_loss'] = F(old['arms']['none']['net_loss']['exact'])
    row['contrasts']['future_minus_no_update'] = row['arms']['future']['net_loss']-row['no_update_net_loss']
    row['always_reference_net_loss'] = F(1,10)


def average(rows):
    if isinstance(rows[0],dict):
        return {key:average([row[key] for row in rows]) for key in rows[0]}
    return sum(rows)/len(rows)


def prepare(output,logline):
    check('integrity','previous manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',identity(SOURCE/'FEP_VERIFICATION_VALUE_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    V.verify(preserved)
    (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_ACTIVE_VERIFICATION_V1.md','check_fep_active_verification.py',
        'FEP_VERIFICATION_VALUE_V1.md','FEP_VERIFICATION_VALUE_V1_REPORT.md','check_fep_verification_value.py',
        'check_fep_reference_feedback.py','check_fep_stopping_attribution.py','check_fep_factor_revision.py')]
    files += [(PREVIOUS/'MANIFEST.json','value_MANIFEST.json'),(PREVIOUS/'CENSUS.json','value_CENSUS.json'),
              (V.PREVIOUS/'RESULTS.json','feedback_RESULTS.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p))
        shutil.copyfile(p,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(V.LEDGER),identity(DECISIONS)]
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,arms=ARMS,controllers=V.NAMES,
        T=T,reference_price=F(1,10),calibration_price=F(1,1000),truths=R.TRUTHS,truth_denominator=BASE,
        known_panel=True,equal_panel_weights=True,old_shared_excluded=True,large_inputs_read_in_place=True,
        primary_criteria=['future mean < passive mean','future mean < immediate mean','future mean < no-update mean'],
        policy_optimization=0,prior_or_price_tuning=0))
    q = qualify()
    write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; main forecast {q["forecast_main_seconds"]:.1f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text())
    qual = json.loads((output/'QUALIFICATION.json').read_text())
    for key,n in qual['groups'].items():
        R.C.COUNTS[key] += n
    V.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    collector = Collector()
    for z,k,ds in read_rows():
        collector.collect(z,k,ds)
        if collector.rows % 40000 == 0:
            logline(f'Integrated {collector.rows} frozen count rows')
    check('scope','complete saved stopping law',collector.rows == 136499 and collector.stopped == 259142)
    prior,actual = collector.finish()
    old = json.loads((V.PREVIOUS/'RESULTS.json').read_text())
    census = json.loads((PREVIOUS/'CENSUS.json').read_text())
    for name in V.NAMES:
        bridge(prior[name],old['prior'][name])
        for label,rows in actual.items():
            bridge(rows[name],old['truths'][label][name])
        for arm in ('immediate','future'):
            check('bridge','same prior extra purchases',prior[name]['arms'][arm]['additional_first_reference_probability'] == F(census[name][arm+'_purchase']['own_prior_probability']['exact']))
        for event in EVENTS:
            check('bridge','same prior selection event',prior[name]['events'][event] == F(census[name][event]['own_prior_probability']['exact']))
        check('prior control','integrated conditional dominance',all(prior[name]['contrasts']['future_minus_'+a] <= 0 for a in ('passive','immediate')))
        check('prior control','both switch categories improve expected cost',all(x['net_difference'] <= 0 for x in prior[name]['event_attribution'].values()))
    check('prior control','averaged passive no worse than no updating',prior['average']['arms']['passive']['net_loss'] <= prior['average']['no_update_net_loss'])
    aggregate = {}
    for name in V.NAMES:
        rows = [actual[label][name] for label in R.PANEL]
        avg = average(rows)
        avg['gates'] = {f'improves_{a}':avg['contrasts']['future_minus_'+a] < 0 for a in ('passive','immediate','no_update')}
        avg['improved_counts'] = {a:sum(row['contrasts']['future_minus_'+a] < 0 for row in rows) for a in ('passive','immediate','no_update')}
        avg['no_worse_counts'] = {a:sum(row['contrasts']['future_minus_'+a] <= 0 for row in rows) for a in ('passive','immediate','no_update')}
        avg['uniform_no_worse'] = {a:count == 9 for a,count in avg['no_worse_counts'].items()}
        avg['below_always_reference_counts'] = {a:sum(row['arms'][a]['net_loss'] < F(1,10) for row in rows) for a in ARMS}
        avg['below_always_reference_counts']['no_update'] = sum(row['no_update_net_loss'] < F(1,10) for row in rows)
        aggregate[name] = avg
    write(output/'PRIOR_CONTROL.json',prior)
    for label,rows in actual.items():
        write(output/(label+'.json'),dict(Q=[F(x,BASE) for x in R.TRUTHS[label]],methods=rows))
    V.verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),count_rows=collector.rows,
        stopped_controller_rows=collector.stopped,panel_environments=9,excluded_shared_diagnostics=1,
        sampled_trajectories=0,policy_optimizations=0,prices_or_priors_tuned=0,
        primary_gates=aggregate['edit']['gates'])
    write(output/'RESULTS.json',dict(summary=summary,prior=prior,truths=actual,equal_panel_aggregate=aggregate))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; primary gates {summary["primary_gates"]}')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,python=platform.python_version(),processes=1,
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified, unfailed record required')
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; frozen rule')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
