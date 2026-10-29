"""Target geometry and energy of archived wrong states under the new record."""
from itertools import product
import numpy as np
from h077.audit import exact_projector
from h090.analysis import Check,components
from h092 import geometry as old
from h092.audit import infer
from h093 import model as m,dynamics,reference

ZERO,TOL=1e-9,1e-12

def probe(record,projector,state,check):
    ref={k:v.copy() for k,v in record.items()};ref['J']=projector.copy();np.fill_diagonal(ref['J'],0)
    h=dynamics.fields(record,state);expected=reference.fields(ref,state);check.field(h,expected)
    parts=np.concatenate((components(record['J'],state),dynamics.factor_fields(record,state)[...,80:,None]),axis=-1)
    refparts=np.concatenate((components(ref['J'],state.astype(np.longdouble)),reference.factor_fields(ref,state)[...,80:,None]),axis=-1)
    check.field(parts,refparts);check.field(parts.sum(-1),h[...,80:])
    energy=dynamics.energy(record,state);check.energy(energy,reference.energy(ref,state))
    factor=dynamics.factor_energy(record,state);check.energy(factor,reference.factor_energy(ref,state))
    long=state.astype(np.longdouble);residual=np.square(long-long@projector).sum(-1)
    regret=np.sum(np.abs(record['interaction_weights']))+factor
    floor=-(128-np.trace(projector))/2-np.sum(np.abs(record['interaction_weights']))
    assert np.all(regret>=-2e-11);check.energy(energy,floor+residual/2+regret)
    wanted=check.decide(expected,state);free=np.r_[0:32,80:128]
    return dict(fields=h,parts=parts,energy=energy,residual=residual.astype(float),factor_energy=factor,factor_regret=regret,
        full_fixed=(wanted==state).all(-1),conditional_fixed=(wanted[...,free]==state[...,free]).all(-1))

def extract(raw,graph,interactions):
    if not interactions:return old.extract(raw,graph,True)
    check=Check();lineages={(r['origin'],r['route'],r['policy'],r['generation'],r['birth']):r for r in graph['lineages']}
    bundles=[];metadata=[]
    for origin in m.ORIGINS:
        target=raw['responses_'+origin];patterns=np.concatenate((raw['inputs'],target),axis=1)
        founder=lineages[origin,'rewrite','ordinary',0,0];node=graph['records'][founder['record']]
        assert node['operation']=='founder' and node['parent_record']==-1
        check.same(raw['packet_outputs'][node['packet_index']],target[m.TRAIN],'founder teaching boundary')
        record=m.get_record(raw,graph,founder['record']);learned=np.concatenate((raw['inputs'],raw['completion_outputs'][node['packet_index']]),axis=1)
        p,rank=exact_projector(learned.astype(np.int64));ref=p.copy();np.fill_diagonal(ref,0)
        check.same(record['J'],ref,'independent completed founder projector',4e-14)
        final=[]
        for b in range(4):
            item=lineages[origin,'rewrite','ordinary',0,b];paired=lineages[origin,'rewrite','pair',0,b]
            assert item['record']==paired['record']==founder['record'] and item['read']==paired['read']
            data=m.get_read(raw,graph,item['read']);final.append(np.stack([data[reader+'_final'][:,0] for reader in m.READERS]))
        final=np.stack(final);corrected=final.copy();corrected[...,80:]=target
        bundle=dict(record=record['J'].copy(),interaction_masks=record['interaction_masks'].copy(),interaction_weights=record['interaction_weights'].copy(),
            projector=p.astype(float),patterns=patterns,final=final,target=target.copy(),learned_patterns=learned.copy())
        for prefix,state in (('intended',patterns),('endpoint',final),('corrected',corrected)):
            bundle.update({prefix+'_'+k:v for k,v in probe(record,p,state,check).items()})
        bundles.append(bundle);metadata.append(dict(origin=origin,record=founder['record'],pattern_rank=rank,
            input_rank=int(np.linalg.matrix_rank(raw['inputs'][m.TRAIN].astype(float)))))
    result={key:np.stack([b[key] for b in bundles]) for key in bundles[0]};result['inputs']=raw['inputs'].copy()
    return result,metadata,dict(geometry_checks=check.count,geometry_max_field_error=check.max_field_error,
        geometry_max_energy_error=check.max_energy_error,geometry_minimum_boundary_distance=check.boundary_minimum)

def get_record(data,oi):
    return dict(J=data['record'][oi],interaction_masks=data['interaction_masks'][oi],interaction_weights=data['interaction_weights'][oi])

def validate(data,metadata):
    if 'interaction_masks' not in data:return old.validate(data,metadata)
    check=Check()
    for oi in range(2):
        p,rank=exact_projector(data['learned_patterns'][oi].astype(np.int64));ref=p.copy();np.fill_diagonal(ref,0)
        check.same(data['record'][oi],ref,'reloaded geometry J',4e-14);check.same(data['projector'][oi],p,'reloaded projector',4e-14)
        assert metadata[oi]['pattern_rank']==rank
        masks,signs,prediction=infer(data['target'][oi,m.TRAIN])
        record=get_record(data,oi);check.same(record['interaction_masks'],masks,'reloaded founder masks')
        check.same(record['interaction_weights'],signs*(((masks&3)!=0)&((masks&12)!=0)),'reloaded founder coefficients')
        final=data['final'][oi];corrected=final.copy();corrected[...,80:]=data['target'][oi]
        for prefix,state in (('intended',data['patterns'][oi]),('endpoint',final),('corrected',corrected)):
            for key,value in probe(record,p,state,check).items():check.same(data[prefix+'_'+key][oi],value,'reloaded '+prefix+' '+key,2e-11 if value.dtype.kind=='f' else 0)
    return check.count

def tables(data,metadata,block,literal=False):
    count=lambda v:sum(bool(x) for x in np.asarray(v).flat) if literal else int(np.count_nonzero(v))
    result=old.tables(data,metadata,block,literal)
    interactions='interaction_masks' in data
    if interactions:
        # The old table's equality test also requires zero quadratic residual.
        # Total energy equality to the generated target floor then forces zero regret.
        for row in result['patterns']:
            oi=m.ORIGINS.index(row['origin']);q=row['association']
            parts=data['intended_parts'][oi,q];drive=(parts[:,:2].sum(-1)+parts[:,3])*data['target'][oi,q]
            row.update(drive_opposed_bits=count(drive < -TOL),drive_neutral_bits=count(np.abs(drive)<=TOL),drive_supported_bits=count(drive>TOL))
    for kind,prefix in (('patterns','intended'),('geometry','endpoint')):
        for row in result[kind]:
            oi=m.ORIGINS.index(row['origin']);q=row['association'];idx=(oi,q) if kind=='patterns' else (oi,row['birth'],m.READERS.index(row['reader']),q)
            row.update(factor_regret_sum=float(data[prefix+'_factor_regret'][idx]) if interactions else 0.,
                       nonlinear_energy_sum=float(data[prefix+'_factor_energy'][idx]) if interactions else 0.)
    return result

def verify(data,metadata,rows):
    assert tables(data,metadata,rows['patterns'][0]['block'],True)==rows,'literal geometry recount'
    return 288

def repair(baseline,active,block,literal=False):
    """Evaluate every saved G0 endpoint; qualification uses the archived tie subset."""
    rows=[];check=Check()
    for oi,origin in enumerate(m.ORIGINS):
        record=get_record(active,oi);states=baseline['final'][oi];energy=dynamics.energy(record,states)
        ref=dict(record,J=active['projector'][oi].astype(np.longdouble));np.fill_diagonal(ref['J'],0)
        check.energy(energy,reference.energy(ref,states));gap=energy-active['intended_energy'][oi]
        for b,ri,q in product(range(4),range(2),range(16)):
            state=states[b,ri,q];target=baseline['target'][oi,q]
            hits=sum(int(u)==int(v) for u,v in zip(state[80:],target)) if literal else int((state[80:]==target).sum())
            matched=bool((state[:80]==baseline['inputs'][q]).all());fixed=bool(baseline['endpoint_conditional_fixed'][oi,b,ri,q])
            oldgap=baseline['endpoint_energy'][oi,b,ri,q]-baseline['intended_energy'][oi,q]
            eligible=hits<44 and matched and fixed and abs(oldgap)<=ZERO and baseline['endpoint_residual'][oi,b,ri,q]<=ZERO
            rows.append(dict(block=block,origin=origin,birth=b,reader=m.READERS[ri],panel='trained' if q in m.TRAIN else 'heldout',association=q,
                archived_queries=1,archived_equal_energy_failed_queries=int(eligible),repaired_failed_queries=int(eligible and gap[b,ri,q]>ZERO),
                unrepaired_failed_queries=int(eligible and gap[b,ri,q]<=ZERO),new_energy_gap_sum=float(gap[b,ri,q]),
                minimum_archived_energy_gap=float(gap[b,ri,q])))
    assert len(rows)==256
    return rows
