"""Independent design construction and damped Newton logistic regression."""
import itertools
import numpy as np
from scipy.special import expit
import support as s


def validate(records):
    identities=[s.key(r) for r in records]
    expected=set(itertools.product(s.CFG['blocks'],s.CFG['histories'],range(4),range(4)))
    s.require(len(identities)==len(set(identities)) and set(identities)==expected,'Missing/duplicate cohort identity')
    for r in records:
        s.require(r['generation']==14 and r['task_rule']==(1 if r['founder']%2==0 else -1),'Boundary/rule identity')
        values=[r[n] for n in s.CFG['expression_features'][:4]]
        s.require(r['current_margin']==min(values) and r['current_pass']==int(min(values)>.25),'Current score inconsistent')
        s.require(r['terminal_success'] in (0,1) and r['terminal_success']==int(r['terminal_margin']>.25),'Target inconsistent')


def columns(model):
    fields=list(s.CFG['expression_features'])
    if model['unsigned']:fields.append('unsigned_access')
    fields.extend('history='+h for h in s.CFG['histories'][1:])
    if model['quadratic']:
        for i in range(4):
            for j in range(i,4):fields.append(s.CFG['expression_features'][i]+'*'+s.CFG['expression_features'][j])
    if model['signed']:fields.append('signed_transfer')
    return fields


def feature(row,name):
    if name.startswith('history='):return float(row['history']==name[8:])
    if '*' in name:
        left,right=name.split('*');return float(row[left])*float(row[right])
    return float(row[name])


def matrix(records,model):
    names=columns(model);x=np.array([[feature(row,n) for n in names] for row in records])
    s.require(np.isfinite(x).all(),'Nonfinite design')
    return x,names


def objective(a,y,w,ridge=.01,hessian=False):
    logits=a@w;probability=expit(logits)
    loss=float(np.mean(np.logaddexp(0.,logits)-y*logits)+ridge*.5*np.dot(w[1:],w[1:]))
    gradient=a.T@(probability-y)/len(y);gradient[1:]+=ridge*w[1:]
    if not hessian:return loss,gradient
    curvature=(a.T*(probability*(1-probability)))@a/len(y)
    curvature[np.arange(1,len(w)),np.arange(1,len(w))]+=ridge
    return loss,gradient,curvature


def newton(a,y):
    s.require(0<float(np.sum(y))<len(y),'Unpenalized intercept needs both outcomes')
    w=np.zeros(a.shape[1]);trace=[]
    for iteration in range(s.PLAN['newton_maximum_iterations']):
        loss,gradient,hessian=objective(a,y,w,hessian=True)
        norm=float(np.max(abs(gradient)));trace.append(dict(iteration=iteration,objective=loss,maximum_gradient=norm))
        if norm<=s.PLAN['newton_gradient_tolerance']:return w,trace
        direction=np.linalg.solve(hessian,gradient);descent=float(gradient@direction)
        s.require(np.isfinite(direction).all() and descent>0,'Invalid Newton descent')
        fraction=1.
        for _ in range(50):
            candidate=w-fraction*direction;candidate_loss,_=objective(a,y,candidate)
            if candidate_loss<=loss-1e-4*fraction*descent+1e-15:break
            fraction*=.5
        else:raise ArithmeticError('Newton line search failed')
        w=candidate
    raise ArithmeticError('Newton convergence limit')


def fit(x,y,train,test):
    mu=np.mean(x[train],axis=0);sigma=np.std(x[train],axis=0);sigma[sigma<=1e-12]=1.
    a=np.c_[np.ones(np.count_nonzero(train)),(x[train]-mu)/sigma]
    b=np.c_[np.ones(np.count_nonzero(test)),(x[test]-mu)/sigma]
    coefficients,trace=newton(a,y[train]);logits=b@coefficients
    return logits,dict(mean=mu.tolist(),scale=sigma.tolist(),coefficients=coefficients.tolist(),
        objective=trace[-1]['objective'],maximum_gradient=trace[-1]['maximum_gradient'],trace=trace,success=True)


def rate(records,train,test):
    rates={};counts={}
    for h in s.CFG['histories']:
        group=[r for r,t in zip(records,train,strict=True) if t and r['history']==h]
        n=len(group);successes=sum(r['terminal_success'] for r in group);s.require(n>0,'Missing training history')
        rates[h]=(successes+.5)/(n+1.);counts[h]=dict(n=n,successes=successes)
    p=np.array([rates[r['history']] for r,t in zip(records,test,strict=True) if t])
    return np.log(p)-np.log1p(-p),dict(rates=rates,counts=counts)


def saved_predictions(records,output):
    """Reconstruct submitted probabilities, and refit without submitted code."""
    validate(records);block=np.array([r['block'] for r in records]);y=np.array([r['terminal_success'] for r in records],float)
    fits=s.read(s.SUB/'results/fits.json');fit_index={(f['model'],f['heldout_block']):f for f in fits}
    s.require(len(fits)==len(fit_index)==48,'Fit identity mismatch')
    raw=s.table(s.SUB/'results/predictions.csv')
    submitted={(r['model'],int(r['block']),r['history'],int(r['founder']),int(r['recipient'])):r for r in raw}
    expected={(m['id'],*s.key(r)) for m in s.CFG['models'] for r in records}
    s.require(len(submitted)==len(raw)==3072 and set(submitted)==expected,'Forecast identity mismatch')
    predictions=[];new_fits=[];checks=[]
    for model in s.CFG['models']:
        if model.get('estimator')!='rate':x,names=matrix(records,model)
        else:names=[]
        for heldout in s.CFG['blocks']:
            train=block!=heldout;test=~train;prior=fit_index[model['id'],heldout]
            s.require(prior['train_blocks']==[b for b in s.CFG['blocks'] if b!=heldout] and prior['n_train']==448 and prior['n_test']==64,'Fold membership mismatch')
            s.require(prior['columns']==names,'Feature whitelist mismatch')
            if model.get('estimator')=='rate':
                saved_z,independent=rate(records,train,test);new_z=saved_z.copy()
                s.require(independent['counts']==prior['counts'],'Rate counts mismatch')
                for h in independent['rates']:s.close(independent['rates'][h],prior['rates'][h])
                objective_difference=0.;gradient=0.
            else:
                s.require(prior['success'],'Submitted optimization failed')
                mean=x[train].mean(axis=0);scale=x[train].std(axis=0);scale[scale<=1e-12]=1.
                s.close(mean,prior['mean'],label='Training means');s.close(scale,prior['scale'],label='Training scales')
                a=np.c_[np.ones(train.sum()),(x[train]-mean)/scale]
                b=np.c_[np.ones(test.sum()),(x[test]-np.array(prior['mean']))/np.array(prior['scale'])]
                weights=np.array(prior['coefficients']);loss,g=objective(a,y[train],weights)
                s.close(loss,prior['objective'],label='Saved objective');gradient=float(np.max(abs(g)))
                s.require(gradient<1e-5,'Saved gradient inconsistent with convergence')
                saved_z=b@weights;new_z,independent=fit(x,y,train,test)
                objective_difference=abs(independent['objective']-loss)
                s.require(objective_difference<=s.PLAN['independent_refit_objective_tolerance'],'Independent objective mismatch')
            error=s.close(expit(saved_z),expit(new_z),s.PLAN['independent_refit_probability_tolerance'],'Independent refit probabilities')
            independent.update(model=model['id'],heldout_block=heldout,columns=names,train_blocks=prior['train_blocks'],n_train=448,n_test=64)
            new_fits.append(independent);saved_error=0.
            for index,z,z_new in zip(np.flatnonzero(test),saved_z,new_z,strict=True):
                row=records[index];saved=submitted[model['id'],*s.key(row)];p=float(expit(z));fresh=float(expit(z_new));target=int(y[index])
                s.require(int(saved['target'])==target,'Saved target mismatch')
                brier=(p-target)**2;logloss=float(np.logaddexp(0.,z)-target*z)
                for name,value in [('log_odds',z),('probability',p),('brier',brier),('log_loss',logloss)]:
                    saved_error=max(saved_error,s.close(value,float(saved[name]),label='Saved '+name))
                predictions.append(dict(model=model['id'],**{k:row[k] for k in s.KEYS},target=target,
                    probability=p,log_odds=float(z),brier=brier,log_loss=logloss,refit_probability=fresh,
                    refit_brier=(fresh-target)**2,refit_log_loss=float(np.logaddexp(0.,z_new)-target*z_new)))
            difference=abs(float(np.mean((expit(saved_z)-y[test])**2)-np.mean((expit(new_z)-y[test])**2)))
            s.require(difference<=s.PLAN['independent_refit_brier_tolerance'],'Refit fold Brier mismatch')
            checks.append(dict(model=model['id'],heldout_block=heldout,saved_arithmetic_error=saved_error,
                maximum_refit_probability_error=error,objective_difference=objective_difference,refit_brier_difference=difference,submitted_gradient=gradient))
    s.csv_write(output/'predictions.csv',predictions);s.dump(output/'refits.json',new_fits);s.dump(output/'fit_checks.json',checks)
    return predictions,checks
