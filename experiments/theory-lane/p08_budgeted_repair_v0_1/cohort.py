"""All-record enrollment and frozen recipient-only construction."""
import numpy as np
import lineage_dynamics as dynamics
import audit_optimizer
from common import equal
from reader import PORTS,decode,stream
from repair import recipient_repair,edge_signs


def seed_identity(block,cfg):
    return cfg['lineage_namespace']+':'+str(block)


def history_index(block,cfg):return cfg['history_by_block'][str(block)]


def develop(acquisition,block,cfg):
    seed=seed_identity(block,cfg);h=history_index(block,cfg)
    packets=np.repeat(acquisition['acquired'][:,None],4,axis=1)[None]
    collected={k:[] for k in ('incoming','outgoing','bodies','masks','births','mean_ports','writer_codes')}
    for generation in range(1,15):
        tolerance=generation in cfg['tolerance_generations'][h]
        raw=dynamics.rebuild(packets,seed,generation,['tolerance_rewrite' if tolerance else 'exact_rewrite'],
                             cfg['development_config'],cfg['cycle'],cfg['tolerance'])
        for name,value in dict(incoming=packets.reshape(16,4096),outgoing=raw['outgoing'].reshape(16,4096),
            bodies=raw['end'].reshape(16,2,16,16),masks=raw['masks'].reshape(16,16,16),
            births=raw['birth'].reshape(16,2,16,16),mean_ports=raw['mean_ports'].reshape(16,2,2),writer_codes=np.array(int(tolerance))).items():
            collected[name].append(value.copy())
        packets=raw['outgoing']
    return dict(block=np.array(block),history=np.array(h),**{k:np.stack(v) for k,v in collected.items()})


def masks(block,cfg):
    eligible=np.flatnonzero(~PORTS.any(axis=0).ravel());result=np.zeros((16,len(cfg['replicates']),16,16),bool)
    for case in range(16):
        f,r=divmod(case,4)
        for ri,rep in enumerate(cfg['replicates']):
            random=stream(cfg['random_namespace'],block,'injury',rep,f//2,r)
            result[case,ri].flat[random.choice(eligible,24,replace=False)]=True
    return result


def construct(outgoing,block,cfg,independent=True):
    assert outgoing.shape==(16,2,16,16)
    h=history_index(block,cfg);records=[];solutions=[];magnitudes=[];changed=[]
    for case,o in enumerate(outgoing):
        completed,solution,magnitude=recipient_repair(o,cfg['optimizer'])
        if independent:
            coupling=audit_optimizer.independent_coupling(o)
            reference=audit_optimizer.solve(coupling,np.flatnonzero(PORTS[0].ravel()),cfg['optimizer'])
            for key in ('signs','candidate_costs','flips','final_improvable_nodes'):equal(reference[key],solution[key],'independent optimizer '+key)
            for key in ('cost','initial_cost','winner','sweeps','selected_improvable_nodes'):assert reference[key]==solution[key]
        f,r=divmod(case,4);missing=o==0;shuffled=o.copy()
        order=stream(cfg['random_namespace'],block,'shuffle',h,f,r).permutation(int(missing.sum()))
        if magnitude>0:shuffled[missing]=magnitude*edge_signs(solution['signs'])[missing][order]
        records.append(np.stack((o,completed,shuffled,np.zeros_like(o))));solutions.append(solution);magnitudes.append(magnitude)
        changed.append(int(np.count_nonzero(completed[missing]!=shuffled[missing])))
    packets=np.ascontiguousarray(records,dtype='<f8').view(np.uint8).reshape(16,4,4096)
    data=dict(block=np.array(block),packets=packets,founders=np.repeat(np.arange(4),4),recipients=np.tile(np.arange(4),4),
        histories=np.full(16,h),masks=masks(block,cfg),replicates=np.array(cfg['replicates']),imputed_magnitudes=np.array(magnitudes),
        missing_edge_counts=(outgoing==0).sum(axis=(1,2,3)),added_abs_weight=np.array([abs(row[1][o==0]).sum() for row,o in zip(records,outgoing)]),
        shuffled_sign_changes=np.array(changed))
    for key in ('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes'):
        data['optimizer_'+key]=np.array([s[key] for s in solutions])
    return data


def body_pass(mean_ports):
    rules=np.repeat([1.,-1.,1.,-1.],4)
    aligned=mean_ports*rules[:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    return aligned.min(axis=(1,2))>.25
