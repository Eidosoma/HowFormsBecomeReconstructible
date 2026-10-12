"""Prepare fixed approximate grafts and controls before native outcome reads."""
import csv
import time
import numpy as np
from common import ROOT,arrays,equal,read,save_arrays,sha,stamp,validate,write
from reader import PORTS,decode,stream,available
from optimizer import align,complete,graft,influence
import audit_optimizer
from sign_graph import equivalent


def masks(cfg,block,founders,recipients):
    eligible=np.flatnonzero(~PORTS.any(axis=0).ravel())
    result=np.zeros((len(founders),len(cfg['replicates']),16,16),bool)
    for case,(f,r) in enumerate(zip(founders,recipients)):
        for ri,rep in enumerate(cfg['replicates']):
            random=stream(cfg['random_namespace'],block,'injury',rep,int(f)//2,int(r))
            result[case,ri].flat[random.choice(eligible,cfg['injury_cells'],replace=False)]=True
    return result


def solve_records(outgoing,donors,options):
    solved=[align(outgoing,d,options) for d in donors]+[complete(outgoing,options)]
    for di,result in enumerate(solved):
        donor=donors[di] if di<2 else None
        other=audit_optimizer.independent_coupling(outgoing,donor)
        intended=influence(outgoing)*np.sign(outgoing)*(np.sign(donor) if donor is not None else 1)
        # Absent edges can acquire -0.0 under sign multiplication; these are the
        # same constraint. Require exact values, without a numerical tolerance.
        assert np.array_equal(other,intended),'independent influence weights'
        pins=np.flatnonzero((PORTS.any(axis=0) if di<2 else PORTS[0]).ravel())
        reference=audit_optimizer.solve(other,pins,options)
        for key in ('signs','candidate_costs','flips','final_improvable_nodes'):equal(reference[key],result[key],'independent optimizer '+key)
        for key in ('cost','initial_cost','winner','sweeps','selected_improvable_nodes'):assert reference[key]==result[key],key
    return solved


def make_records(outgoing,donors,common,magnitudes,solved,own_signs):
    variants=[None,outgoing,graft(outgoing,own_signs,common,magnitudes)]
    variants += [graft(outgoing,d,common,magnitudes) for d in donors]
    variants += [graft(outgoing,d,common,magnitudes,s['signs']) for d,s in zip(donors,solved[:2])]
    variants += [graft(outgoing,np.ones_like(outgoing),common,magnitudes,solved[2]['signs']),np.zeros_like(outgoing)]
    return variants


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
    old_receipt=read(previous/'COMPLETE.json')
    audit=ROOT.parent/'p05_sign_alignment_audit_v0_1/COMPLETE.json'
    bind(audit,cfg['alignment_audit_complete_sha256'])
    outputs={};rows=[];all_checks=0
    for block,n in zip(cfg['blocks'],cfg['cases_per_block']):
        name=f'cases_{block:06d}.npz';bind(previous/name,old_receipt['outputs_sha256'][name])
        old=arrays(previous/name);assert len(old['founders'])==n
        out=decode(old['packets'][:,1]);donors=decode(old['donor_packets'])
        solutions=[solve_records(o,dd,cfg['optimizer']) for o,dd in zip(out,donors)]
        all_checks+=3*n
        # Missing own signs first enter construction after all solvers finish.
        incoming=decode(old['packets'][:,0]);records=[];equivalences=[];changes=[]
        for case,solved in enumerate(solutions):
            common=old['common_edges'][case]
            assert not out[case][~available(old['original_masks'][case])].any()
            row=make_records(out[case],donors[case],common,abs(incoming[case]),solved,incoming[case])
            row[0]=incoming[case];records.append(np.stack(row))
            pins=np.flatnonzero(PORTS.any(axis=0).ravel())
            eq=[bool(equivalent(row[3+d],row[5+d],pins)['ok']) for d in (0,1)]
            change=[int(np.count_nonzero(np.sign(row[3+d][common])!=np.sign(row[5+d][common]))) for d in (0,1)]
            equivalences.append(eq);changes.append(change)
            for di,result in enumerate(solved):
                rows.append(dict(block=block,case=case,problem=('same','opposite','completion')[di],
                    initial_cost=result['initial_cost'],cost=result['cost'],total_weight=result['total_weight'],
                    mismatch_fraction=result['mismatch_fraction'],winner=result['winner'],sweeps=result['sweeps'],
                    selected_improvable_nodes=result['selected_improvable_nodes'],
                    backup_sign_changes=change[di] if di<2 else '',hybrid_gauge_equivalent=eq[di] if di<2 else ''))
        values=np.stack(records)
        packets=np.ascontiguousarray(values,dtype='<f8').view(np.uint8).reshape(n,9,4096)
        equal(packets[:,[0,1,2,3,4,8]],old['packets'][:,[0,1,3,4,5,7]],'unaltered controls')
        for vi in range(3,8):equal(abs(values[:,2]),abs(values[:,vi]),'matched unsigned records')
        data={k:old[k] for k in ('block','histories','founders','recipients','original_masks','original_end','original_mean_ports','original_birth','donor_packets','donor_founders','common_edges')}
        data.update(packets=packets,masks=masks(cfg,block,old['founders'],old['recipients']),
                    replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),
                    hybrid_gauge_equivalent=np.array(equivalences),backup_sign_changes=np.array(changes))
        for key in ('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes'):
            data['optimizer_'+key]=np.array([[s[key] for s in group] for group in solutions])
        outputs[name]=save_arrays(folder/name,data)
    with (folder/'optimizer.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    outputs['optimizer.csv']=sha(folder/'optimizer.csv')
    donors=[r for r in rows if r['problem']!='completion']
    feasibility=dict(problems=192,independent_optimizer_checks=all_checks,donor_pairs=128,
        changed_backup_pairs=sum(r['backup_sign_changes']>0 for r in donors),
        non_equivalent_hybrids=sum(not r['hybrid_gauge_equivalent'] for r in donors),
        strict_objective_improvements=sum(r['cost']<r['initial_cost'] for r in donors),
        selected_with_improving_single_flip=sum(r['selected_improvable_nodes']>0 for r in rows),
        maximum_sweeps_used=max(r['sweeps'] for r in rows),seconds=time.perf_counter()-begin)
    write(folder/'FEASIBILITY.json',feasibility);outputs['FEASIBILITY.json']=sha(folder/'FEASIBILITY.json')
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=64,blocks=8,new_native_outcomes=0,
        config_sha256=sha(ROOT/'config.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        code_sha256={name:sha(ROOT/name) for name in ('common.py','prepare.py','optimizer.py','audit_optimizer.py','reader.py','sign_graph.py')},
        sources_sha256=bindings,outputs_sha256=outputs,source_prepared=str(previous),
        independent_optimizer_checks=all_checks,nontrivial_comparison=feasibility['non_equivalent_hybrids']>0))
    print(feasibility,flush=True)


if __name__=='__main__':prepare(read(ROOT/'config.json'))
