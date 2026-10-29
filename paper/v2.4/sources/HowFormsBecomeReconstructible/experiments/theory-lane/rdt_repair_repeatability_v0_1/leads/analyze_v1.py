"""Post-hoc full-trajectory diagnosis; no new futures, fitting or verdict changes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time
import numpy as np

STUDY = Path(__file__).resolve().parents[1]
RUN = STUDY/'runs/pilot_v1'
FROZEN = STUDY/'jobs/pilot_v1/inputs'
sys.path.insert(0,str(FROZEN))
from rr_common import ev, read, ledger, require, inherited


def interval(values):
    mean=statistics.mean(values)
    sd=statistics.stdev(values)
    radius=2.131449545559323*sd/math.sqrt(len(values))
    return dict(mean=mean,lower=mean-radius,upper=mean+radius,block_values=values,
                status='POST_HOC_DESCRIPTIVE_NOT_SIMULTANEOUS')


def near(a,b):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-12,'Independent arithmetic difference')


def main():
    output=STUDY/'leads/v1'
    output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    admission=inherited.admission()
    ev.write(output/'CPU_ADMISSION.json',admission)
    require(admission['within_limit'],'One shared CPU slot required')
    complete=read(RUN/'COMPLETE.json')
    source_manifest=read(RUN/'OUTPUTS.json')['sha256']
    require(ev.sha(RUN/'OUTPUTS.json')==complete['output_manifest_sha256'],'Output binding changed')
    require(read(RUN/'VERIFICATION.json')['status']=='PASS','Completed audited source required')
    source_sha={}
    def checked(path):
        relative=str(path.relative_to(RUN))
        require(ev.sha(path)==source_manifest[relative],'Changed source '+relative)
        source_sha[relative]=source_manifest[relative]
        return read(path)
    original=checked(RUN/'ANALYSIS.json')
    seal=checked(RUN/'study/PANEL_SEAL.json')
    rows,forecasts=seal['rows'],seal['forecasts']
    blocks=sorted({r['block'] for r in rows})
    count=Counter((r['block'],r['current_pass']) for r in rows)
    weights=np.array([1/(2*len(blocks)*count[r['block'],r['current_pass']]) for r in rows])
    # generation, repeat, packet, arm; classes are correct, opposite, other.
    values={g:dict(correct=np.zeros((19,4,63,2),bool),opposite=np.zeros((19,4,63,2),bool),margin=np.zeros((19,4,63,2))) for g in ('matched','independent')}
    seen=set(); scalar_cells=0
    for rep in range(4):
        owner=RUN/'study'/f'replicate_{rep}'
        for item in checked(owner/'FUTURE_REFERENCES.json'):
            target,committed=ledger.referenced(owner,item['reference'],item['identity'])
            indices=item['indices']; regime=item['identity']['regime']
            receipt=checked(target/'future.json')
            raw_path=target/'future.npz'
            require(ev.sha(raw_path)==source_manifest[str(raw_path.relative_to(RUN))],'Raw manifest changed')
            source_sha[str(raw_path.relative_to(RUN))]=source_manifest[str(raw_path.relative_to(RUN))]
            raw=ev.load(raw_path,receipt['raw_sha256'])
            require(raw['generations'].tolist()==list(range(15,34)),'Horizon changed')
            local_rows=[rows[i] for i in indices]
            require(receipt['keys']==[r['key'] for r in local_rows],'Case identity changed')
            aligned=raw['windows'].mean(axis=2)*np.array([r['rule'] for r in local_rows])[None,:,None,None,None]*np.array([[1.,-1.],[-1.,1.]])
            correct=np.all(aligned>.25,axis=(-2,-1));opposite=np.all(aligned<-.25,axis=(-2,-1));margin=aligned.min(axis=(-2,-1))
            for gi in range(19):
                for li,row in enumerate(local_rows):
                    for arm in range(2):
                        signed=[]
                        for cue in range(2):
                            for port in range(2):
                                m=math.fsum(raw['windows'][gi,li,:,arm,cue,port])/32*row['rule']*(1 if cue==port else -1)
                                near(m,aligned[gi,li,arm,cue,port]);signed.append(m);scalar_cells+=1
                        require(bool(correct[gi,li,arm])==all(x>.25 for x in signed),'Correct-task reduction differs')
                        require(bool(opposite[gi,li,arm])==all(x<-.25 for x in signed),'Opposite-task reduction differs')
                        near(margin[gi,li,arm],min(signed))
            for li,i in enumerate(indices):
                identity=(regime,rep,i);require(identity not in seen,'Duplicated case');seen.add(identity)
                for name,array in [('correct',correct),('opposite',opposite),('margin',margin)]: values[regime][name][:,rep,i,:]=array[:,li,:]
    require(len(seen)==504,'Full repeated panel required')
    result=dict(status='POST_HOC_EXPLORATORY',primary_verdict_unchanged=complete['decision'],regimes={},
        scope='All 19 native read generations and both regimes; no selected peak or subgroup replaces terminal outcomes. Opposite-task success is all four intended-task aligned means below -0.25, equivalent to the other supplied rule; all remaining outcomes are other. Temporal comparisons and additional task categories were specified after terminal outcomes were exposed.',
        no_new_native_reads=True,no_fitting=True,new_scientific_run=False)
    for regime,arrays in values.items():
        d=arrays['correct'][...,1].astype(int)-arrays['correct'][...,0].astype(int)
        profile=[]
        for gi,generation in enumerate(range(15,34)):
            point=dict(generation=generation,purpose='writer' if generation<33 else 'terminal',
                control_success=float(weights@arrays['correct'][gi,:,:,0].mean(axis=0)),
                repair_success=float(weights@arrays['correct'][gi,:,:,1].mean(axis=0)),
                rescue_count=int(np.sum(d[gi]==1)),harm_count=int(np.sum(d[gi]==-1)))
            for name,packet_values in [('benefit',d[gi].mean(axis=0)),('margin_change',(arrays['margin'][gi,:,:,1]-arrays['margin'][gi,:,:,0]).mean(axis=0)),('opposite_task_change',(arrays['opposite'][gi,:,:,1].astype(int)-arrays['opposite'][gi,:,:,0].astype(int)).mean(axis=0))]:
                block_values=[]
                for block in blocks:
                    class_values=[statistics.mean(float(packet_values[i]) for i,row in enumerate(rows) if row['block']==block and row['current_pass']==current) for current in (0,1)]
                    block_values.append(statistics.mean(class_values))
                point[name]=interval(block_values)
                near(float(weights@packet_values),point[name]['mean'])
            profile.append(point)
        for field in ('control_success','repair_success'):
            near(profile[-1][field],original['regimes'][regime][field])
        near(profile[-1]['benefit']['mean'],original['regimes'][regime]['mean_benefit'])
        predictions={tuple(f['key']):f['probabilities'] for f in forecasts if f['regime']==regime}
        scores={}
        for model in ('tt008','direct_rival','candidate'):
            p=np.array([predictions[tuple(row['key'])][model] for row in rows])
            losses=(arrays['correct'][-1,:,:,0]-p[None,:])**2
            scores[model]=[float(weights@losses[rep]) for rep in range(4)]
            near(statistics.mean(scores[model]),original['regimes'][regime]['control_forecasts'][model]['estimate'])
        comparisons={}
        for rival in ('tt008','direct_rival'):
            gains=[a-b for a,b in zip(scores[rival],scores['candidate'],strict=True)]
            saved=original['regimes'][regime]['control_forecast_gains'][rival+'_minus_successor']
            bv=saved['block_values']
            comparisons[rival]=dict(gain=saved,replicate_gains=gains,positive_replicates=sum(v>0 for v in gains),positive_blocks=sum(v>0 for v in bv),
                leave_one_block_mean_range=[min((sum(bv)-v)/15 for v in bv),max((sum(bv)-v)/15 for v in bv)],required_original_margin=.002 if rival=='tt008' else 0.,
                original_margin_supported_in_descriptive_secondary_interval=saved['lower']>(.002 if rival=='tt008' else 0.))
        terminal_d=d[-1]
        repeated=dict(any_rescue_packets=int(np.any(terminal_d==1,axis=0).sum()),any_harm_packets=int(np.any(terminal_d==-1,axis=0).sum()),both_rescue_and_harm_packets=int((np.any(terminal_d==1,axis=0)&np.any(terminal_d==-1,axis=0)).sum()),all_four_zero_packets=int(np.all(terminal_d==0,axis=0).sum()))
        transitions=Counter()
        for rep in range(4):
            for i in range(63):
                labels=[]
                for arm in range(2):
                    labels.append('correct' if arrays['correct'][-1,rep,i,arm] else 'opposite' if arrays['opposite'][-1,rep,i,arm] else 'other')
                transitions[' to '.join(labels)]+=1
        # Every one of the nine categories is shown, including zeros.
        terminal_transitions={a+' to '+b:transitions[a+' to '+b] for a in ('correct','opposite','other') for b in ('correct','opposite','other')}
        result['regimes'][regime]=dict(profile=profile,forecast_scores_by_replicate=scores,forecast_comparisons=comparisons,terminal_packet_repeat_patterns=repeated,terminal_task_transitions=terminal_transitions)
    result['verification']=dict(status='PASS',scalar_port_means=scalar_cells,all_terminal_primary_summaries_reproduced=True,all_six_fixed_forecast_scores_reproduced=True)
    result['source_sha256']=source_sha
    result['costs']=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,new_native_reads=0,new_model_fits=0)
    result['script_sha256']=ev.sha(Path(__file__))
    ev.write(output/'LEADS.json',result)
    print(json.dumps(dict(regimes={g:dict(early=v['profile'][0],terminal=v['profile'][-1],forecast_comparisons=v['forecast_comparisons'],terminal_task_transitions=v['terminal_task_transitions'],terminal_packet_repeat_patterns=v['terminal_packet_repeat_patterns']) for g,v in result['regimes'].items()},verification=result['verification'],costs=result['costs']),indent=2))


if __name__=='__main__': main()
