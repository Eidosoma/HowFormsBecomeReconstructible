"""Prepare and independently check repairs without reading new native outcomes."""
import csv
import time
import numpy as np
from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,validate,write
from reader import PORTS,decode,stream,available
from optimizer import influence
from repair import recipient_repair,reference_records
import audit_optimizer
import audit_repair


def masks(cfg,block,founders,recipients):
    eligible=np.flatnonzero(~PORTS.any(axis=0).ravel())
    result=np.zeros((len(founders),len(cfg['replicates']),16,16),bool)
    for case,(f,r) in enumerate(zip(founders,recipients)):
        for ri,rep in enumerate(cfg['replicates']):
            random=stream(cfg['random_namespace'],block,'injury',rep,int(f)//2,int(r))
            result[case,ri].flat[random.choice(eligible,cfg['injury_cells'],replace=False)]=True
    return result


def checked_repair(outgoing,options):
    repaired,result,magnitude=recipient_repair(outgoing,options)
    coupling=audit_optimizer.independent_coupling(outgoing)
    assert np.array_equal(coupling,influence(outgoing)*np.sign(outgoing))
    reference=audit_optimizer.solve(coupling,np.flatnonzero(PORTS[0].ravel()),options)
    for key in ('signs','candidate_costs','flips','final_improvable_nodes'):equal(reference[key],result[key],'independent optimizer '+key)
    for key in ('cost','initial_cost','winner','sweeps','selected_improvable_nodes'):assert reference[key]==result[key],key
    return repaired,result,magnitude


def prepare(cfg):
    validate(cfg);begin=time.perf_counter();folder=ROOT/'prepared';folder.mkdir(exist_ok=False);bindings={}
    source=(ROOT/cfg['source_run']).resolve()
    def bind(path,digest):
        assert sha(path)==digest,str(path);bindings[str(path)]=digest
    bind(source/'COMPLETE.json',cfg['source_complete_sha256'])
    parent=read(source/'COMPLETE.json');assert parent['independent_verification_passed']
    bind(source/'manifest.json',parent['outputs_sha256']['manifest.json'])
    manifest=read(source/'manifest.json');previous=source/'inputs/prepared'
    bind(previous/'COMPLETE.json',manifest['files_sha256']['prepared/COMPLETE.json'])
    old_receipt=read(previous/'COMPLETE.json');outputs={};rows=[];all_checks=0
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        name=f'cases_{block:06d}.npz';bind(previous/name,old_receipt['outputs_sha256'][name])
        old=arrays(previous/name);assert len(old['founders'])==n
        out=decode(old['packets'][:,1])
        # Only O enters the entire primary repair, before historical control data.
        solutions=[checked_repair(o,cfg['optimizer']) for o in out];all_checks+=n
        incoming=decode(old['packets'][:,0]);records=[];full_edges=[];outside=[];magnitudes=[]
        for case,(recipient,solution,magnitude) in enumerate(solutions):
            equal(solution['signs'],old['optimizer_signs'][case,2],'unchanged completion optimizer')
            common=old['common_edges'][case];mask=old['original_masks'][case]
            parts=[cfg['random_namespace'],block,'shuffle',int(old['histories'][case]),int(old['founders'][case]),int(old['recipients'][case])]
            row,full,_=reference_records(out[case],incoming[case],common,~available(mask),solution,magnitude,recipient,stream(*parts))
            reference_full,reference_magnitude,extra=audit_repair.check_case(row,out[case],incoming[case],common,mask,solution['signs'],parts)
            equal(full,reference_full,'full support');assert magnitude==reference_magnitude
            records.append(row);full_edges.append(full);outside.append(extra);magnitudes.append(magnitude)
            missing=out[case]==0
            rows.append(dict(block=block,case=case,history=int(old['histories'][case]),founder=int(old['founders'][case]),recipient=int(old['recipients'][case]),
                common_edges=int(common.sum()),full_backup_edges=int(full.sum()),recipient_missing_edges=int(missing.sum()),
                missing_edges_outside_original_injury=extra,imputed_magnitude=magnitude,
                common_added_abs_weight=float(abs(row[2][missing]).sum()),full_added_abs_weight=float(abs(row[4][missing]).sum()),
                imputed_support_added_abs_weight=float(abs(row[5][missing]).sum()),recipient_added_abs_weight=float(abs(row[6][missing]).sum()),
                shuffled_sign_changes=int(np.count_nonzero(row[6][missing]!=row[7][missing])),
                optimizer_cost=solution['cost'],optimizer_sweeps=solution['sweeps'],selected_improvable_nodes=solution['selected_improvable_nodes']))
        values=np.stack(records);packets=np.ascontiguousarray(values,dtype='<f8').view(np.uint8).reshape(n,9,4096)
        equal(packets[:,[0,1,2,8]],old['packets'][:,[0,1,7,8]],'unchanged historical controls')
        data={k:old[k] for k in ('block','histories','founders','recipients','original_masks','original_end','original_mean_ports','original_birth','common_edges')}
        data.update(packets=packets,masks=masks(cfg,block,old['founders'],old['recipients']),
            replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),
            full_edges=np.array(full_edges),outside_injury_missing_edges=np.array(outside),imputed_magnitudes=np.array(magnitudes))
        for key in ('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes'):
            data['optimizer_'+key]=np.array([s[1][key] for s in solutions])
        outputs[name]=save_arrays(folder/name,data)
    with (folder/'resources.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    outputs['resources.csv']=sha(folder/'resources.csv')
    feasibility=dict(problems=64,independent_optimizer_checks=all_checks,independent_record_checks=len(rows)*9,
        common_edges=sum(r['common_edges'] for r in rows),full_backup_edges=sum(r['full_backup_edges'] for r in rows),
        recipient_missing_edges=sum(r['recipient_missing_edges'] for r in rows),
        missing_edges_outside_original_injury=sum(r['missing_edges_outside_original_injury'] for r in rows),
        cases_with_extra_live_edges=sum(r['missing_edges_outside_original_injury']>0 for r in rows),
        cases_with_shuffled_changes=sum(r['shuffled_sign_changes']>0 for r in rows),
        selected_with_improving_single_flip=sum(r['selected_improvable_nodes']>0 for r in rows),
        maximum_sweeps_used=max(r['optimizer_sweeps'] for r in rows),seconds=time.perf_counter()-begin)
    write(folder/'FEASIBILITY.json',feasibility);outputs['FEASIBILITY.json']=sha(folder/'FEASIBILITY.json')
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=64,blocks=8,new_native_outcomes=0,
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={name:sha(ROOT/name) for name in ('common.py','prepare.py','repair.py','audit_repair.py','optimizer.py','audit_optimizer.py','reader.py','sign_graph.py')},
        sources_sha256=bindings,outputs_sha256=outputs,source_prepared=str(previous),independent_optimizer_checks=all_checks,
        independent_record_checks=len(rows)*9))
    print(feasibility,flush=True)


if __name__=='__main__':prepare(read(ROOT/'config.json'))
