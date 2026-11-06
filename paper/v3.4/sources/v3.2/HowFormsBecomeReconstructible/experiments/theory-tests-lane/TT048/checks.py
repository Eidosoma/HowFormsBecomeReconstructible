"""Adversarial controls, information boundary, arithmetic and strict scoring."""
from common import *
import ast,math
import native as n
import methods,independent,corruption,analysis

def rejects(fn):
 try:fn()
 except (AssertionError,ValueError,TypeError):return
 raise AssertionError('invalid fixture accepted')

def run():
 zero=np.zeros((2,256));out,meta=methods.build(zero);independent.methods(zero,out,meta)
 for d in meta['decisions'][4:]:assert d['action']=='abstain'
 for a in (0,1,4,5):exact(out[a],zero,'empty record preserved')
 rng=np.random.default_rng(480048);original=rng.uniform(.1,1,(2,256));acquired=np.repeat(original[None],4,axis=0)
 rows,cm=corruption.make(original,acquired,EXCLUDED,0);independent.corruption(original,acquired,EXCLUDED,0,rows,cm)
 for ri in (0,1,2,3,5,6):
  outputs,m=methods.build(rows[ri]);independent.methods(rows[ri],outputs,m)
  if ri in (5,6):
   assert m['optimizer']['cost']==0
   assert all(m['decisions'][a]['structurally_eligible'] for a in (2,3,4,5))
   assert all(d['historical_status']=='UNVERIFIED' for d in m['decisions'])
   exact(outputs[4],rows[ri],'balanced forest unchanged');exact(outputs[5],rows[ri],'balanced optimizer unchanged')
 # Opposite hidden labels on exactly the same input cannot affect this API.
 one,m1=methods.build(rows[6]);two,m2=methods.build(rows[6].copy());exact(one,two,'identical record action')
 assert m1['decisions']==m2['decisions']
 rejects(lambda:methods.build(rows[6],history_label=1));rejects(lambda:methods.build(dict(packet=rows[6],history=1)))
 rejects(lambda:methods.build(np.ones((2,255))));bad=original.copy();bad[0,0]=np.nan;rejects(lambda:methods.build(bad))
 tree=ast.parse((ROOT/'methods.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='build')
 assert [a.arg for a in fn.args.args]==['outgoing'] and not fn.args.kwarg
 assert not ({x.id for x in ast.walk(fn) if isinstance(x,ast.Name)} & {'source','read','open','founder','regime','history','target'})
 c=np.full(512,1/32.);g=np.ones(256,np.int8);c[0]=-1.;c[1]=98/32.
 assert methods.eligible(g,c)['weighted_disagreement']==.05 and methods.eligible(g,c)['eligible']
 c[0]*=1+1e-10;assert not methods.eligible(g,c)['eligible']
 c=np.zeros(512);c[0]=1;assert not methods.eligible(g,c)['eligible']
 c=np.ones(512);other=g.copy();other[n.PORTS[1]]=-1
 assert not methods.eligible(g,c,other)['eligible'] and not methods.eligible(g,c,improvable=1)['eligible']
 broken=g.copy();broken[n.PORTS[1][0]]=-1;assert not methods.eligible(broken,c)['eligible']
 # Independent scalar tally retains harmful policies and all abstention cases.
 data={};nf=4
 for endpoint in ('intended','opposite'):
  data[endpoint+'_pass']=rng.integers(0,2,(8,16,6,nf)).astype(bool)
  data[endpoint+'_margin']=rng.normal(size=(8,16,6,nf))
 initial=np.arange(16)%3!=0;eligible=rng.integers(0,2,(8,16,6)).astype(bool);actions=rng.integers(0,3,(8,16,6),dtype=np.int8)
 agg=analysis.reduce(data,initial,0,eligible,actions)
 for gi,group in enumerate(GROUPS):
  ix=np.flatnonzero(analysis.subset(initial,0,group))
  for endpoint in ('intended','opposite'):
   x=data[endpoint+'_pass']
   for ri in range(8):
    for ai in range(6):
     assert agg[endpoint+'_counts'][gi,ri,ai]==sum(int(x[ri,c,ai,f]) for c in ix for f in range(nf))
     assert agg[endpoint+'_conditional_counts'][gi,ri,ai]==sum(int(x[ri,c,ai,f]) for c in ix for f in range(nf) if eligible[ri,c,ai])
    for ki,(a,b) in enumerate(PAIRS):
     table=np.zeros((2,2),np.int64);sgn=np.zeros(3,np.int64)
     for c0 in ix:
      change=sum(int(x[ri,c0,b,f])-int(x[ri,c0,a,f]) for f in range(nf));sgn[int(np.sign(change))+1]+=1
      for f in range(nf):table[int(x[ri,c0,a,f]),int(x[ri,c0,b,f])]+=1
     exact(table,agg[endpoint+'_paired_table'][gi,ri,ki],'scalar paired table');exact(sgn,agg[endpoint+'_record_signs'][gi,ri,ki],'scalar harms')
     if len(ix):
      values=[sum(int(x[ri,c0,b,f])-int(x[ri,c0,a,f]) for c0 in ix)/len(ix) for f in range(nf)]
      se=math.sqrt(sum((values[i]-values[j])**2 for i in range(nf) for j in range(i))/(nf*nf*(nf-1)))
      near(se,agg[endpoint+'_effect_mc_se'][gi,ri,ki],'independent paired MC error')
 second={k:v.copy() for k,v in agg.items()};second['records']*=3
 for k in ('eligible_counts','action_counts','intended_counts','opposite_counts','intended_conditional_counts','opposite_conditional_counts',
           'intended_paired_table','opposite_paired_table','intended_record_signs','opposite_record_signs'):second[k]*=3
 for endpoint in ('intended','opposite'):second[endpoint+'_effect_mc_se']*=2
 combined=analysis.combine([agg,second])
 for endpoint in ('intended','opposite'):
  near(combined['equal_'+endpoint+'_effect_mc_se'][0],agg[endpoint+'_effect_mc_se'][0]*math.sqrt(5)/2)
  near(combined['pooled_'+endpoint+'_effect_mc_se'][0],agg[endpoint+'_effect_mc_se'][0]*math.sqrt(37)/4)
 assert np.all(combined['group_records'][4:]==0) and not combined['eligible_rate_defined'][4:].any()
 # Strict boundary and opposite target are scored separately.
 import reader
 for value,expected in ((.25,False),(np.nextafter(.25,np.inf),True),(np.nextafter(.25,-np.inf),False)):
  means=np.array([[[[[[value,-value],[-value,value]]]]]])
  assert bool(reader.scores(means,np.array([0]),.25)['both_pass'].item())==expected
  assert not bool(reader.scores(means,np.array([1]),.25)['both_pass'].item())
 return dict(status='PASS',balanced_correct_and_wrong_zero_cost=True,coherent_wrong_can_pass_structural_gate=True,
  identical_input_hidden_label_abstention_limit=True,history_always_unverified=True,empty_and_disconnected_abstention=True,
  exact_threshold_checked=True,wrong_shapes_and_hidden_fields_rejected=True,independent_corruption_and_repairs=True,
  all_pairwise_counts_and_harms=True,squared_weight_mc_errors=True,strict_task_boundary=True)
