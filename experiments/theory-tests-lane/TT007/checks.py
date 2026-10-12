"""Synthetic implementation qualification; no native outcomes are consumed."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
from scipy.special import expit
import analysis
import geometry as g
import models as m
import support as s


def synthetic(seed=701):
    rng=np.random.default_rng(seed);rows=[]
    for block in s.CFG['blocks']:
        for history in s.CFG['histories']:
            for founder in range(4):
                for recipient in range(4):
                    values=rng.uniform(-.2,1.,4);margin=float(min(values));target=int(rng.random()<expit(2*values[0]-values[2]))
                    row=dict(block=block,history=history,founder=founder,recipient=recipient,generation=14,task_rule=1 if founder%2==0 else -1)
                    row.update(zip(s.CFG['expression_features'][:4],map(float,values)))
                    row.update(current_margin=margin,current_pass=int(margin>.25),unsigned_access=float(rng.uniform(0,.4)),
                        signed_transfer=float(rng.uniform(-.2,.2)),terminal_success=target,terminal_margin=.8 if target else -.1)
                    rows.append(row)
    return rows


def submitted():
    sys.path.insert(0,str(s.SUB))
    try:
        spec=importlib.util.spec_from_file_location('tt007_submitted_analysis',s.SUB/'analyze.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    finally:sys.path.pop(0)
    return module


def rejects(action,label):
    try:action()
    except (ValueError,AssertionError,ArithmeticError):return
    raise AssertionError('Failed to reject '+label)


def capture_checks():
    body=np.full((2,16,16),.2);mask=np.zeros((16,16),bool)
    weight=float(np.tanh(.6))**2
    s.close(g.capture(body,mask),np.full((2,16,16),weight),1e-15,'Returning-edge fallback')
    body[1]=-.2
    s.close(g.capture(body,mask),np.full((2,16,16),weight),1e-15,'Contrast product')
    body[0]=.2;body[1]=.2+1e-6
    delta=(np.tanh(3*body[0,0,0])-np.tanh(3*body[1,0,0]))/2
    packet=g.capture(body,mask)
    s.close(packet,np.full((2,16,16),delta**2),1e-25,'Exact nonzero branch')
    s.require(0<float(packet.max())<1e-4,'Tiny contrast fixture')
    mask[0,0]=True;packet=g.capture(body,mask)
    zero={(0,0,0),(0,0,15),(1,0,0),(1,15,0)}
    s.require(set(map(tuple,np.argwhere(packet==0)))==zero,'Damaged incident edges or torus wrap')
    s.require(not g.capture(np.zeros_like(body),mask).any(),'Zero packet')


def graph_checks():
    rng=np.random.default_rng(702);packet=rng.normal(size=(2,16,16));packet[abs(packet)<.5]=0
    dense=np.zeros((256,256))
    # Assemble by each vertex's four neighbors, without the production edge list.
    for y in range(16):
        for x in range(16):
            for yy,xx,w in [(y,(x+1)%16,packet[0,y,x]),(y,(x-1)%16,packet[0,y,(x-1)%16]),
                            ((y+1)%16,x,packet[1,y,x]),((y-1)%16,x,packet[1,(y-1)%16,x])]:
                dense[y*16+x,yy*16+xx]=w
    den=abs(dense).sum(axis=1);dense=np.divide(dense,den[:,None],out=np.zeros_like(dense),where=den[:,None]>0)
    s.close(g.operator(packet).toarray(),dense,3e-16,'Sparse/dense normalization')
    means=[]
    for op in [dense,abs(dense)]:
        value=np.zeros(256);value[g.PORTS[0]]=1
        for _ in range(64):value=op@value;value[g.PORTS[0]]=1
        means.append([float(value[p].mean()) for p in g.PORTS[1:]])
    for rule in [-1,1]:s.close(g.transfers(packet,rule),[min(rule*means[0][0],-rule*means[0][1]),min(means[1])],1e-14)
    s.close(g.operator(packet*1e-300).toarray(),dense,1e-15,'Tiny positive rescaling')
    s.close(g.transfers(np.zeros_like(packet),1),[0,0],0.)
    s.require(np.max(abs(g.operator(packet)).sum(axis=1))<=1+1e-14,'Operator bound')


def derivatives():
    rng=np.random.default_rng(703);a=np.c_[np.ones(96),rng.normal(size=(96,5))];y=rng.integers(0,2,96);w=rng.normal(size=6)
    value,gradient,hessian=m.objective(a,y,w,hessian=True);epsilon=1e-5;basis=np.eye(6)*epsilon
    numerical_g=np.array([(m.objective(a,y,w+d)[0]-m.objective(a,y,w-d)[0])/(2*epsilon) for d in basis])
    numerical_h=np.column_stack([(m.objective(a,y,w+d)[1]-m.objective(a,y,w-d)[1])/(2*epsilon) for d in basis])
    s.close(gradient,numerical_g,1e-9,'Finite difference gradient');s.close(hessian,numerical_h,1e-9,'Finite difference Hessian')
    s.require(np.linalg.eigvalsh(hessian).min()>0 and np.isfinite(value),'Strict convexity fixture')
    intercept=np.array([np.log(3.),0,0,0,0,0]);a=np.c_[np.ones(4),np.zeros((4,5))];y=np.array([1,1,1,0])
    s.close(m.objective(a,y,intercept)[1],np.zeros(6),1e-15,'Unpenalized intercept')


def fits_and_isolation():
    source=submitted();rows=synthetic();m.validate(rows);source.validate(rows,s.CFG)
    blocks=np.array([r['block'] for r in rows]);test=blocks==blocks[0];train=~test;y=np.array([r['terminal_success'] for r in rows],float)
    y_flip=y.copy();y_flip[test]=1-y_flip[test];max_error=0.
    poisoned=copy.deepcopy(rows)
    for row in poisoned:
        for field in ['block','founder','recipient','generation','task_rule','terminal_margin','terminal_success','seed','future_success']:row[field]=1e100
    for model in s.CFG['models'][1:]:
        x,names=m.matrix(rows,model);xx,source_names=source.design(rows,s.CFG,model)
        s.require(names==source_names,'Submitted feature order');s.close(x,xx,0.)
        s.close(x,m.matrix(poisoned,model)[0],0.);s.close(x,source.design(poisoned,s.CFG,model)[0],0.)
        own_z,own=m.fit(x,y,train,test);source_z,old=source.fit_fold(x,y,train,test,s.CFG)
        max_error=max(max_error,s.close(expit(own_z),expit(source_z),1e-4,'Newton/L-BFGS-B synthetic agreement'))
        for fitter,base_z,base in [(m.fit,own_z,own),(lambda *args:source.fit_fold(*args,s.CFG),source_z,old)]:
            z,other=fitter(x,y_flip,train,test);s.close(z,base_z,0.,'Held-out labels influenced prediction')
            s.close(other['coefficients'],base['coefficients'],0.)
            changed=x.copy();changed[test]=17*x[test]+4
            _,other=fitter(changed,y,train,test)
            for field in ['coefficients','mean','scale']:s.close(other[field],base[field],0.,'Held-out features influenced '+field)
        a=np.c_[np.ones(train.sum()),(x[train]-np.array(own['mean']))/np.array(own['scale'])]
        s.require(np.max(abs(m.objective(a,y[train],np.array(own['coefficients']))[1]))<=1e-10,'Newton residual')
    z,base=source.rate_fold(rows,y,train,test,s.CFG);changed_z,changed=source.rate_fold(rows,y_flip,train,test,s.CFG)
    s.close(z,changed_z,0.);s.require(base==changed,'Rate uses held-out targets')
    own_z,own=m.rate(rows,train,test);s.close(own_z,z,1e-14);s.require(own==base,'Half-count history rate')
    return dict(synthetic_logistic_models=5,maximum_probability_error=max_error,heldout_label_and_feature_isolation='PASS',forbidden_fields='PASS')


def matching_checks():
    source=submitted();rows=synthetic();left,right=s.CFG['matched_pair']
    # Binary-representable .5 base plus the two nearest .52 values straddles .02.
    for row in rows:
        for name in s.CFG['expression_features'][:4]:row[name]=.5
        if row['history']==right and row['recipient']==0:row[s.CFG['expression_features'][0]]=.52
        if row['history']==right and row['recipient']==1:row[s.CFG['expression_features'][0]]=np.nextafter(.52,0.).item()
        if row['history']==right and row['recipient']==2:row[s.CFG['expression_features'][0]]=.25
        row['current_margin']=min(row[n] for n in s.CFG['expression_features'][:4]);row['current_pass']=int(row['current_margin']>.25)
    pairs=analysis.pair_rows(rows);original,unused=source.matching(rows,s.CFG)
    analysis.compare(pairs,original,'Synthetic matching')
    for row in pairs:s.require(row['strict_match']==int(row['recipient'] in [1,3]),'Strict caliper/pass boundary')
    s.require(all(analysis.choice(a,b)==expected for a,b,expected in [(1,1,.5),(2,1,1),(1,2,0)]),'Choice ties')
    s.require(analysis.subset([])['difference'] is None and analysis.decision([],'margin')['success_rate'] is None,'Empty subset')
    fixed=copy.deepcopy(rows)
    for row in fixed:
        for name in s.CFG['expression_features'][:4]:row[name]=.5 if row['history']==left else .625
        row['current_margin']=min(row[n] for n in s.CFG['expression_features'][:4]);row['current_pass']=1
    previous=s.CFG['match_caliper']
    try:
        s.CFG['match_caliper']=.125
        s.require(all(p['strict_match'] for p in analysis.pair_rows(fixed)),'Inclusive exact caliper boundary')
        s.CFG['match_caliper']=float(np.nextafter(.125,0.))
        s.require(not any(p['strict_match'] for p in analysis.pair_rows(fixed)),'Immediately outside caliper')
    finally:s.CFG['match_caliper']=previous


def corruption_checks():
    rows=synthetic();rejects(lambda:m.validate(rows[:-1]),'missing context');rejects(lambda:m.validate(rows+[rows[0]]),'duplicated context')
    rejects(lambda:s.close([1],[float('nan')]),'nonfinite observation');rejects(lambda:s.close([1],[1,1]),'shape mismatch')
    rejects(lambda:analysis.compare_csv([dict(id=1,v=1),dict(id=1,v=1)],[dict(id='1',v='1'),dict(id='2',v='1')],['id']),'duplicate CSV')
    parent=Path(os.environ.get('TT007_TMP',s.HERE.parent/'.cache'));parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tt007_check_',dir=parent) as directory:
        value=np.array([1.,2.]);index={'x':dict(shape=[2],dtype=value.dtype.str,sha256=hashlib.sha256(value.tobytes()).hexdigest())}
        path=Path(directory)/'case.npz';np.savez(path,x=value,__index__=np.frombuffer(json.dumps(index).encode(),np.uint8));s.arrays(path)
        value[0]=3.;np.savez(path,x=value,__index__=np.frombuffer(json.dumps(index).encode(),np.uint8));rejects(lambda:s.arrays(path),'corrupted indexed array')


def run():
    started=time.monotonic();results={}
    for check in [capture_checks,graph_checks,derivatives,fits_and_isolation,matching_checks,corruption_checks]:
        result=check();results[check.__name__]=dict(status='PASS',**(result or {}))
    return dict(status='PASS',groups=len(results),checks=results,seconds=time.monotonic()-started,native_trajectories_generated=0)


if __name__=='__main__':print(json.dumps(run(),indent=2))
