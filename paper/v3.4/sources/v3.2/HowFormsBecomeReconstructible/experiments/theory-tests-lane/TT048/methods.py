"""Record-only proposals and explicit abstention; no controls or task labels."""
import math,time
import numpy as np
import native as n
import optimizer as opt
import repair
from common import OPTIONS,ARMS,exact

def eligible(signs,c,graph_signs=None,improvable=0):
 g=np.asarray(signs).reshape(256);total=math.fsum(map(abs,map(float,c)))
 fraction=opt.objective(g,c)/total if total else 0.
 connected=all(set(nodes)&set(opt.INPUT_PINS) or not any(c[e]!=0 and int(opt.U[e]) in nodes for e in range(512)) for nodes in opt.groups(c))
 output_uniform=all(len(set(g[port].tolist()))==1 for port in n.PORTS[1:])
 agreement=graph_signs is None or np.array_equal(g[np.concatenate(n.PORTS[1:])],np.asarray(graph_signs).reshape(256)[np.concatenate(n.PORTS[1:])])
 accepted=bool(total>0 and fraction<=.05 and connected and output_uniform and agreement and improvable==0)
 return dict(eligible=accepted,empty=total==0,weighted_disagreement=float(fraction),
  all_observed_components_anchored=bool(connected),output_patches_uniform=bool(output_uniform),
  forest_output_agreement=bool(agreement),selected_improvable_nodes=int(improvable),historical_status='UNVERIFIED')

def proposal(o,g,median):
 edges=np.asarray(g).reshape(256)[opt.U]*np.asarray(g).reshape(256)[opt.V]
 magnitude=np.where(o.ravel()!=0,abs(o.ravel()),median)
 return (magnitude*edges).reshape(2,256)

def build(outgoing):
 if type(outgoing) is not np.ndarray or outgoing.shape!=(2,256) or outgoing.dtype!=np.float64 or not np.isfinite(outgoing).all():
  raise ValueError('only a finite 2-by-256 float64 current record is accepted')
 before=outgoing.tobytes();c=opt.coupling(outgoing)
 start=time.process_time();g=opt.forest(c,opt.INPUT_PINS);graph_cpu=time.process_time()-start
 start=time.process_time();z,solution,median=repair.recipient(outgoing,OPTIONS);optimizer_cpu=time.process_time()-start
 m=solution['signs'].ravel();gp=proposal(outgoing,g,median);mp=proposal(outgoing,m,median)
 gd=eligible(g,c);md=eligible(m,c,g,solution['selected_improvable_nodes'])
 rows=np.stack((outgoing,z,gp,mp,gp if gd['eligible'] else outgoing,mp if md['eligible'] else outgoing))
 assert outgoing.tobytes()==before
 exact(abs(rows[2]),abs(rows[3]),'graph/optimizer identical support and magnitude budgets')
 exact(rows[1][outgoing!=0],outgoing[outgoing!=0],'TT014 observed weights preserved')
 decisions=[]
 for name,record in zip(ARMS,rows):
  gate=gd if name in ('G','GA') else md if name in ('M','MA') else None
  abstain=name in ('GA','MA') and not gate['eligible']
  edited=record.tobytes()!=outgoing.tobytes()
  decisions.append(dict(arm=name,action='abstain' if abstain else 'edit' if edited else 'no_change',
   historical_status='UNVERIFIED',structural_diagnostics=gate,structurally_eligible=None if gate is None else gate['eligible'],
   added_edges=int(np.count_nonzero((outgoing==0)&(record!=0))),
   flipped_nonzero_edges=int(np.count_nonzero((outgoing!=0)&(record*outgoing<0))),
   changed_edge_values=int(np.count_nonzero(record!=outgoing)),total_abs_weight=math.fsum(map(abs,map(float,record.ravel())))))
 return rows,dict(graph_signs=g,optimizer=solution,median=median,decisions=decisions,
  graph_cpu_seconds=graph_cpu,optimizer_and_zero_fill_cpu_seconds=optimizer_cpu,optimizer_calls=1)
