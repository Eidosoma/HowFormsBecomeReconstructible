"""All observed first-later-failure boundaries; exact paired single-step interventions."""
import hashlib
import time
import numpy as np
import audit_reader
import audit_optimizer
import lineage_dynamics as dynamics
from repair import recipient_repair
from read_case import replay
from common import ROOT,read,write,arrays,save_arrays,equal,sha,stamp


def select_events(cfg):
    contexts={};events=[]
    for b in cfg['blocks']:
        data=arrays(ROOT/'sources'/f'continuation_{b:06d}.npz')
        good=data['both_pass']
        for v,name in enumerate(('warning','periodic','random','repeated')):
            for case in range(16):
                bad=np.flatnonzero(~good[:,v,case])
                if not good[0,v,case] or not len(bad):continue
                gi=int(bad[0]);g=gi+15;incoming=data['incoming'][gi,v,case]
                digest=hashlib.sha256(incoming.tobytes()).hexdigest();key=(b,case,g,digest)
                event=dict(block=b,case=case,generation=g,policy=name,source_variant=v,
                    source_repair_applied=bool(data['applied'][gi,v,case]),incoming_sha256=digest)
                if key not in contexts:
                    contexts[key]=dict(incoming=incoming.copy(),mask=data['masks'][gi].copy(),
                        prepared=data['prepared'][gi,v,case].copy(),birth=data['birth'][gi,case].copy(),
                        end=data['end'][gi,v,case].copy(),mean_ports=data['mean_ports'][gi,v,case].copy(),
                        port_windows=data['port_windows'][gi,:,v,case].copy(),events=[])
                else:
                    for field in ('prepared','end','mean_ports'):
                        equal(contexts[key][field],data[field][gi,v,case],'deduplicated factual '+field)
                contexts[key]['events'].append(event);events.append(event)
    assert len(events)==10 and len(contexts)==7,'Changed exposed failure census'
    return contexts,events


def main(folder,cfg):
    folder.mkdir(exist_ok=False);begin=time.process_time()
    contexts,events=select_events(cfg)
    write(folder/'SELECTION.json',dict(at_utc=stamp(),selection='Every first failure after common first success; all source policies; deduplicate by block/case/generation/incoming bytes.',
        events=events,unique_contexts=len(contexts),source_complete_sha256=cfg['prior_complete_sha256']))
    rows=[];checks=0
    for i,((b,case,g,digest),source) in enumerate(contexts.items()):
        w=dynamics.decode(source['incoming'])
        repaired,solution,magnitude=recipient_repair(w,cfg['optimizer'])
        other=audit_optimizer.solve(audit_optimizer.independent_coupling(w),np.flatnonzero(dynamics.PORTS[0].ravel()),cfg['optimizer'])
        for key in ('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes'):
            if isinstance(solution[key],np.ndarray):equal(solution[key],other[key],'optimizer '+key)
            else:assert solution[key]==other[key],key
        checks+=1
        packets=np.stack((source['incoming'],dynamics.encode(repaired)))
        factual=int(source['events'][0]['source_repair_applied'])
        equal(packets[factual],source['prepared'],'factual prepared packet')
        identity=cfg['continuation_namespace']+':'+str(b);mask=source['mask'][case]
        raw=replay(packets,mask,case,identity,g,cfg)
        flat=audit_reader.replay(packets,mask,case//4,case%4,identity,0,cfg,original=True,generation=g,rhos=[0.,0.])
        equal(raw['birth'],flat['birth'],'paired reset')
        equal(raw['birth'],source['birth'],'factual reset')
        for key in ('end','mean_ports','port_windows'):
            equal(raw[key],flat[key][0],'independent paired '+key)
            equal(raw[key][:,factual] if key=='port_windows' else raw[key][factual],source[key],'factual replay '+key)
        rule=1. if (case//4)%2==0 else -1.
        aligned=raw['mean_ports']*rule*np.array([[1.,-1.],[-1.,1.]])
        margins=aligned.min(axis=(1,2));good=margins>.25;assert not good[factual]
        outcome=('rescue_by_current_repair' if good[1] and not good[0] else
                 'harm_by_current_repair' if good[0] and not good[1] else
                 'both_pass' if good.all() else 'both_fail')
        fields=dict(incoming=source['incoming'],packets=packets,mask=mask,**raw,
            min_margin=margins,both_pass=good,optimizer_signs=solution['signs'],magnitude=np.array(magnitude))
        path=folder/f'context_{i:02d}.npz';file_hash=save_arrays(path,fields)
        rows.append(dict(context=i,block=b,case=case,generation=g,events=source['events'],
            no_repair_margin=float(margins[0]),repair_margin=float(margins[1]),outcome=outcome,sha256=file_hash))
    result=dict(status='COMPLETE',at_utc=stamp(),cpu_seconds=time.process_time()-begin,
        contexts=rows,source_policy_events=len(events),unique_contexts=len(rows),paired_read_contexts=2*len(rows),
        independent_optimizer_checks=checks,independent_replay_contexts=2*len(rows),all_factual_bytes_match=True,
        counts={name:sum(r['outcome']==name for r in rows) for name in ('rescue_by_current_repair','harm_by_current_repair','both_fail','both_pass')},
        interpretation='Post-hoc selected failing states under their realized current injury/noise. Tests only this repair at this boundary. Both-fail does not rule out earlier repair, other interventions, or success under another disturbance. Not a population repair-effect estimate or a schedule-level causal effect.',
        source_complete_sha256=cfg['prior_complete_sha256'],files_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()})
    write(folder/'COMPLETE.json',result)
    return result
